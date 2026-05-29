from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:DaneDVBkeuAFOVTZzXEIjSBkTAIMSvaV@zephyr.proxy.rlwy.net:49651/railway")
print(f"DATABASE_URL: {DATABASE_URL}")

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,   # 사용 전 ping → 끊긴 connection 자동 폐기·재생성
    pool_recycle=300,     # 5분 이상 된 connection은 사용 전 폐기 (Railway proxy idle 회피)
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()