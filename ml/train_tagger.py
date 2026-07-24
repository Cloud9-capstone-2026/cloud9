"""
3계층 시퀀스 태깅 학습 (2단계): 거래별 인과 귀속 라벨 직접 학습.

실행: python -m ml.train_tagger  (레포 최상위, ml.prepare + trade_labels 재생성 후)
학습: train_extended s11~s23 / 검증: 계좌 10% / 평가: eval_natural s101·s102

타깃 = 생성기가 기록한 거래별 편향 귀속 확률(trade_labels 4컬럼, DECISIONS 2단계):
  attr_disposition   (매도) 1 − p₀/p₁ — 처분효과가 만든 초과 확률 귀속
  attr_overconfidence(매수) 1 − p₀/p₁ — 상승일 증폭 귀속
  attr_lottery/herd  (매수) 선택 가중의 성분 비중
모델 출력(sigmoid)이 곧 "이 거래가 그 편향 때문일 확률"의 추정 — 1단계 IG 프록시를
대체하는 지도학습 직접 추정이며, 출력 단위가 거래라 1·2계층과 정합.

평가: 편향별로 해당 거래 부분집합(처분=매도, 나머지=매수)에서 Spearman·AUC·MAE +
계좌 수준 sanity(거래 예측 평균 vs 계좌 라벨). trades는 바이트 불변이므로
ml/cache의 events를 재사용한다.

산출: ml/artifacts/tagger.pt + tagger_meta.json (backend/models/layer3.py가 읽음)
"""

import json
import os
import random
from datetime import datetime

import numpy as np
import pandas as pd
import torch
from scipy.stats import spearmanr
from torch import nn

from synthetic_data import config
from . import seqfeat
from .gru_model import GRUTagger

CACHE_DIR = os.path.join("ml", "cache")
ART_DIR = os.path.join("ml", "artifacts")
SEED = 7

ATTRS = ["attr_disposition", "attr_overconfidence", "attr_lottery", "attr_herd"]
# 편향별 유효 거래 부분집합(라벨이 정의되는 거래 종류)과 계좌 라벨 대응
ATTR_SIDE = {"attr_disposition": "매도", "attr_overconfidence": "매수",
             "attr_lottery": "매수", "attr_herd": "매수"}
ATTR_PARAM = {"attr_disposition": "disposition_strength",
              "attr_overconfidence": "overconfidence",
              "attr_lottery": "lottery_preference",
              "attr_herd": "herd_sensitivity"}

TRAIN_SETS = [f"train_extended_s{s}" for s in config.DATASET_TRAIN_SEEDS]
EVAL_SETS = [f"eval_natural_s{s}" for s in config.DATASET_EVAL_SEEDS]

HIDDEN, LAYERS, BATCH, MAX_EPOCHS, PATIENCE, LR = 64, 1, 256, 100, 8, 1e-3
MAX_LEN_PCTL, MAX_LEN_CAP = 95, 256
VAL_FRAC = 0.1


def _load_set(name: str, max_len: int, norm_stats: dict | None):
    """세트 → (feat|시퀀스 재료). norm_stats가 없으면 feat만 반환(통계 fit용)."""
    ev = pd.read_parquet(os.path.join(CACHE_DIR, f"{name}_events.parquet"))
    tr = pd.read_csv(config.dataset_path(name, "trades"))
    tl = pd.read_csv(config.dataset_path(name, "trade_labels"))
    assert len(ev) == len(tr) == len(tl), f"{name}: events/trades/trade_labels 행수 불일치"
    ev = seqfeat.attach_trade_rows(ev, tr)
    feat = seqfeat.event_features(ev)
    attr_mat = tl[ATTRS].to_numpy(dtype="float32")  # trades 행 순서
    side = tr["거래구분"].to_numpy()
    return feat, attr_mat, side


def _to_tensors(feat, attr_mat, norm_stats, max_len):
    ids, X, lengths, rows = seqfeat.build_sequences(
        feat, norm_stats, max_len, return_rows=True
    )
    valid = rows >= 0
    Y = np.zeros((*rows.shape, len(ATTRS)), dtype="float32")
    Y[valid] = attr_mat[rows[valid]]
    return ids, X, lengths, rows, Y, valid.astype("float32")


def main():
    random.seed(SEED)
    np.random.seed(SEED)
    torch.manual_seed(SEED)
    os.makedirs(ART_DIR, exist_ok=True)

    print("학습 세트 로드...", flush=True)
    feats, attrs, sides = [], [], []
    for name in TRAIN_SETS:
        feat, attr_mat, side = _load_set(name, 0, None)
        feat["agent_id"] = name + "/" + feat["agent_id"]
        feats.append(feat)
        attrs.append(attr_mat)
        sides.append(side)

    # 세트 간 _trade_row 충돌 방지: 세트별 오프셋 부여 후 라벨 행렬 연결
    offset = 0
    for i, f in enumerate(feats):
        f["_trade_row"] = f["_trade_row"] + offset
        offset += len(attrs[i])
    feat_train = pd.concat(feats, ignore_index=True)
    attr_train = np.vstack(attrs)

    norm_stats = seqfeat.fit_norm_stats(feat_train)
    counts = feat_train.groupby("agent_id").size()
    max_len = int(min(np.percentile(counts, MAX_LEN_PCTL), MAX_LEN_CAP))
    print(f"시퀀스 길이: p{MAX_LEN_PCTL}={max_len} (계좌 {len(counts):,})", flush=True)

    ids, X, lengths, rows, Y, M = _to_tensors(feat_train, attr_train, norm_stats, max_len)
    idx = np.arange(len(ids))
    rng = np.random.default_rng(SEED)
    rng.shuffle(idx)
    n_val = int(len(idx) * VAL_FRAC)
    vi, ti = idx[:n_val], idx[n_val:]
    print(f"학습 {len(ti):,} / 검증 {len(vi):,} 계좌, "
          f"라벨 거래 {int(M.sum()):,}건", flush=True)

    Xt, Lt = torch.from_numpy(X), torch.from_numpy(lengths)
    Yt, Mt = torch.from_numpy(Y), torch.from_numpy(M)

    model = GRUTagger(seqfeat.N_CHANNELS, HIDDEN, LAYERS, len(ATTRS))
    opt = torch.optim.Adam(model.parameters(), lr=LR)
    crit = nn.BCEWithLogitsLoss(reduction="none")

    def _masked_loss(logits, y, m):
        return (crit(logits, y) * m.unsqueeze(-1)).sum() / (m.sum() * len(ATTRS))

    def _eval_loss(sub):
        model.eval()
        with torch.no_grad():
            tot, n = 0.0, 0.0
            for b in range(0, len(sub), BATCH):
                s = sub[b : b + BATCH]
                logits = model(Xt[s], Lt[s])
                tot += (crit(logits, Yt[s]) * Mt[s].unsqueeze(-1)).sum().item()
                n += Mt[s].sum().item() * len(ATTRS)
        return tot / n

    best, best_state, bad = float("inf"), None, 0
    for epoch in range(1, MAX_EPOCHS + 1):
        model.train()
        rng.shuffle(ti)
        for b in range(0, len(ti), BATCH):
            s = ti[b : b + BATCH]
            opt.zero_grad()
            loss = _masked_loss(model(Xt[s], Lt[s]), Yt[s], Mt[s])
            loss.backward()
            opt.step()
        vl = _eval_loss(vi)
        marker = ""
        if vl < best - 1e-5:
            best, best_state, bad = vl, {k: v.clone() for k, v in model.state_dict().items()}, 0
            marker = " *"
        else:
            bad += 1
        print(f"epoch {epoch:3d}  val_bce {vl:.4f}{marker}", flush=True)
        if bad >= PATIENCE:
            print(f"early stop (patience {PATIENCE})", flush=True)
            break
    model.load_state_dict(best_state)

    # ---- 평가: 거래 단위 (처음으로 진짜 per-trade 정답 대비) -----------------
    report = {}
    for name in EVAL_SETS:
        feat, attr_mat, side = _load_set(name, max_len, norm_stats)
        e_ids, eX, eL, e_rows, eY, eM = _to_tensors(feat, attr_mat, norm_stats, max_len)
        model.eval()
        preds = []
        with torch.no_grad():
            for b in range(0, len(e_ids), BATCH):
                preds.append(torch.sigmoid(
                    model(torch.from_numpy(eX[b:b+BATCH]),
                          torch.from_numpy(eL[b:b+BATCH]))).numpy())
        P = np.vstack(preds)  # [N, T, 4]

        valid = e_rows >= 0
        flat_rows = e_rows[valid]                # 원본 trades 행 번호
        flat_pred = P[valid]                     # [n, 4]
        flat_true = attr_mat[flat_rows]
        flat_side = side[flat_rows]

        tab = {}
        print(f"\n[{name}]  (라벨 거래 {len(flat_rows):,}건)")
        print(f"  {'타깃':<22} {'대상':>4} {'rho':>7} {'AUC':>7} {'MAE':>8}")
        for j, a in enumerate(ATTRS):
            sel = flat_side == ATTR_SIDE[a]
            t, p = flat_true[sel, j], flat_pred[sel, j]
            rho = spearmanr(t, p).statistic if len(t) > 2 else float("nan")
            pos = t > 0
            if 0 < pos.sum() < len(t):  # AUC = 랭크 기반 (sklearn 없이)
                r = pd.Series(p).rank().to_numpy()
                auc = (r[pos].sum() - pos.sum() * (pos.sum() + 1) / 2) / (
                    pos.sum() * (~pos).sum())
            else:
                auc = float("nan")
            mae = float(np.mean(np.abs(t - p)))
            tab[a] = {"rho": round(float(rho), 3), "auc": round(float(auc), 3),
                      "mae": round(mae, 4), "n": int(sel.sum())}
            print(f"  {a:<22} {ATTR_SIDE[a]:>4} {tab[a]['rho']:>7} "
                  f"{tab[a]['auc']:>7} {tab[a]['mae']:>8}")

        # 계좌 수준 sanity: 거래 예측 평균 vs 계좌 라벨 (1단계 지표와 비교 가능)
        labels = pd.read_csv(
            config.dataset_path(name, "labels"),
            dtype={"agent_id": str}).set_index("agent_id")
        acc = {}
        aid_arr = np.repeat(np.asarray(e_ids), valid.sum(axis=1))
        acc_df = pd.DataFrame(flat_pred, columns=ATTRS)
        acc_df["agent_id"] = aid_arr
        mean_pred = acc_df.groupby("agent_id")[ATTRS].mean()
        joined = mean_pred.join(labels)
        for a in ATTRS:
            acc[a] = round(float(
                joined[a].corr(joined[ATTR_PARAM[a]], method="spearman")), 3)
        print(f"  [계좌 sanity rho] " +
              ", ".join(f"{ATTR_PARAM[a]} {acc[a]}" for a in ATTRS))
        report[name] = {"per_trade": tab, "account_sanity": acc}

    torch.save(model.state_dict(), os.path.join(ART_DIR, "tagger.pt"))
    meta = {
        "created": datetime.now().isoformat(timespec="seconds"),
        "attrs": ATTRS,
        "attr_side": ATTR_SIDE,
        "attr_param": ATTR_PARAM,
        "norm_stats": norm_stats,
        "max_len": max_len,
        "model": {"hidden": HIDDEN, "layers": LAYERS,
                  "n_channels": seqfeat.N_CHANNELS},
        "train_sets": TRAIN_SETS,
        "eval_sets": EVAL_SETS,
        "val_bce": round(best, 5),
        "eval_report": report,
    }
    with open(os.path.join(ART_DIR, "tagger_meta.json"), "w", encoding="utf-8") as fp:
        json.dump(meta, fp, ensure_ascii=False, indent=2)
    print(f"\n아티팩트 저장 → {ART_DIR}/tagger.pt, tagger_meta.json", flush=True)


if __name__ == "__main__":
    main()
