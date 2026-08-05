"""
3계층 (딥러닝) — 시퀀스 태깅 GRU로 거래별 편향 귀속 확률 추론 (2단계).

ml/train/train_tagger.py가 저장한 아티팩트(ml/artifacts/tagger.pt, tagger_meta.json)만
읽는다. 피처 생성은 학습과 동일 코드 경로(synthetic_data.features.build_features →
ml.seqfeat) — 합성 학습과 실계좌 추론이 같은 변환을 지나는 것이 sim-to-real 원칙.

출력 (score_account) — 거래 우선(trade-first):
  per_trade   거래별 판정 리스트(시퀀스 최근 max_len건). 각 항목 =
              {row(입력 행 위치), bias_scores(편향별 귀속 확률 0~1 — 모델 sigmoid
               출력 그대로), top_bias, trade_score(=최대 귀속 확률)}.
              "이 거래는 ~편향 때문일 수도"의 지도학습 직접 추정 — 타깃이 생성기의
              거래별 인과 라벨이므로 1단계의 IG 프록시와 달리 의미가 정의상 일치.
  lstm_score  per_trade trade_score의 최댓값 (시퀀스 절단 밖 거래의 폴백용 요약)
  bias_mean   편향별 거래 평균 확률 (참고용 — 제품 출력 아님)

실패 정책: 어떤 이유로든(아티팩트 부재·시세 조회 실패·torch 미설치) 채점을 못 하면
None → 호출부(detect.py)는 2계층 가중으로 폴백.

알려진 한계: 유니버스(2020년 201종목) 밖 종목·기간의 LOTT 랭크는 결측(마스크) —
학습 데이터에도 결측 구간이 있어 모델이 마스크 패턴을 학습한 상태다.
"""

import hashlib
import json
import logging
import os
import sys
from datetime import timedelta
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

# 레포 루트를 path에 추가 — ml/·synthetic_data/ 패키지 import용
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# 아티팩트 위치: 환경변수 우선(배포 서버 — 모델 파일은 gitignore라 레포에 없음),
# 없으면 로컬 학습 산출 경로. 둘 다 비어 있으면 GitHub Release에서 내려받는다
# (_ensure_artifacts — CANARY_MODEL_RELEASE 태그 필요, 사설 레포는 GITHUB_TOKEN).
_ART_DIR = Path(os.environ.get("CANARY_MODEL_DIR", _REPO_ROOT / "ml" / "artifacts"))
_RELEASE_ASSETS = ("tagger.pt", "tagger_meta.json", "distribution_ref.json",
                   "hashes.json")
logger = logging.getLogger(__name__)

try:
    import torch
    from ml import seqfeat
    from ml.gru_model import GRUTagger
    _IMPORT_ERROR = None
except Exception as e:  # torch 미설치 등 — score는 None 폴백
    _IMPORT_ERROR = e

# pykrx가 requests에 timeout을 안 걸어 KRX 무응답 시 무한 행 위험 —
# 전역 기본 timeout 패치는 synthetic_data.net 한 곳으로 통합 (idempotent).
# requests 자체는 아래 Release 다운로드(_ensure_artifacts)가 직접 쓴다.
import requests

from synthetic_data.net import ensure_timeout_patch

ensure_timeout_patch()

# 시세 룩백 버퍼: abn_vol 기준선(60거래일)·LOTT 창 확보용 (캘린더 일수)
_PRICE_LOOKBACK_DAYS = 150

# 리포트용 편향 표시명 (키 = 계좌 라벨 파라미터명 — top_bias 값과 동일 체계)
BIAS_NAMES = {
    "disposition_strength": "처분효과",
    "overconfidence": "과잉확신",
    "lottery_preference": "복권형선호",
    "herd_sensitivity": "군집거래",
}


def _ensure_artifacts() -> Path:
    """아티팩트 확보: 로컬 존재 시 그대로, 없으면 GitHub Release에서 1회 다운로드.

    다운로드 실패는 예외 → _load_artifacts → score_account None → 2계층 폴백
    (기존 실패 정책 그대로). 태그 미설정이면 시도 없이 즉시 부재 처리."""
    if (_ART_DIR / "tagger.pt").exists() and (_ART_DIR / "tagger_meta.json").exists():
        return _ART_DIR
    tag = os.environ.get("CANARY_MODEL_RELEASE")
    if not tag:
        raise RuntimeError(
            f"모델 아티팩트 없음({_ART_DIR}) — CANARY_MODEL_DIR 또는 "
            "CANARY_MODEL_RELEASE(다운로드 태그)를 설정할 것")
    repo = os.environ.get("CANARY_MODEL_REPO", "Cloud9-capstone-2026/cloud9")
    headers = {"Accept": "application/vnd.github+json"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    r = requests.get(f"https://api.github.com/repos/{repo}/releases/tags/{tag}",
                     headers=headers, timeout=30)
    r.raise_for_status()
    assets = {a["name"]: a for a in r.json().get("assets", [])}
    missing = [n for n in ("tagger.pt", "tagger_meta.json") if n not in assets]
    if missing:
        raise RuntimeError(f"Release {tag}에 필수 자산 없음: {missing}")
    _ART_DIR.mkdir(parents=True, exist_ok=True)
    for name in _RELEASE_ASSETS:
        if name not in assets:
            continue  # 선택 자산(hashes 등)은 없어도 동작
        dl = requests.get(assets[name]["url"],
                          headers={**headers, "Accept": "application/octet-stream"},
                          timeout=300)
        dl.raise_for_status()
        tmp = _ART_DIR / (name + ".tmp")
        tmp.write_bytes(dl.content)
        tmp.replace(_ART_DIR / name)  # 부분 다운로드가 정본이 되지 않도록 원자 교체

    # 무결성 검증: hashes.json의 출력물 지문과 대조 — 전송 손상·자산 뒤섞임 탐지.
    # (hashes.json 자체가 같은 Release에서 오므로 악의적 교체까지 막지는 못함 —
    # 그건 Release 접근 권한의 문제. 여기서는 무결성만 책임진다.)
    # 불일치는 예외 → 기존 실패 정책(2계층 폴백). hashes.json 없으면 검증 생략 경고.
    hashes_path = _ART_DIR / "hashes.json"
    if hashes_path.exists():
        with open(hashes_path, encoding="utf-8") as fp:
            expected = json.load(fp).get("artifacts", {})
        for name, want in expected.items():
            p = _ART_DIR / name
            if not p.exists():
                continue
            got = hashlib.sha256(p.read_bytes()).hexdigest()
            if got != want:
                raise RuntimeError(
                    f"아티팩트 무결성 불일치: {name} (기대 {want[:12]}…, 실제 {got[:12]}…)")
        logger.info("layer3 아티팩트 무결성 검증 통과 (%d개)", len(expected))
    else:
        logger.warning("hashes.json 부재 — 다운로드 아티팩트 무결성 검증 생략")
    logger.info("layer3 아티팩트 다운로드 완료: %s (%s)", tag, _ART_DIR)
    return _ART_DIR


@lru_cache(maxsize=1)
def _load_artifacts():
    if _IMPORT_ERROR is not None:
        raise RuntimeError(f"layer3 의존성 import 실패: {_IMPORT_ERROR!r}")
    art = _ensure_artifacts()
    with open(art / "tagger_meta.json", encoding="utf-8") as fp:
        meta = json.load(fp)
    m = meta["model"]
    model = GRUTagger(m["n_channels"], m["hidden"], m["layers"], len(meta["attrs"]),
                      dropout=m.get("dropout", 0.0))  # eval 모드라 추론엔 무영향
    model.load_state_dict(torch.load(art / "tagger.pt", map_location="cpu"))
    model.eval()
    return model, meta


def _fetch_price_df(tickers, d_min, d_max) -> pd.DataFrame:
    """계좌 종목들의 OHLCV → market_data 스키마. price_cache 경유 —
    커버된 구간은 네트워크 없음, 부족 구간만 pykrx 증분 조회(2-1).
    실패 종목은 건너뜀(해당 종목 시장 컨텍스트는 결측 → 마스크)."""
    from price_cache import get_ohlcv  # 지연 import (모듈 로드 의존 최소화)

    start = d_min - timedelta(days=_PRICE_LOOKBACK_DAYS)
    df = get_ohlcv(tickers, start, d_max)
    if df.empty:
        raise RuntimeError("시세 조회 전면 실패 — layer3 스킵")
    return df


def _fetch_index_df(price_df) -> pd.DataFrame:
    """코스피 지수 종가. 로그인 필요 API라 실패할 수 있음 — 실패 시 NaN 지수
    (driver 피처 결측 → 마스크)로 진행한다."""
    days = sorted(price_df["거래일자"].unique())
    try:
        from synthetic_data.market_data import get_index_data
        idx = get_index_data()  # 로컬 캐시 적중 시 네트워크 없음
        idx = idx[idx["거래일자"].isin(set(days))]
        if len(idx) >= max(2, len(days) // 2):  # 기간 커버가 충분할 때만 사용
            return idx
    except Exception:
        pass
    try:
        from pykrx import stock
        df = stock.get_index_ohlcv(
            days[0].strftime("%Y%m%d"), days[-1].strftime("%Y%m%d"), "1001"
        )
        if df is not None and not df.empty:
            return pd.DataFrame({
                "거래일자": pd.to_datetime(df.index).date,
                "종가": df["종가"].astype(float).values,
            })
    except Exception:
        pass
    return pd.DataFrame({"거래일자": days, "종가": [np.nan] * len(days)})


def score_from_trades(trades: pd.DataFrame, price_df=None, index_df=None) -> dict | None:
    """합성 스키마 거래(agent_id·종목코드 등 features.REQUIRED_COLUMNS)를 단일
    계좌로 보고 채점. price/index 미지정 시 pykrx에서 조회(테스트에서는 주입)."""
    try:
        from synthetic_data.features import build_features

        model, meta = _load_artifacts()
        trades = trades.reset_index(drop=True).copy()
        trades["거래일자"] = pd.to_datetime(trades["거래일자"]).dt.date
        if price_df is None:
            real = sorted({t for t in trades["종목코드"].unique()
                           if not str(t).startswith("NM_")})
            price_df = _fetch_price_df(
                real, trades["거래일자"].min(), trades["거래일자"].max()
            )
        if index_df is None:
            index_df = _fetch_index_df(price_df)

        out = build_features(trades, price_df, index_df, windows=(None,))
        ev = seqfeat.attach_trade_rows(out["events"], trades)
        feat = seqfeat.event_features(ev)
        ids, X, lengths, rows = seqfeat.build_sequences(
            feat, meta["norm_stats"], meta["max_len"], return_rows=True
        )
        if not ids:
            return None
        with torch.no_grad():
            probs = torch.sigmoid(
                model(torch.from_numpy(X), torch.from_numpy(lengths))
            ).numpy()

        # 단일 계좌 전제 — 첫 계좌 기준
        L = int(lengths[0])
        P = probs[0, :L]        # [L, 4] 거래별 편향 귀속 확률
        seq_rows = rows[0, :L]  # 각 위치의 trades 행 번호
        params = [meta["attr_param"][a] for a in meta["attrs"]]
        src = (trades["_src_row"].to_numpy()
               if "_src_row" in trades.columns else trades.index.to_numpy())

        per_trade = []
        for i in range(L):
            r = int(seq_rows[i])
            row = trades.iloc[r]
            scores = {p: round(float(P[i, j]), 4) for j, p in enumerate(params)}
            top = max(scores, key=scores.get)
            per_trade.append({
                "row": int(src[r]),
                "거래일자": str(row["거래일자"]),
                "종목코드": str(row["종목코드"]),
                "거래구분": str(row["거래구분"]),
                "bias_scores": scores,
                "top_bias": top,
                "top_bias_명": BIAS_NAMES.get(top, top),
                "trade_score": round(max(scores.values()), 4),
            })

        return {
            "per_trade": per_trade,
            "lstm_score": round(max(e["trade_score"] for e in per_trade), 4),
            "bias_mean": {p: round(float(P[:, j].mean()), 4)
                          for j, p in enumerate(params)},
            "n_events": L,
        }
    except Exception as e:
        logger.warning("layer3 채점 실패 — 2계층 폴백: %r", e)
        return None


def score_account(standard_df: pd.DataFrame, user_id: str = "user") -> dict | None:
    """백엔드 표준 컬럼(날짜·종목명·매매구분·체결수량·체결단가·총거래금액) 입력.

    종목명 → 종목코드 매핑(feature_eng.get_ticker_code) 후 합성 스키마로 변환해
    score_from_trades에 위임. 매핑 실패 종목은 가짜 코드("NM_종목명")로 남겨
    포지션 추적은 유지하되 시장 컨텍스트만 결측(마스크) 처리되게 한다.

    반환의 per_trade[i]["row"]는 standard_df의 행 위치(0-base, 원래 순서 기준)
    — 호출부(detect.py)가 거래별 점수를 자기 행에 매칭할 때 쓴다."""
    try:
        from pipeline.feature_eng import get_ticker_code

        df = standard_df.reset_index(drop=True).copy()
        name_map = {}
        for name in df["종목명"].dropna().unique():
            try:
                code = get_ticker_code(str(name))
            except Exception:
                code = None
            name_map[name] = code if code else f"NM_{name}"

        qty = pd.to_numeric(df["체결수량"], errors="coerce")
        price = pd.to_numeric(df["체결단가"], errors="coerce")
        if "총거래금액" in df.columns:
            value = pd.to_numeric(df["총거래금액"], errors="coerce")
        else:  # 컬럼 자체가 없는 CSV — 수량×단가로 재구성
            value = pd.Series(np.nan, index=df.index)
        trades = pd.DataFrame({
            "거래일자": pd.to_datetime(df["날짜"]).dt.date,
            "agent_id": str(user_id),
            "종목코드": df["종목명"].map(name_map),
            "거래구분": np.where(
                df["매매구분"].astype(str).str.contains("매수"), "매수", "매도"
            ),
            "거래수량": qty,
            "거래단가": price,
            "거래금액": value.fillna(qty * price),
        })
        trades["_src_row"] = df.index  # 표준 입력의 행 위치 (per_trade 매칭용)
        trades = trades.dropna(subset=["거래수량", "거래단가"])
        if trades.empty:
            return None
        return score_from_trades(trades)
    except Exception as e:
        logger.warning("layer3 입력 변환 실패 — 2계층 폴백: %r", e)
        return None
