"""
reentry_after_loss.py
템플릿: 손실 후 재진입 D일 — 손실 확정 매도 후 D일 이내(경계 포함) 같은 종목
재매수를 플래그.

손실 여부는 포지션 재생의 실현손익 기준(평균단가법). 원가미상 매도는 손실로
치지 않으므로(모르는 것을 손실로 단정하지 않음) 자동 제외된다.
"""

import pandas as pd


def check_reentry_after_loss(df: pd.DataFrame, pos: pd.DataFrame,
                             days: int) -> pd.Series:
    """(매수일 − 최근손실매도일) <= days 인 매수 → True (df와 같은 인덱스)."""
    is_buy = df["매매구분"].astype(str).str.contains("매수")
    last_loss = pd.to_datetime(pos["최근손실매도일"])
    gap = (pd.to_datetime(df["날짜"]).dt.normalize() - last_loss).dt.days
    return is_buy & last_loss.notna() & (gap <= days)
