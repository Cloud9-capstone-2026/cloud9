"""
거래 일지 CRUD — 거래(Trade) 1건당 사용자가 작성하는 일지 1건(1:1).

POST   /journals        — 특정 거래에 대한 일지 신규 작성.
GET    /journals        — 본인 일지 목록(최신순, 페이지네이션), Trade 조인해서
                           stock/date/type 채워 반환.
PUT    /journals/{id}   — 일지 수정(emotion/reason/review만 — 어느 거래에
                           달린 일지인지는 변경 불가, 프론트 "수정하기"도
                           거래 자체는 안 바꿈).
DELETE /journals/{id}   — 일지 삭제.

[스펙 출처] frontend/src/screens/JournalWriteScreen.tsx, data/types.ts
(2026-09 확인). risk는 이 라우터 응답에 없음 — GET /trades가 분석 점수를
아직 안 내려줘서 선행 작업 필요(orm.TradeJournal 독스트링 참고).
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from auth import get_current_user
from database import get_db
from orm import Trade, TradeJournal, User

router = APIRouter()

# 프론트 theme/tokens.ts의 EMOTIONS와 동기화 필요 — 프론트가 새 태그를
# 추가하면 여기도 같이 바꿔야 400이 안 남.
EMOTIONS = {"조급함", "욕심", "두려움", "확신", "홧김", "미련", "불안", "무심함", "후회", "흥분"}


class JournalCreateRequest(BaseModel):
    trade_id: int
    emotion: str = Field(min_length=1, max_length=20)
    reason: str = Field(min_length=1, max_length=2000)
    review: str = Field(min_length=1, max_length=2000)


class JournalUpdateRequest(BaseModel):
    emotion: str = Field(min_length=1, max_length=20)
    reason: str = Field(min_length=1, max_length=2000)
    review: str = Field(min_length=1, max_length=2000)


def _validate_emotion(emotion: str) -> None:
    if emotion not in EMOTIONS:
        raise HTTPException(400, f"emotion은 {sorted(EMOTIONS)} 중 하나여야 합니다")


def _own_trade_or_404(db: Session, trade_id: int, user_id: int) -> Trade:
    trade = (
        db.query(Trade)
        .filter(Trade.id == trade_id, Trade.user_id == user_id)
        .first()
    )
    if trade is None:
        raise HTTPException(404, "거래를 찾을 수 없습니다")
    return trade


def _serialize(j: TradeJournal, trade: Trade) -> dict:
    return {
        "id": j.id,
        "trade_id": j.trade_id,
        "stock": trade.종목명,
        "date": trade.거래일자,
        "type": trade.거래구분,
        "emotion": j.emotion,
        "memo": j.reason[:40],
        "reason": j.reason,
        "review": j.review,
        "created_at": j.created_at,
        "updated_at": j.updated_at,
    }


# POST /journals — 거래 1건에 일지는 1개만. 이미 있으면 409로 명시 응답
# (프론트가 그 경우엔 PUT으로 가야 하므로, 조용히 upsert로 덮지 않음).
@router.post("/", status_code=201)
def create_journal(
    payload: JournalCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    trade = _own_trade_or_404(db, payload.trade_id, current_user.id)
    _validate_emotion(payload.emotion)

    existing = (
        db.query(TradeJournal)
        .filter(TradeJournal.trade_id == payload.trade_id,
                TradeJournal.user_id == current_user.id)
        .first()
    )
    if existing is not None:
        raise HTTPException(409, "이 거래에는 이미 일지가 있습니다")

    journal = TradeJournal(
        user_id=current_user.id,
        trade_id=payload.trade_id,
        emotion=payload.emotion,
        reason=payload.reason,
        review=payload.review,
    )
    db.add(journal)
    db.commit()
    db.refresh(journal)
    return _serialize(journal, trade)


@router.get("/")
def get_journals(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rows = (
        db.query(TradeJournal, Trade)
        .join(Trade, Trade.id == TradeJournal.trade_id)
        .filter(TradeJournal.user_id == current_user.id)
        .order_by(TradeJournal.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return [_serialize(j, t) for j, t in rows]


@router.put("/{journal_id}")
def update_journal(
    journal_id: int,
    payload: JournalUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _validate_emotion(payload.emotion)
    journal = (
        db.query(TradeJournal)
        .filter(TradeJournal.id == journal_id, TradeJournal.user_id == current_user.id)
        .first()
    )
    if journal is None:
        raise HTTPException(404, "일지를 찾을 수 없습니다")

    journal.emotion = payload.emotion
    journal.reason = payload.reason
    journal.review = payload.review
    db.commit()
    db.refresh(journal)

    trade = db.query(Trade).filter(Trade.id == journal.trade_id).first()
    return _serialize(journal, trade)


@router.delete("/{journal_id}")
def delete_journal(
    journal_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    journal = (
        db.query(TradeJournal)
        .filter(TradeJournal.id == journal_id, TradeJournal.user_id == current_user.id)
        .first()
    )
    if journal is None:
        raise HTTPException(404, "일지를 찾을 수 없습니다")
    db.delete(journal)
    db.commit()
    return {"id": journal_id, "deleted": True}