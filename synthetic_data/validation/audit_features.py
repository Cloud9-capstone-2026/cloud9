"""
features.py 회귀 테스트 (7-3-4): 합성 CSV(라벨 포함) → 피처×라벨 rho 표 + 교차검증.

용도: 생성기·빌더를 바꿀 때마다 실행해 (1) 4개 편향 라벨의 학습성(스모크 rho)이
회귀하지 않았는지, (2) 빌더의 처분 측정이 하네스와 정합인지, (3) 관측창별 유효
계좌 수를 확인한다. rho는 목표가 아니라 스모크(DECISIONS.md §0 순환 방지 원칙).

실행: python -m synthetic_data.validation.audit_features  (기본: config.OUTPUT_CSV_PATH)
"""

import os
import sys

import pandas as pd

from .. import config
from ..features import build_features, load_trades_csv
from ..market.lott import load_lott_table
from ..market_data import get_index_data, get_price_data

# 7-1d/7-2 확정 시점의 스모크 기준값 (자연 모드 canonical, 시드 7) — 큰 폭 하락 시 회귀 의심.
# ★ 확장 모드 데이터에 돌리면 기준값·교차검증 참조치는 1:1로 적용되지 않는다(참고용):
#   라벨 산포 확대로 채널 피처 rho는 상승하고, n_buys x OC처럼 그룹 배율 교란으로
#   부풀어 있던 상관은 오히려 하락(교란 해소 — 회귀 아님), 풀드 PGR/PLR은 중립 25%
#   혼입으로 하락하는 것이 정상이다 (7-5 검증 실측: EXPERIMENTS.md).
REFERENCE = {
    ("pgr_plr_ratio", "disposition_strength"): 0.36,
    ("n_buys", "overconfidence"): 0.37,
    ("oc_timing_corr", "overconfidence"): 0.34,
    ("mean_abn_vol_at_buy", "herd_sensitivity"): 0.19,
    ("mean_lott_at_buy", "lottery_preference"): 0.36,
}
# 하네스(kcmi_metrics) 풀드 처분 참조값 — 기초보유 제외 규칙이 양쪽 동일하므로
# 빌더의 풀드 PGR/PLR 비율은 이 값과 거의 일치해야 한다 (시드 7, 7-2 확정 설정).
HARNESS_DISP_REF = 2.187


def main(csv_path: str, labels_path: str | None = None):
    trades, labels = load_trades_csv(csv_path)
    if labels is None:
        # 7-4 패키징 이후: 라벨은 trades에 없고 별도 labels.csv에 있다
        lp = labels_path or config.LABELS_CSV_PATH
        if os.path.exists(lp):
            labels = pd.read_csv(lp, dtype={"agent_id": str}).set_index("agent_id")
            print(f"라벨 소스: {lp}")
        else:
            sys.exit("라벨 없음 — trades의 편향라벨 컬럼 또는 "
                     f"{lp}가 필요합니다(합성 데이터 전용 테스트).")
    print(f"거래 {len(trades):,}건, 계좌 {trades['agent_id'].nunique():,}개")

    price_df = get_price_data(config.UNIVERSE_TICKERS)
    index_df = get_index_data()
    out = build_features(trades, price_df, index_df, windows=(None, 63, 21),
                         lott_table=load_lott_table(config.LOTT_TABLE_PATH))
    agg = out["aggregates"]

    # (1) 하네스 교차검증: 풀드 PGR/PLR
    full = agg[agg["window"] == "full"].set_index("agent_id")
    pooled = (full["gs"].sum() / full["go"].sum()) / (full["ls"].sum() / full["lo"].sum())
    dev = pooled / HARNESS_DISP_REF - 1.0
    print(f"\n[교차검증] 풀드 PGR/PLR: {pooled:.3f}  (하네스 {HARNESS_DISP_REF}, "
          f"편차 {dev * 100:+.1f}% — 기초보유 제외 규칙 동일하므로 ~0% 기대)")

    # (2) 스모크 rho (full 창, disp는 valid 계좌만)
    joined = full.join(labels)
    print("\n[스모크 rho] (기준값 대비 — 목표 아님, 회귀 감지용)")
    for (feat, lab), ref in REFERENCE.items():
        sub = joined[joined["disp_valid"]] if feat == "pgr_plr_ratio" else joined
        rho = sub[feat].corr(sub[lab], method="spearman")
        flag = "" if rho >= ref - 0.08 else "  << 회귀 의심"
        print(f"  {feat} x {lab}: {rho:.3f}  (기준 {ref}){flag}")

    # (3) 관측창별 유효성
    print("\n[관측창별 유효 계좌] (disp_valid 통과 / 전체)")
    for w in ("full", "63d", "21d"):
        sub = agg[agg["window"] == w]
        print(f"  {w:>4}: {int(sub['disp_valid'].sum()):,} / {len(sub):,}")


if __name__ == "__main__":
    main(
        sys.argv[1] if len(sys.argv) > 1 else config.OUTPUT_CSV_PATH,
        sys.argv[2] if len(sys.argv) > 2 else None,
    )
