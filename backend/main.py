from fastapi import FastAPI
from database import engine, Base
from routers import trades

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Canary API")

app.include_router(trades.router, prefix="/trades", tags=["trades"])

@app.get("/")
def root():
    return {"message": "Canary API 작동 중"}

# analysis 추가
from routers import trades, analysis  

app.include_router(analysis.router, prefix="/analysis", tags=["analysis"])