"""
사용자 정의 규칙 템플릿 레지스트리 (1계층).

1계층의 정체성: "사용자가 스스로 정한(동의한) 절제 규칙 위반" — 판정은 항상
거래 1건 + 파라미터로 설명이 끝나고, 시세 없이 계좌 데이터만 쓴다.

운영 규약(2026-08-07 회의 + 08-21 확정):
- 온보딩에서 설정, 이후 수정 가능. 수정은 소급 없이 다음 업로드부터
  (과거 분석 결과는 재계산하지 않는다 — 구조가 보장).
- 미설정 사용자는 기본 조합 = default_on 템플릿의 기본값 → 기존 1계층 v1
  (일중 반복매매 4회 + 당일 왕복매매)과 판정이 완전히 동일하다.
- 기본 꺼짐 템플릿의 추천값(default_param)은 온보딩 화면 표시용일 뿐 판정에
  자동 개입하지 않는다. 근거: 최소 보유기간 3일은 KCMI 22-02 재현 타깃의
  개인투자자 보유 중앙값(3일)에서, 재진입 5일·물타기 3회는 직접 문헌 수치가
  없어 보수적 관행값(온보딩에서 조정 전제). 금액 한도 2종은 개인차가 커서
  추천값 없음(켤 때 입력 필수).

판정 함수 공통 시그니처: fn(전체 이력 df, 포지션 재생 결과, 파라미터)
→ df와 같은 인덱스의 bool Series. 이력 전체로 계산하고 신규 거래만 잘라
쓰는 것은 호출부(run_rule_based) 책임.
"""

from dataclasses import dataclass
from typing import Callable, Optional

import pandas as pd

from models.rule_based.rules.amount_caps import (check_daily_total_cap,
                                                 check_single_buy_cap)
from models.rule_based.rules.averaging_down import check_averaging_down
from models.rule_based.rules.daily_frequency import check_daily_trade_frequency
from models.rule_based.rules.min_holding import check_min_holding
from models.rule_based.rules.reentry_after_loss import check_reentry_after_loss
from models.rule_based.rules.same_day_roundtrip import check_same_day_roundtrip

# 규칙 가중치 — v1 동결값 공통(제품 판단값). rule_score 표시용이며 판정(verdict)은
# flag 개수 기반이라 템플릿이 추가돼도 재캘리브레이션이 필요 없다.
DEFAULT_WEIGHT = 0.7


@dataclass(frozen=True)
class RuleTemplate:
    id: str                 # user_rules 저장·조회 키 (안정 식별자)
    표시명: str              # triggered_rules에 실리는 이름 (프론트 표시)
    param_unit: Optional[str]   # 파라미터 단위 ("회"·"일"·"원"), 없으면 None
    default_param: Optional[float]  # 기본값/온보딩 추천값 (없으면 입력 필수)
    default_on: bool        # 미설정 사용자에게 켜지는가
    needs_positions: bool   # 포지션 재생 결과가 필요한가
    fn: Callable[[pd.DataFrame, Optional[pd.DataFrame], Optional[float]],
                 pd.Series]


def _daily_freq(df, pos, n):
    return check_daily_trade_frequency(df, int(n))


def _roundtrip(df, pos, _param):
    return check_same_day_roundtrip(df)


def _min_holding(df, pos, x):
    return check_min_holding(df, pos, int(x))


def _reentry(df, pos, d):
    return check_reentry_after_loss(df, pos, int(d))


def _averaging(df, pos, m):
    return check_averaging_down(df, pos, int(m))


TEMPLATES = {t.id: t for t in [
    RuleTemplate("daily_frequency", "일중_반복매매", "회", 4, True, False,
                 _daily_freq),
    RuleTemplate("same_day_roundtrip", "당일_왕복매매", None, None, True, False,
                 _roundtrip),
    RuleTemplate("min_holding", "최소_보유기간", "일", 3, False, True,
                 _min_holding),
    RuleTemplate("reentry_after_loss", "손실후_재진입", "일", 5, False, True,
                 _reentry),
    RuleTemplate("averaging_down", "물타기_반복", "회", 3, False, True,
                 _averaging),
    RuleTemplate("single_buy_cap", "매수금액_상한", "원", None, False, False,
                 check_single_buy_cap),
    RuleTemplate("daily_total_cap", "일일_매매대금_상한", "원", None, False,
                 False, check_daily_total_cap),
]}

# 미설정 사용자의 기본 조합 — 1계층 v1과 판정 동일 (회귀 테스트가 감시)
DEFAULT_RULESET = [(t.id, t.default_param)
                   for t in TEMPLATES.values() if t.default_on]
