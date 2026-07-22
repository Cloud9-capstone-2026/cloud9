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
        # 오늘 가격 스냅샷 캐시(step에서 하루 1회 계산). N=1000 × 166일에서 agent마다
        # price_data 전체를 다시 필터링하는 비용을 제거. 빈 프레임으로 초기화.
        self._today_prices = self.price_data.iloc[0:0]

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
    def get_today_prices(self) -> pd.DataFrame:
        return self._today_prices  # step()에서 하루 1회 계산해 둔 오늘 스냅샷
 
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

    def _prepare_market(self, tickers: list[str]):
        """코스피 지수 수익률과 월별 LOTT 합성값(고유변동성+주가, 둘 다 월말 고정)을 미리 계산.

        - get_prev_market_return용: 날짜 -> '전일에 끝난' 지수 수익률 (shift(1)).
          당일 종가 수익률을 그대로 쓰면 장중 매수 판단에 당일 종가가 새는 look-ahead.
          단, 아래 CAPM 회귀는 종목-지수 '동시점' 정렬이 맞으므로 shift 안 한 원본을 쓴다.
        - LOTT용: 각 달 마지막 거래일 기준 직전 W거래일로 시장모형(CAPM) 잔차의 표준편차
          (고유변동성)를 구하고, 월말 종가와 함께 KCMI식 랭크 합으로 합성. '이번 달 계산 →
          다음 달 적용'(get_lott_scores가 직전 달을 조회)으로 룩어헤드를 구조적으로 차단.
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

        W = config.LOTT_WINDOW_DAYS
        self._monthly_lott: dict = {}
        for (yy, mm) in sorted({(d.year, d.month) for d in days}):
            month_days = [d for d in days if d.year == yy and d.month == mm]
            pos = days.index(month_days[-1])
            if pos + 1 < W:
                continue  # 룩백 부족 (초기 월) — 시뮬 기간엔 사용되지 않는 구간
            window = days[pos - W + 1 : pos + 1]
            ivol = {}
            for t in tickers:
                sub = pd.concat(
                    [ret_wide[t].loc[window], idx_ret.loc[window]], axis=1
                ).dropna()
                if len(sub) < 2:
                    continue
                x, y = sub.iloc[:, 1].to_numpy(), sub.iloc[:, 0].to_numpy()
                slope, intercept = np.polyfit(x, y, 1)  # 시장모형(CAPM) 회귀
                resid = y - (slope * x + intercept)
                ivol[t] = float(resid.std(ddof=1))
            if not ivol:
                continue
            s_ivol = pd.Series(ivol)
            s_price = close_wide.loc[month_days[-1]].reindex(s_ivol.index)
            # KCMI LOTT 구조: 랭크 합 (고유변동성 높을수록·주가 낮을수록 높은 점수)
            self._monthly_lott[(yy, mm)] = (
                s_ivol.rank(pct=True) + (-s_price).rank(pct=True)
            ).to_dict()
 
    def get_herd_breadth(self, lag_days: int) -> dict[str, int]:
        """lag_days일 전(완료된 과거일)의 종목별 매수자 수(breadth)를 반환.

        반드시 이미 처리 끝난 과거일만 참조한다. 오늘 진행 중인 매수를 반영하면
        shuffle_do의 무작위 처리 순서에 따라 결과가 달라지는 순서의존성이 생긴다.
        해당 시점 데이터가 없으면(시뮬 초반) 빈 dict.
        """
        idx = self.day_idx - lag_days
        if idx < 0:
            return {}
        past_date = self.trading_days[idx]
        buyers = self.daily_buyers.get(past_date, {})
        return {ticker: len(agents) for ticker, agents in buyers.items()}

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
        # 오늘 가격 스냅샷을 1회만 계산해 캐시 → 모든 agent가 공유(get_today_prices).
        self._today_prices = self.price_data[
            self.price_data["거래일자"] == self.current_date
        ]
        self.agents.shuffle_do("step")
        self.day_idx += 1
 
    def run(self):
        for _ in range(len(self.trading_days)):
            self.step()
 
    # -- 출력 ------------------------------------------------------------------
    def trades_to_dataframe(self) -> pd.DataFrame:
        return pd.DataFrame([t.to_dict() for t in self.trades])
 