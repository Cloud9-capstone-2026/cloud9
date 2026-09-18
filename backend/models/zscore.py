"""
zscore.py
2계층 통계 탐지: 거래 1건당 Z-score + 마할라노비스 거리

baseline(이전 업로드 거래)이 MIN_BASELINE_ROWS 미만이면 통계 계층은
"판정 불가" — 3계층 판정 불가와 같은 규약으로 trade_results를 전부 None으로
돌려주고, 앙상블은 stat flag 없이 나머지 계층만으로 판정한다(2026-09-18).
과거의 하드코딩 기본 통계(단가 5만±3만 등)는 첫 업로드에서 비싼 주식을
전부 경고로 만들어 폐기.
"""

import numpy as np
import pandas as pd
from scipy.spatial.distance import mahalanobis

FEATURES = ["체결단가", "체결수량", "총거래금액"]

MIN_BASELINE_ROWS = 10


def compute_baseline_stats(baseline: pd.DataFrame) -> tuple:
    arr = baseline[FEATURES]
    mean = arr.mean()
    std  = arr.std().replace(0, 1)
    cov  = np.cov(arr.values.T)
    cov += np.eye(cov.shape[0]) * 1e-6
    return mean, std, cov


def run_zscore(new_trades: pd.DataFrame, baseline: pd.DataFrame, threshold: float = 2.5) -> dict:
    """
    반환: {
        "is_anomaly": bool,
        "available": bool,   # False = baseline 부족으로 판정 불가
        "trade_results": [
            {"날짜", "종목명", "z_vector", "mahalanobis", "stat_score", "is_anomaly"}, ...
        ]   # 판정 불가면 거래 수만큼 None
    }
    stat_score = 1 - exp(-mahalanobis / threshold)  # 0~1 부드러운 saturation
    """
    if len(new_trades) == 0:
        return {"is_anomaly": False, "available": True, "trade_results": []}

    if len(baseline) < MIN_BASELINE_ROWS:
        return {"is_anomaly": False, "available": False,
                "trade_results": [None] * len(new_trades)}

    mean, std, cov = compute_baseline_stats(baseline)
    cov_inv = np.linalg.inv(cov)

    trade_results = []
    for _, row in new_trades.iterrows():
        vec = row[FEATURES].astype(float).values
        z_vec = (vec - mean.values) / std.values
        m_dist = float(mahalanobis(vec, mean.values, cov_inv))
        stat_score = float(1 - np.exp(-m_dist / threshold))

        trade_results.append({
            "날짜": str(row["날짜"].date()),
            "종목명": row["종목명"],
            "z_vector": z_vec.tolist(),
            "mahalanobis": round(m_dist, 4),
            "stat_score": round(stat_score, 4),
            "is_anomaly": m_dist > threshold
        })

    is_anomaly = any(t["is_anomaly"] for t in trade_results)
    return {"is_anomaly": is_anomaly, "available": True, "trade_results": trade_results}
