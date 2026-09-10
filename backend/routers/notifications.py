"""
GET  /notifications           — 본인 알림 목록(최신순, 페이지네이션) + 안읽음 수.
POST /notifications/{id}/read — 알림 1건 읽음 처리.

알림 생성은 이 라우터가 아니라 pipeline/jobs.py(run_analysis_job)와
routers/trades.py(upload_trades)가 각 상태 전이 시점에 직접 담당한다.
type 값은 프론트 NotifKind와 동일: upload/uploadFail/analysis/analyzeFail.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from auth import get_current_user
from database import get_db
from orm import Notification, User

router = APIRouter()


def _serialize(n: Notification) -> dict:
    return {
        "id": n.id,
        "type": n.type,
        "file_name": n.file_name,
        "trade_count": n.trade_count,
        "job_id": n.job_id,
        "upload_id": n.upload_id,
        "is_read": n.is_read,
        "created_at": n.created_at,
    }


@router.get("/")
def get_notifications(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    notifications = (
        db.query(Notification)
        .filter(Notification.user_id == current_user.id)
        .order_by(Notification.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    unread_count = (
        db.query(Notification)
        .filter(Notification.user_id == current_user.id,
                Notification.is_read.is_(False))
        .count()
    )
    return {
        "notifications": [_serialize(n) for n in notifications],
        "unread_count": unread_count,
    }


@router.post("/{notification_id}/read")
def mark_notification_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    notification = (
        db.query(Notification)
        .filter(Notification.id == notification_id,
                Notification.user_id == current_user.id)
        .first()
    )
    if notification is None:
        raise HTTPException(status_code=404, detail="알림을 찾을 수 없습니다")

    if not notification.is_read:
        notification.is_read = True
        db.commit()
        db.refresh(notification)

    return _serialize(notification)