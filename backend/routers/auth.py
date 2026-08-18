"""
POST /auth/signup  - 이메일+비밀번호+이름으로 가입. 가입 즉시 이메일 인증
                      메일을 발송한다(현재는 email_service가 로그 출력만 함
                      — 2026-08-18, 이메일 발송 수단 미정).
POST /auth/login    - OAuth2PasswordRequestForm 사용 (username 필드에 이메일을 넣음).
                      이렇게 하면 Swagger UI의 "Authorize" 버튼이 그대로 동작함.
                      [주의] email_verified 여부로 로그인을 막지 않는다 —
                      발송 수단이 아직 없어 막으면 아무도 가입을 완료 못 함.
                      발송 수단 확정 후 이 게이트를 켤지는 별도 논의 필요.
POST /auth/verify-email         - 인증 링크의 토큰으로 email_verified=True 처리.
POST /auth/verify-email/resend  - 인증 메일 재발송(미인증 상태일 때만, 존재 여부는 비노출).
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

[레이트리밋 — 2026-08-17 최초 추가, 2026-08-18 신규 엔드포인트분 추가]
login: 5/minute, signup: 3/minute — 브루트포스/스팸 방지.
verify-email/resend: 3/minute — 이메일 스팸 발송 방지.
social/{provider}: 10/minute — 로그인류라 login과 비슷한 수준이되, provider
검증 자체가 외부 API 호출(카카오/네이버)이라 너무 빡빡하면 정상 사용자도
막힐 수 있어 login보다 약간 여유를 둠.
slowapi 데코레이터가 동작하려면 엔드포인트 함수가 정확히 `request: Request`
파라미터를 받아야 함(내부적으로 이 파라미터에서 클라이언트 IP를 읽음).
"""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from auth import (create_access_token, create_email_verification_token,
                  decode_email_verification_token, get_password_hash,
                  verify_password)
from database import get_db
from email_service import send_verification_email
from orm import User
from rate_limit import limiter
from social_auth import VERIFIERS

router = APIRouter()


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    name: str = Field(min_length=1, max_length=50)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class VerifyEmailRequest(BaseModel):
    token: str


class ResendVerificationRequest(BaseModel):
    email: EmailStr


class SocialLoginRequest(BaseModel):
    token: str


@router.post("/signup", status_code=status.HTTP_201_CREATED, response_model=TokenResponse)
@limiter.limit("3/minute")
def signup(request: Request, payload: SignupRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="이미 가입된 이메일입니다")

    user = User(
        email=payload.email,
        name=payload.name,
        hashed_password=get_password_hash(payload.password),
        provider="local",
        # email_verified는 컬럼 기본값(False) 그대로 — 아래에서 인증 메일 발송.
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    verify_token = create_email_verification_token(user.email)
    send_verification_email(user.email, verify_token)

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
def verify_email(payload: VerifyEmailRequest, db: Session = Depends(get_db)):
    email = decode_email_verification_token(payload.token)
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="해당 이메일의 계정을 찾을 수 없습니다")
    user.email_verified = True
    db.commit()
    return {"message": "이메일 인증이 완료되었습니다"}


@router.post("/verify-email/resend")
@limiter.limit("3/minute")
def resend_verification(request: Request, payload: ResendVerificationRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    # 계정 존재/인증 여부를 응답으로 노출하지 않음(이메일 나열 공격 방지) —
    # 있든 없든, 인증됐든 안 됐든 응답 메시지는 항상 동일.
    if user and not user.email_verified:
        verify_token = create_email_verification_token(user.email)
        send_verification_email(user.email, verify_token)
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