from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from models import AnalysisResult

router = APIRouter()

# POST /analysis — C파트 분석 결과 받아서 저장
@router.post("/")
def save_analysis(data: dict, db: Session = Depends(get_db)):
    result = AnalysisResult(
        user_id     = data.get("user_id"),
        rule_score  = data.get("rule_score"),
        is_anomaly  = data.get("is_anomaly"),
        xai_result  = data.get("xai_result"),
    )
    db.add(result)
    db.commit()
    return {"message": "분석 결과 저장 완료"}

# GET /analysis — A파트에 분석 결과 전달
@router.get("/")
def get_analysis(db: Session = Depends(get_db)):
    results = db.query(AnalysisResult).all()
    return results