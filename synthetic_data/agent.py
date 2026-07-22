"""
InvestorAgent: 하루 단위로 매도->매수 판단을 수행하는 개인 투자자 agent.
"""
 
from typing import TYPE_CHECKING

import mesa
import pandas as pd
 
from . import config
from .params import BehaviorParams, InvestorGroup
from .schema import Trade
if TYPE_CHECKING:
    from .model import MarketModel


class InvestorAgent(mesa.Agent):
    def __init__(
        self,
        model: "MarketModel",
        params: BehaviorParams,
        initial_cash: float,
        group: InvestorGroup,
    ):
        super().__init__(model)
        self.params = params
        # 인구통계 그룹 태그(표 Ⅲ-1). agent 객체에만 보관 — CSV(편향라벨)에는 안 넣는다
        # (실제 증권사 CSV에 없는 필드 + 이상탐지 leakage 방지). 5-5 그룹별 검증은
        # kcmi_metrics가 model 객체를 받으므로 agent.group으로 직접 접근.
        self.group = group
        self.cash = initial_cash
        # positions: {종목코드: {"수량": int, "평균단가": float, "매입일": date}}
        self.positions: dict[str, dict] = {}
 
    def step(self):
        today_prices = self.model.get_today_prices()
        if today_prices.empty:
            return
        self._maybe_sell(today_prices)
        self._maybe_buy(today_prices)
 
    # -- 매도 판단 (처분효과) -------------------------------------------------
    def _maybe_sell(self, today_prices: pd.DataFrame):
        for ticker, pos in list(self.positions.items()):
            row = today_prices[today_prices["종목코드"] == ticker]
            if row.empty:
                continue
            close = float(row.iloc[0]["종가"])
 
            if pos["매입일"] == self.model.current_date:
                continue  # 매수 당일 매도 배제 (KCMI 22-02 방법론과 동일)
 
            is_gain = close >= pos["평균단가"]
            prob = self.params.base_sell_prob * (
                self.params.disposition_strength if is_gain else 1.0
            )
            if self.random.random() < min(prob, 0.9):
                self._execute_sell(ticker, pos, row.iloc[0])
 
    def _execute_sell(self, ticker: str, pos: dict, price_row: pd.Series):
        low, high = float(price_row["저가"]), float(price_row["고가"])
        exec_price = self.random.uniform(low, high)  # TODO(2단계): 체결가 샘플링 정교화
        qty = pos["수량"]
 
        trade = Trade(
            거래일자=self.model.current_date,
            agent_id=str(self.unique_id),
            종목코드=ticker,
            거래구분="매도",
            거래수량=qty,
            거래단가=round(exec_price),
            처리시간=self._sample_time(),
            편향라벨=self.params.as_label(),
        )
        self.cash += trade.정산금액
        del self.positions[ticker]
        trade.예수금 = round(self.cash)
        self.model.record_trade(trade)
 
    # -- 매수 판단 (과잉확신 + 복권형 선호) -----------------------------------
    def _maybe_buy(self, today_prices: pd.DataFrame):
        market_return = self.model.get_prev_market_return()
        prob = self.params.base_buy_prob
        if market_return is not None and market_return > 0:
            prob *= (
                1 + self.params.overconfidence * market_return
                * config.OVERCONFIDENCE_MARKET_SCALE
            )
 
        if self.random.random() >= min(prob, 0.9):
            return
        if self.cash < 100_000:
            return
 
        ticker = self._pick_ticker(today_prices)
        if ticker is None:
            return
        row = today_prices[today_prices["종목코드"] == ticker].iloc[0]
        self._execute_buy(ticker, row)
 
    def _pick_ticker(self, today_prices: pd.DataFrame) -> str | None:
        """복권형 선호와 군집 신호를 배타적 분기가 아니라 가중합으로 결합해 종목을 고른다.

        KCMI 22-02가 복권형 지표(LOTT)를 세 축의 '랭크 합'으로 만든 것과 같은 가법 구조.
        두 성향이 모두 강한 agent는 '저가이면서 동시에 몰린' 종목에 두 항이 함께 가산돼
        자연스럽게 이중 가중된다. 두 파라미터가 서로 간섭하지 않아 5단계 캘리브레이션에서
        각 축을 독립적으로 맞출 수 있다.
        """
        candidates = today_prices["종목코드"].unique().tolist()
        if not candidates:
            return None

        lottery = self._lottery_scores(candidates)
        herd = self._herd_scores(candidates)

        weights = [
            config.PICK_BASE_WEIGHT
            + self.params.lottery_preference * lottery[t]
            + self.params.herd_sensitivity * herd[t]
            for t in candidates
        ]
        return self.random.choices(candidates, weights=weights, k=1)[0]

    def _lottery_scores(self, candidates: list[str]) -> dict[str, float]:
        """월별 사전계산된 LOTT 합성값(고유변동성+주가, 직전 달 기준)을 조회해 그날 후보 안에서
        [0,1] 재정규화(herd_score와 스케일 일치). 데이터 없으면 전 종목 동률 → lottery 항 중립.
        TODO(5단계): 왜도(EISKEW) 축 추가로 KCMI 3축 완성."""
        lott = self.model.get_lott_scores(self.model.current_date)
        if not lott:
            return {t: 0.0 for t in candidates}
        return self._rank_norm(candidates, {t: lott.get(t, 0.0) for t in candidates})

    def _herd_scores(self, candidates: list[str]) -> dict[str, float]:
        """군집 신호: lag일 전(완료된 과거일) 매수자 폭(breadth)이 클수록 높은 점수.
        오늘 거래가능 후보로만 한정하고, 데이터 없는 종목은 breadth 0으로 최하위."""
        breadth = self.model.get_herd_breadth(config.HERD_LAG_DAYS)
        return self._rank_norm(candidates, {t: breadth.get(t, 0) for t in candidates})

    @staticmethod
    def _rank_norm(
        candidates: list[str], values: dict[str, float]
    ) -> dict[str, float]:
        """values를 오름차순 랭크해 [0,1]로 정규화. 동률은 평균 랭크로 처리.

        동률 평균랭크가 중요한 이유: 시뮬 초반처럼 전 종목 breadth가 0인 경우, 단순 정렬
        위치로 랭크를 매기면 값이 같은데도 정렬 순서 때문에 일부 종목이 불공평하게
        가점된다. 평균 랭크는 동률 종목에 같은 점수를 준다.
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
 
    def _execute_buy(self, ticker: str, price_row: pd.Series):
        low, high = float(price_row["저가"]), float(price_row["고가"])
        exec_price = self.random.uniform(low, high)  # TODO(2단계): 체결가 샘플링 정교화
 
        max_affordable_qty = int(self.cash // (exec_price * 1.001))
        if max_affordable_qty <= 0:
            return
        lo, hi = config.BUY_CASH_FRACTION_RANGE
        qty = max(1, int(max_affordable_qty * self.random.uniform(lo, hi)))
 
        trade = Trade(
            거래일자=self.model.current_date,
            agent_id=str(self.unique_id),
            종목코드=ticker,
            거래구분="매수",
            거래수량=qty,
            거래단가=round(exec_price),
            처리시간=self._sample_time(),
            편향라벨=self.params.as_label(),
        )
        self.cash -= trade.정산금액

        existing = self.positions.get(ticker)
        if existing is None:
            self.positions[ticker] = {
                "수량": qty,
                "평균단가": trade.거래단가,
                "매입일": self.model.current_date,
            }
        else:
            # 이미 보유 중이면 통째로 덮어쓰지 않고 병합: 수량 합산 + 평균단가 가중평균.
            # 매입일은 최초 매입일 유지 (갱신하지 않음).
            new_qty = existing["수량"] + qty
            existing["평균단가"] = (
                existing["평균단가"] * existing["수량"] + trade.거래단가 * qty
            ) / new_qty
            existing["수량"] = new_qty

        trade.예수금 = round(self.cash)
        self.model.record_trade(trade)

    def _sample_time(self) -> str:
        """장중(09:00~15:30) 균등분포로 체결 처리시각을 샘플링. 가격과 독립.

        분포용 참고 필드일 뿐 하루 안의 매매 순서 신호가 아니다(schema.Trade.처리시간 주석 참고).

        5-7 검토 결론 — uniform 유지 확정. 사유: 장중 시간대 분포의 '정량' 근거를 확보할
        수 없음 — pykrx는 일간 API뿐(시간대 함수 부재 확인), KCMI는 일간 가정이라 무관한
        소스, 미시구조 문헌의 U자형(시가·종가 집중; Jain & Joh 1988 등)은 형태만 주고
        파라미터를 주지 않음. 근거 없는 계수를 지어내지 않는 원칙(4-4 체결가와 동일)에
        따라 유지. 단, 이상탐지가 처리시간을 피처로 쓰게 되거나 시간대별 실데이터를
        확보하면 문헌 기반 U자형으로 교체(6단계 후보).
        """
        sec = self.random.randint(9 * 3600, 15 * 3600 + 30 * 60)
        h, rem = divmod(sec, 3600)
        m, s = divmod(rem, 60)
        return f"{h:02d}:{m:02d}:{s:02d}"