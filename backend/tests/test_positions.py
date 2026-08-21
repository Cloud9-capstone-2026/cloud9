"""
포지션 재생(rule_based/positions.py) 검산 — 손계산 대조, 네트워크·모델 0.

각 행의 결과는 "그 거래 적용 직전" 상태라는 규약과, 평균단가법 원가 계산,
엣지 정책(이력 밖 잔고 매도, 같은 날 순서 유지)을 고정한다.
"""

import pandas as pd
import pytest

from models.rule_based.positions import replay_positions


def _df(rows):
    """rows: (날짜, 종목명, 구분, 수량, 단가)"""
    return pd.DataFrame(
        [{"날짜": pd.Timestamp(d), "종목명": s, "매매구분": k,
          "체결수량": q, "체결단가": p} for d, s, k, q, p in rows]
    )


def test_average_cost_and_realized_pnl():
    """매수→추가매수→일부매도→전량매도 — 평단·손익을 자릿수까지 검산."""
    df = _df([
        ("2020-06-01", "A", "매수", 100, 10000),
        ("2020-06-03", "A", "매수", 100, 12000),   # 평단 11000으로
        ("2020-06-05", "A", "매도", 50, 13000),    # 익절 (13000-11000)*50
        ("2020-06-08", "A", "매도", 150, 9000),    # 손절 (9000-11000)*150
    ])
    out = replay_positions(df)

    assert out.loc[1, "보유수량_직전"] == 100
    assert out.loc[1, "평균단가_직전"] == 10000

    assert out.loc[2, "보유수량_직전"] == 200
    assert out.loc[2, "평균단가_직전"] == 11000       # (100*10000+100*12000)/200
    assert out.loc[2, "실현손익"] == (13000 - 11000) * 50

    assert out.loc[3, "보유수량_직전"] == 150
    assert out.loc[3, "평균단가_직전"] == 11000       # 매도는 평단 불변
    assert out.loc[3, "실현손익"] == (9000 - 11000) * 150
    assert not out["원가미상"].any()


def test_averaging_down_visible_from_prior_avg():
    """물타기 판정 재료 — 낮은 가격 추가 매수 시 '직전 평단'이 보인다."""
    df = _df([
        ("2020-06-01", "A", "매수", 100, 10000),
        ("2020-06-02", "A", "매수", 100, 8000),    # 평단(10000)보다 낮은 매수
    ])
    out = replay_positions(df)
    assert out.loc[1, "평균단가_직전"] == 10000  # 규칙: 체결단가 8000 < 이 값 → 물타기


def test_loss_sale_date_tracked_for_reentry():
    """재진입 판정 재료 — 손실 매도일이 이후 매수 행에 보인다."""
    df = _df([
        ("2020-06-01", "A", "매수", 100, 10000),
        ("2020-06-03", "A", "매도", 100, 9000),    # 손실 확정
        ("2020-06-05", "A", "매수", 50, 9500),     # 재진입
        ("2020-06-09", "B", "매수", 10, 5000),     # 다른 종목은 무관
    ])
    out = replay_positions(df)
    assert out.loc[1, "최근손실매도일"] is pd.NaT or pd.isna(out.loc[1, "최근손실매도일"])
    assert out.loc[2, "최근손실매도일"] == pd.Timestamp("2020-06-03")
    assert pd.isna(out.loc[3, "최근손실매도일"])   # B 종목엔 손실 이력 없음


def test_profit_sale_not_recorded_as_loss():
    df = _df([
        ("2020-06-01", "A", "매수", 100, 10000),
        ("2020-06-03", "A", "매도", 100, 11000),   # 익절
        ("2020-06-05", "A", "매수", 50, 9500),
    ])
    out = replay_positions(df)
    assert pd.isna(out.loc[2, "최근손실매도일"])


def test_same_day_order_preserved():
    """당일 매수→매도 — 매도 행에서 최근매수일이 같은 날로 보인다 (왕복 판정)."""
    df = _df([
        ("2020-06-01", "A", "매수", 100, 10000),
        ("2020-06-01", "A", "매도", 100, 10100),
    ])
    out = replay_positions(df)
    assert out.loc[1, "최근매수일"] == pd.Timestamp("2020-06-01")
    assert out.loc[1, "실현손익"] == pytest.approx(100 * 100)


def test_unknown_basis_sale_is_flagged_not_guessed():
    """이력 밖 잔고 매도 — 손익을 지어내지 않고 원가미상 처리, 이후는 정상."""
    df = _df([
        ("2020-06-01", "A", "매도", 100, 9000),    # 업로드 전 보유분 매도
        ("2020-06-03", "A", "매수", 50, 8000),
        ("2020-06-05", "A", "매도", 50, 8500),
    ])
    out = replay_positions(df)
    assert out.loc[0, "원가미상"] == True  # noqa: E712
    assert pd.isna(out.loc[0, "실현손익"])
    assert pd.isna(out.loc[0, "최근손실매도일"])  # 미상 매도는 손실로 안 침
    assert out.loc[2, "실현손익"] == (8500 - 8000) * 50  # 이후 재생은 정상


def test_partial_oversell_resets_holding():
    """보유량 초과 매도(혼합 잔고)도 원가미상 — 보유 리셋 후 정상 재개."""
    df = _df([
        ("2020-06-01", "A", "매수", 50, 10000),
        ("2020-06-03", "A", "매도", 80, 11000),    # 50은 알지만 30은 미상 — 전체 미상
        ("2020-06-05", "A", "매수", 10, 9000),
    ])
    out = replay_positions(df)
    assert out.loc[1, "원가미상"] == True  # noqa: E712
    assert pd.isna(out.loc[1, "실현손익"])
    assert out.loc[2, "보유수량_직전"] == 0  # 리셋됨


def test_unsorted_input_aligned_to_original_rows():
    """입력이 날짜 역순이어도 재생은 시간순, 결과는 원래 행 위치에 정렬."""
    df = _df([
        ("2020-06-05", "A", "매도", 100, 12000),   # 행 0 (시간상 마지막)
        ("2020-06-01", "A", "매수", 100, 10000),   # 행 1 (시간상 처음)
    ])
    out = replay_positions(df)
    assert out.loc[0, "보유수량_직전"] == 100      # 매도 시점엔 이미 보유
    assert out.loc[0, "실현손익"] == (12000 - 10000) * 100
    assert out.loc[1, "보유수량_직전"] == 0        # 첫 매수 직전엔 없음


def test_multi_stock_independent():
    df = _df([
        ("2020-06-01", "A", "매수", 100, 10000),
        ("2020-06-01", "B", "매수", 10, 50000),
        ("2020-06-03", "A", "매도", 100, 9000),
    ])
    out = replay_positions(df)
    assert out.loc[1, "평균단가_직전"] != out.loc[2, "평균단가_직전"]
    assert out.loc[2, "평균단가_직전"] == 10000
    assert pd.isna(out.loc[1, "실현손익"])         # B 매수엔 손익 없음


def test_empty_input():
    out = replay_positions(_df([]))
    assert len(out) == 0
