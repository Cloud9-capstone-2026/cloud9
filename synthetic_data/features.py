"""
피처 빌더 (7-3): 13필드 거래 CSV + pykrx 시세·지수 → 3계층 ML 입력 피처.

원칙
- 입력은 거래 CSV(DataFrame)와 시세·지수뿐 — 생성기 내부 객체(model/agent) 의존
  금지, RNG 없음(결정적). 합성 학습 데이터와 실계좌 추론이 '같은 코드 경로'를
  지나는 것이 sim-to-real의 물리적 보장이다(DECISIONS.md §2-6).
- 절단 규칙(KCMI 22-02 p42의 CSV 버전): 매수 기록이 없는(또는 보유 수량을 초과하는)
  매도 수량은 원가 미상 — 수익률·보유기간 산출에서 제외하고 활동량·대금에는 포함.
  합성의 기초보유 매도와 실계좌의 조회기간 절단이 같은 코드로 처리된다.
- 실계좌 CSV에는 부분매도가 존재한다(합성은 전량청산). 부분매도는 수량 차감으로
  처리하고 평균단가·최초매입일을 유지한다. 하루 안 처리 순서는 행 순서를 신뢰
  (처리시간은 블랙리스트라 사용 불가 — 동일 종목 당일 매수·매도 조합의 순서
  모호성은 알려진 한계).
- 피처 블랙리스트(DECISIONS §2-6): 처리시간(로드 시 드롭), 체결가의 일중 위치,
  투입비율 미시패턴, cost_ratio(합성에서 상수 요율이라 무정보). 편향라벨 컬럼은
  분리 반환만 하고 피처 계산에 절대 쓰지 않는다(없어도 동작 — 실계좌 형태).

시장 컨텍스트 정의 (생성기 채널과 동일 — 채널-피처 정합이 7단계 감사의 핵심 교훈):
- abn_vol   : 전일 거래량 / 그 이전 ATTN_VOL_AVG_DAYS일 평균 (shift로 look-ahead 차단)
- prior_ret1/5 : 전일 기준 최근 1일/ATTN_RET_DAYS일 누적 수익률
- driver    : '전일에 끝난' 지수 수익률 (model._index_ret와 동일 shift(1) 규약)
- lott_rank : lott.compute_monthly_lott의 직전 달 계산치를 적용월에 매핑, 월별 pct 랭크

측정 주의: 회전율·보유평가액(MTM)은 'CSV-관측 가능' 버전이다 — 조회기간 이전
취득분(합성의 기초보유)은 볼 수 없어 분모가 과소평가된다. 실계좌도 동일한 편향을
가지므로 학습/추론 간에는 일관(DECISIONS §2-5). 하네스(kcmi_metrics)의 시딩 버전과
값이 다른 것이 정상이며, 처분(PGR/PLR)은 양쪽 모두 절단분을 제외하므로 일치해야 한다.
"""

import ast
from collections import defaultdict

import numpy as np
import pandas as pd

from . import config
from .market.lott import apply_month_rank, compute_monthly_lott

# 실계좌 입력 스키마(추론 시 기대 입력): 합성 13필드에서 처리시간·편향라벨을 뺀 11필드
#   거래일자, 고객ID, 종목코드, 거래구분, 거래수량, 거래단가, 거래금액,
#   수수료, 거래세, 정산금액, 예수금
# 계좌 식별 컬럼은 실계좌 '고객ID' / 합성 'agent_id' 모두 수용해 내부적으로
# agent_id로 정규화한다. 수수료·거래세·정산금액·예수금은 현재 피처에 미사용
# (cost_ratio는 블랙리스트, 예수금 기반 현금비율 피처는 향후 후보) — 없어도 동작.
REQUIRED_COLUMNS = [
    "거래일자", "종목코드", "거래구분", "거래수량", "거래단가", "거래금액",
]
_ID_ALIASES = {"agent_id", "고객id", "고객"}  # 정규화(공백 제거·소문자) 후 비교
BLACKLIST_COLUMNS = ["처리시간"]  # 아티팩트(uniform) — 로드 단계에서 물리적으로 제거

# 계좌·윈도 집계 피처 명세: 정의·권장 변환(왜도 처리)·유효성 조건.
# 변환은 여기서 '적용하지 않고' 명세만 제공한다 — 원값 보존, 적용은 ML 전처리 몫.
AGGREGATE_SPEC = {
    "pgr": {"정의": "이익 실현율 Σgs/Σgo (position-day)", "변환": None, "유효성": "disp_valid"},
    "plr": {"정의": "손실 실현율 Σls/Σlo", "변환": None, "유효성": "disp_valid"},
    "pgr_plr_ratio": {"정의": "처분효과 위험비율 PGR/PLR", "변환": "log", "유효성": "disp_valid"},
    "n_buys": {"정의": "매수 건수", "변환": "log1p", "유효성": None},
    "n_sells": {"정의": "매도 건수", "변환": "log1p", "유효성": None},
    "active_days": {"정의": "거래 발생 일수", "변환": None, "유효성": None},
    "turnover_annual": {
        "정의": "일평균 (매수+매도대금)/2 ÷ 일평균 MTM × 250 — CSV-관측 가능 버전(모듈 docstring)",
        "변환": "log1p", "유효성": "mtm_days>0",
    },
    "oc_timing_corr": {"정의": "일별 매수건수 × driver(전일 지수수익률) Pearson", "변환": None,
                       "유효성": "매수 존재·분산>0"},
    "buy_after_up_ratio": {"정의": "driver>0인 날 매수 비중", "변환": None, "유효성": "n_buys>0"},
    "mean_lott_at_buy": {"정의": "매수 종목 LOTT 월별 pct 랭크 평균", "변환": None, "유효성": "n_buys>0"},
    "mean_abn_vol_at_buy": {"정의": "매수 시점 abn_vol 평균", "변환": "log1p", "유효성": "n_buys>0"},
    "mean_prior_ret1_at_buy": {"정의": "매수 시점 전일 종목수익률 평균", "변환": None, "유효성": "n_buys>0"},
    "holding_days_mean": {"정의": "원가 확인 매도의 보유 거래일수 평균", "변환": "log1p",
                          "유효성": "known 매도 존재"},
    "holding_days_median": {"정의": "동 중앙값", "변환": None, "유효성": "known 매도 존재"},
    "return_at_sale_mean": {"정의": "원가 확인 매도의 실현수익률 평균", "변환": None,
                            "유효성": "known 매도 존재"},
    "nstock_mean": {"정의": "보유일 기준 일평균 보유종목수", "변환": "log1p", "유효성": "보유일>0"},
    "disp_valid": {"정의": "PGR/PLR 최소 관측 필터(go≥10, lo≥10, gs≥2, ls≥2) 통과 여부",
                   "변환": None, "유효성": None},
}

# 하네스와 동일한 최소 관측 필터 (kcmi_metrics._adj_disposition)
_DISP_MIN_OBS, _DISP_MIN_SOLD = 10, 2


def load_trades_csv(path):
    """거래 CSV 로드 → (trades_df, labels_df|None).

    합성(13필드, agent_id)과 실계좌(11필드, 고객ID) 스키마 모두 수용 — 계좌 컬럼을
    agent_id로 정규화하고, 블랙리스트 컬럼 드롭 + 편향라벨 분리."""
    df = pd.read_csv(path, dtype=str)

    def _norm(name: str) -> str:
        return name.replace(" ", "").replace("_", "").lower()

    id_cols = [c for c in df.columns if _norm(c) in {_norm(a) for a in _ID_ALIASES}
               or _norm(c) in ("고객id", "agentid", "고객번호", "계좌id")]
    if not id_cols:
        raise ValueError("계좌 식별 컬럼 없음 (agent_id 또는 고객ID 계열 필요)")
    df = df.rename(columns={id_cols[0]: "agent_id"})

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"필수 컬럼 누락: {missing}")
    for c in ("거래수량", "거래단가", "거래금액"):
        df[c] = pd.to_numeric(df[c])
    df["거래일자"] = pd.to_datetime(df["거래일자"]).dt.date

    labels = None
    if "편향라벨" in df.columns:  # 합성 데이터 전용 — 분리만 하고 피처 계산 미사용
        labels = (
            df.groupby("agent_id")["편향라벨"].first()
            .apply(ast.literal_eval).apply(pd.Series)
        )
        df = df.drop(columns=["편향라벨"])
    df = df.drop(columns=[c for c in BLACKLIST_COLUMNS if c in df.columns])
    return df, labels


def _market_context(price_df, index_df, d_min, d_max):
    """시장 컨텍스트 테이블 일괄 구축 (모듈 docstring의 정의 그대로)."""
    span = price_df[(price_df["거래일자"] >= d_min) & (price_df["거래일자"] <= d_max)]
    trading_days = sorted(span["거래일자"].unique())

    close_map = {
        (tk, d): float(c)
        for tk, d, c in zip(span["종목코드"], span["거래일자"], span["종가"])
    }
    close_ff: dict = {}
    for tk in span["종목코드"].unique():
        last = None
        for d in trading_days:
            c = close_map.get((tk, d))
            if c is not None:
                last = c
            if last is not None:
                close_ff[(tk, d)] = last

    # 종목 컨텍스트 (전체 히스토리로 계산 후 조회 — 초기 구간 rolling 확보)
    vol_wide = price_df.pivot(index="거래일자", columns="종목코드", values="거래량").sort_index()
    abn = (
        vol_wide / vol_wide.shift(1).rolling(config.ATTN_VOL_AVG_DAYS, min_periods=20).mean()
    ).shift(1)
    close_wide = price_df.pivot(index="거래일자", columns="종목코드", values="종가").sort_index()
    close_ffill = close_wide.ffill()
    ret1 = close_ffill.pct_change().shift(1)
    retN = close_ffill.pct_change(config.ATTN_RET_DAYS).shift(1)
    abn_map = abn.stack().to_dict()
    ret1_map = ret1.stack().to_dict()
    retN_map = retN.stack().to_dict()

    idx = index_df.sort_values("거래일자").reset_index(drop=True)
    idx_ret = idx["종가"].pct_change()
    driver_map = dict(zip(idx["거래일자"], idx_ret.shift(1)))

    tickers = sorted(price_df["종목코드"].unique())
    lott_rank = apply_month_rank(compute_monthly_lott(price_df, index_df, tickers))

    return {
        "trading_days": trading_days,
        "close_map": close_map,
        "close_ff": close_ff,
        "abn": abn_map,
        "ret1": ret1_map,
        "retN": retN_map,
        "driver": driver_map,
        "lott_rank": lott_rank,
    }


def build_features(trades, price_df, index_df, windows=(None, 63, 21)):
    """거래 CSV → {"events", "account_days", "aggregates"} 3테이블.

    events       : 거래 1건=1행 (3계층 시퀀스 입력). 매도는 원가 확인 여부(basis) 포함.
    account_days : 계좌×거래일 패널 — 처분 관측(장 시작 스냅샷 규약: 매수 당일 제외
                   자동 충족, kcmi_metrics._replay와 동일)과 보유종목수·MTM(장 마감).
    aggregates   : 계좌×관측창 집계 (AGGREGATE_SPEC 참조). 관측창은 기간 말 기준
                   직전 N거래일(None=전체) — 실서비스의 '최근 N일 조회'와 정합.
    """
    d_min, d_max = trades["거래일자"].min(), trades["거래일자"].max()
    ctx = _market_context(price_df, index_df, d_min, d_max)
    calendar = sorted(set(ctx["trading_days"]) | set(trades["거래일자"].unique()))
    day_index = {d: i for i, d in enumerate(calendar)}

    trades_by_day: dict = defaultdict(list)
    for row in trades.itertuples():  # 행 순서 = 하루 안 처리 순서 (docstring 참조)
        trades_by_day[row.거래일자].append(row)

    positions: dict = defaultdict(dict)  # aid -> {tk: [qty, avg, first_day]}
    event_rows, day_rows = [], []

    for d in calendar:
        day_trades = trades_by_day.get(d, [])
        sold_today = {(t.agent_id, t.종목코드) for t in day_trades if t.거래구분 == "매도"}

        # (1) 장 시작 스냅샷 — 처분 관측 (오늘 거래 적용 전 → 매수 당일 제외 자동)
        paper: dict = {}
        for aid, pmap in positions.items():
            if not pmap:
                continue
            go = gs = lo = ls = 0
            for tk, pos in pmap.items():
                c = ctx["close_map"].get((tk, d))
                if c is None:
                    continue
                sold = (aid, tk) in sold_today
                if c >= pos[1]:  # 등호 포함 (agent 판단·하네스와 동일)
                    go += 1
                    gs += sold
                else:
                    lo += 1
                    ls += sold
            if go or lo:
                paper[aid] = [go, gs, lo, ls]

        # (2) 오늘 거래 적용 (행 순서) + 이벤트 피처
        acts: dict = defaultdict(lambda: [0, 0, 0.0, 0.0])  # aid -> [매수n, 매도n, 매수액, 매도액]
        for t in day_trades:
            aid, tk, qty = t.agent_id, t.종목코드, int(t.거래수량)
            drv = ctx["driver"].get(d)
            ev = {
                "agent_id": aid, "거래일자": d, "거래구분": t.거래구분, "종목코드": tk,
                "거래수량": qty, "거래금액": float(t.거래금액),
                "driver": drv,
                "is_after_up": (None if drv is None or pd.isna(drv) else bool(drv > 0)),
                "abn_vol": ctx["abn"].get((d, tk), np.nan),
                "prior_ret1": ctx["ret1"].get((d, tk), np.nan),
                "prior_ret5": ctx["retN"].get((d, tk), np.nan),
                "lott_rank": np.nan,
                "basis": None, "return_at_sale": np.nan, "holding_days": np.nan,
            }
            lr = ctx["lott_rank"].get((d.year, d.month))
            if lr is not None:
                ev["lott_rank"] = float(lr.get(tk, np.nan))

            if t.거래구분 == "매수":
                a = acts[aid]
                a[0] += 1
                a[2] += float(t.거래금액)
                pos = positions[aid].get(tk)
                price_ = float(t.거래단가)
                if pos is None:
                    positions[aid][tk] = [qty, price_, d]
                else:  # 병합: 수량 합산 + 가중평균단가, 최초매입일 유지
                    nq = pos[0] + qty
                    pos[1] = (pos[1] * pos[0] + price_ * qty) / nq
                    pos[0] = nq
            else:  # 매도 — 절단 규칙 + 부분매도
                a = acts[aid]
                a[1] += 1
                a[3] += float(t.거래금액)
                pos = positions[aid].get(tk)
                if pos is None:
                    ev["basis"] = "unknown"  # 원가 미상 (조회기간 이전 취득분)
                else:
                    ev["basis"] = "known" if qty <= pos[0] else "partial"
                    ev["return_at_sale"] = float(t.거래단가) / pos[1] - 1.0
                    ev["holding_days"] = day_index[d] - day_index[pos[2]]
                    pos[0] -= min(qty, pos[0])
                    if pos[0] <= 0:
                        del positions[aid][tk]
            event_rows.append(ev)

        # (3) 장 마감 — 보유종목수·MTM
        eod: dict = {}
        for aid, pmap in positions.items():
            if not pmap:
                continue
            mtm = sum(
                pos[0] * ctx["close_ff"].get((tk, d), 0.0) for tk, pos in pmap.items()
            )
            eod[aid] = (len(pmap), mtm)

        for aid in set(paper) | set(acts) | set(eod):
            go, gs, lo, ls = paper.get(aid, [0, 0, 0, 0])
            nb, ns, bv, sv = acts.get(aid, [0, 0, 0.0, 0.0])
            npos, mtm = eod.get(aid, (0, 0.0))
            day_rows.append({
                "agent_id": aid, "거래일자": d,
                "go": go, "gs": gs, "lo": lo, "ls": ls,
                "n_buys": nb, "n_sells": ns, "buy_value": bv, "sell_value": sv,
                "n_positions": npos, "mtm": mtm,
            })

    events = pd.DataFrame(event_rows)
    account_days = pd.DataFrame(day_rows)

    aggs = []
    for w in windows:
        days_w = calendar if w is None else calendar[-w:]
        label = "full" if w is None else f"{w}d"
        aggs.append(_aggregate_window(events, account_days, days_w, ctx, label))
    aggregates = pd.concat(aggs, ignore_index=True)

    return {"events": events, "account_days": account_days, "aggregates": aggregates}


def _aggregate_window(events, account_days, days_w, ctx, label):
    dset = set(days_w)
    ad = account_days[account_days["거래일자"].isin(dset)]
    ev = events[events["거래일자"].isin(dset)]

    g = ad.groupby("agent_id")
    out = g[["go", "gs", "lo", "ls", "n_buys", "n_sells", "buy_value", "sell_value"]].sum()
    out["active_days"] = g.apply(
        lambda x: int(((x["n_buys"] + x["n_sells"]) > 0).sum()), include_groups=False
    )
    pos_days = ad[ad["n_positions"] > 0].groupby("agent_id")
    out["nstock_mean"] = pos_days["n_positions"].mean()
    mtm_days = ad[ad["mtm"] > 0].groupby("agent_id")
    mean_mtm = mtm_days["mtm"].mean()
    n_mtm_days = mtm_days.size()
    # 일평균 유량/일평균 MTM × 250 — 분모는 MTM>0인 날 기준 (CSV-관측 가능 버전)
    out["turnover_annual"] = (
        ((out["buy_value"] + out["sell_value"]) / 2.0 / n_mtm_days) / mean_mtm * 250.0
    )

    out["pgr"] = out["gs"] / out["go"]
    out["plr"] = out["ls"] / out["lo"]
    # PLR=0(또는 관측 0) → inf/NaN 발생 — validity 플래그와 별개로 값 자체를 NaN으로
    # 정리해 플래그를 무시하는 다운스트림도 안전하게.
    out["pgr_plr_ratio"] = (out["pgr"] / out["plr"]).replace([np.inf, -np.inf], np.nan)
    out["disp_valid"] = (
        (out["go"] >= _DISP_MIN_OBS) & (out["lo"] >= _DISP_MIN_OBS)
        & (out["gs"] >= _DISP_MIN_SOLD) & (out["ls"] >= _DISP_MIN_SOLD)
    )

    buys = ev[ev["거래구분"] == "매수"]
    gb = buys.groupby("agent_id")
    out["buy_after_up_ratio"] = gb["is_after_up"].mean()
    out["mean_lott_at_buy"] = gb["lott_rank"].mean()
    out["mean_abn_vol_at_buy"] = gb["abn_vol"].mean()
    out["mean_prior_ret1_at_buy"] = gb["prior_ret1"].mean()

    sells = ev[(ev["거래구분"] == "매도") & (ev["basis"] == "known")]
    gs_ = sells.groupby("agent_id")
    out["holding_days_mean"] = gs_["holding_days"].mean()
    out["holding_days_median"] = gs_["holding_days"].median()
    out["return_at_sale_mean"] = gs_["return_at_sale"].mean()

    # 매수 타이밍 × driver 상관 (일별 매수건수 벡터를 창 전체로 펼쳐 0 채움)
    cnt = (
        ad.pivot_table(index="agent_id", columns="거래일자", values="n_buys",
                       aggfunc="sum", fill_value=0)
        .reindex(columns=days_w, fill_value=0)
    )
    dv = np.array([ctx["driver"].get(d, np.nan) for d in days_w], dtype=float)
    ok = ~np.isnan(dv)
    X = cnt.to_numpy()[:, ok].astype(float)
    D = dv[ok]
    Xc = X - X.mean(axis=1, keepdims=True)
    Dc = D - D.mean()
    den = np.sqrt((Xc ** 2).sum(axis=1) * (Dc ** 2).sum())
    corr = np.where(den > 0, (Xc @ Dc) / np.where(den > 0, den, 1.0), np.nan)
    out["oc_timing_corr"] = pd.Series(corr, index=cnt.index)

    out = out.reset_index()
    out.insert(1, "window", label)
    return out
