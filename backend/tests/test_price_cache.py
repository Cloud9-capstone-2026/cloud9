"""
price_cache 검증 — mock 카운터 방식 (벽시계 측정 없음, 2026-08-05 착수 기준).

fetcher를 호출 기록이 남는 가짜로 대체해 다음을 명시적으로 assert 한다:
  최초 요청 = 종목당 1회 / 동일 요청 반복 = 0회 / 부분 구간 확장 = 부족 구간만.
캐시 디렉터리는 tmp_path — 테스트 간·실환경과 완전 격리.
"""

import json
import threading
from datetime import date, timedelta

import numpy as np
import pandas as pd
import pytest

import price_cache
from price_cache import get_ohlcv


class FakeFetcher:
    """수식 기반 결정론 OHLCV + 호출 기록. scale로 '수정주가 소급 변경' 시뮬레이션."""

    def __init__(self, scale: float = 1.0):
        self.calls: list[tuple[str, date, date]] = []
        self.scale = scale

    def __call__(self, ticker: str, start: date, end: date) -> pd.DataFrame:
        self.calls.append((ticker, start, end))
        days = pd.bdate_range(start, end)
        if len(days) == 0:
            return pd.DataFrame(columns=["거래일자", "시가", "고가", "저가", "종가", "거래량"])
        t = np.array([d.toordinal() for d in days], dtype=float)
        close = np.round((10_000 + int(ticker) + (t % 97) * 10) * self.scale)
        return pd.DataFrame({
            "거래일자": days, "시가": close - 10, "고가": close + 20,
            "저가": close - 20, "종가": close, "거래량": np.full(len(days), 1000.0),
        })


@pytest.fixture()
def cache_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(price_cache, "CACHE_DIR", tmp_path)
    return tmp_path


S = date(2020, 3, 2)
E = date(2020, 5, 29)
TICKERS = ["000010", "000020"]


def test_first_request_one_call_per_ticker(cache_dir):
    f = FakeFetcher()
    out = get_ohlcv(TICKERS, S, E, fetcher=f)
    assert [c[0] for c in f.calls] == TICKERS  # 종목당 정확히 1회
    assert all(c[1] == S and c[2] == E for c in f.calls)
    assert set(out["종목코드"]) == set(TICKERS)
    assert list(out.columns) == price_cache._COLUMNS
    assert out["거래일자"].min() >= S and out["거래일자"].max() <= E


def test_repeat_request_zero_calls(cache_dir):
    f = FakeFetcher()
    a = get_ohlcv(TICKERS, S, E, fetcher=f)
    n_first = len(f.calls)
    b = get_ohlcv(TICKERS, S, E, fetcher=f)
    assert len(f.calls) == n_first  # 반복 요청 = 추가 호출 0
    pd.testing.assert_frame_equal(
        a.sort_values(["종목코드", "거래일자"]).reset_index(drop=True),
        b.sort_values(["종목코드", "거래일자"]).reset_index(drop=True),
    )


def test_partial_extension_fetches_missing_only(cache_dir):
    f = FakeFetcher()
    get_ohlcv(TICKERS, S, E, fetcher=f)
    n_first = len(f.calls)

    e2 = E + timedelta(days=30)
    out = get_ohlcv(TICKERS, S, e2, fetcher=f)
    ext_calls = f.calls[n_first:]
    assert len(ext_calls) == len(TICKERS)  # 종목당 부족 구간 1회
    for _tk, c_start, c_end in ext_calls:
        # 시작점은 부족 구간(E+1) 또는 소급 감지용 겹침 창(최대 OVERLAP_DAYS 이전)
        assert c_start >= E + timedelta(days=1) - timedelta(days=price_cache.OVERLAP_DAYS)
        assert c_start <= E + timedelta(days=1)
        assert c_end == e2
    assert out["거래일자"].max() > E  # 확장 구간 데이터 실제 포함


def test_coverage_is_request_range_not_row_dates(cache_dir):
    """요청 구간 끝이 주말(행 없음)이어도 반복 요청이 0회여야 한다 —
    커버 범위를 행 날짜로 정의하면 이 테스트가 깨진다(휴장일 결손 오판)."""
    f = FakeFetcher()
    e_sun = date(2020, 5, 31)  # 일요일 — 마지막 행은 5/29(금)
    get_ohlcv(["000010"], S, e_sun, fetcher=f)
    n_first = len(f.calls)
    get_ohlcv(["000010"], S, e_sun, fetcher=f)
    assert len(f.calls) == n_first


def test_corrupted_sidecar_refetches_safely(cache_dir):
    f = FakeFetcher()
    get_ohlcv(["000010"], S, E, fetcher=f)
    (cache_dir / "000010.json").write_text("{부서진 json", encoding="utf-8")
    out = get_ohlcv(["000010"], S, E, fetcher=f)
    assert len(f.calls) == 2  # 폐기 → 전체 1회 재조회
    assert len(out) > 0


def test_rows_outside_declared_range_discarded(cache_dir):
    """parquet 행이 sidecar 선언 구간 밖이면 불일치 — 폐기 후 재조회."""
    f = FakeFetcher()
    get_ohlcv(["000010"], S, E, fetcher=f)
    sc = cache_dir / "000010.json"
    side = json.loads(sc.read_text(encoding="utf-8"))
    side["ranges"] = [["2020-04-01", "2020-04-10"]]  # 행보다 좁은 구간으로 위조
    sc.write_text(json.dumps(side), encoding="utf-8")
    get_ohlcv(["000010"], S, E, fetcher=f)
    assert len(f.calls) == 2


def test_retroactive_adjustment_triggers_full_refetch(cache_dir):
    """겹침 창에서 종가가 달라지면(수정주가 소급 변경) 전체 재조회."""
    f1 = FakeFetcher(scale=1.0)
    get_ohlcv(["000010"], S, E, fetcher=f1)

    f2 = FakeFetcher(scale=2.0)  # 소급 변경된 세계
    out = get_ohlcv(["000010"], S, E + timedelta(days=30), fetcher=f2)
    # 겹침 대조 1회 + 전체 재조회 1회
    assert len(f2.calls) == 2
    assert f2.calls[-1][1] == S and f2.calls[-1][2] == E + timedelta(days=30)
    # 캐시가 새 스케일로 일관되게 교체됨 (구간별 혼합 오염 없음)
    first = out.sort_values("거래일자").iloc[0]
    assert first["종가"] == pytest.approx((10_000 + 10 + (S.toordinal() % 97) * 10) * 2.0)


def test_fetcher_failure_skips_ticker(cache_dir):
    f = FakeFetcher()

    def flaky(ticker, start, end):
        if ticker == "000020":
            raise RuntimeError("KRX down")
        return f(ticker, start, end)

    out = get_ohlcv(TICKERS, S, E, fetcher=flaky)
    assert set(out["종목코드"]) == {"000010"}  # 실패 종목만 빠짐


def test_concurrent_same_ticker_single_fetch(cache_dir):
    """같은 종목 동시 요청 — 종목별 lock으로 fetch는 1회만."""
    f = FakeFetcher()
    started = threading.Event()

    def slow(ticker, start, end):
        started.set()
        threading.Event().wait(0.2)  # fetch 지연 시뮬레이션
        return f(ticker, start, end)

    results = []
    threads = [threading.Thread(
        target=lambda: results.append(get_ohlcv(["000010"], S, E, fetcher=slow)))
        for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(f.calls) == 1  # 두 번째 스레드는 캐시 적중
    assert len(results) == 2 and all(len(r) for r in results)
