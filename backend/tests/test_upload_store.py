"""
업로드 원본 보관(pipeline/upload_store.py) — upload_files 테이블 왕복 검증.
디스크 폴백은 2026-09-02 삭제(테이블 상시 존재) — DB 경로만 남았다.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import orm
from database import Base
from pipeline import upload_store


@pytest.fixture()
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    session.add(orm.CsvUpload(id=7, file_name="원본.xls", status="pending"))
    session.commit()
    yield session
    session.close()


def test_db_roundtrip(db):
    upload_store.save_upload(7, b"<html>raw</html>", db)
    db.commit()
    assert upload_store.load_upload(7, db) == (b"<html>raw</html>", "원본.xls")
    assert upload_store.load_upload(99, db) is None  # 행 없음 → 호출자가 실패 처리
