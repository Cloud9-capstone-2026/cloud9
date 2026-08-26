"""
KCMI 22-02 편향 측정 하네스.

KCMI가 각 편향을 측정한 방식을 그대로 재현하는 계산 로직. "표 숫자 = 파라미터 입력값"이
아니라 "표 숫자 = 재현해야 할 결과"라는 전제 위에서, 캘리브레이션보다 먼저 갖춘다.
5-4(전체 평균)·5-5(그룹 상대구조)·6단계에서 반복 재사용하는 커밋 모듈.

설계 전제 — trade log replay
    CSV/Trade 객체에는 평균단가·매입일이 없다. 보유기간·처분효과·회전율은 (agent, 종목)별
    포지션 상태(수량·가중평균단가·매입일)를 필요로 하므로, 거래로그를 실행순(=model.trades
    append 순서)으로 재생해 포지션을 복원한다.

    이 재생은 "매도 = 전량청산"(agent._execute_sell: qty=pos['수량'], del positions[ticker])
    불변식에 의존한다. 매도가 포지션을 매번 완전히 닫으므로 재생에 모호함이 없다.
    ★ 나중에 부분매도를 도입하면 이 하네스의 replay도 같이 손봐야 한다.

    입력은 CSV가 아니라 run() 직후의 model 객체(.trades, .price_data, .trading_days)다.

그룹 분해(5-5)
    agent.group(InvestorGroup, 표 Ⅲ-1 4축)을 이용해 축별(신규여부/성별/연령/자산)로
    보유기간·회전율·처분·과잉확신 감도를 분해하고, KCMI 기대 순서와의 일치(O/X)를 판정.
    복권 H-L·군집 β는 2-카테고리 축(신규여부·성별)만 — 연령·자산은 그룹당 거래 수가 적어
    30종목 횡단면에서 노이즈 과다(안정적이면 확대 검토).
"""

from collections import defaultdict

from datetime import date

import numpy as np
import pandas as pd

from .. import config

# 연율화 상수 — 한국 시장 연간 거래일 관례치. 원 논문(김민기·김준석 2021)에 정확한 상수가
# 명시돼 있지 않아 표준 가정. KCMI "연 1,600%"와 대조할 때 이 상수로 환산한다.
TRADING_DAYS_PER_YEAR = 250

# KCMI 22-02 목표치(대조용).
# 회전율 재앵커 (7-1d): 실측 연 1600%의 55.4%는 일중거래(당일 매수-매도, 21-11 그림
# Ⅱ-19)인데 본 생성기는 일중거래 채널이 구조적으로 없다(매수 당일 매도 배제). 따라서
# 우리 데이터의 올바른 대조치는 비일중 성분 = 1600% x (1-0.554) ~= 714%. 7-1d 이전의
# 1600% 달성은 보유평가액(분모)이 비현실적으로 작아서 가능했던 '맞는 숫자, 틀린
# 메커니즘'이었음 — 초기 보유 도입으로 분모가 현실화되며 드러남.
KCMI_TARGETS = {
    "holding_mean": 9.67,
    "holding_median": 3.0,
    "turnover_annual": 7.14,  # 연 714% (비일중 성분 — 위 주석)
    "disposition_ratio": 2.18,
    "sias_beta": 0.169,
}

# ---------------------------------------------------------------------------
# 그룹 축 정의 + KCMI 기대 순서 (순서 재현 판정표용)
# ---------------------------------------------------------------------------
_AXES = {
    "신규여부": lambda g: g.new_key,
    "성별": lambda g: g.gender,
    "연령": lambda g: g.age,
    "자산": lambda g: g.asset,
}
_AXIS_ORDER = {
    "신규여부": ["신규", "기존"],
    "성별": ["여성", "남성"],
    "연령": ["20대이하", "30대", "40대", "50대", "60대이상"],
    "자산": ["1천만원이하", "3천만원이하", "1억원이하", "1억원초과"],
}
# 회전율·과잉확신 공통 기대 순서(내림차순): 그림 Ⅳ-1.A / 표 Ⅳ-1 MKT(t-1) 동일 패턴.
_TURN_EXPECT = {
    "신규여부": ["신규", "기존"],
    "성별": ["남성", "여성"],
    "연령": ["20대이하", "30대", "40대", "50대", "60대이상"],
    "자산": ["1천만원이하", "3천만원이하", "1억원이하", "1억원초과"],
}
_EXPECTED = {
    "회전율": _TURN_EXPECT,
    "과잉확신": _TURN_EXPECT,
    # 처분(표 Ⅳ-4 분석(5)): 여>남, 30>40>20>50>60, 신규>기존.
    "처분": {
        "성별": ["여성", "남성"],
        "연령": ["30대", "40대", "20대이하", "50대", "60대이상"],
        "신규여부": ["신규", "기존"],
    },
    # 처분조정(6-0): agent 자기정규화 지표 — 활동수준 교란 제거 후 같은 기대 순서.
    "처분조정": {
        "성별": ["여성", "남성"],
        "연령": ["30대", "40대", "20대이하", "50대", "60대이상"],
        "신규여부": ["신규", "기존"],
    },
    # 복권 H-L(그림 Ⅳ-13 LOTT1): 남>여, 기존>신규(그림 판독 결과 그대로).
    "복권HL": {"성별": ["남성", "여성"], "신규여부": ["기존", "신규"]},
    # 군집 β(표 A3-1): 신규>기존, 여>남.
    "군집β": {"신규여부": ["신규", "기존"], "성별": ["여성", "남성"]},
}

# 보유종목수 분포 대조치 (김민기·김준석 2021 <그림 Ⅱ-9>, %): 1종목 / ≤3 / ≤10 / >10.
# 7-1c에서 신규 앵커로 도입 — 정확 재현이 아니라 분포 형태 접근이 목표(>3종목 보유자
# 유의미 비중 + 기존>신규 분산 순서).
_NSTOCK_KCMI = {"전체": (20, 39, 31, 9), "기존": (16, 39, 35, 11), "신규": (32, 41, 23, 3)}


# ---------------------------------------------------------------------------
# 가격 조회 맵
# ---------------------------------------------------------------------------
def _build_close_maps(model, trading_days):
    """(ticker, date)->종가 두 종류를 만든다.

    close_map : 그날 실제 체결 종가만(거래정지로 빠진 날은 키 없음). 처분효과 판정에 사용 —
                모델 _maybe_sell이 today_prices에 행이 없으면 그 종목을 건너뛰는 것과 정합.
    close_ff  : 종목별 직전 종가로 ffill. 보유평가액 MTM에 사용 — 거래정지일에도 보유분을
                평가하기 위함.
    """
    price = model.price_data
    price = price[price["거래일자"].isin(set(trading_days))]

    close_map: dict = {}
    for tk, d, c in zip(price["종목코드"], price["거래일자"], price["종가"]):
        close_map[(tk, d)] = float(c)

    tickers = sorted(price["종목코드"].unique())
    close_ff: dict = {}
    for tk in tickers:
        last = None
        for d in trading_days:
            c = close_map.get((tk, d))
            if c is not None:
                last = c
            if last is not None:
                close_ff[(tk, d)] = last
    return close_map, close_ff, tickers


# ---------------------------------------------------------------------------
# 핵심 replay — 포지션 복원 + 그룹별 지표 재료 누적
# ---------------------------------------------------------------------------
def _replay(model, trading_days, close_map, close_ff, group_of):
    """거래로그 재생. 모든 누적기는 InvestorGroup 단위로 키잉(축별 분해는 나중에 합산).

    group_of: agent_id(str) -> InvestorGroup (frozen dataclass, hashable).
    """
    day_index = {d: i for i, d in enumerate(trading_days)}

    trades_by_day: dict = defaultdict(list)
    for t in model.trades:  # model.trades는 실행순 → 일별로 모아도 일 내부 순서 보존
        trades_by_day[t.거래일자].append(t)

    positions: dict = defaultdict(dict)  # agent_id -> {ticker: {수량, 평균단가, 매입일}}
    # 보유종목수(7-1c-1, 그림 Ⅱ-9 대조): agent -> [보유종목수 일합, 보유일수, 첫거래 day_idx]
    nstock_agent: dict = defaultdict(lambda: [0.0, 0, None])

    # 기초보유 시딩 (7-1d, KCMI 22-02 p42): 시뮬 시작 전 보유분은 "매칭에는 반영하되
    # 이 수량이 매칭된 조합은 분석에서 제외" — replay에 포지션을 심되 플래그를 붙여
    # 보유기간·처분 패널에서 제외하고, 보유평가액 MTM·매도대금(회전율)에는 포함한다.
    # 추가 매수로 병합돼도 플래그 유지(조합 전체 제외), 전량 매도로 청산되면 해제
    # (이후 같은 종목 재매수는 신규 포지션). ★부분매도 도입 시 이 규칙도 재검토.
    basis_flag: set = set()  # {(agent_id, ticker)}
    for aid, pmap in getattr(model, "initial_positions", {}).items():
        for tk, pos in pmap.items():
            positions[aid][tk] = dict(pos)
            basis_flag.add((aid, tk))
        nstock_agent[aid][2] = 0  # 첫날부터 활동 (전기간 평균 분모)
    holding_periods: dict = defaultdict(list)   # group -> [보유 거래일수]
    holdings_value_by_day: dict = {}            # date -> {group: 보유평가액(ffill)}
    # KCMI(김민기·김준석 2021, p65-66) 회전율 분자는 "일간 매수·매도대금의 평균값"
    # = (매수대금+매도대금)/2. 합산이 아니라 평균이므로 매수/매도를 분리 집계한다.
    buy_value_by_day: dict = {}                 # date -> {group: 매수대금 합}
    sell_value_by_day: dict = {}                # date -> {group: 매도대금 합}
    buy_count_by_day: dict = {}                 # date -> {group: 매수 건수} (과잉확신 감도용)
    # group -> [gain_obs, gain_sold, loss_obs, loss_sold] (처분효과 position-day 패널)
    disp = defaultdict(lambda: [0, 0, 0, 0])
    # agent -> 동일 카운터 (6-0 조정 지표용): agent별 PGR_i/PLR_i는 자기 활동수준으로
    # 자기정규화되므로, 풀드 비조정 지표의 노출 혼합(저활동 그룹 부풀림)이 제거된다.
    disp_agent = defaultdict(lambda: [0, 0, 0, 0])
    # 복권형 초과보유용(풀드): 종목별 '그날 보유비중' 누적 → 일평균.
    holding_share_acc: dict = defaultdict(float)
    holding_share_days = 0

    for d in trading_days:
        day_trades = trades_by_day.get(d, [])

        # (1) 처분효과 관측: 오늘 '시작 시점' 보유 포지션 스냅샷(오늘 거래 적용 전).
        #     이 스냅샷의 포지션은 전부 매입일 < d 라 '매수 당일 제외'가 자동 충족된다.
        sold_today = {
            (t.agent_id, t.종목코드) for t in day_trades if t.거래구분 == "매도"
        }
        for agent_id, pos_map in positions.items():
            g = group_of[agent_id]
            for ticker, pos in pos_map.items():
                if (agent_id, ticker) in basis_flag:
                    continue  # 기초보유 — 처분 패널 제외 (p42)
                c = close_map.get((ticker, d))  # 실제 체결 종가만(모델 skip과 정합)
                if c is None:
                    continue
                is_gain = c >= pos["평균단가"]  # 등호 포함 (agent.py와 동일)
                sold = (agent_id, ticker) in sold_today
                ca = disp_agent[agent_id]
                if is_gain:
                    disp[g][0] += 1
                    disp[g][1] += sold
                    ca[0] += 1
                    ca[1] += sold
                else:
                    disp[g][2] += 1
                    disp[g][3] += sold
                    ca[2] += 1
                    ca[3] += sold

        # (2) 오늘 거래 적용(실행순) + 그룹별 매수/매도대금·건수 집계.
        bv, sv, bc = defaultdict(float), defaultdict(float), defaultdict(int)
        for t in day_trades:
            aid, ticker, qty = t.agent_id, t.종목코드, int(t.거래수량)
            g = group_of[aid]
            if nstock_agent[aid][2] is None:  # 첫 거래일 기록 (전기간 평균 분모용)
                nstock_agent[aid][2] = day_index[d]
            if t.거래구분 == "매도":
                sv[g] += float(t.거래금액)
                pos = positions[aid].get(ticker)
                if pos is not None:
                    if (aid, ticker) in basis_flag:
                        # 기초보유 청산 — 보유기간 제외(p42), 플래그 해제(재매수는 신규)
                        basis_flag.discard((aid, ticker))
                    else:
                        holding_periods[g].append(
                            day_index[d] - day_index[pos["매입일"]]
                        )
                    del positions[aid][ticker]
            else:  # 매수 — 병합(수량 합산·가중평균단가·매입일 최초 유지), agent._execute_buy와 동일
                bv[g] += float(t.거래금액)
                bc[g] += 1
                price_ = float(t.거래단가)
                pos = positions[aid].get(ticker)
                if pos is None:
                    positions[aid][ticker] = {
                        "수량": qty, "평균단가": price_, "매입일": d
                    }
                else:
                    new_qty = pos["수량"] + qty
                    pos["평균단가"] = (
                        pos["평균단가"] * pos["수량"] + price_ * qty
                    ) / new_qty
                    pos["수량"] = new_qty
        buy_value_by_day[d] = dict(bv)
        sell_value_by_day[d] = dict(sv)
        buy_count_by_day[d] = dict(bc)

        # (3) end-of-day 보유평가액(ffill 종가) — MTM 로직 공유, 종목별+그룹별 분해.
        v_by_ticker: dict = defaultdict(float)
        v_by_group: dict = defaultdict(float)
        for agent_id, pos_map in positions.items():
            g = group_of[agent_id]
            if pos_map:  # end-of-day 보유종목수 누적 (그림 Ⅱ-9 '일평균 보유종목수')
                st = nstock_agent[agent_id]
                st[0] += len(pos_map)
                st[1] += 1
            for ticker, pos in pos_map.items():
                c = close_ff.get((ticker, d))
                if c is not None:
                    val = pos["수량"] * c
                    v_by_ticker[ticker] += val
                    v_by_group[g] += val
        holdings_value_by_day[d] = dict(v_by_group)
        total_v = sum(v_by_ticker.values())
        if total_v > 0:  # 초과보유용: 그날 종목별 보유비중 누적(풀드)
            holding_share_days += 1
            for ticker, vv in v_by_ticker.items():
                holding_share_acc[ticker] += vv / total_v

    holding_weight = (
        {t: s / holding_share_days for t, s in holding_share_acc.items()}
        if holding_share_days > 0 else {}
    )
    return {
        "holding_periods": dict(holding_periods),
        "nstock_agent": dict(nstock_agent),
        "holdings_value_by_day": holdings_value_by_day,
        "buy_value_by_day": buy_value_by_day,
        "sell_value_by_day": sell_value_by_day,
        "buy_count_by_day": buy_count_by_day,
        "disp": dict(disp),
        "disp_agent": dict(disp_agent),
        "holding_weight": holding_weight,
    }


def _slice_days(day_group_map, member):
    """date -> {group: v} 를 member(그룹 집합)에 대해 합산해 date -> float 로."""
    return {
        d: sum(v for g, v in gv.items() if g in member)
        for d, gv in day_group_map.items()
    }


def _turnover(trading_days, holdings_value_by_day, buy_value_by_day, sell_value_by_day):
    """풀드 일별 회전율 (KCMI/김민기·김준석 2021 정의, p65-66).

    분자 = 일간 매수·매도대금의 '평균값' = (매수대금+매도대금)/2 — 합산 아님.
    분모 = 전일·당일 보유평가액의 평균(첫날은 당일값만).
    ※ 초기 구현이 분자를 합산으로 잘못 써서 2배 부풀려진 3978%로 측정했었음(소급 정정)."""
    turnovers = []
    for i, d in enumerate(trading_days):
        num = (buy_value_by_day.get(d, 0.0) + sell_value_by_day.get(d, 0.0)) / 2.0
        v_today = holdings_value_by_day.get(d, 0.0)
        if i == 0:
            den = v_today  # 전일 보유평가액 없음 → 당일값만
        else:
            v_prev = holdings_value_by_day.get(trading_days[i - 1], 0.0)
            den = (v_prev + v_today) / 2.0
        if den > 0:
            turnovers.append(num / den)
    d_daily = float(np.mean(turnovers)) if turnovers else float("nan")
    return {
        "daily": d_daily,
        "annual": d_daily * TRADING_DAYS_PER_YEAR,
        "cum_period": d_daily * len(trading_days),
        "n_days": len(trading_days),
    }


def _disposition(counters):
    """[gain_obs, gain_sold, loss_obs, loss_sold] -> PGR/PLR 비율."""
    go, gs, lo, ls = counters
    pgr = gs / go if go else float("nan")
    plr = ls / lo if lo else float("nan")
    ratio = (pgr / plr) if (plr and not np.isnan(plr) and plr != 0) else float("nan")
    return {"pgr": pgr, "plr": plr, "ratio": ratio, "gain_obs": go, "loss_obs": lo}


def _overconf_sensitivity(trading_days, index_ret, buy_count_by_day, member):
    """과잉확신 간이 감도: 전일 시장수익률 상승일 vs 비상승일의 일평균 매수건수 비율.

    index_ret은 model._index_ret(=shift(1) 적용, agent가 실제로 보는 값)와 동일 소스 —
    생성(당일 반응)과 측정(전일 반응)의 시차가 어긋나지 않는다. VAR 아님(간이 지표)."""
    up, dn = [], []
    for d in trading_days:
        r = index_ret.get(d)
        if r is None:
            continue
        n = sum(v for g, v in buy_count_by_day.get(d, {}).items() if g in member)
        (up if r > 0 else dn).append(n)
    if not up or not dn:
        return float("nan")
    dn_m = float(np.mean(dn))
    return float(np.mean(up)) / dn_m if dn_m > 0 else float("nan")


def _sias_beta(trades, trading_days, tickers):
    """Sias(2004) 군집거래 β = 시차1일 횡단면 상관.

    비중 = 매수자수/(매수자수+매도자수) (distinct agent, Sias 원식). 그날 매수·매도 둘 다
    0인 종목은 횡단면에서 제외. 각 날 횡단면 z-score 표준화 후 인접 두 날 상관의 평균.
    trades를 인자로 받아 그룹 필터링된 부분집합에도 재사용."""
    buyers: dict = defaultdict(set)
    sellers: dict = defaultdict(set)
    for t in trades:
        key = (t.종목코드, t.거래일자)
        (buyers if t.거래구분 == "매수" else sellers)[key].add(t.agent_id)

    frac: dict = {}
    for d in trading_days:
        for tk in tickers:
            b = len(buyers.get((tk, d), ()))
            s = len(sellers.get((tk, d), ()))
            if b + s > 0:
                frac[(tk, d)] = b / (b + s)

    z: dict = {}
    for d in trading_days:
        vals = [(tk, frac[(tk, d)]) for tk in tickers if (tk, d) in frac]
        if len(vals) < 2:
            continue
        arr = np.array([v for _, v in vals])
        sd = arr.std(ddof=0)
        if sd == 0:
            continue
        mu = arr.mean()
        for tk, v in vals:
            z[(tk, d)] = (v - mu) / sd

    corrs = []
    for i in range(1, len(trading_days)):
        d, dp = trading_days[i], trading_days[i - 1]
        pairs = [
            (z[(tk, d)], z[(tk, dp)])
            for tk in tickers
            if (tk, d) in z and (tk, dp) in z
        ]
        if len(pairs) < 2:
            continue
        a = np.array([p[0] for p in pairs])
        b = np.array([p[1] for p in pairs])
        if a.std() == 0 or b.std() == 0:
            continue
        corrs.append(float(np.corrcoef(a, b)[0, 1]))

    return {
        "beta": float(np.mean(corrs)) if corrs else float("nan"),
        "n_day_pairs": len(corrs),
    }


# ---------------------------------------------------------------------------
# 복권형 이원 지표 (그림 Ⅳ-12 보유 / Ⅳ-13 거래)
# ---------------------------------------------------------------------------
def _lottery_rank(model, trading_days):
    """종목별 LOTT 랭크(공통). 시뮬 각 달에 '적용된' LOTT 합성값(직전 달 계산치)을 평균 후
    종목 횡단면 pct 랭크. 6-4·6-5부터 KCMI LOTT(1) 3축(FF3 고유변동성+주가+EISKEW) 완성.
    데이터 없으면 None."""
    sim_months = sorted({(d.year, d.month) for d in trading_days})
    acc: dict = defaultdict(list)
    for (yy, mm) in sim_months:
        # 시장 전체 순위표는 적용월 기준이라 model.get_lott_scores가 그 달 값을 바로 준다
        # (예전엔 직전 달 계산치 _monthly_lott를 여기서 매핑했음 — 2026-08-26 표로 통일).
        for tk, sc in model.get_lott_scores(date(yy, mm, 1)).items():
            acc[tk].append(sc)
    avg = {tk: float(np.mean(v)) for tk, v in acc.items() if v}
    if len(avg) < 2:
        return None
    return pd.Series(avg).rank(pct=True)  # ticker -> [0,1]


def _excess_summary(lott_rank, excess):
    """초과비중(excess)을 LOTT 랭크 5분위로 묶어 '분위 합산' 초과비중을 산출.

    7-2 단위 정정: 기존엔 상·하위 분위의 '종목별 평균' 초과를 H/L로 썼는데, KCMI
    그림 Ⅳ-12/Ⅳ-13은 분위 '합산' 초과비중이다(본문 p61-62: 보유 High +6%/Q4 +8%/
    Low -30%(LOTT1), 거래 High +21%/Q4 +14%/Q2 -8%/Low -30%(LOTT2 기준 인용)).
    따라서 5-5~7-1의 '거래 H-L 5.1%'는 KCMI 공표치와 직접 비교할 수 없는 자체
    통계였음 — 분위 합산으로 정정하고 앵커를 공표 수치(거래 H-L ~ +51%p)로 교체.
    주의: 공표 거래비중 수치는 LOTT(2) 기준 인용이고 우리 랭크는 LOTT(1) — 본문이
    "질적 차이 없음"을 명시하나 수치 잔차의 일부는 이 차이에서 올 수 있음(문서화)."""
    common = [t for t in excess.index if t in lott_rank.index]
    if len(common) < 2:
        return None
    lr = lott_rank.loc[common]
    ex = excess.loc[common]
    order = lr.sort_values(ascending=False).index.tolist()
    k = max(1, len(order) // 5)
    H = float(ex.loc[order[:k]].sum())
    L = float(ex.loc[order[-k:]].sum())
    return {
        "corr": float(lr.corr(ex)), "H": H, "L": L, "HmL": H - L,
        "n": len(common), "k": k,
    }


def _holding_excess(lott_rank, holding_weight, marketcap):
    """초과보유비중(그림 Ⅳ-12): 우리 개인 보유분포 − 시총분포. 시총 dict 없으면 None."""
    mcap = {t: c for t, c in (marketcap or {}).items() if c > 0}
    if not mcap or lott_rank is None or not holding_weight:
        return None
    tickers = sorted(mcap)
    total_cap = sum(mcap[t] for t in tickers)
    hw = pd.Series({t: float(holding_weight.get(t, 0.0)) for t in tickers})
    if total_cap <= 0 or hw.sum() <= 0:
        return None
    hw = hw / hw.sum()
    cap = pd.Series({t: mcap[t] / total_cap for t in tickers})
    return _excess_summary(lott_rank, hw - cap)


def _trading_excess(trades, lott_rank, inst_foreign):
    """초과거래비중(그림 Ⅳ-13): 우리 개인 거래분포 − 기관외국인 거래분포.

    각자 유형 내에서 정규화(합 1)해 빼므로 토이 볼륨 vs 실측 볼륨 스케일이 상쇄된다.
    trades를 인자로 받아 그룹 필터링된 부분집합에도 재사용."""
    inf = {t: v for t, v in (inst_foreign or {}).items() if v > 0}
    if not inf or lott_rank is None:
        return None
    tickers = sorted(inf)
    tv: dict = defaultdict(float)
    for tr in trades:
        tv[tr.종목코드] += float(tr.거래금액)
    total_tv = sum(tv.get(t, 0.0) for t in tickers)
    total_bench = sum(inf[t] for t in tickers)
    if total_tv <= 0 or total_bench <= 0:
        return None
    our = pd.Series({t: tv.get(t, 0.0) / total_tv for t in tickers})
    bench = pd.Series({t: inf[t] / total_bench for t in tickers})
    return _excess_summary(lott_rank, our - bench)


def _lottery(model, trading_days, holding_weight):
    """복권형 이원 지표(그림 Ⅳ-12 보유 + Ⅳ-13 거래). LOTT 랭크는 공유."""
    lott_rank = _lottery_rank(model, trading_days)
    return {
        "holding": _holding_excess(
            lott_rank, holding_weight, getattr(config, "MARKETCAP_20200302", {})
        ),
        "trading": _trading_excess(
            model.trades, lott_rank, getattr(config, "INST_FOREIGN_TRADEVALUE", {})
        ),
    }


# ---------------------------------------------------------------------------
# 진입점
# ---------------------------------------------------------------------------
def compute_metrics(model) -> dict:
    """run() 끝난 model에서 KCMI 지표(풀드 + 축별 그룹 분해)를 측정해 dict로 반환."""
    trading_days = list(model.trading_days)
    group_of = {str(a.unique_id): a.group for a in model.agents}
    all_groups = set(group_of.values())
    n_agents_of = defaultdict(int)
    for g in group_of.values():
        n_agents_of[g] += 1

    close_map, close_ff, tickers = _build_close_maps(model, trading_days)
    rp = _replay(model, trading_days, close_map, close_ff, group_of)
    lott_rank = _lottery_rank(model, trading_days)

    def _adj_disposition(member):
        """6-0 조정 처분: agent별 PGR_i/PLR_i(자기정규화)의 그룹 중앙값.

        비조정 풀드 지표는 노출 혼합으로 저활동 그룹이 부풀려짐(KCMI Cox는 Turn 통제).
        최소 관측 필터(gain/loss obs>=10, 각 매도>=2)로 불안정 비율 제외 — 필터 통과
        agent 수(n)를 함께 보고해 선택편향 정도를 드러낸다."""
        ratios = []
        for aid, g in group_of.items():
            if g not in member:
                continue
            c = rp["disp_agent"].get(aid)
            if not c:
                continue
            go, gs, lo, ls = c
            if go >= 10 and lo >= 10 and gs >= 2 and ls >= 2:
                ratios.append((gs / go) / (ls / lo))
        return {
            "median": float(np.median(ratios)) if ratios else float("nan"),
            "n": len(ratios),
        }

    def _nstock_dist(member):
        """일평균 보유종목수 분포(그림 Ⅱ-9 대조, 7-1c-1).

        주 정의 = 보유일 기준 평균(보유 종목이 있던 날만 분모). 참고 정의 = 첫 거래
        이후 전 거래일 기준(무보유일 0 포함) — KCMI '일평균'의 분모가 명시돼 있지 않아
        두 정의를 모두 계산·보고하고 그림에 가까운 쪽을 해석 기준으로 삼는다."""
        held, full = [], []
        n_days = len(trading_days)
        for aid, g in group_of.items():
            if g not in member:
                continue
            st = rp["nstock_agent"].get(aid)
            if not st or st[1] == 0:
                continue
            held.append(st[0] / st[1])
            full.append(st[0] / (n_days - st[2]))

        def buckets(vals):
            n = len(vals)
            if not n:
                return None
            edges = [(0.0, 1.0), (1.0, 3.0), (3.0, 10.0), (10.0, float("inf"))]
            return [100.0 * sum(1 for v in vals if lo < v <= hi) / n for lo, hi in edges]

        return {
            "n": len(held),
            "mean": float(np.mean(held)) if held else float("nan"),
            "buckets": buckets(held),
            "buckets_full": buckets(full),
        }

    def _metrics_for(member):
        hp = [x for g in member for x in rp["holding_periods"].get(g, [])]
        holding = {
            "mean": float(np.mean(hp)) if hp else float("nan"),
            "median": float(np.median(hp)) if hp else float("nan"),
            "n": len(hp),
        }
        turnover = _turnover(
            trading_days,
            _slice_days(rp["holdings_value_by_day"], member),
            _slice_days(rp["buy_value_by_day"], member),
            _slice_days(rp["sell_value_by_day"], member),
        )
        counters = [0, 0, 0, 0]
        for g in member:
            c = rp["disp"].get(g)
            if c:
                for i in range(4):
                    counters[i] += c[i]
        disposition = _disposition(counters)
        overconf = _overconf_sensitivity(
            trading_days, model._index_ret, rp["buy_count_by_day"], member
        )
        return holding, turnover, disposition, overconf

    # --- 풀드 ---
    holding, turnover, disposition, overconf = _metrics_for(all_groups)
    disposition_adj = _adj_disposition(all_groups)
    sias = _sias_beta(model.trades, trading_days, tickers)
    lottery = _lottery(model, trading_days, rp["holding_weight"])
    newfn = _AXES["신규여부"]
    assetfn = _AXES["자산"]
    nstock = {
        "전체": _nstock_dist(all_groups),
        "기존": _nstock_dist({g for g in all_groups if newfn(g) == "기존"}),
        "신규": _nstock_dist({g for g in all_groups if newfn(g) == "신규"}),
        # 자산축 평균 (그림 Ⅱ-10 '자산↑=종목수↑' 단조 확인용)
        "자산": {
            cat: _nstock_dist({g for g in all_groups if assetfn(g) == cat})
            for cat in _AXIS_ORDER["자산"]
        },
    }

    # --- 축별 분해 ---
    groups_out: dict = {}
    for axis, keyfn in _AXES.items():
        cats: dict = {}
        for cat in _AXIS_ORDER[axis]:
            member = {g for g in all_groups if keyfn(g) == cat}
            if not member:
                continue
            h, to, dp, oc = _metrics_for(member)
            adj = _adj_disposition(member)
            entry = {
                "n_agents": sum(n_agents_of[g] for g in member),
                "holding_mean": h["mean"], "holding_median": h["median"],
                "turnover_annual": to["annual"],
                "disp_ratio": dp["ratio"],
                "disp_adj": adj["median"], "disp_adj_n": adj["n"],
                "overconf": oc,
                "lottery_HmL": None, "sias_beta": None,
            }
            # 복권 H-L·군집 β는 2-카테고리 축만 (연령·자산은 표본 얇아 노이즈 과다)
            if axis in ("신규여부", "성별"):
                sub = [t for t in model.trades if keyfn(group_of[t.agent_id]) == cat]
                te = _trading_excess(
                    sub, lott_rank, getattr(config, "INST_FOREIGN_TRADEVALUE", {})
                )
                entry["lottery_HmL"] = te["HmL"] if te else None
                entry["sias_beta"] = _sias_beta(sub, trading_days, tickers)["beta"]
            cats[cat] = entry
        groups_out[axis] = cats

    return {
        "n_trades": len(model.trades),
        "holding": holding,
        "turnover": turnover,
        "disposition": disposition,
        "disposition_adj": disposition_adj,
        "overconf": overconf,
        "sias": sias,
        "lottery": lottery,
        "nstock": nstock,
        "groups": groups_out,
    }


# ---------------------------------------------------------------------------
# 리포트
# ---------------------------------------------------------------------------
def _fmt(v, pct=False):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "n/a"
    return f"{v * 100:.1f}%" if pct else f"{v:.3f}"


def _order_of(cats: dict, field, reverse=True):
    """카테고리를 field 값 기준 내림차순(기본) 정렬한 이름 리스트."""
    valid = [
        (c, e[field]) for c, e in cats.items()
        if e[field] is not None and not (isinstance(e[field], float) and np.isnan(e[field]))
    ]
    return [c for c, _ in sorted(valid, key=lambda x: x[1], reverse=reverse)]


def print_report(m: dict):
    T = KCMI_TARGETS
    print("=" * 66)
    print(f"KCMI 22-02 편향 측정  (거래 {m['n_trades']:,}건)")
    print("=" * 66)

    h = m["holding"]
    print("\n[보유기간]  (거래일 수, n={})".format(h["n"]))
    print(f"  평균  : {_fmt(h['mean'])}  ← KCMI {T['holding_mean']}")
    print(f"  중앙값: {_fmt(h['median'])}  ← KCMI {T['holding_median']}")

    tv = m["turnover"]
    print("\n[회전율]  (풀드, 분자=(매수+매도)/2 — KCMI 정의)")
    print(f"  일평균          : {_fmt(tv['daily'], pct=True)}")
    print(f"  연율화 (×{TRADING_DAYS_PER_YEAR}) : {_fmt(tv['annual'], pct=True)}"
          f"  ← KCMI 연 {T['turnover_annual'] * 100:.0f}%")
    print(f"  {tv['n_days']}일 누적       : {_fmt(tv['cum_period'], pct=True)}  (관측기간 그대로)")

    dp = m["disposition"]
    print("\n[처분효과 위험비율]  (position-day PGR/PLR)")
    print(f"  PGR(이익 실현율)={_fmt(dp['pgr'])} (obs {dp['gain_obs']:,}), "
          f"PLR(손실 실현율)={_fmt(dp['plr'])} (obs {dp['loss_obs']:,})")
    print(f"  비율 PGR/PLR : {_fmt(dp['ratio'])}  ← KCMI {T['disposition_ratio']}")
    da = m["disposition_adj"]
    print(f"  조정(agent 자기정규화 중앙값): {_fmt(da['median'])}  (유효 agent {da['n']:,})")

    print(f"\n[과잉확신 감도]  (상승 다음날/비상승 다음날 매수건수 비율, 간이)")
    print(f"  전체 : {_fmt(m['overconf'])}  (>1이면 과잉확신 방향)")

    s = m["sias"]
    print("\n[Sias 군집거래 β]  (시차1 횡단면 상관, 일쌍 {})".format(s["n_day_pairs"]))
    print(f"  β : {_fmt(s['beta'])}  ← KCMI {T['sias_beta']}")

    print("\n[복권형 선호]  (LOTT 5분위 '합산' 초과비중 — 7-2 단위 정정)")
    print("  KCMI 대조: 보유(Ⅳ-12) H-L ~ +36%p (High+6/Low-30), "
          "거래(Ⅳ-13) H-L ~ +51%p (High+21/Low-30, LOTT2 인용)")
    lot = m["lottery"]

    def _excess_line(label, r, bench_hint):
        if r is None:
            print(f"  {label}: 미설정 → skip  ({bench_hint})")
        else:
            print(f"  {label}: H {_fmt(r['H'], pct=True)}  L {_fmt(r['L'], pct=True)}  "
                  f"H-L {_fmt(r['HmL'], pct=True)}  corr {_fmt(r['corr'])}  "
                  f"(n={r['n']}, 분위 {r['k']})")

    _excess_line("초과보유(vs 시총)   ", lot["holding"], "MARKETCAP_20200302")
    _excess_line("초과거래(vs 기관외국)", lot["trading"], "INST_FOREIGN_TRADEVALUE")

    print("\n[보유종목수]  (일평균 분포 %: 1종목/≤3/≤10/>10 — 그림 Ⅱ-9 대조)")
    for label in ("전체", "기존", "신규"):
        e = m["nstock"][label]
        if e["buckets"] is None:
            continue
        b = "/".join(f"{x:.0f}" for x in e["buckets"])
        bf = "/".join(f"{x:.0f}" for x in e["buckets_full"])
        ref = "/".join(str(x) for x in _NSTOCK_KCMI[label])
        print(f"  {label}: {b} (전기간 기준 {bf})  ← KCMI {ref}"
              f"  (n={e['n']:,}, 평균 {e['mean']:.1f}종목)")
    asset_means = " > ".join(
        f"{cat} {e['mean']:.1f}" for cat, e in m["nstock"]["자산"].items()
        if e["buckets"] is not None
    )
    print(f"  자산축 평균(기대: 자산이 클수록 큼 — 그림 Ⅱ-10): {asset_means}")

    # --- 그룹 분해 ---
    print("\n" + "-" * 66)
    print("[그룹 분해]  (축별, 나머지 축 풀링)")
    for axis, cats in m["groups"].items():
        print(f"\n  ◆ {axis}")
        print(f"    {'카테고리':<10} {'n':>5} {'보유(평균/중앙)':>14} {'회전율':>9} "
              f"{'처분':>7} {'처분조정':>8} {'과잉감도':>8} {'복권H-L':>8} {'군집β':>7}")
        for cat in _AXIS_ORDER[axis]:
            if cat not in cats:
                continue
            e = cats[cat]
            lot_s = _fmt(e["lottery_HmL"], pct=True) if e["lottery_HmL"] is not None else "-"
            sias_s = _fmt(e["sias_beta"]) if e["sias_beta"] is not None else "-"
            print(f"    {cat:<10} {e['n_agents']:>5} "
                  f"{e['holding_mean']:>7.2f}/{e['holding_median']:<5.1f} "
                  f"{e['turnover_annual']*100:>8.0f}% "
                  f"{_fmt(e['disp_ratio']):>7} {_fmt(e['disp_adj']):>8} "
                  f"{_fmt(e['overconf']):>8} {lot_s:>8} {sias_s:>7}")

    # --- 순서 재현 판정표 ---
    print("\n" + "-" * 66)
    print("[순서 재현 판정표]  (KCMI 기대 순서 vs 측정 순서)")
    field_of = {
        "회전율": ("turnover_annual", True),
        "처분": ("disp_ratio", True),
        "처분조정": ("disp_adj", True),
        "과잉확신": ("overconf", True),
        "복권HL": ("lottery_HmL", True),
        "군집β": ("sias_beta", True),
    }
    for metric, per_axis in _EXPECTED.items():
        field, rev = field_of[metric]
        for axis, expected in per_axis.items():
            cats = m["groups"].get(axis, {})
            measured = _order_of(cats, field, reverse=rev)
            ok = "O" if measured == expected else "X"
            print(f"  {metric}×{axis}: 기대 {'>'.join(expected)}")
            print(f"    측정 {'>'.join(measured) if measured else '(측정불가)'} → {ok}")
    # 보유기간(파생 기대: 회전율 역순 — 회전 높을수록 짧게 보유)
    for axis, expected in _TURN_EXPECT.items():
        cats = m["groups"].get(axis, {})
        measured = _order_of(cats, "holding_mean", reverse=False)  # 짧은 순
        ok = "O" if measured == expected else "X"
        print(f"  보유(파생)×{axis}: 기대(짧은순) {'>'.join(expected)}")
        print(f"    측정 {'>'.join(measured) if measured else '(측정불가)'} → {ok}")
    print("=" * 66)


if __name__ == "__main__":
    from ..core.model import MarketModel

    print(f"모델 구동: N={config.N_INVESTORS} ...")
    model = MarketModel(
        n_investors=config.N_INVESTORS,
        tickers=config.UNIVERSE_TICKERS,
        seed=config.RANDOM_SEED,
    )
    model.run()
    print_report(compute_metrics(model))
