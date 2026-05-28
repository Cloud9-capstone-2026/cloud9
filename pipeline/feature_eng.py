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


def get_ticker_code(name: str) -> str | None:
    try:
        tickers = pykrx_stock.get_market_ticker_list()
        for ticker in tickers:
            if pykrx_stock.get_market_ticker_name(ticker) == name:
                return ticker
        return None
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