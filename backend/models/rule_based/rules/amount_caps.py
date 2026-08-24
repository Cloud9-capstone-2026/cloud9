"""
amount_caps.py
템플릿 2종: 금액 한도 — 사용자가 스스로 정하는 절제 규칙 중 가장 직관적인 유형.

- 매수금액 상한 W원: 한 번의 매수 금액이 W를 넘으면 그 매수를 플래그
- 일일 매매대금 상한 V원: 하루 총 거래대금이 V를 넘으면 그날 거래 전부 플래그
  (체결 시각이 없어 "초과 이후 거래만"은 판정 불가 — 날 단위가 정직한 정의)

금액은 총거래금액 컬럼이 있으면 그것을, 없으면 수량×단가.
"""

import pandas as pd


def _amounts(df: pd.DataFrame) -> pd.Series:
    if "총거래금액" in df.columns:
        amt = pd.to_numeric(df["총거래금액"], errors="coerce")
        if amt.notna().all():
            return amt
    return (pd.to_numeric(df["체결수량"], errors="coerce")
            * pd.to_numeric(df["체결단가"], errors="coerce"))


def check_single_buy_cap(df: pd.DataFrame, pos: pd.DataFrame,
                         limit: float) -> pd.Series:
    is_buy = df["매매구분"].astype(str).str.contains("매수")
    return is_buy & (_amounts(df) > limit)


def check_daily_total_cap(df: pd.DataFrame, pos: pd.DataFrame,
                          limit: float) -> pd.Series:
    day = pd.to_datetime(df["날짜"]).dt.normalize()
    daily_total = _amounts(df).groupby(day).transform("sum")
    return daily_total > limit
