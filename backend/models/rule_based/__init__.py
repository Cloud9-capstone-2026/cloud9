"""
rule_based/__init__.py
Rule-based 탐지 — 거래별 점수 산출 (1계층 v1: 2026-07-25 동결)

규칙 셋 v1 (전부 표준 컬럼만으로 계산 — 포지션 재생 불필요):
  R1 일중_반복매매  같은 종목 하루 4회 이상 매매 (rules/daily_frequency)
  R2 당일_왕복매매  동일 종목 같은 날 매수+매도   (rules/same_day_roundtrip)
손익 기반 규칙(손실 직후 재진입·물타기 반복)은 포지션 재생 인프라 필요 → v2 이월.

점수화: rule_score = 1 − Π(1 − wᵢ)  (위반한 규칙들의 가중 결합)
  - 규칙이 추가돼도 [0,1] 유지 — 앙상블 스케일 불변
  - wᵢ = 규칙별 심각도의 제품 판단값(유형 C — 데이터 캘리브레이션 대상 아님:
    bright line 임계값을 데이터로 정하면 2계층과 역할이 겹침)
  - v1: w=0.7 공통 → 1개 위반 0.7, 2개 위반 0.91

★ 앙상블 가중치·임계값 캘리브레이션은 이 정의 동결 위에서 수행 —
  규칙 추가·변경 시 재캘리브레이션 필요 (PROCESS.md 2026-07-25).
"""

import pandas as pd

from models.rule_based.rules.daily_frequency import check_daily_trade_frequency
from models.rule_based.rules.same_day_roundtrip import check_same_day_roundtrip

# (규칙명, 가중치 w, 판정 함수) — 함수는 df와 같은 인덱스의 bool Series 반환
RULES = [
    ("일중_반복매매", 0.7, check_daily_trade_frequency),
    ("당일_왕복매매", 0.7, check_same_day_roundtrip),
]


def run_rule_based(df: pd.DataFrame) -> dict:
    """
    반환: {
        "is_anomaly": bool,
        "trade_results": [
            {"날짜", "종목명", "rule_score": float 0~1, "triggered_rules": [...]}, ...
        ]
    }
    """
    if len(df) == 0:
        return {"is_anomaly": False, "trade_results": []}

    df = df.reset_index(drop=True)
    flags = {name: fn(df) for name, _w, fn in RULES}

    trade_results = []
    for i, row in df.iterrows():
        triggered = [name for name, _w, _fn in RULES if flags[name].iloc[i]]
        score = 1.0
        for name, w, _fn in RULES:
            if name in triggered:
                score *= 1.0 - w
        score = round(1.0 - score, 4)

        trade_results.append({
            "날짜": str(row["날짜"].date()),
            "종목명": row["종목명"],
            "rule_score": score,
            "triggered_rules": triggered,
        })

    is_anomaly = any(t["rule_score"] > 0 for t in trade_results)
    return {"is_anomaly": is_anomaly, "trade_results": trade_results}
