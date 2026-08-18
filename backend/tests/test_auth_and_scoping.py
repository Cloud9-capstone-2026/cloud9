"""
인증·API 소유권 파트 최소 테스트.

기존 test_analysis_jobs.py는 get_current_user를 가짜 유저로 override해서
job 소유권 로직만 검증하고, "auth.py 자체는 별도 유닛테스트 영역"이라고
명시적으로 남겨둔 부분이 있었음 — 이 파일이 그 공백을 채운다.

이 파일은 get_current_user를 override하지 않는다. 즉 실제 회원가입 →
로그인(JWT 발급) → Authorization 헤더로 보호된 엔드포인트 호출까지
전체 인증 플로우를 실물로 태운다. get_db만 sqlite 인메모리로 override해
프로덕션 DB와 완전히 격리한다.

레이트리밋(slowapi) 주의사항:
limiter는 rate_limit.py의 모듈 전역 싱글턴이라 프로세스(=pytest 세션)
전체에서 상태가 누적된다. 이 파일에서 회원가입/로그인을 여러 번 호출하면
분당 제한(signup 3/min, login 5/min)에 금방 걸려 무관한 테스트가 429로
실패할 수 있다. 그래서 각 테스트 시작 전에 limiter.reset()으로 카운터를
비운다(autouse fixture).
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


@pytest.fixture()
def client(monkeypatch):
    """실제 인증 플로우가 살아있는 TestClient. DB만 인메모리로 격리."""
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
    limiter.reset()  # 이전 테스트에서 쌓인 호출 카운트 제거
    c = TestClient(app)
    yield c
    app.dependency_overrides.clear()


def _signup(client, email="a@test.com", password="password123", name="테스터"):
    return client.post("/auth/signup", json={
        "email": email, "password": password, "name": name,
    })


def _login(client, email="a@test.com", password="password123"):
    # OAuth2PasswordRequestForm은 form-data + username 필드에 이메일을 넣음
    # (routers/auth.py 주석 참고 — Swagger Authorize 버튼 호환 목적)
    return client.post("/auth/login", data={
        "username": email, "password": password,
    })


def _auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# 회원가입
# ---------------------------------------------------------------------------

def test_signup_success_returns_token(client):
    r = _signup(client)
    assert r.status_code == 201
    body = r.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]  # 비어있지 않음


def test_signup_duplicate_email_rejected(client):
    _signup(client, email="dup@test.com")
    r2 = _signup(client, email="dup@test.com")
    assert r2.status_code == 400


def test_signup_password_too_short_rejected(client):
    # SignupRequest.password는 Field(min_length=8) — Pydantic이 라우터
    # 진입 전에 422로 거부해야 함
    r = client.post("/auth/signup", json={
        "email": "short@test.com", "password": "1234567", "name": "테스터",
    })
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# 로그인
# ---------------------------------------------------------------------------

def test_login_success_returns_token(client):
    _signup(client, email="login@test.com")
    r = _login(client, email="login@test.com")
    assert r.status_code == 200
    assert r.json()["token_type"] == "bearer"


def test_login_wrong_password_rejected(client):
    _signup(client, email="wrongpw@test.com", password="correct123")
    r = _login(client, email="wrongpw@test.com", password="incorrect123")
    assert r.status_code == 401


def test_login_unknown_email_rejected(client):
    r = _login(client, email="ghost@test.com", password="whatever123")
    assert r.status_code == 401


# ---------------------------------------------------------------------------
# 보호된 엔드포인트 — 토큰 검증
# ---------------------------------------------------------------------------

def test_protected_endpoint_without_token_401(client):
    assert client.get("/trades").status_code == 401
    assert client.get("/analysis").status_code == 401


def test_protected_endpoint_invalid_token_401(client):
    r = client.get("/trades", headers=_auth_header("this-is-not-a-jwt"))
    assert r.status_code == 401


def test_protected_endpoint_valid_token_200(client):
    _signup(client, email="valid@test.com")
    token = _login(client, email="valid@test.com").json()["access_token"]
    r = client.get("/trades", headers=_auth_header(token))
    assert r.status_code == 200
    assert r.json() == []  # 아직 업로드한 거래 없음


# ---------------------------------------------------------------------------
# 본인 데이터 스코핑 — GET /trades, /trades/uploads, /analysis
# ---------------------------------------------------------------------------

def test_user_only_sees_own_trades_and_analysis(client):
    """유저 A의 데이터가 유저 B에게 노출되면 안 됨 (JWT 도입의 핵심 목적)."""
    from orm import Trade, AnalysisResult, User

    _signup(client, email="userA@test.com")
    _signup(client, email="userB@test.com")
    token_a = _login(client, email="userA@test.com").json()["access_token"]
    token_b = _login(client, email="userB@test.com").json()["access_token"]

    # DB에 두 유저 몫 데이터를 직접 심어둠 (업로드 파이프라인은 이 테스트의
    # 관심사가 아니므로 우회 — test_analysis_jobs.py가 그 경로는 이미 커버)
    from database import get_db
    from main import app
    override = app.dependency_overrides[get_db]
    db = next(override())

    user_a = db.query(User).filter(User.email == "userA@test.com").one()
    user_b = db.query(User).filter(User.email == "userB@test.com").one()

    import datetime
    db.add(Trade(
        user_id=user_a.id, 거래일자=datetime.date(2026, 1, 1), 종목명="A전자",
        거래구분="매수", 거래수량=1, 거래단가=1000, 거래금액=1000,
        수수료=0, 거래세=0, 정산금액=1000,
    ))
    db.add(Trade(
        user_id=user_b.id, 거래일자=datetime.date(2026, 1, 1), 종목명="B전자",
        거래구분="매수", 거래수량=1, 거래단가=2000, 거래금액=2000,
        수수료=0, 거래세=0, 정산금액=2000,
    ))
    db.add(AnalysisResult(user_id=user_a.id, final_score=0.1, is_anomaly=False))
    db.add(AnalysisResult(user_id=user_b.id, final_score=0.9, is_anomaly=True))
    db.commit()
    db.close()

    # 유저 A로 조회 — 본인 거래·분석결과만 보여야 함
    trades_a = client.get("/trades", headers=_auth_header(token_a)).json()
    assert len(trades_a) == 1
    assert trades_a[0]["종목명"] == "A전자"

    analysis_a = client.get("/analysis", headers=_auth_header(token_a)).json()
    assert len(analysis_a) == 1
    assert analysis_a[0]["is_anomaly"] is False

    # 유저 B로 조회 — 마찬가지로 본인 것만
    trades_b = client.get("/trades", headers=_auth_header(token_b)).json()
    assert len(trades_b) == 1
    assert trades_b[0]["종목명"] == "B전자"


def test_user_only_sees_own_uploads(client):
    from orm import CsvUpload, User

    _signup(client, email="uploadA@test.com")
    _signup(client, email="uploadB@test.com")
    token_a = _login(client, email="uploadA@test.com").json()["access_token"]

    from database import get_db
    from main import app
    override = app.dependency_overrides[get_db]
    db = next(override())
    user_a = db.query(User).filter(User.email == "uploadA@test.com").one()
    user_b = db.query(User).filter(User.email == "uploadB@test.com").one()
    db.add(CsvUpload(user_id=user_a.id, file_name="a.csv", status="done"))
    db.add(CsvUpload(user_id=user_b.id, file_name="b.csv", status="done"))
    db.commit()
    db.close()

    uploads_a = client.get("/trades/uploads", headers=_auth_header(token_a)).json()
    assert len(uploads_a) == 1
    assert uploads_a[0]["file_name"] == "a.csv"


# ---------------------------------------------------------------------------
# 헬스체크 / 루트
# ---------------------------------------------------------------------------

def test_root_endpoint(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "message" in r.json()


def test_health_endpoint_reports_ok(client):
    # 주의: main.health()는 Depends(get_db)가 아니라 database.SessionLocal을
    # 직접 사용하므로 이 테스트의 sqlite override와는 무관하게 실제
    # DATABASE_URL(미설정 시 로컬 sqlite:///./local.db) 기준으로 동작함.
    # 그래도 로컬/CI 둘 다 fallback sqlite가 항상 접속 가능하므로 200을
    # 기대해도 안전함 — 다만 DI를 우회한다는 설계는 인지해둘 것.
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"