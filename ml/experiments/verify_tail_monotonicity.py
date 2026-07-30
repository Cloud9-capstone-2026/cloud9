"""
단계 0 실험 B — 확장 꼬리 단조성 검증 (하드 게이트, 사전 등록 기준 고정분).

실행: python -m ml.experiments.verify_tail_monotonicity   (레포 루트에서)

질문: 편향 강도를 극단까지 키운 확장 데이터(train_extended s11~s23)에서,
채널별 tail 성분 계좌의 "라벨이 셀수록 실제 행동 지표도 세지는가".

정의 고정(2026-07-30 계획서 승인분):
- 대상 = 채널별로 meta 모드_<파라미터> == 'tail'인 계좌만(5시드 풀링).
- 행동지표(피처/집계 코드 재사용 — aggregates parquet, full 윈도):
    처분    : pgr_plr_ratio (disp_valid 통과 계좌만)
    과잉확신: (상승일 매수÷상승일수) / 그 값 + (비상승일 매수÷비상승일수) — 등록
              지표 '상승일 일평균÷비상승일 일평균'의 유계 단조 변환(순위 동치,
              분모 0으로 인한 무한대 회피용 구현 세부). 상승일 = 전일 지수수익률>0
              (생성기 부스트 게이트와 동일 정의), 노출일수는 계좌 진입일부터 계산.
    복권    : mean_lott_at_buy (매수 있는 계좌만)
    군집    : mean_abn_vol_at_buy (매수 있는 계좌만)
- 판정 1 = 꼬리 라벨 4분위 그룹의 지표 평균 단조 비감소.
  허용: 인접 역전 1건, 크기 < 결합 표준오차 sqrt(SE_i^2 + SE_{i+1}^2).
- 판정 2 = 부분 순위상관: 지표·라벨을 랭크 변환 후 [나머지 3개 편향 라벨 +
  인구통계 4축 더미 + log(1+거래수) + 시드 더미]로 각각 OLS 잔차화, 잔차 상관이
  양(+)이고 p < 0.05.
- 통과 = 채널별로 판정 1·2 모두 만족. 미통과 채널은 ceteris-paribus 재실험으로.
"""

import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

_REPO = str(Path(__file__).resolve().parents[2])
sys.path.insert(0, _REPO)

from synthetic_data import config  # noqa: E402
from synthetic_data.market_data import get_index_data  # noqa: E402

CACHE_DIR = os.path.join(_REPO, "ml", "cache")
TRAIN_SETS = [f"train_extended_s{s}" for s in config.DATASET_TRAIN_SEEDS]
PARAMS = ["disposition_strength", "overconfidence", "lottery_preference",
          "herd_sensitivity"]
DEMO_AXES = ["신규여부", "성별", "연령", "자산"]


def _up_day_calendar() -> pd.DataFrame:
    """거래일별 상승 여부(전일 지수수익률>0 — 생성기 부스트 게이트와 동일)."""
    idx = get_index_data().sort_values("거래일자").reset_index(drop=True)
    idx["거래일자"] = pd.to_datetime(idx["거래일자"])
    driver = idx["종가"].pct_change().shift(1)  # d의 driver = d-1의 수익률
    cal = pd.DataFrame({"거래일자": idx["거래일자"], "is_up": (driver > 0)})
    lo = pd.to_datetime(config.SIM_START_DATE)
    hi = pd.to_datetime(config.SIM_END_DATE)
    return cal[(cal["거래일자"] >= lo) & (cal["거래일자"] <= hi)].reset_index(drop=True)


def _oc_metric(events: pd.DataFrame, meta: pd.DataFrame, cal: pd.DataFrame) -> pd.Series:
    """계좌별 과잉확신 지표(유계형): (상승일 일평균 매수)/(상승+비상승 일평균 합)."""
    buys = events[events["거래구분"] == "매수"].copy()
    buys["거래일자"] = pd.to_datetime(buys["거래일자"])
    up_days = set(cal.loc[cal["is_up"], "거래일자"])
    buys["on_up"] = buys["거래일자"].isin(up_days)
    b = buys.groupby("agent_id")["on_up"].agg(b_up="sum", b_all="count")
    b["b_non"] = b["b_all"] - b["b_up"]

    entry = pd.to_datetime(meta.set_index("agent_id")["진입일"])
    days = cal["거래일자"].to_numpy()
    ups = cal["is_up"].to_numpy()
    n_up_after = pd.Series(
        [(ups & (days >= e)).sum() for e in entry], index=entry.index)
    n_non_after = pd.Series(
        [((~ups) & (days >= e)).sum() for e in entry], index=entry.index)

    df = b.join(n_up_after.rename("n_up")).join(n_non_after.rename("n_non"))
    df = df[(df["n_up"] > 0) & (df["n_non"] > 0) & (df["b_all"] > 0)]
    r_up = df["b_up"] / df["n_up"]
    r_non = df["b_non"] / df["n_non"]
    return (r_up / (r_up + r_non)).rename("metric")  # 등록 비율의 유계 단조 변환


def load_channel_frames() -> pd.DataFrame:
    """5시드 풀링: 계좌별 [라벨 4종, 지표 4종, 인구통계, log거래수, 시드]."""
    cal = _up_day_calendar()
    rows = []
    for name in TRAIN_SETS:
        seed = name.rsplit("_s", 1)[1]
        labels = pd.read_csv(config.dataset_path(name, "labels"),
                             dtype={"agent_id": str}).set_index("agent_id")
        meta = pd.read_csv(config.dataset_path(name, "meta"), dtype={"agent_id": str})
        ag = pd.read_parquet(
            os.path.join(CACHE_DIR, f"{name}_aggregates.parquet"))
        ag["agent_id"] = ag["agent_id"].astype(str)
        ag = ag[ag["window"] == "full"].set_index("agent_id")
        events = pd.read_parquet(os.path.join(CACHE_DIR, f"{name}_events.parquet"))
        events["agent_id"] = events["agent_id"].astype(str)

        df = labels[PARAMS].copy()
        df["metric_disposition_strength"] = ag["pgr_plr_ratio"].where(ag["disp_valid"])
        df["metric_lottery_preference"] = ag["mean_lott_at_buy"].where(ag["n_buys"] > 0)
        df["metric_herd_sensitivity"] = ag["mean_abn_vol_at_buy"].where(ag["n_buys"] > 0)
        df["metric_overconfidence"] = _oc_metric(events, meta, cal)
        df["n_trades"] = (ag["n_buys"].fillna(0) + ag["n_sells"].fillna(0))
        m = meta.set_index("agent_id")
        for ax in DEMO_AXES:
            df[ax] = m[ax]
        for p in PARAMS:
            df[f"모드_{p}"] = m[f"모드_{p}"]
        df["seed"] = seed
        rows.append(df.reset_index())
    return pd.concat(rows, ignore_index=True)


def check_monotonic(x: pd.Series, y: pd.Series):
    """판정 1: x 4분위 그룹별 y 평균 단조 비감소 (허용 역전 1건 & < 결합 SE)."""
    q = pd.qcut(x, 4, labels=False, duplicates="drop")
    g = y.groupby(q)
    means, ses, ns = g.mean(), g.sem(), g.size()
    drops = []
    for i in range(len(means) - 1):
        d = means.iloc[i + 1] - means.iloc[i]
        if d < 0:
            drops.append((i, float(d), float(np.hypot(ses.iloc[i], ses.iloc[i + 1]))))
    ok = (len(drops) == 0) or (len(drops) == 1 and abs(drops[0][1]) < drops[0][2])
    return ok, means.tolist(), ses.tolist(), ns.tolist(), drops


def partial_rank_corr(df: pd.DataFrame, param: str):
    """판정 2: 랭크 변환 후 통제변수 OLS 잔차 상관 + p값."""
    others = [p for p in PARAMS if p != param]
    ctrl = pd.get_dummies(
        df[DEMO_AXES + ["seed"]].astype(str), drop_first=True).astype(float)
    ctrl["log_n_trades"] = np.log1p(df["n_trades"].astype(float))
    for p in others:
        ctrl[f"rank_{p}"] = df[p].rank()
    X = np.column_stack([np.ones(len(df)), ctrl.to_numpy(dtype=float)])
    def resid(v):
        beta, *_ = np.linalg.lstsq(X, v, rcond=None)
        return v - X @ beta
    rx = resid(df[param].rank().to_numpy(dtype=float))
    ry = resid(df[f"metric_{param}"].rank().to_numpy(dtype=float))
    r, _ = stats.pearsonr(rx, ry)
    dof = len(df) - X.shape[1] - 2
    t = r * np.sqrt(dof / (1 - r * r))
    p_two = 2 * stats.t.sf(abs(t), dof)
    return float(r), float(p_two), int(len(df))


def main():
    pooled = load_channel_frames()
    out, all_pass = {}, True
    print("\n=== 실험 B: 확장 꼬리 단조성 (tail 성분 계좌, 5시드 풀링) ===")
    for param in PARAMS:
        sub = pooled[(pooled[f"모드_{param}"] == "tail")
                     & pooled[f"metric_{param}"].notna()].copy()
        ok1, means, ses, ns, drops = check_monotonic(sub[param], sub[f"metric_{param}"])
        r, p, n = partial_rank_corr(sub, param)
        ok2 = (r > 0) and (p < 0.05)
        verdict = "통과" if (ok1 and ok2) else "미통과"
        all_pass &= (ok1 and ok2)
        out[param] = {
            "n_tail_accounts": n, "quartile_means": [round(v, 4) for v in means],
            "quartile_ns": ns, "inversions": drops, "mono_ok": ok1,
            "partial_rank_r": round(r, 4), "p_two_sided": float(f"{p:.3g}"),
            "corr_ok": ok2, "verdict": verdict,
        }
        q = " → ".join(f"{v:.3f}" for v in means)
        print(f"\n[{param}] tail 계좌 {n:,}")
        print(f"  4분위 지표 평균: {q}  (역전 {len(drops)}건)  판정1 {'OK' if ok1 else 'FAIL'}")
        print(f"  부분 순위상관 r={r:+.4f}  p={p:.3g}  판정2 {'OK' if ok2 else 'FAIL'}  → {verdict}")

    print(f"\n종합: {'전 채널 통과' if all_pass else '미통과 채널 존재 — ceteris-paribus 재실험 경로'}")
    out_path = os.path.join(CACHE_DIR, "verify_tail_monotonicity.json")
    with open(out_path, "w", encoding="utf-8") as fp:
        json.dump(out, fp, ensure_ascii=False, indent=2)
    print(f"결과 저장: {out_path}")


if __name__ == "__main__":
    main()
