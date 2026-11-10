import logging
import os
from typing import Optional, TypedDict

import httpx
from fastapi import HTTPException
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token

_HTTP_TIMEOUT = 5.0

logger = logging.getLogger("canary.social_auth")


class SocialUserInfo(TypedDict):
    provider_id: str
    email: Optional[str]
    name: Optional[str]
    email_verified: bool


def verify_google_id_token(token: str) -> SocialUserInfo:
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    if not client_id:
        # aud 검증 없이 통과시키면 다른 앱용 토큰도 받아버린다 — 차라리 막는다.
        logger.error("GOOGLE_CLIENT_ID 미설정 — 구글 로그인 요청을 거부함 (.env 확인)")
        raise HTTPException(status_code=503, detail="구글 로그인을 일시적으로 사용할 수 없습니다")
    try:
        payload = google_id_token.verify_oauth2_token(
            token, google_requests.Request(), audience=client_id,
        )
    except ValueError:
        raise HTTPException(status_code=401, detail="유효하지 않은 구글 토큰입니다")
    if not payload.get("email_verified", False):
        raise HTTPException(status_code=401, detail="이메일 인증이 완료된 구글 계정만 사용할 수 있습니다")
    return {
        "provider_id": payload["sub"],
        "email": payload.get("email"),
        "name": payload.get("name"),
        "email_verified": bool(payload.get("email_verified", False)),
    }


def verify_naver_access_token(token: str) -> SocialUserInfo:
    try:
        resp = httpx.get(
            "https://openapi.naver.com/v1/nid/me",
            headers={"Authorization": f"Bearer {token}"},
            timeout=_HTTP_TIMEOUT,
        )
        resp.raise_for_status()
    except httpx.HTTPError:
        raise HTTPException(status_code=401, detail="유효하지 않은 네이버 토큰입니다")

    data = resp.json()
    if data.get("resultcode") != "00":
        raise HTTPException(status_code=401, detail="유효하지 않은 네이버 토큰입니다")

    info = data.get("response", {})
    return {
        "provider_id": str(info["id"]),
        "email": info.get("email"),
        "name": info.get("name") or info.get("nickname"),
        # 네이버 API는 별도 email_verified 플래그를 안 줌 — 이메일이 왔다면
        # 네이버 계정 자체에서 이미 검증된 값이라고 간주.
        "email_verified": bool(info.get("email")),
    }


VERIFIERS = {
    "google": verify_google_id_token,
    "naver": verify_naver_access_token,
}