"""
routers/analysis.py 전체 교체본.

변경 사항:
- GET /analysis: JWT 인증 추가, 본인 결과만 필터링 (trades.py와 동일 패턴).
- POST /analysis: 실제 운영 흐름에서는 안 쓰임을 확인함 —
  pipeline/detect.py가 백그라운드 job 안에서 AnalysisResult를 직접 저장하고,
  이 엔드포인트를 HTTP로 호출하는 코드는 어디에도 없음 (C파트 로직이
  routers를 거치지 않고 파이프라인에 완전히 통합돼 있음).
  삭제 대신 일단 남겨두되 "테스트/디버그 전용"이라고 명시하고 JWT는 걸지 않음
  (운영 트래픽에 안 쓰이므로 인증 우선순위 낮음). 필요 없다고 판단되면
  다음 정리 때 완전히 삭제해도 무방.
"""
import re
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from auth import get_current_user
from database import get_db
from orm import AnalysisResult, User

router = APIRouter()


def _parse_user_id(raw) -> int | None:
    if raw is None:
        return None
    match = re.search(r"(\d+)$", str(raw))
    return int(match.group(1)) if match else None


# POST /analysis — [테스트/디버그 전용] 운영 흐름에서는 미사용.
# pipeline/detect.py가 백그라운드 job 안에서 AnalysisResult를 직접 저장하므로
# 이 엔드포인트를 거칠 필요가 없음. Swagger/Postman으로 임의 데이터 저장해
# 프론트/DB 확인용으로 쓸 때만 사용.
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
    return {"message": "분석 결과 저장 완료 (테스트용 엔드포인트)", "saved_count": len(ensemble)}


# GET /analysis — 본인 분석 결과만 조회 (프론트 리포트 화면이 실제로 쓰는 엔드포인트)
@router.get("/")
def get_analysis(db: Session = Depends(get_db),
                  current_user: User = Depends(get_current_user)):
    results = (
        db.query(AnalysisResult)
        .filter(AnalysisResult.user_id == current_user.id)
        .all()
    )
    return results