"""
업로드 원본 보관(pipeline/upload_store.py) — DB 우선·디스크 폴백 정책 검증.

upload_files 테이블은 팀장 작업으로 추후 생성되므로, 테스트 전용 ORM 클래스를
orm.UploadFile로 주입해 DB 경로를 고정하고, 없을 때는 디스크로 가는지 본다.
"""

import pytest
from sqlalchemy import Column, DateTime, Integer, LargeBinary, create_engine, func
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import orm
from database import Base
from pipeline import upload_store


@pytest.fixture()
def db_with_table(monkeypatch):
    """orm.UploadFile(노션 초안 컬럼)을 임시로 정의하고 인메모리 DB에 테이블 생성."""
    if not hasattr(orm, "UploadFile"):
        class UploadFile(Base):
            __tablename__ = "upload_files"
            __table_args__ = {"extend_existing": True}
            id = Column(Integer, primary_key=True)
            upload_id = Column(Integer, unique=True, nullable=False)
            content = Column(LargeBinary, nullable=False)
            size = Column(Integer, nullable=False)
            created_at = Column(DateTime, server_default=func.now())
        monkeypatch.setattr(orm, "UploadFile", UploadFile, raising=False)
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    db.add(orm.CsvUpload(id=7, file_name="원본.xls", status="pending"))
    db.commit()
    yield db
    db.close()


def test_db_roundtrip_when_table_exists(db_with_table, tmp_path, monkeypatch):
    monkeypatch.setattr(upload_store, "UPLOAD_DIR", tmp_path / "uploads")
    upload_store.save_upload(7, "원본.xls", b"<html>raw</html>", db=db_with_table)
    db_with_table.commit()
    assert not (tmp_path / "uploads").exists()  # 디스크엔 안 씀
    assert upload_store.load_upload(7, db_with_table) == (b"<html>raw</html>", "원본.xls")
    assert upload_store.load_upload(99, db_with_table) is None


def test_disk_fallback_when_no_table(tmp_path, monkeypatch):
    monkeypatch.setattr(upload_store, "UPLOAD_DIR", tmp_path / "uploads")
    monkeypatch.setattr(upload_store, "_model", lambda: None)  # 테이블 없음
    upload_store.save_upload(3, "a.csv", b"x,y\n1,2", db=object())
    assert (tmp_path / "uploads" / "3.csv").read_bytes() == b"x,y\n1,2"
    assert upload_store.load_upload(3, db=object()) == (b"x,y\n1,2", "3.csv")
    assert upload_store.load_upload(4) is None
