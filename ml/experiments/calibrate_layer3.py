"""
3계층 판정 임계값 재보정 — 서비스 채점 경로 그대로.

실행 (레포 최상위):
  python -m ml.experiments.calibrate_layer3                       # s103으로 선택, s104로 확인
  python -m ml.experiments.calibrate_layer3 --theta 0.7283        # 주어진 값만 평가(선택 생략)

무엇을 하나
- 채점: backend/models/layer3.score_from_trades와 같은 경로 — 전체 이력을 창 분할
  (_score_windows)로 채점, 점수는 소수 넷째 자리 반올림, 시장 맥락(abn·r1·r5)이 전부
  결측인 거래는 제외. 거래 방향에 맞는 축만 판정 대상(매도=처분효과, 매수=나머지).
- 양성(τ): 그 축의 거래별 라벨 ≥ 0.5 (methodology.md "임계값 결정 방식").
- 축별 평가는 **그 축 자신의 점수**로 한다 — 과잉확신 양성을 복권형 점수로 잡은 것은
  과잉확신 탐지 성공이 아니다(옛 calibrate_ensemble은 전체 플래그로 세어 이 구분이 없었다).
- 선택 규칙(결과를 보기 전에 고정): 네 축 모두 재현율 ≥ AXIS_FLOOR인 후보 중 가장 높은 θ.
  조건을 만족하는 후보가 없으면 그대로 보고한다.
- 선택 세트(s103)로 고르고 확인 세트(s104)는 고른 값을 고정해 한 번만 평가한다.
- 범위(0~1) 밖 라벨 거래는 입력 시퀀스에는 두고 집계에서만 제외하며 그 수를 기록한다.

산출: ml/cache/l3scores_{세트}_{지문}.parquet (점수 캐시 — 지문 = 모델 가중치·메타·
      그 세트의 피처 캐시 파일 해시라 셋 중 하나만 바뀌어도 다시 채점),
      ml/cache/calibrate_layer3_{실행시각}.json (보정 기록: 지문·세트·τ·하한·후보 간격·
      공통/축별 임계값과 두 세트의 결과)
"""
import argparse
import hashlib
import json
import os
import sys
from datetime import datetime

import numpy as np
import pandas as pd
import torch

_REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(_REPO, "backend"))  # models.layer3

from synthetic_data import config  # noqa: E402
from synthetic_data.main import check_label_alignment  # noqa: E402
from .. import seqfeat  # noqa: E402
from ..gru_model import GRUTagger  # noqa: E402
from models.layer3 import _score_windows  # noqa: E402

CACHE_DIR = os.path.join(_REPO, "ml", "cache")
ART_DIR = os.path.join(_REPO, "ml", "artifacts")
TAU = 0.5          # 양성 라벨 기준
AXIS_FLOOR = 0.30  # 네 축 재현율 하한
GRID = np.round(np.arange(0.05, 0.9951, 0.0005), 4)  # 후보 θ (점수 전 구간)
SELECT_SET, CHECK_SET = "eval_natural_s103", "eval_natural_s104"


def _sha(path, n=12):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:n]


def _git_head():
    try:
        import subprocess
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=_REPO,
                                       text=True).strip()
    except Exception:  # noqa: BLE001 — git 없는 환경이면 기록만 비움
        return None


def fingerprint(name):
    """세트별 점수 지문: 모델 가중치 + 메타(정규화 통계·max_len) + 그 세트의 피처 캐시."""
    return "-".join(_sha(p) for p in (os.path.join(ART_DIR, "tagger.pt"),
                                      os.path.join(ART_DIR, "tagger_meta.json"),
                                      os.path.join(CACHE_DIR, f"{name}_events.parquet")))


def load_model():
    meta = json.load(open(os.path.join(ART_DIR, "tagger_meta.json"), encoding="utf-8"))
    m = meta["model"]
    model = GRUTagger(m["n_channels"], m["hidden"], m["layers"], len(meta["attrs"]),
                      dropout=m.get("dropout", 0.0))
    model.load_state_dict(torch.load(os.path.join(ART_DIR, "tagger.pt"), map_location="cpu"))
    model.eval()
    return model, meta


def load_set(name):
    ev = pd.read_parquet(os.path.join(CACHE_DIR, f"{name}_events.parquet"))
    tr = pd.read_csv(config.dataset_path(name, "trades"), dtype={"종목코드": str})
    tl = pd.read_csv(config.dataset_path(name, "trade_labels"))
    assert len(ev) == len(tr), f"{name}: events/trades 행수 불일치"
    check_label_alignment(tr, tl)
    feat = seqfeat.event_features(seqfeat.attach_trade_rows(ev, tr))
    return feat, tr, tl


def score_set(name, model, meta):
    """세트 전 거래의 축별 점수 (서비스 경로). 캐시는 지문(모델·메타·피처 캐시)으로 분리."""
    path = os.path.join(CACHE_DIR, f"l3scores_{name}_{fingerprint(name)}.parquet")
    if os.path.exists(path):
        return pd.read_parquet(path)
    feat, tr, _tl = load_set(name)
    no_market = set(feat.loc[feat[["abn", "r1", "r5"]].isna().all(axis=1), "_trade_row"].astype(int))
    L = int(feat.groupby("agent_id").size().max())  # 절단 없이 전체 이력
    ids, X, lengths, rows = seqfeat.build_sequences(feat, meta["norm_stats"], L, return_rows=True)
    W = int(meta["max_len"])
    params = [meta["attr_param"][a] for a in meta["attrs"]]
    recs = []
    for k in range(len(ids)):
        N = int(lengths[k])
        P = _score_windows(model, torch.from_numpy(X[k, :N]), W).numpy()
        for i in range(N):
            r = int(rows[k, i])
            if r in no_market:
                continue
            recs.append((r, *np.round(P[i].astype(float), 4)))
    S = pd.DataFrame(recs, columns=["row"] + params).sort_values("row").reset_index(drop=True)
    S["side"] = tr["거래구분"].to_numpy()[S["row"]]
    S.attrs["n_no_market"] = len(no_market)
    S.to_parquet(path, index=False)
    print(f"{name}: 채점 {len(S):,}/{len(tr):,}건 (시장 맥락 없음 제외 {len(no_market)}) → {path}")
    return S


def build_eval(name, model, meta):
    """채점 결과 + 라벨 → 평가 프레임. 범위 밖 라벨 행은 집계 제외(수 기록)."""
    S = score_set(name, model, meta)
    _feat, _tr, tl = load_set(name)
    attrs = meta["attrs"]
    lab = tl.iloc[S["row"].to_numpy()].reset_index(drop=True)
    bad = ~lab[attrs].apply(lambda c: c.between(0.0, 1.0)).all(axis=1)
    E = S.loc[~bad].reset_index(drop=True)
    labE = lab.loc[~bad].reset_index(drop=True)
    for a in attrs:
        E["y_" + a] = (labE[a].to_numpy() >= TAU) & (E["side"].to_numpy() == meta["attr_side"][a])
    return E, int(bad.sum())


def metrics(E, meta, theta):
    """theta: float(공통) 또는 {param: θ}(축별). 축별은 그 축 점수·그 방향만, 전체는
    방향별 최댓값(=서비스 trade_score)."""
    attrs, side_of, param_of = meta["attrs"], meta["attr_side"], meta["attr_param"]
    th = {param_of[a]: (theta if not isinstance(theta, dict) else theta[param_of[a]]) for a in attrs}
    side = E["side"].to_numpy()
    out, flag_any, y_any = {}, np.zeros(len(E), bool), np.zeros(len(E), bool)
    for a in attrs:
        p = param_of[a]
        m = side == side_of[a]
        y = E["y_" + a].to_numpy()
        f = (E[p].to_numpy() >= th[p]) & m
        tp, fp, fn = int((f & y).sum()), int((f & ~y).sum()), int((~f & y).sum())
        out[p] = {"theta": th[p], "n_pos": int(y.sum()), "n_flag": int(f.sum()), "tp": tp, "fp": fp, "fn": fn,
                  "precision": tp / (tp + fp) if tp + fp else float("nan"),
                  "recall": tp / (tp + fn) if tp + fn else float("nan")}
        flag_any |= f
        y_any |= y
    tp, fp, fn = int((flag_any & y_any).sum()), int((flag_any & ~y_any).sum()), int((~flag_any & y_any).sum())
    out["overall"] = {"n": len(E), "n_pos": int(y_any.sum()), "n_flag": int(flag_any.sum()), "tp": tp, "fp": fp, "fn": fn,
                      "precision": tp / (tp + fp) if tp + fp else float("nan"),
                      "recall": tp / (tp + fn) if tp + fn else float("nan"),
                      "flag_rate": float(flag_any.mean())}
    return out


def sweep(E, meta):
    """공통 θ 후보 전 구간의 축별 재현율·정밀도 표."""
    rows = []
    for th in GRID:
        m = metrics(E, meta, float(th))
        rows.append({"theta": float(th), "precision": m["overall"]["precision"], "recall": m["overall"]["recall"],
                     "flag_rate": m["overall"]["flag_rate"],
                     **{f"R:{p}": m[p]["recall"] for p in m if p != "overall"},
                     **{f"P:{p}": m[p]["precision"] for p in m if p != "overall"}})
    return pd.DataFrame(rows)


def select_common(tbl, params):
    ok = tbl[(tbl[[f"R:{p}" for p in params]] >= AXIS_FLOOR).all(axis=1)]
    return None if ok.empty else float(ok["theta"].max())


def select_per_axis(tbl, params):
    """참고용: 축마다 따로 재현율 ≥ AXIS_FLOOR를 만족하는 가장 높은 θ."""
    out = {}
    for p in params:
        ok = tbl[tbl[f"R:{p}"] >= AXIS_FLOOR]
        out[p] = None if ok.empty else float(ok["theta"].max())
    return out


def _fmt(m, params):
    o = m["overall"]
    lines = [f"  전체      n={o['n']:,} 양성={o['n_pos']:,} 플래그={o['n_flag']:,} ({o['flag_rate']*100:.1f}%)"
             f"  정밀도 {o['precision']:.3f} 재현율 {o['recall']:.3f}"]
    for p in params:
        x = m[p]
        lines.append(f"  {p:<22} θ={x['theta']:.4f} 양성={x['n_pos']:,} 플래그={x['n_flag']:,}"
                     f"  정밀도 {x['precision']:.3f} 재현율 {x['recall']:.3f}  (TP {x['tp']:,} FP {x['fp']:,} FN {x['fn']:,})")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--theta", type=float, default=None, help="이 값만 평가(선택 생략)")
    ap.add_argument("--select", default=SELECT_SET)
    ap.add_argument("--check", default=CHECK_SET)
    args = ap.parse_args()

    model, meta = load_model()
    params = [meta["attr_param"][a] for a in meta["attrs"]]
    print(f"모델 생성 {meta['created']} / 학습 세트 {meta.get('train_sets')}")
    record = {"model_created": meta["created"], "tau": TAU, "axis_floor": AXIS_FLOOR,
              "grid": {"start": float(GRID[0]), "stop": float(GRID[-1]), "step": 0.0005},
              "rule": "네 축 모두 재현율 ≥ axis_floor인 후보 중 가장 높은 θ (각 축 자신의 점수·방향 기준)",
              "select_set": args.select, "check_set": args.check,
              "fingerprints": {s: fingerprint(s) for s in (args.select, args.check) if s},
              # 평가에 쓴 거래·라벨 파일과 실행 코드 — 어떤 라벨로 계산한 결과인지 식별용
              "data_hashes": {s: {"trades": _sha(config.dataset_path(s, "trades")),
                                  "trade_labels": _sha(config.dataset_path(s, "trade_labels"))}
                              for s in (args.select, args.check) if s},
              "code_commit": _git_head(),
              "sets": {}}

    E_sel, bad_sel = build_eval(args.select, model, meta)
    print(f"\n[{args.select}] 평가 {len(E_sel):,}건 (범위 밖 라벨 제외 {bad_sel}건)")
    record["sets"][args.select] = {"n_eval": len(E_sel), "n_bad_label_excluded": bad_sel}

    per_axis = None
    if args.theta is None:
        tbl = sweep(E_sel, meta)
        theta = select_common(tbl, params)
        per_axis = select_per_axis(tbl, params)
        print(f"\n선택(공통 θ, 규칙: {record['rule']}): {theta}")
        print(f"참고(축별 θ, 각 축 재현율 ≥ {AXIS_FLOOR}): {per_axis}")
        if theta is None or any(v is None for v in per_axis.values()):
            tbl.to_csv(os.path.join(CACHE_DIR, f"calibrate_layer3_sweep_{args.select}.csv"), index=False)
            raise SystemExit(f"기준 미달: 네 축 재현율 ≥ {AXIS_FLOOR}를 만족하는 후보가 없다 "
                             f"(공통 {theta}, 축별 {per_axis}). 후보표는 저장함.")
        f1 = 2 * tbl["precision"] * tbl["recall"] / (tbl["precision"] + tbl["recall"]).clip(lower=1e-12)
        print("\n후보표 발췌 (전체 정밀도/재현율, 축별 재현율):")
        marks = {"현행 0.7283": 0.7283, "F1 최대": float(tbl.loc[f1.idxmax(), "theta"]),
                 "선택": theta, **{f"축별 {p}": v for p, v in per_axis.items()}}
        for nm, th in marks.items():
            if th is None:
                continue
            r = tbl.iloc[(tbl["theta"] - th).abs().argmin()]
            print(f"  {nm:<28} θ={r['theta']:.4f} P {r['precision']:.3f} R {r['recall']:.3f} flag {r['flag_rate']*100:.1f}%  "
                  + " ".join(f"{p.split('_')[0][:4]} {r[f'R:{p}']:.2f}" for p in params))
        record["selected_theta"] = theta
        record["per_axis_theta_reference"] = per_axis
        tbl_path = os.path.join(CACHE_DIR, f"calibrate_layer3_sweep_{args.select}.csv")
        tbl.to_csv(tbl_path, index=False)
        record["sweep_table"] = tbl_path
    else:
        theta = args.theta

    def _report(nm, E, bad):
        rec = record["sets"].setdefault(nm, {"n_eval": len(E), "n_bad_label_excluded": bad})
        m = metrics(E, meta, theta)
        print(f"\n[{nm}] 공통 θ={theta}\n{_fmt(m, params)}")
        rec["common"] = m
        if per_axis:
            mp = metrics(E, meta, per_axis)
            print(f"[{nm}] 축별 θ\n{_fmt(mp, params)}")
            rec["per_axis"] = mp
        if theta != 0.7283:
            m0 = metrics(E, meta, 0.7283)
            print(f"[{nm}] 옛 공통 0.7283 비교\n{_fmt(m0, params)}")
            rec["at_0.7283"] = m0

    _report(args.select, E_sel, bad_sel)
    if args.check:
        E_chk, bad_chk = build_eval(args.check, model, meta)
        print(f"\n[{args.check}] 확인 세트 — 선택 세트에서 고른 값 고정 (범위 밖 라벨 제외 {bad_chk}건)")
        _report(args.check, E_chk, bad_chk)

    out = os.path.join(CACHE_DIR, f"calibrate_layer3_{datetime.now():%Y%m%d_%H%M%S}.json")
    json.dump(record, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=2, default=float)
    print(f"\n보정 기록 → {out}")


if __name__ == "__main__":
    main()
