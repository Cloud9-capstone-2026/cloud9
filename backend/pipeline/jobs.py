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
from collections import Counter
from datetime import datetime

from database import SessionLocal
from orm import AnalysisJob, AnalysisResult, CsvUpload, Trade
from pipeline.csv_mapper import MappingError, map_file
from pipeline.detect import run_pipeline_from_db
from pipeline.upload_store import load_upload

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

    각 행에 업로드 주인(CsvUpload.user_id)을 새긴다 — 조회 API가 본인
    거래만 필터하므로 이게 없으면 업로드한 거래가 화면에 안 보인다.

    중복 판정은 같은 사용자 범위에서 5컬럼(거래일자·종목명·거래구분·거래수량·
    거래단가) 키의 **개수 대조**다: 파일에 같은 키가 F행, DB에 D행이면 F-D행만
    저장. 존재 여부(있냐 없냐)로 걸렀던 옛 방식은 분할 체결·같은 날 동일 조건
    재거래처럼 똑같이 생긴 진짜 거래 여러 건 중 첫 건만 남기고 유실시켰다
    (2026-09-02 수리). 개수 대조면 그 경우 전부 저장되고, 같은 파일 재업로드는
    여전히 전량 걸러진다(멱등). 정산금액은 증권사 CSV에 없어 기본값으로
    채워지므로 키에 넣으면 판정이 왜곡된다. 사용자 범위 제한이 없으면 다른
    유저의 동일 거래가 "중복"으로 오인되어 저장이 스킵된다.
    detect(분석)는 신규 판정을 여기에 위임한다 — upload_id로 저장된 행 전부가
    신규다(중복 걸러내기는 이 함수가 유일한 책임 지점).
    """
    loaded = load_upload(upload_id, db)  # upload_files 테이블에서 원본 조회
    if loaded is None:
        raise MappingError(f"업로드 원본 파일 없음: upload_id={upload_id}")
    raw, filename = loaded
    out = map_file(raw, filename)

    upload = db.query(CsvUpload).filter(CsvUpload.id == upload_id).first()
    owner_user_id = upload.user_id if upload else None

    # 기존 거래의 5키 개수를 쿼리 1번으로 적재 (행별 존재 쿼리 N번 → 1번)
    owner_filter = (Trade.user_id == owner_user_id) if owner_user_id is not None \
        else Trade.user_id.is_(None)
    existing = Counter(
        db.query(Trade.거래일자, Trade.종목명, Trade.거래구분,
                 Trade.거래수량, Trade.거래단가).filter(owner_filter).all())

    new_count = 0
    for _, row in out.iterrows():
        거래일자 = row["거래일자"].date()
        key = (거래일자, str(row["종목명"]), row["거래구분"],
               int(row["거래수량"]), int(row["거래단가"]))
        if existing[key] > 0:
            existing[key] -= 1  # DB의 기존 1건과 상쇄 — 파일에 더 있는 만큼만 신규
            continue
        db.add(Trade(
            user_id   = owner_user_id,
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


def recover_stale_jobs() -> int:
    """서버 기동 시 1회(main.py) — 이전 프로세스가 남긴 미완료 job 정리.

    분석은 웹서버 프로세스 안(BackgroundTasks)에서 돌므로 재시작하면 실행
    중이던 작업(running)도, 대기열에 있던 작업(pending — 대기열 자체가 죽은
    프로세스 메모리)도 함께 증발한다. 그런데 DB 상태는 남아서 폴링이 영영
    done/failed 신호를 못 받는다. 기동 직후에는 실제로 도는 분석이 있을 수
    없으므로(요청받기 전 + 분석은 이 프로세스에서만) 남은 running·pending은
    전부 고아 — failed로 정리해 사용자가 재업로드하게 한다.

    이때 그 업로드가 만들다 만 중간 산출물(저장된 거래·분석 결과)도 함께
    지운다 — "전부 아니면 전무"를 재시작 실패에도 적용. 남겨두면 재업로드가
    전 행을 중복으로 걸러 신규 0건이 되고, 저장만 되고 판정은 영영 없는
    거래가 생긴다. 지우면 죽은 시점과 무관하게 재업로드가 깨끗한 첫
    업로드처럼 저장→분석 전 과정을 다시 돈다. 원본 파일은 디스크에 남아
    재업로드·원인 조사가 가능하다.

    정리 실패가 서버 기동을 막으면 안 되므로 전체를 예외로 감싼다.

    ※ 단일 인스턴스 전제: "기동 시점의 running·pending = 전부 고아"는 서버
    프로세스가 하나일 때만 참이다. 멀티 워커·다중 인스턴스·무중단 배포(구·신
    프로세스 공존)를 도입하면 이 일괄 정리가 옆 프로세스의 정상 작업을 죽이므로,
    그때는 lease(작업의 최종 갱신 시각) 기반 stale 판정으로 교체해야 한다."""
    try:
        db = SessionLocal()
        try:
            stale = (db.query(AnalysisJob)
                       .filter(AnalysisJob.status.in_(["running", "pending"]))
                       .all())
            for job in stale:
                job.status = "failed"
                job.error_reason = "서버 재시작으로 중단됨"  # 내부 기록만
                job.finished_at = datetime.now()
                db.query(Trade).filter(
                    Trade.upload_id == job.upload_id
                ).delete(synchronize_session=False)
                db.query(AnalysisResult).filter(
                    AnalysisResult.upload_id == job.upload_id
                ).delete(synchronize_session=False)
                upload = db.query(CsvUpload).filter(
                    CsvUpload.id == job.upload_id).first()
                if upload:
                    upload.status = "failed"
                    upload.row_count = None  # 지웠으므로 건수도 무효
            db.commit()
            if stale:
                logger.warning("재시작으로 중단된 job %d건 실패 처리", len(stale))
            return len(stale)
        finally:
            db.close()
    except Exception as e:  # noqa: BLE001 — 정리 실패해도 기동은 계속
        logger.warning("stale job 정리 실패 — 기동 계속: %r", e)
        return 0


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
