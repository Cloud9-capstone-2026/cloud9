"""
LOTT(1) 월별 합성값 계산 — 생성기(model)와 피처 빌더(features)가 공유하는 순수 모듈.

7-3-1에서 model._prepare_market으로부터 추출(동작 불변 — 시드 7 거래 스트림 exact
검증). KCMI LOTT(1) 3축: FF3 잔차 고유변동성 + 주가(역순) + EISKEW(부록1 모형(7)
공표 계수)의 랭크 합. '이번 달 계산 → 다음 달 적용'(룩어헤드 차단)은 호출 측 규약
— model.get_lott_scores와 features의 적용월 매핑이 담당한다.
"""

import numpy as np
import pandas as pd

from . import config


def build_ff3_factors(ret_wide: pd.DataFrame, idx_ret: pd.Series) -> pd.DataFrame:
    """SMB·HML 일별 요인 (6-4, FF3 승격 — KCMI 원 방식과 동일 계열).

    분류는 2020-03-02 정적 스냅샷(시총 프리즈 + PBR 프리즈): 시총 중위 2분할 ×
    BM(=1/PBR) 30/70% 3분할 = 6포트폴리오, 정적 시총가중(VW) 일별 수익률.
    SMB = 소형 3개 평균 − 대형 3개 평균, HML = 고BM 2개 평균 − 저BM 2개 평균.
    근사 명시: (1) 분류·가중 모두 기간 내 고정 스냅샷 (2) 요인 모집단이 시장 전체가
    아니라 우리 201종목 계층화 유니버스 (3) PBR 결측/음수 13종목은 요인 구축에서 제외.
    """
    caps = config.MARKETCAP_20200302
    pbrs = config.PBR_20200302
    univ = [t for t in ret_wide.columns if t in caps and t in pbrs]
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


def compute_monthly_lott(
    price_data: pd.DataFrame, index_data: pd.DataFrame, tickers: list[str]
) -> dict:
    """(연, 월) -> {ticker: LOTT 합성값}. 입력은 market_data 스키마의 시세·지수.

    각 달 마지막 거래일 기준 직전 LOTT_WINDOW_DAYS 거래일로 FF3 잔차의 표준편차
    (고유변동성)·왜도를 구하고, EISKEW·월말 종가와 함께 KCMI식 랭크 합으로 합성.
    EISKEW는 부록1 <표 A1-1> 모형(7)의 공표 평균계수 적용(재추정 없음 — 우리
    201종목으론 KCMI의 월별 횡단면 재추정 재현 불가). 섹터 더미는 계수 미공개로
    생략(랭크 사용이라 절편·공통항 무영향). 모멘텀 데이터 부족 월은 0(중립).
    """
    idx_close = index_data.set_index("거래일자")["종가"].sort_index()
    close_wide = (
        price_data.pivot(index="거래일자", columns="종목코드", values="종가")
        .sort_index()
    )
    ret_wide = close_wide.pct_change()
    days = list(close_wide.index)
    idx_ret = idx_close.pct_change().reindex(close_wide.index)

    factors = build_ff3_factors(ret_wide, idx_ret)
    close_ffill = close_wide.ffill()  # 모멘텀 끝점용 (정지일 직전가 대체)
    kosdaq_set = set(config.KOSDAQ_TICKERS)
    caps_all = pd.Series(
        {t: config.MARKETCAP_20200302.get(t) for t in close_wide.columns},
        dtype=float,
    )
    t1, t2 = caps_all.quantile(1 / 3), caps_all.quantile(2 / 3)  # 규모 3분위(정적)

    W = config.LOTT_WINDOW_DAYS
    MOM_LONG, MOM_SKIP = 252, 21  # 모멘텀: 과거 12개월 누적, 최근 1개월 제외
    monthly_lott: dict = {}
    for (yy, mm) in sorted({(d.year, d.month) for d in days}):
        month_days = [d for d in days if d.year == yy and d.month == mm]
        pos = days.index(month_days[-1])
        if pos + 1 < W:
            continue  # 룩백 부족 (초기 월) — 시뮬 기간엔 사용되지 않는 구간
        window = days[pos - W + 1 : pos + 1]
        fwin = factors.loc[window]
        ivol, iskew = {}, {}
        for t in tickers:
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
            continue
        s_ivol = pd.Series(ivol)

        s_skew = pd.Series(iskew).reindex(s_ivol.index).fillna(0.0)
        caps_m = caps_all.reindex(s_ivol.index)
        small = (caps_m <= t1).astype(float)
        mid = ((caps_m > t1) & (caps_m <= t2)).astype(float)
        kosdaq = pd.Series(
            {t: 1.0 if t in kosdaq_set else 0.0 for t in s_ivol.index}
        )
        if pos + 1 >= MOM_LONG + MOM_SKIP:
            mom = (
                close_ffill.iloc[pos - MOM_SKIP] / close_ffill.iloc[pos - MOM_LONG]
                - 1.0
            ).reindex(s_ivol.index).fillna(0.0)
        else:
            mom = pd.Series(0.0, index=s_ivol.index)
        eiskew = (
            0.113 * s_skew + 1.540 * s_ivol - 0.23 * mom
            + 0.026 * kosdaq + 0.401 * small + 0.290 * mid
        )

        s_price = close_wide.loc[month_days[-1]].reindex(s_ivol.index)
        # KCMI LOTT(1) 3축 완성 (6-5): 고유변동성 + 주가(역순) + EISKEW 랭크 합
        monthly_lott[(yy, mm)] = (
            s_ivol.rank(pct=True) + (-s_price).rank(pct=True)
            + eiskew.rank(pct=True)
        ).to_dict()
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
