"""
사용자별 판정 규칙 조합 로드 — 1계층 사용자 정의 규칙의 이음새.

user_rules 테이블(orm.UserRule)은 팀장 작업으로 추후 생성된다. 그 전에는,
그리고 등록이 없는 사용자에게는 기본 조합(templates.DEFAULT_RULESET —
기존 1계층 v1과 동일)을 돌려줘 판정이 항상 성립한다.

분석 실행 시점에 읽으므로 규칙 수정은 다음 업로드 분석부터 적용된다
(소급 없음 — 과거 분석 결과는 재계산하지 않는다).

기대 스키마(팀장 전달): user_rules(user_id FK, rule_id str, param float
nullable, enabled bool, updated_at, (user_id, rule_id) unique).
"""

import logging

from models.rule_based.templates import DEFAULT_RULESET, TEMPLATES

logger = logging.getLogger(__name__)


def _fetch_user_rules(db, user_id):
    """DB 조회부 — orm에 UserRule이 아직 없으면 None. 테스트 주입 지점."""
    try:
        from orm import UserRule
    except ImportError:
        return None
    try:
        return db.query(UserRule).filter(UserRule.user_id == user_id).all()
    except Exception as e:  # noqa: BLE001 — 테이블 미생성 등
        logger.warning("user_rules 조회 실패 — 기본 조합 사용: %r", e)
        return None


def load_ruleset(db, user_id) -> list:
    """[(template_id, param)] 반환.

    - 테이블 없음·조회 실패·등록 0행(미설정 사용자) → 기본 조합
    - 등록이 있으면 그대로 존중: enabled만 채택, 모르는 rule_id는 경고 후
      스킵, param이 비어 있으면 템플릿 추천값으로, 추천값도 없는 규칙(금액
      한도류)은 값 없이 켤 수 없어 스킵. 전부 꺼둔 사용자는 빈 조합(위반
      없음) — 명시적 선택으로 존중한다.
    """
    if db is None or user_id is None:
        return DEFAULT_RULESET
    rows = _fetch_user_rules(db, user_id)
    if rows is None or len(rows) == 0:
        return DEFAULT_RULESET

    ruleset = []
    for r in rows:
        if not getattr(r, "enabled", False):
            continue
        t = TEMPLATES.get(getattr(r, "rule_id", None))
        if t is None:
            logger.warning("알 수 없는 규칙 id 무시: %r", getattr(r, "rule_id", None))
            continue
        param = r.param if getattr(r, "param", None) is not None else t.default_param
        if param is None and t.param_unit is not None:
            logger.warning("규칙 %s: 파라미터 없음(추천값도 없음) — 건너뜀", t.id)
            continue
        ruleset.append((t.id, param))
    return ruleset
