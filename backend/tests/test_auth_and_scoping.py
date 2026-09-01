"""
B파트(인증·API 소유권) 최소 테스트.

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


def _signup(client, email="a@test.com", password="password123", name="테스터", agreed_terms=True):
    return client.post("/auth/signup", json={
        "email": email, "password": password, "name": name, "agreed_terms": agreed_terms,
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


def test_signup_sets_local_provider_and_unverified_email(client):
    """소셜로그인 스키마(2026-08-18, 옵션A) 도입 후 회원가입 계약 고정.

    이메일/비번 가입은 provider='local'로 명시 기록되고, email_verified는
    아직 이메일 인증 발송 플로우가 없으므로 기본값 False로 남아야 한다.
    """
    from orm import User

    _signup(client, email="localprovider@test.com")

    from database import get_db
    from main import app
    db = next(app.dependency_overrides[get_db]())
    user = db.query(User).filter(User.email == "localprovider@test.com").one()
    assert user.provider == "local"
    assert user.provider_id is None
    assert user.email_verified is False
    db.close()


def test_signup_password_too_short_rejected(client):
    # SignupRequest.password는 Field(min_length=8) — Pydantic이 라우터
    # 진입 전에 422로 거부해야 함
    r = client.post("/auth/signup", json={
        "email": "short@test.com", "password": "1234567", "name": "테스터", "agreed_terms": True,
    })
    assert r.status_code == 422


def test_signup_requires_agreed_terms(client):
    """agreed_terms가 false면 400 — 이용약관 동의 없이는 가입 불가."""
    r = _signup(client, email="noagree@test.com", agreed_terms=False)
    assert r.status_code == 400


def test_signup_missing_agreed_terms_field_rejected(client):
    """agreed_terms 필드 자체를 안 보내면 Pydantic이 422로 거부해야 함."""
    r = client.post("/auth/signup", json={
        "email": "missingfield@test.com", "password": "password123", "name": "테스터",
    })
    assert r.status_code == 422


def test_signup_records_agreed_terms_timestamp(client):
    from orm import User

    _signup(client, email="agreetime@test.com")

    from database import get_db
    from main import app
    db = next(app.dependency_overrides[get_db]())
    user = db.query(User).filter(User.email == "agreetime@test.com").one()
    assert user.agreed_terms is True
    assert user.agreed_terms_at is not None
    db.close()


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
    db.add(AnalysisResult(user_id=user_a.id, deep_score=0.1, is_anomaly=False))
    db.add(AnalysisResult(user_id=user_b.id, deep_score=0.9, is_anomaly=True))
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
# 페이지네이션 (2026-08-27 추가)
# ---------------------------------------------------------------------------

def test_trades_pagination_limit_and_offset(client):
    from orm import Trade, User
    import datetime

    _signup(client, email="pagetrades@test.com")
    token = _login(client, email="pagetrades@test.com").json()["access_token"]

    from database import get_db
    from main import app
    db = next(app.dependency_overrides[get_db]())
    user = db.query(User).filter(User.email == "pagetrades@test.com").one()
    for i in range(5):
        db.add(Trade(
            user_id=user.id, 거래일자=datetime.date(2026, 1, i + 1), 종목명=f"종목{i}",
            거래구분="매수", 거래수량=1, 거래단가=1000, 거래금액=1000,
            수수료=0, 거래세=0, 정산금액=1000,
        ))
    db.commit()
    db.close()

    page1 = client.get("/trades?limit=2&offset=0", headers=_auth_header(token)).json()
    assert len(page1) == 2
    # 거래일자 내림차순 — 가장 최근(1/5) 거래가 먼저 나와야 함
    assert page1[0]["종목명"] == "종목4"
    assert page1[1]["종목명"] == "종목3"

    page2 = client.get("/trades?limit=2&offset=2", headers=_auth_header(token)).json()
    assert len(page2) == 2
    assert page2[0]["종목명"] == "종목2"


def test_trades_pagination_default_limit_applied(client):
    r = _signup(client, email="defaultlimit@test.com")
    token = r.json()["access_token"]
    r = client.get("/trades", headers=_auth_header(token))
    assert r.status_code == 200  # limit 파라미터 없이도 정상 동작(기본값 50)


def test_trades_pagination_rejects_limit_over_max(client):
    token = _signup(client, email="overmaxlimit@test.com").json()["access_token"]
    r = client.get("/trades?limit=201", headers=_auth_header(token))
    assert r.status_code == 422


def test_uploads_pagination_limit(client):
    from orm import CsvUpload, User

    _signup(client, email="pageuploads@test.com")
    token = _login(client, email="pageuploads@test.com").json()["access_token"]

    from database import get_db
    from main import app
    db = next(app.dependency_overrides[get_db]())
    user = db.query(User).filter(User.email == "pageuploads@test.com").one()
    for i in range(3):
        db.add(CsvUpload(user_id=user.id, file_name=f"{i}.csv", status="done"))
    db.commit()
    db.close()

    r = client.get("/trades/uploads?limit=1", headers=_auth_header(token))
    assert len(r.json()) == 1


def test_analysis_pagination_newest_first(client):
    from orm import AnalysisResult, User

    _signup(client, email="pageanalysis@test.com")
    token = _login(client, email="pageanalysis@test.com").json()["access_token"]

    from database import get_db
    from main import app
    db = next(app.dependency_overrides[get_db]())
    user = db.query(User).filter(User.email == "pageanalysis@test.com").one()
    ids = []
    for i in range(3):
        row = AnalysisResult(user_id=user.id, deep_score=float(i), is_anomaly=False)
        db.add(row)
        db.flush()
        ids.append(row.id)
    db.commit()
    db.close()

    r = client.get("/analysis?limit=2", headers=_auth_header(token))
    body = r.json()
    assert len(body) == 2
    assert [row["id"] for row in body] == list(reversed(ids))[:2]  # 최신순


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


# ---------------------------------------------------------------------------
# 이메일 인증 (2026-08-18)
# ---------------------------------------------------------------------------

def test_signup_sends_verification_email(client, monkeypatch):
    """가입 시 send_verification_email이 정확히 1회, 본인 이메일로 호출되는지."""
    sent = []
    import routers.auth as auth_router_mod
    monkeypatch.setattr(
        auth_router_mod, "send_verification_email",
        lambda to_email, code: sent.append((to_email, code)),
    )
    _signup(client, email="verifyme@test.com")
    assert len(sent) == 1
    assert sent[0][0] == "verifyme@test.com"
    assert len(sent[0][1]) == 6 and sent[0][1].isdigit()


def test_verify_email_with_valid_code_marks_verified(client, monkeypatch):
    sent = []
    import routers.auth as auth_router_mod
    monkeypatch.setattr(
        auth_router_mod, "send_verification_email",
        lambda to_email, code: sent.append((to_email, code)),
    )
    _signup(client, email="tobeverified@test.com")
    code = sent[0][1]

    r = client.post("/auth/verify-email", json={"email": "tobeverified@test.com", "code": code})
    assert r.status_code == 200

    from database import get_db
    from main import app
    from orm import User
    db = next(app.dependency_overrides[get_db]())
    user = db.query(User).filter(User.email == "tobeverified@test.com").one()
    assert user.email_verified is True
    assert user.verification_code_hash is None  # 검증 성공 후 재사용 방지로 무효화됨
    db.close()


def test_verify_email_rejects_wrong_code(client, monkeypatch):
    monkeypatch.setattr(
        "routers.auth.send_verification_email", lambda to_email, code: None,
    )
    _signup(client, email="wrongcode@test.com")
    r = client.post("/auth/verify-email", json={"email": "wrongcode@test.com", "code": "000000"})
    assert r.status_code == 400


def test_verify_email_code_is_single_use(client, monkeypatch):
    """한 번 성공한 코드는 재사용할 수 없어야 함(replay 방지)."""
    sent = []
    monkeypatch.setattr(
        "routers.auth.send_verification_email",
        lambda to_email, code: sent.append((to_email, code)),
    )
    _signup(client, email="singleuse@test.com")
    code = sent[0][1]

    r1 = client.post("/auth/verify-email", json={"email": "singleuse@test.com", "code": code})
    assert r1.status_code == 200

    r2 = client.post("/auth/verify-email", json={"email": "singleuse@test.com", "code": code})
    assert r2.status_code == 400


def test_verify_email_rejects_unknown_email(client):
    r = client.post("/auth/verify-email", json={"email": "ghost@test.com", "code": "123456"})
    assert r.status_code == 400


def test_resend_verification_does_not_leak_account_existence(client, monkeypatch):
    """존재하지 않는 이메일이든 이미 인증된 이메일이든 응답 메시지가 동일해야 함."""
    sent = []
    import routers.auth as auth_router_mod
    monkeypatch.setattr(
        auth_router_mod, "send_verification_email",
        lambda to_email, code: sent.append(to_email),
    )
    _signup(client, email="resendme@test.com")
    sent.clear()  # 가입 시 자동 발송된 것은 이 검증 대상이 아니므로 리셋

    r_unknown = client.post("/auth/verify-email/resend", json={"email": "ghost2@test.com"})
    assert r_unknown.status_code == 200
    assert sent == []  # 존재하지 않으니 발송 안 됨

    r_known = client.post("/auth/verify-email/resend", json={"email": "resendme@test.com"})
    assert sent == ["resendme@test.com"]  # 존재+미인증이니 실제로는 발송됨
    assert r_known.json() == r_unknown.json()  # 그런데도 응답 형태로는 존재 여부 유추 불가


def test_resend_invalidates_previous_code(client, monkeypatch):
    """재발송하면 이전 코드는 더 이상 통하지 않아야 함."""
    sent = []
    monkeypatch.setattr(
        "routers.auth.send_verification_email",
        lambda to_email, code: sent.append(code),
    )
    _signup(client, email="resendinvalidate@test.com")
    old_code = sent[0]

    client.post("/auth/verify-email/resend", json={"email": "resendinvalidate@test.com"})
    new_code = sent[1]
    assert old_code != new_code

    r_old = client.post("/auth/verify-email", json={"email": "resendinvalidate@test.com", "code": old_code})
    assert r_old.status_code == 400

    r_new = client.post("/auth/verify-email", json={"email": "resendinvalidate@test.com", "code": new_code})
    assert r_new.status_code == 200


# ---------------------------------------------------------------------------
# 소셜로그인 (2026-08-18) — 아직 provider 앱 등록 전이라 verifier를 mock으로 대체
# ---------------------------------------------------------------------------

def test_social_login_creates_new_user(client, monkeypatch):
    from social_auth import VERIFIERS

    monkeypatch.setitem(VERIFIERS, "google", lambda token: {
        "provider_id": "google-uid-123",
        "email": "social1@test.com",
        "name": "소셜유저",
        "email_verified": True,
    })

    r = client.post("/auth/social/google", json={"token": "fake-id-token"})
    assert r.status_code == 200
    assert r.json()["token_type"] == "bearer"

    from orm import User
    from database import get_db
    from main import app
    db = next(app.dependency_overrides[get_db]())
    user = db.query(User).filter(User.provider_id == "google-uid-123").one()
    assert user.provider == "google"
    assert user.email == "social1@test.com"
    assert user.email_verified is True
    db.close()


def test_social_login_existing_user_logs_in_without_duplicate(client, monkeypatch):
    from social_auth import VERIFIERS

    fake_verify = lambda token: {
        "provider_id": "naver-uid-999", "email": "social2@test.com",
        "name": "네이버유저", "email_verified": True,
    }
    monkeypatch.setitem(VERIFIERS, "naver", fake_verify)

    r1 = client.post("/auth/social/naver", json={"token": "t1"})
    r2 = client.post("/auth/social/naver", json={"token": "t2"})  # 매번 새 토큰이어도 동일 유저
    assert r1.status_code == 200 and r2.status_code == 200

    from orm import User
    from database import get_db
    from main import app
    db = next(app.dependency_overrides[get_db]())
    count = db.query(User).filter(User.provider_id == "naver-uid-999").count()
    assert count == 1  # 중복 계정 생성 안 됨
    db.close()


def test_social_login_rejects_email_already_used_by_local_account(client, monkeypatch):
    """계정당 로그인수단 1개 고정(옵션A) — 이미 로컬로 가입된 이메일과
    같은 이메일로 소셜로그인 시도하면 자동 연동하지 않고 409로 거부."""
    from social_auth import VERIFIERS

    _signup(client, email="alreadylocal@test.com")

    monkeypatch.setitem(VERIFIERS, "naver", lambda token: {
        "provider_id": "naver-uid-1", "email": "alreadylocal@test.com",
        "name": "네이버유저", "email_verified": True,
    })
    r = client.post("/auth/social/naver", json={"token": "t"})
    assert r.status_code == 409


def test_social_login_unknown_provider_rejected(client):
    r = client.post("/auth/social/facebook", json={"token": "t"})
    assert r.status_code == 400


# ---------------------------------------------------------------------------
# 비밀번호 재설정 (2026-08-27)
# ---------------------------------------------------------------------------

def test_password_reset_request_does_not_leak_account_existence(client, monkeypatch):
    sent = []
    import routers.auth as auth_router_mod
    monkeypatch.setattr(
        auth_router_mod, "send_password_reset_email",
        lambda to_email, code: sent.append(to_email),
    )
    _signup(client, email="resetme@test.com")
    sent.clear()

    r_unknown = client.post("/auth/password-reset/request", json={"email": "ghost3@test.com"})
    assert r_unknown.status_code == 200
    assert sent == []

    r_known = client.post("/auth/password-reset/request", json={"email": "resetme@test.com"})
    assert sent == ["resetme@test.com"]
    assert r_known.json() == r_unknown.json()


def test_password_reset_request_skipped_for_social_accounts(client, monkeypatch):
    """소셜로그인 계정은 비밀번호 자체가 없으므로 코드 발송 안 함(응답은 동일)."""
    from social_auth import VERIFIERS

    sent = []
    import routers.auth as auth_router_mod
    monkeypatch.setattr(
        auth_router_mod, "send_password_reset_email",
        lambda to_email, code: sent.append(to_email),
    )
    monkeypatch.setitem(VERIFIERS, "google", lambda token: {
        "provider_id": "g-1", "email": "socialreset@test.com",
        "name": "소셜유저", "email_verified": True,
    })
    client.post("/auth/social/google", json={"token": "t"})

    r = client.post("/auth/password-reset/request", json={"email": "socialreset@test.com"})
    assert r.status_code == 200
    assert sent == []


def test_password_reset_confirm_changes_password_and_allows_login(client, monkeypatch):
    sent = []
    import routers.auth as auth_router_mod
    monkeypatch.setattr(
        auth_router_mod, "send_password_reset_email",
        lambda to_email, code: sent.append((to_email, code)),
    )
    _signup(client, email="resetflow@test.com", password="oldpassword123")
    client.post("/auth/password-reset/request", json={"email": "resetflow@test.com"})
    code = sent[0][1]

    r = client.post("/auth/password-reset/confirm", json={
        "email": "resetflow@test.com", "code": code, "new_password": "newpassword456",
    })
    assert r.status_code == 200

    old_login = _login(client, email="resetflow@test.com", password="oldpassword123")
    assert old_login.status_code == 401
    new_login = _login(client, email="resetflow@test.com", password="newpassword456")
    assert new_login.status_code == 200


def test_password_reset_confirm_rejects_wrong_code(client, monkeypatch):
    monkeypatch.setattr("routers.auth.send_password_reset_email", lambda to_email, code: None)
    _signup(client, email="resetwrong@test.com")
    client.post("/auth/password-reset/request", json={"email": "resetwrong@test.com"})

    r = client.post("/auth/password-reset/confirm", json={
        "email": "resetwrong@test.com", "code": "000000", "new_password": "newpassword456",
    })
    assert r.status_code == 400


def test_password_reset_confirm_code_is_single_use(client, monkeypatch):
    sent = []
    monkeypatch.setattr(
        "routers.auth.send_password_reset_email",
        lambda to_email, code: sent.append(code),
    )
    _signup(client, email="resetsingleuse@test.com")
    client.post("/auth/password-reset/request", json={"email": "resetsingleuse@test.com"})
    code = sent[0]

    r1 = client.post("/auth/password-reset/confirm", json={
        "email": "resetsingleuse@test.com", "code": code, "new_password": "newpassword456",
    })
    assert r1.status_code == 200

    r2 = client.post("/auth/password-reset/confirm", json={
        "email": "resetsingleuse@test.com", "code": code, "new_password": "anotherpassword789",
    })
    assert r2.status_code == 400


def test_password_reset_confirm_without_request_rejected(client):
    _signup(client, email="noresetrequest@test.com")
    r = client.post("/auth/password-reset/confirm", json={
        "email": "noresetrequest@test.com", "code": "123456", "new_password": "newpassword456",
    })
    assert r.status_code == 400


# ---------------------------------------------------------------------------
# 프로필 조회/수정 (2026-08-27)
# ---------------------------------------------------------------------------

def test_get_my_profile_requires_auth(client):
    r = client.get("/auth/me")
    assert r.status_code == 401


def test_get_my_profile_returns_own_info(client):
    token = _signup(client, email="profiletest@test.com", name="원래이름").json()["access_token"]
    r = client.get("/auth/me", headers=_auth_header(token))
    assert r.status_code == 200
    body = r.json()
    assert body["email"] == "profiletest@test.com"
    assert body["name"] == "원래이름"
    assert body["provider"] == "local"


def test_update_my_profile_changes_name(client):
    token = _signup(client, email="renametest@test.com", name="옛날이름").json()["access_token"]
    r = client.patch("/auth/me", json={"name": "새이름"}, headers=_auth_header(token))
    assert r.status_code == 200
    assert r.json()["name"] == "새이름"

    check = client.get("/auth/me", headers=_auth_header(token))
    assert check.json()["name"] == "새이름"


def test_update_my_profile_requires_auth(client):
    r = client.patch("/auth/me", json={"name": "몰래"})
    assert r.status_code == 401


def test_update_my_profile_rejects_empty_name(client):
    token = _signup(client, email="emptynametest@test.com").json()["access_token"]
    r = client.patch("/auth/me", json={"name": ""}, headers=_auth_header(token))
    assert r.status_code == 422


def test_change_password_requires_auth(client):
    r = client.put("/auth/me/password", json={
        "current_password": "a", "new_password": "newpassword123",
    })
    assert r.status_code == 401


def test_change_password_success_and_can_login_with_new(client):
    token = _signup(client, email="changepw@test.com", password="oldpassword123").json()["access_token"]
    r = client.put("/auth/me/password", json={
        "current_password": "oldpassword123", "new_password": "newpassword456",
    }, headers=_auth_header(token))
    assert r.status_code == 200

    old_login = _login(client, email="changepw@test.com", password="oldpassword123")
    assert old_login.status_code == 401
    new_login = _login(client, email="changepw@test.com", password="newpassword456")
    assert new_login.status_code == 200


def test_change_password_rejects_wrong_current_password(client):
    token = _signup(client, email="wrongcurrentpw@test.com", password="oldpassword123").json()["access_token"]
    r = client.put("/auth/me/password", json={
        "current_password": "totallywrong", "new_password": "newpassword456",
    }, headers=_auth_header(token))
    assert r.status_code == 401


def test_change_password_rejected_for_social_account(client, monkeypatch):
    from social_auth import VERIFIERS

    monkeypatch.setitem(VERIFIERS, "naver", lambda token: {
        "provider_id": "n-pw-1", "email": "socialpw@test.com",
        "name": "네이버유저", "email_verified": True,
    })
    r = client.post("/auth/social/naver", json={"token": "t"})
    token = r.json()["access_token"]

    r2 = client.put("/auth/me/password", json={
        "current_password": "whatever", "new_password": "newpassword456",
    }, headers=_auth_header(token))
    assert r2.status_code == 400