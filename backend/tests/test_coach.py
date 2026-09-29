"""
계좌 편향 점수(pipeline.coach) — 편향별로 맞는 거래 쪽만 평균, 해당 거래가 없으면 None.
규칙 조언 — 거래의 편향 점수가 기준을 넘고 짝 규칙이 꺼져 있을 때만.
"""

from datetime import date

import pandas as pd
import pytest

from pipeline.coach import (account_bias_scores, daily_amount_median,
                            load_account_bias_scores, rule_advice)

N = 5  # 테스트 표본 크기(점수 계산에 최소 건수 기준은 없음)


def _scores(d=0.0, o=0.0, l=0.0, h=0.0):
    return {"disposition_strength": d, "overconfidence": o,
            "lottery_preference": l, "herd_sensitivity": h}


def test_each_bias_averages_only_its_side():
    """매수 8건·매도 5건 — 처분효과는 매도 5건만, 나머지는 매수 8건만 평균.
    전 거래 평균이었다면 처분효과가 매수의 0에 희석돼 0.5×5/13로 떨어진다."""
    rows = ([("매수", _scores(d=0.0, o=0.2, l=0.4, h=0.1))] * 8
            + [("매도", _scores(d=0.5, o=0.0, l=0.0, h=0.0))] * 5)
    out = account_bias_scores(rows)
    assert out["disposition_strength"] == {"score": 50.0, "n_trades": 5, "side": "매도"}
    assert out["overconfidence"] == {"score": 20.0, "n_trades": 8, "side": "매수"}
    assert out["lottery_preference"]["score"] == 40.0
    assert out["herd_sensitivity"]["score"] == 10.0


def test_single_trade_scored_zero_trades_none():
    """최소 건수 기준 없음 — 1건이어도 점수, 해당 쪽 거래가 0건이면 None."""
    out = account_bias_scores([("매도", _scores(d=0.9))])
    assert out["disposition_strength"] == {"score": 90.0, "n_trades": 1, "side": "매도"}
    assert out["overconfidence"] == {"score": None, "n_trades": 0, "side": "매수"}


def test_trades_without_scores_skipped():
    rows = [("매수", None)] * 10 + [("매수", _scores(o=0.6))] * N
    out = account_bias_scores(rows)
    assert out["overconfidence"] == {"score": 60.0, "n_trades": N, "side": "매수"}


def test_no_rows_all_withheld():
    out = account_bias_scores([])
    assert all(v["score"] is None and v["n_trades"] == 0 for v in out.values())


# ─ 규칙 조언 (거래 1건 단위) ─

TH = 0.7283        # 3계층 기준(detect.DEEP_THRESHOLD)과 같은 값을 넘겨 쓴다
MEDIAN = 2_600_000.0


def test_advice_per_bias_over_threshold():
    """과잉확신 → 일일 매매대금 상한(본인 중앙값), 처분효과 → 최소 보유기간 3일."""
    assert rule_advice(_scores(o=0.8), set(), MEDIAN, TH) == [{
        "bias": "overconfidence", "rule_id": "daily_total_cap",
        "label": "일일_매매대금_상한", "suggested_param": MEDIAN, "param_unit": "원"}]
    assert rule_advice(_scores(d=0.8), set(), MEDIAN, TH) == [{
        "bias": "disposition_strength", "rule_id": "min_holding",
        "label": "최소_보유기간", "suggested_param": 3, "param_unit": "일"}]


def test_advice_not_limited_to_top_bias():
    """가장 강한 편향이 복권형이어도 과잉확신이 기준을 넘으면 조언한다."""
    out = rule_advice(_scores(o=0.80, l=0.85), set(), MEDIAN, TH)
    assert [a["bias"] for a in out] == ["overconfidence"]


def test_advice_both_biases_listed():
    out = rule_advice(_scores(d=0.9, o=0.9), set(), MEDIAN, TH)
    assert {a["rule_id"] for a in out} == {"daily_total_cap", "min_holding"}


@pytest.mark.parametrize("scores,enabled", [
    (_scores(o=0.72, d=0.72), set()),                  # 기준 미달
    (_scores(l=0.9, h=0.9), set()),                    # 복권형·군집은 조언 없음
    (_scores(o=0.9, d=0.9), {"daily_total_cap", "min_holding"}),  # 이미 켜 둠
    (None, set()),                                     # 3계층 판정 없는 거래
])
def test_no_advice(scores, enabled):
    assert rule_advice(scores, enabled, MEDIAN, TH) == []


def test_advice_at_threshold_boundary():
    assert rule_advice(_scores(o=TH), set(), MEDIAN, TH) != []


def test_no_cap_advice_without_history_amount():
    """하루 매매대금을 못 구하면 상한은 권하지 않는다(값 없이 켤 수 없는 규칙)."""
    assert rule_advice(_scores(o=0.9), set(), None, TH) == []


def _history(rows):
    return pd.DataFrame(rows, columns=["날짜", "매매구분", "총거래금액"])


def test_daily_median_sums_buy_and_sell_per_day():
    """하루 합(매수+매도) 200만·500만·260만 → 중앙값 260만. 평균(320만)이 아니다."""
    h = _history([
        ("2026-09-01", "매수", 1_200_000), ("2026-09-01", "매도", 800_000),
        ("2026-09-03", "매수", 5_000_000),
        ("2026-09-08", "매수", 2_600_000),
    ])
    assert daily_amount_median(h) == 2_600_000.0


def test_daily_median_rounds_to_ten_thousand_with_floor():
    assert daily_amount_median(_history([("2026-09-01", "매수", 1_234_567)])) == 1_230_000.0
    assert daily_amount_median(_history([("2026-09-01", "매수", 3_000)])) == 10_000.0
    assert daily_amount_median(_history([])) is None


@pytest.fixture()
def db():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    import orm  # noqa: F401 — 테이블 등록
    from database import Base
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    s = sessionmaker(bind=engine)()
    yield s
    s.close()


def _add(db, user_id, kind, scores, link=True):
    from orm import AnalysisResult, Trade
    t = Trade(user_id=user_id, 거래일자=date(2026, 1, 5), 종목명="A", 거래구분=kind,
              거래수량=1, 거래단가=100, 거래금액=100, 수수료=0, 거래세=0, 정산금액=100)
    db.add(t)
    db.flush()
    db.add(AnalysisResult(user_id=user_id, trade_id=t.id if link else None,
                          detail={"bias_scores": scores}))
    db.commit()


def test_load_uses_own_results_and_trade_side(db):
    """본인 결과만, 거래구분은 연결된 거래에서. 남의 결과는 섞이지 않는다."""
    for _ in range(N):
        _add(db, 1, "매도", _scores(d=0.4))
        _add(db, 1, "매수", _scores(o=0.2))
        _add(db, 2, "매도", _scores(d=1.0))   # 다른 사용자
    out = load_account_bias_scores(db, 1)
    assert out["scores"]["disposition_strength"]["score"] == 40.0
    assert out["scores"]["overconfidence"]["score"] == 20.0


def test_load_excludes_results_without_trade_link(db):
    """trade_id 없는 옛 결과는 매수/매도를 알 수 없어 계산에서 빠진다."""
    _add(db, 1, "매도", _scores(d=0.9), link=False)
    out = load_account_bias_scores(db, 1)
    assert out == {"scores": out["scores"]}
    assert out["scores"]["disposition_strength"] == {
        "score": None, "n_trades": 0, "side": "매도"}


# ─ API: GET /coach/scores (실제 로그인 흐름 — test_survey와 같은 방식) ─

@pytest.fixture()
def client():
    from fastapi.testclient import TestClient
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    import orm  # noqa: F401
    from database import Base, get_db
    from main import app
    from rate_limit import limiter

    engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        s = Session()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_db] = override_get_db
    limiter.reset()
    yield TestClient(app), Session
    app.dependency_overrides.clear()


def _login(c, email):
    c.post("/auth/signup", json={"email": email, "password": "password123",
                                 "name": "테스터", "agreed_terms": True})
    r = c.post("/auth/login", data={"username": email, "password": "password123"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_scores_requires_auth(client):
    c, _ = client
    assert c.get("/coach/scores").status_code == 401


def test_scores_returns_only_own_account(client):
    """두 사용자 — 각자 로그인하면 자기 결과로 계산된 점수만 받는다."""
    from orm import User
    c, Session = client
    h1 = _login(c, "coach1@test.com")
    h2 = _login(c, "coach2@test.com")
    s = Session()
    u1 = s.query(User).filter(User.email == "coach1@test.com").one().id
    u2 = s.query(User).filter(User.email == "coach2@test.com").one().id
    for _ in range(N):
        _add(s, u1, "매도", _scores(d=0.3))
        _add(s, u2, "매도", _scores(d=0.8))
    s.close()

    body1 = c.get("/coach/scores", headers=h1).json()
    body2 = c.get("/coach/scores", headers=h2).json()
    assert body1["scores"]["disposition_strength"]["score"] == 30.0
    assert body2["scores"]["disposition_strength"]["score"] == 80.0
    assert set(body1["scores"]) == {"disposition_strength", "overconfidence",
                                    "lottery_preference", "herd_sensitivity"}
    assert body1["scores"]["overconfidence"] == {"score": None, "n_trades": 0,
                                                 "side": "매수"}
    assert set(body1) == {"scores"}
