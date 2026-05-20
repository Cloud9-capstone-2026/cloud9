"""
daily_frequency.py
규칙 정의: 같은 종목 하루 N회 이상 매매
"""

import pandas as pd

DAILY_TRADE_LIMIT = 1


def check_daily_trade_frequency(df: pd.DataFrame) -> list:
    detections = []

    df = df.copy()
    df["날짜_일"] = df["날짜"].dt.date

    grouped = df.groupby(["날짜_일", "종목명"]).size().reset_index(name="횟수")
    flagged = grouped[grouped["횟수"] >= DAILY_TRADE_LIMIT]

    for _, row in flagged.iterrows():
        detections.append({
            "rule": "일중_반복매매",
            "날짜": str(row["날짜_일"]),
            "종목명": row["종목명"],
            "횟수": int(row["횟수"]),
            "evidence": f"{row['날짜_일']} {row['종목명']} {row['횟수']}회 매매",
        })

    return detections