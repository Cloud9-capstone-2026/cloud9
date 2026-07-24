"""
이벤트 시퀀스 텐서화 — 학습(ml.train_gru)과 추론(backend.models.layer3)이 공유하는
순수 모듈. features.build_features의 events 테이블만 입력으로 받는다(생성기 객체
의존 금지 — synthetic_data.features와 같은 sim-to-real 원칙).

피처 17채널 = 기본 10 + 결측 마스크 7:
  side       매수=1 / 매도=0
  amt        log1p(거래금액)
  gap        log1p(직전 거래와의 간격 일수) — 계좌 내 첫 거래는 0
  abn        log1p(전일 비정상거래량)          ┐
  r1         전일 종목수익률                   │
  r5         최근 5일 종목수익률               │ 시장 컨텍스트 — 결측 가능
  lott       LOTT 월별 pct 랭크               │ (실계좌에서 시세 조회 실패·유니버스 밖
  drv        전일 지수수익률                   │  종목이면 NaN → 마스크 0 + 값 0 대치.
  ras        매도 실현수익률(원가 확인분만)     │  학습 데이터에도 초기 구간 결측이 있어
  hld        log1p(보유 거래일수)             ┘  모델이 마스크 패턴을 학습 때부터 겪는다)

정규화: side·마스크 제외 9채널을 학습 세트에서 fit한 (mean, std)로 z-score.
NaN은 정규화 후 0(=평균) 대치, 대응 마스크 채널이 관측 여부를 전달한다.
"""

import numpy as np
import pandas as pd

BASE_FEATURES = ["side", "amt", "gap", "abn", "r1", "r5", "lott", "drv", "ras", "hld"]
MASKED_FEATURES = ["abn", "r1", "r5", "lott", "drv", "ras", "hld"]  # 결측 가능 채널
NORM_FEATURES = [f for f in BASE_FEATURES if f != "side"]  # z-score 대상
N_CHANNELS = len(BASE_FEATURES) + len(MASKED_FEATURES)  # 17


def attach_trade_rows(events: pd.DataFrame, trades: pd.DataFrame) -> pd.DataFrame:
    """events(build_features 출력, 거래와 1:1)에 원본 trades의 행 위치 컬럼을 부착.

    build_features의 events 순서 = 캘린더 일 오름차순 × 일 내 원본 행 순서
    = trades를 거래일자로 안정 정렬한 순서. 이 사상으로 events[i]가 trades의
    몇 번째 행인지(_trade_row)를 복원한다 — trade_labels(행 1:1)와의 조인,
    layer3의 per_trade 행 매칭이 모두 이 컬럼 하나로 정렬된다.
    """
    order = np.argsort(
        pd.to_datetime(trades["거래일자"]).to_numpy(), kind="stable"
    )
    ev = events.reset_index(drop=True).copy()
    if len(ev) != len(order):
        raise ValueError(f"events({len(ev)}) != trades({len(order)}) — 1:1 가정 위반")
    ev["_trade_row"] = order
    return ev


def event_features(events: pd.DataFrame) -> pd.DataFrame:
    """events 테이블 → 계좌·시간순 정렬된 피처 프레임(agent_id + BASE_FEATURES).

    events는 build_features가 캘린더 순서로 만든 것을 신뢰하되, 계좌별 안정 정렬로
    (agent_id, 거래일자, 원래 행 순서)를 보장한다. `_trade_row` 컬럼이 있으면
    (attach_trade_rows 부착) 그대로 통과시킨다 — 라벨 조인·행 매칭용.
    """
    df = events.reset_index(drop=True).copy()
    df["_ord"] = np.arange(len(df))
    df = df.sort_values(["agent_id", "거래일자", "_ord"], kind="stable")

    out = pd.DataFrame(index=df.index)
    out["agent_id"] = df["agent_id"].astype(str)
    if "_trade_row" in df.columns:
        out["_trade_row"] = df["_trade_row"].astype("int64")
    out["side"] = (df["거래구분"] == "매수").astype("float32")
    out["amt"] = np.log1p(df["거래금액"].astype(float).clip(lower=0))
    days = pd.to_datetime(df["거래일자"])
    gap = days.groupby(df["agent_id"]).diff().dt.days
    out["gap"] = np.log1p(gap.fillna(0).clip(lower=0))
    out["abn"] = np.log1p(pd.to_numeric(df["abn_vol"], errors="coerce").clip(lower=0))
    out["r1"] = pd.to_numeric(df["prior_ret1"], errors="coerce")
    out["r5"] = pd.to_numeric(df["prior_ret5"], errors="coerce")
    out["lott"] = pd.to_numeric(df["lott_rank"], errors="coerce")
    out["drv"] = pd.to_numeric(df["driver"], errors="coerce")
    out["ras"] = pd.to_numeric(df["return_at_sale"], errors="coerce")
    out["hld"] = np.log1p(pd.to_numeric(df["holding_days"], errors="coerce").clip(lower=0))
    return out


def fit_norm_stats(feat: pd.DataFrame) -> dict:
    """학습 세트 피처 프레임에서 정규화 통계 fit (결측 제외 mean/std)."""
    stats = {}
    for f in NORM_FEATURES:
        v = feat[f].dropna()
        std = float(v.std())
        stats[f] = {"mean": float(v.mean()), "std": std if std > 1e-8 else 1.0}
    return stats


def build_sequences(feat: pd.DataFrame, norm_stats: dict, max_len: int,
                    return_rows: bool = False):
    """피처 프레임 → (agent_ids, X[N, max_len, 17], lengths[N][, rows[N, max_len]]).

    - z-score 후 NaN→0 대치, 마스크 채널(관측=1) 부착
    - 계좌당 최근 max_len건만 사용(오래된 앞부분 절단), 뒤쪽 패딩
    - return_rows=True: 각 시퀀스 위치의 원본 trades 행 번호(_trade_row) 행렬도
      반환(패딩 = -1) — 시퀀스 태깅 라벨 정렬·거래별 출력 매칭용.
      feat에 _trade_row가 없으면 ValueError.
    """
    feat = feat.copy()
    for f in NORM_FEATURES:
        s = norm_stats[f]
        feat[f] = (feat[f] - s["mean"]) / s["std"]
    for f in MASKED_FEATURES:
        feat[f"m_{f}"] = feat[f].notna().astype("float32")
    cols = BASE_FEATURES + [f"m_{f}" for f in MASKED_FEATURES]
    feat[BASE_FEATURES] = feat[BASE_FEATURES].fillna(0.0)
    if return_rows and "_trade_row" not in feat.columns:
        raise ValueError("return_rows=True에는 _trade_row 컬럼 필요 (attach_trade_rows)")

    ids, mats, rowlists = [], [], []
    for aid, g in feat.groupby("agent_id", sort=True):
        m = g[cols].to_numpy(dtype="float32")
        if len(m) == 0:
            continue
        ids.append(aid)
        mats.append(m[-max_len:])
        if return_rows:
            rowlists.append(g["_trade_row"].to_numpy(dtype="int64")[-max_len:])

    n = len(ids)
    X = np.zeros((n, max_len, N_CHANNELS), dtype="float32")
    lengths = np.zeros(n, dtype="int64")
    rows = np.full((n, max_len), -1, dtype="int64") if return_rows else None
    for i, m in enumerate(mats):
        X[i, : len(m)] = m
        lengths[i] = len(m)
        if return_rows:
            rows[i, : len(m)] = rowlists[i]
    if return_rows:
        return ids, X, lengths, rows
    return ids, X, lengths
