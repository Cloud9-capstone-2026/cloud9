"""
분포 점검 v2 검증 — 가짜 기준 분포 주입, 파일·네트워크·모델 비의존.

계약: check_distribution(account_metrics) →
  {"status": ok|out_of_range|unavailable, "checked": [...], "out_of_range": {...},
   "deep_excluded": bool}
[p1, p99] 밖 지표만 이탈로 기록, None 지표는 점검 제외, 재료 없으면 unavailable.
deep_excluded = 이탈 지표 수 >= CANARY_DIST_TRIGGER(기본 2) — 항상 존재.
"""

import json

import pytest

from pipeline import monitor
from pipeline.monitor import check_distribution

REF = {
    "metrics": {
        "turnover_annual": {"quantiles": [3.0, 6.0, 15.0, 38.0, 91.0, 219.0, 700.0]},
        "holding_days_mean": {"quantiles": [1.0, 2.0, 4.0, 8.0, 15.0, 40.0, 65.0]},
        "n_trades": {"quantiles": [1, 3, 20, 50, 90, 160, 210]},
    }
}

INSIDE = {"turnover_annual": 40.0, "holding_days_mean": 8.0, "n_trades": 60}


@pytest.fixture()
def fake_ref(tmp_path, monkeypatch):
    (tmp_path / "distribution_ref.json").write_text(
        json.dumps(REF), encoding="utf-8")
    monkeypatch.setattr(monitor, "_ART_DIR", tmp_path)
    return tmp_path


def test_all_inside_is_ok(fake_ref):
    out = check_distribution(INSIDE)
    assert out["status"] == "ok"
    assert out["out_of_range"] == {}
    assert sorted(out["checked"]) == sorted(REF["metrics"])


@pytest.mark.parametrize("key,value", [
    ("turnover_annual", 2000.0),   # p99(700) 초과 — 초고회전 계좌
    ("turnover_annual", 1.0),      # p1(3) 미만
    ("holding_days_mean", 400.0),  # 초장기 보유
])
def test_out_of_range_flags_metric(fake_ref, key, value):
    out = check_distribution({**INSIDE, key: value})
    assert out["status"] == "out_of_range"
    assert key in out["out_of_range"]
    detail = out["out_of_range"][key]
    assert detail["value"] == value
    assert detail["ref_p1"] == REF["metrics"][key]["quantiles"][0]
    assert detail["ref_p99"] == REF["metrics"][key]["quantiles"][-1]
    # 나머지 지표는 이탈 아님
    assert set(out["out_of_range"]) == {key}


def test_boundary_values_are_inside(fake_ref):
    """경계값(p1·p99 정확히)은 범위 안 — 폐구간 판정."""
    out = check_distribution({**INSIDE, "turnover_annual": 700.0})
    assert out["status"] == "ok"
    out = check_distribution({**INSIDE, "turnover_annual": 3.0})
    assert out["status"] == "ok"


def test_none_metric_skipped_not_flagged(fake_ref):
    """값이 None인 지표(예: 매도만 있는 계좌의 보유기간)는 점검 제외."""
    out = check_distribution({**INSIDE, "holding_days_mean": None})
    assert out["status"] == "ok"
    assert "holding_days_mean" not in out["checked"]


UNAVAILABLE = {"status": "unavailable", "deep_excluded": False}


def test_no_metrics_is_unavailable(fake_ref):
    assert check_distribution(None) == UNAVAILABLE
    assert check_distribution({}) == UNAVAILABLE


def test_missing_ref_is_unavailable(tmp_path, monkeypatch):
    monkeypatch.setattr(monitor, "_ART_DIR", tmp_path)  # 빈 디렉터리
    assert check_distribution(INSIDE) == UNAVAILABLE


def test_corrupted_ref_is_unavailable(tmp_path, monkeypatch):
    (tmp_path / "distribution_ref.json").write_text("{부서짐", encoding="utf-8")
    monkeypatch.setattr(monitor, "_ART_DIR", tmp_path)
    assert check_distribution(INSIDE) == UNAVAILABLE


# ─ v2: 발동(deep_excluded) 판정 ─

def test_one_metric_out_does_not_exclude(fake_ref):
    """이탈 1개는 기록만 — 발동 아님 (기본 기준 2개)."""
    out = check_distribution({**INSIDE, "turnover_annual": 2000.0})
    assert out["status"] == "out_of_range"
    assert out["deep_excluded"] is False


def test_two_metrics_out_excludes_deep(fake_ref):
    """이탈 2개부터 발동 — 3계층 판정 제외 신호."""
    out = check_distribution({**INSIDE, "turnover_annual": 2000.0,
                              "holding_days_mean": 400.0})
    assert out["status"] == "out_of_range"
    assert out["deep_excluded"] is True


def test_all_inside_not_excluded(fake_ref):
    assert check_distribution(INSIDE)["deep_excluded"] is False


def test_trigger_threshold_env_override(fake_ref, monkeypatch):
    """CANARY_DIST_TRIGGER로 발동 기준 조정 — 재시작만으로 튜닝 가능해야 한다."""
    metrics = {**INSIDE, "turnover_annual": 2000.0}  # 이탈 1개
    monkeypatch.setenv("CANARY_DIST_TRIGGER", "1")
    assert check_distribution(metrics)["deep_excluded"] is True
    monkeypatch.setenv("CANARY_DIST_TRIGGER", "3")
    assert check_distribution({**metrics, "holding_days_mean": 400.0}
                              )["deep_excluded"] is False
