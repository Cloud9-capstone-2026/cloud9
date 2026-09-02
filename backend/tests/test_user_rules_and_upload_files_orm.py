"""
orm.UserRule / orm.UploadFile 실제 테이블 검증 (2026-08-27, 은우 요청 반영).

test_user_rules.py는 _fetch_user_rules를 monkeypatch로 대체해 로드 정책만
검증하고(DB 실물 불필요), test_upload_store.py는 orm.UploadFile이 없던
시점에 만들어져 필요시 가짜 클래스를 주입한다. 이 파일은 실제로 이
두 모델이 진짜 DB(SQLite 인메모리)에 저장·조회되는지, 그리고
pipeline.user_rules.load_ruleset이 실제 UserRule 행을 정말로 읽어오는지를
확인한다.
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database import Base
import orm


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_user_rule_unique_constraint_per_user_and_rule(db):
    """(user_id, rule_id) 조합은 유일해야 함 — 동일 조합 재등록은 UPDATE로 처리해야지
    새 행 추가가 아니다(스펙 그대로)."""
    from sqlalchemy.exc import IntegrityError

    db.add(orm.User(id=1, name="테스터"))
    db.commit()
    db.add(orm.UserRule(user_id=1, rule_id="min_holding", param=3, enabled=True))
    db.commit()

    db.add(orm.UserRule(user_id=1, rule_id="min_holding", param=5, enabled=True))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_user_rule_param_nullable_for_paramless_rules(db):
    """same_day_roundtrip처럼 파라미터가 없는 규칙은 param=None이어도 저장돼야 함."""
    db.add(orm.User(id=2, name="테스터2"))
    db.commit()
    db.add(orm.UserRule(user_id=2, rule_id="same_day_roundtrip", param=None, enabled=True))
    db.commit()

    saved = db.query(orm.UserRule).filter(orm.UserRule.user_id == 2).one()
    assert saved.param is None
    assert saved.enabled is True


def test_load_ruleset_reads_real_user_rule_rows(db):
    """pipeline.user_rules.load_ruleset이 실제 UserRule 테이블에서 값을 읽어오는지 e2e 확인."""
    from pipeline.user_rules import load_ruleset

    db.add(orm.User(id=3, name="테스터3"))
    db.commit()
    db.add_all([
        orm.UserRule(user_id=3, rule_id="min_holding", param=7, enabled=True),
        orm.UserRule(user_id=3, rule_id="daily_frequency", param=2, enabled=False),  # 꺼둠
    ])
    db.commit()

    ruleset = load_ruleset(db, 3)
    assert ruleset == [("min_holding", 7)]  # enabled=False인 daily_frequency는 제외


def test_upload_file_stores_and_retrieves_raw_bytes(db):
    """upload_files가 실제로 바이트를 저장·조회하고, size가 실제 길이와 일치하는지."""
    from pipeline import upload_store

    db.add(orm.CsvUpload(id=100, file_name="원본.csv", status="pending"))
    db.commit()

    raw = b"a,b,c\n1,2,3\n"
    upload_store.save_upload(100, raw, db)
    db.commit()

    saved = db.query(orm.UploadFile).filter(orm.UploadFile.upload_id == 100).one()
    assert bytes(saved.content) == raw
    assert saved.size == len(raw)

    loaded = upload_store.load_upload(100, db)
    assert loaded == (raw, "원본.csv")


def test_upload_file_upload_id_unique(db):
    """같은 upload_id로 두 번 저장 시도하면 unique 제약에 걸려야 함."""
    from sqlalchemy.exc import IntegrityError

    db.add(orm.CsvUpload(id=200, file_name="a.csv", status="pending"))
    db.commit()
    db.add(orm.UploadFile(upload_id=200, content=b"x", size=1))
    db.commit()

    db.add(orm.UploadFile(upload_id=200, content=b"y", size=1))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()