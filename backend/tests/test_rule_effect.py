"""
규칙 효과 측정(GET /rules/{id}/effect, pipeline/rule_effect.py) 검증 (2026-10-04).

지키는 것:
- 저장된 판정이 아니라 지금 기준 규칙으로 모든 업로드를 다시 판정한다
  (켜기 전 업로드도 위반이 잡혀야 전후 비교가 성립)
- 재판정은 실제 분석과 같은 문맥: 앞선 업로드 거래 + 이번 업로드 거래
- 켠 시점(adopted_at) = 현재 켜진 구간의 시작, 이력 없으면 null
- 분석 완료 업로드만, 본인 데이터만
"""
from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


@pytest.fixture()
def env():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    from database import Base
    import orm  # noqa: F401
    Base.metadata.create_all(bind=engine)

    from main import app
    from database import get_db
    from rate_limit import limiter

    def override_get_db():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    limiter.reset()
    yield TestClient(app), TestSession
    app.dependency_overrides.clear()


def _signup(client, email="e@test.com"):
    r = client.post("/auth/signup", json={
        "email": email, "password": "password123", "name": "테스터",
        "agreed_terms": True,
    })
    assert r.status_code == 201
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _user_id(Session, email):
    import orm
    db = Session()
    try:
        return db.query(orm.User).filter_by(email=email).one().id
    finally:
        db.close()


def _add_upload(Session, user_id, trades, started_at, status="done"):
    """trades: [(날짜, 종목명, 거래구분, 수량, 단가)]"""
    import orm
    db = Session()
    try:
        up = orm.CsvUpload(user_id=user_id, file_name="f.csv", status="done")
        db.add(up)
        db.flush()
        db.add(orm.AnalysisJob(upload_id=up.id, user_id=user_id, status=status,
                               started_at=started_at))
        for d, name, side, qty, price in trades:
            amt = qty * price
            db.add(orm.Trade(user_id=user_id, upload_id=up.id, 거래일자=d,
                             종목명=name, 거래구분=side, 거래수량=qty,
                             거래단가=price, 거래금액=amt, 수수료=0, 거래세=0,
                             정산금액=amt))
        db.commit()
        return up.id
    finally:
        db.close()


PAST = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=1)
FUTURE = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=1)
D = date(2026, 9, 1)


# ---------------------------------------------------------------------------
# 켠 시점 계산 (순수 함수)
# ---------------------------------------------------------------------------

def _log(enabled, at, source="manual"):
    return SimpleNamespace(enabled=enabled, created_at=at, source=source)


def test_adoption_point_cases():
    from pipeline.rule_effect import adoption_point
    t1, t2, t3 = datetime(2026, 10, 1), datetime(2026, 10, 2), datetime(2026, 10, 3)

    assert adoption_point([]) == (None, None)
    assert adoption_point([_log(True, t1, "recommendation")]) == (t1, "recommendation")
    # 켜진 채 파라미터만 바꾼 건 새 시작이 아님
    assert adoption_point([_log(True, t1), _log(True, t2)]) == (t1, "manual")
    # 껐다 다시 켜면 다시 켠 시점
    assert adoption_point([_log(True, t1), _log(False, t2),
                           _log(True, t3, "recommendation")]) == (t3, "recommendation")
    # 지금 꺼져 있으면 없음
    assert adoption_point([_log(True, t1), _log(False, t2)]) == (None, None)


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------

def test_before_and_after_both_rejudged_with_current_rule(env):
    """핵심: 켜기 전 업로드도 지금 규칙으로 위반이 잡힌다(저장값이면 0)."""
    client, Session = env
    h = _signup(client)
    uid = _user_id(Session, "e@test.com")

    # 켜기 전: 매수 4건 중 2건이 100만 원 초과
    _add_upload(Session, uid, [
        (D, "A", "매수", 10, 200_000), (D, "B", "매수", 10, 150_000),
        (D, "C", "매수", 1, 50_000), (D, "D", "매수", 1, 60_000),
    ], started_at=PAST)

    r = client.put("/rules/single_buy_cap", headers=h,
                   json={"enabled": True, "param": 1_000_000,
                         "source": "recommendation"})
    assert r.status_code == 200

    # 켠 뒤: 매수 4건 중 1건 초과
    _add_upload(Session, uid, [
        (D + timedelta(days=7), "A", "매수", 10, 200_000),
        (D + timedelta(days=7), "B", "매수", 1, 50_000),
        (D + timedelta(days=8), "C", "매수", 1, 50_000),
        (D + timedelta(days=8), "D", "매수", 1, 60_000),
    ], started_at=FUTURE)

    r = client.get("/rules/single_buy_cap/effect", headers=h)
    assert r.status_code == 200
    body = r.json()
    assert body["param"] == 1_000_000
    assert body["adopted_source"] == "recommendation"
    assert body["adopted_at"] is not None
    assert [(u["violations"], u["after_adoption"]) for u in body["uploads"]] == [
        (2, False), (1, True)]
    assert body["summary"]["before"]["violation_rate"] == 0.5
    assert body["summary"]["after"]["violation_rate"] == 0.25
    assert body["summary"]["comparable"] is True


def test_rejudge_uses_previous_uploads_as_context(env):
    """실제 분석과 같은 문맥 — 같은 날 같은 종목이 두 업로드에 나뉘어 있으면
    뒤 업로드 판정에서는 앞 업로드 거래까지 세고, 앞 업로드 판정에서는 안 센다."""
    client, Session = env
    h = _signup(client)
    uid = _user_id(Session, "e@test.com")
    _add_upload(Session, uid, [(D, "A", "매수", 1, 1000), (D, "A", "매도", 1, 1000)],
                started_at=PAST)
    _add_upload(Session, uid, [(D, "A", "매수", 1, 1000), (D, "A", "매도", 1, 1000)],
                started_at=PAST)

    body = client.get("/rules/daily_frequency/effect", headers=h).json()
    assert body["param"] == 4
    assert [u["violations"] for u in body["uploads"]] == [0, 2]


def test_no_log_means_no_adoption_point(env):
    client, Session = env
    h = _signup(client)
    uid = _user_id(Session, "e@test.com")
    _add_upload(Session, uid, [(D, "A", "매수", 1, 1000)], started_at=PAST)

    body = client.get("/rules/min_holding/effect", headers=h).json()
    assert body["param"] == 3                 # 미설정 → 템플릿 추천값
    assert body["adopted_at"] is None
    assert body["currently_enabled"] is False
    assert all(u["after_adoption"] is False for u in body["uploads"])
    assert body["summary"]["comparable"] is False


def test_amount_cap_needs_param_or_preview(env):
    client, Session = env
    h = _signup(client)
    uid = _user_id(Session, "e@test.com")
    _add_upload(Session, uid, [(D, "A", "매수", 10, 200_000)], started_at=PAST)

    assert client.get("/rules/daily_total_cap/effect", headers=h).status_code == 400
    r = client.get("/rules/daily_total_cap/effect", headers=h,
                   params={"param": 1_000_000})
    assert r.status_code == 200
    assert r.json()["uploads"][0]["violations"] == 1


def test_failed_uploads_and_other_users_excluded(env):
    client, Session = env
    h = _signup(client, "a@test.com")
    _signup(client, "b@test.com")
    a, b = _user_id(Session, "a@test.com"), _user_id(Session, "b@test.com")
    _add_upload(Session, a, [(D, "A", "매수", 1, 1000)], started_at=PAST)
    _add_upload(Session, a, [(D, "A", "매수", 1, 1000)], started_at=PAST,
                status="failed")
    _add_upload(Session, b, [(D, "A", "매수", 1, 1000)], started_at=PAST)

    body = client.get("/rules/min_holding/effect", headers=h).json()
    assert len(body["uploads"]) == 1


def test_no_uploads_returns_empty(env):
    client, _ = env
    h = _signup(client)
    body = client.get("/rules/min_holding/effect", headers=h).json()
    assert body["uploads"] == []
    assert body["summary"]["before"]["violation_rate"] is None


def test_effect_unknown_rule_and_auth(env):
    client, _ = env
    h = _signup(client)
    assert client.get("/rules/nope/effect", headers=h).status_code == 404
    assert client.get("/rules/min_holding/effect").status_code == 401