"""
GET /jobs/{job_id} — 분석 작업 상태.
업로드 응답의 job_id로 1~2초 간격 폴링,
done/failed가 오면 중단. done이면 기존 결과 조회 API로 이동.

- 소유자 확인: 이제 쿼리 파라미터 user_id 대신 JWT에서 추출한 current_user.id로 비교.
  기존 주석대로 "인증 도입 시 주입 지점만 바뀌면 된다"던 부분이 바로 여기.
- error_reason(내부 기록)은 절대 응답에 넣지 않는다 — failed는 일반 문구만.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from auth import get_current_user
from database import get_db
from orm import AnalysisJob, User

router = APIRouter()


@router.get("/{job_id}")
def get_job(job_id: int,
            db: Session = Depends(get_db),
            current_user: User = Depends(get_current_user)):
    job = db.query(AnalysisJob).filter(AnalysisJob.id == job_id).first()
    if job is None:
        raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다")
    if job.user_id is not None and job.user_id != current_user.id:
        # 존재 여부도 숨김 — 타인 job의 존재를 추측할 수 없게 404로 통일
        raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다")

    out = {"job_id": job.id, "status": job.status}
    if job.status == "done":
        out["upload_id"] = job.upload_id
    elif job.status == "failed":
        out["message"] = "분석에 실패했습니다"
    return out