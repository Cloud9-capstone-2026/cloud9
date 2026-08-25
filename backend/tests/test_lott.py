"""
복권성(LOTT) 월별 합성값 — 시점별 시장 스냅샷 인자 도입(lott.py) 검증.

고정하는 것: (1) 기본 경로(snapshots=None)의 출력은 리팩터 전과 동일(픽스처 골든)
(2) 달마다 같은 스냅샷을 주면 기본 경로와 정확히 같다 (3) 스냅샷이 다른 달만
값이 바뀌고, 스냅샷 없는 달은 건너뛴다. 네트워크·모델 0.
"""

import pandas as pd
import pytest

from synthetic_data import config
from synthetic_data.market.lott import compute_monthly_lott

# 리팩터 전(ad1fb1e) 코드로 conftest 픽스처에서 얻은 값 — 60일 룩백 후 3개월.
_GOLDEN = {
    (2020, 5): {"000010": 3.0, "000020": 1.6666666666666665, "000030": 1.3333333333333333},
    (2020, 6): {"000010": 1.6666666666666665, "000020": 2.333333333333333, "000030": 2.0},
    (2020, 7): {"000010": 1.6666666666666665, "000020": 2.0, "000030": 2.333333333333333},
}
_TICKERS = ["000010", "000020", "000030"]
_CAPS = pd.Series({"000010": 1e9, "000020": 5e9, "000030": 2e10})
_PBRS = pd.Series({"000010": 0.5, "000020": 1.0, "000030": 2.0})
_KOSDAQ = {"000020"}


def _same(a, b):
    assert a.keys() == b.keys()
    for k in a:
        assert a[k] == pytest.approx(b[k], abs=1e-12), k


def test_default_path_matches_pre_refactor_golden(price_df, index_df):
    _same(compute_monthly_lott(price_df, index_df, _TICKERS), _GOLDEN)


@pytest.fixture()
def fixture_snapshot_config(monkeypatch):
    """config 스냅샷을 픽스처 종목 값으로 바꿔 FF3 요인·규모분류가 실제로 작동하게."""
    monkeypatch.setattr(config, "MARKETCAP_20200302", _CAPS.to_dict())
    monkeypatch.setattr(config, "PBR_20200302", _PBRS.to_dict())
    monkeypatch.setattr(config, "KOSDAQ_TICKERS", sorted(_KOSDAQ))


def test_same_snapshot_every_month_equals_default(price_df, index_df, fixture_snapshot_config):
    base = compute_monthly_lott(price_df, index_df, _TICKERS)
    assert base.keys() == _GOLDEN.keys()
    snaps = {k: (_CAPS, _PBRS, _KOSDAQ) for k in base}
    _same(compute_monthly_lott(price_df, index_df, _TICKERS, snapshots=snaps), base)


def test_per_month_snapshot_changes_only_that_month(price_df, index_df, fixture_snapshot_config):
    base = compute_monthly_lott(price_df, index_df, _TICKERS)
    # 6월만 시총 순서를 뒤집고 코스닥 집합을 바꿈, 7월은 스냅샷 없음.
    flipped = pd.Series({"000010": 2e10, "000020": 5e9, "000030": 1e9})
    snaps = {
        (2020, 5): (_CAPS, _PBRS, _KOSDAQ),
        (2020, 6): (flipped, _PBRS, {"000010", "000030"}),
    }
    out = compute_monthly_lott(price_df, index_df, _TICKERS, snapshots=snaps)
    assert set(out) == {(2020, 5), (2020, 6)}  # 7월 스킵
    assert out[(2020, 5)] == pytest.approx(base[(2020, 5)], abs=1e-12)
    assert out[(2020, 6)] != pytest.approx(base[(2020, 6)], abs=1e-12)
