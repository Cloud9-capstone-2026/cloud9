"""
회원 탈퇴 유예 처리 + CSV 원본 90일 보관 정책 배치.

- process_scheduled_withdrawals: scheduled_deletion_at이 지난 계정을 실제로
  삭제한다. FK에 ondelete=CASCADE를 걸지 않고 애플리케이션 레벨에서 자식→
  부모 순서로 직접 삭제한다 (기존 FK 제약을 건드리는 마이그레이션을 피하기
  위한 의도적 선택, 2026-09-02).
- cleanup_old_csv_files: 업로드 90일 지난 원본(upload_files.content)만
  NULL로 비운다. 분석 결과(analysis_results)는 그대로 유지.

두 배치 모두 APScheduler BackgroundScheduler로 매일 새벽에 실행한다.
"""
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.background import BackgroundScheduler

from database import SessionLocal
from orm import (AnalysisJob, AnalysisResult, CsvUpload, SurveyResult, Trade,
                  UploadFile, User, UserRule)

WITHDRAWAL_GRACE_DAYS = 30
CSV_RETENTION_DAYS = 90


def _delete_user_cascade(db, user_id: int) -> None:
    """FK CASCADE 없이 자식 테이블부터 순서대로 삭제."""
    upload_ids = [
        row.id for row in db.query(CsvUpload.id).filter(CsvUpload.user_id == user_id).all()
    ]

    if upload_ids:
        db.query(AnalysisResult).filter(AnalysisResult.upload_id.in_(upload_ids)).delete(synchronize_session=False)
        db.query(AnalysisJob).filter(AnalysisJob.upload_id.in_(upload_ids)).delete(synchronize_session=False)
        db.query(UploadFile).filter(UploadFile.upload_id.in_(upload_ids)).delete(synchronize_session=False)
        db.query(Trade).filter(Trade.upload_id.in_(upload_ids)).delete(synchronize_session=False)

    # upload_id로 안 걸리는 잔여분(레거시 직접 저장 등) 정리
    db.query(AnalysisResult).filter(AnalysisResult.user_id == user_id).delete(synchronize_session=False)
    db.query(AnalysisJob).filter(AnalysisJob.user_id == user_id).delete(synchronize_session=False)
    db.query(Trade).filter(Trade.user_id == user_id).delete(synchronize_session=False)

    db.query(CsvUpload).filter(CsvUpload.user_id == user_id).delete(synchronize_session=False)
    db.query(SurveyResult).filter(SurveyResult.user_id == user_id).delete(synchronize_session=False)
    db.query(UserRule).filter(UserRule.user_id == user_id).delete(synchronize_session=False)

    db.query(User).filter(User.id == user_id).delete(synchronize_session=False)


def process_scheduled_withdrawals() -> None:
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        due_users = (
            db.query(User)
            .filter(User.scheduled_deletion_at.isnot(None))
            .filter(User.scheduled_deletion_at <= now)
            .all()
        )
        for user in due_users:
            _delete_user_cascade(db, user.id)
        db.commit()
    finally:
        db.close()


def cleanup_old_csv_files() -> None:
    db = SessionLocal()
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(days=CSV_RETENTION_DAYS)
        old_upload_ids = [
            row.id for row in db.query(CsvUpload.id).filter(CsvUpload.uploaded_at <= cutoff).all()
        ]
        if old_upload_ids:
            (
                db.query(UploadFile)
                .filter(UploadFile.upload_id.in_(old_upload_ids))
                .filter(UploadFile.content.isnot(None))
                .update({"content": None, "size": None}, synchronize_session=False)
            )
        db.commit()
    finally:
        db.close()


def start_scheduler() -> BackgroundScheduler:
    scheduler = BackgroundScheduler(timezone="Asia/Seoul")
    scheduler.add_job(process_scheduled_withdrawals, "cron", hour=3, minute=0, id="process_scheduled_withdrawals")
    scheduler.add_job(cleanup_old_csv_files, "cron", hour=3, minute=30, id="cleanup_old_csv_files")
    scheduler.start()
    return scheduler