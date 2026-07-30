"""
단계 0 실험 B 후속 — 군집(herd) ceteris-paribus 재실험 (사전 등록된 미통과 경로).

실행: python -m ml.experiments.verify_herd_ceteris_paribus   (레포 루트에서)

배경: 관찰 데이터(확장 5시드)에서 herd 채널만 판정2 미달(부분 순위상관
r=+0.031, 양방향 p=0.071 — 부호는 양). 교란(다른 편향·인구통계 혼합)과
꼬리 구간의 얕은 반응이 겹친 것인지, 메커니즘 자체가 죽어 있는지를 분리한다.

설계: herd_sensitivity만 {0.0, 0.3, 0.6, 0.9, 1.2} 그리드로 계좌에 순환 배정,
나머지 파라미터는 자연 평균으로 전원 고정(그룹 배율·확장 혼합 미적용), 자연
모드 시드 7 1회. 지표는 실험 B와 동일 코드 경로(build_features aggregates의
mean_abn_vol_at_buy).

판정(사전 지정): 레벨별 지표 평균 단조 증가 + 계좌 단위 Spearman p<0.05(양).
통과 시 = 메커니즘 유효, 관찰 미달은 교란·노이즈 소산으로 결론(문서화 후 진행).
미통과 시 = 생성기 군집 채널 자체 재검토(중단·논의).
"""

import os
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

_REPO = str(Path(__file__).resolve().parents[2])
sys.path.insert(0, _REPO)

from synthetic_data import config  # noqa: E402
from synthetic_data.core import model as model_mod  # noqa: E402
from synthetic_data.core.params import BehaviorParams  # noqa: E402
from synthetic_data.features import build_features, load_trades_csv  # noqa: E402
from synthetic_data.market_data import get_index_data, get_price_data  # noqa: E402

HERD_GRID = [0.0, 0.3, 0.6, 0.9, 1.2]
FIXED = dict(  # 자연 평균 고정값 (config.BehaviorParamRanges 0730 확정 기준)
    disposition_strength=4.40, overconfidence=0.1,
    lottery_preference=0.15, base_buy_prob=0.12, base_sell_prob=0.064,
)


def main():
    counter = {"i": 0}

    def fixed_params(rng, ranges, group, multipliers):
        hs = HERD_GRID[counter["i"] % len(HERD_GRID)]
        counter["i"] += 1
        return BehaviorParams(herd_sensitivity=hs, **FIXED)

    orig = model_mod.sample_investor_params
    model_mod.sample_investor_params = fixed_params
    try:
        m = model_mod.MarketModel(
            n_investors=config.N_INVESTORS,
            tickers=config.UNIVERSE_TICKERS,
            seed=7, mode="natural",
        )
        m.run()
    finally:
        model_mod.sample_investor_params = orig

    hs_by_agent = {str(a.unique_id): a.params.herd_sensitivity for a in m.agents}

    # 실험 B와 동일 지표 경로: trades CSV → build_features → aggregates
    from synthetic_data.main import TRADES_COLUMNS
    df = m.trades_to_dataframe()[TRADES_COLUMNS]
    with tempfile.TemporaryDirectory() as td:
        p = os.path.join(td, "cp_trades.csv")
        df.to_csv(p, index=False, encoding="utf-8-sig")
        trades, _ = load_trades_csv(p)
    out = build_features(trades, get_price_data(config.UNIVERSE_TICKERS),
                         get_index_data(), windows=(None,))
    ag = out["aggregates"]
    ag = ag[(ag["window"] == "full") & (ag["n_buys"] > 0)].copy()
    ag["hs"] = ag["agent_id"].astype(str).map(hs_by_agent)

    g = ag.groupby("hs")["mean_abn_vol_at_buy"]
    means, ses, ns = g.mean(), g.sem(), g.size()
    print("\n=== herd ceteris-paribus (시드 7, herd만 변화·전원 그 외 동일) ===")
    print(f"{'herd':>6}{'계좌':>8}{'abn_vol@buy 평균':>18}{'SE':>10}")
    for hs in sorted(means.index):
        print(f"{hs:>6}{ns[hs]:>8}{means[hs]:>18.4f}{ses[hs]:>10.4f}")

    mono = all(means[b] >= means[a]
               for a, b in zip(sorted(means.index), sorted(means.index)[1:]))
    r, p = stats.spearmanr(ag["hs"], ag["mean_abn_vol_at_buy"])
    ok = mono and (r > 0) and (p < 0.05)
    print(f"\n단조 증가: {'OK' if mono else 'FAIL'} | Spearman r={r:+.4f} p={p:.3g}"
          f" | 판정: {'통과 — 메커니즘 유효' if ok else '미통과 — 군집 채널 재검토'}")


if __name__ == "__main__":
    main()
