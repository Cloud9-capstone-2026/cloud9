"""
POST /auth/signup - 이메일+비밀번호+이름으로 가입
POST /auth/login   - OAuth2PasswordRequestForm 사용 (username 필드에 이메일을 넣음).
                      이렇게 하면 Swagger UI의 "Authorize" 버튼이 그대로 동작함.

[레이트리밋 추가 — 2026-08-17]
login: 5/minute — 브루트포스 비밀번호 시도 방지가 목적이라 빡빡하게.
signup: 3/minute — 스팸 가입 방지. 로그인보다 자주 호출될 이유가 없음.
slowapi 데코레이터가 동작하려면 엔드포인트 함수가 정확히 `request: Request`
파라미터를 받아야 함(내부적으로 이 파라미터에서 클라이언트 IP를 읽음).
"""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from auth import create_access_token, get_password_hash, verify_password
from database import get_db
from orm import User
from rate_limit import limiter

router = APIRouter()


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    name: str = Field(min_length=1, max_length=50)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


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
    )
    db.add(user)
    db.commit()
    db.refresh(user)

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