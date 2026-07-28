"""
가격·지수 데이터 모듈.

get_price_data(tickers): UNIVERSE 각 종목의 일별 OHLC를
    "종목코드/거래일자/시가/고가/저가/종가" 스키마로 통일해 반환.
get_index_data(): 코스피 지수(config.KOSPI_INDEX_CODE)의 일별 종가를 "거래일자/종가"로 반환.

두 함수 모두 config.LOTT_ESTIMATION_START ~ SIM_END_DATE 범위로 조회한다(시뮬 시작 전
LOTT 룩백 포함). 시뮬레이션이 실제로 도는 기간(>= SIM_START_DATE) 분리는 MarketModel이 담당.

설계 메모:
- 수정주가(adjusted=True) 고정: 처분효과가 매수가 대비 현재가(비율)를 비교하는데, 분할·증자가
  섞인 데이터에서 미수정가면 손익이 왜곡된다. 수정주가는 시리즈를 상수배 스케일할 뿐이라
  일별 수익률(=처분효과·시장모형 회귀가 보는 값)은 그대로 보존된다.
- 거래정지(거래량 0) 행 제거: 정지 종목이 계속 매수 후보로 남는 것 방지.
- 거래일자는 파이썬 date로 통일. pykrx 인덱스는 Timestamp이고 model은 date로 비교하므로,
  안 맞추면 에러 없이 조용히 빈 결과가 나온다(가장 위험한 유형의 버그).
- pykrx 결과는 로컬 parquet로 캐싱. 캐시 키에 (기간=확장시작일·종료일, 종목셋, adjusted)를
  반영해 이 중 하나라도 바뀌면 캐시가 자동 무효화된다.
"""

import hashlib
import os
import time
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv
from pykrx import stock

from . import config

# pykrx가 requests에 timeout을 안 걸어 KRX 무응답 시 무한 행(hang)에 빠질 수 있다
# (6-1 유니버스 샘플링에서 실측). 201종목 최초 fetch도 같은 per-ticker 패턴이라
# 런타임 경로에도 세션 기본 timeout을 강제한다. (캐시 적중 시엔 네트워크 자체가 없음.)
_orig_request = requests.Session.request


def _request_with_timeout(self, *args, **kwargs):
    kwargs.setdefault("timeout", 15)
    return _orig_request(self, *args, **kwargs)


requests.Session.request = _request_with_timeout

# 거래량은 6-3 유동성 현실성 측정(주문수량/일거래량)용 — 시세 스키마에 보존.
_PRICE_COLUMNS = ["종목코드", "거래일자", "시가", "고가", "저가", "종가", "거래량"]
_ADJUSTED = True
_SCHEMA_VER = "v2"  # 컬럼 추가 시 캐시 무효화용


def _cache_file(name: str) -> str:
    return os.path.join(config.PRICE_CACHE_DIR, name)


def _fetch_price(tickers: list[str]) -> pd.DataFrame:
    """pykrx에서 각 종목 OHLC를 받아 통일 스키마로 concat. 거래일자는 datetime64로 둠
    (parquet 저장에 깔끔). date 변환은 get_price_data 최종 단계에서 일괄 수행."""
    frames = []
    for i, ticker in enumerate(tickers):
        df = None
        for attempt in (1, 2):  # timeout 등 일시 오류 1회 재시도
            try:
                df = stock.get_market_ohlcv(
                    config.LOTT_ESTIMATION_START, config.SIM_END_DATE, ticker,
                    adjusted=_ADJUSTED,
                )
                break
            except Exception:  # noqa: BLE001
                if attempt == 2:
                    raise
                time.sleep(2.0)
        time.sleep(0.1)  # KRX 쓰로틀링 방지 (캐시 적중 시 이 루프 자체가 안 돎)
        if (i + 1) % 50 == 0:
            print(f"  가격 fetch {i + 1}/{len(tickers)}", flush=True)
        if df.empty:
            continue
        df = df[df["거래량"] > 0]  # 거래정지일 제거
        if df.empty:
            continue
        frames.append(
            pd.DataFrame(
                {
                    "종목코드": ticker,
                    "거래일자": df.index,  # DatetimeIndex -> datetime64 컬럼
                    "시가": df["시가"].round().astype("int64").values,
                    "고가": df["고가"].round().astype("int64").values,
                    "저가": df["저가"].round().astype("int64").values,
                    "종가": df["종가"].round().astype("int64").values,
                    "거래량": df["거래량"].astype("int64").values,
                }
            )
        )

    if not frames:
        raise RuntimeError(
            "pykrx에서 어떤 종목도 데이터를 받지 못했습니다 (네트워크/종목코드/기간 확인)."
        )
    return pd.concat(frames, ignore_index=True)[_PRICE_COLUMNS]


def get_price_data(tickers: list[str]) -> pd.DataFrame:
    """UNIVERSE 각 종목의 일별 OHLC를 통일 스키마로 반환. (기간은 config에서 읽음)"""
    digest = hashlib.md5(",".join(sorted(tickers)).encode()).hexdigest()[:8]
    cache = _cache_file(
        f"ohlcv_{_SCHEMA_VER}_{config.LOTT_ESTIMATION_START}_{config.SIM_END_DATE}"
        f"_adj{_ADJUSTED}_{digest}.parquet"
    )
    if os.path.exists(cache):
        result = pd.read_parquet(cache)
    else:
        result = _fetch_price(tickers)
        os.makedirs(config.PRICE_CACHE_DIR, exist_ok=True)
        result.to_parquet(cache, index=False)

    # 거래일자를 파이썬 date로 통일 (신규·캐시 경로 공통). model의 date 비교와 정합.
    result = result.copy()
    result["거래일자"] = pd.to_datetime(result["거래일자"]).dt.date
    return result


def get_index_data() -> pd.DataFrame:
    """코스피 지수의 일별 종가를 "거래일자(date)/종가(float)"로 반환. 캐싱."""
    cache = _cache_file(
        f"index_{config.KOSPI_INDEX_CODE}_{config.LOTT_ESTIMATION_START}_{config.SIM_END_DATE}.parquet"
    )
    if os.path.exists(cache):
        result = pd.read_parquet(cache)
    else:
        # 코스피 지수 API는 KRX 로그인이 필요 → 저장소 루트 .env의 KRX_ID/KRX_PW 로드.
        # (최초 1회 fetch에만 필요. 이후엔 캐시로 credential-free 유지. 가격 OHLCV는 공개라 무관.)
        load_dotenv(Path(__file__).resolve().parent.parent / ".env")
        df = stock.get_index_ohlcv(
            config.LOTT_ESTIMATION_START, config.SIM_END_DATE, config.KOSPI_INDEX_CODE
        )
        if df.empty:
            raise RuntimeError("pykrx에서 코스피 지수 데이터를 받지 못했습니다.")
        result = pd.DataFrame(
            {"거래일자": df.index, "종가": df["종가"].astype(float).values}
        )
        os.makedirs(config.PRICE_CACHE_DIR, exist_ok=True)
        result.to_parquet(cache, index=False)

    result = result.copy()
    result["거래일자"] = pd.to_datetime(result["거래일자"]).dt.date
    return result
