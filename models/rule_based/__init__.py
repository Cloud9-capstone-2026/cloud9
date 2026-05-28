"""
rule_based/__init__.py
Rule-based 탐지 — 거래별 점수 산출
"""

import pandas as pd
from models.rule_based.rules.daily_frequency import check_daily_trade_frequency


def run_rule_based(df: pd.DataFrame) -> dict:
    """
    반환: {
        "is_anomaly": bool,
        "trade_results": [
            {"날짜", "종목명", "rule_score": 0 or 1, "triggered_rules": [...]}, ...
        ]
    }
    """
    if len(df) == 0:
        return {"is_anomaly": False, "trade_results": []}

    df = df.reset_index(drop=True)
    freq_flags = check_daily_trade_frequency(df)

    trade_results = []
    for i, row in df.iterrows():
        rules = []
        if freq_flags.iloc[i]:
            rules.append("일중_반복매매")

        trade_results.append({
            "날짜": str(row["날짜"].date()),
            "종목명": row["종목명"],
            "rule_score": 1 if rules else 0,
            "triggered_rules": rules
        })

    is_anomaly = any(t["rule_score"] == 1 for t in trade_results)
    return {"is_anomaly": is_anomaly, "trade_results": trade_results}