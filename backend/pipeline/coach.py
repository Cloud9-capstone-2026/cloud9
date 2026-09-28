"""
계좌 단위 편향 점수 — 거래별 3계층 점수(bias_scores)를 계좌 하나의 점수로 모은다.

편향마다 의미 있는 거래 쪽만 평균 낸다. 학습 라벨이 처분효과는 매도에서만,
과잉확신·복권형·군집은 매수에서만 정의돼 있어(반대편 라벨은 0 — 생성기가
매도 쪽 편향 채널을 만들지 않음) 모델은 반대편 거래에 0 가까운 값을 낸다.
전 거래 평균을 내면 그 0이 섞여 매수·매도 비율만큼 희석된다(매수 80% 계좌의
처분효과 ≈ 실제의 1/5). 따라서 점수의 의미는 "매도 결정의 처분효과"와
"매수 결정의 과잉확신·복권형·군집"이다.
"""

from orm import AnalysisResult, Trade

# 편향 → 점수를 내는 거래구분 (ml/train/train_tagger.ATTR_SIDE와 같은 사실)
BIAS_SIDE = {
    "disposition_strength": "매도",
    "overconfidence": "매수",
    "lottery_preference": "매수",
    "herd_sensitivity": "매수",
}


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
    trade_id가 없는 옛 결과(거래 연결 도입 전)는 구분을 알 수 없어 빼고,
    그중 점수가 있던 건수를 n_excluded_no_link로 알린다."""
    rows = (
        db.query(Trade.거래구분, AnalysisResult.detail)
        .outerjoin(Trade, Trade.id == AnalysisResult.trade_id)
        .filter(AnalysisResult.user_id == user_id)
        .all()
    )
    linked, excluded = [], 0
    for side, detail in rows:
        scores = (detail or {}).get("bias_scores")
        if side is None:
            excluded += bool(scores)
            continue
        linked.append((side, scores))
    return {"scores": account_bias_scores(linked), "n_excluded_no_link": excluded}
