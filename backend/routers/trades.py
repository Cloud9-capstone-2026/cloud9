from fastapi import APIRouter, BackgroundTasks, Depends, UploadFile, File
from sqlalchemy.orm import Session
from database import get_db
from orm import Trade, CsvUpload, AnalysisJob
from pipeline.jobs import run_analysis_job
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

# POST /trades/upload — CSV 저장 + 분석 job 생성 후 즉시 202 반환
# 분석은 BackgroundTasks의 worker(pipeline.jobs)가 수행 
@router.post("/upload", status_code=202)
async def upload_trades(background_tasks: BackgroundTasks,
                        file: UploadFile = File(...),
                        db: Session = Depends(get_db)):
    contents = await file.read()
    if file.filename.lower().endswith(('.xlsx', '.xls')):
        df = pd.read_excel(io.BytesIO(contents))
    else:
        df = pd.read_csv(io.StringIO(contents.decode("utf-8-sig")))
    # 날짜를 date 객체로 명시 변환 — Postgres는 문자열을 암묵 변환해주지만
    # sqlite(로컬·테스트)는 거부하므로 DB 무관하게 타입을 통일한다.
    df["거래일자"] = pd.to_datetime(df["거래일자"]).dt.date

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

    # 3. 분석 job 생성(pending). upload_id unique — 같은 업로드에 중복 생성 불가.
    job = AnalysisJob(upload_id=csv_upload.id, status="pending")
    db.add(job)

    # 4. commit이 끝난 뒤에만 백그라운드 등록 — worker는 자체 세션으로 읽으므로
    #    등록이 먼저면 미커밋 행을 못 보는 레이스가 생긴다.
    db.commit()
    db.refresh(job)
    background_tasks.add_task(run_analysis_job, job.id)

    return {
        "upload_id": csv_upload.id,
        "job_id": job.id,
        "status": job.status,
        "message": f"{new_count}건 저장 완료 (중복 {skip_count}건 스킵)",
    }
