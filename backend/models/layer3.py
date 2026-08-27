"""
3계층 (딥러닝) — 시퀀스 태깅 GRU로 거래별 편향 귀속 확률 추론 (2단계).

ml/train/train_tagger.py가 저장한 아티팩트(ml/artifacts/tagger.pt, tagger_meta.json)만
읽는다. 피처 생성은 학습과 동일 코드 경로(synthetic_data.features.build_features →
ml.seqfeat) — 합성 학습과 실계좌 추론이 같은 변환을 지나는 것이 sim-to-real 원칙.

출력 (score_account) — 거래 우선(trade-first):
  per_trade   거래별 판정 리스트(전 거래 — 이력이 max_len을 넘으면 창을 1건씩
              밀며 나눠 채점, _score_windows 참조). 각 항목 =
              {row(입력 행 위치), bias_scores(편향별 귀속 확률 0~1 — 모델 sigmoid
               출력 그대로), top_bias, trade_score(=최대 귀속 확률),
               evidence(편향별 판정 근거 — models.xai IG 분해: 이 거래 자신의
               값 피처별 기여 전체 + 현재/과거 문맥 기여율. 계산 실패 시 키 부재)}.
              "이 거래는 ~편향 때문일 수도"의 지도학습 직접 추정 — 타깃이 생성기의
              거래별 인과 라벨이므로 1단계의 IG 프록시와 달리 의미가 정의상 일치.
              시장 맥락이 전무한 거래(시세 조회 실패 등)는 제외 — 사유는
              score_from_trades 본문 주석 참조.
  lstm_score  per_trade trade_score의 최댓값 (계좌 요약 참고용)
  bias_mean   편향별 거래 평균 확률 (참고용 — 제품 출력 아님)

실패 정책: 어떤 이유로든(아티팩트 부재·시세 조회 전면 실패·torch 미설치) 채점을
못 하면 None → 호출부(detect.py)는 2계층 가중으로 폴백. 일부 거래만 시장 맥락이
없으면 그 거래만 per_trade에서 빠지고(위) 나머지는 정상 채점.

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

from config.settings import get  # 2026-08-27 CANARY_MODEL_REPO settings.yaml 이관

# 아티팩트 위치: 환경변수 우선(배포 서버 — 모델 파일은 gitignore라 레포에 없음),
# 없으면 로컬 학습 산출 경로. 둘 다 비어 있으면 GitHub Release에서 내려받는다
# (_ensure_artifacts — CANARY_MODEL_RELEASE 태그 필요, 사설 레포는 GITHUB_TOKEN).
_ART_DIR = Path(os.environ.get("CANARY_MODEL_DIR", _REPO_ROOT / "ml" / "artifacts"))
_RELEASE_ASSETS = ("tagger.pt", "tagger_meta.json", "distribution_ref.json",
                   "hashes.json", "lott_ranks.csv")  # lott_ranks.csv: 복권성 순위표(선택)
logger = logging.getLogger(__name__)

try:
    import torch
    from ml import seqfeat
    from ml.gru_model import GRUTagger
    _IMPORT_ERROR = None
except Exception as e:  # torch 미설치 등 — score는 None 폴백
    _IMPORT_ERROR = e

# requests는 아래 Release 다운로드(_ensure_artifacts)가 직접 쓴다.
# 시세·지수·종목명은 2026-08-26부터 KRX Open API(synthetic_data.market.krx_api) 경유.
import requests

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
        repo = get("model.repo", "Cloud9-capstone-2026/cloud9", env_override="CANARY_MODEL_REPO")
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
    커버된 구간은 네트워크 없음, 부족 구간만 KRX Open API 증분 조회.
    실패 종목은 건너뜀(해당 종목 시장 컨텍스트는 결측 → 마스크)."""
    from price_cache import get_ohlcv  # 지연 import (모듈 로드 의존 최소화)

    start = d_min - timedelta(days=_PRICE_LOOKBACK_DAYS)
    df = get_ohlcv(tickers, start, d_max)
    if df.empty:
        raise RuntimeError("시세 조회 전면 실패 — layer3 스킵")
    return df


def _fetch_index_df(price_df) -> pd.DataFrame:
    """코스피 지수 종가 — KRX Open API 날짜별 캐시(krx_api.index_close). 시세 조회가
    같은 날짜들을 이미 캐시했으므로 보통 네트워크 없음. 실패 시 NaN 지수(driver 피처
    결측 → 마스크)로 진행한다."""
    days = sorted(price_df["거래일자"].unique())
    try:
        from synthetic_data.market import krx_api
        return pd.DataFrame({"거래일자": days,
                             "종가": [krx_api.index_close(d) for d in days]})
    except Exception:
        logger.warning("코스피 지수 조회 실패 — driver 피처 결측으로 진행", exc_info=True)
    return pd.DataFrame({"거래일자": days, "종가": [np.nan] * len(days)})


def _account_metrics(aggregates: pd.DataFrame) -> dict | None:
    """계좌 행동 지표 — ml.train.make_distribution_ref와 동일 정의.

    pipeline.monitor의 분포 점검(v1)이 학습 분포와 대조하는 값. 산출 실패는
    None(점검 unavailable)일 뿐 채점에는 영향 없다."""
    try:
        ag = aggregates[aggregates["window"] == "full"]
        if ag.empty:
            return None
        row = ag.iloc[0]  # 단일 계좌 전제 (score_from_trades와 동일)

        def _f(key):
            v = row.get(key)
            return None if v is None or pd.isna(v) else float(v)

        n_buys = _f("n_buys") or 0.0
        n_sells = _f("n_sells") or 0.0
        n_tr = n_buys + n_sells
        return {
            "turnover_annual": _f("turnover_annual"),
            "buy_share": (n_buys / n_tr) if n_tr > 0 else None,
            "mean_abn_vol_at_buy": _f("mean_abn_vol_at_buy"),
            "mean_lott_at_buy": _f("mean_lott_at_buy"),
            "holding_days_mean": _f("holding_days_mean"),
            "n_trades": n_tr,
        }
    except Exception as e:  # noqa: BLE001 — 지표는 부가 정보, 채점을 막지 않음
        logger.warning("계좌 지표 산출 실패 — 분포 점검 생략: %r", e)
        return None


def _score_windows(model, M, W: int):
    """전체 시퀀스 M[N, C]의 거래별 편향 확률 [N, n_targets] (sigmoid 완료).

    모델은 학습 조건상 한 번에 W(max_len)건까지만 본다. N > W면 오래된 거래를
    절단하는 대신 창을 거래 1건씩 밀며 여러 번 채점한다:
      위치 0..W-1   첫 창 [0, W)에서 채점 — 이력이 그것뿐(학습 시퀀스의 시작과
                    같은 상황)
      위치 t >= W   직전 W-1건을 담은 창 [t-W+1, t]의 마지막 위치로 채점 —
                    모든 거래가 균일하게 최대 문맥을 확보(학습 시퀀스의 마지막
                    위치와 같은 조건)
    창들은 서로 독립이라 배치로 묶어 한 번에 순전파한다.
    """
    N = M.shape[0]
    with torch.no_grad():
        if N <= W:
            return torch.sigmoid(model(M.unsqueeze(0), torch.tensor([N])))[0, :N]
        parts = [torch.sigmoid(model(M[:W].unsqueeze(0), torch.tensor([W])))[0]]
        CHUNK = 512  # 꼬리 창 배치 상한 — 초대형 계좌 메모리 절충
        for s in range(W, N, CHUNK):
            tails = torch.stack(
                [M[t - W + 1: t + 1] for t in range(s, min(s + CHUNK, N))])
            lens = torch.full((len(tails),), W, dtype=torch.long)
            parts.append(torch.sigmoid(model(tails, lens))[:, W - 1])
        return torch.cat(parts)


def _attach_evidence(model, M, W, params, per_trade, positions) -> None:
    """per_trade 각 항목에 evidence(XAI 근거) 부착 — 실패해도 채점은 유지.

    positions: per_trade 각 항목의 시퀀스 내 위치(시장 맥락 없는 거래 제외로
    어긋날 수 있어 명시적으로 받는다). 창 규약은 _score_windows와 동일 —
    위치 t < min(N, W)는 첫 창에서, t >= W는 자기 꼬리 창의 마지막 위치에서
    근거를 계산하므로 점수와 근거가 같은 문맥을 공유한다.

    편향별 값 = {trade_share·context_share(현재 거래 대 과거 문맥의 기여
    절댓값 비율 — 합 1), features(값 채널 10개 전부, |기여| 내림차순 —
    feature는 표시명, attribution은 로짓 단위 부호 유지)}.
    관측여부 채널은 결측 표현용 내부 구조라 features에서 제외한다 — 그 몫은
    trade_share/context_share 총량에는 반영되어 있다.
    """
    try:
        from models.xai import evidence_summary, trade_attributions

        first_len = min(M.shape[0], W)
        first = [t for t in positions if t < first_len]
        jobs = []  # (per_trade 항목, 해당 거래의 기여도 [4, T, C], 창 내 위치)
        by_pos = dict(zip(positions, per_trade))
        if first:
            attrs = trade_attributions(model, M[:first_len], first_len,
                                       targets=first)
            jobs += [(by_pos[t], attrs[i], t) for i, t in enumerate(first)]
        for t in (t for t in positions if t >= W):
            attrs = trade_attributions(model, M[t - W + 1: t + 1], W,
                                       targets=[W - 1])
            jobs.append((by_pos[t], attrs[0], W - 1))

        for entry, attr, t in jobs:
            ev = {}
            for j, p in enumerate(params):
                s = evidence_summary(attr[j], t)
                own, ctx = abs(s["own_total"]), abs(s["context_total"])
                denom = own + ctx
                ev[p] = {
                    "trade_share":
                        round(own / denom, 2) if denom > 1e-9 else None,
                    "context_share":
                        round(ctx / denom, 2) if denom > 1e-9 else None,
                    "features": [
                        {"feature": f["name"], "attribution": f["attribution"]}
                        for f in s["features"]
                        if not f["feature"].startswith("m_")],
                }
            entry["evidence"] = ev
    except Exception as e:  # noqa: BLE001 — 근거는 부가 정보, 채점을 막지 않음
        logger.warning("XAI 근거 계산 실패 — evidence 없이 진행: %r", e)


def _prepare_features(trades: pd.DataFrame, price_df=None, index_df=None):
    """합성 스키마 거래 → 피처 테이블(build_features 출력)까지의 준비 단계.

    채점(score_from_trades)과 지표 산출(account_metrics)이 공유 — 계좌 지표의
    산식이 채점 경로와 어긋날 수 없게 한 곳으로 모은다. 시세 미지정 시 조회."""
    from synthetic_data.features import build_features

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
    from lott_table import get_lott_table  # 시장 전체 복권성 순위표 (없으면 None → 옛 경로)
    return trades, build_features(trades, price_df, index_df, windows=(None,),
                                  lott_table=get_lott_table())


def score_from_trades(trades: pd.DataFrame, price_df=None, index_df=None) -> dict | None:
    """합성 스키마 거래(agent_id·종목코드 등 features.REQUIRED_COLUMNS)를 단일
    계좌로 보고 채점. price/index 미지정 시 KRX Open API에서 조회(테스트에서는 주입)."""
    try:
        model, meta = _load_artifacts()
        trades, out = _prepare_features(trades, price_df, index_df)
        ev = seqfeat.attach_trade_rows(out["events"], trades)
        feat = seqfeat.event_features(ev)

        # 시장 맥락(시세 기반 피처)이 전무한 거래는 채점 대상에서 제외 —
        # "시세 조회 실패"라는 시스템 사정이 결측 신호로 둔갑해 점수에 스며드는
        # 것을 차단한다. 이런 결측은 학습 데이터에 없던 원인이라 모델의 해석을
        # 신뢰할 수 없다. (매수의 보유기간처럼 정의상 없는 구조적 결측은 학습이
        # 아는 정당한 결측이라 그대로 채점한다.) 제외된 거래는 시퀀스 문맥으로는
        # 남고, detect.py에서 deep 없이 2계층 판정된다(layers_available=2).
        no_market = set(
            feat.loc[feat[["abn", "r1", "r5"]].isna().all(axis=1), "_trade_row"]
            .astype(int)
        )

        # 절단 없이 전체 이력을 시퀀스로 — max_len은 "한 번에 보는 창 크기"일
        # 뿐 채점 범위의 한계가 아니다 (창 분할은 _score_windows).
        ids, X, lengths, rows = seqfeat.build_sequences(
            feat, meta["norm_stats"], max(len(feat), 1), return_rows=True
        )
        if not ids:
            return None

        # 단일 계좌 전제 — 첫 계좌 기준
        N = int(lengths[0])
        M = torch.from_numpy(X[0, :N])  # [N, 17] 정규화 완료 전체 시퀀스
        seq_rows = rows[0, :N]          # 각 위치의 trades 행 번호
        W = int(meta["max_len"])
        P = _score_windows(model, M, W).numpy()  # [N, 4] 거래별 편향 귀속 확률
        params = [meta["attr_param"][a] for a in meta["attrs"]]
        src = (trades["_src_row"].to_numpy()
               if "_src_row" in trades.columns else trades.index.to_numpy())

        per_trade = []
        positions = []  # 각 per_trade 항목의 시퀀스 내 위치 (evidence 매칭용)
        for i in range(N):
            r = int(seq_rows[i])
            if r in no_market:
                continue
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
            positions.append(i)
        if not per_trade:
            logger.warning("전 거래 시장 맥락 결측 — layer3 스킵 (2계층 폴백)")
            return None

        _attach_evidence(model, M, W, params, per_trade, positions)

        return {
            "per_trade": per_trade,
            "lstm_score": round(max(e["trade_score"] for e in per_trade), 4),
            "bias_mean": {p: round(float(P[positions, j].mean()), 4)
                          for j, p in enumerate(params)},
            "n_events": len(per_trade),
            "account_metrics": _account_metrics(out["aggregates"]),
        }
    except Exception as e:
        logger.warning("layer3 채점 실패 — 2계층 폴백: %r", e)
        return None


def _to_synthetic(standard_df: pd.DataFrame, user_id: str = "user") -> pd.DataFrame | None:
    """백엔드 표준 컬럼(날짜·종목명·매매구분·체결수량·체결단가·총거래금액) →
    합성 스키마 변환. score_account와 account_metrics가 공유.

    종목명 → 종목코드 매핑(feature_eng.get_ticker_code) — 매핑 실패 종목은
    가짜 코드("NM_종목명")로 남겨 포지션 추적은 유지하되 시장 컨텍스트만
    결측(마스크) 처리되게 한다. 유효 행이 없으면 None."""
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
    return None if trades.empty else trades


def score_account(standard_df: pd.DataFrame, user_id: str = "user") -> dict | None:
    """백엔드 표준 컬럼 입력 → 합성 스키마 변환 후 score_from_trades에 위임.

    반환의 per_trade[i]["row"]는 standard_df의 행 위치(0-base, 원래 순서 기준)
    — 호출부(detect.py)가 거래별 점수를 자기 행에 매칭할 때 쓴다."""
    try:
        trades = _to_synthetic(standard_df, user_id)
        if trades is None:
            return None
        return score_from_trades(trades)
    except Exception as e:
        logger.warning("layer3 입력 변환 실패 — 2계층 폴백: %r", e)
        return None


def account_metrics(standard_df: pd.DataFrame, user_id: str = "user",
                    price_df=None, index_df=None) -> dict | None:
    """분포 점검용 계좌 지표만 산출 — 채점보다 훨씬 싸고 모델 아티팩트 불필요.

    detect.py가 3계층 채점(XAI 포함, 분 단위) 전에 호출해, 학습 분포 밖 계좌는
    채점을 아예 생략할 수 있게 한다(분포 점검 v2). 변환·피처 계산을 채점
    경로(_to_synthetic → _prepare_features)와 공유하므로 산식이 어긋날 수 없다.
    실패는 None — pipeline.monitor가 unavailable로 처리."""
    # 분포 기준(distribution_ref.json)은 모델과 같은 릴리스 번들로 내려오는데,
    # 점검이 채점보다 먼저 돌므로 확보를 여기서 시도해 둔다 — 새 서버의 첫
    # 분석부터 기준 파일이 준비되게. 실패(태그 미설정 등)해도 지표 산출은
    # 계속한다: 모델 없는 2계층 모드 서버는 정상 운영 상태다.
    try:
        _ensure_artifacts()
    except Exception:  # noqa: BLE001
        pass
    try:
        trades = _to_synthetic(standard_df, user_id)
        if trades is None:
            return None
        _, out = _prepare_features(trades, price_df, index_df)
        return _account_metrics(out["aggregates"])
    except Exception as e:
        logger.warning("계좌 지표 산출 실패 — 분포 점검 생략: %r", e)
        return None
