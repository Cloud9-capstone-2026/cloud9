"""
config/settings.yaml 로더.

비밀값(DB 접속정보, API 키, JWT 시크릿)은 여전히 .env/환경변수로만 관리한다 —
settings.yaml은 git에 커밋되는 파일이라 비밀값을 넣으면 안 된다.
이 파일은 그 외의, 재배포 없이 조정하고 싶은 튜닝값(만료시간, 포트 등)을
코드 곳곳의 os.getenv 기본값 대신 한 곳에서 관리하기 위한 용도.

우선순위: 환경변수(env_override로 지정한 이름) > settings.yaml > default 인자
(운영에서 급하게 값을 바꿔야 할 때 .env만 건드리면 되도록 — 배포 파이프라인이
settings.yaml까지 매번 고쳐 커밋하게 만들지 않기 위함)

사용 예:
    from config.settings import get
    port = int(get("app.port", 8080))
    expire = int(get("auth.jwt_expire_minutes", 10080, env_override="JWT_EXPIRE_MINUTES"))
"""
import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

import yaml

_SETTINGS_PATH = Path(__file__).resolve().parent / "settings.yaml"


@lru_cache()
def _load() -> dict:
    """프로세스 생애주기 동안 1회만 읽음 — 파일이 없거나 비어있으면 빈 dict."""
    if not _SETTINGS_PATH.exists():
        return {}
    with open(_SETTINGS_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def get(key_path: str, default: Any = None, env_override: Optional[str] = None) -> Any:
    """
    key_path: "auth.jwt_expire_minutes" 같은 dot 표기로 settings.yaml 중첩 키 조회.
    env_override: 이 이름의 환경변수가 설정돼 있으면 그 값을 최우선으로 반환
                  (settings.yaml 값도, default도 무시).
    """
    if env_override and os.getenv(env_override) is not None:
        return os.getenv(env_override)

    node = _load()
    for part in key_path.split("."):
        if not isinstance(node, dict) or part not in node:
            return default
        node = node[part]
    return node if node is not None else default