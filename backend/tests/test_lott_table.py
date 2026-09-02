"""
시장 전체 복권성 순위표 연결(backend/lott_table.py, features.lott_table 인자) 검증.

고정하는 것: CSV → dict 계약 / 표 없으면 None / 표 주입 시 해당 (월, 종목)의
lott_rank가 채워지고 없는 월·종목은 결측 / 표 None이면 layer3 준비 단계의 피처가
표 없는 build_features와 동일(회귀). 네트워크·모델 0.
"""

import numpy as np
import pandas as pd
import pytest

import lott_table
from synthetic_data.features import build_features


def _write_csv(path, rows):
    pd.DataFrame(rows, columns=["적용연", "적용월", "종목코드", "lott_rank"]).to_csv(
        path, index=False, encoding="utf-8")


@pytest.fixture()
def fake_table_file(tmp_path, monkeypatch):
    p = tmp_path / "lott_ranks.csv"
    _write_csv(p, [(2020, 5, "000010", 0.9), (2020, 5, "000020", 0.1),
                   (2020, 6, "000010", 0.5), (2020, 6, "000030", 0.7)])
    monkeypatch.setenv("CANARY_LOTT_TABLE", str(p))
    lott_table._load.cache_clear()
    return p


def test_csv_to_dict_contract(fake_table_file):
    t = lott_table.get_lott_table()
    assert set(t) == {(2020, 5), (2020, 6)}
    assert t[(2020, 5)]["000010"] == 0.9
    assert t[(2020, 6)].index.dtype == object  # 종목코드는 문자열(선행 0 보존)
    assert "000020" not in t[(2020, 6)].index


def test_missing_file_returns_none(tmp_path, monkeypatch):
    monkeypatch.setenv("CANARY_LOTT_TABLE", str(tmp_path / "없음.csv"))
    assert lott_table.get_lott_table() is None


def test_injected_table_fills_events(synthetic_trades, price_df, index_df, fake_table_file):
    t = lott_table.get_lott_table()
    ev = build_features(synthetic_trades.copy(), price_df, index_df, windows=(None,),
                        lott_table=t)["events"]
    ev["월"] = pd.to_datetime(ev["거래일자"]).dt.month
    may_10 = ev[(ev["월"] == 5) & (ev["종목코드"] == "000010")]
    assert len(may_10) and (may_10["lott_rank"] == 0.9).all()
    jun_20 = ev[(ev["월"] == 6) & (ev["종목코드"] == "000020")]  # 표에 없는 (월, 종목)
    assert len(jun_20) and jun_20["lott_rank"].isna().all()
    assert ev[ev["월"] == 3]["lott_rank"].isna().all()  # 표에 없는 달


# ─ 신선도 판정 + 자체 다운로드 (2026-09-02 모델 Release에서 분리) ─

def _this_month_rows():
    import datetime
    t = datetime.date.today()
    return [(t.year, t.month, "000010", 0.5)]


@pytest.fixture()
def download_env(tmp_path, monkeypatch):
    """CANARY_LOTT_TABLE 해제 + 아티팩트 경로를 tmp로 — 다운로드 로직이 사는 환경."""
    monkeypatch.delenv("CANARY_LOTT_TABLE", raising=False)
    monkeypatch.setenv("CANARY_MODEL_DIR", str(tmp_path))
    monkeypatch.setattr(lott_table, "_last_download_try", None)
    lott_table._load.cache_clear()
    return tmp_path


def _mock_release(monkeypatch, csv_bytes):
    """GitHub API 2단 호출(태그 조회 → 자산 다운로드) 흉내. 호출 URL 기록."""
    calls = []

    class _Resp:
        def __init__(self, js=None, content=b""):
            self._js, self.content = js, content
        def raise_for_status(self):
            pass
        def json(self):
            return self._js

    def fake_get(url, **k):
        calls.append(url)
        if "/releases/tags/" in url:
            return _Resp(js={"assets": [{"name": "lott_ranks.csv", "url": "asset://lott"}]})
        return _Resp(content=csv_bytes)
    monkeypatch.setattr(lott_table.requests, "get", fake_get)
    return calls


def test_stale_table_triggers_download(download_env, monkeypatch):
    _write_csv(download_env / "lott_ranks.csv", [(2020, 5, "000010", 0.9)])  # 이번 달 없음
    fresh = pd.DataFrame(_this_month_rows(),
                         columns=["적용연", "적용월", "종목코드", "lott_rank"])
    calls = _mock_release(monkeypatch, fresh.to_csv(index=False).encode())
    t = lott_table.get_lott_table()
    assert calls  # 다운로드 시도됨
    import datetime
    today = datetime.date.today()
    assert (today.year, today.month) in t  # 새 표가 반환됨
    assert t[(today.year, today.month)]["000010"] == 0.5


def test_download_failure_keeps_old_table_with_cooldown(download_env, monkeypatch):
    _write_csv(download_env / "lott_ranks.csv", [(2020, 5, "000010", 0.9)])
    calls = []

    def fail_get(url, **k):
        calls.append(url)
        raise lott_table.requests.ConnectionError("no network")
    monkeypatch.setattr(lott_table.requests, "get", fail_get)

    t = lott_table.get_lott_table()
    assert t[(2020, 5)]["000010"] == 0.9  # 예외 없이 기존 표 유지
    n = len(calls)
    assert n >= 1
    assert lott_table.get_lott_table() is not None  # 쿨다운 안 — 재시도 없음
    assert len(calls) == n


def test_env_path_skips_download(fake_table_file, monkeypatch):
    def no_network(*a, **k):
        raise AssertionError("CANARY_LOTT_TABLE 지정 시 네트워크 호출 금지")
    monkeypatch.setattr(lott_table.requests, "get", no_network)
    monkeypatch.setattr(lott_table, "_last_download_try", None)
    assert lott_table.get_lott_table() is not None  # 2020년 표(낡음)라도 그대로 신뢰


def test_layer3_prepare_uses_table_or_falls_back(synthetic_trades, price_df, index_df,
                                                monkeypatch, fake_table_file):
    from models import layer3

    # 표 None → 표 없는 build_features와 동일 (기존 경로 회귀)
    monkeypatch.setattr(lott_table, "get_lott_table", lambda: None)
    _, feats = layer3._prepare_features(synthetic_trades.copy(), price_df, index_df)
    base = build_features(synthetic_trades.copy(), price_df, index_df, windows=(None,))
    pd.testing.assert_frame_equal(feats["events"].reset_index(drop=True),
                                  base["events"].reset_index(drop=True))

    # 표 있음 → lott_rank가 표 값으로 채워짐
    monkeypatch.setattr(lott_table, "get_lott_table",
                        lambda: {(2020, 5): pd.Series({"000010": 0.42})})
    _, feats2 = layer3._prepare_features(synthetic_trades.copy(), price_df, index_df)
    ev = feats2["events"]
    hit = ev[(pd.to_datetime(ev["거래일자"]).dt.month == 5) & (ev["종목코드"] == "000010")]
    assert len(hit) and np.allclose(hit["lott_rank"], 0.42)
