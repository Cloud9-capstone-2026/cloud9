"""
계좌 편향 점수(pipeline.coach) — 편향별로 맞는 거래 쪽만 평균, 적은 거래는 보류.
"""

from datetime import date

import pytest

from pipeline.coach import MIN_TRADES, account_bias_scores, load_account_bias_scores


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


def test_too_few_trades_withheld():
    rows = ([("매도", _scores(d=0.9))] * (MIN_TRADES - 1)
            + [("매수", _scores(o=0.3))] * MIN_TRADES)
    out = account_bias_scores(rows)
    assert out["disposition_strength"] == {
        "score": None, "n_trades": MIN_TRADES - 1, "side": "매도"}
    assert out["overconfidence"]["score"] == 30.0


def test_trades_without_scores_skipped():
    rows = [("매수", None)] * 10 + [("매수", _scores(o=0.6))] * MIN_TRADES
    out = account_bias_scores(rows)
    assert out["overconfidence"] == {"score": 60.0, "n_trades": MIN_TRADES, "side": "매수"}


def test_no_rows_all_withheld():
    out = account_bias_scores([])
    assert all(v["score"] is None and v["n_trades"] == 0 for v in out.values())


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
    for _ in range(MIN_TRADES):
        _add(db, 1, "매도", _scores(d=0.4))
        _add(db, 1, "매수", _scores(o=0.2))
        _add(db, 2, "매도", _scores(d=1.0))   # 다른 사용자
    out = load_account_bias_scores(db, 1)
    assert out["scores"]["disposition_strength"]["score"] == 40.0
    assert out["scores"]["overconfidence"]["score"] == 20.0
    assert out["n_excluded_no_link"] == 0


def test_load_excludes_results_without_trade_link(db):
    """trade_id 없는 옛 결과는 매수/매도를 알 수 없어 제외하고 건수로 알린다."""
    _add(db, 1, "매도", _scores(d=0.9), link=False)
    _add(db, 1, "매도", None, link=False)            # 점수도 없던 결과는 세지 않음
    out = load_account_bias_scores(db, 1)
    assert out["n_excluded_no_link"] == 1
    assert out["scores"]["disposition_strength"]["n_trades"] == 0
