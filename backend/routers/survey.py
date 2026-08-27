"""
POST /survey/submit — 투자 성향 자가진단(20문항) 제출.

스펙 출처: 나림 팀 Notion "투자 성향 자가진단 검사" 문서(2026-08-26 확인).
문항 id는 축_순번 형식의 문자열이다: ds_1~ds_5(disposition_strength),
oc_1~oc_5(overconfidence), lp_1~lp_5(lottery_preference),
hs_1~hs_5(herd_sensitivity). reverse 채점 대상은 ds_5, oc_5, hs_5 3개뿐
(lottery_preference 축엔 reverse 문항 없음) — Notion 문서에 Y로 명시돼 있음.

[중요 — 원 스펙 대비 변경점] Notion 문서의 요청 예시는 바디에 user_id를
직접 포함하지만(`{"user_id": 123, "answers": [...]}`), 이 프로젝트는 그
문서 작성 이후 JWT 인증이 전체 API에 도입됐다(trades/analysis/jobs/auth
라우터와 동일 패턴). 그래서 user_id는 요청 바디로 받지 않고
Depends(get_current_user)로 토큰에서 추출한다 — 클라이언트가 남의
user_id를 넣어 결과를 위조하는 경로를 차단하기 위함이며, 이미 다른
라우터에 적용된 보안 원칙과 일관성을 맞춘 것. 프론트 연동 시 요청 바디에
user_id를 넣지 않아도 된다는 점을 도경에게 공유 필요.

채점 로직(Notion 문서 2절 그대로):
1. reverse 문항은 (6 - 응답값)으로 변환.
2. 축별 raw = 5문항 채점값 합 (5~25).
3. normalized = (raw-5)/(25-5)*100 (0~100).
4. normalized >= 50 → high, 미만 → low (고정 기준선).
5. type_code = 4축을 disposition_strength→overconfidence→lottery_preference
   →herd_sensitivity 순서로 H/L 이어붙인 4자리.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from auth import get_current_user
from database import get_db
from orm import SurveyResult, User

router = APIRouter()

QUESTIONS_PER_AXIS = 5

# 축 prefix ↔ 축 이름. AXIS_ORDER는 type_code 조합 순서와 동일해야 함(Notion 문서 2-5).
PREFIX_TO_AXIS = {
    "ds": "disposition_strength",
    "oc": "overconfidence",
    "lp": "lottery_preference",
    "hs": "herd_sensitivity",
}
AXIS_ORDER = ("disposition_strength", "overconfidence", "lottery_preference", "herd_sensitivity")
AXIS_TO_PREFIX = {axis: prefix for prefix, axis in PREFIX_TO_AXIS.items()}

ALL_QUESTION_IDS = {f"{prefix}_{n}" for prefix in PREFIX_TO_AXIS for n in range(1, QUESTIONS_PER_AXIS + 1)}
TOTAL_QUESTIONS = len(ALL_QUESTION_IDS)  # 20

# reverse 채점 대상 (Notion 문서에서 reverse=Y로 명시된 3개뿐 — lottery_preference엔 없음)
REVERSE_QUESTION_IDS = {"ds_5", "oc_5", "hs_5"}

_QUESTION_ID_PATTERN = r"^(ds|oc|lp|hs)_[1-5]$"


class SurveyAnswer(BaseModel):
    question_id: str = Field(pattern=_QUESTION_ID_PATTERN)
    value: int = Field(ge=1, le=5)


class SurveySubmitRequest(BaseModel):
    answers: list[SurveyAnswer]

    @field_validator("answers")
    @classmethod
    def _validate_answers(cls, answers: list[SurveyAnswer]) -> list[SurveyAnswer]:
        if len(answers) != TOTAL_QUESTIONS:
            raise ValueError(f"answers는 정확히 {TOTAL_QUESTIONS}개여야 합니다")
        ids = {a.question_id for a in answers}
        if len(ids) != TOTAL_QUESTIONS or ids != ALL_QUESTION_IDS:
            raise ValueError(f"question_id는 {sorted(ALL_QUESTION_IDS)} 각각 정확히 1번씩 있어야 합니다")
        return answers


def _score_axis(answers_by_id: dict[str, int], prefix: str) -> tuple[int, float, str]:
    raw = 0
    for n in range(1, QUESTIONS_PER_AXIS + 1):
        qid = f"{prefix}_{n}"
        value = answers_by_id[qid]
        raw += (6 - value) if qid in REVERSE_QUESTION_IDS else value

    normalized = (raw - QUESTIONS_PER_AXIS) / (QUESTIONS_PER_AXIS * 4) * 100
    level = "high" if normalized >= 50 else "low"
    return raw, normalized, level


@router.post("/submit")
def submit_survey(
    payload: SurveySubmitRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    answers_by_id = {a.question_id: a.value for a in payload.answers}

    axis_scores: dict[str, tuple[int, float, str]] = {
        axis: _score_axis(answers_by_id, AXIS_TO_PREFIX[axis]) for axis in AXIS_ORDER
    }

    type_code = "".join(
        "H" if axis_scores[axis][2] == "high" else "L" for axis in AXIS_ORDER
    )

    result = SurveyResult(
        user_id=current_user.id,
        disposition_strength_raw=axis_scores["disposition_strength"][0],
        disposition_strength_normalized=axis_scores["disposition_strength"][1],
        disposition_strength_level=axis_scores["disposition_strength"][2],
        overconfidence_raw=axis_scores["overconfidence"][0],
        overconfidence_normalized=axis_scores["overconfidence"][1],
        overconfidence_level=axis_scores["overconfidence"][2],
        lottery_preference_raw=axis_scores["lottery_preference"][0],
        lottery_preference_normalized=axis_scores["lottery_preference"][1],
        lottery_preference_level=axis_scores["lottery_preference"][2],
        herd_sensitivity_raw=axis_scores["herd_sensitivity"][0],
        herd_sensitivity_normalized=axis_scores["herd_sensitivity"][1],
        herd_sensitivity_level=axis_scores["herd_sensitivity"][2],
        type_code=type_code,
        answers=[{"question_id": a.question_id, "value": a.value} for a in payload.answers],
    )
    db.add(result)
    db.commit()
    db.refresh(result)

    return {
        "result_id": result.id,
        "scores": {
            axis: {
                "raw": axis_scores[axis][0],
                "normalized": axis_scores[axis][1],
                "level": axis_scores[axis][2],
            }
            for axis in AXIS_ORDER
        },
        "type_code": type_code,
        "created_at": result.created_at,
    }