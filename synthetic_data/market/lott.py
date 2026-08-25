"""
LOTT(1) 월별 합성값 계산 — 생성기(model)와 피처 빌더(features)가 공유하는 순수 모듈.

7-3-1에서 model._prepare_market으로부터 추출(동작 불변 — 시드 7 거래 스트림 exact
검증). KCMI LOTT(1) 3축: FF3 잔차 고유변동성 + 주가(역순) + EISKEW(부록1 모형(7)
공표 계수)의 랭크 합. '이번 달 계산 → 다음 달 적용'(룩어헤드 차단)은 호출 측 규약
— model.get_lott_scores와 features의 적용월 매핑이 담당한다.

시장 정보(시총·PBR·코스닥 여부)는 두 경로로 들어온다.
- 기본(합성 학습 경로): config의 2020-03-02 정적 스냅샷 1개 — 기존 동작 그대로.
- snapshots 지정(실계좌용 월별 순위표 구축): 달마다 그 달 말 스냅샷으로 FF3 요인과
  규모 분류를 다시 계산. 월별 핵심 산식은 _month_lott 하나를 양쪽이 공유한다.
"""

import numpy as np
import pandas as pd

from .. import config


def build_ff3_factors(
    ret_wide: pd.DataFrame, idx_ret: pd.Series, caps=None, pbrs=None
) -> pd.DataFrame:
    """SMB·HML 일별 요인 (6-4, FF3 승격 — KCMI 원 방식과 동일 계열).

    분류는 시총 프리즈 + PBR 프리즈 스냅샷 1개: 시총 중위 2분할 × BM(=1/PBR) 30/70%
    3분할 = 6포트폴리오, 정적 시총가중(VW) 일별 수익률.
    SMB = 소형 3개 평균 − 대형 3개 평균, HML = 고BM 2개 평균 − 저BM 2개 평균.
    caps/pbrs: ticker -> 값 (dict 또는 Series). None이면 config 2020-03-02 스냅샷.
    PBR 결측·0 이하 종목은 BM을 만들 수 없어 요인 구축에서 제외(config 스냅샷은
    이미 그 13종목이 빠져 있어 동작 동일).
    근사 명시: (1) 분류·가중 모두 입력 스냅샷에 고정 (2) 요인 모집단은 ret_wide에
    있는 종목 — 합성 경로는 우리 201종목 계층화 유니버스.
    """
    caps = pd.Series(config.MARKETCAP_20200302 if caps is None else caps, dtype=float)
    pbrs = pd.Series(config.PBR_20200302 if pbrs is None else pbrs, dtype=float)
    caps, pbrs = caps.dropna(), pbrs[pbrs > 0]
    univ = [t for t in ret_wide.columns if t in caps.index and t in pbrs.index]
    bm = pd.Series({t: 1.0 / pbrs[t] for t in univ})
    cap = pd.Series({t: caps[t] for t in univ})

    size_med = cap.median()
    lo30, hi70 = bm.quantile(0.3), bm.quantile(0.7)

    def bucket(t):
        s = "S" if cap[t] <= size_med else "B"
        v = "L" if bm[t] <= lo30 else ("H" if bm[t] > hi70 else "M")
        return s + v

    groups: dict = {}
    for t in univ:
        groups.setdefault(bucket(t), []).append(t)

    def vw_ret(members):
        w = cap[members] / cap[members].sum()
        sub = ret_wide[members]
        # 결측일(정지 등)은 해당일 가용 종목으로 가중 재정규화
        wsum = sub.notna().mul(w, axis=1).sum(axis=1)
        return sub.mul(w, axis=1).sum(axis=1, min_count=1) / wsum

    port = {k: vw_ret(v) for k, v in groups.items() if v}
    smb = (
        sum(port.get(k, 0) for k in ("SL", "SM", "SH")) / 3
        - sum(port.get(k, 0) for k in ("BL", "BM", "BH")) / 3
    )
    hml = (
        sum(port.get(k, 0) for k in ("SH", "BH")) / 2
        - sum(port.get(k, 0) for k in ("SL", "BL")) / 2
    )
    return pd.DataFrame({"MKT": idx_ret, "SMB": smb, "HML": hml})


_MOM_LONG, _MOM_SKIP = 252, 21  # 모멘텀: 과거 12개월 누적, 최근 1개월 제외


def _month_lott(
    ret_wide, close_wide, close_ffill, pos, fwin, tickers, caps_all, kosdaq_set
):
    """한 달치 LOTT 합성값 {ticker: 값}. 회귀 재료가 있는 종목이 없으면 None.

    pos: 그 달 마지막 거래일의 행 위치, fwin: 룩백 창(행 인덱스 = 창의 거래일)의
    FF3 요인, caps_all: 규모 3분위용 시총(ret_wide 열 기준), kosdaq_set: 코스닥 집합.
    """
    window = fwin.index
    t1, t2 = caps_all.quantile(1 / 3), caps_all.quantile(2 / 3)  # 규모 3분위
    ivol, iskew = {}, {}
    for t in tickers:
        if t not in ret_wide.columns:
            continue  # 기간 내 거래가 없어 시세 열 자체가 없는 종목 (거래정지 등)
        sub = pd.concat([ret_wide[t].loc[window], fwin], axis=1).dropna()
        if len(sub) < 15:  # 3요인 4파라미터 — 최소 관측 확보
            continue
        y = sub.iloc[:, 0].to_numpy()
        X = np.column_stack(
            [np.ones(len(sub)), sub[["MKT", "SMB", "HML"]].to_numpy()]
        )
        beta, *_ = np.linalg.lstsq(X, y, rcond=None)  # FF3 회귀 (6-4)
        resid = y - X @ beta
        ivol[t] = float(resid.std(ddof=1))
        iskew[t] = float(pd.Series(resid).skew())  # FF3 잔차 왜도 (6-5 입력)
    if not ivol:
        return None
    s_ivol = pd.Series(ivol)

    s_skew = pd.Series(iskew).reindex(s_ivol.index).fillna(0.0)
    caps_m = caps_all.reindex(s_ivol.index)
    small = (caps_m <= t1).astype(float)
    mid = ((caps_m > t1) & (caps_m <= t2)).astype(float)
    kosdaq = pd.Series(
        {t: 1.0 if t in kosdaq_set else 0.0 for t in s_ivol.index}
    )
    if pos + 1 >= _MOM_LONG + _MOM_SKIP:
        mom = (
            close_ffill.iloc[pos - _MOM_SKIP] / close_ffill.iloc[pos - _MOM_LONG]
            - 1.0
        ).reindex(s_ivol.index).fillna(0.0)
    else:
        mom = pd.Series(0.0, index=s_ivol.index)
    eiskew = (
        0.113 * s_skew + 1.540 * s_ivol - 0.23 * mom
        + 0.026 * kosdaq + 0.401 * small + 0.290 * mid
    )

    s_price = close_wide.iloc[pos].reindex(s_ivol.index)
    # KCMI LOTT(1) 3축 완성 (6-5): 고유변동성 + 주가(역순) + EISKEW 랭크 합
    return (
        s_ivol.rank(pct=True) + (-s_price).rank(pct=True)
        + eiskew.rank(pct=True)
    ).to_dict()


def compute_monthly_lott(
    price_data: pd.DataFrame,
    index_data: pd.DataFrame,
    tickers: list[str],
    snapshots: dict | None = None,
) -> dict:
    """(연, 월) -> {ticker: LOTT 합성값}. 입력은 market_data 스키마의 시세·지수.

    각 달 마지막 거래일 기준 직전 LOTT_WINDOW_DAYS 거래일로 FF3 잔차의 표준편차
    (고유변동성)·왜도를 구하고, EISKEW·월말 종가와 함께 KCMI식 랭크 합으로 합성.
    EISKEW는 부록1 <표 A1-1> 모형(7)의 공표 평균계수 적용(재추정 없음 — 우리
    201종목으론 KCMI의 월별 횡단면 재추정 재현 불가). 섹터 더미는 계수 미공개로
    생략(랭크 사용이라 절편·공통항 무영향). 모멘텀 데이터 부족 월은 0(중립).

    snapshots: {(연, 월): (시총 Series, PBR Series, 코스닥 ticker 집합)}. None이면
    config 2020-03-02 스냅샷 1개로 요인·규모분류를 한 번만 계산(합성 학습 경로,
    기존 동작). 지정하면 달마다 그 달의 스냅샷으로 다시 계산하고, 스냅샷이 없는
    달은 건너뛴다.
    """
    idx_close = index_data.set_index("거래일자")["종가"].sort_index()
    close_wide = (
        price_data.pivot(index="거래일자", columns="종목코드", values="종가")
        .sort_index()
    )
    ret_wide = close_wide.pct_change()
    days = list(close_wide.index)
    idx_ret = idx_close.pct_change().reindex(close_wide.index)
    close_ffill = close_wide.ffill()  # 모멘텀 끝점용 (정지일 직전가 대체)

    if snapshots is None:
        factors = build_ff3_factors(ret_wide, idx_ret)
        caps_all = pd.Series(
            {t: config.MARKETCAP_20200302.get(t) for t in close_wide.columns},
            dtype=float,
        )
        kosdaq_set = set(config.KOSDAQ_TICKERS)

    W = config.LOTT_WINDOW_DAYS
    monthly_lott: dict = {}
    for (yy, mm) in sorted({(d.year, d.month) for d in days}):
        month_days = [d for d in days if d.year == yy and d.month == mm]
        pos = days.index(month_days[-1])
        if pos + 1 < W:
            continue  # 룩백 부족 (초기 월) — 시뮬 기간엔 사용되지 않는 구간
        window = days[pos - W + 1 : pos + 1]
        if snapshots is None:
            fwin = factors.loc[window]
        else:
            if (yy, mm) not in snapshots:
                continue
            caps, pbrs, kosdaq_set = snapshots[(yy, mm)]
            fwin = build_ff3_factors(
                ret_wide.loc[window], idx_ret.loc[window], caps, pbrs
            )
            caps_all = pd.Series(caps, dtype=float).reindex(close_wide.columns)
        scores = _month_lott(
            ret_wide, close_wide, close_ffill, pos, fwin, tickers, caps_all, kosdaq_set
        )
        if scores is not None:
            monthly_lott[(yy, mm)] = scores
    return monthly_lott


def apply_month_rank(monthly_lott: dict) -> dict:
    """'계산월 -> 적용월(+1개월)' 매핑 후 월별 횡단면 pct 랭크로 정규화.

    반환: (적용연, 적용월) -> pd.Series(ticker -> [0,1] 랭크). features와 감사
    스크립트가 공유하는 유틸 (model은 자체 규약 get_lott_scores 사용)."""
    out = {}
    for (yy, mm), scores in monthly_lott.items():
        ay, am = (yy + 1, 1) if mm == 12 else (yy, mm + 1)
        out[(ay, am)] = pd.Series(scores).rank(pct=True)
    return out
