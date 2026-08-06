"""
GET /jobs/{job_id} — 분석 작업 상태 폴링 (2-2).

프론트 계약(도경 공유분): 업로드 응답의 job_id로 1~2초 간격 폴링,
done/failed가 오면 중단. done이면 기존 결과 조회 API로 이동.

- 소유자 확인: job.user_id가 있으면 요청 user_id와 불일치 시 404
  (존재 여부도 숨김 — 타인 job의 존재를 추측할 수 없게).
  로그인 도입 전에는 job.user_id가 비어 있어 검증이 자동 통과하고,
  네이버 로그인이 붙으면 user_id 주입 지점만 인증 값으로 바뀌면 된다.
- error_reason(내부 기록)은 절대 응답에 넣지 않는다 — failed는 일반 문구만.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from orm import AnalysisJob

router = APIRouter()


@router.get("/{job_id}")
def get_job(job_id: int, user_id: int | None = None,
            db: Session = Depends(get_db)):
    job = db.query(AnalysisJob).filter(AnalysisJob.id == job_id).first()
    if job is None:
        raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다")
    if job.user_id is not None and job.user_id != user_id:
        raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다")

    out = {"job_id": job.id, "status": job.status}
    if job.status == "done":
        out["upload_id"] = job.upload_id
    elif job.status == "failed":
        out["message"] = "분석에 실패했습니다"
    return out
