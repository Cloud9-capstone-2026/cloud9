"""
GET /news         — 공시 목록(최신순, 페이지네이션 + 기간 필터). 홈 탭
                     "오늘의 주요 소식"(limit=3)과 전체 소식 화면이 같은
                     엔드포인트를 쓴다.
GET /news/related — 특정 종목 관련 공시(리포트 상세 "관련 공시·뉴스").
                     trade_id로 종목명을 알아내 그 종목 공시만 필터.

데이터는 refresh_dart_disclosures(scheduler.py, 3시간마다)가 미리 캐시해둔
dart_disclosures를 조회만 한다 — 요청마다 OpenDART를 직접 호출하지 않음.

[알아둘 것] title은 OpenDART report_nm 그대로라 mock처럼 내용을 요약한
문장이 아니라 공시 제목 그대로임(pipeline/dart_news.py 참고).
"""
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from auth import get_current_user
from database import get_db
from orm import DartDisclosure, Trade, User

router = APIRouter()

# 프론트 PERIODS(theme/tokens.ts)와 동기화 필요 — 프론트가 새 기간을 추가하면 여기도 맞춰야 함.
PERIOD_DAYS = {
    "최근 1개월": 30, "최근 3개월": 90, "최근 6개월": 180,
    "최근 1년": 365, "최근 3년": 365 * 3,
}


def _serialize(d: DartDisclosure) -> dict:
    return {
        "id": d.id,
        "corp": d.corp_name,
        "type": d.report_type,
        "title": d.title,
        "date": d.disclosure_date,
    }


@router.get("/")
def get_news(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    period: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(DartDisclosure)
    if period is not None:
        days = PERIOD_DAYS.get(period)
        if days is None:
            raise HTTPException(400, f"period는 {list(PERIOD_DAYS)} 중 하나여야 합니다")
        q = q.filter(DartDisclosure.disclosure_date >= date.today() - timedelta(days=days))

    news = (
        q.order_by(DartDisclosure.disclosure_date.desc(), DartDisclosure.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return [_serialize(n) for n in news]


@router.get("/related")
def get_related_news(
    trade_id: int = Query(...),
    limit: int = Query(default=3, ge=1, le=20),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """리포트 상세 화면용 — trade_id의 종목명과 일치하는 공시만, 최신순."""
    trade = (
        db.query(Trade)
        .filter(Trade.id == trade_id, Trade.user_id == current_user.id)
        .first()
    )
    if trade is None:
        raise HTTPException(404, "거래를 찾을 수 없습니다")

    news = (
        db.query(DartDisclosure)
        .filter(DartDisclosure.corp_name == trade.종목명)
        .order_by(DartDisclosure.disclosure_date.desc(), DartDisclosure.id.desc())
        .limit(limit)
        .all()
    )
    return [_serialize(n) for n in news]