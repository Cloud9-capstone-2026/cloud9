"""
min_holding.py
템플릿: 최소 보유기간 X일 — 산 지 X일 미만에 판 매도를 플래그.

당일_왕복매매의 일반화 버전(X=1이면 당일 매도를 잡음)이지만 대체가 아니라
별도 템플릿이다: 왕복 규칙은 그날 그 종목의 매수까지 전부 플래그하는 반면
이 규칙은 위반의 주체인 매도에만 붙는다(매수 시점엔 아직 위반이 아니므로).

최근매수일이 없는 매도(업로드 이력 밖 보유분)는 보유기간을 알 수 없어 제외.
"""

import pandas as pd


def check_min_holding(df: pd.DataFrame, pos: pd.DataFrame, days: int) -> pd.Series:
    """보유일수(매도일 − 최근매수일) < days 인 매도 → True (df와 같은 인덱스)."""
    is_sell = df["매매구분"].astype(str).str.contains("매도")
    last_buy = pd.to_datetime(pos["최근매수일"])
    holding = (pd.to_datetime(df["날짜"]).dt.normalize() - last_buy).dt.days
    return is_sell & last_buy.notna() & (holding < days)
