from pathlib import Path

from fastapi import (APIRouter, BackgroundTasks, Depends, File, HTTPException,
                     UploadFile)
from sqlalchemy.orm import Session
from database import get_db
from orm import Trade, CsvUpload, AnalysisJob
from pipeline.jobs import run_analysis_job
from pipeline.upload_store import ALLOWED_EXTS, save_upload

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

# POST /trades/upload — 원본 파일 저장 + 분석 job 생성 후 즉시 202 반환
# 파싱·매핑(증권사별 양식 → 표준 스키마, LLM 매핑표)·거래 저장·분석은 전부
# BackgroundTasks의 worker(pipeline.jobs)가 수행 — LLM 호출이 수 초라
# 요청 안에서 하면 즉시 응답 원칙이 깨진다.
@router.post("/upload", status_code=202)
async def upload_trades(background_tasks: BackgroundTasks,
                        file: UploadFile = File(...),
                        db: Session = Depends(get_db)):
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXTS:
        raise HTTPException(400, "지원하지 않는 파일 형식입니다 (csv/xlsx/xls)")
    contents = await file.read()
    if not contents:
        raise HTTPException(400, "빈 파일입니다")

    # 1. csv_uploads INSERT + 원본 파일 보관 (row_count는 매핑 후 worker가 채움)
    csv_upload = CsvUpload(file_name=file.filename, status="pending")
    db.add(csv_upload)
    db.flush()
    save_upload(csv_upload.id, file.filename, contents)

    # 2. 분석 job 생성(pending). upload_id unique — 같은 업로드에 중복 생성 불가.
    job = AnalysisJob(upload_id=csv_upload.id, status="pending")
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
