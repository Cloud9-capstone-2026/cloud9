"""
KRX Open API 클라이언트(synthetic_data/market/krx_api.py)로의 전환 검증 — 네트워크 0.

고정하는 것: 수정주가 보정(분할은 보정, 유상증자는 미보정, 무변화는 그대로) /
실계좌 종목명→코드 맵이 종목기본정보에서 만들어짐 / price_cache 기본 fetcher가
날짜별 캐시에서 종목 하나의 OHLCV를 잘라 옛 스키마로 돌려줌.
"""

from datetime import date

import numpy as np
import pandas as pd
import pytest
import requests

from synthetic_data.market import krx_api


def _rows(closes, shares, mktcap=None, tk="000010"):
    days = pd.bdate_range("2024-01-02", periods=len(closes)).date
    return pd.DataFrame({
        "종목코드": tk, "거래일자": days,
        "시가": closes, "고가": [c * 1.01 for c in closes], "저가": [c * 0.99 for c in closes],
        "종가": closes, "거래량": 1000, "거래대금": 1.0,
        "시가총액": mktcap if mktcap is not None else [c * s for c, s in zip(closes, shares)],
        "상장주식수": shares,
    })


def test_adjust_split_scales_earlier_prices():
    """1:5 액면분할(주식수 5배, 가격 1/5, 시총 연속) — 분할 전 가격에 1/5."""
    df = _rows([50000, 50500, 10100, 10200], [100, 100, 500, 500])
    out = krx_api.adjust_prices(df)
    assert out["종가"].tolist() == pytest.approx([10000, 10100, 10100, 10200])
    assert out["수정계수"].tolist() == pytest.approx([0.2, 0.2, 1.0, 1.0])
    assert out["저가"].iloc[0] == pytest.approx(50000 * 0.99 * 0.2)  # OHLC 함께 조정


def test_rights_issue_not_adjusted():
    """유상증자 — 주식수는 늘지만 가격은 그대로(시총이 뜀) → 보정 없음."""
    df = _rows([10000, 10000, 10050, 10100], [100, 100, 150, 150])
    out = krx_api.adjust_prices(df)
    assert out["종가"].tolist() == [10000, 10000, 10050, 10100]
    assert (out["수정계수"] == 1.0).all()


def test_no_change_is_identity_and_multi_ticker_independent():
    a = _rows([100, 101, 102], [10, 10, 10], tk="A")
    b = _rows([1000, 500, 505], [10, 20, 20], tk="B")  # B만 1:2 분할
    out = krx_api.adjust_prices(pd.concat([a, b], ignore_index=True))
    assert out[out["종목코드"] == "A"]["종가"].tolist() == [100, 101, 102]
    assert out[out["종목코드"] == "B"]["종가"].tolist() == pytest.approx([500, 500, 505])


def test_name_map_from_base_info(monkeypatch):
    from pipeline import feature_eng

    calls = []

    def fake_base_info(d):
        calls.append(d)
        if len(calls) == 1:  # 첫 날은 휴장일
            return pd.DataFrame(columns=["종목코드", "종목명", "주식종류", "증권그룹", "소속부", "시장"])
        return pd.DataFrame({"종목코드": ["005930", "005935"], "종목명": ["삼성전자", "삼성전자우"],
                             "주식종류": ["보통주", "구형우선주"], "증권그룹": ["주권", "주권"],
                             "소속부": ["", ""], "시장": ["KOSPI", "KOSPI"]})

    monkeypatch.setattr(krx_api, "base_info", fake_base_info)
    monkeypatch.setattr(feature_eng, "_NAME_TO_CODE", None)
    assert feature_eng.get_ticker_code("삼성전자우") == "005935"
    assert feature_eng.get_ticker_code("없는회사") is None
    assert len(calls) == 2  # 휴장일 하루 건너뜀


def test_price_cache_default_fetcher_shape(monkeypatch):
    import price_cache

    days = [date(2024, 1, 2), date(2024, 1, 3)]
    monkeypatch.setattr(krx_api, "prefetch", lambda s, e, with_index=True: days)
    monkeypatch.setattr(krx_api, "load_daily", lambda ds: pd.concat(
        [_rows([100, 110], [10, 10], tk="000010").assign(거래일자=days),
         _rows([5, 6], [10, 10], tk="000020").assign(거래일자=days)], ignore_index=True))
    out = price_cache._default_fetcher("000010", days[0], days[-1])
    assert list(out.columns) == ["거래일자", "시가", "고가", "저가", "종가", "거래량"]
    assert out["종가"].tolist() == [100, 110] and len(out) == 2


def test_layer3_index_fallback_uses_cached_index(monkeypatch, price_df):
    from models import layer3

    monkeypatch.setattr(krx_api, "index_close", lambda d: 2000.0 + d.day)
    idx = layer3._fetch_index_df(price_df)
    assert len(idx) == price_df["거래일자"].nunique() and np.isfinite(idx["종가"]).all()

    def boom(d):
        raise RuntimeError("no key")
    monkeypatch.setattr(krx_api, "index_close", boom)
    idx2 = layer3._fetch_index_df(price_df)
    assert idx2["종가"].isna().all()  # 실패 시 NaN 지수 (기존 정책)


def _http_error(status):
    r = requests.Response()
    r.status_code = status
    return requests.HTTPError(f"{status}", response=r)


def test_cached_gives_up_immediately_on_auth_denial(tmp_path, monkeypatch):
    """401·403은 기다려도 안 풀리는 권한 문제 — sleep 없이 즉시 예외, 캐시 파일 없음.
    (2026-09-25 코스피 지수 API 승인 만료 뒤 분석마다 재시도 5분이 낭비됐다.)"""
    monkeypatch.setattr(krx_api, "CACHE", tmp_path)

    def no_sleep(s):
        raise AssertionError(f"sleep({s}) 호출됨 — 권한 거절은 재시도하면 안 된다")
    monkeypatch.setattr(krx_api.time, "sleep", no_sleep)
    calls = []
    for status in (401, 403):
        def fetch():
            calls.append(status)
            raise _http_error(status)
        with pytest.raises(requests.HTTPError):
            krx_api._cached("index", f"2026{status}", fetch)
    assert calls == [401, 403]
    assert not list(tmp_path.rglob("*.parquet"))


def test_cached_still_retries_other_errors(tmp_path, monkeypatch):
    """500·네트워크 오류는 기존대로 재시도 — 두 번째에 성공하면 캐시한다."""
    monkeypatch.setattr(krx_api, "CACHE", tmp_path)
    slept = []
    monkeypatch.setattr(krx_api.time, "sleep", lambda s: slept.append(s))
    n = {"calls": 0}

    def fetch():
        n["calls"] += 1
        if n["calls"] == 1:
            raise _http_error(500)
        return pd.DataFrame({"종가": [1.0]})
    out = krx_api._cached("index", "20260101", fetch)
    assert n["calls"] == 2 and out["종가"].iloc[0] == 1.0
    assert slept[0] == 10
    assert (tmp_path / "index" / "20260101.parquet").exists()
