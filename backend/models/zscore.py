"""
zscore.py
2계층 통계 탐지: 거래 1건당 Z-score + 마할라노비스 거리
"""

import numpy as np
import pandas as pd
from scipy.spatial.distance import mahalanobis

FEATURES = ["체결단가", "체결수량", "총거래금액"]

#baseline z-score 계산 - 행이 10개 미만일 때
DEFAULT_MEAN = {"체결단가": 50000, "체결수량": 10, "총거래금액": 500000}
DEFAULT_STD  = {"체결단가": 30000, "체결수량": 5,  "총거래금액": 300000}
MIN_BASELINE_ROWS = 10


def compute_baseline_stats(baseline: pd.DataFrame) -> tuple:
    if len(baseline) < MIN_BASELINE_ROWS:
        mean = pd.Series(DEFAULT_MEAN)
        std  = pd.Series(DEFAULT_STD)
        cov  = np.diag(std.values ** 2)
        return mean, std, cov

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
        "trade_results": [
            {"날짜", "종목명", "z_vector", "mahalanobis", "stat_score", "is_anomaly"}, ...
        ]
    }
    stat_score = 1 - exp(-mahalanobis / threshold)  # 0~1 부드러운 saturation
    """
    if len(new_trades) == 0:
        return {"is_anomaly": False, "trade_results": []}

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
    return {"is_anomaly": is_anomaly, "trade_results": trade_results}