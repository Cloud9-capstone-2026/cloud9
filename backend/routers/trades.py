from pathlib import Path

from fastapi import (APIRouter, BackgroundTasks, Depends, File, HTTPException,
                     UploadFile)
from sqlalchemy.orm import Session
from auth import get_current_user
from database import get_db
from orm import Trade, CsvUpload, AnalysisJob, User
from pipeline.jobs import run_analysis_job
from pipeline.upload_store import ALLOWED_EXTS, save_upload

router = APIRouter()

# GET /trades/uploads — 본인 업로드 히스토리만 조회
@router.get("/uploads")
def get_uploads(db: Session = Depends(get_db),
                 current_user: User = Depends(get_current_user)):
    uploads = (
        db.query(CsvUpload)
        .filter(CsvUpload.user_id == current_user.id)
        .order_by(CsvUpload.id.desc())
        .all()
    )
    return uploads

# GET /trades — 본인 거래 내역만 조회
@router.get("/")
def get_trades(db: Session = Depends(get_db),
               current_user: User = Depends(get_current_user)):
    trades = db.query(Trade).filter(Trade.user_id == current_user.id).all()
    return trades

# POST /trades/upload — 원본 파일 저장 + 분석 job 생성 후 즉시 202 반환
@router.post("/upload", status_code=202)
async def upload_trades(background_tasks: BackgroundTasks,
                        file: UploadFile = File(...),
                        db: Session = Depends(get_db),
                        current_user: User = Depends(get_current_user)):
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXTS:
        raise HTTPException(400, "지원하지 않는 파일 형식입니다 (csv/xlsx/xls)")
    contents = await file.read()
    if not contents:
        raise HTTPException(400, "빈 파일입니다")

    # 1. csv_uploads INSERT + 원본 파일 보관 (row_count는 매핑 후 worker가 채움)
    csv_upload = CsvUpload(file_name=file.filename, status="pending", user_id=current_user.id)
    db.add(csv_upload)
    db.flush()
    save_upload(csv_upload.id, file.filename, contents)

    # 2. 분석 job 생성(pending). upload_id unique — 같은 업로드에 중복 생성 불가.
    job = AnalysisJob(upload_id=csv_upload.id, status="pending", user_id=current_user.id)
    db.add(job)

    # 3. commit이 끝난 뒤에만 백그라운드 등록 — worker는 자체 세션으로 읽으므로
    #    등록이 먼저면 미커밋 행을 못 보는 레이스가 생긴다.
    db.commit()
    db.refresh(job)
    background_tasks.add_task(run_analysis_job, job.id)

    return {
        "upload_id": csv_upload.id,
        "job_id": job.id,
        "status": job.status,
        "message": "파일 접수 완료, 분석 대기중",
    }