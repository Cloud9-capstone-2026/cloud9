"""
투자자 성향 파라미터 + 그룹(인구통계) 배정.

5-3 그룹 인프라: agent 생성 시 KCMI 표 Ⅲ-1 비율로 (성별, 연령, 자산, 신규여부)를
배정하고, 파라미터는 `clip(gauss(grand_mean, std) × Π multiplier)` 로 결합한다.
multiplier가 전부 1.0인 동안(5-5 전) 이 식은 기존 `clip(gauss(...))`와 수학적으로
동일 — baseline exact 일치가 회귀검증 기준.

그룹 태그는 agent 객체에만 보관하고 CSV(편향라벨 포함)에는 넣지 않는다 — 실제 증권사
CSV에 없는 필드이고, 이상탐지 모델이 그룹 태그로 컨닝(leakage)할 위험 방지.
"""

import random
from dataclasses import dataclass

from . import config
from .config import BehaviorParamRanges


@dataclass(frozen=True)
class InvestorGroup:
    """KCMI 표 Ⅲ-1의 4축 인구통계 태그."""

    gender: str  # "여성" | "남성"
    age: str     # "20대이하" | "30대" | "40대" | "50대" | "60대이상"
    asset: str   # "1천만원이하" | "3천만원이하" | "1억원이하" | "1억원초과"
    is_new: bool

    @property
    def new_key(self) -> str:
        return "신규" if self.is_new else "기존"


def sample_investor_group(rng: random.Random) -> InvestorGroup:
    """신규여부 먼저 → 나머지 3축은 신규 조건부 분포로 배정 (표 Ⅲ-1 교차분포).

    반드시 넘겨받은 rng(그룹 전용 스트림)로만 뽑는다 — 파라미터 스트림(py_rng)과
    분리해 그룹 로직 변경이 파라미터 draw를 밀지 않게 한다(model.py 참조).
    """
    is_new = rng.random() < config.P_NEW
    key = "신규" if is_new else "기존"

    def pick(dist_by_new: dict) -> str:
        dist = dist_by_new[key]
        cats = list(dist)
        return rng.choices(cats, weights=[dist[c] for c in cats], k=1)[0]

    return InvestorGroup(
        gender=pick(config.GENDER_DIST_BY_NEW),
        age=pick(config.AGE_DIST_BY_NEW),
        asset=pick(config.ASSET_DIST_BY_NEW),
        is_new=is_new,
    )


@dataclass
class BehaviorParams:
    # loss_aversion은 5-6에서 제거 — 행동 로직 어디에도 쓰이지 않는 죽은 파라미터였고,
    # Barberis-Xiong 실현효용으로 매도 로직에 연결하는 안은 disposition_strength가 이미
    # 잡는 이익/손실 매도 비대칭과 이중계상되어 기각(B-X는 6단계 이후 재설계 시 검토).
    disposition_strength: float = 1.0
    overconfidence: float = 0.1
    lottery_preference: float = 0.0
    herd_sensitivity: float = 0.0
    base_buy_prob: float = 0.05
    base_sell_prob: float = 0.05

    def as_label(self) -> dict:
        return {
            "disposition_strength": self.disposition_strength,
            "overconfidence": self.overconfidence,
            "lottery_preference": self.lottery_preference,
            "herd_sensitivity": self.herd_sensitivity,
        }


def _group_multiplier(param: str, group: InvestorGroup, multipliers: dict) -> float:
    """(파라미터 × 축 × 카테고리) 테이블에서 이 그룹의 배율 곱을 조회.
    테이블에 없는 (파라미터, 축) 조합은 1.0 (영향 없음)."""
    axes = multipliers.get(param, {})
    cats = {
        "gender": group.gender,
        "age": group.age,
        "asset": group.asset,
        "new": group.new_key,
    }
    m = 1.0
    for axis, cat in cats.items():
        m *= axes.get(axis, {}).get(cat, 1.0)
    # 극단 조합 폭주 방지 상한 (config 주석 참조). 하한은 per-param clip이 담당.
    return min(m, config.MULTIPLIER_CAP)


def sample_investor_params(
    rng: random.Random,
    ranges: BehaviorParamRanges,
    group: InvestorGroup,
    multipliers: dict,
) -> BehaviorParams:
    """최종값 = clip( gauss(grand_mean, std) × Π multiplier , lo, hi ).

    - 기존 std를 그룹 내 노이즈로 그대로 재사용(새 자유변수 없음).
    - clip은 곱셈 결과(최종값)를 감싼다 — 배율≠1이어도 backstop이 최종값을 bound.
    - loss_aversion은 5-6에서 제거됨(BehaviorParams 주석 참고). 이때 첫 gauss draw가
      사라져 py_rng 스트림이 이동 — 5-3의 exact 회귀검증 시대는 종료, 이후 검증은
      다시드 범위 검증(kcmi_metrics)으로 수행.
    """
    def clip(v, lo, hi=None):
        v = max(v, lo)
        return min(v, hi) if hi is not None else v

    def mult(param: str) -> float:
        return _group_multiplier(param, group, multipliers)

    return BehaviorParams(
        disposition_strength=clip(
            rng.gauss(*ranges.disposition_strength) * mult("disposition_strength"), 0.5
        ),
        overconfidence=clip(
            rng.gauss(*ranges.overconfidence) * mult("overconfidence"), 0.0
        ),
        lottery_preference=clip(
            rng.gauss(*ranges.lottery_preference) * mult("lottery_preference"), 0.0, 1.0
        ),
        herd_sensitivity=clip(
            rng.gauss(*ranges.herd_sensitivity) * mult("herd_sensitivity"), 0.0, 1.0
        ),
        base_buy_prob=clip(
            rng.gauss(*ranges.base_buy_prob) * mult("base_buy_prob"), 0.01
        ),
        base_sell_prob=clip(
            rng.gauss(*ranges.base_sell_prob) * mult("base_sell_prob"), 0.01
        ),
    )
