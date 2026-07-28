"""
3계층 GRU 멀티태스크 회귀 학습 + GBDT 베이스라인 (최소 슬라이스 2단계).

실행: python -m ml.train.train_gru  (레포 최상위, ml.train.prepare 완료 후)
학습: train_extended s11~s23 (계좌 90/10 학습/검증 분할, 검증은 early stopping용)
평가: eval_natural s101·s102 (최종 평가 전용 — 학습·튜닝에 미사용)
타깃: 4개 편향 파라미터 (dataset/{name}_labels.csv)

같은 평가 세트에서 GBDT(HistGradientBoosting, aggregates full 창 입력) 베이스라인을
함께 학습·채점해 한 표로 출력한다 — GRU와의 차이 = 시퀀스 정보의 순수 기여분.
(베이스라인 논리: 집계 통계로 도달 가능한 상한선을 먼저 재고, 시퀀스 모델이
그걸 넘는지 본다. herd_sensitivity는 생성 신호 자체가 약해(스모크 rho 0.19~0.25)
낮게 나오는 것이 데이터 쪽에서 예정된 결과다 — DECISIONS.md §5.)

산출 (ml/artifacts/, .gitignore):
- model.pt   : GRU state_dict
- meta.json  : 피처 스펙·정규화 통계·라벨 변환·자연분포 백분위 그리드·평가 성능·
               데이터 버전(시드 목록). backend/models/layer3.py가 이 두 파일만 읽는다.
"""

import json
import os
import random
from datetime import datetime

import numpy as np
import pandas as pd
import torch
from scipy.stats import spearmanr
from sklearn.ensemble import HistGradientBoostingRegressor
from torch import nn

from synthetic_data import config
from .. import seqfeat
from ..gru_model import GRURegressor

CACHE_DIR = os.path.join("ml", "cache")
ART_DIR = os.path.join("ml", "artifacts")
SEED = 7

TARGETS = ["disposition_strength", "overconfidence", "lottery_preference", "herd_sensitivity"]
# 라벨 변환: disposition은 우왜도(log), 나머지는 원값 — 이후 학습 통계로 z-score.
LOG_TARGETS = {"disposition_strength"}

TRAIN_SETS = [f"train_extended_s{s}" for s in config.DATASET_TRAIN_SEEDS]
EVAL_SETS = [f"eval_natural_s{s}" for s in config.DATASET_EVAL_SEEDS]

# GBDT 베이스라인 입력에서 제외할 aggregates 컬럼 (식별자·창 라벨)
AGG_DROP = ["agent_id", "window"]

HIDDEN, LAYERS, BATCH, MAX_EPOCHS, PATIENCE, LR = 64, 1, 256, 100, 8, 1e-3
MAX_LEN_PCTL, MAX_LEN_CAP = 95, 256
VAL_FRAC = 0.1


def _load_set(name: str):
    ev = pd.read_parquet(os.path.join(CACHE_DIR, f"{name}_events.parquet"))
    labels = pd.read_csv(
        config.dataset_path(name, "labels"), dtype={"agent_id": str}
    ).set_index("agent_id")
    ag = pd.read_parquet(os.path.join(CACHE_DIR, f"{name}_aggregates.parquet"))
    return ev, labels, ag


def _transform_labels(labels: pd.DataFrame, stats: dict | None):
    """라벨 → (log 변환) → z-score. stats=None이면 fit(학습 세트)."""
    y = labels[TARGETS].astype(float).copy()
    for t in LOG_TARGETS:
        y[t] = np.log(y[t])
    if stats is None:
        stats = {t: {"mean": float(y[t].mean()), "std": float(y[t].std())} for t in TARGETS}
    for t in TARGETS:
        y[t] = (y[t] - stats[t]["mean"]) / stats[t]["std"]
    return y, stats


def _inverse_labels(z: np.ndarray, stats: dict) -> np.ndarray:
    out = np.empty_like(z)
    for j, t in enumerate(TARGETS):
        v = z[:, j] * stats[t]["std"] + stats[t]["mean"]
        out[:, j] = np.exp(v) if t in LOG_TARGETS else v
    return out


def _agg_matrix(ag: pd.DataFrame):
    """aggregates full 창 → (agent_ids, 수치 행렬). HistGBDT는 NaN 네이티브 처리."""
    full = ag[ag["window"] == "full"].copy()
    full["disp_valid"] = full["disp_valid"].astype(float)
    ids = full["agent_id"].astype(str).tolist()
    X = full.drop(columns=AGG_DROP).apply(pd.to_numeric, errors="coerce")
    X = X.replace([np.inf, -np.inf], np.nan)
    return ids, X.to_numpy(dtype="float64"), list(X.columns)


def _spearman_table(y_true: pd.DataFrame, y_pred: np.ndarray) -> dict:
    out = {}
    for j, t in enumerate(TARGETS):
        rho = spearmanr(y_true[t].to_numpy(), y_pred[:, j]).statistic
        mae = float(np.mean(np.abs(y_true[t].to_numpy() - y_pred[:, j])))
        out[t] = {"rho": round(float(rho), 3), "mae": round(mae, 4)}
    return out


def main():
    random.seed(SEED)
    np.random.seed(SEED)
    torch.manual_seed(SEED)
    os.makedirs(ART_DIR, exist_ok=True)

    # ---- 학습 데이터 조립 -------------------------------------------------
    print("학습 세트 로드...", flush=True)
    feats, labels_all, agg_ids, agg_X, agg_cols = [], [], [], None, None
    agg_X_list = []
    for name in TRAIN_SETS:
        ev, labels, ag = _load_set(name)
        f = seqfeat.event_features(ev)
        f["agent_id"] = name + "/" + f["agent_id"]  # 시드 간 agent_id 충돌 방지
        labels.index = name + "/" + labels.index
        feats.append(f)
        labels_all.append(labels)
        ids, X, agg_cols = _agg_matrix(ag)
        agg_ids += [name + "/" + i for i in ids]
        agg_X_list.append(X)
    feat_train = pd.concat(feats, ignore_index=True)
    labels_train = pd.concat(labels_all)
    agg_X = np.vstack(agg_X_list)

    norm_stats = seqfeat.fit_norm_stats(feat_train)
    counts = feat_train.groupby("agent_id").size()
    max_len = int(min(np.percentile(counts, MAX_LEN_PCTL), MAX_LEN_CAP))
    print(f"시퀀스 길이: p{MAX_LEN_PCTL}={max_len} (계좌 {len(counts):,}, "
          f"중앙값 {int(counts.median())}건)", flush=True)

    ids, X, lengths = seqfeat.build_sequences(feat_train, norm_stats, max_len)
    y_df, label_stats = _transform_labels(labels_train.loc[ids], None)
    y = y_df.to_numpy(dtype="float32")

    # 계좌 단위 90/10 분할 (검증 = early stopping 전용)
    idx = np.arange(len(ids))
    rng = np.random.default_rng(SEED)
    rng.shuffle(idx)
    n_val = int(len(idx) * VAL_FRAC)
    vi, ti = idx[:n_val], idx[n_val:]
    print(f"학습 {len(ti):,} / 검증 {len(vi):,} 계좌 "
          f"(거래 없는 계좌 {len(labels_train) - len(ids)}개 제외)", flush=True)

    Xt = torch.from_numpy(X)
    Lt = torch.from_numpy(lengths)
    Yt = torch.from_numpy(y)

    # ---- GRU 학습 ---------------------------------------------------------
    model = GRURegressor(seqfeat.N_CHANNELS, HIDDEN, LAYERS, len(TARGETS))
    opt = torch.optim.Adam(model.parameters(), lr=LR)
    lossf = nn.MSELoss()

    def _eval_loss(sub):
        model.eval()
        with torch.no_grad():
            tot, n = 0.0, 0
            for b in range(0, len(sub), BATCH):
                s = sub[b : b + BATCH]
                p = model(Xt[s], Lt[s])
                tot += lossf(p, Yt[s]).item() * len(s)
                n += len(s)
        return tot / n

    best, best_state, bad = float("inf"), None, 0
    for epoch in range(1, MAX_EPOCHS + 1):
        model.train()
        rng.shuffle(ti)
        for b in range(0, len(ti), BATCH):
            s = ti[b : b + BATCH]
            opt.zero_grad()
            loss = lossf(model(Xt[s], Lt[s]), Yt[s])
            loss.backward()
            opt.step()
        vl = _eval_loss(vi)
        marker = ""
        if vl < best - 1e-4:
            best, best_state, bad = vl, {k: v.clone() for k, v in model.state_dict().items()}, 0
            marker = " *"
        else:
            bad += 1
        print(f"epoch {epoch:3d}  val_mse {vl:.4f}{marker}", flush=True)
        if bad >= PATIENCE:
            print(f"early stop (patience {PATIENCE})", flush=True)
            break
    model.load_state_dict(best_state)

    # ---- GBDT 베이스라인 학습 (aggregates full 창) -------------------------
    print("\nGBDT 베이스라인 학습...", flush=True)
    y_agg, _ = _transform_labels(labels_train.loc[agg_ids], label_stats)
    gbdts = {}
    for j, t in enumerate(TARGETS):
        g = HistGradientBoostingRegressor(random_state=SEED)
        g.fit(agg_X, y_agg[t].to_numpy())
        gbdts[t] = g

    # ---- 평가 (자연 시드 2개, 학습 미사용) ---------------------------------
    report = {}
    for name in EVAL_SETS:
        ev, labels, ag = _load_set(name)
        f = seqfeat.event_features(ev)
        e_ids, eX, eL = seqfeat.build_sequences(f, norm_stats, max_len)
        model.eval()
        with torch.no_grad():
            preds = []
            for b in range(0, len(e_ids), BATCH):
                preds.append(model(torch.from_numpy(eX[b:b+BATCH]),
                                   torch.from_numpy(eL[b:b+BATCH])).numpy())
        gru_pred = _inverse_labels(np.vstack(preds), label_stats)
        gru_tab = _spearman_table(labels.loc[e_ids], gru_pred)

        a_ids, aX, _ = _agg_matrix(ag)
        gz = np.column_stack([gbdts[t].predict(aX) for t in TARGETS])
        gbdt_pred = _inverse_labels(gz, label_stats)
        gbdt_tab = _spearman_table(labels.loc[a_ids], gbdt_pred)

        report[name] = {"gru": gru_tab, "gbdt": gbdt_tab,
                        "n_gru": len(e_ids), "n_gbdt": len(a_ids)}
        print(f"\n[{name}]  (GRU n={len(e_ids):,} / GBDT n={len(a_ids):,})")
        print(f"  {'타깃':<22} {'GRU rho':>8} {'GBDT rho':>9} {'GRU mae':>9} {'GBDT mae':>9}")
        for t in TARGETS:
            print(f"  {t:<22} {gru_tab[t]['rho']:>8} {gbdt_tab[t]['rho']:>9} "
                  f"{gru_tab[t]['mae']:>9} {gbdt_tab[t]['mae']:>9}")

    # ---- 아티팩트 저장 ----------------------------------------------------
    # 자연분포 백분위 그리드: 커밋본 canonical 자연 라벨(시드 7)의 quantile 0..100 —
    # layer3가 예측치 → 백분위(0~1) 변환에 사용. lstm_score = 4개 백분위의 최댓값.
    nat = pd.read_csv(config.LABELS_CSV_PATH)
    pct_grid = {
        t: [float(v) for v in np.quantile(nat[t].astype(float), np.linspace(0, 1, 101))]
        for t in TARGETS
    }

    torch.save(model.state_dict(), os.path.join(ART_DIR, "model.pt"))
    meta = {
        "created": datetime.now().isoformat(timespec="seconds"),
        "targets": TARGETS,
        "log_targets": sorted(LOG_TARGETS),
        "label_stats": label_stats,
        "norm_stats": norm_stats,
        "max_len": max_len,
        "model": {"hidden": HIDDEN, "layers": LAYERS,
                  "n_channels": seqfeat.N_CHANNELS},
        "train_sets": TRAIN_SETS,
        "eval_sets": EVAL_SETS,
        "val_mse": round(best, 4),
        "eval_report": report,
        "natural_percentile_grid": pct_grid,
    }
    with open(os.path.join(ART_DIR, "meta.json"), "w", encoding="utf-8") as fp:
        json.dump(meta, fp, ensure_ascii=False, indent=2)
    print(f"\n아티팩트 저장 → {ART_DIR}/model.pt, meta.json", flush=True)


if __name__ == "__main__":
    main()
