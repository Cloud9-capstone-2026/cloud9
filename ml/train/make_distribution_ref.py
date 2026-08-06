"""
실계좌 분포 모니터링 기준치 생성 (단계 1b — Release 번들 동봉용).

실행: python -m ml.train.make_distribution_ref   (레포 루트에서)

학습 데이터(확장 5시드, 계좌 단위 full 윈도 집계)에서 핵심 지표의 분위수를
기록한다. 추론 시 실계좌 지표가 이 범위를 크게 벗어나면 sim-to-real 이탈
경고 플래그를 결과에 남기는 용도(단계 3에서 소비). 배포 서버에는 dataset/이
없으므로 이 파일을 아티팩트와 함께 배포한다.
"""

import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO))

from synthetic_data import config  # noqa: E402

CACHE_DIR = _REPO / "ml" / "cache"
ART_DIR = _REPO / "ml" / "artifacts"
PCTS = [1, 5, 25, 50, 75, 95, 99]


def main():
    frames = []
    for s in config.DATASET_TRAIN_SEEDS:
        ag = pd.read_parquet(CACHE_DIR / f"train_extended_s{s}_aggregates.parquet")
        frames.append(ag[ag["window"] == "full"])
    ag = pd.concat(frames, ignore_index=True)
    n_tr = ag["n_buys"].fillna(0) + ag["n_sells"].fillna(0)
    metrics = {
        "turnover_annual": ag["turnover_annual"],
        "buy_share": (ag["n_buys"] / n_tr.where(n_tr > 0)),
        "mean_abn_vol_at_buy": ag["mean_abn_vol_at_buy"],
        "mean_lott_at_buy": ag["mean_lott_at_buy"],
        "holding_days_mean": ag["holding_days_mean"],
        "n_trades": n_tr,
    }
    out = {"source": "train_extended 5시드 pooled, 계좌 단위 full 윈도",
           "n_accounts": int(len(ag)), "percentiles": PCTS, "metrics": {}}
    for k, v in metrics.items():
        v = pd.to_numeric(v, errors="coerce").dropna()
        out["metrics"][k] = {
            "n": int(len(v)),
            "quantiles": [round(float(x), 6) for x in np.percentile(v, PCTS)],
        }
    path = ART_DIR / "distribution_ref.json"
    with open(path, "w", encoding="utf-8") as fp:
        json.dump(out, fp, ensure_ascii=False, indent=2)
    print(f"distribution_ref.json → {path}")
    for k, m in out["metrics"].items():
        print(f"  {k:<22} p1~p99: {m['quantiles'][0]} ~ {m['quantiles'][-1]}")


if __name__ == "__main__":
    main()
