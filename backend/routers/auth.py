"""
POST /auth/signup - 이메일+비밀번호+이름으로 가입
POST /auth/login   - OAuth2PasswordRequestForm 사용 (username 필드에 이메일을 넣음).
                      이렇게 하면 Swagger UI의 "Authorize" 버튼이 그대로 동작함.

[입력검증 보강 — 2026-08-17]
기존 SignupRequest는 email 형식만 검증하고 password/name은 아무 문자열이나
(빈 문자열 포함) 통과시켰다. 최소 길이 제약을 추가:
- password: 8~72자. 72자 상한은 bcrypt 자체 제약(72바이트 초과 시 내부 에러)에
  맞춘 것 — 프론트에서 방지 못한 값이 와도 서버가 먼저 400으로 막아줌.
- name: 1~50자. DB 컬럼(String(50))과 일치시켜, DB 제약 위반으로 인한
  500 대신 요청 단계에서 422로 명확히 거부되게 함.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from auth import create_access_token, get_password_hash, verify_password
from database import get_db
from orm import User

router = APIRouter()


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    name: str = Field(min_length=1, max_length=50)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/signup", status_code=status.HTTP_201_CREATED, response_model=TokenResponse)
def signup(payload: SignupRequest, db: Session = Depends(get_db)):
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
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
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