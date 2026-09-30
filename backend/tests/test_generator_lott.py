"""
합성 생성기의 복권성 조회(model.MarketModel.get_lott_scores)가 시장 전체 순위표를
적용월 기준으로 그대로 읽는지 — 시세·네트워크 없이 인스턴스 껍데기만 만들어 검증.
(표 → 생성기 → _rank_norm 경로의 첫 이음새. 예전엔 유니버스 201종목만으로 직전 달을
그 자리 계산했고, 이제 학습·추론이 같은 표를 쓴다.)
"""

from datetime import date

import pandas as pd
import pytest

from synthetic_data.core.model import MarketModel


def _stub(table):
    m = MarketModel.__new__(MarketModel)  # __init__(시세 조회) 우회
    m._lott_table = table
    return m


def test_get_lott_scores_reads_applied_month_directly():
    m = _stub({(2020, 3): pd.Series({"000010": 0.9, "000020": 0.1}),
               (2020, 4): pd.Series({"000010": 0.2})})
    assert m.get_lott_scores(date(2020, 3, 2)) == {"000010": 0.9, "000020": 0.1}
    assert m.get_lott_scores(date(2020, 4, 28)) == {"000010": 0.2}


def test_get_lott_scores_missing_month_is_empty():
    m = _stub({(2020, 3): pd.Series({"000010": 0.9})})
    assert m.get_lott_scores(date(2020, 5, 4)) == {}


def test_get_lott_scores_drops_nan_so_rank_never_negative():
    """순위표의 결측은 빠진다 — 표에 없는 종목과 같이 0.0(최하위)으로 처리.
    결측이 _rank_norm에 들어가면 음수 순위가 나와 복권형 라벨이 음수가 됐다
    (2026-10-01, 7세트 212건)."""
    from synthetic_data.core.model import _rank_norm
    m = _stub({(2020, 3): pd.Series({"000010": 0.9, "000020": float("nan"),
                                     "000030": 0.1})})
    lott = m.get_lott_scores(date(2020, 3, 2))
    assert lott == {"000010": 0.9, "000030": 0.1}
    cands = ["000010", "000020", "000030", "000040"]  # 000040 = 표에 없음
    rank = _rank_norm(cands, {t: lott.get(t, 0.0) for t in cands})
    assert all(0.0 <= v <= 1.0 for v in rank.values())
    assert rank["000020"] == rank["000040"]  # 결측 = 표에 없음과 동일 취급


def test_rank_norm_rejects_nan():
    from synthetic_data.core.model import _rank_norm
    with pytest.raises(ValueError):
        _rank_norm(["a", "b"], {"a": 0.2, "b": float("nan")})


def test_check_trade_labels_rejects_out_of_range():
    """라벨 4종은 정의상 0~1 — 범위 밖이면 생성을 중단한다."""
    from synthetic_data.main import check_trade_labels
    ok = pd.DataFrame({"attr_disposition": [0.0, 0.77], "attr_overconfidence": [0.19, 0.0],
                       "attr_lottery": [0.52, 1.0], "attr_herd": [0.0, 0.29]})
    check_trade_labels(ok)
    for col, bad in [("attr_lottery", -0.03), ("attr_herd", 1.2),
                     ("attr_disposition", float("nan"))]:
        df = ok.copy()
        df.loc[0, col] = bad
        with pytest.raises(ValueError):
            check_trade_labels(df)
