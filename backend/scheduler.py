"""
CSV 원본 90일 보관 정책 배치 + DART 공시 갱신 배치.

- cleanup_old_csv_files: 업로드 90일 지난 원본(upload_files.content)만
  NULL로 비운다. 분석 결과(analysis_results)는 그대로 유지.
- refresh_dart_disclosures(pipeline/dart_news.py): 최근 7일 OpenDART 공시를
  캐시에 반영(2026-09-09 추가). 3시간마다 — 일 1만 콜 쿼터 대비 여유 많음.

두 배치 모두 APScheduler BackgroundScheduler로 실행한다.

2026-10-04: 회원 탈퇴 유예 배치(process_scheduled_withdrawals) 제거 —
탈퇴가 즉시 삭제로 바뀌어 /auth/withdraw에서 바로 처리한다
(account_deletion.py 참고).
"""
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.background import BackgroundScheduler

from database import SessionLocal
from orm import CsvUpload, UploadFile
from pipeline.dart_news import refresh_dart_disclosures

CSV_RETENTION_DAYS = 90


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
    scheduler.add_job(cleanup_old_csv_files, "cron", hour=3, minute=30, id="cleanup_old_csv_files")
    scheduler.add_job(refresh_dart_disclosures, "cron", hour="*/3", id="refresh_dart_disclosures")
    scheduler.start()
    return scheduler