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

    for _, row in df.iterrows():
        trade = Trade(
            거래일자 = row["거래일자"],
            종목명   = row["종목명"],
            거래구분 = row["거래구분"],
            거래수량 = int(row["거래수량"]),
            거래단가 = int(row["거래단가"]),
            거래금액 = int(row["거래금액"]),
            수수료   = int(row["수수료"]),
            거래세   = int(row["거래세"]),
            정산금액 = int(row["정산금액"]),
        )
        db.add(trade)

    db.commit()
    return {"message": f"{len(df)}건 저장 완료"}