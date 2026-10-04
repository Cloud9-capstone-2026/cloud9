"""
회원 탈퇴 실삭제(account_deletion.delete_user_cascade) 검증 — FK 강제 상태에서.

SQLite는 기본적으로 FK를 검사하지 않아, 자식 테이블 삭제가 빠져도 로컬
테스트에선 통과하고 운영(Postgres)에서만 터진다. 그래서 PRAGMA foreign_keys=ON
으로 운영과 같은 조건을 만든다.

2026-10-03: 알림(notifications)·거래일지(trade_journals)가 생긴 뒤 삭제 목록에
추가되지 않아, 업로드 이력이 있는 계정은 삭제가 FK 위반으로 실패하던 문제의
회귀 테스트. 규칙 변경 이력(rule_change_logs)도 함께 검사한다.
"""
from datetime import date

import pytest
from sqlalchemy import create_engine, event
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

    @event.listens_for(engine, "connect")
    def _fk_on(dbapi_conn, _record):
        dbapi_conn.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


def _seed_full_user(db, user_id: int) -> None:
    """업로드→분석→알림→거래일지→규칙까지 쓴 계정 1개."""
    db.add(orm.User(id=user_id, name=f"u{user_id}"))
    db.flush()
    up = orm.CsvUpload(user_id=user_id, file_name="a.csv", status="done")
    db.add(up)
    db.flush()
    db.add(orm.UploadFile(upload_id=up.id, content=b"x", size=1))
    job = orm.AnalysisJob(upload_id=up.id, user_id=user_id, status="done")
    db.add(job)
    trade = orm.Trade(user_id=user_id, upload_id=up.id, 거래일자=date(2026, 9, 1),
                      종목명="테스트", 거래구분="매수", 거래수량=1, 거래단가=1000,
                      거래금액=1000, 수수료=0, 거래세=0, 정산금액=1000)
    db.add(trade)
    db.flush()
    db.add(orm.AnalysisResult(user_id=user_id, upload_id=up.id, job_id=job.id,
                              trade_id=trade.id, detail={}))
    db.add(orm.Notification(user_id=user_id, type="analysis", message="m",
                            job_id=job.id, upload_id=up.id))
    db.add(orm.TradeJournal(user_id=user_id, trade_id=trade.id, emotion="calm",
                            reason="r", review="v"))
    db.add(orm.UserRule(user_id=user_id, rule_id="min_holding", param=3, enabled=True))
    db.add(orm.RuleChangeLog(user_id=user_id, rule_id="min_holding", action="set",
                             enabled=True, param=3, source="recommendation"))
    db.commit()


def test_delete_user_cascade_with_fk_enforced(db):
    from account_deletion import delete_user_cascade

    _seed_full_user(db, 1)
    _seed_full_user(db, 2)

    delete_user_cascade(db, 1)
    db.commit()  # FK 위반이면 여기서 IntegrityError

    assert db.get(orm.User, 1) is None
    for model in (orm.CsvUpload, orm.AnalysisJob, orm.Trade, orm.AnalysisResult,
                  orm.Notification, orm.TradeJournal, orm.UserRule,
                  orm.RuleChangeLog, orm.SurveyResult):
        assert db.query(model).filter(model.user_id == 1).count() == 0, model.__name__

    # 다른 사용자 데이터는 그대로
    assert db.get(orm.User, 2) is not None
    assert db.query(orm.Notification).filter_by(user_id=2).count() == 1
    assert db.query(orm.RuleChangeLog).filter_by(user_id=2).count() == 1