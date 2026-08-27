"""
GET /rules       — 전체 규칙 템플릿 7종 + 본인 설정값 병합 조회.
PUT /rules/{id}  — 규칙 하나 설정(켜기/끄기, 파라미터). upsert.
DELETE /rules/{id} — 설정 삭제(기본값으로 되돌림).

1계층(Rule-based) "사용자가 스스로 정한 절제 규칙" 온보딩/설정 화면용 API.
models/rule_based/templates.py(TEMPLATES, 7종 정의)와 pipeline/user_rules.py
(load_ruleset — 분석 실행 시점에 이 값을 읽어감)를 그대로 활용한다.

수정은 소급 없이 다음 업로드 분석부터 적용된다(과거 분석 결과는 재계산하지
않음) — templates.py 상단 운영 규약 그대로.

[2026-08-27] user_rules 테이블(orm.UserRule)은 있었지만 이 값을 사용자가
실제로 넣을 API가 없어서 추가.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from auth import get_current_user
from database import get_db
from models.rule_based.templates import TEMPLATES
from orm import User, UserRule

router = APIRouter()


class RuleUpdateRequest(BaseModel):
    enabled: bool
    param: float | None = None


def _template_or_404(rule_id: str):
    template = TEMPLATES.get(rule_id)
    if template is None:
        raise HTTPException(status_code=404, detail=f"존재하지 않는 규칙입니다: {rule_id}")
    return template


def _serialize(template, user_rule: UserRule | None) -> dict:
    """템플릿 메타데이터 + 사용자 설정(없으면 템플릿 기본값)을 합친 응답 1건."""
    if user_rule is not None:
        enabled = user_rule.enabled
        param = user_rule.param
    else:
        enabled = template.default_on
        param = template.default_param

    return {
        "rule_id": template.id,
        "label": template.표시명,
        "param_unit": template.param_unit,
        "default_param": template.default_param,
        "default_on": template.default_on,
        "enabled": enabled,
        "param": param,
        "updated_at": user_rule.updated_at if user_rule is not None else None,
    }


@router.get("/")
def list_rules(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """7종 템플릿 전체를, 사용자가 설정해둔 값과 병합해서 반환.

    설정 안 한 규칙은 템플릿의 default_on/default_param을 그대로 보여준다 —
    즉 이 응답 전체가 "지금 이 사용자에게 실제로 적용 중인 규칙 조합"과 같다
    (pipeline/user_rules.load_ruleset의 폴백 로직과 동일한 우선순위)."""
    user_rules = {
        r.rule_id: r
        for r in db.query(UserRule).filter(UserRule.user_id == current_user.id).all()
    }
    return [_serialize(t, user_rules.get(t.id)) for t in TEMPLATES.values()]


@router.put("/{rule_id}")
def set_rule(
    rule_id: str,
    payload: RuleUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """규칙 하나를 켜거나/끄거나 파라미터를 설정. 이미 설정이 있으면 UPDATE,
    없으면 새로 생성(upsert) — templates.py 운영 규약의 "(user_id, rule_id)당
    1행" 원칙을 지킨다."""
    template = _template_or_404(rule_id)

    # 켜려는데 파라미터가 필요한 규칙(param_unit 있음)인데 값도 없고
    # 추천값도 없는 경우(금액 한도류) — 값 없이는 켤 수 없다(templates.py
    # 운영 규약: "추천값도 없는 규칙은 값 없이 켤 수 없어 스킵"과 동일 원칙을
    # 여기서는 저장 시점에 400으로 미리 막는다).
    if payload.enabled and template.param_unit is not None:
        effective_param = payload.param if payload.param is not None else template.default_param
        if effective_param is None:
            raise HTTPException(
                status_code=400,
                detail=f"{rule_id}는 파라미터 없이 켤 수 없습니다 (단위: {template.param_unit})",
            )

    existing = (
        db.query(UserRule)
        .filter(UserRule.user_id == current_user.id, UserRule.rule_id == rule_id)
        .first()
    )
    if existing is not None:
        existing.enabled = payload.enabled
        existing.param = payload.param
        db.commit()
        db.refresh(existing)
        row = existing
    else:
        row = UserRule(
            user_id=current_user.id, rule_id=rule_id,
            enabled=payload.enabled, param=payload.param,
        )
        db.add(row)
        db.commit()
        db.refresh(row)

    return _serialize(template, row)


@router.delete("/{rule_id}")
def reset_rule(
    rule_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """설정을 지워 템플릿 기본값으로 되돌린다. 설정한 적 없어도 200(멱등)."""
    template = _template_or_404(rule_id)

    existing = (
        db.query(UserRule)
        .filter(UserRule.user_id == current_user.id, UserRule.rule_id == rule_id)
        .first()
    )
    if existing is not None:
        db.delete(existing)
        db.commit()

    return _serialize(template, None)