"""
daily_frequency.py
규칙: 같은 종목 하루 N회 이상 매매 → 해당 거래들 플래그
"""

import pandas as pd

DAILY_TRADE_LIMIT = 4


def check_daily_trade_frequency(df: pd.DataFrame,
                                limit: int = DAILY_TRADE_LIMIT) -> pd.Series:
    """
    각 거래별로 규칙 위반 여부(True/False) 반환 (df와 같은 인덱스).
    limit는 사용자 정의 규칙 템플릿의 파라미터(N회) — 기본값은 v1 동결값.
    """
    df = df.copy()
    df["날짜_일"] = df["날짜"].dt.date

    counts = df.groupby(["날짜_일", "종목명"])["종목명"].transform("size")
    return counts >= limit