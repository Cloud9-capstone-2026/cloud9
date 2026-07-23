"""
MarketModel: 전체 시뮬레이션(가격 데이터 + agent 집합 + 일별 step)을 관리.
"""
 
import random
from datetime import datetime
 
import mesa
import numpy as np
import pandas as pd
 
from . import config
from .agent import InvestorAgent
from .market_data import get_index_data, get_price_data
from .params import sample_investor_group, sample_investor_params
from .schema import Trade
 
 
def _rank_norm(candidates: list[str], values: dict[str, float]) -> dict[str, float]:
    """values를 오름차순 랭크해 [0,1]로 정규화. 동률은 평균 랭크로 처리.

    (agent.py에서 6-2 호이스팅으로 이동 — day-level 값이라 하루 1회면 충분.
    부동소수점 동일성을 위해 산식 그대로 유지: less + (equal-1)/2.0 → /(n-1).)
    동률 평균랭크가 중요한 이유: 시뮬 초반처럼 전 종목 breadth가 0인 경우, 단순 정렬
    위치 랭크는 정렬 순서 때문에 일부 종목이 불공평하게 가점된다.
    """
    n = len(candidates)
    if n <= 1:
        return {t: 0.0 for t in candidates}
    vals = [values[t] for t in candidates]
    out = {}
    for t in candidates:
        v = values[t]
        less = sum(1 for u in vals if u < v)
        equal = sum(1 for u in vals if u == v)
        avg_rank = less + (equal - 1) / 2.0
        out[t] = avg_rank / (n - 1)
    return out


class MarketModel(mesa.Model):
    def __init__(
        self,
        n_investors: int,
        tickers: list[str],
        seed: int = 1,
    ):
        super().__init__(rng=seed)
        # RNG 스트림 분리: 그룹 배정과 파라미터 산포는 독립된 무작위 과정이므로 별도
        # 스트림을 쓴다. 단일 스트림이면 그룹 로직 변경(예: 독립→신규조건부)이 소비하는
        # 난수 개수를 바꿔 무관한 파라미터 draw까지 통째로 밀리고, 그룹-파라미터 간
        # PRNG 인접성에 의한 가짜 상관도 생길 수 있다. 부수 효과로 multiplier=1.0인
        # 동안 py_rng 스트림이 그룹 도입 전과 바이트 단위로 동일 → exact 회귀검증 성립.
        py_rng = random.Random(seed)        # 파라미터·초기자산 (기존 스트림 유지)
        group_rng = random.Random(seed + 1)  # 그룹 태깅 전용
 
        # 가격은 pykrx 실데이터. LOTT 룩백 때문에 SIM_START 이전(2019-11~)까지 받으므로,
        # price_data(전체)는 LOTT·지수 계산용으로 보관하고 시뮬 캘린더는 SIM_START 이후만 건다.
        self.price_data = get_price_data(tickers)
        sim_start = datetime.strptime(config.SIM_START_DATE, "%Y%m%d").date()
        all_days = sorted(self.price_data["거래일자"].unique())
        self.trading_days = [d for d in all_days if d >= sim_start]
        self.day_idx = 0
        self.current_date = self.trading_days[0]
        self.trades: list[Trade] = []
        # 군집거래 집계: {거래일자: {종목코드: {매수한 agent_id 집합}}}
        self.daily_buyers: dict = {}
        # 오늘 스냅샷 캐시(step에서 하루 1회 계산, 6-2 호이스팅 — 유니버스 확장 대비):
        # 가격 dict(agent별 pandas 필터 제거) + LOTT/herd 랭크 정규화(agent 무관한
        # day-level 값이라 1회만 계산; 기존엔 agent×매수판단마다 O(n²) 재계산).
        self._today_candidates: list = []
        self._today_price_map: dict = {}   # ticker -> (저가, 고가, 종가)
        self._today_lott_norm: dict = {}   # ticker -> [0,1] 랭크 정규화
        self._today_herd_norm: dict = {}
        # 유동성 가드용 전일 거래량 (당일 거래량은 장중 look-ahead라 전일 사용).
        self._prev_volume: dict = {}       # ticker -> 전일 거래량
        self._today_volume: dict = {}

        # 코스피 지수 수익률 + 월별 LOTT 스코어 사전계산 (확장 히스토리 사용).
        self._prepare_market(tickers)
 
        ranges = config.BehaviorParamRanges()
        for _ in range(n_investors):
            group = sample_investor_group(group_rng)  # group_rng만 소모
            params = sample_investor_params(py_rng, ranges, group, config.MULTIPLIERS)
            cash_lo, cash_hi = config.INITIAL_CASH_BY_ASSET[group.asset]
            initial_cash = round(
                py_rng.uniform(cash_lo, cash_hi)
            )  # 정수(원)로 시작 → 예수금 스냅샷이 소수 오프셋 없이 정산금액과 정확히 정합
            # (자산 그룹별 범위 — draw 수는 agent당 uniform 1회로 기존과 동일)
            InvestorAgent(self, params, initial_cash, group)
 
    # -- 헬퍼 -----------------------------------------------------------------
    def get_today_price(self, ticker: str):
        """오늘 (저가, 고가, 종가) 튜플. 오늘 거래 없는 종목이면 None."""
        return self._today_price_map.get(ticker)

    def get_buy_qty_cap(self, ticker: str):
        """유동성 가드(6-3): 매수 주문수량 상한 = 전일 거래량 × ORDER_MAX_VOLUME_FRACTION.
        전일 데이터 없으면(시뮬 첫날·신규 편입) None = 무제한."""
        v = self._prev_volume.get(ticker)
        if v is None:
            return None
        return int(v * config.ORDER_MAX_VOLUME_FRACTION)
 
    def get_prev_market_return(self) -> float | None:
        # 전일에 '끝난' 코스피 지수 수익률(= 종가[d-1]/종가[d-2] - 1). _prepare_market에서
        # shift(1)로 하루 밀어 저장하므로 당일 종가 look-ahead가 없다. 지수 히스토리가
        # 2019-11부터라 시뮬 첫날(2020-03-02)도 전일 수익률이 정상 정의됨.
        return self._index_ret.get(self.current_date)

    def get_lott_scores(self, current_date) -> dict:
        """current_date가 속한 달에 적용할 LOTT 합성값(직전 달에 사전계산). 없으면 빈 dict."""
        y, m = current_date.year, current_date.month
        py, pm = (y - 1, 12) if m == 1 else (y, m - 1)
        return self._monthly_lott.get((py, pm), {})

    def _build_ff3_factors(self, ret_wide, idx_ret):
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

    def _prepare_market(self, tickers: list[str]):
        """코스피 지수 수익률과 월별 LOTT 합성값(고유변동성+주가, 둘 다 월말 고정)을 미리 계산.

        - get_prev_market_return용: 날짜 -> '전일에 끝난' 지수 수익률 (shift(1)).
          당일 종가 수익률을 그대로 쓰면 장중 매수 판단에 당일 종가가 새는 look-ahead.
          단, 아래 요인 회귀는 종목-요인 '동시점' 정렬이 맞으므로 shift 안 한 원본을 쓴다.
        - LOTT용: 각 달 마지막 거래일 기준 직전 W거래일로 FF3(시장+SMB+HML, 6-4에서
          시장모형 1요인 승격) 잔차의 표준편차(고유변동성)를 구하고, 월말 종가와 함께
          KCMI식 랭크 합으로 합성. '이번 달 계산 → 다음 달 적용'(get_lott_scores가
          직전 달을 조회)으로 룩어헤드를 구조적으로 차단.
        """
        idx = get_index_data()
        idx_close = idx.set_index("거래일자")["종가"].sort_index()

        close_wide = (
            self.price_data.pivot(index="거래일자", columns="종목코드", values="종가")
            .sort_index()
        )
        ret_wide = close_wide.pct_change()
        days = list(close_wide.index)  # 전체 캘린더 (2019-11~)
        idx_ret = idx_close.pct_change().reindex(close_wide.index)  # 지수를 종목 캘린더에 정렬

        # 과잉확신 트리거용은 하루 밀어서(shift) 저장: _index_ret[d] = 전일에 끝난 수익률.
        # (idx_ret 원본은 아래 CAPM 회귀에서 동시점 정렬로 계속 사용.)
        prev_ret = idx_ret.shift(1)
        self._index_ret = {
            d: (None if pd.isna(r) else float(r)) for d, r in prev_ret.items()
        }

        factors = self._build_ff3_factors(ret_wide, idx_ret)
        close_ffill = close_wide.ffill()  # 모멘텀 끝점용 (정지일 직전가 대체)
        kosdaq_set = set(config.KOSDAQ_TICKERS)
        caps_all = pd.Series(
            {t: config.MARKETCAP_20200302.get(t) for t in close_wide.columns},
            dtype=float,
        )
        t1, t2 = caps_all.quantile(1 / 3), caps_all.quantile(2 / 3)  # 규모 3분위(정적)

        W = config.LOTT_WINDOW_DAYS
        MOM_LONG, MOM_SKIP = 252, 21  # 모멘텀: 과거 12개월 누적, 최근 1개월 제외
        self._monthly_lott: dict = {}
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

            # --- EISKEW (6-5): 부록1 <표 A1-1> 모형(7)의 공표 평균계수를 적용한
            #     사전적 고유왜도. 재추정 없이 공표 계수 사용(우리 201종목으론 KCMI의
            #     월별 횡단면 재추정(월 1,788종목) 재현 불가). 섹터 더미는 계수 미공개로
            #     생략(랭크 사용이라 절편·공통항은 무영향). 모멘텀 데이터 부족 월은 0(중립)
            #     — 시뮬 적용월(2020-02 계산 이후)엔 미발동(LOTT_ESTIMATION_START 확장).
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
            self._monthly_lott[(yy, mm)] = (
                s_ivol.rank(pct=True) + (-s_price).rank(pct=True)
                + eiskew.rank(pct=True)
            ).to_dict()
 
    def get_herd_breadth(self, lag_days: int) -> dict[str, float]:
        """과거 HERD_WINDOW_DAYS일의 종목별 매수자 수(breadth)를 감쇠 가중 합산해 반환.

        6-6 재설계: 기존 lag-1 단일일 breadth는 노이즈가 크고 지속성이 없어 매수→익일
        전량매도 반전 flow에 묻혔다. 다일 감쇠 창(DECAY^(k-1) 가중)은 몰림 신호를
        여러 날 유지시켜 매수 지속성(Sias 양의 시차 상관의 원천)을 만든다.
        반드시 이미 처리 끝난 과거일만 참조(shuffle_do 순서의존성 차단). 데이터 없으면 빈 dict.
        """
        acc: dict = {}
        for k in range(config.HERD_WINDOW_DAYS):
            idx = self.day_idx - lag_days - k
            if idx < 0:
                break
            w = config.HERD_DECAY ** k
            for ticker, agents in self.daily_buyers.get(
                self.trading_days[idx], {}
            ).items():
                acc[ticker] = acc.get(ticker, 0.0) + w * len(agents)
        return acc

    def record_trade(self, trade: Trade):
        self.trades.append(trade)
        if trade.거래구분 == "매수":
            # 군집거래 집계: 종목별 '서로 다른 매수자 수'(breadth)를 오늘 날짜에 누적.
            # 거래 건수가 아니라 distinct agent 수 → Sias(2004)의 거래자 폭 개념과 정합.
            day = self.daily_buyers.setdefault(self.current_date, {})
            day.setdefault(trade.종목코드, set()).add(trade.agent_id)
 
    # -- 스텝 ------------------------------------------------------------------
    def step(self):
        self.current_date = self.trading_days[self.day_idx]
        day_df = self.price_data[self.price_data["거래일자"] == self.current_date]
        # 후보 순서는 기존 unique() 순서 그대로 유지 (choices의 RNG 재현성 보존)
        self._today_candidates = day_df["종목코드"].unique().tolist()
        self._today_price_map = {
            tk: (float(lo), float(hi), float(cl))
            for tk, lo, hi, cl in zip(
                day_df["종목코드"], day_df["저가"], day_df["고가"], day_df["종가"]
            )
        }
        # 전일 거래량 롤링 (유동성 가드용)
        self._prev_volume = self._today_volume
        self._today_volume = {
            tk: int(v) for tk, v in zip(day_df["종목코드"], day_df["거래량"])
        }
        # LOTT/herd 랭크 정규화 — agent와 무관한 day-level 값이라 하루 1회만.
        cands = self._today_candidates
        lott = self.get_lott_scores(self.current_date)
        if lott:
            self._today_lott_norm = _rank_norm(
                cands, {t: lott.get(t, 0.0) for t in cands}
            )
        else:  # 데이터 없으면 전 종목 동률(중립) — 기존 agent 폴백과 동일
            self._today_lott_norm = {t: 0.0 for t in cands}
        breadth = self.get_herd_breadth(config.HERD_LAG_DAYS)
        self._today_herd_norm = _rank_norm(
            cands, {t: breadth.get(t, 0) for t in cands}
        )
        self.agents.shuffle_do("step")
        self.day_idx += 1
 
    def run(self):
        for _ in range(len(self.trading_days)):
            self.step()
 
    # -- 출력 ------------------------------------------------------------------
    def trades_to_dataframe(self) -> pd.DataFrame:
        return pd.DataFrame([t.to_dict() for t in self.trades])
 