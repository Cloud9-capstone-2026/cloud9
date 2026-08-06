"""
detect.py 순수 함수 스모크 — DB·네트워크 없이 표준화 → 신규 추출 → 앙상블
배관이 계약대로 동작함을 보증한다 (비동기 전환으로 이 배관이 worker로 이사).
run_pipeline_from_db 자체(DB 세션 필요)는 test_analysis_jobs가 job 단위로 커버.
"""

import numpy as np
import pandas as pd
import pytest

from models.rule_based import run_rule_based
from models.zscore import run_zscore
from pipeline.detect import (
    FINAL_THRESHOLD,
    LSTM_W3,
    RULE_W,
    RULE_W3,
    STAT_W,
    STAT_W3,
    _build_ensemble,
    _extract_new_trades,
)


def test_extract_first_upload_returns_all(standard_trades):
    """baseline 비어있음(첫 업로드) → 전체가 신규, 위치는 0..n-1."""
    empty = pd.DataFrame(columns=standard_trades.columns)
    new, pos = _extract_new_trades(empty, standard_trades)
    assert len(new) == len(standard_trades)
    assert list(pos) == list(range(len(standard_trades)))


def test_extract_dedup_returns_only_new(standard_trades):
    """이전 업로드에 있던 5건 제외 → 신규 3건, new_df 내 위치 보존."""
    baseline = standard_trades.head(5)
    new, pos = _extract_new_trades(baseline, standard_trades)
    assert len(new) == 3
    assert list(pos) == [5, 6, 7]
    pd.testing.assert_frame_equal(
        new.reset_index(drop=True),
        standard_trades.tail(3).reset_index(drop=True),
    )


def test_rule_and_stat_shapes(standard_trades):
    """1·2계층 실행 스모크 — 행 수·키 계약 (픽스처 8건, 규칙 위반 없음)."""
    rule = run_rule_based(standard_trades)
    stat = run_zscore(standard_trades, standard_trades.head(5))
    assert len(rule["trade_results"]) == len(standard_trades)
    assert len(stat["trade_results"]) == len(standard_trades)
    for r in rule["trade_results"]:
        assert set(r) >= {"날짜", "종목명", "rule_score", "triggered_rules"}
        assert 0.0 <= r["rule_score"] <= 1.0
    for s in stat["trade_results"]:
        assert set(s) >= {"날짜", "종목명", "stat_score", "mahalanobis"}
        assert 0.0 <= s["stat_score"] <= 1.0


@pytest.fixture()
def layer_results(standard_trades):
    rule = run_rule_based(standard_trades)
    stat = run_zscore(standard_trades, standard_trades.head(5))
    return rule, stat


def test_ensemble_two_layer_fallback(layer_results):
    """3계층 부재(None) → 2계층 가중(0.3/0.7), lstm 필드는 None."""
    rule, stat = layer_results
    ens = _build_ensemble(rule, stat, None)
    assert len(ens) == len(rule["trade_results"])
    for e, r, s in zip(ens, rule["trade_results"], stat["trade_results"]):
        want = RULE_W * r["rule_score"] + STAT_W * s["stat_score"]
        assert e["final_score"] == pytest.approx(want, abs=1e-4)
        assert e["lstm_score"] is None
        assert e["lstm_top_bias"] is None
        assert e["is_anomaly"] == (e["final_score"] > FINAL_THRESHOLD)


def test_ensemble_three_layer_and_row_fallback(layer_results):
    """3계층 점수 있는 행은 0.3/0.3/0.4 가중, None인 행(시퀀스 절단 밖)만
    2계층 폴백 — 행 단위 혼합이 계약."""
    rule, stat = layer_results
    n = len(rule["trade_results"])
    bias = {"disposition_strength": 0.9, "overconfidence": 0.1,
            "lottery_preference": 0.1, "herd_sensitivity": 0.1}
    lstm_rows = [{"score": 0.9, "top_bias": "disposition_strength",
                  "bias_scores": bias} for _ in range(n)]
    lstm_rows[0] = None  # 절단 밖 거래 시뮬레이션

    ens = _build_ensemble(rule, stat, lstm_rows)
    r0, s0 = rule["trade_results"][0], stat["trade_results"][0]
    assert ens[0]["final_score"] == pytest.approx(
        RULE_W * r0["rule_score"] + STAT_W * s0["stat_score"], abs=1e-4)
    assert ens[0]["lstm_score"] is None

    for e, r, s in zip(ens[1:], rule["trade_results"][1:], stat["trade_results"][1:]):
        want = (RULE_W3 * r["rule_score"] + STAT_W3 * s["stat_score"]
                + LSTM_W3 * 0.9)
        assert e["final_score"] == pytest.approx(want, abs=1e-4)
        assert e["lstm_score"] == 0.9
        assert e["lstm_top_bias"] == "disposition_strength"
        assert e["lstm_bias_scores"] == bias
