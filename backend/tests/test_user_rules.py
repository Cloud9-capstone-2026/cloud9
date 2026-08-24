"""
사용자 규칙 로드 이음새(pipeline/user_rules.py) 검증 — DB 테이블 실존 불요.

user_rules 테이블은 팀장 작업으로 추후 생성되므로, 조회부(_fetch_user_rules)를
가짜 행으로 대체해 로드 정책만 고정한다: 미설정 → 기본 조합 / 등록 존중 /
무효 항목 방어.
"""

from types import SimpleNamespace

from pipeline import user_rules
from pipeline.user_rules import load_ruleset
from models.rule_based.templates import DEFAULT_RULESET


def _row(rule_id, param=None, enabled=True):
    return SimpleNamespace(rule_id=rule_id, param=param, enabled=enabled)


def test_no_table_or_no_rows_falls_back_to_default():
    """테이블 없음(현재 상태) 또는 등록 0행 → 기본 조합."""
    assert load_ruleset(object(), user_id=1) == DEFAULT_RULESET  # orm에 UserRule 없음
    assert load_ruleset(None, None) == DEFAULT_RULESET


def test_registered_rules_are_used(monkeypatch):
    monkeypatch.setattr(user_rules, "_fetch_user_rules", lambda db, uid: [
        _row("min_holding", 3),
        _row("daily_frequency", 2),
    ])
    assert load_ruleset(object(), 1) == [("min_holding", 3),
                                         ("daily_frequency", 2)]


def test_all_disabled_means_empty_ruleset(monkeypatch):
    """전부 꺼둔 사용자 — 명시적 선택이므로 기본 조합으로 되돌리지 않는다."""
    monkeypatch.setattr(user_rules, "_fetch_user_rules", lambda db, uid: [
        _row("daily_frequency", 4, enabled=False),
        _row("same_day_roundtrip", enabled=False),
    ])
    assert load_ruleset(object(), 1) == []


def test_unknown_rule_id_skipped(monkeypatch):
    monkeypatch.setattr(user_rules, "_fetch_user_rules", lambda db, uid: [
        _row("없는_규칙", 1),
        _row("same_day_roundtrip"),
    ])
    assert load_ruleset(object(), 1) == [("same_day_roundtrip", None)]


def test_missing_param_filled_with_recommended_or_skipped(monkeypatch):
    monkeypatch.setattr(user_rules, "_fetch_user_rules", lambda db, uid: [
        _row("min_holding"),       # param 없음 → 추천값 3
        _row("single_buy_cap"),    # param 없음 + 추천값 없음(금액) → 스킵
    ])
    assert load_ruleset(object(), 1) == [("min_holding", 3)]
