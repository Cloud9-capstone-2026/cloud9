"""
averaging_down.py
템플릿: 물타기 반복 M회 — 보유 중인 종목을 평균단가보다 낮은 가격에 추가
매수하는 것을 "물타기 1회"로 세고, 같은 종목에서 누적 M회째부터 플래그.

시세 없이 거래 데이터만으로 판정한다(평가손실 대신 "평단보다 낮은 매수"로
정의 — 1계층은 시세 무관 원칙). 포지션을 전량 청산하면 카운트가 리셋된다
(새 포지션은 새 출발).
"""

import numpy as np
import pandas as pd


def check_averaging_down(df: pd.DataFrame, pos: pd.DataFrame,
                         times: int) -> pd.Series:
    dates = pd.to_datetime(df["날짜"]).dt.normalize()
    order = dates.reset_index(drop=True).sort_values(kind="stable").index

    is_buy = df["매매구분"].astype(str).str.contains("매수").to_numpy()
    prices = pd.to_numeric(df["체결단가"], errors="coerce").to_numpy(dtype=float)
    names = df["종목명"].astype(str).to_numpy()
    held = pos["보유수량_직전"].to_numpy(dtype=float)
    avg = pos["평균단가_직전"].to_numpy(dtype=float)

    flag = np.zeros(len(df), dtype=bool)
    count: dict[str, int] = {}
    for p in order:
        if not is_buy[p]:
            continue
        if held[p] == 0:
            count[names[p]] = 0  # 새 포지션 시작 — 물타기 카운트 리셋
        elif not np.isnan(avg[p]) and prices[p] < avg[p]:
            count[names[p]] = count.get(names[p], 0) + 1
            if count[names[p]] >= times:
                flag[p] = True
    return pd.Series(flag, index=df.index)
