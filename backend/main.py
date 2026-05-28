from fastapi import FastAPI
from database import engine, Base
from routers import trades, analysis
import uvicorn
import os

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Canary API")

app.include_router(trades.router, prefix="/trades", tags=["trades"])
app.include_router(analysis.router, prefix="/analysis", tags=["analysis"])

@app.get("/")
def root():
    return {"message": "Canary API 작동 중"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run("main:app", host="0.0.0.0", port=port)