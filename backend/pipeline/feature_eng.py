"""
feature_eng.py
종목명 → 종목코드 매핑 (layer3의 시세 조회용).

LLM 컬럼 매핑·표준화(구 map_columns_with_llm·standardize)와 시장 데이터 병합
(구 attach_market_data)은 예전 동기 파이프라인의 잔재로 미호출이라 제거 —
컬럼 매핑은 pipeline.csv_mapper가 Trade 스키마 대상으로 새로 구현(2026-08-15).
"""

import logging
import sys
from datetime import date, timedelta
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

logger = logging.getLogger(__name__)

# 종목명 → 코드 역매핑 캐시. 프로세스당 1회 전체 맵을 만들어 두면 이후 조회는 O(1).
_NAME_TO_CODE: dict | None = None


def _build_name_map() -> dict:
    """KRX Open API 종목기본정보(코스피+코스닥, 최근 거래일)로 종목명→코드 맵.

    2026-08-26 pykrx(KRX 웹 스크래핑, 약관·IP 차단) → Open API 전환. 서버에도
    KRX_API_KEY가 필요하다. 실패하면 빈 맵(전 종목 미매핑 → layer3가 NM_ 코드로
    강등, 시장 컨텍스트만 결측 처리) — 기존 실패 정책 그대로."""
    from synthetic_data.market import krx_api

    d = date.today()
    for _ in range(10):  # 최근 거래일 탐색 (휴장일은 빈 응답)
        info = krx_api.base_info(d)
        if len(info):
            break
        d -= timedelta(days=1)
    mapping: dict = {}
    for code, nm in zip(info["종목코드"], info["종목명"]):
        mapping.setdefault(nm, code)
    return mapping


def get_ticker_code(name: str) -> str | None:
    global _NAME_TO_CODE
    try:
        if _NAME_TO_CODE is None:
            _NAME_TO_CODE = _build_name_map()
        return _NAME_TO_CODE.get(name)
    except Exception:
        return None