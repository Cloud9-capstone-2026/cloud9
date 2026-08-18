"""
소셜로그인 제공자별 토큰 검증.

[2026-08-18] 구글/네이버만 지원(카카오는 팀 결정으로 이번 범위에서 제외 —
이메일 동의항목을 쓰려면 카카오 "개인 개발자 비즈 앱" 전환 + 별도 심사가
필요해 일정상 보류. 나중에 추가할 때는 VERIFIERS에 항목만 더하면 됨).

아직 구글/네이버 어느 콘솔에도 앱 등록 전이라, 서버 쪽 비밀키(client
secret) 없이 동작하도록 설계했다:

- 구글: 클라이언트(React Native)가 구글 SDK로 받은 ID 토큰을 그대로 여기로
  넘긴다. google-auth 라이브러리가 구글 공개키로 서명·만료를 검증하므로
  우리 서버는 별도 시크릿이 필요 없다. GOOGLE_CLIENT_ID 환경변수가 설정되면
  audience(aud claim)까지 검증해 "우리 앱이 발급받은 토큰이 맞는지"까지
  확인한다 — 미설정 시 서명 검증만 하고 넘어가므로(약한 검증) 앱 등록 후
  반드시 채워야 한다.
- 네이버: 클라이언트가 이미 OAuth로 받아온 access_token을 그대로 네이버
  사용자정보 API에 실어 보내 신원을 확인한다. 이 방식도 서버 쪽 비밀키가
  필요 없다(단순 프록시 호출).

주의: 실제 앱 등록 전이라 네이버 응답 필드명은 공식 문서 기준으로 작성했지만
실제 토큰으로 검증된 적은 없음 — 앱 등록 후 반드시 실제 로그인 1회 이상
테스트 필요.
"""
import os
from typing import Optional, TypedDict

import httpx
from fastapi import HTTPException
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token

_HTTP_TIMEOUT = 5.0


class SocialUserInfo(TypedDict):
    provider_id: str
    email: Optional[str]
    name: Optional[str]
    email_verified: bool


def verify_google_id_token(token: str) -> SocialUserInfo:
    client_id = os.getenv("GOOGLE_CLIENT_ID")  # 미설정 시 audience 검증 생략
    try:
        payload = google_id_token.verify_oauth2_token(
            token, google_requests.Request(), audience=client_id,
        )
    except ValueError:
        raise HTTPException(status_code=401, detail="유효하지 않은 구글 토큰입니다")
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