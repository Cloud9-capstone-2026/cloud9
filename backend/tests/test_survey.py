"""
POST /survey/submit 테스트.

test_auth_and_scoping.py와 동일 패턴(get_db만 sqlite 인메모리로 override,
get_current_user는 실제 JWT 플로우 그대로) — 인증 우회 없이 실제 가입→로그인
→ Authorization 헤더로 제출까지 태운다.

question_id는 Notion 확정 스펙 기준 문자열 형식(ds_1~hs_5)이다.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

ALL_QUESTION_IDS = [
    f"{prefix}_{n}" for prefix in ("ds", "oc", "lp", "hs") for n in range(1, 6)
]


@pytest.fixture()
def client(monkeypatch):
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
    c = TestClient(app)
    yield c
    app.dependency_overrides.clear()


def _signup_and_login(client, email="survey@test.com"):
    client.post("/auth/signup", json={
        "email": email, "password": "password123", "name": "테스터", "agreed_terms": True,
    })
    r = client.post("/auth/login", data={"username": email, "password": "password123"})
    return r.json()["access_token"]


def _auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _make_answers(overrides: dict | None = None, default: int = 3) -> list[dict]:
    overrides = overrides or {}
    return [
        {"question_id": qid, "value": overrides.get(qid, default)}
        for qid in ALL_QUESTION_IDS
    ]


# ---------------------------------------------------------------------------
# 기본 동작
# ---------------------------------------------------------------------------

def test_submit_requires_auth(client):
    r = client.post("/survey/submit", json={"answers": _make_answers()})
    assert r.status_code == 401


def test_submit_all_neutral_answers(client):
    """전부 3점(중립)이면 정규화 점수가 정확히 50이어야 함 (raw=15, (15-5)/20*100=50)."""
    token = _signup_and_login(client)
    r = client.post("/survey/submit", json={"answers": _make_answers(default=3)},
                     headers=_auth_header(token))
    assert r.status_code == 200
    body = r.json()
    for axis in ("disposition_strength", "overconfidence", "lottery_preference", "herd_sensitivity"):
        assert body["scores"][axis]["raw"] == 15
        assert body["scores"][axis]["normalized"] == 50.0
        assert body["scores"][axis]["level"] == "high"  # 50 이상은 high


def test_submit_all_max_answers_gives_high_type_code(client):
    token = _signup_and_login(client)
    r = client.post("/survey/submit", json={"answers": _make_answers(default=5)},
                     headers=_auth_header(token))
    assert r.status_code == 200
    assert r.json()["type_code"] == "HHHH"


def test_reverse_scoring_applied_correctly(client):
    """Notion 문서 2절 계산 예시 재현 (overconfidence 축):
    oc_1=4, oc_2=5, oc_3=3, oc_4=4, oc_5(reverse)=2 → raw=4+5+3+4+(6-2)=20,
    normalized=(20-5)/20*100=75, level=high."""
    token = _signup_and_login(client)
    answers = _make_answers(overrides={
        "oc_1": 4, "oc_2": 5, "oc_3": 3, "oc_4": 4, "oc_5": 2,
    })
    r = client.post("/survey/submit", json={"answers": answers}, headers=_auth_header(token))
    assert r.status_code == 200
    body = r.json()
    assert body["scores"]["overconfidence"]["raw"] == 20
    assert body["scores"]["overconfidence"]["normalized"] == 75.0
    assert body["scores"]["overconfidence"]["level"] == "high"


def test_type_code_order_matches_axis_order(client):
    token = _signup_and_login(client)
    overrides = {qid: 5 for qid in ALL_QUESTION_IDS if qid.startswith("ds_")}
    overrides.update({qid: 1 for qid in ALL_QUESTION_IDS if not qid.startswith("ds_")})
    r = client.post("/survey/submit", json={"answers": _make_answers(overrides=overrides)},
                     headers=_auth_header(token))
    body = r.json()
    assert body["type_code"][0] == "H"  # disposition_strength
    assert body["type_code"][1] == "L"  # overconfidence
    assert body["type_code"][2] == "L"  # lottery_preference
    assert body["type_code"][3] == "L"  # herd_sensitivity


def test_submit_persists_user_id_and_raw_answers(client):
    from database import get_db
    from main import app
    from orm import SurveyResult, User

    token = _signup_and_login(client, email="persisttest@test.com")
    r = client.post("/survey/submit", json={"answers": _make_answers()}, headers=_auth_header(token))
    result_id = r.json()["result_id"]

    db = next(app.dependency_overrides[get_db]())
    user = db.query(User).filter(User.email == "persisttest@test.com").one()
    saved = db.query(SurveyResult).filter(SurveyResult.id == result_id).one()
    assert saved.user_id == user.id
    assert len(saved.answers) == 20
    db.close()


# ---------------------------------------------------------------------------
# 입력 검증
# ---------------------------------------------------------------------------

def test_submit_rejects_wrong_answer_count(client):
    token = _signup_and_login(client)
    answers = _make_answers()[:19]
    r = client.post("/survey/submit", json={"answers": answers}, headers=_auth_header(token))
    assert r.status_code == 422


def test_submit_rejects_duplicate_question_id(client):
    token = _signup_and_login(client)
    answers = _make_answers()
    answers[-1]["question_id"] = "ds_1"  # hs_5 대신 ds_1 중복
    r = client.post("/survey/submit", json={"answers": answers}, headers=_auth_header(token))
    assert r.status_code == 422


def test_submit_rejects_value_out_of_range(client):
    token = _signup_and_login(client)
    answers = _make_answers(overrides={"ds_1": 6})
    r = client.post("/survey/submit", json={"answers": answers}, headers=_auth_header(token))
    assert r.status_code == 422


def test_submit_rejects_unknown_question_id_format(client):
    """ds_6, xx_1처럼 정의되지 않은 id는 패턴 검증에서 걸려야 함."""
    token = _signup_and_login(client)
    answers = _make_answers()
    answers[0]["question_id"] = "ds_6"
    r = client.post("/survey/submit", json={"answers": answers}, headers=_auth_header(token))
    assert r.status_code == 422


def test_submit_ignores_user_id_in_body(client):
    """Notion 문서 예시는 user_id를 바디에 포함하지만, 실제로는 무시되고
    토큰의 사용자로 저장돼야 한다(클라이언트가 남의 user_id를 넣어도 무효)."""
    from database import get_db
    from main import app
    from orm import SurveyResult, User

    token = _signup_and_login(client, email="realuser@test.com")
    payload = {"user_id": 999999, "answers": _make_answers()}
    r = client.post("/survey/submit", json=payload, headers=_auth_header(token))
    assert r.status_code == 200

    db = next(app.dependency_overrides[get_db]())
    real_user = db.query(User).filter(User.email == "realuser@test.com").one()
    saved = db.query(SurveyResult).filter(SurveyResult.id == r.json()["result_id"]).one()
    assert saved.user_id == real_user.id
    assert saved.user_id != 999999
    db.close()


# ---------------------------------------------------------------------------
# GET /survey/latest, /survey/history (2026-08-27 추가)
# ---------------------------------------------------------------------------

def test_get_latest_requires_auth(client):
    r = client.get("/survey/latest")
    assert r.status_code == 401


def test_get_latest_404_when_no_submissions(client):
    token = _signup_and_login(client, email="nosurvey@test.com")
    r = client.get("/survey/latest", headers=_auth_header(token))
    assert r.status_code == 404


def test_get_latest_returns_most_recent_submission(client):
    token = _signup_and_login(client, email="latesttest@test.com")
    r1 = client.post("/survey/submit", json={"answers": _make_answers(default=3)},
                      headers=_auth_header(token))
    r2 = client.post("/survey/submit", json={"answers": _make_answers(default=5)},
                      headers=_auth_header(token))

    latest = client.get("/survey/latest", headers=_auth_header(token))
    assert latest.status_code == 200
    assert latest.json()["result_id"] == r2.json()["result_id"]
    assert latest.json()["result_id"] != r1.json()["result_id"]


def test_get_latest_only_returns_own_result(client):
    """유저 A의 최신 결과가 유저 B에게 노출되면 안 됨."""
    token_a = _signup_and_login(client, email="scopeA@test.com")
    client.post("/survey/submit", json={"answers": _make_answers()}, headers=_auth_header(token_a))

    token_b = _signup_and_login(client, email="scopeB@test.com")
    r = client.get("/survey/latest", headers=_auth_header(token_b))
    assert r.status_code == 404  # B는 제출 이력이 없으므로


def test_get_history_requires_auth(client):
    r = client.get("/survey/history")
    assert r.status_code == 401


def test_get_history_returns_newest_first(client):
    token = _signup_and_login(client, email="historytest@test.com")
    ids = []
    for v in (3, 4, 5):
        r = client.post("/survey/submit", json={"answers": _make_answers(default=v)},
                         headers=_auth_header(token))
        ids.append(r.json()["result_id"])

    history = client.get("/survey/history", headers=_auth_header(token))
    assert history.status_code == 200
    body = history.json()
    assert len(body) == 3
    assert [r["result_id"] for r in body] == list(reversed(ids))  # 최신순


def test_get_history_respects_limit(client):
    token = _signup_and_login(client, email="limittest@test.com")
    for v in (1, 2, 3, 4, 5):
        client.post("/survey/submit", json={"answers": _make_answers(default=(v % 5) + 1)},
                    headers=_auth_header(token))

    r = client.get("/survey/history?limit=2", headers=_auth_header(token))
    assert len(r.json()) == 2


def test_get_history_rejects_limit_over_max(client):
    token = _signup_and_login(client, email="limitmaxtest@test.com")
    r = client.get("/survey/history?limit=101", headers=_auth_header(token))
    assert r.status_code == 422