"""
feature_eng.py
종목명 → 종목코드 매핑 (layer3의 시세 조회용).

LLM 컬럼 매핑·표준화(구 map_columns_with_llm·standardize)와 시장 데이터 병합
(구 attach_market_data)은 예전 동기 파이프라인의 잔재로 미호출이라 제거 —
컬럼 매핑은 pipeline.csv_mapper가 Trade 스키마 대상으로 새로 구현(2026-08-15).
"""

import logging

logging.getLogger("pykrx").setLevel(logging.ERROR)


# 종목명 → 코드 역매핑 캐시. 기존 구현은 이름 하나당 전 시장 티커를 순회해
# 다종목 CSV에서 업로드 응답이 분 단위로 늘어졌다. pykrx의 이름 조회는 첫 호출에서
# 전체 상장 목록을 받아 인프로세스 캐싱하므로(실측: 첫 5.6초, 이후 0초), 프로세스당
# 1회만 전체 맵을 만들어 두면 이후 조회는 O(1)이다.
_NAME_TO_CODE: dict | None = None


def _build_name_map() -> dict:
    # pykrx의 StockTicker 싱글턴이 상장 전 종목의 (티커→종목명) 테이블을 1회
    # fetch로 보유한다(get_market_ticker_name의 내부 소스). 이 테이블을 역매핑해
    # 이름→코드 dict를 만든다 — 날짜 기반 목록 API(get_market_ticker_list·
    # get_market_ohlcv_by_ticker)는 이 환경에서 로그인 요구로 실패함(실측).
    # 내부 API라 pykrx 버전 변경 시 깨질 수 있음 — 실패하면 빈 맵(전 종목 미매핑
    # → layer3가 NM_ 코드로 강등, 시장 컨텍스트만 결측 처리).
    from pykrx.website.krx.market.ticker import StockTicker
    df = StockTicker().listed  # index=티커, columns: 종목/ISIN/시장
    mapping: dict = {}
    for ticker, row in df.iterrows():
        nm = row["종목"]
        if isinstance(nm, str):
            mapping.setdefault(nm, ticker)
    return mapping


def get_ticker_code(name: str) -> str | None:
    global _NAME_TO_CODE
    try:
        if _NAME_TO_CODE is None:
            _NAME_TO_CODE = _build_name_map()
        return _NAME_TO_CODE.get(name)
    except Exception:
        return None