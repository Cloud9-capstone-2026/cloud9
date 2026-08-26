"""
가격·지수 데이터 모듈 (KRX Open API 경유 — market/krx_api).

get_price_data(tickers): UNIVERSE 각 종목의 일별 OHLC를
    "종목코드/거래일자/시가/고가/저가/종가/거래량" 스키마로 통일해 반환.
get_index_data(): 코스피 지수의 일별 종가를 "거래일자/종가"로 반환.

두 함수 모두 config.LOTT_ESTIMATION_START ~ SIM_END_DATE 범위로 조회한다(시뮬 시작 전
LOTT 룩백 포함). 시뮬레이션이 실제로 도는 기간(>= SIM_START_DATE) 분리는 MarketModel이 담당.

설계 메모:
- 출처 전환(2026-08-26): pykrx(KRX 웹 스크래핑)는 약관·IP 차단으로 폐기 → KRX Open API.
  누구나 인증키만 있으면 같은 데이터를 다시 받을 수 있어 재현성이 복원된다.
- 수정주가: Open API는 미수정주가만 주므로 krx_api.adjust_prices가 상장주식수·시총
  연속성으로 액면분할·무상증자를 보정한다(유상증자 권리락 이론가 보정은 없음 — 알려진
  근사). 처분효과가 매수가 대비 현재가를 비교하므로 분할 보정이 핵심이며, 수정주가는
  시리즈를 상수배 스케일할 뿐이라 일별 수익률은 보존된다.
- 거래정지(거래량 0) 행 제거: 정지 종목이 계속 매수 후보로 남는 것 방지.
- 거래일자는 파이썬 date로 통일. model은 date로 비교하므로 안 맞추면 에러 없이 조용히
  빈 결과가 나온다(가장 위험한 유형의 버그).
- 조립 결과는 로컬 parquet로 캐싱. 캐시 키에 (기간, 종목셋, 스키마 버전)을 반영해
  하나라도 바뀌면 자동 무효화. 원천 일별 캐시(ml/cache/krx)는 krx_api가 관리.
"""

import hashlib
import os
from datetime import datetime

import pandas as pd

from . import config
from .market import krx_api

_PRICE_COLUMNS = ["종목코드", "거래일자", "시가", "고가", "저가", "종가", "거래량"]
_SCHEMA_VER = "v3"  # v3: KRX Open API + 자체 수정주가 (v2: pykrx adjusted)


def _cache_file(name: str) -> str:
    return os.path.join(config.PRICE_CACHE_DIR, name)


def _range():
    s = datetime.strptime(config.LOTT_ESTIMATION_START, "%Y%m%d").date()
    e = datetime.strptime(config.SIM_END_DATE, "%Y%m%d").date()
    return s, e


def _trading_days() -> list:
    s, e = _range()
    return krx_api.prefetch(s, e)  # 캐시 적중 시 네트워크 없음


def get_price_data(tickers: list[str]) -> pd.DataFrame:
    """UNIVERSE 각 종목의 일별 OHLC(수정주가)를 통일 스키마로 반환. (기간은 config에서 읽음)"""
    digest = hashlib.md5(",".join(sorted(tickers)).encode()).hexdigest()[:8]
    cache = _cache_file(
        f"ohlcv_{_SCHEMA_VER}_{config.LOTT_ESTIMATION_START}_{config.SIM_END_DATE}_{digest}.parquet"
    )
    if os.path.exists(cache):
        result = pd.read_parquet(cache)
    else:
        raw = krx_api.load_daily(_trading_days())
        raw = raw[raw["종목코드"].isin(set(tickers))]
        if raw.empty:
            raise RuntimeError("KRX Open API 캐시에 요청 종목이 없습니다 (종목코드/기간 확인).")
        adj = krx_api.adjust_prices(raw)
        adj = adj[adj["거래량"] > 0]  # 거래정지일 제거
        result = adj[_PRICE_COLUMNS].sort_values(["종목코드", "거래일자"]).reset_index(drop=True)
        result["거래일자"] = pd.to_datetime(result["거래일자"])
        os.makedirs(config.PRICE_CACHE_DIR, exist_ok=True)
        result.to_parquet(cache, index=False)

    result = result.copy()
    result["거래일자"] = pd.to_datetime(result["거래일자"]).dt.date
    return result


def get_index_data() -> pd.DataFrame:
    """코스피 지수의 일별 종가를 "거래일자(date)/종가(float)"로 반환. 캐싱."""
    cache = _cache_file(
        f"index_{_SCHEMA_VER}_{config.KOSPI_INDEX_CODE}_{config.LOTT_ESTIMATION_START}_{config.SIM_END_DATE}.parquet"
    )
    if os.path.exists(cache):
        result = pd.read_parquet(cache)
    else:
        days = _trading_days()
        result = pd.DataFrame({"거래일자": pd.to_datetime(days),
                               "종가": [krx_api.index_close(d) for d in days]})
        os.makedirs(config.PRICE_CACHE_DIR, exist_ok=True)
        result.to_parquet(cache, index=False)

    result = result.copy()
    result["거래일자"] = pd.to_datetime(result["거래일자"]).dt.date
    return result
