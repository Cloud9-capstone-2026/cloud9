"""
계좌 단위 편향 점수 — 거래별 3계층 점수(bias_scores)를 계좌 하나의 점수로 모은다.

편향마다 의미 있는 거래 쪽만 평균 낸다. 학습 라벨이 처분효과는 매도에서만,
과잉확신·복권형·군집은 매수에서만 정의돼 있어(반대편 라벨은 0 — 생성기가
매도 쪽 편향 채널을 만들지 않음) 모델은 반대편 거래에 0 가까운 값을 낸다.
전 거래 평균을 내면 그 0이 섞여 매수·매도 비율만큼 희석된다(매수 80% 계좌의
처분효과 ≈ 실제의 1/5). 따라서 점수의 의미는 "매도 결정의 처분효과"와
"매수 결정의 과잉확신·복권형·군집"이다.

규칙 조언 — 거래의 편향 점수가 3계층 기준을 넘으면, 그 편향을 줄이는 데 도움이
되는 절제 규칙을 켜 보라고 권한다. 규칙은 편향을 잡는 도구가 아니라 사용자가
스스로 거는 약속이라, 짝은 "그 습관을 늦추는 약속인가"로 골랐다. 복권형·군집은
그런 규칙이 7종 중에 없어 조언하지 않는다.
"""

import pandas as pd

from models.rule_based.rules.amount_caps import _amounts
from models.rule_based.templates import TEMPLATES
from orm import AnalysisResult, Trade

# 편향 → 점수를 내는 거래구분 (ml/train/train_tagger.ATTR_SIDE와 같은 사실)
BIAS_SIDE = {
    "disposition_strength": "매도",
    "overconfidence": "매수",
    "lottery_preference": "매수",
    "herd_sensitivity": "매수",
}


# 편향 → 권하는 규칙. 처분효과는 "이익 종목을 서둘러 파는" 쪽만 다룬다
# (손실 종목을 오래 드는 쪽은 맞는 규칙이 없음).
ADVICE_RULE = {
    "overconfidence": "daily_total_cap",
    "disposition_strength": "min_holding",
}

ADVICE_DISCLAIMER = ("이 조언은 매매 습관 점검을 위한 참고 정보이며 투자 권유가 "
                     "아닙니다. 투자 판단과 책임은 투자자 본인에게 있습니다.")


def daily_amount_median(history: pd.DataFrame) -> float | None:
    """거래가 있던 날들의 하루 매매대금(매수+매도) 중앙값, 만 원 단위.

    금액 정의는 일일 매매대금 상한 규칙과 같아 추천값과 판정이 어긋나지 않는다.
    평균이 아닌 중앙값 — 하루만 크게 거래해도 평균은 끌려간다. 이 값을 상한으로
    켜면 지금 거래일의 절반가량이 상한을 넘는다."""
    if len(history) == 0:
        return None
    day = pd.to_datetime(history["날짜"]).dt.normalize()
    median = _amounts(history).groupby(day).sum().median()
    if pd.isna(median):
        return None
    return float(max(round(median, -4), 10_000))


def rule_advice(side, bias_scores, enabled_rule_ids, daily_median, threshold) -> list:
    """거래 1건의 (거래구분, 편향 점수) → 규칙 조언 목록(없으면 빈 목록).

    편향마다 따로 본다(가장 강한 편향이 아니어도 기준을 넘으면 조언). 그 거래
    방향의 편향만 본다(매도는 처분효과, 매수는 과잉확신 — 반대편 점수는 판정에도
    쓰지 않는 값). 짝 규칙이 이미 켜져 있으면 권하지 않는다. bias_scores가 없는
    거래(3계층 제외·판정 불가)는 조언 없음."""
    advice = []
    for bias, rule_id in ADVICE_RULE.items():
        score = (bias_scores or {}).get(bias)
        if (BIAS_SIDE[bias] != side or score is None or score < threshold
                or rule_id in enabled_rule_ids):
            continue
        template = TEMPLATES[rule_id]
        param = (daily_median if rule_id == "daily_total_cap"
                 else template.default_param)
        if param is None:
            continue
        advice.append({
            "bias": bias,
            "rule_id": rule_id,
            "label": template.표시명,
            "suggested_param": param,
            "param_unit": template.param_unit,
        })
    return advice


def account_bias_scores(rows) -> dict:
    """(거래구분, bias_scores) 목록 → 편향별 {score 0~100 | None, n_trades, side}.

    bias_scores가 없는 거래(3계층 제외·판정 불가)는 건너뛴다. 해당 쪽 거래가
    하나도 없으면 score는 None — 0점과 구분된다."""
    sums = dict.fromkeys(BIAS_SIDE, 0.0)
    counts = dict.fromkeys(BIAS_SIDE, 0)
    for side, scores in rows:
        if not scores:
            continue
        for bias, need in BIAS_SIDE.items():
            value = scores.get(bias)
            if side == need and value is not None:
                sums[bias] += float(value)
                counts[bias] += 1
    return {
        bias: {
            "score": (round(sums[bias] / counts[bias] * 100, 1)
                      if counts[bias] else None),
            "n_trades": counts[bias],
            "side": need,
        }
        for bias, need in BIAS_SIDE.items()
    }


def load_account_bias_scores(db, user_id: int) -> dict:
    """본인 분석 결과 전체로 계좌 점수 계산.

    결과 detail에는 매수/매도가 없어 trade_id로 거래와 이어 구분을 얻는다.
    trade_id가 없는 옛 결과(거래 연결 도입 전)는 구분을 알 수 없어 조인에서
    빠진다."""
    rows = (
        db.query(Trade.거래구분, AnalysisResult.detail)
        .join(Trade, Trade.id == AnalysisResult.trade_id)
        .filter(AnalysisResult.user_id == user_id)
        .all()
    )
    return {"scores": account_bias_scores(
        (side, (detail or {}).get("bias_scores")) for side, detail in rows)}
