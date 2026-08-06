"""
분석 job worker (2-2) — 업로드 라우트가 BackgroundTasks로 등록하는 실행 함수.

실행 규율:
- 요청 스코프 DB 세션 재사용 금지 — worker는 SessionLocal로 자체 세션을 열고 닫는다
  (요청 세션은 응답 반환 시 닫히므로 재사용하면 닫힌 세션에 쓰게 된다).
- 시작은 조건부 UPDATE(pending→running, WHERE status='pending')로만 한다.
  영향 행이 0이면 다른 worker가 이미 잡았거나 종료된 job — 즉시 반환.
  중복 실행 차단을 애플리케이션 로직이 아니라 DB 원자성에 맡기는 것.
- 종료 전이(running→done|failed)도 같은 방식의 조건부 UPDATE — 허용 외 전이
  (done→running 등)는 구조적으로 불가능하다.
- 실패 원인은 error_reason에 내부 기록만 하고 API 응답에는 내보내지 않는다.
"""

import logging
from datetime import datetime

from database import SessionLocal
from orm import AnalysisJob, AnalysisResult, Trade
from pipeline.detect import run_pipeline_from_db

logger = logging.getLogger(__name__)


def notify_done(job_id: int, upload_id: int) -> None:
    """완료 푸시 알림 훅 — RN 푸시 구현 시 여기서 발송한다(지금은 자리만)."""


def _transition(db, job_id: int, from_status: str, values: dict) -> bool:
    """조건부 상태 전이. 성공(1행) 여부 반환 — 0행이면 전이 불가 상태였던 것."""
    n = (db.query(AnalysisJob)
           .filter(AnalysisJob.id == job_id, AnalysisJob.status == from_status)
           .update(values, synchronize_session=False))
    db.commit()
    return n == 1


def run_analysis_job(job_id: int) -> None:
    db = SessionLocal()
    try:
        if not _transition(db, job_id, "pending",
                           {"status": "running", "started_at": datetime.now()}):
            logger.info("job %s: pending 아님 — 이미 처리 중/완료, 건너뜀", job_id)
            return
        job = db.query(AnalysisJob).filter(AnalysisJob.id == job_id).first()
        try:
            run_pipeline_from_db(
                db,
                upload_id=job.upload_id,
                Trade=Trade,
                AnalysisResult=AnalysisResult,
                user_id=f"user_{job.user_id:03d}" if job.user_id else "user_001",
            )
            _transition(db, job_id, "running",
                        {"status": "done", "finished_at": datetime.now()})
            notify_done(job_id, job.upload_id)
        except Exception as e:  # noqa: BLE001 — 실패는 상태로 기록, 서버는 계속
            db.rollback()
            logger.warning("job %s 분석 실패: %r", job_id, e)
            _transition(db, job_id, "running",
                        {"status": "failed", "finished_at": datetime.now(),
                         "error_reason": repr(e)[:500]})
    finally:
        db.close()
