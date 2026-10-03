"""
/rules API + 규칙 변경 이력(rule_change_logs) 검증 (2026-10-03).

이력은 진단→규칙 추천→재업로드 효과 측정의 기준점("언제 켰는지")이라
다음을 지킨다:
- 실제 적용 상태가 바뀔 때만 1행 (같은 값 재저장은 기록 안 함)
- param을 비워 켜면 템플릿 추천값으로 기록 (판정에 쓰이는 값과 동일)
- 추천 카드에서 켠 경우 source="recommendation"으로 구분
- 본인 이력만 조회

DB만 sqlite 인메모리로 격리하고 인증은 실제 회원가입 토큰을 쓴다
(test_auth_and_scoping.py와 같은 방식).
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


@pytest.fixture()
def client():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    from database import Base
    import orm  # noqa: F401 — 테이블 정의 등록
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
    c = TestClient(app)
    yield c
    app.dependency_overrides.clear()


def _token(client, email="r@test.com") -> dict:
    r = client.post("/auth/signup", json={
        "email": email, "password": "password123", "name": "테스터",
        "agreed_terms": True,
    })
    assert r.status_code == 201
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _history(client, h, **params):
    r = client.get("/rules/history", headers=h, params=params)
    assert r.status_code == 200
    return r.json()


# ---------------------------------------------------------------------------
# 기존 동작 (이력 추가 전에도 테스트가 없던 부분)
# ---------------------------------------------------------------------------

def test_list_rules_returns_seven_templates_with_defaults(client):
    h = _token(client)
    r = client.get("/rules/", headers=h)
    assert r.status_code == 200
    rules = {x["rule_id"]: x for x in r.json()}
    assert len(rules) == 7
    assert rules["daily_frequency"]["enabled"] is True
    assert rules["min_holding"]["enabled"] is False
    assert rules["min_holding"]["param"] == 3


def test_unknown_rule_404(client):
    h = _token(client)
    assert client.put("/rules/nope", headers=h, json={"enabled": True}).status_code == 404


def test_amount_cap_without_param_rejected(client):
    """금액 한도류는 추천값이 없어 값 없이 켤 수 없다."""
    h = _token(client)
    r = client.put("/rules/daily_total_cap", headers=h, json={"enabled": True})
    assert r.status_code == 400
    assert _history(client, h) == []


# ---------------------------------------------------------------------------
# 변경 이력
# ---------------------------------------------------------------------------

def test_enable_rule_logs_once_with_default_param(client):
    h = _token(client)
    r = client.put("/rules/min_holding", headers=h, json={"enabled": True})
    assert r.status_code == 200

    hist = _history(client, h)
    assert len(hist) == 1
    row = hist[0]
    assert row["rule_id"] == "min_holding"
    assert row["action"] == "set"
    assert row["enabled"] is True
    assert row["param"] == 3          # 비워 켜면 추천값으로 기록
    assert row["source"] == "manual"


def test_recommendation_source_recorded(client):
    h = _token(client)
    r = client.put("/rules/daily_total_cap", headers=h,
                   json={"enabled": True, "param": 3_000_000,
                         "source": "recommendation"})
    assert r.status_code == 200
    row = _history(client, h)[0]
    assert row["source"] == "recommendation"
    assert row["param"] == 3_000_000


def test_invalid_source_rejected(client):
    h = _token(client)
    r = client.put("/rules/min_holding", headers=h,
                   json={"enabled": True, "source": "admin"})
    assert r.status_code == 422


def test_same_state_put_not_logged(client):
    """같은 값 재저장, 그리고 비워 둔 param = 추천값으로 명시한 param도 같은 상태."""
    h = _token(client)
    client.put("/rules/min_holding", headers=h, json={"enabled": True})
    client.put("/rules/min_holding", headers=h, json={"enabled": True})
    client.put("/rules/min_holding", headers=h, json={"enabled": True, "param": 3})
    assert len(_history(client, h)) == 1


def test_putting_default_state_not_logged(client):
    """기본으로 켜진 규칙을 기본값 그대로 저장하면 적용 상태가 그대로라 기록 없음."""
    h = _token(client)
    client.put("/rules/daily_frequency", headers=h, json={"enabled": True})
    assert _history(client, h) == []


def test_param_change_and_disable_each_logged_newest_first(client):
    h = _token(client)
    client.put("/rules/min_holding", headers=h, json={"enabled": True})
    client.put("/rules/min_holding", headers=h, json={"enabled": True, "param": 5})
    client.put("/rules/min_holding", headers=h, json={"enabled": False, "param": 5})

    hist = _history(client, h)
    assert [(x["enabled"], x["param"]) for x in hist] == [
        (False, 5), (True, 5), (True, 3)]


def test_reset_logs_back_to_template_default(client):
    h = _token(client)
    client.put("/rules/min_holding", headers=h, json={"enabled": True})
    r = client.delete("/rules/min_holding", headers=h)
    assert r.status_code == 200

    hist = _history(client, h)
    assert len(hist) == 2
    assert hist[0]["action"] == "reset"
    assert hist[0]["enabled"] is False   # min_holding 기본은 꺼짐


def test_reset_without_setting_not_logged(client):
    h = _token(client)
    assert client.delete("/rules/min_holding", headers=h).status_code == 200
    assert _history(client, h) == []


def test_history_filter_by_rule_and_limit(client):
    h = _token(client)
    client.put("/rules/min_holding", headers=h, json={"enabled": True})
    client.put("/rules/averaging_down", headers=h, json={"enabled": True})
    client.put("/rules/reentry_after_loss", headers=h, json={"enabled": True})

    only = _history(client, h, rule_id="averaging_down")
    assert [x["rule_id"] for x in only] == ["averaging_down"]
    assert len(_history(client, h, limit=2)) == 2
    assert client.get("/rules/history", headers=h,
                      params={"rule_id": "nope"}).status_code == 404


def test_history_only_own_rows(client):
    a = _token(client, "a@test.com")
    b = _token(client, "b@test.com")
    client.put("/rules/min_holding", headers=a, json={"enabled": True})
    assert _history(client, b) == []
    assert len(_history(client, a)) == 1


def test_history_requires_auth(client):
    assert client.get("/rules/history").status_code == 401