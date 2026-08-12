"""
detect.py 순수 함수 스모크 — DB·네트워크 없이 표준화 → 신규 추출 → 판정
배관이 계약대로 동작함을 보증한다 (비동기 전환으로 이 배관이 worker로 이사).
run_pipeline_from_db 자체(DB 세션 필요)는 test_analysis_jobs가 job 단위로 커버.

판정 계약: 계층별 독립 flag(rule=위반 존재, stat=마할라노비스>2.5,
deep=점수>=DEEP_THRESHOLD) → flag 개수 0/1/2+ = 정상/경고/이상.
"""

import pandas as pd
import pytest

from models.rule_based import run_rule_based
from models.zscore import run_zscore
from pipeline.detect import DEEP_THRESHOLD, _build_ensemble, _extract_new_trades


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


# ─ 판정(verdict) 계약 — 계층 결과를 손으로 구성해 조합별로 검증 ─

def _rule_row(triggered):
    return {"날짜": "2020-06-01", "종목명": "테스트A",
            "rule_score": 0.7 if triggered else 0.0,
            "triggered_rules": ["당일_왕복매매"] if triggered else []}


def _stat_row(anomalous, m=None):
    if m is None:
        m = 3.1 if anomalous else 1.2
    return {"날짜": "2020-06-01", "종목명": "테스트A", "z_vector": [0, 0, 0],
            "mahalanobis": m, "stat_score": 0.7 if anomalous else 0.3,
            "is_anomaly": anomalous}


def _deep_row(score):
    return {"score": score, "top_bias": "disposition_strength",
            "top_bias_명": "처분효과",
            "bias_scores": {"disposition_strength": score, "overconfidence": 0.1,
                            "lottery_preference": 0.1, "herd_sensitivity": 0.1}}


def _one(rule_on, stat_on, deep_score):
    """계층 판정 1거래 구성 → ensemble 1행 반환."""
    rule = {"is_anomaly": rule_on, "trade_results": [_rule_row(rule_on)]}
    stat = {"is_anomaly": stat_on, "trade_results": [_stat_row(stat_on)]}
    rows = None if deep_score is None else [_deep_row(deep_score)]
    return _build_ensemble(rule, stat, rows)[0]


HI = DEEP_THRESHOLD + 0.01   # deep flag 켜지는 점수
LO = DEEP_THRESHOLD - 0.01   # 안 켜지는 점수


@pytest.mark.parametrize("rule_on,stat_on,deep_score,want", [
    (False, False, LO, "정상"),   # flag 0개
    (True,  False, LO, "경고"),   # rule만
    (False, True,  LO, "경고"),   # stat만
    (False, False, HI, "경고"),   # deep만
    (True,  True,  LO, "이상"),   # 2개
    (True,  False, HI, "이상"),
    (True,  True,  HI, "이상"),   # 3개
])
def test_verdict_mapping(rule_on, stat_on, deep_score, want):
    e = _one(rule_on, stat_on, deep_score)
    assert e["verdict"] == want
    assert e["flags"] == {"rule": rule_on, "stat": stat_on,
                          "deep": deep_score >= DEEP_THRESHOLD}
    assert e["layers_available"] == 3


@pytest.mark.parametrize("rule_on,stat_on,want", [
    (False, False, "정상"),
    (True,  False, "경고"),
    (True,  True,  "이상"),   # 2계층만으로도 "이상" 가능
])
def test_verdict_without_deep_layer(rule_on, stat_on, want):
    """3계층 판정 불가(절단 밖·실패) — 두 계층만으로 같은 규칙 적용."""
    e = _one(rule_on, stat_on, None)
    assert e["verdict"] == want
    assert e["layers_available"] == 2
    assert "deep" not in e["flags"]
    assert e["deep"] is None


def test_deep_flag_theta_boundary():
    """θ 경계: 정확히 θ면 flag(이상 신호는 포함 판정), 그 아래면 미flag."""
    assert _one(False, False, DEEP_THRESHOLD)["flags"]["deep"] is True
    assert _one(False, False, DEEP_THRESHOLD - 1e-6)["flags"]["deep"] is False


def test_ensemble_row_contract():
    """프론트 계약 필드 — 키·타입·계층별 상세 재료."""
    e = _one(True, False, HI)
    assert set(e) == {"날짜", "종목명", "verdict", "flags", "layers_available",
                      "rule", "stat", "deep"}
    assert e["rule"]["triggered_rules"] == ["당일_왕복매매"]
    assert isinstance(e["stat"]["mahalanobis"], float)
    assert e["deep"]["top_bias_명"] == "처분효과"
    assert set(e["deep"]["bias_scores"]) == {
        "disposition_strength", "overconfidence",
        "lottery_preference", "herd_sensitivity"}


def test_deep_evidence_passthrough():
    """layer3가 계산한 evidence(판정 근거)는 deep에 그대로 실린다 — 없으면 None."""
    ev = {"disposition_strength": {
        "trade_share": 0.62, "context_share": 0.38,
        "features": [{"feature": "보유기간", "attribution": 0.42}]}}
    rule = {"is_anomaly": False, "trade_results": [_rule_row(False)]}
    stat = {"is_anomaly": False, "trade_results": [_stat_row(False)]}
    e = _build_ensemble(rule, stat, [{**_deep_row(HI), "evidence": ev}])[0]
    assert e["deep"]["evidence"] == ev
    assert _one(False, False, HI)["deep"]["evidence"] is None  # 계산 실패 행


def test_stat_flag_follows_zscore_definition(standard_trades):
    """stat flag는 zscore의 거래별 is_anomaly(마할라노비스>2.5)를 그대로 따른다."""
    rule = run_rule_based(standard_trades)
    stat = run_zscore(standard_trades, standard_trades.head(5))
    ens = _build_ensemble(rule, stat, None)
    for e, s in zip(ens, stat["trade_results"]):
        assert e["flags"]["stat"] == s["is_anomaly"]
        assert e["stat"]["mahalanobis"] == s["mahalanobis"]
