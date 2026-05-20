"""
rule_based/__init__.py
Rule-based 탐지 실행
"""

import pandas as pd
from models.rule_based.rules.daily_frequency import check_daily_trade_frequency


def run_rule_based(df: pd.DataFrame) -> dict:
    detections = []
    detections += check_daily_trade_frequency(df)

    is_anomaly = len(detections) > 0
    score = min(len(detections) / len(df), 1.0) if len(df) > 0 else 0.0

    return {
        "is_anomaly": is_anomaly,
        "score": round(score, 4),
        "detections": detections
    }