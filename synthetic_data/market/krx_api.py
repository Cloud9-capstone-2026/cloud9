"""
KRX Open API 클라이언트 + 날짜별 캐시 — 시세·지수·종목정보의 유일한 수집 경로.

배경: KRX 웹사이트를 긁는 pykrx는 약관(자동화 수집 금지)·IP 차단 문제로 2026-08-26
폐기. 공식 창구인 KRX Open API(openapi.krx.co.kr, 인증키, 일 1만 콜)로 통일한다.
생성기 시세(market_data), 실계좌 종목명→코드(backend feature_eng), 복권성 순위표
(ml/train/make_lott_table)가 모두 여기를 거친다. 키는 .env의 KRX_API_KEY.

캐시: ml/cache/krx/{daily,index,base}/{YYYYMMDD}.parquet — 하루 1파일, 휴장일은 빈
파일(캘린더 역할). 재실행 시 새 날짜만 요청. 시세는 미수정주가이며 수정주가는
adjust_prices()가 상장주식수·시총으로 만든다(아래 참조).
"""

import os
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import requests
from dotenv import load_dotenv

_REPO = Path(__file__).resolve().parents[2]
load_dotenv(_REPO / ".env")

API = "https://data-dbg.krx.co.kr/svc/apis/"
CACHE = Path(os.environ.get("CANARY_KRX_CACHE_DIR", _REPO / "ml" / "cache" / "krx"))
PACE_SEC = 0.2
WORKERS = 4

DAILY_COLUMNS = ["종목코드", "시장", "소속부", "시가", "고가", "저가", "종가",
                 "거래량", "거래대금", "시가총액", "상장주식수"]


def _get(path: str, bas_dd: str) -> list[dict]:
    key = os.environ.get("KRX_API_KEY")
    if not key:
        raise RuntimeError("KRX_API_KEY 미설정 — .env 또는 환경변수에 KRX Open API 인증키 필요")
    r = requests.get(API + path, params={"basDd": bas_dd}, headers={"AUTH_KEY": key}, timeout=30)
    r.raise_for_status()
    return r.json()["OutBlock_1"]


def _cached(kind: str, key: str, fetch) -> pd.DataFrame:
    path = CACHE / kind / f"{key}.parquet"
    if path.exists():
        return pd.read_parquet(path)
    for wait in (10, 30, 60, 180, None):  # 네트워크·한도 초과 등 — 점점 길게 재시도
        try:
            df = fetch()
            break
        except Exception as e:  # noqa: BLE001
            if wait is None:
                raise
            print(f"  krx {kind}/{key} 실패({type(e).__name__}: {e}) — {wait}초 후 재시도", flush=True)
            time.sleep(wait)
    time.sleep(PACE_SEC)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path)
    return df


def _num(s) -> pd.Series:
    return pd.to_numeric(pd.Series(s).astype(str).str.replace(",", ""), errors="coerce")


def ymd(d: date) -> str:
    return d.strftime("%Y%m%d")


def daily(d: date) -> pd.DataFrame:
    """코스피+코스닥 전 종목 그날 시세(DAILY_COLUMNS). 휴장일이면 빈 DataFrame."""
    def fetch():
        s = ymd(d)
        rows = _get("sto/stk_bydd_trd", s) + _get("sto/ksq_bydd_trd", s)
        if not rows:
            return pd.DataFrame(columns=DAILY_COLUMNS)
        raw = pd.DataFrame(rows)
        return pd.DataFrame({
            "종목코드": raw["ISU_CD"].astype(str), "시장": raw["MKT_NM"].astype(str),
            "소속부": raw["SECT_TP_NM"].astype(str),
            "시가": _num(raw["TDD_OPNPRC"]), "고가": _num(raw["TDD_HGPRC"]),
            "저가": _num(raw["TDD_LWPRC"]), "종가": _num(raw["TDD_CLSPRC"]),
            "거래량": _num(raw["ACC_TRDVOL"]), "거래대금": _num(raw["ACC_TRDVAL"]),
            "시가총액": _num(raw["MKTCAP"]), "상장주식수": _num(raw["LIST_SHRS"]),
        })
    return _cached("daily", ymd(d), fetch)


def index_close(d: date) -> float:
    """코스피 지수 종가. 지수 API는 그날 코스피 계열 전체를 주므로 '코스피' 행만."""
    def fetch():
        rows = [r for r in _get("idx/kospi_dd_trd", ymd(d)) if r["IDX_NM"] == "코스피"]
        if not rows:
            raise RuntimeError(f"{d} 코스피 지수 행 없음")
        return pd.DataFrame({"종가": [float(str(rows[0]["CLSPRC_IDX"]).replace(",", ""))]})
    return float(_cached("index", ymd(d), fetch)["종가"].iloc[0])


def base_info(d: date) -> pd.DataFrame:
    """그날의 종목기본정보: 종목코드·종목명·주식종류·증권그룹·소속부·시장."""
    def fetch():
        s = ymd(d)
        rows = _get("sto/stk_isu_base_info", s) + _get("sto/ksq_isu_base_info", s)
        if not rows:  # 휴장일
            return pd.DataFrame(columns=["종목코드", "종목명", "주식종류", "증권그룹", "소속부", "시장"])
        raw = pd.DataFrame(rows)
        return pd.DataFrame({
            "종목코드": raw["ISU_SRT_CD"].astype(str), "종목명": raw["ISU_ABBRV"].astype(str),
            "주식종류": raw["KIND_STKCERT_TP_NM"].astype(str),
            "증권그룹": raw["SECUGRP_NM"].astype(str), "소속부": raw["SECT_TP_NM"].astype(str),
            "시장": raw["MKT_TP_NM"].astype(str),
        })
    return _cached("base", ymd(d), fetch)


def prefetch(start: date, end: date, with_index: bool = True) -> list[date]:
    """[start, end] 평일의 시세(+지수)를 캐시에 채우고 거래일 목록을 돌려준다.
    호출당 1~2초라 스레드 WORKERS개로 병렬(한도는 일 콜 수 기준)."""
    weekdays = [start + timedelta(days=i) for i in range((end - start).days + 1)]
    weekdays = [d for d in weekdays if d.weekday() < 5]

    def fill(d):
        if len(daily(d)) and with_index:
            index_close(d)
        return d

    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        for i, _ in enumerate(ex.map(fill, weekdays), 1):
            if i % 100 == 0:
                print(f"  krx 수집 {i}/{len(weekdays)}일", flush=True)
    return [d for d in weekdays if len(daily(d))]


def load_daily(days: list[date]) -> pd.DataFrame:
    """캐시된 일별 시세를 long 포맷(거래일자 컬럼 추가)으로 합친다."""
    frames = [daily(d).assign(거래일자=d) for d in days]
    return pd.concat(frames, ignore_index=True)


def adjust_prices(df: pd.DataFrame, tol: float = 0.08) -> pd.DataFrame:
    """미수정주가 → 수정주가 (액면분할·병합·무상증자 보정). 시가·고가·저가·종가를 함께 조정.

    원리: 분할·병합(감자)·무상증자는 상장주식수가 k배로 바뀌고 시가총액은 연속이다
    (가격이 1/k). 유상증자·전환은 주식수와 함께 시총도 같은 비율로 뛰므로 시총 연속성
    조건에서 걸러진다(보정 안 함 — KRX 수정주가의 권리락 이론가 보정은 하지 않는다,
    알려진 근사). 종목별로 날짜순 정렬해 상장주식수 변화율 |k−1| > tol 이고 시총 변화가
    k의 절반(로그 기준)보다 작으면 — 정지 후 재개 등으로 당일 가격이 정확히 1/k가 아니어도
    시총은 크게 안 움직이므로 종가 비율보다 견고 — 그 이전 모든 행의 가격에 1/k를 곱한다.
    입력은 long 포맷(종목코드·거래일자·시가·고가·저가·종가·시가총액·상장주식수).
    반환은 같은 행 순서의 복사본 + '수정계수' 컬럼(누적).
    """
    out = df.copy()
    out["수정계수"] = 1.0
    price_cols = ["시가", "고가", "저가", "종가"]
    out[price_cols] = out[price_cols].astype("float64")  # 정수 원시가에 계수 곱 — dtype 경고 방지
    for tk, g in out.groupby("종목코드", sort=False):
        g = g.sort_values("거래일자")
        shares = g["상장주식수"].to_numpy(dtype=float)
        mcap = g["시가총액"].to_numpy(dtype=float)
        factor = 1.0
        factors = [1.0] * len(g)
        # 뒤에서 앞으로: 변화 시점 이전 행들에 누적 계수 적용
        for i in range(len(g) - 1, 0, -1):
            if shares[i - 1] > 0 and shares[i] > 0 and mcap[i - 1] > 0 and mcap[i] > 0:
                k = shares[i] / shares[i - 1]
                if abs(k - 1.0) > tol and abs(np.log(mcap[i] / mcap[i - 1])) < 0.5 * abs(np.log(k)):
                    factor /= k
            factors[i - 1] = factor
        if factor != 1.0:
            idx = g.index
            f = pd.Series(factors, index=idx)
            out.loc[idx, "수정계수"] = f
            for c in price_cols:
                out.loc[idx, c] = out.loc[idx, c] * f
    return out
