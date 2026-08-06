"""
앙상블 가중치·임계값 캘리브레이션 (PROCESS.md 2026-07-25 계획 승인분).

실행: python -m ml.experiments.calibrate_ensemble            # 1~3단계 (튜닝 s11·s13)
      python -m ml.experiments.calibrate_ensemble --eval W1 W2 W3 THETA   # 4단계 (평가 시드 1회)

경계(승인된 계획 그대로): 합성 정답은 '편향 거래'만 정의하므로 이 실험의 산출은
**편향 탐지 관점의 최적 가중**이다. rule/stat 가중이 낮게 나와도 두 계층의 존재
가치(명백 위반·비편향 이상치) 부정의 근거가 아니다 — 그 가치는 이 정답에 없다.

정답 정의: y = [4개 편향 귀속확률의 최댓값 ≥ τ], τ=0.5.
  최댓값 근거: 제품 판정 문장("이 거래는 X 편향 때문일 수도")이 개별 편향 단위
  주장이므로 OR 의미론이 맞다. 합산은 발생(과잉확신)과 선택(복권·군집)이라는
  다른 인과 단계의 이중계상. 감도분석: τ∈{0.3,0.7} + noisy-OR(1−Π(1−pᵢ)) 병행.

2계층 baseline: 계좌 이력 전반부(시간순)/후반부 분할 — 유형 C 근사(단기 안정
가정, 실서비스의 오래된 baseline 대비 낙관적). baseline<10행 계좌는 zscore 기본
통계 폴백(첫 업로드 시나리오) — 그 비율을 함께 보고.

전제: 세 계층 정의 동결 상태(1계층 v1 R1+R2, 2계층 현행, 3계층 확정 태거).
계층 정의 변경 시 이 캘리브레이션은 무효 — 재실행 필요.
"""

import json
import os
import sys

import numpy as np
import pandas as pd
import torch
from sklearn.metrics import average_precision_score, precision_recall_curve

from pathlib import Path

_REPO = str(Path(__file__).resolve().parents[2])  # ml/experiments/ → 레포 루트
sys.path.insert(0, os.path.join(_REPO, "backend"))  # models.rule_based / models.zscore

from synthetic_data import config  # noqa: E402
from ..gru_model import GRUTagger  # noqa: E402
from ..train.train_tagger import ATTRS, _load_set, _to_tensors  # noqa: E402

from models.rule_based import run_rule_based  # noqa: E402
from models.zscore import run_zscore  # noqa: E402

CACHE_DIR = os.path.join("ml", "cache")
ART_DIR = os.path.join("ml", "artifacts")
TUNE_SETS = ["train_extended_s11", "train_extended_s13"]
EVAL_SETS = ["eval_natural_s101", "eval_natural_s102"]
TAU = 0.5
BATCH = 256
AXIS_FLOOR = 0.3  # 최약축 재현율 하한 (보정 후보용)


def _load_tagger():
    with open(os.path.join(ART_DIR, "tagger_meta.json"), encoding="utf-8") as fp:
        meta = json.load(fp)
    m = meta["model"]
    model = GRUTagger(m["n_channels"], m["hidden"], m["layers"], len(meta["attrs"]),
                      dropout=m.get("dropout", 0.0))
    model.load_state_dict(
        torch.load(os.path.join(ART_DIR, "tagger.pt"), map_location="cpu"))
    model.eval()
    return model, meta


def build_table(name: str, model, meta, force: bool = False) -> pd.DataFrame:
    """세트 → 거래별 (rule, stat, lstm, 귀속 4종) 점수 테이블. parquet 캐싱."""
    path = os.path.join(CACHE_DIR, f"ensemble_scores_{name}.parquet")
    if os.path.exists(path) and not force:
        return pd.read_parquet(path)

    # 3계층: 배포 아티팩트 태거 일괄 배치 (실서비스와 동일 값)
    feat, attr_mat, _side = _load_set(name)
    ids, X, L, rows, _Y, _M = _to_tensors(feat, attr_mat, meta["norm_stats"], meta["max_len"])
    lstm = np.full(len(attr_mat), np.nan, dtype="float32")
    with torch.no_grad():
        for b in range(0, len(ids), BATCH):
            P = torch.sigmoid(model(torch.from_numpy(X[b:b+BATCH]),
                                    torch.from_numpy(L[b:b+BATCH]))).numpy()
            r = rows[b:b+BATCH]
            v = r >= 0
            lstm[r[v]] = P[v].max(axis=-1)

    # 1·2계층: 표준 컬럼 변환 후 계좌별 전/후반 분할 채점
    tr = pd.read_csv(config.dataset_path(name, "trades"))
    std = pd.DataFrame({
        "날짜": pd.to_datetime(tr["거래일자"]),
        "종목명": tr["종목코드"].astype(str),
        "매매구분": tr["거래구분"],
        "체결수량": tr["거래수량"],
        "체결단가": tr["거래단가"],
        "총거래금액": tr["거래금액"],
    })
    rule = np.full(len(tr), np.nan, dtype="float32")
    stat = np.full(len(tr), np.nan, dtype="float32")
    n_acc = small_base = 0
    for _aid, g in std.groupby(tr["agent_id"].to_numpy(), sort=False):
        n = len(g)
        if n < 2:
            continue
        n_acc += 1
        half = n // 2
        if half < 10:
            small_base += 1  # zscore 기본 통계 폴백 (첫 업로드 시나리오)
        base, new = g.iloc[:half], g.iloc[half:]
        rr = run_rule_based(new)
        sr = run_zscore(new, base)
        for k, ridx in enumerate(g.index[half:]):
            rule[ridx] = rr["trade_results"][k]["rule_score"]
            stat[ridx] = sr["trade_results"][k]["stat_score"]

    tbl = pd.DataFrame({
        "trade_row": np.arange(len(tr)),
        "agent_id": tr["agent_id"].astype(str),
        "side": tr["거래구분"],
        "rule": rule, "stat": stat, "lstm": lstm,
    })
    for j, a in enumerate(ATTRS):
        tbl[a] = attr_mat[:, j]
    n_all = len(tbl)
    tbl = tbl.dropna(subset=["rule", "stat", "lstm"]).reset_index(drop=True)
    print(f"{name}: 채점 {len(tbl):,}/{n_all:,}행 (후반부∩시퀀스창; "
          f"baseline<10행 계좌 {small_base:,}/{n_acc:,})", flush=True)
    tbl.to_parquet(path, index=False)
    return tbl


def _labels(tbl: pd.DataFrame, tau: float = TAU) -> np.ndarray:
    return (tbl[ATTRS].max(axis=1) >= tau).to_numpy()


def sweep_weights(tbl: pd.DataFrame):
    """심플렉스 0.05 격자 231조합 — AP(임계값 무관) 순위."""
    y = _labels(tbl)
    S = tbl[["rule", "stat", "lstm"]].to_numpy(dtype="float64")
    print(f"\n양성(편향 거래) 비율: {y.mean() * 100:.1f}%  (n={len(y):,})")
    res = []
    for w1 in np.round(np.arange(0, 1.0001, 0.05), 2):
        for w2 in np.round(np.arange(0, 1.0001 - w1, 0.05), 2):
            w3 = round(1 - w1 - w2, 2)
            ap = average_precision_score(y, S @ np.array([w1, w2, w3]))
            res.append((ap, w1, w2, w3))
    res.sort(reverse=True)

    def _ap_of(w1, w2, w3):
        return next(ap for ap, a, b, c in res if (a, b, c) == (w1, w2, w3))

    print("\n=== 가중치 AP 상위 10 (rule/stat/lstm) ===")
    for ap, w1, w2, w3 in res[:10]:
        print(f"  AP {ap:.4f}  ({w1:.2f}, {w2:.2f}, {w3:.2f})")
    print("=== 참조점 ===")
    print(f"  lstm 단독 (0,0,1)      AP {_ap_of(0, 0, 1.0):.4f}")
    print(f"  현행 (0.3,0.3,0.4)     AP {_ap_of(0.3, 0.3, 0.4):.4f}")
    print(f"  rule 단독 (1,0,0)      AP {_ap_of(1.0, 0, 0):.4f}")
    print(f"  stat 단독 (0,1,0)      AP {_ap_of(0, 1.0, 0):.4f}")
    return res, y, S


def threshold_candidates(tbl, y, S, w):
    """확정 가중에 대한 θ 후보표: F1최대 / 플래그 5% / 10% / 최약축 하한 보정."""
    f = S @ np.asarray(w)
    prec, rec, thr = precision_recall_curve(y, f)
    f1 = 2 * prec[:-1] * rec[:-1] / np.clip(prec[:-1] + rec[:-1], 1e-12, None)
    cands = {
        "F1최대": float(thr[int(np.nanargmax(f1))]),
        "플래그5%": float(np.quantile(f, 0.95)),
        "플래그10%": float(np.quantile(f, 0.90)),
    }
    axis_pos = {a: (tbl[a] >= TAU).to_numpy() for a in ATTRS}

    def _axis_recalls(flag):
        return {a: (float((flag & p).sum() / p.sum()) if p.sum() else float("nan"))
                for a, p in axis_pos.items()}

    # 최약축 보정: 모든 축 재현율 ≥ AXIS_FLOOR 를 만족하는 가장 높은 θ
    qs = np.quantile(f, np.linspace(0.5, 0.999, 200))
    th_floor = None
    for th in sorted(qs, reverse=True):
        if min(_axis_recalls(f > th).values()) >= AXIS_FLOOR:
            th_floor = float(th)
            break
    if th_floor is not None:
        cands[f"최약축≥{AXIS_FLOOR}"] = th_floor

    print(f"\n=== 임계값 후보표 (가중치 {tuple(round(x, 2) for x in w)}, τ={TAU}) ===")
    header = f"  {'후보':<10} {'θ':>7} {'정밀도':>7} {'재현율':>7} {'플래그율':>8}"
    header += "".join(f" {a.replace('attr_', 'R:'):>8}" for a in ATTRS)
    print(header)
    out = {}
    for nm, th in cands.items():
        flag = f > th
        p = float(y[flag].mean()) if flag.any() else float("nan")
        r = float(flag[y].mean()) if y.any() else float("nan")
        ar = _axis_recalls(flag)
        out[nm] = {"theta": round(th, 4), "precision": round(p, 3),
                   "recall": round(r, 3), "flag_rate": round(float(flag.mean()), 4),
                   "axis_recall": {a: round(v, 3) for a, v in ar.items()}}
        print(f"  {nm:<10} {th:>7.4f} {p:>7.3f} {r:>7.3f} {flag.mean() * 100:>7.1f}%"
              + "".join(f" {ar[a]:>8.3f}" for a in ATTRS))
    return out


def sensitivity(tbl, S, w_best):
    """정답 정의 감도: τ {0.3,0.5,0.7} × 최댓값/noisy-OR — AP(최적 w vs lstm 단독)."""
    mx = tbl[ATTRS].max(axis=1).to_numpy()
    noisy = 1 - np.prod(1 - tbl[ATTRS].to_numpy(), axis=1)
    defs = {f"max≥{t}": mx >= t for t in (0.3, 0.5, 0.7)}
    defs["noisyOR≥0.5"] = noisy >= 0.5
    print("\n=== 정답 정의 감도분석 ===")
    print(f"  {'정의':<12} {'양성율':>7} {'AP(최적w)':>10} {'AP(lstm단독)':>12}")
    for nm, yv in defs.items():
        ap_b = average_precision_score(yv, S @ np.asarray(w_best))
        ap_l = average_precision_score(yv, S @ np.array([0, 0, 1.0]))
        print(f"  {nm:<12} {yv.mean() * 100:>6.1f}% {ap_b:>10.4f} {ap_l:>12.4f}")


def main():
    model, meta = _load_tagger()
    if "--eval" in sys.argv:  # 4단계: θ 결정 후 봉인 시드 1회 검증
        i = sys.argv.index("--eval")
        w = [float(x) for x in sys.argv[i + 1: i + 4]]
        theta = float(sys.argv[i + 4])
        print(f"[4단계] 가중치 {w}, θ={theta} — 평가 시드 최종 검증")
        for name in EVAL_SETS:
            tbl = build_table(name, model, meta)
            y = _labels(tbl)
            f = tbl[["rule", "stat", "lstm"]].to_numpy() @ np.asarray(w)
            flag = f > theta
            ar = {a: float((flag & (tbl[a] >= TAU)).sum() / max((tbl[a] >= TAU).sum(), 1))
                  for a in ATTRS}
            print(f"  {name}: 정밀도 {float(y[flag].mean()):.3f} / "
                  f"재현율 {float(flag[y].mean()):.3f} / 플래그율 {flag.mean() * 100:.1f}%"
                  f" / 축별 재현율 " + ", ".join(f"{a.replace('attr_', '')} {v:.3f}"
                                            for a, v in ar.items()))
        return

    tables = [build_table(name, model, meta) for name in TUNE_SETS]
    tbl = pd.concat(tables, ignore_index=True)
    res, y, S = sweep_weights(tbl)
    w_best = list(res[0][1:])
    threshold_candidates(tbl, y, S, w_best)
    if tuple(w_best) != (0.3, 0.3, 0.4):  # 현행 가중 비교표 (참고)
        threshold_candidates(tbl, y, S, [0.3, 0.3, 0.4])
    sensitivity(tbl, S, w_best)
    print("\nθ 후보표를 보고 최종 (가중치, θ) 결정 후: "
          "python -m ml.calibrate_ensemble --eval W1 W2 W3 THETA")


if __name__ == "__main__":
    main()
