"""
[/health 엔드포인트 추가 — 2026-08-17]
단순히 "서버 프로세스가 살아있다"만 확인하면 오늘 겪은 것 같은 상황
(uvicorn은 떴는데 DB 연결이나 설정 문제로 실제 요청은 다 실패하는 경우)을
구분 못 함. 그래서 DB 연결까지 실제로 확인하도록 만듦.

- DB 연결 성공: 200 + {"status": "ok", "db": "ok"}
- DB 연결 실패: 503 + {"status": "degraded", "db": "error"} — 500이 아니라
  503(Service Unavailable)을 쓰는 이유: 서버 코드 자체는 정상이고 의존
  서비스(DB)만 문제인 상황이라, 모니터링/헬스체크 도구들이 관례적으로
  503을 "일시적으로 이용 불가"로 해석하기 때문.
- 인증 불필요 — 로드밸런서/모니터링이 토큰 없이 주기적으로 찔러보는 용도.
"""
from dotenv import load_dotenv
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.settings import get
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from database import engine, Base, SessionLocal
from routers import trades, analysis, jobs, auth
import uvicorn
import os

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Canary API")

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