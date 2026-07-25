"""
3계층 시퀀스 태깅 학습 (2단계): 거래별 인과 귀속 라벨 직접 학습.

실행: python -m ml.train_tagger  (레포 최상위, ml.prepare + trade_labels 재생성 후)
학습: train_extended s11~s23 (계좌 90/10 학습/검증 분할, 검증은 early stopping용)
평가: eval_natural s101·s102 (최종 평가 전용 — 학습·튜닝에 미사용)

타깃 = 생성기가 기록한 거래별 편향 귀속 확률(trade_labels 4컬럼, DECISIONS 8-1):
  attr_disposition   (매도) 1 − p₀/p₁ — 처분효과가 만든 초과 확률 귀속
  attr_overconfidence(매수) 1 − p₀/p₁ — 상승일 증폭 귀속
  attr_lottery/herd  (매수) 선택 가중의 성분 비중
모델 출력(sigmoid)이 곧 "이 거래가 그 편향 때문일 확률"의 추정 — 출력 단위가
거래라 1·2계층과 정합.

데이터 적재·학습 루프는 함수로 분리되어 sweep_tagger(하이퍼파라미터 스윕)가
재사용한다. 이 스크립트의 기본값 실행 = 스윕 이전의 1차 설정.

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

HIDDEN, LAYERS, DROPOUT, BATCH, MAX_EPOCHS, PATIENCE, LR = 64, 1, 0.0, 256, 100, 8, 1e-3
MAX_LEN_PCTL, MAX_LEN_CAP = 95, 256
VAL_FRAC = 0.1

_crit = nn.BCEWithLogitsLoss(reduction="none")


def _load_set(name: str):
    """세트 → (피처 프레임, trades 행 순서의 귀속 라벨 행렬, 거래구분 배열)."""
    ev = pd.read_parquet(os.path.join(CACHE_DIR, f"{name}_events.parquet"))
    tr = pd.read_csv(config.dataset_path(name, "trades"))
    tl = pd.read_csv(config.dataset_path(name, "trade_labels"))
    assert len(ev) == len(tr) == len(tl), f"{name}: events/trades/trade_labels 행수 불일치"
    ev = seqfeat.attach_trade_rows(ev, tr)
    feat = seqfeat.event_features(ev)
    return feat, tl[ATTRS].to_numpy(dtype="float32"), tr["거래구분"].to_numpy()


def _to_tensors(feat, attr_mat, norm_stats, max_len):
    ids, X, lengths, rows = seqfeat.build_sequences(
        feat, norm_stats, max_len, return_rows=True
    )
    valid = rows >= 0
    Y = np.zeros((*rows.shape, len(ATTRS)), dtype="float32")
    Y[valid] = attr_mat[rows[valid]]
    return ids, X, lengths, rows, Y, valid.astype("float32")


def load_train_tensors(verbose: bool = True) -> dict:
    """학습 5시드 조립 → 텐서·분할·정규화 통계. train/sweep 공용 (1회 로드 후 재사용)."""
    feats, attrs = [], []
    for name in TRAIN_SETS:
        feat, attr_mat, _side = _load_set(name)
        feat["agent_id"] = name + "/" + feat["agent_id"]
        feats.append(feat)
        attrs.append(attr_mat)
    offset = 0  # 세트 간 _trade_row 충돌 방지 오프셋
    for i, f in enumerate(feats):
        f["_trade_row"] = f["_trade_row"] + offset
        offset += len(attrs[i])
    feat_train = pd.concat(feats, ignore_index=True)
    attr_train = np.vstack(attrs)

    norm_stats = seqfeat.fit_norm_stats(feat_train)
    counts = feat_train.groupby("agent_id").size()
    max_len = int(min(np.percentile(counts, MAX_LEN_PCTL), MAX_LEN_CAP))

    ids, X, lengths, rows, Y, M = _to_tensors(feat_train, attr_train, norm_stats, max_len)
    idx = np.arange(len(ids))
    rng = np.random.default_rng(SEED)
    rng.shuffle(idx)
    n_val = int(len(idx) * VAL_FRAC)
    vi, ti = idx[:n_val], idx[n_val:]
    if verbose:
        print(f"시퀀스 길이: p{MAX_LEN_PCTL}={max_len} (계좌 {len(counts):,}) / "
              f"학습 {len(ti):,} / 검증 {len(vi):,} 계좌, "
              f"라벨 거래 {int(M.sum()):,}건", flush=True)
    return {
        "Xt": torch.from_numpy(X), "Lt": torch.from_numpy(lengths),
        "Yt": torch.from_numpy(Y), "Mt": torch.from_numpy(M),
        "ti": ti, "vi": vi, "norm_stats": norm_stats, "max_len": max_len,
    }


def train_config(data: dict, hidden: int, layers: int, dropout: float, lr: float,
                 max_epochs: int = MAX_EPOCHS, patience: int = PATIENCE,
                 seed: int = SEED, verbose: bool = True):
    """설정 하나 학습 → (best val_bce, best state_dict, 수렴 epoch). 스윕 공용."""
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    Xt, Lt, Yt, Mt = data["Xt"], data["Lt"], data["Yt"], data["Mt"]
    ti, vi = data["ti"].copy(), data["vi"]
    rng = np.random.default_rng(seed)

    model = GRUTagger(seqfeat.N_CHANNELS, hidden, layers, len(ATTRS), dropout=dropout)
    opt = torch.optim.Adam(model.parameters(), lr=lr)

    def _masked_loss(logits, y, m):
        return (_crit(logits, y) * m.unsqueeze(-1)).sum() / (m.sum() * len(ATTRS))

    def _eval_loss(sub):
        model.eval()
        with torch.no_grad():
            tot, n = 0.0, 0.0
            for b in range(0, len(sub), BATCH):
                s = sub[b : b + BATCH]
                tot += (_crit(model(Xt[s], Lt[s]), Yt[s]) * Mt[s].unsqueeze(-1)).sum().item()
                n += Mt[s].sum().item() * len(ATTRS)
        return tot / n

    best, best_state, best_epoch, bad = float("inf"), None, 0, 0
    for epoch in range(1, max_epochs + 1):
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
            best, best_epoch, bad = vl, epoch, 0
            best_state = {k: v.clone() for k, v in model.state_dict().items()}
            marker = " *"
        else:
            bad += 1
        if verbose:
            print(f"epoch {epoch:3d}  val_bce {vl:.4f}{marker}", flush=True)
        if bad >= patience:
            if verbose:
                print(f"early stop (patience {patience})", flush=True)
            break
    return best, best_state, best_epoch


def evaluate_and_report(model, norm_stats, max_len) -> dict:
    """봉인된 평가 시드에서 거래 단위 평가 + 계좌 sanity. (최종 모델에만 사용할 것)"""
    report = {}
    for name in EVAL_SETS:
        feat, attr_mat, side = _load_set(name)
        e_ids, eX, eL, e_rows, eY, eM = _to_tensors(feat, attr_mat, norm_stats, max_len)
        model.eval()
        preds = []
        with torch.no_grad():
            for b in range(0, len(e_ids), BATCH):
                preds.append(torch.sigmoid(
                    model(torch.from_numpy(eX[b:b+BATCH]),
                          torch.from_numpy(eL[b:b+BATCH]))).numpy())
        P = np.vstack(preds)

        valid = e_rows >= 0
        flat_rows = e_rows[valid]
        flat_pred = P[valid]
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

        # 계좌 수준 sanity: 거래 예측 평균 vs 계좌 라벨
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
    return report


def main(hidden=HIDDEN, layers=LAYERS, dropout=DROPOUT, lr=LR):
    os.makedirs(ART_DIR, exist_ok=True)
    print("학습 세트 로드...", flush=True)
    data = load_train_tensors()
    best, best_state, best_epoch = train_config(data, hidden, layers, dropout, lr)

    model = GRUTagger(seqfeat.N_CHANNELS, hidden, layers, len(ATTRS), dropout=dropout)
    model.load_state_dict(best_state)
    report = evaluate_and_report(model, data["norm_stats"], data["max_len"])

    torch.save(model.state_dict(), os.path.join(ART_DIR, "tagger.pt"))
    meta = {
        "created": datetime.now().isoformat(timespec="seconds"),
        "attrs": ATTRS,
        "attr_side": ATTR_SIDE,
        "attr_param": ATTR_PARAM,
        "norm_stats": data["norm_stats"],
        "max_len": data["max_len"],
        "model": {"hidden": hidden, "layers": layers, "dropout": dropout,
                  "n_channels": seqfeat.N_CHANNELS},
        "train_sets": TRAIN_SETS,
        "eval_sets": EVAL_SETS,
        "lr": lr,
        "val_bce": round(best, 5),
        "best_epoch": best_epoch,
        "eval_report": report,
    }
    with open(os.path.join(ART_DIR, "tagger_meta.json"), "w", encoding="utf-8") as fp:
        json.dump(meta, fp, ensure_ascii=False, indent=2)
    print(f"\n아티팩트 저장 → {ART_DIR}/tagger.pt, tagger_meta.json", flush=True)


if __name__ == "__main__":
    main()
