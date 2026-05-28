from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.orm import Session
from database import get_db
from models import Trade
import pandas as pd
import io

router = APIRouter()

# GET /trades — DB에서 전체 거래 내역 조회
@router.get("/")
def get_trades(db: Session = Depends(get_db)):
    trades = db.query(Trade).all()
    return trades

# POST /trades/upload — CSV 업로드 → DB 저장
@router.post("/upload")
async def upload_trades(file: UploadFile = File(...), db: Session = Depends(get_db)):
    contents = await file.read()
    df = pd.read_csv(io.StringIO(contents.decode("utf-8-sig")))

    # 1. csv_uploads에 먼저 INSERT
    csv_upload = CsvUpload(
        file_name = file.filename,
        row_count = len(df),
        status    = "pending"
    )
    db.add(csv_upload)
    db.flush()  # id 바로 받아오기 위해 flush

    # 2. trades 저장 시 upload_id 함께 저장
    for _, row in df.iterrows():
        trade = Trade(
            upload_id = csv_upload.id,  # 연결
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

    # 3. 저장 완료 후 status를 done으로 업데이트
    csv_upload.status = "done"
    db.commit()

    return {"message": f"{len(df)}건 저장 완료", "upload_id": csv_upload.id}