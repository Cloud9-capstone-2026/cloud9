"""
JWT 인증 핵심 로직.

- 비밀번호 해싱: passlib(bcrypt)
- 토큰 발급/검증: python-jose (HS256)
- get_current_user: 라우터에서 Depends(get_current_user)로 사용.
  기존 각 라우터가 user_id를 쿼리 파라미터/요청 바디로 직접 받던 방식을
  대체한다 — user_id는 이제 클라이언트가 보내는 값이 아니라 토큰에서
  서버가 추출하는 값이다 (클라이언트가 남의 user_id를 넣어도 무시됨).

환경변수 (.env에 추가 필요):
  JWT_SECRET_KEY   - 32바이트 이상 랜덤 문자열. 예: python -c "import secrets; print(secrets.token_hex(32))"
  JWT_EXPIRE_MINUTES - 선택. 기본 10080(7일). 앱 특성상 자동 로그아웃 안 되게 넉넉히 설정.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # repo 루트 (config/ 접근용)

from config.settings import get

import hmac
import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from database import get_db
from orm import User

SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not SECRET_KEY:
    # 개발 편의를 위해 fallback을 두지 않고 바로 죽인다 — 이 값이 비어있으면
    # 배포 시 매 재시작마다 발급된 토큰이 전부 무효화되는 사고로 이어지기 쉽다.
    raise RuntimeError(
        "JWT_SECRET_KEY 환경변수가 설정되지 않았습니다. "
        ".env에 JWT_SECRET_KEY=<랜덤문자열>을 추가하세요."
    )
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(get("auth.jwt_expire_minutes", 10080, env_override="JWT_EXPIRE_MINUTES"))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# tokenUrl은 Swagger UI의 "Authorize" 버튼이 로그인 요청을 보낼 엔드포인트.
# routers/auth.py의 실제 prefix("/auth")와 일치해야 함.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    # "sub"(subject)에 user_id를 문자열로 저장하는 건 JWT 표준 관례.
    to_encode = {"sub": str(user_id), "exp": expire}
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


# --- 이메일 인증 코드 (2026-08-24, 딥링크 방식에서 전환) --------------------
# 배경: 커스텀 스키마는 Gmail 인앱브라우저에서 링크가 안 눌리는 경우가 있고,
# 유니버설 링크는 도메인+apple-app-site-association/assetlinks.json 설정이
# 필요한 데다 Expo Go 개발 중엔 딥링크 자체가 테스트 불가 → 6자리 숫자 코드로
# 대체(도메인 의존성 없음, 프론트는 입력 화면만 있으면 됨).
#
# 코드 원문은 DB에 저장하지 않고 HMAC-SHA256 해시만 저장한다. 코드가 6자리라
# bcrypt처럼 느린 해시를 쓸 필요는 없고(경우의 수가 100만 개뿐이라 느린 해시가
# 안전성을 크게 높이지 않음), 대신 브루트포스는 verify-email 엔드포인트의
# 레이트리밋으로 막는다.
EMAIL_VERIFY_CODE_EXPIRE_MINUTES = int(
    get("auth.email_verify_code_expire_minutes", 10, env_override="EMAIL_VERIFY_CODE_EXPIRE_MINUTES")
)


def generate_verification_code() -> str:
    """000000~999999 사이 6자리 코드를 문자열로 반환(앞자리 0 유지).

    random 모듈이 아닌 secrets를 쓰는 이유: random은 예측 가능한 PRNG라
    보안 목적(인증 코드 생성)에는 부적합.
    """
    return f"{secrets.randbelow(1_000_000):06d}"


def hash_verification_code(code: str) -> str:
    return hmac.new(SECRET_KEY.encode(), code.encode(), hashlib.sha256).hexdigest()


def verify_verification_code(code: str, code_hash: str) -> bool:
    """타이밍 공격 방지를 위해 hmac.compare_digest로 비교."""
    return hmac.compare_digest(hash_verification_code(code), code_hash)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="인증 정보가 유효하지 않습니다",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id_raw = payload.get("sub")
        if user_id_raw is None:
            raise credentials_exception
        user_id = int(user_id_raw)
    except (JWTError, ValueError):
        raise credentials_exception

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception
    return user