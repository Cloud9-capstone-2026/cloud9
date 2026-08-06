"""
피처 골든 스냅샷 — build_features의 출력 값 자체를 박제한다.

목적: 시세 조회 경로를 캐시로 바꾸는 등의 수술에서 값이 에러 없이
조용히 달라지는 사고를 즉시 감지. 손으로 검산 가능한 필드(실현수익률·
보유일수)는 수식으로, 시장 컨텍스트 필드는 첫 실행에서 얻은 값을 상수로 동결.
"""

import numpy as np
import pandas as pd
import pytest


@pytest.fixture(scope="module")
def events(synthetic_trades, price_df, index_df):
    from synthetic_data.features import build_features

    out = build_features(synthetic_trades.copy(), price_df, index_df, windows=(None,))
    return out["events"].reset_index(drop=True)


def _close(price_df, tk, day):
    sel = price_df[(price_df["종목코드"] == tk) & (price_df["거래일자"] == day)]
    return float(sel["종가"].iloc[0])


def test_events_one_row_per_trade(events, synthetic_trades):
    assert len(events) == len(synthetic_trades)


def test_return_at_sale_exact(events, price_df):
    """매도 실현수익률 = 체결가/평균단가 − 1 (체결가 = 픽스처 종가라 수식 검산)."""
    days = sorted(price_df["거래일자"].unique())
    sells = events[events["거래구분"] == "매도"].set_index(
        events[events["거래구분"] == "매도"]["종목코드"].astype(str) + "@"
        + events[events["거래구분"] == "매도"]["거래일자"].astype(str)
    )

    # 000010: 60일 종가에 10주 매수 → 66일 종가에 전량 매도
    buy, sell = _close(price_df, "000010", days[60]), _close(price_df, "000010", days[66])
    key = f"000010@{days[66]}"
    assert key in sells.index
    assert sells.loc[key, "return_at_sale"] == pytest.approx(sell / buy - 1, abs=1e-9)
    assert sells.loc[key, "holding_days"] == 6  # 66-60 (거래일 기준)

    # 000030: 68일 매수 → 80일 매도
    buy, sell = _close(price_df, "000030", days[68]), _close(price_df, "000030", days[80])
    key = f"000030@{days[80]}"
    assert sells.loc[key, "return_at_sale"] == pytest.approx(sell / buy - 1, abs=1e-9)


def test_basis_known_for_all_sells(events):
    """전 매도가 관측된 매수에서 나왔으므로 원가 미상이 없어야 한다."""
    sells = events[events["거래구분"] == "매도"]
    assert sells["return_at_sale"].notna().all()


def test_market_context_golden(events):
    """시장 컨텍스트(전일수익률·비정상거래량·지수) 골든 값 — 첫 실행에서 동결.

    이 테스트가 깨졌다면: (1) 시세 조회/캐시 경로가 값을 바꿨거나
    (2) features의 컨텍스트 계산 정의가 바뀐 것. 둘 다 조용히 지나가면 안 되는
    변화다 — 의도한 변경이면 아래 상수를 갱신하고 사유를 커밋 메시지에 남길 것.
    """
    golden = {
        # (행 위치, 컬럼): 동결 값 — capture_golden.py 산출
        (0, "prior_ret1"): GOLDEN_PRIOR_RET1_ROW0,
        (4, "abn_vol"): GOLDEN_ABN_VOL_ROW4,      # 거래량 급증 구간의 매도
        (5, "abn_vol"): GOLDEN_ABN_VOL_ROW5,      # 급증 구간의 매수
    }
    for (i, col), want in golden.items():
        got = float(events.loc[i, col])
        assert got == pytest.approx(want, rel=1e-6), (i, col)


# ─ 동결 상수 (backend/tests/capture_golden.py 1회 실행 산출값, 2026-08-05) ─
GOLDEN_PRIOR_RET1_ROW0 = -0.0009214891264283098
GOLDEN_ABN_VOL_ROW4 = 5.029153869973839
GOLDEN_ABN_VOL_ROW5 = 4.165366035442259
