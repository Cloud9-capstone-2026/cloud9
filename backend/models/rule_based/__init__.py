"""
rule_based/__init__.py
1계층 — 사용자 정의 규칙 템플릿 조합으로 거래별 판정.

정체성: "사용자가 스스로 정한(동의한) 절제 규칙 위반". 템플릿 정의와 기본
조합은 templates.py(레지스트리), 사용자별 조합 로드는 pipeline.user_rules.

판정 구도(3계층과 동일): 전체 이력을 문맥으로 계산하되 결과는 신규 거래만
반환 — 손실 후 재진입처럼 과거 업로드의 거래가 문맥인 템플릿 때문. 판정
대상 범위는 신규 거래 그대로라 소급 재판정은 없다.

점수화: rule_score = 1 − Π(1 − w), w=0.7 공통(v1 동결값 승계 — templates.
DEFAULT_WEIGHT). 표시용 점수이며 판정(verdict)은 flag 개수 기반이라
템플릿이 추가·변경돼도 재캘리브레이션이 필요 없다.
"""

import pandas as pd

from models.rule_based.positions import replay_positions
from models.rule_based.templates import (DEFAULT_RULESET, DEFAULT_WEIGHT,
                                         TEMPLATES)


def run_rule_based(df: pd.DataFrame, new_positions=None, ruleset=None) -> dict:
    """전체 이력 df 중 신규 거래(new_positions 행 번호)만 판정.

    new_positions 생략 = 전체가 판정 대상, ruleset 생략 = 기본 조합 —
    기존 호출 run_rule_based(신규 거래 df)가 지금까지와 동일하게 동작한다.

    ruleset: [(template_id, param)] — pipeline.user_rules.load_ruleset 산출.
    빈 조합(사용자가 전부 끔)이면 위반 없음으로 처리된다.

    반환(기존과 동일): {
        "is_anomaly": bool,
        "trade_results": [
            {"날짜", "종목명", "rule_score": float 0~1, "triggered_rules": [...]}, ...
        ]
    }
    """
    if len(df) == 0:
        return {"is_anomaly": False, "trade_results": []}

    df = df.reset_index(drop=True)
    if new_positions is None:
        new_positions = range(len(df))
    if ruleset is None:
        ruleset = DEFAULT_RULESET

    active = [(TEMPLATES[tid], param) for tid, param in ruleset
              if tid in TEMPLATES]
    # 포지션 재생은 필요한 템플릿이 있을 때만, 전체 이력으로 1회
    pos = (replay_positions(df)
           if any(t.needs_positions for t, _p in active) else None)

    flags = {t.표시명: t.fn(df, pos, param) for t, param in active}

    trade_results = []
    for i in new_positions:
        i = int(i)
        row = df.iloc[i]
        triggered = [name for name, s in flags.items() if bool(s.iloc[i])]
        score = 1.0
        for _ in triggered:
            score *= 1.0 - DEFAULT_WEIGHT
        score = round(1.0 - score, 4)

        trade_results.append({
            "날짜": str(row["날짜"].date()),
            "종목명": row["종목명"],
            "rule_score": score,
            "triggered_rules": triggered,
        })

    is_anomaly = any(t["rule_score"] > 0 for t in trade_results)
    return {"is_anomaly": is_anomaly, "trade_results": trade_results}
