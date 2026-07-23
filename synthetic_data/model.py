"""
MarketModel: 전체 시뮬레이션(가격 데이터 + agent 집합 + 일별 step)을 관리.
"""
 
import math
import random
from datetime import datetime, timedelta
 
import mesa
import pandas as pd
 
from . import config
from .agent import InvestorAgent
from .lott import compute_monthly_lott
from .market_data import get_index_data, get_price_data
from .params import sample_investor_group, sample_investor_params
from .schema import Trade
 
 
def _poisson(rng: random.Random, lam: float) -> int:
    """Knuth 방식 포아송 샘플 (numpy RNG를 쓰지 않는 이유: py_rng 계열과 동일한
    random.Random 스트림 규율 유지 — 7-1d 초기 종목수 k ~ 1+Poisson(λ))."""
    L = math.exp(-lam)
    k, p = 0, 1.0
    while True:
        p *= rng.random()
        if p <= L:
            return k
        k += 1


def _weighted_sample_no_replace(
    rng: random.Random, items: list, weights: list[float], k: int
) -> list:
    """가중 비복원 샘플링 k개 (7-1d 초기 보유 종목 선택 — 시총 가중)."""
    items, weights = list(items), list(weights)
    out = []
    for _ in range(min(k, len(items))):
        r = rng.random() * sum(weights)
        acc = 0.0
        i = 0
        for i, w in enumerate(weights):
            acc += w
            if r <= acc:
                break
        out.append(items.pop(i))
        weights.pop(i)
    return out


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
        entry_rng = random.Random(seed + 2)  # 신규투자자 진입일 전용 (7-1b) — 별도
        # 스트림이라 진입 로직 on/off가 파라미터·그룹 draw를 밀지 않는다(5-3 RNG 규율)
        portfolio_rng = random.Random(seed + 3)  # 기존투자자 초기 보유 전용 (7-1d)
 
        # 가격은 pykrx 실데이터. LOTT 룩백 때문에 SIM_START 이전(2019-11~)까지 받으므로,
        # price_data(전체)는 LOTT·지수 계산용으로 보관하고 시뮬 캘린더는 SIM_START 이후만 건다.
        self.price_data = get_price_data(tickers)
        sim_start = datetime.strptime(config.SIM_START_DATE, "%Y%m%d").date()
        all_days = sorted(self.price_data["거래일자"].unique())
        self.trading_days = [d for d in all_days if d >= sim_start]
        self.day_idx = 0
        self.current_date = self.trading_days[0]
        self.trades: list[Trade] = []
        # 오늘 스냅샷 캐시(step에서 하루 1회 계산, 6-2 호이스팅 — 유니버스 확장 대비):
        # 가격 dict(agent별 pandas 필터 제거) + LOTT/attention 랭크 정규화(agent 무관한
        # day-level 값이라 1회만 계산; 기존엔 agent×매수판단마다 O(n²) 재계산).
        self._today_candidates: list = []
        self._today_price_map: dict = {}   # ticker -> (저가, 고가, 종가)
        self._today_lott_norm: dict = {}   # ticker -> [0,1] 랭크 정규화
        self._today_attn_norm: dict = {}   # ticker -> [0,1] attention 랭크 (7-1)
        # 유동성 가드용 전일 거래량 (당일 거래량은 장중 look-ahead라 전일 사용).
        self._prev_volume: dict = {}       # ticker -> 전일 거래량
        self._today_volume: dict = {}

        # 코스피 지수 수익률 + 월별 LOTT 스코어 사전계산 (확장 히스토리 사용).
        self._prepare_market(tickers)
 
        # 신규투자자 진입일 분포 (7-1b): 그림 Ⅱ-1 주별 가중을 거래일 단위로 전개.
        entry_days, entry_weights = self._build_entry_distribution()

        # 기존투자자 초기 보유 준비 (7-1d): 시뮬 시작 직전 종가 + 시총 가중 샘플링 풀.
        # 취득단가 = 직전 거래일(2020-02-28) 종가 프록시 — 실제 취득가는 알 수 없고,
        # 측정에서는 p42 규칙으로 제외되므로 agent 매도 판단(손익 기준점)에만 쓰인다.
        self.initial_positions: dict = {}  # agent_id -> {ticker: {수량, 평균단가, 매입일}}
        self.initial_assets: dict = {}     # agent_id -> 초기 총자산(주식+현금, 분할 전) — meta 출력용(7-4)
        pre = self.price_data[self.price_data["거래일자"] < sim_start]
        base_date = pre["거래일자"].max()
        last_close = pre.sort_values("거래일자").groupby("종목코드")["종가"].last()
        pf_tickers = [t for t in last_close.index if config.MARKETCAP_20200302.get(t)]
        pf_caps = [float(config.MARKETCAP_20200302[t]) for t in pf_tickers]

        ranges = config.BehaviorParamRanges()
        for _ in range(n_investors):
            group = sample_investor_group(group_rng)  # group_rng만 소모
            params = sample_investor_params(py_rng, ranges, group, config.MULTIPLIERS)
            cash_lo, cash_hi = config.INITIAL_CASH_BY_ASSET[group.asset]
            initial_cash = round(
                py_rng.uniform(cash_lo, cash_hi)
            )  # 정수(원)로 시작 → 예수금 스냅샷이 소수 오프셋 없이 정산금액과 정확히 정합
            # (자산 그룹별 범위 — draw 수는 agent당 uniform 1회로 기존과 동일.
            #  7-1d부터 이 값은 '총자산'이고, 기존투자자는 아래에서 주식/현금으로 분할)
            total_asset = initial_cash  # 분할 전 총자산 스냅샷 (meta 출력용)
            init_pos: dict = {}
            if config.INITIAL_PORTFOLIO and group.new_key == "기존":
                frac = portfolio_rng.uniform(*config.INITIAL_STOCK_FRACTION)
                k = 1 + _poisson(portfolio_rng, config.INITIAL_NSTOCK_LAMBDA[group.asset])
                budget_per = initial_cash * frac / k
                for tk in _weighted_sample_no_replace(
                    portfolio_rng, pf_tickers, pf_caps, k
                ):
                    price = float(last_close[tk])
                    qty = int(budget_per // price)
                    if qty <= 0:  # 소액계좌 × 고가주 — 스킵 (유효 종목수 감소, 현실 정합)
                        continue
                    init_pos[tk] = {"수량": qty, "평균단가": price, "매입일": base_date}
                initial_cash = round(
                    initial_cash
                    - sum(p["수량"] * p["평균단가"] for p in init_pos.values())
                )
            if config.STAGGERED_ENTRY and group.new_key == "신규":
                entry_date = entry_rng.choices(entry_days, weights=entry_weights, k=1)[0]
            else:  # 기존투자자(또는 플래그 off)는 첫날부터
                entry_date = self.trading_days[0]
            a = InvestorAgent(self, params, initial_cash, group, entry_date, init_pos)
            self.initial_assets[str(a.unique_id)] = total_asset
            if init_pos:  # 하네스 replay 시딩용 스냅샷 (p42 기초보유 플래그의 원천)
                self.initial_positions[str(a.unique_id)] = {
                    tk: dict(p) for tk, p in init_pos.items()
                }

    def _build_entry_distribution(self):
        """config.NEW_ENTRY_WEEKLY_WEIGHTS(주별)를 시뮬 거래일 단위 가중으로 전개.

        주 가중치를 그 주에 속한 거래일들에 균등 분할(주 내 일별 분포는 자료 없음 —
        균등이 최소 가정). 어떤 주에도 속하지 않는 거래일은 가중 0으로 제외된다."""
        weeks = [
            (datetime.strptime(d, "%Y-%m-%d").date(), w)
            for d, w in config.NEW_ENTRY_WEEKLY_WEIGHTS
        ]
        day_week: dict = {}  # 거래일 -> 주 시작일
        counts: dict = {}    # 주 시작일 -> 그 주의 거래일 수
        for d in self.trading_days:
            for ws, _ in weeks:
                if ws <= d < ws + timedelta(days=7):
                    day_week[d] = ws
                    counts[ws] = counts.get(ws, 0) + 1
                    break
        weight_of = dict(weeks)
        days = [d for d in self.trading_days if d in day_week]
        weights = [weight_of[day_week[d]] / counts[day_week[d]] for d in days]
        return days, weights
 
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

    def _prepare_market(self, tickers: list[str]):
        """코스피 지수 수익률과 월별 LOTT 합성값(고유변동성+주가, 둘 다 월말 고정)을 미리 계산.

        - get_prev_market_return용: 날짜 -> '전일에 끝난' 지수 수익률 (shift(1)).
          당일 종가 수익률을 그대로 쓰면 장중 매수 판단에 당일 종가가 새는 look-ahead.
          단, 아래 요인 회귀는 종목-요인 '동시점' 정렬이 맞으므로 shift 안 한 원본을 쓴다.
        - LOTT용: FF3 잔차 고유변동성+주가+EISKEW 랭크 합 — 계산은 7-3-1에서
          lott.compute_monthly_lott로 추출(동작 불변, 생성기와 피처 빌더가 공유.
          상세 주석은 lott.py 참조). '이번 달 계산 → 다음 달 적용'(get_lott_scores가
          직전 달을 조회)으로 룩어헤드를 구조적으로 차단.
        """
        idx = get_index_data()
        idx_close = idx.set_index("거래일자")["종가"].sort_index()

        close_wide = (
            self.price_data.pivot(index="거래일자", columns="종목코드", values="종가")
            .sort_index()
        )
        idx_ret = idx_close.pct_change().reindex(close_wide.index)  # 지수를 종목 캘린더에 정렬

        # 과잉확신 트리거용은 하루 밀어서(shift) 저장: _index_ret[d] = 전일에 끝난 수익률.
        prev_ret = idx_ret.shift(1)
        self._index_ret = {
            d: (None if pd.isna(r) else float(r)) for d, r in prev_ret.items()
        }

        # LOTT 월별 합성값 (lott.py로 추출 — FF3 요인 회귀·EISKEW 포함)
        self._monthly_lott: dict = compute_monthly_lott(self.price_data, idx, tickers)

        close_ffill = close_wide.ffill()  # attention 수익률 성분용 (정지일 직전가 대체)

        # --- attention 스코어 (7-1): 관측가능 시장 신호 기반 군집 채널 ---
        # 전일 비정상거래량(전일 거래량 / 그 이전 ATTN_VOL_AVG_DAYS일 평균)과 전일 종가
        # 기준 최근 ATTN_RET_DAYS일 수익률을 각각 일별 횡단면 pct 랭크 후 가중 합산.
        # 두 성분 모두 shift(1)로 '전일까지 확정된' 값만 쓴다 — 당일 거래량·종가는
        # 장중 look-ahead이므로 사용 금지(유동성 가드 _prev_volume과 동일 원칙).
        vol_wide = (
            self.price_data.pivot(index="거래일자", columns="종목코드", values="거래량")
            .sort_index()
        )
        # 분자: 최근 ATTN_VOL_SMOOTH_DAYS일 평균 거래량 (1이면 전일 단일일과 동일).
        # 분모: 그 이전 ATTN_VOL_AVG_DAYS일 평균 — 분자 창과 겹치지 않게 shift.
        S = config.ATTN_VOL_SMOOTH_DAYS
        abn_vol = vol_wide.rolling(S, min_periods=1).mean() / vol_wide.shift(S).rolling(
            config.ATTN_VOL_AVG_DAYS, min_periods=20
        ).mean()
        ret_recent = close_ffill.pct_change(config.ATTN_RET_DAYS)
        if config.ATTN_RET_MODE == "abs":
            ret_recent = ret_recent.abs()
        # 랭크 결측(초기 구간·데이터 갭)은 0.5(횡단면 중립)로 — 신호 없음 = 무편향 취급.
        r_vol = abn_vol.shift(1).rank(axis=1, pct=True).fillna(0.5)
        r_ret = ret_recent.shift(1).rank(axis=1, pct=True).fillna(0.5)
        self._attn_score = (
            config.ATTN_VOL_WEIGHT * r_vol + config.ATTN_RET_WEIGHT * r_ret
        )
 
    def record_trade(self, trade: Trade):
        # (7-1: 내부 breadth 집계(daily_buyers)는 attention 채널 교체로 제거 —
        #  군집 신호가 agent 매수 이력이 아니라 실측 시장 데이터(_attn_score)에서 나온다.)
        self.trades.append(trade)
 
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
        # LOTT/attention 랭크 정규화 — agent와 무관한 day-level 값이라 하루 1회만.
        cands = self._today_candidates
        lott = self.get_lott_scores(self.current_date)
        if lott:
            self._today_lott_norm = _rank_norm(
                cands, {t: lott.get(t, 0.0) for t in cands}
            )
        else:  # 데이터 없으면 전 종목 동률(중립) — 기존 agent 폴백과 동일
            self._today_lott_norm = {t: 0.0 for t in cands}
        # attention (7-1): 사전계산된 스코어(전일까지 확정 신호)를 오늘 후보로 랭크 정규화.
        if self.current_date in self._attn_score.index:
            row = self._attn_score.loc[self.current_date]
            neutral = 0.5 * (config.ATTN_VOL_WEIGHT + config.ATTN_RET_WEIGHT)
            vals = {t: float(row.get(t, neutral)) for t in cands}
            self._today_attn_norm = _rank_norm(cands, vals)
        else:
            self._today_attn_norm = {t: 0.0 for t in cands}
        self.agents.shuffle_do("step")
        self.day_idx += 1
 
    def run(self):
        for _ in range(len(self.trading_days)):
            self.step()
 
    # -- 출력 ------------------------------------------------------------------
    def trades_to_dataframe(self) -> pd.DataFrame:
        return pd.DataFrame([t.to_dict() for t in self.trades])
 