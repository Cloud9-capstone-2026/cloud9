"""
사용자 정의 규칙 템플릿(rule_based/templates.py) 검증 — 네트워크·모델 0.

템플릿별 위반/무위반 시나리오와 경계값, 그리고 "미설정 사용자의 기본 조합 =
기존 1계층 v1"이라는 회귀 계약을 고정한다. (run_rule_based 배선은 다음 단계 —
여기서는 부품 단위 검증.)
"""

import pandas as pd
import pytest

from models.rule_based.positions import replay_positions
from models.rule_based.templates import DEFAULT_RULESET, TEMPLATES


def _df(rows):
    """rows: (날짜, 종목명, 구분, 수량, 단가)"""
    return pd.DataFrame(
        [{"날짜": pd.Timestamp(d), "종목명": s, "매매구분": k,
          "체결수량": q, "체결단가": p} for d, s, k, q, p in rows]
    )


def _run(template_id, df, param=None):
    t = TEMPLATES[template_id]
    pos = replay_positions(df) if t.needs_positions else None
    return t.fn(df, pos, param if param is not None else t.default_param)


# ─ 일중 반복매매 (N회) ─

def test_daily_frequency_parameterized():
    df = _df([
        ("2020-06-01", "A", "매수", 10, 100),
        ("2020-06-01", "A", "매도", 10, 101),
        ("2020-06-02", "A", "매수", 10, 100),
    ])
    assert not _run("daily_frequency", df).any()          # 기본 N=4 — 2회는 통과
    out = _run("daily_frequency", df, param=2)            # N=2로 낮추면
    assert list(out) == [True, True, False]               # 그날 2건이 걸림


# ─ 최소 보유기간 (X일) ─

def test_min_holding_x1_catches_same_day_sell():
    """X=1 = "1일 미만 보유 매도" = 당일 매도. 위반은 매도 행에만 붙는다."""
    df = _df([
        ("2020-06-01", "A", "매수", 10, 100),
        ("2020-06-01", "A", "매도", 10, 101),   # 당일 매도 — 위반
        ("2020-06-02", "B", "매수", 10, 100),
        ("2020-06-03", "B", "매도", 10, 101),   # 1일 보유 — X=1 통과
    ])
    assert list(_run("min_holding", df, param=1)) == [False, True, False, False]


def test_min_holding_boundary():
    """정확히 X일 보유는 통과 (위반 = 미만)."""
    df = _df([
        ("2020-06-01", "A", "매수", 10, 100),
        ("2020-06-03", "A", "매도", 5, 101),    # 2일 보유 — X=3 위반
        ("2020-06-04", "A", "매도", 5, 101),    # 3일 보유 — X=3 통과
    ])
    assert list(_run("min_holding", df, param=3)) == [False, True, False]


def test_min_holding_unknown_buy_date_skipped():
    df = _df([("2020-06-01", "A", "매도", 10, 100)])  # 업로드 이력 밖 보유분
    assert not _run("min_holding", df, param=30).any()


# ─ 손실 후 재진입 (D일) ─

def test_reentry_after_loss_boundary():
    """손실 매도 후 D일 이내(경계 포함) 재매수만 위반."""
    df = _df([
        ("2020-06-01", "A", "매수", 10, 1000),
        ("2020-06-02", "A", "매도", 10, 900),    # 손실 확정
        ("2020-06-07", "A", "매수", 5, 950),     # 5일째 — D=5 위반 (경계)
        ("2020-06-01", "B", "매수", 10, 1000),
        ("2020-06-02", "B", "매도", 10, 900),    # 손실 확정
        ("2020-06-09", "B", "매수", 5, 950),     # 7일째 — D=5 통과
    ])
    out = _run("reentry_after_loss", df, param=5)
    assert list(out) == [False, False, True, False, False, False]


def test_reentry_ignores_profit_sale():
    df = _df([
        ("2020-06-01", "A", "매수", 10, 1000),
        ("2020-06-02", "A", "매도", 10, 1100),   # 익절
        ("2020-06-03", "A", "매수", 5, 1050),    # 재매수 — 손실 아님, 통과
    ])
    assert not _run("reentry_after_loss", df, param=5).any()


def test_reentry_ignores_unknown_basis_sale():
    df = _df([
        ("2020-06-01", "A", "매도", 10, 900),    # 원가미상 — 손실로 안 침
        ("2020-06-02", "A", "매수", 5, 950),
    ])
    assert not _run("reentry_after_loss", df, param=5).any()


# ─ 물타기 반복 (M회) ─

def test_averaging_down_counts_to_threshold():
    df = _df([
        ("2020-06-01", "A", "매수", 10, 1000),
        ("2020-06-02", "A", "매수", 10, 900),    # 물타기 1회 — M=2 미달
        ("2020-06-03", "A", "매수", 10, 800),    # 물타기 2회 — 위반 시작
    ])
    assert list(_run("averaging_down", df, param=2)) == [False, False, True]


def test_averaging_down_resets_after_liquidation():
    df = _df([
        ("2020-06-01", "A", "매수", 10, 1000),
        ("2020-06-02", "A", "매수", 10, 900),    # 물타기 1회
        ("2020-06-03", "A", "매도", 20, 950),    # 전량 청산 — 리셋
        ("2020-06-04", "A", "매수", 10, 1000),   # 새 포지션
        ("2020-06-05", "A", "매수", 10, 900),    # 새 포지션의 물타기 1회 — M=2 미달
    ])
    assert not _run("averaging_down", df, param=2).any()


def test_averaging_down_ignores_higher_price_buys():
    df = _df([
        ("2020-06-01", "A", "매수", 10, 1000),
        ("2020-06-02", "A", "매수", 10, 1100),   # 불타기 — 카운트 아님
        ("2020-06-03", "A", "매수", 10, 1200),
    ])
    assert not _run("averaging_down", df, param=1).any()


# ─ 금액 한도 2종 ─

def test_single_buy_cap_flags_only_oversized_buys():
    df = _df([
        ("2020-06-01", "A", "매수", 100, 10000),   # 100만원 — 통과
        ("2020-06-02", "A", "매수", 100, 60000),   # 600만원 — 위반
        ("2020-06-03", "A", "매도", 200, 60000),   # 매도는 대상 아님
    ])
    out = _run("single_buy_cap", df, param=5_000_000)
    assert list(out) == [False, True, False]


def test_daily_total_cap_flags_whole_day():
    df = _df([
        ("2020-06-01", "A", "매수", 100, 30000),   # 300만
        ("2020-06-01", "B", "매도", 100, 30000),   # 300만 — 그날 합 600만
        ("2020-06-02", "A", "매수", 10, 30000),    # 30만 — 통과
    ])
    out = _run("daily_total_cap", df, param=5_000_000)
    assert list(out) == [True, True, False]


def test_daily_total_cap_uses_총거래금액_when_present():
    df = _df([("2020-06-01", "A", "매수", 1, 1)])
    df["총거래금액"] = [9_999_999]
    assert _run("daily_total_cap", df, param=5_000_000).all()


# ─ run_rule_based: 이력 문맥 + 사용자 조합 실행 ─

def test_run_rule_based_cross_upload_context():
    """손실 매도는 과거 업로드, 재매수는 신규 — 이력 문맥으로 잡히고
    반환은 신규 거래 수만큼만."""
    from models.rule_based import run_rule_based

    full = _df([
        ("2020-06-01", "A", "매수", 10, 1000),   # ← 과거 업로드
        ("2020-06-02", "A", "매도", 10, 900),    # ← 과거 업로드 (손실)
        ("2020-06-04", "A", "매수", 5, 950),     # ← 신규 (재진입 2일째)
    ])
    out = run_rule_based(full, new_positions=[2],
                         ruleset=[("reentry_after_loss", 5)])
    assert len(out["trade_results"]) == 1              # 신규만 반환
    assert out["trade_results"][0]["triggered_rules"] == ["손실후_재진입"]
    assert out["is_anomaly"] is True


def test_run_rule_based_combined_score():
    """2중 위반 시 결합식 1−(1−0.7)² = 0.91 유지."""
    from models.rule_based import run_rule_based

    full = _df([
        ("2020-06-01", "A", "매수", 10, 1000),
        ("2020-06-01", "A", "매도", 10, 990),    # 당일 왕복 + 최소보유 위반
    ])
    out = run_rule_based(full, ruleset=[("same_day_roundtrip", None),
                                        ("min_holding", 3)])
    sell = out["trade_results"][1]
    assert sorted(sell["triggered_rules"]) == ["당일_왕복매매", "최소_보유기간"]
    assert sell["rule_score"] == 0.91


def test_run_rule_based_empty_ruleset_no_flags():
    """전부 꺼둔 사용자 — 위반 없음, 점수 전부 0."""
    from models.rule_based import run_rule_based

    full = _df([
        ("2020-06-01", "A", "매수", 10, 1000),
        ("2020-06-01", "A", "매도", 10, 990),
    ])
    out = run_rule_based(full, ruleset=[])
    assert out["is_anomaly"] is False
    assert all(t["rule_score"] == 0.0 for t in out["trade_results"])


# ─ 레지스트리 계약 ─

def test_default_ruleset_is_v1():
    """미설정 사용자의 기본 조합 = 기존 1계층 v1 (일중 4회 + 당일 왕복)."""
    assert DEFAULT_RULESET == [("daily_frequency", 4), ("same_day_roundtrip", None)]


def test_all_templates_return_aligned_bool_series():
    df = _df([
        ("2020-06-01", "A", "매수", 10, 1000),
        ("2020-06-01", "A", "매도", 10, 1010),
    ])
    for tid, t in TEMPLATES.items():
        param = t.default_param if t.default_param is not None else 1
        out = _run(tid, df, param=param)
        assert isinstance(out, pd.Series) and out.dtype == bool, tid
        assert list(out.index) == list(df.index), tid
