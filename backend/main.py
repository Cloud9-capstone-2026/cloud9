"""
[레이트리밋 추가 — 2026-08-17]
/auth/login, /auth/signup이 지금까지 완전히 무방비였음 — 브루트포스
비밀번호 시도나 스팸 가입을 막을 방법이 없었음. slowapi(IP 기준 카운트)로
분당 요청 수를 제한. 실제 제한 값은 routers/auth.py에 엔드포인트별로
붙어있고, 여기서는 앱 전역에 필요한 배선(limiter 등록, 초과 시 429 응답
핸들러)만 한다.
"""
from dotenv import load_dotenv
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.settings import get
load_dotenv()

# .env(로컬 개발용 폴백)를 먼저 채운 뒤, EC2에서는 이 호출이 진짜 비밀값
# 3개(DATABASE_URL/JWT_SECRET_KEY/GMAIL_APP_PASSWORD)를 Parameter Store
# 값으로 덮어쓴다. 로컬에서는 IAM 역할이 없어 조용히 실패하고 .env 값이
# 그대로 유지된다 (2026-08-26, secrets_loader.py 참고).
from secrets_loader import load_secrets_into_env
load_secrets_into_env()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text
from database import engine, Base, SessionLocal
from rate_limit import limiter
from routers import trades, analysis, jobs, auth, survey
import uvicorn
import os

Base.metadata.create_all(bind=engine)

# 이전 프로세스가 남긴 미완료 분석 job 정리 — 재시작으로 끊긴 작업이 running/
# pending으로 남으면 폴링이 영영 완료 신호를 못 받는다. (pipeline/jobs.py 참조)
from pipeline.jobs import recover_stale_jobs
recover_stale_jobs()

app = FastAPI(title="Canary API")

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(trades.router, prefix="/trades", tags=["trades"])
app.include_router(analysis.router, prefix="/analysis", tags=["analysis"])
app.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
app.include_router(survey.router, prefix="/survey", tags=["survey"])

@app.get("/")
def root():
    return {"message": "Canary API 작동 중"}

@app.get("/health")
def health():
    db_ok = True
    try:
        db = SessionLocal()
        try:
            db.execute(text("SELECT 1"))
        finally:
            db.close()
    except Exception:
        db_ok = False

    body = {"status": "ok" if db_ok else "degraded",
            "db": "ok" if db_ok else "error"}
    if not db_ok:
        return JSONResponse(status_code=503, content=body)
    return body

if __name__ == "__main__":
    port = int(get("app.port", 8080, env_override="PORT"))
    uvicorn.run("main:app", host="0.0.0.0", port=port)