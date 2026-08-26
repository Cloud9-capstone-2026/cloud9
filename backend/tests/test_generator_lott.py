"""
합성 생성기의 복권성 조회(model.MarketModel.get_lott_scores)가 시장 전체 순위표를
적용월 기준으로 그대로 읽는지 — 시세·네트워크 없이 인스턴스 껍데기만 만들어 검증.
(표 → 생성기 → _rank_norm 경로의 첫 이음새. 예전엔 유니버스 201종목만으로 직전 달을
그 자리 계산했고, 이제 학습·추론이 같은 표를 쓴다.)
"""

from datetime import date

import pandas as pd

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
