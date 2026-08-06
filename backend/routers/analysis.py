import re
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from orm import AnalysisResult

router = APIRouter()


def _parse_user_id(raw) -> int | None:
    if raw is None:
        return None
    match = re.search(r"(\d+)$", str(raw))
    return int(match.group(1)) if match else None


# POST /analysis — C파트 분석 결과 받아서 거래별 1행씩 저장
@router.post("/")
def save_analysis(data: dict, db: Session = Depends(get_db)):
    user_id = _parse_user_id(data.get("user_id"))
    ensemble = data.get("detection_result", {}).get("ensemble", [])

    for e in ensemble:
        deep = e.get("deep") or {}
        row = AnalysisResult(
            user_id     = user_id,
            rule_score  = (e.get("rule") or {}).get("score"),
            stat_score  = (e.get("stat") or {}).get("score"),
            lstm_score  = deep.get("score"),  # 3계층 판정 불가 거래는 None
            final_score = None,               # 가중합 폐기
            is_anomaly  = e.get("verdict") == "이상",
            xai_result  = {
                "날짜": e.get("날짜"),
                "종목명": e.get("종목명"),
                "verdict": e.get("verdict"),
                "flags": e.get("flags"),
                "layers_available": e.get("layers_available"),
                "triggered_rules": (e.get("rule") or {}).get("triggered_rules"),
                "mahalanobis": (e.get("stat") or {}).get("mahalanobis"),
                "top_bias": deep.get("top_bias"),
            },
        )
        db.add(row)
    db.commit()
    return {"message": "분석 결과 저장 완료", "saved_count": len(ensemble)}

# GET /analysis — A파트에 분석 결과 전달
@router.get("/")
def get_analysis(db: Session = Depends(get_db)):
    results = db.query(AnalysisResult).all()
    return results