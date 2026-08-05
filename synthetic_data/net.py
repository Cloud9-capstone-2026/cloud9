"""
pykrx 네트워크 안전장치 — requests 세션 기본 timeout 패치 (단일 지점, idempotent).

pykrx가 requests에 timeout을 걸지 않아 KRX 무응답 시 무한 행(hang) 위험이 있다
(6-1 유니버스 샘플링에서 실측). pykrx는 session 주입을 지원하지 않으므로 호출
범위로 한정한 패치가 불가능하고, 전역 기본값 패치가 유일한 실효 수단이다.

- setdefault 방식: 명시적으로 timeout을 준 호출(예: layer3의 Release 다운로드
  timeout=300)에는 영향이 없다. timeout 미지정 호출에만 기본값이 붙는다.
- ensure_timeout_patch()는 몇 번을 불러도 1회만 적용된다 — 기존에 layer3·
  market_data·regenerate_universe 3곳이 각자 중복 패치하던 것을 이 헬퍼로 통합.
"""

import requests

DEFAULT_TIMEOUT = 15  # 초 — KRX 평시 응답의 수 배, 무한 행만 차단하는 보수값

_patched = False


def ensure_timeout_patch(timeout: int = DEFAULT_TIMEOUT) -> None:
    global _patched
    if _patched:
        return
    orig = requests.Session.request

    def _request_with_timeout(self, *args, **kwargs):
        kwargs.setdefault("timeout", timeout)
        return orig(self, *args, **kwargs)

    requests.Session.request = _request_with_timeout
    _patched = True
