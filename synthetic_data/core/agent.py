"""
InvestorAgent: 하루 단위로 매도->매수 판단을 수행하는 개인 투자자 agent.
"""
 
from typing import TYPE_CHECKING

import mesa

from .. import config
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
        entry_date,
        init_positions: dict | None = None,
    ):
        super().__init__(model)
        self.params = params
        # 인구통계 그룹 태그(표 Ⅲ-1). agent 객체에만 보관 — CSV(편향라벨)에는 안 넣는다
        # (실제 증권사 CSV에 없는 필드 + 이상탐지 leakage 방지). 5-5 그룹별 검증은
        # kcmi_metrics가 model 객체를 받으므로 agent.group으로 직접 접근.
        self.group = group
        # 진입일(7-1b): 신규투자자는 계좌 개설 시점(그림 Ⅱ-1 분포)부터 활동.
        # 진입 전에는 step이 no-op — 현금도 사실상 진입 시점에 유입되는 것과 동일.
        self.entry_date = entry_date
        self.cash = initial_cash
        # positions: {종목코드: {"수량": int, "평균단가": float, "매입일": date}}
        # 기존투자자는 초기 보유(7-1d)를 갖고 시작 — 매입일이 시뮬 시작 전 날짜라
        # '매수 당일 매도 배제'와 충돌 없이 첫날부터 매도 가능. 매도·병합 로직은 동일.
        self.positions: dict[str, dict] = (
            {tk: dict(p) for tk, p in init_positions.items()} if init_positions else {}
        )

    def step(self):
        if self.model.current_date < self.entry_date:  # 진입 전 (7-1b)
            return
        if not self.model._today_candidates:  # 오늘 거래가능 종목 없음
            return
        self._maybe_sell()
        self._maybe_buy()

    # -- 매도 판단 (처분효과) -------------------------------------------------
    def _maybe_sell(self):
        for ticker, pos in list(self.positions.items()):
            price = self.model.get_today_price(ticker)
            if price is None:  # 오늘 거래 없는 종목(거래정지 등) — 매도 불가
                continue
            low, high, close = price

            if pos["매입일"] == self.model.current_date:
                continue  # 매수 당일 매도 배제 (KCMI 22-02 방법론과 동일)

            is_gain = close >= pos["평균단가"]
            prob = self.params.base_sell_prob * (
                self.params.disposition_strength if is_gain else 1.0
            )
            if self.random.random() < min(prob, 0.9):
                self._execute_sell(ticker, pos, low, high)

    def _execute_sell(self, ticker: str, pos: dict, low: float, high: float):
        exec_price = self.random.uniform(low, high)  # TODO: 체결가 샘플링 정교화(보류)
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
    def _maybe_buy(self):
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
 
        ticker = self._pick_ticker()
        if ticker is None:
            return
        low, high, _close = self.model.get_today_price(ticker)
        self._execute_buy(ticker, low, high)
 
    def _pick_ticker(self) -> str | None:
        """복권형 선호와 군집(attention) 신호를 배타적 분기가 아니라 가중합으로 결합해
        종목을 고른다.

        KCMI 22-02가 복권형 지표(LOTT)를 세 축의 '랭크 합'으로 만든 것과 같은 가법 구조.
        두 성향이 모두 강한 agent는 '저가이면서 동시에 주목받는' 종목에 두 항이 함께
        가산돼 자연스럽게 이중 가중된다. 두 파라미터가 서로 간섭하지 않아 캘리브레이션에서
        각 축을 독립적으로 맞출 수 있다.

        군집 항은 7-1에서 내부 breadth → 관측가능 시장 attention(전일 비정상거래량+최근
        수익률 랭크)으로 교체 — 실계좌 피처와 생성 채널이 같은 값이 된다(config 참조).
        LOTT/attention 랭크 정규화는 agent와 무관한 day-level 값이라 model.step()이 하루
        1회 계산해 둔 스냅샷(_today_lott_norm/_today_attn_norm)을 그대로 쓴다(6-2).
        """
        candidates = self.model._today_candidates
        if not candidates:
            return None

        lottery = self.model._today_lott_norm
        attn = self.model._today_attn_norm

        hs = self.params.herd_sensitivity * config.HERD_WEIGHT_SCALE  # 6-6 스케일
        lp = self.params.lottery_preference * config.LOTT_WEIGHT_SCALE  # 7-2 스케일
        weights = [
            config.PICK_BASE_WEIGHT
            + lp * lottery[t]
            + hs * attn[t]
            for t in candidates
        ]
        return self.random.choices(candidates, weights=weights, k=1)[0]

    # (_lottery_scores/_herd_scores/_rank_norm은 6-2에서 model.step()의 day-level
    #  스냅샷 계산으로 이동 — agent×매수판단마다 O(n²) 재계산하던 것을 하루 1회로.)
 
    def _execute_buy(self, ticker: str, low: float, high: float):
        exec_price = self.random.uniform(low, high)  # TODO: 체결가 샘플링 정교화(보류)
 
        max_affordable_qty = int(self.cash // (exec_price * 1.001))
        if max_affordable_qty <= 0:
            return
        lo, hi = config.BUY_CASH_FRACTION_RANGE
        qty = max(1, int(max_affordable_qty * self.random.uniform(lo, hi)))
        # 유동성 가드(6-3): 전일 거래량의 일정 비율을 넘는 매수 주문은 상한으로 절단.
        cap = self.model.get_buy_qty_cap(ticker)
        if cap is not None:
            if cap <= 0:
                return  # 전일 거래가 사실상 없던 종목 — 매수 스킵
            qty = min(qty, cap)
 
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