"""
분석 job worker — 업로드 라우트가 BackgroundTasks로 등록하는 실행 함수.

처리 순서: 원본 파일 매핑(LLM 매핑표 + 결정론적 변환, pipeline.csv_mapper) →
trades 저장 → 분석(pipeline.detect). 매핑을 업로드 요청이 아니라 여기서 하는
이유: LLM 호출이 수 초라 요청 안에서 하면 즉시 202 응답 원칙이 깨진다.

실행 규율:
- 요청 스코프 DB 세션 재사용 금지 — worker는 SessionLocal로 자체 세션을 열고 닫는다
  (요청 세션은 응답 반환 시 닫히므로 재사용하면 닫힌 세션에 쓰게 된다).
- 시작은 조건부 UPDATE(pending→running, WHERE status='pending')로만 한다.
  영향 행이 0이면 다른 worker가 이미 잡았거나 종료된 job — 즉시 반환.
  중복 실행 차단을 애플리케이션 로직이 아니라 DB 원자성에 맡기는 것.
- 종료 전이(running→done|failed)도 같은 방식의 조건부 UPDATE — 허용 외 전이
  (done→running 등)는 구조적으로 불가능하다.
- 실패 원인은 error_reason에 내부 기록만 하고 API 응답에는 내보내지 않는다.
- 재실행 안전: 거래 저장은 행별 중복 체크라 도중 실패 후 재시도해도 이중
  저장이 없다. 매핑 실패 시에는 아무것도 저장되지 않는다(전부 아니면 전무).
"""

import logging
from datetime import datetime

from database import SessionLocal
from orm import AnalysisJob, AnalysisResult, CsvUpload, Trade
from pipeline.csv_mapper import MappingError, map_file
from pipeline.detect import run_pipeline_from_db
from pipeline.upload_store import find_upload

logger = logging.getLogger(__name__)


def notify_done(job_id: int, upload_id: int) -> None:
    """완료 푸시 알림 구현하게되면....."""


def _transition(db, job_id: int, from_status: str, values: dict) -> bool:
    """조건부 상태 전이. 성공(1행) 여부 반환 — 0행이면 전이 불가 상태였던 것."""
    n = (db.query(AnalysisJob)
           .filter(AnalysisJob.id == job_id, AnalysisJob.status == from_status)
           .update(values, synchronize_session=False))
    db.commit()
    return n == 1


def _store_trades(db, upload_id: int) -> None:
    """원본 파일 매핑 → trades 저장. 실패는 예외로 — 호출부가 job 실패 처리.

    중복 체크는 5컬럼(거래일자·종목명·거래구분·거래수량·거래단가) — 증권사
    CSV에는 정산금액이 없어 기본값으로 채워지므로 중복 키에 넣으면 판정이
    왜곡되고, 분석(detect)의 신규 거래 추출 키와도 이 5컬럼이 일치한다.
    """
    path = find_upload(upload_id)
    if path is None:
        raise MappingError(f"업로드 원본 파일 없음: upload_id={upload_id}")
    out = map_file(path.read_bytes(), path.name)

    new_count = 0
    for _, row in out.iterrows():
        거래일자 = row["거래일자"].date()
        exists = db.query(Trade).filter(
            Trade.거래일자 == 거래일자,
            Trade.종목명   == str(row["종목명"]),
            Trade.거래구분 == row["거래구분"],
            Trade.거래수량 == int(row["거래수량"]),
            Trade.거래단가 == int(row["거래단가"]),
        ).first()
        if exists:
            continue
        db.add(Trade(
            upload_id = upload_id,
            거래일자  = 거래일자,
            종목명    = str(row["종목명"]),
            거래구분  = row["거래구분"],
            거래수량  = int(row["거래수량"]),
            거래단가  = int(row["거래단가"]),
            거래금액  = int(row["거래금액"]),
            수수료    = int(row["수수료"]),
            거래세    = int(row["거래세"]),
            정산금액  = int(row["정산금액"]),
        ))
        new_count += 1

    upload = db.query(CsvUpload).filter(CsvUpload.id == upload_id).first()
    if upload:
        upload.row_count = new_count
        upload.status = "done"
    db.commit()
    logger.info("upload %s: 거래 %d건 저장 (중복 %d건 스킵)",
                upload_id, new_count, len(out) - new_count)


def _mark_upload_failed(db, upload_id: int) -> None:
    try:
        upload = db.query(CsvUpload).filter(CsvUpload.id == upload_id).first()
        if upload:
            upload.status = "failed"
            db.commit()
    except Exception:  # noqa: BLE001 — 상태 표기 실패가 실패 처리를 막으면 안 됨
        db.rollback()


def run_analysis_job(job_id: int) -> None:
    db = SessionLocal()
    try:
        if not _transition(db, job_id, "pending",
                           {"status": "running", "started_at": datetime.now()}):
            logger.info("job %s: pending 아님 — 이미 처리 중/완료, 건너뜀", job_id)
            return
        job = db.query(AnalysisJob).filter(AnalysisJob.id == job_id).first()
        try:
            _store_trades(db, job.upload_id)
            run_pipeline_from_db(
                db,
                upload_id=job.upload_id,
                Trade=Trade,
                AnalysisResult=AnalysisResult,
                user_id=f"user_{job.user_id:03d}" if job.user_id else "user_001",
                job_id=job.id,
            )
            _transition(db, job_id, "running",
                        {"status": "done", "finished_at": datetime.now()})
            notify_done(job_id, job.upload_id)
        except Exception as e:  # noqa: BLE001 — 실패는 상태로 기록, 서버는 계속
            db.rollback()
            logger.warning("job %s 처리 실패: %r", job_id, e)
            _mark_upload_failed(db, job.upload_id)
            _transition(db, job_id, "running",
                        {"status": "failed", "finished_at": datetime.now(),
                         "error_reason": repr(e)[:500]})
    finally:
        db.close()
