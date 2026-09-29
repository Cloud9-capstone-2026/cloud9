"""
GET /coach/scores — 본인 계좌의 편향별 점수(편향마다 해당 거래 쪽만 평균).

계산은 pipeline.coach — 라우터는 로그인 사용자 기준으로 부르기만 한다.
응답: {"scores": {편향: {"score": 0~100 | null, "n_trades", "side"}}}.
score가 null이면 해당 쪽 거래가 없는 것
(0점이 아님 — 화면에서 구분 표시 필요). n_trades로 몇 건 기준인지 알 수 있다.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from auth import get_current_user
from database import get_db
from orm import User
from pipeline.coach import load_account_bias_scores

router = APIRouter()


@router.get("/scores")
def get_scores(db: Session = Depends(get_db),
               current_user: User = Depends(get_current_user)):
    return load_account_bias_scores(db, current_user.id)
