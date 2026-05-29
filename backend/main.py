import sys
from pathlib import Path

# 프로젝트 루트를 import 경로에 추가 (pipeline, ML models 디렉토리 접근용)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import engine, Base
from routers import trades, analysis
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

app.include_router(trades.router, prefix="/trades", tags=["trades"])
app.include_router(analysis.router, prefix="/analysis", tags=["analysis"])

@app.get("/")
def root():
    return {"message": "Canary API 작동 중"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
