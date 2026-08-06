"""
same_day_roundtrip.py
규칙(R2): 동일 종목을 같은 날 매수하고 매도(왕복매매) → 해당 종목·일의 거래들 플래그

충동적 단타의 bright line — 날짜·종목·매매구분만으로 판정 가능(포지션 재생 불필요).
손익 기반 규칙(손실 직후 재진입·물타기)은 포지션 재생 인프라가 필요해 v2 이월.
"""

import pandas as pd


def check_same_day_roundtrip(df: pd.DataFrame) -> pd.Series:
    """각 거래별 위반 여부(True/False) 반환 (df와 같은 인덱스)."""
    df = df.copy()
    df["날짜_일"] = df["날짜"].dt.date
    grp = df.groupby(["날짜_일", "종목명"])["매매구분"]
    has_buy = grp.transform(lambda s: (s == "매수").any())
    has_sell = grp.transform(lambda s: (s == "매도").any())
    return has_buy & has_sell
