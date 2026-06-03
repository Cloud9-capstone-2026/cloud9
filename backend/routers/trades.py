from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.orm import Session
from database import get_db
from orm import Trade, CsvUpload, AnalysisResult
from pipeline.detect import run_pipeline_from_db
import pandas as pd
import io

router = APIRouter()

# GET /trades/uploads — 업로드 히스토리 조회
@router.get("/uploads")
def get_uploads(db: Session = Depends(get_db)):
    uploads = db.query(CsvUpload).order_by(CsvUpload.id.desc()).all()
    return uploads

# GET /trades — DB에서 전체 거래 내역 조회
@router.get("/")
def get_trades(db: Session = Depends(get_db)):
    trades = db.query(Trade).all()
    return trades

# POST /trades/upload — CSV 업로드 → DB 저장 → 파이프라인 트리거 (in-process)
@router.post("/upload")
async def upload_trades(file: UploadFile = File(...), db: Session = Depends(get_db)):
    contents = await file.read()
    df = pd.read_csv(io.StringIO(contents.decode("utf-8-sig")))

    # 1. csv_uploads INSERT
    csv_upload = CsvUpload(
        file_name = file.filename,
        row_count = len(df),
        status    = "pending",
    )
    db.add(csv_upload)
    db.flush()

    # 2. trades 행별 INSERT (중복 체크 추가)
    new_count = 0
    skip_count = 0

    for _, row in df.iterrows():
        # 중복 체크: 6개 컬럼 모두 일치하면 스킵
        exists = db.query(Trade).filter(
            Trade.거래일자  == row["거래일자"],
            Trade.종목명    == row["종목명"],
            Trade.거래구분  == row["거래구분"],
            Trade.거래수량  == int(row["거래수량"]),
            Trade.거래단가  == int(row["거래단가"]),
            Trade.정산금액  == int(row["정산금액"]),
        ).first()

        if exists:
            skip_count += 1
            continue

        trade = Trade(
            upload_id = csv_upload.id,
            거래일자  = row["거래일자"],
            종목명    = row["종목명"],
            거래구분  = row["거래구분"],
            거래수량  = int(row["거래수량"]),
            거래단가  = int(row["거래단가"]),
            거래금액  = int(row["거래금액"]),
            수수료    = int(row["수수료"]),
            거래세    = int(row["거래세"]),
            정산금액  = int(row["정산금액"]),
        )
        db.add(trade)
        new_count += 1

    csv_upload.status = "done"
    csv_upload.row_count = new_count
    db.commit()

    # 3. 파이프라인 트리거 (in-process). 분석 실패해도 업로드는 살아남도록 try/except.
    analysis_summary = None
    try:
        analysis = run_pipeline_from_db(
            db,
            upload_id=csv_upload.id,
            Trade=Trade,
            AnalysisResult=AnalysisResult,
            user_id="user_001",
        )
        ensemble = analysis["detection_result"]["ensemble"]
        analysis_summary = {
            "new_trades_count": analysis["new_trades_count"],
            "anomalies": sum(1 for e in ensemble if e["is_anomaly"]),
            "saved_path": analysis.get("saved_path"),
        }
    except Exception as ex:
        analysis_summary = {"error": str(ex)}

    return {
        "message": f"{new_count}건 저장 완료 (중복 {skip_count}건 스킵)",
        "upload_id": csv_upload.id,
        "analysis": analysis_summary,
    }
