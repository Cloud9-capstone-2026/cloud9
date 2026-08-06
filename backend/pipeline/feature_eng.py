"""
feature_eng.py
LLM 컬럼 매핑 + 표준 포맷 변환 + 시장 데이터 병합
"""

import json
import os
import logging
import contextlib
import pandas as pd
from pykrx import stock as pykrx_stock
from google import genai
from dotenv import load_dotenv

load_dotenv()
logging.getLogger("pykrx").setLevel(logging.ERROR)

STANDARD_COLUMNS = ["날짜", "종목명", "매매구분", "체결수량", "체결단가", "총거래금액", "거래소"]


def map_columns_with_llm(columns: list[str]) -> dict:
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    prompt = f"""다음은 증권사 거래내역 CSV의 컬럼명 목록입니다:
{columns}

아래 표준 컬럼 각각에 해당하는 원본 컬럼명을 매핑해주세요.
해당하는 컬럼이 없으면 null로 표시하세요.

표준 컬럼: 날짜, 종목명, 매매구분, 체결수량, 체결단가, 총거래금액, 거래소

반드시 아래 JSON 형식으로만 답하세요. 다른 텍스트 없이 JSON만:
{{
  "날짜": "원본컬럼명 또는 null",
  "종목명": "원본컬럼명 또는 null",
  "매매구분": "원본컬럼명 또는 null",
  "체결수량": "원본컬럼명 또는 null",
  "체결단가": "원본컬럼명 또는 null",
  "총거래금액": "원본컬럼명 또는 null",
  "거래소": "원본컬럼명 또는 null"
}}"""

    response = client.models.generate_content(
        model="gemini-3.1-flash-lite",
        contents=prompt
    )

    return json.loads(response.text)


def standardize(df: pd.DataFrame, mapping: dict) -> pd.DataFrame:
    rename_map = {
        original: standard
        for standard, original in mapping.items()
        if original and original != "null" and original in df.columns
    }
    df = df.rename(columns=rename_map)

    cols = [c for c in STANDARD_COLUMNS if c in df.columns]
    df = df[cols].copy()

    if "날짜" in df.columns:
        df["날짜"] = pd.to_datetime(df["날짜"])

    for col in ["체결수량", "체결단가", "총거래금액"]:
        if col in df.columns:
            df[col] = pd.to_numeric(
                df[col].astype(str).str.replace(",", ""), errors="coerce"
            )

    return df.sort_values("날짜").reset_index(drop=True)


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


def attach_market_data(df: pd.DataFrame) -> pd.DataFrame:
    if "종목명" not in df.columns or not df["종목명"].notna().any():
        raise ValueError("종목명 컬럼이 있어야 합니다.")

    with open(os.devnull, 'w') as devnull:
        with contextlib.redirect_stderr(devnull):
            unique_names = df["종목명"].unique()
            name_to_code = {name: get_ticker_code(name) for name in unique_names}

            start = df["날짜"].min().strftime("%Y%m%d")
            end = df["날짜"].max().strftime("%Y%m%d")

            market_frames = []
            for name, code in name_to_code.items():
                if code is None:
                    continue
                try:
                    market_df = pykrx_stock.get_market_ohlcv_by_date(start, end, code)
                    market_df.index = pd.to_datetime(market_df.index)
                    market_df.index.name = "날짜"
                    market_df = market_df[["거래량"]].rename(columns={"거래량": "당일거래량"})
                    market_df["종목명"] = name
                    market_frames.append(market_df.reset_index())
                except Exception:
                    continue

    if not market_frames:
        return df

    market_all = pd.concat(market_frames, ignore_index=True)
    df = df.merge(market_all, on=["날짜", "종목명"], how="left")

    return df