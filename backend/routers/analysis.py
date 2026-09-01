"""
routers/analysis.py.

[입력검증 보강 — 2026-08-17]
POST /analysis가 기존엔 `data: dict`로 완전히 타입 없이 받았음 — 구조가
조금만 어긋나도 .get() 체인 중간에서 500이 나거나, 최악의 경우 None/빈값이
그대로 DB에 저장돼 잘못된 분석 결과가 조용히 쌓일 수 있었음.
아래처럼 중첩 Pydantic 모델로 명시하면, FastAPI가 요청 단계에서 구조를
검증해 맞지 않으면 422로 명확히 거부한다 (핸들러 코드에 도달하기 전에).

- GET /analysis: JWT 인증, 본인 결과만 필터링 (trades.py와 동일 패턴).
- POST /analysis: 실제 운영 흐름에서는 안 쓰임을 확인함 —
  pipeline/detect.py가 백그라운드 job 안에서 AnalysisResult를 직접 저장하고,
  이 엔드포인트를 HTTP로 호출하는 코드는 어디에도 없음. 삭제 대신 남겨두되
  "테스트/디버그 전용"으로 명시, JWT는 안 걺(운영 트래픽에 안 쓰이므로).
"""
import re
from typing import Optional, Union

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from auth import get_current_user
from database import get_db
from orm import AnalysisResult, User

router = APIRouter()


def _parse_user_id(raw) -> Optional[int]:
    if raw is None:
        return None
    match = re.search(r"(\d+)$", str(raw))
    return int(match.group(1)) if match else None


class RuleResult(BaseModel):
    score: Optional[float] = None
    triggered_rules: Optional[list] = None


class StatResult(BaseModel):
    score: Optional[float] = None
    mahalanobis: Optional[float] = None


class DeepResult(BaseModel):
    score: Optional[float] = None
    top_bias: Optional[str] = None


class EnsembleItem(BaseModel):
    날짜: Optional[str] = None
    종목명: Optional[str] = None
    verdict: Optional[str] = None
    flags: Optional[list] = None
    layers_available: Optional[list] = None
    rule: Optional[RuleResult] = None
    stat: Optional[StatResult] = None
    deep: Optional[DeepResult] = None


class DetectionResult(BaseModel):
    ensemble: list[EnsembleItem] = []


class SaveAnalysisRequest(BaseModel):
    user_id: Optional[Union[str, int]] = None
    detection_result: DetectionResult = DetectionResult()


# POST /analysis — [테스트/디버그 전용] 운영 흐름에서는 미사용.
# pipeline/detect.py가 백그라운드 job 안에서 AnalysisResult를 직접 저장하므로
# 이 엔드포인트를 거칠 필요가 없음. Swagger/Postman으로 임의 데이터 저장해
# 프론트/DB 확인용으로 쓸 때만 사용.
@router.post("/")
def save_analysis(payload: SaveAnalysisRequest, db: Session = Depends(get_db)):
    user_id = _parse_user_id(payload.user_id)

    for e in payload.detection_result.ensemble:
        row = AnalysisResult(
            user_id     = user_id,
            rule_score  = e.rule.score if e.rule else None,
            stat_score  = e.stat.score if e.stat else None,
            deep_score  = e.deep.score if e.deep else None,  # 3계층 판정 불가 거래는 None
            is_anomaly  = e.verdict == "이상",
            detail      = {
                "날짜": e.날짜,
                "종목명": e.종목명,
                "verdict": e.verdict,
                "flags": e.flags,
                "layers_available": e.layers_available,
                "triggered_rules": e.rule.triggered_rules if e.rule else None,
                "mahalanobis": e.stat.mahalanobis if e.stat else None,
                "top_bias": e.deep.top_bias if e.deep else None,
            },
        )
        db.add(row)
    db.commit()
    return {
        "message": "분석 결과 저장 완료 (테스트용 엔드포인트)",
        "saved_count": len(payload.detection_result.ensemble),
    }


# GET /analysis — 본인 분석 결과만 조회 (프론트 리포트 화면이 실제로 쓰는 엔드포인트)
# [페이지네이션 추가 — 2026-08-27] trades.py와 동일 이유·기본값.
@router.get("/")
def get_analysis(limit: int = Query(default=50, ge=1, le=200),
                  offset: int = Query(default=0, ge=0),
                  db: Session = Depends(get_db),
                  current_user: User = Depends(get_current_user)):
    results = (
        db.query(AnalysisResult)
        .filter(AnalysisResult.user_id == current_user.id)
        .order_by(AnalysisResult.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return results