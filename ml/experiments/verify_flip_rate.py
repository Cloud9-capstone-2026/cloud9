"""
단계 0 실험 A — 처분 플립률 검증 (하드 게이트, 사전 등록 기준 고정분).

실행: python -m ml.experiments.verify_flip_rate   (레포 루트에서)

질문: attr_disposition ≥ 0.5로 "처분효과(이익 실현) 때문"이라 귀속된 매도 중,
실제로는 손실 매도인 모순 건("플립")이 얼마나 되는가.

정의 고정(2026-07-30 계획서 승인분):
- 플립 = attr_disposition ≥ 0.5 매도 중 실현수익률 < 0.
  실현수익률은 재구현하지 않고 features.build_features의 return_at_sale
  (거래단가/평균단가 − 1, 세금·수수료 제외)을 그대로 사용 — 피처와 정의 동일을
  구현 공유로 보장. basis 미상(원가 확인 불가) 매도는 모집단에서 제외하고 건수 병기.
- 데이터 = 평가 시드 s101·s102 각각 + 풀링.
- 통과 = 플립률 Wilson 95% CI 상한이 시드별·풀링 모두 5% 미만.
- 조건부 수용 = 풀링 플립률 5~15%이면서 플립의 70% 이상이 저귀속(attr < 0.6) 구간.
- 재검토 = 그 외 (15% 초과 또는 고귀속 만연) → 전면 중단·재계획.

정합성 전제(보완 1번): trade_labels는 trades와 행 순서 1:1 — 실행 전에
(agent_id, 거래일자, 거래구분) 세 컬럼의 행 단위 완전 일치를 assert.
"""

import json
import math
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

_REPO = str(Path(__file__).resolve().parents[2])  # ml/experiments/ → 레포 루트
sys.path.insert(0, _REPO)

from synthetic_data import config  # noqa: E402
from synthetic_data.features import load_trades_csv  # noqa: E402
from ml.seqfeat import attach_trade_rows  # noqa: E402

CACHE_DIR = os.path.join(_REPO, "ml", "cache")
EVAL_SETS = ["eval_natural_s103", "eval_natural_s104"]  # 0730 시드 교체 (봉인 복원)
ATTR_THRESHOLD = 0.5  # 귀속 판정 경계 (캘리브레이션 τ와 동일 값)
LOW_ATTR = 0.6        # 조건부 수용의 "저귀속" 경계
CI_Z = 1.959963984540054  # 95%


def wilson_ci(k: int, n: int) -> tuple[float, float]:
    """이항 비율 Wilson 95% CI. n=0이면 (nan, nan)."""
    if n == 0:
        return float("nan"), float("nan")
    p = k / n
    z2 = CI_Z * CI_Z
    denom = 1.0 + z2 / n
    center = (p + z2 / (2 * n)) / denom
    half = CI_Z * math.sqrt(p * (1 - p) / n + z2 / (4 * n * n)) / denom
    return center - half, center + half


def assert_label_alignment(name: str) -> pd.DataFrame:
    """trades·trade_labels 행 1:1 정합 assert 후 라벨 프레임 반환 (원본 CSV 문자열 비교)."""
    raw_trades = pd.read_csv(config.dataset_path(name, "trades"), dtype=str)
    labels = pd.read_csv(config.dataset_path(name, "trade_labels"), dtype=str)
    if len(raw_trades) != len(labels):
        raise AssertionError(
            f"{name}: 행 수 불일치 trades={len(raw_trades)} labels={len(labels)}")
    for col in ("agent_id", "거래일자", "거래구분"):
        same = (raw_trades[col].to_numpy() == labels[col].to_numpy())
        if not same.all():
            bad = int(np.argmax(~same))
            raise AssertionError(
                f"{name}: {col} 행 {bad} 불일치 "
                f"(trades={raw_trades[col].iat[bad]!r}, labels={labels[col].iat[bad]!r})")
    for col in ("attr_disposition", "attr_overconfidence", "attr_lottery", "attr_herd"):
        labels[col] = pd.to_numeric(labels[col])
    return labels


def analyze_one(name: str) -> dict:
    labels = assert_label_alignment(name)
    trades, _ = load_trades_csv(config.dataset_path(name, "trades"))

    ev_path = os.path.join(CACHE_DIR, f"{name}_events.parquet")
    if not os.path.exists(ev_path):
        raise FileNotFoundError(f"{ev_path} 없음 — 먼저 python -m ml.train.prepare 실행")
    events = pd.read_parquet(ev_path)
    events = attach_trade_rows(events, trades)  # 길이 불일치 시 여기서 ValueError

    sells = events[events["거래구분"] == "매도"].copy()
    sells["attr_disp"] = labels["attr_disposition"].to_numpy()[sells["_trade_row"].to_numpy()]
    # 교차 검증: 라벨 쪽 거래구분도 매도여야 함 (행 사상 자체의 무결성 확인)
    lab_side = labels["거래구분"].to_numpy()[sells["_trade_row"].to_numpy()]
    assert (lab_side == "매도").all(), "행 사상 오류 — events 매도가 labels 매도와 불일치"

    pop = sells[sells["attr_disp"] >= ATTR_THRESHOLD]
    known = pop[pop["return_at_sale"].notna()]
    flips = known[known["return_at_sale"] < 0]

    k, n = len(flips), len(known)
    lo, hi = wilson_ci(k, n)
    out = {
        "name": name,
        "n_sells": len(sells),
        "n_attr_ge_05": len(pop),
        "n_basis_unknown": int(len(pop) - n),
        "n_known": n,
        "n_flips": k,
        "flip_rate": k / n if n else float("nan"),
        "ci_low": lo,
        "ci_high": hi,
        "flip_attr_mean": float(flips["attr_disp"].mean()) if k else None,
        "flip_attr_median": float(flips["attr_disp"].median()) if k else None,
        "flip_attr_lt06_share": float((flips["attr_disp"] < LOW_ATTR).mean()) if k else None,
        "flip_ras_mean": float(flips["return_at_sale"].mean()) if k else None,
    }
    return out


def main():
    results = [analyze_one(name) for name in EVAL_SETS]

    pooled_k = sum(r["n_flips"] for r in results)
    pooled_n = sum(r["n_known"] for r in results)
    lo, hi = wilson_ci(pooled_k, pooled_n)
    pooled = {
        "name": "pooled",
        "n_attr_ge_05": sum(r["n_attr_ge_05"] for r in results),
        "n_basis_unknown": sum(r["n_basis_unknown"] for r in results),
        "n_known": pooled_n,
        "n_flips": pooled_k,
        "flip_rate": pooled_k / pooled_n if pooled_n else float("nan"),
        "ci_low": lo,
        "ci_high": hi,
    }
    # 풀링 저귀속 비중 = 시드별 플립 건수 가중 평균
    if pooled_k:
        pooled["flip_attr_lt06_share"] = float(
            sum((r["flip_attr_lt06_share"] or 0.0) * r["n_flips"] for r in results)
            / pooled_k
        )
    else:
        pooled["flip_attr_lt06_share"] = None

    all_rows = results + [pooled]
    print("\n=== 실험 A: 처분 플립률 (attr >= 0.5 매도 중 실현수익률 < 0) ===")
    print(f"{'세트':<22}{'귀속매도':>8}{'원가미상':>8}{'모집단':>8}{'플립':>6}"
          f"{'플립률':>9}{'CI하한':>9}{'CI상한':>9}{'attr<0.6':>9}")
    for r in all_rows:
        share = r.get("flip_attr_lt06_share")
        print(f"{r['name']:<22}{r['n_attr_ge_05']:>8}{r['n_basis_unknown']:>8}"
              f"{r['n_known']:>8}{r['n_flips']:>6}"
              f"{r['flip_rate']*100:>8.3f}%{r['ci_low']*100:>8.3f}%{r['ci_high']*100:>8.3f}%"
              f"{(share*100 if share is not None else float('nan')):>8.1f}%")

    uppers = [r["ci_high"] for r in all_rows]
    if all(u < 0.05 for u in uppers):
        verdict = "통과 — 전 CI 상한 < 5%"
    elif pooled["flip_rate"] <= 0.15 and (pooled["flip_attr_lt06_share"] or 0) >= 0.70:
        verdict = "조건부 수용 — 5~15% & 저귀속(attr<0.6) 70%+ 집중 (유형 C 문서화 필요)"
    else:
        verdict = "재검토 — 사전 기준 초과 (전면 중단·재계획)"
    print(f"\n판정: {verdict}")

    out_path = os.path.join(CACHE_DIR, "verify_flip_rate.json")
    with open(out_path, "w", encoding="utf-8") as fp:
        json.dump({"results": all_rows, "verdict": verdict,
                   "attr_threshold": ATTR_THRESHOLD, "low_attr": LOW_ATTR},
                  fp, ensure_ascii=False, indent=2)
    print(f"결과 저장: {out_path}")


if __name__ == "__main__":
    main()
