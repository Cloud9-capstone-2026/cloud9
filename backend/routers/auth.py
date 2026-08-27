"""
POST /auth/signup  - 이메일+비밀번호+이름+이용약관동의로 가입. 가입 즉시 이메일
                      인증 메일을 발송한다. agreed_terms가 false/누락이면 400.
                      (2026-08-26, 도경과 협의 후 필드 추가)
POST /auth/login    - OAuth2PasswordRequestForm 사용 (username 필드에 이메일을 넣음).
                      이렇게 하면 Swagger UI의 "Authorize" 버튼이 그대로 동작함.
                      [주의] email_verified 여부로 로그인을 막지 않는다 —
                      발송 수단이 아직 없어 막으면 아무도 가입을 완료 못 함.
                      발송 수단 확정 후 이 게이트를 켤지는 별도 논의 필요.
POST /auth/verify-email         - 이메일+6자리 코드로 email_verified=True 처리.
                      (2026-08-24, 딥링크 방식에서 전환 — 도경과 협의 완료)
POST /auth/verify-email/resend  - 인증 메일 재발송(미인증 상태일 때만, 존재 여부는 비노출).
                      재발송 시 새 코드가 기존 코드를 덮어써 자동 무효화됨.
POST /auth/social/{provider}    - 구글/네이버 소셜로그인 (카카오는 이메일
                      동의항목에 별도 비즈앱 심사가 필요해 이번 범위에서
                      제외 — 2026-08-18 팀 결정).
                      provider는 google | naver. body의 token은
                      구글은 ID 토큰, 네이버는 access_token(클라이언트가
                      각 사 SDK로 이미 발급받은 값을 그대로 전달).
                      기존 회원(provider+provider_id 일치)이면 로그인,
                      신규면 계정 생성. 단, 같은 이메일이 이미 다른 방식
                      (로컬 또는 다른 provider)으로 가입돼 있으면 409로 거부
                      — 계정당 로그인수단 1개 고정 원칙(옵션A, 2026-08-18
                      팀 결정) 때문에 자동 연동은 하지 않음.

[2026-08-27 추가 — 계정 관리 API]
POST /auth/password-reset/request  - 비밀번호를 잊었을 때. 이메일만 받고,
                      계정이 있고 provider='local'이면 6자리 코드 발송.
                      계정 존재 여부는 응답으로 노출 안 함(resend-verification
                      과 동일 원칙).
POST /auth/password-reset/confirm  - 이메일+코드+새 비밀번호로 재설정.
                      코드는 이메일 인증과 같은 방식(HMAC 해시, 만료시간)
                      이지만 컬럼은 분리(auth.py 주석 참고).
GET  /auth/me                      - 본인 프로필 조회.
PATCH /auth/me                     - 본인 이름 변경.
PUT  /auth/me/password              - 로그인 상태에서 비밀번호 변경
                      (현재 비밀번호 확인 필요 — 재설정과 다른 플로우).
                      provider != 'local'인 계정(소셜로그인)은 애초에
                      비밀번호가 없으므로 400.

[레이트리밋 — 2026-08-17 최초 추가, 2026-08-18/27 신규 엔드포인트분 추가]
login: 5/minute, signup: 3/minute — 브루트포스/스팸 방지.
verify-email/resend: 3/minute — 이메일 스팸 발송 방지.
verify-email: 5/minute — 6자리 코드 브루트포스 방지(경우의 수 100만개뿐이라
필수. IP당 제한이라 완벽하진 않지만 1차 방어선).
social/{provider}: 10/minute — 로그인류라 login과 비슷한 수준이되, provider
검증 자체가 외부 API 호출(카카오/네이버)이라 너무 빡빡하면 정상 사용자도
막힐 수 있어 login보다 약간 여유를 둠.
password-reset/request: 3/minute — verify-email/resend와 동일 이유(이메일 스팸 방지).
password-reset/confirm: 5/minute — verify-email과 동일 이유(코드 브루트포스 방지).
me/password: 5/minute — current_password 브루트포스 시도 방지.
slowapi 데코레이터가 동작하려면 엔드포인트 함수가 정확히 `request: Request`
파라미터를 받아야 함(내부적으로 이 파라미터에서 클라이언트 IP를 읽음).
"""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from sqlalchemy.orm import Session

from datetime import datetime, timedelta, timezone

from auth import (EMAIL_VERIFY_CODE_EXPIRE_MINUTES,
                  PASSWORD_RESET_CODE_EXPIRE_MINUTES, create_access_token,
                  generate_verification_code, get_current_user,
                  get_password_hash, hash_verification_code, verify_password,
                  verify_verification_code)
from database import get_db
from email_service import send_password_reset_email, send_verification_email
from orm import User
from rate_limit import limiter
from social_auth import VERIFIERS

router = APIRouter()


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    name: str = Field(min_length=1, max_length=50)
    # 이용약관/개인정보처리방침 동의 (2026-08-26 추가). 반드시 true여야 가입
    # 가능 — false를 명시적으로 보내는 것과 필드를 아예 안 보내는 것 둘 다
    # 막아야 하므로 Optional로 두지 않고 필수 필드로 강제한다.
    agreed_terms: bool


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class VerifyEmailRequest(BaseModel):
    email: EmailStr
    code: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")


class ResendVerificationRequest(BaseModel):
    email: EmailStr


class SocialLoginRequest(BaseModel):
    token: str


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirmRequest(BaseModel):
    email: EmailStr
    code: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")
    new_password: str = Field(min_length=8, max_length=72)


class UpdateProfileRequest(BaseModel):
    name: str = Field(min_length=1, max_length=50)


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=72)


class UserProfileResponse(BaseModel):
    id: int
    email: str | None
    name: str
    provider: str | None
    email_verified: bool
    agreed_terms: bool
    created_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


@router.post("/signup", status_code=status.HTTP_201_CREATED, response_model=TokenResponse)
@limiter.limit("3/minute")
def signup(request: Request, payload: SignupRequest, db: Session = Depends(get_db)):
    if not payload.agreed_terms:
        raise HTTPException(status_code=400, detail="이용약관 및 개인정보처리방침에 동의해야 가입할 수 있습니다")

    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="이미 가입된 이메일입니다")

    user = User(
        email=payload.email,
        name=payload.name,
        hashed_password=get_password_hash(payload.password),
        provider="local",
        agreed_terms=True,
        agreed_terms_at=datetime.now(timezone.utc),
        # email_verified는 컬럼 기본값(False) 그대로 — 아래에서 인증 메일 발송.
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    code = generate_verification_code()
    user.verification_code_hash = hash_verification_code(code)
    user.verification_code_expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=EMAIL_VERIFY_CODE_EXPIRE_MINUTES
    )
    db.commit()
    send_verification_email(user.email, code)

    token = create_access_token(user.id)
    return TokenResponse(access_token=token)


@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")
def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # OAuth2PasswordRequestForm.username 필드에 이메일을 넣어서 보낸다 (Swagger UI 폼 필드명 고정이라 어쩔 수 없음)
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="이메일 또는 비밀번호가 올바르지 않습니다",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(user.id)
    return TokenResponse(access_token=token)


@router.post("/verify-email")
@limiter.limit("5/minute")
def verify_email(request: Request, payload: VerifyEmailRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not user.verification_code_hash:
        raise HTTPException(status_code=400, detail="유효하지 않거나 만료된 인증 코드입니다")

    expires_at = user.verification_code_expires_at
    if expires_at and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if not expires_at or expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="유효하지 않거나 만료된 인증 코드입니다")

    if not verify_verification_code(payload.code, user.verification_code_hash):
        raise HTTPException(status_code=400, detail="인증 코드가 올바르지 않습니다")

    user.email_verified = True
    # 재사용(replay) 방지 — 검증에 성공한 코드는 즉시 무효화.
    user.verification_code_hash = None
    user.verification_code_expires_at = None
    db.commit()
    return {"message": "이메일 인증이 완료되었습니다"}


@router.post("/verify-email/resend")
@limiter.limit("3/minute")
def resend_verification(request: Request, payload: ResendVerificationRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    # 계정 존재/인증 여부를 응답으로 노출하지 않음(이메일 나열 공격 방지) —
    # 있든 없든, 인증됐든 안 됐든 응답 메시지는 항상 동일.
    if user and not user.email_verified:
        code = generate_verification_code()
        user.verification_code_hash = hash_verification_code(code)
        user.verification_code_expires_at = datetime.now(timezone.utc) + timedelta(
            minutes=EMAIL_VERIFY_CODE_EXPIRE_MINUTES
        )
        db.commit()
        send_verification_email(user.email, code)
    return {"message": "해당 이메일이 가입되어 있고 미인증 상태라면 인증 메일을 보냈습니다"}


@router.post("/social/{provider}", response_model=TokenResponse)
@limiter.limit("10/minute")
def social_login(request: Request, provider: str, payload: SocialLoginRequest, db: Session = Depends(get_db)):
    verifier = VERIFIERS.get(provider)
    if verifier is None:
        raise HTTPException(status_code=400, detail=f"지원하지 않는 provider입니다: {provider}")

    info = verifier(payload.token)

    user = (
        db.query(User)
        .filter(User.provider == provider, User.provider_id == info["provider_id"])
        .first()
    )

    if user is None:
        if info["email"]:
            existing = db.query(User).filter(User.email == info["email"]).first()
            if existing:
                # 계정당 로그인수단 1개 고정(옵션A) — 자동 연동하지 않고 명확히 거부
                raise HTTPException(
                    status_code=409,
                    detail=f"이미 다른 방식으로 가입된 이메일입니다 (가입수단: {existing.provider or 'local'})",
                )

        user = User(
            name=info["name"] or f"{provider}사용자",
            email=info["email"],
            provider=provider,
            provider_id=info["provider_id"],
            # 소셜 제공자가 이미 이메일 소유권을 검증했다고 간주.
            email_verified=info["email_verified"],
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    token = create_access_token(user.id)
    return TokenResponse(access_token=token)


@router.post("/password-reset/request")
@limiter.limit("3/minute")
def request_password_reset(request: Request, payload: PasswordResetRequest, db: Session = Depends(get_db)):
    """비밀번호를 잊은 사용자용. 계정 존재/provider 여부를 응답으로 노출하지
    않는다(resend-verification과 동일 원칙) — 계정이 없거나, 있어도
    provider != 'local'(소셜로그인이라 비밀번호 자체가 없음)이면 그냥
    아무 일도 안 하고 동일한 메시지를 반환한다."""
    user = db.query(User).filter(User.email == payload.email).first()
    if user and user.provider == "local":
        code = generate_verification_code()
        user.password_reset_code_hash = hash_verification_code(code)
        user.password_reset_code_expires_at = datetime.now(timezone.utc) + timedelta(
            minutes=PASSWORD_RESET_CODE_EXPIRE_MINUTES
        )
        db.commit()
        send_password_reset_email(user.email, code)
    return {"message": "해당 이메일의 로컬 계정이 있다면 재설정 코드를 보냈습니다"}


@router.post("/password-reset/confirm")
@limiter.limit("5/minute")
def confirm_password_reset(request: Request, payload: PasswordResetConfirmRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not user.password_reset_code_hash:
        raise HTTPException(status_code=400, detail="유효하지 않거나 만료된 재설정 코드입니다")

    expires_at = user.password_reset_code_expires_at
    if expires_at and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if not expires_at or expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="유효하지 않거나 만료된 재설정 코드입니다")

    if not verify_verification_code(payload.code, user.password_reset_code_hash):
        raise HTTPException(status_code=400, detail="재설정 코드가 올바르지 않습니다")

    user.hashed_password = get_password_hash(payload.new_password)
    # 재사용(replay) 방지 — 검증에 성공한 코드는 즉시 무효화.
    user.password_reset_code_hash = None
    user.password_reset_code_expires_at = None
    db.commit()
    return {"message": "비밀번호가 재설정되었습니다"}


@router.get("/me", response_model=UserProfileResponse)
def get_my_profile(current_user: User = Depends(get_current_user)):
    return current_user


@router.patch("/me", response_model=UserProfileResponse)
def update_my_profile(
    payload: UpdateProfileRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    current_user.name = payload.name
    db.commit()
    db.refresh(current_user)
    return current_user


@router.put("/me/password")
@limiter.limit("5/minute")
def change_my_password(
    request: Request,
    payload: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """로그인 상태에서 비밀번호 변경 — 비밀번호 재설정(모를 때)과 달리
    현재 비밀번호를 알아야 한다. 소셜로그인 계정은 애초에 비밀번호가
    없으므로 400."""
    if current_user.provider != "local":
        raise HTTPException(
            status_code=400,
            detail=f"{current_user.provider} 계정은 비밀번호를 변경할 수 없습니다",
        )
    if not verify_password(payload.current_password, current_user.hashed_password):
        raise HTTPException(status_code=401, detail="현재 비밀번호가 올바르지 않습니다")

    current_user.hashed_password = get_password_hash(payload.new_password)
    db.commit()
    return {"message": "비밀번호가 변경되었습니다"}