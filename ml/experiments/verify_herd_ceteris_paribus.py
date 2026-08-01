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

import json
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


def main(seed: int = 7):
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
            seed=seed, mode="natural",
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
    means, meds, ses, ns = g.mean(), g.median(), g.sem(), g.size()
    print(f"\n=== herd ceteris-paribus (시드 {seed}, herd만 변화·전원 그 외 동일) ===")
    print(f"{'herd':>6}{'계좌':>8}{'평균':>10}{'중앙값':>10}{'SE':>10}")
    for hs in sorted(means.index):
        print(f"{hs:>6}{ns[hs]:>8}{means[hs]:>10.4f}{meds[hs]:>10.4f}{ses[hs]:>10.4f}")

    # 판정 1(실험 B와 동일 관용 규칙): 평균 단조 비감소, 허용 = 인접 역전 1건이고
    # 크기 < 결합 SE. 판정 2: Spearman 양(+)·p<0.05 (계좌 단위 — 이상치에 강건).
    levels = sorted(means.index)
    drops = []
    for a, b in zip(levels, levels[1:]):
        d = float(means[b] - means[a])
        if d < 0:
            drops.append({"from": a, "to": b, "drop": round(d, 4),
                          "combined_se": round(float(np.hypot(ses[a], ses[b])), 4)})
    mono = (len(drops) == 0) or (
        len(drops) == 1 and abs(drops[0]["drop"]) < drops[0]["combined_se"])
    r, p = stats.spearmanr(ag["hs"], ag["mean_abn_vol_at_buy"])
    ok = mono and (r > 0) and (p < 0.05)
    verdict = "통과 — 메커니즘 유효" if ok else "미통과 — 군집 채널 재검토"
    print(f"\n단조(허용 1건<결합SE): {'OK' if mono else 'FAIL'} (역전 {len(drops)}건)"
          f" | Spearman r={r:+.4f} p={p:.3g} | 판정: {verdict}")

    out_path = os.path.join(_REPO, "ml", "cache",
                            f"verify_herd_ceteris_paribus_s{seed}.json")
    with open(out_path, "w", encoding="utf-8") as fp:
        json.dump({
            "herd_grid": HERD_GRID, "fixed_params": FIXED, "seed": seed,
            "level_means": {str(hs): round(float(means[hs]), 4) for hs in levels},
            "level_medians": {str(hs): round(float(meds[hs]), 4) for hs in levels},
            "level_ses": {str(hs): round(float(ses[hs]), 4) for hs in levels},
            "level_ns": {str(hs): int(ns[hs]) for hs in levels},
            "inversions": drops, "monotonic_with_tolerance": bool(mono),
            "spearman_r": round(float(r), 4), "p": float(f"{p:.3g}"),
            "verdict": verdict,
        }, fp, ensure_ascii=False, indent=2)
    print(f"결과 저장: {out_path}")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 7)
