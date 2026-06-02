from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./local.db")
_db_host = DATABASE_URL.split("@")[-1] if "@" in DATABASE_URL else DATABASE_URL
print(f"DATABASE_URL: {_db_host}")

# SQLite(로컬)는 멀티스레드 접근 옵션 필요, Postgres(배포)는 connection pool 관리
_is_sqlite = DATABASE_URL.startswith("sqlite")
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,   # 사용 전 ping → 끊긴 connection 자동 폐기·재생성
    pool_recycle=300,     # 5분 이상 된 connection은 사용 전 폐기 (Railway proxy idle 회피)
    connect_args={"check_same_thread": False} if _is_sqlite else {},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()