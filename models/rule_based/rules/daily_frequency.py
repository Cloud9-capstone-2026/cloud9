"""
daily_frequency.py
규칙: 같은 종목 하루 N회 이상 매매 → 해당 거래들 플래그
"""

import pandas as pd

DAILY_TRADE_LIMIT = 4


def check_daily_trade_frequency(df: pd.DataFrame) -> pd.Series:
    """
    각 거래별로 규칙 위반 여부(True/False) 반환 (df와 같은 인덱스)
    """
    df = df.copy()
    df["날짜_일"] = df["날짜"].dt.date

    counts = df.groupby(["날짜_일", "종목명"])["종목명"].transform("size")
    return counts >= DAILY_TRADE_LIMIT