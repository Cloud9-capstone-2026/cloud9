"""
다중 시드·모드 데이터셋 생성기 (7-5).

실행: python -m synthetic_data.generate_dataset  (레포 최상위에서, 총 ~3분)

산출: dataset/{trades,labels,meta,trade_labels}/ 종류별 하위 폴더에 학습(확장 샘플링)
      5시드 + 평가(자연) 2시드 = 종류당 7파일 + dataset/manifest.csv. 산출물은
      .gitignore(용량) — 시드·config가 고정이라 이 스크립트 1회 실행으로 누구든
      완전 재현 가능하며, 파일 전달은 팀 드라이브로 한다.

평가 시드는 자연 분포이므로 KCMI 재현 지표를 함께 출력한다(확장 모드는 재현 검증
대상이 아님 — '탐지 스펙트럼 정의'이지 현실 재현이 아니다. config.EXTENDED_MIXTURE 참조).
"""

import os

import pandas as pd

from . import config
from .validation.kcmi_metrics import compute_metrics
from .main import package_outputs
from .core.model import MarketModel


def _run_one(mode: str, seed: int, verify: bool) -> dict:
    name = f"{'train_extended' if mode == 'extended' else 'eval_natural'}_s{seed}"
    print(f"\n=== {name} 생성 중 ===", flush=True)
    model = MarketModel(
        n_investors=config.N_INVESTORS,
        tickers=config.UNIVERSE_TICKERS,
        seed=seed,
        mode=mode,
    )
    model.run()
    paths = {kind: config.dataset_path(name, kind) for kind in config.DATASET_KINDS}
    n_trades, n_agents = package_outputs(
        model, paths["trades"], paths["labels"], paths["meta"],
        trade_labels_path=paths["trade_labels"],
    )
    row = {"name": name, "mode": mode, "seed": seed,
           "n_trades": n_trades, "n_agents": n_agents,
           "n_investors": config.N_INVESTORS,
           "sim": f"{config.SIM_START_DATE}-{config.SIM_END_DATE}"}

    if verify:  # 평가 시드: 자연 분포 → KCMI 재현 핵심 지표 확인
        r = compute_metrics(model)
        h, tv, dp = r["holding"], r["turnover"], r["disposition"]
        print(f"  [KCMI 재현] 보유 {h['mean']:.2f}/{h['median']:.1f} (9.67/3.0) | "
              f"회전 {tv['annual'] * 100:.0f}% (714%) | 처분 {dp['ratio']:.3f} (2.18) | "
              f"OC {r['overconf']:.3f} | H-L {r['lottery']['trading']['HmL'] * 100:+.1f}%p (+51%p)")
        row.update(holding_mean=round(h["mean"], 2), turnover=round(tv["annual"], 3),
                   disposition=round(dp["ratio"], 3))
    return row


def main():
    for kind in config.DATASET_KINDS:  # 종류별 하위 폴더 (config.dataset_path 규약)
        os.makedirs(os.path.join(config.DATASET_DIR, kind), exist_ok=True)
    rows = []
    for seed in config.DATASET_TRAIN_SEEDS:
        rows.append(_run_one("extended", seed, verify=False))
    for seed in config.DATASET_EVAL_SEEDS:
        rows.append(_run_one("natural", seed, verify=True))
    manifest = pd.DataFrame(rows)
    mpath = os.path.join(config.DATASET_DIR, "manifest.csv")
    manifest.to_csv(mpath, index=False, encoding="utf-8-sig")
    print(f"\nmanifest → {mpath}")
    print(manifest[["name", "mode", "seed", "n_trades"]].to_string(index=False))


if __name__ == "__main__":
    main()
