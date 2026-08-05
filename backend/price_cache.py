"""
시세 조회 캐시 (단계 2-1) — 종목별 parquet + sidecar 증분 캐시.

분석마다 종목별 순차 pykrx 호출(150일 룩백)을 반복하던 것을, 조회 성공 구간을
로컬에 쌓아 부족한 구간만 받아오게 한다. 분석 속도 개선 + KRX 장애 의존 완화.

설계 (2026-08-05 착수 기준 반영):
- 커버 범위의 정의 = "조회에 성공한 요청 구간"(sidecar의 ranges). 행의 최소/최대
  날짜가 아니다 — 휴장일·주말로 행이 없는 구간을 결손으로 오판하지 않기 위함.
- 동시성: 종목별 threading.Lock. 2-2의 BackgroundTasks worker가 스레드풀에서
  돌므로 같은 종목 동시 접근이 실제로 발생한다.
- 원자성: parquet·sidecar 모두 임시파일 → os.replace 교체. 부분 쓰기가 정본이
  되지 않는다.
- 정합: sidecar 스키마 불일치·파일 손상·행 날짜가 선언 구간 밖이면 그 종목
  캐시를 폐기하고 재조회한다.
- 수정주가 소급 변경 감지: KRX 수정주가는 기업행위(분할·증자)로 과거 값이 통째로
  바뀔 수 있다(2026-08-05 데이터 손실 복구 과정에서 실측). 기존 커버 구간에
  이어붙일 때 직전 OVERLAP_DAYS 만큼 겹쳐 받아 캐시와 대조하고, 불일치면 그
  종목을 전체 재조회한다. (겹침이 없는 옛 구간의 소급 변경은 감지 범위 밖 —
  알려진 한계로 문서화.)
- fetcher 주입: pykrx 호출은 fetcher(ticker, start, end) 함수로 분리 — 테스트가
  mock 카운터로 대체해 호출 횟수·구간을 검증한다.

공개 API:
  get_ohlcv(tickers, start, end, fetcher=None) -> DataFrame
    market_data 스키마(종목코드·거래일자(date)·시가·고가·저가·종가·거래량).
    조회 실패 종목은 건너뜀(빈 결과 가능) — 호출부(layer3)의 기존 실패 정책 유지.
"""

import json
import logging
import os
import threading
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

_SCHEMA_VER = "v1"
_COLUMNS = ["종목코드", "거래일자", "시가", "고가", "저가", "종가", "거래량"]

# 수정주가 소급 변경 감지용 겹침 창 (캘린더 일수)
OVERLAP_DAYS = 10

CACHE_DIR = Path(os.environ.get(
    "CANARY_PRICE_CACHE_DIR", Path(__file__).resolve().parent / ".price_cache"))

_locks_guard = threading.Lock()
_locks: dict[str, threading.Lock] = {}


def _lock_for(ticker: str) -> threading.Lock:
    with _locks_guard:
        if ticker not in _locks:
            _locks[ticker] = threading.Lock()
        return _locks[ticker]


# ─────────────────────────── 날짜 구간 연산 ───────────────────────────
# ranges = [(start, end)] date 튜플 목록, 폐구간, 정렬·병합 상태 유지

def _merge_ranges(ranges: list[tuple[date, date]]) -> list[tuple[date, date]]:
    out: list[tuple[date, date]] = []
    for s, e in sorted(ranges):
        if out and s <= out[-1][1] + timedelta(days=1):  # 겹침·인접 병합
            out[-1] = (out[-1][0], max(out[-1][1], e))
        else:
            out.append((s, e))
    return out


def _gaps(ranges: list[tuple[date, date]], start: date, end: date
          ) -> list[tuple[date, date]]:
    """[start, end] 중 ranges가 커버하지 않는 부분 구간들."""
    gaps = []
    cur = start
    for s, e in ranges:
        if e < cur:
            continue
        if s > end:
            break
        if s > cur:
            gaps.append((cur, min(s - timedelta(days=1), end)))
        cur = max(cur, e + timedelta(days=1))
        if cur > end:
            return gaps
    if cur <= end:
        gaps.append((cur, end))
    return gaps


# ─────────────────────────── 저장/적재 ───────────────────────────

def _paths(ticker: str) -> tuple[Path, Path]:
    return CACHE_DIR / f"{ticker}.parquet", CACHE_DIR / f"{ticker}.json"


def _load(ticker: str) -> tuple[pd.DataFrame | None, list[tuple[date, date]]]:
    """캐시 적재. 손상·정합 위반이면 (None, []) — 폐기 후 재조회 유도."""
    pq, sc = _paths(ticker)
    if not (pq.exists() and sc.exists()):
        return None, []
    try:
        with open(sc, encoding="utf-8") as fp:
            side = json.load(fp)
        if side.get("schema") != _SCHEMA_VER:
            raise ValueError(f"sidecar 스키마 불일치: {side.get('schema')}")
        ranges = [(date.fromisoformat(s), date.fromisoformat(e))
                  for s, e in side["ranges"]]
        df = pd.read_parquet(pq)
        if list(df.columns) != _COLUMNS:
            raise ValueError("parquet 컬럼 불일치")
        df["거래일자"] = pd.to_datetime(df["거래일자"]).dt.date  # 저장은 datetime64
        days = df["거래일자"]
        if len(df) and not all(
            any(s <= d <= e for s, e in ranges) for d in (days.min(), days.max())
        ):
            raise ValueError("행 날짜가 선언 구간 밖 — sidecar/parquet 불일치")
        return df, ranges
    except Exception as e:  # noqa: BLE001 — 어떤 손상이든 폐기가 안전
        logger.warning("price_cache %s 손상 — 폐기 후 재조회: %r", ticker, e)
        return None, []


def _store(ticker: str, df: pd.DataFrame, ranges: list[tuple[date, date]]) -> None:
    """임시파일 → os.replace 원자 교체. parquet 먼저, sidecar 나중
    (교체 사이에 죽으면 '행 ⊆ 구간' 검사로 다음 적재 때 폐기된다)."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    pq, sc = _paths(ticker)
    df = df.sort_values("거래일자").reset_index(drop=True)

    tmp_pq = pq.with_suffix(".parquet.tmp")
    out = df.copy()
    out["거래일자"] = pd.to_datetime(out["거래일자"])  # parquet 호환
    out.to_parquet(tmp_pq, index=False)
    os.replace(tmp_pq, pq)

    tmp_sc = sc.with_suffix(".json.tmp")
    with open(tmp_sc, "w", encoding="utf-8") as fp:
        json.dump({"schema": _SCHEMA_VER,
                   "ranges": [[s.isoformat(), e.isoformat()] for s, e in ranges]},
                  fp, ensure_ascii=False)
    os.replace(tmp_sc, sc)


def _normalize(raw: pd.DataFrame, ticker: str) -> pd.DataFrame:
    """fetcher 반환(거래일자·시가·고가·저가·종가·거래량) → 캐시 스키마.
    거래정지(거래량 0) 행 제거 — market_data와 동일 정책."""
    if raw is None or len(raw) == 0:
        return pd.DataFrame(columns=_COLUMNS)
    df = raw.copy()
    df["거래일자"] = pd.to_datetime(df["거래일자"]).dt.date
    df = df[df["거래량"] > 0]
    df["종목코드"] = ticker
    return df[_COLUMNS].reset_index(drop=True)


def _default_fetcher(ticker: str, start: date, end: date) -> pd.DataFrame:
    """pykrx 수정주가 OHLCV. layer3 기존 경로와 동일 파라미터."""
    from synthetic_data.net import ensure_timeout_patch
    ensure_timeout_patch()
    from pykrx import stock

    df = stock.get_market_ohlcv(
        start.strftime("%Y%m%d"), end.strftime("%Y%m%d"), ticker, adjusted=True)
    if df is None or df.empty:
        return pd.DataFrame(columns=["거래일자", "시가", "고가", "저가", "종가", "거래량"])
    return pd.DataFrame({
        "거래일자": pd.to_datetime(df.index),
        "시가": df["시가"].values, "고가": df["고가"].values,
        "저가": df["저가"].values, "종가": df["종가"].values,
        "거래량": df["거래량"].values,
    })


# ─────────────────────────── 조회 본체 ───────────────────────────

def _overlap_mismatch(cached: pd.DataFrame, fresh: pd.DataFrame,
                      lo: date, hi: date) -> bool:
    """[lo, hi] 겹침 창에서 캐시와 새 조회의 (날짜 집합, 종가, 거래량) 대조."""
    c = cached[(cached["거래일자"] >= lo) & (cached["거래일자"] <= hi)]
    f = fresh[(fresh["거래일자"] >= lo) & (fresh["거래일자"] <= hi)]
    if set(c["거래일자"]) != set(f["거래일자"]):
        return True
    if len(c) == 0:
        return False
    m = c.set_index("거래일자")[["종가", "거래량"]].join(
        f.set_index("거래일자")[["종가", "거래량"]], rsuffix="_new")
    return bool((m["종가"] != m["종가_new"]).any()
                or (m["거래량"] != m["거래량_new"]).any())


def _get_one(ticker: str, start: date, end: date, fetcher) -> pd.DataFrame:
    df, ranges = _load(ticker)
    gaps = _gaps(ranges, start, end)

    if gaps:
        pieces = [] if df is None else [df]
        new_ranges = list(ranges)
        refetch_full = False
        for g0, g1 in gaps:
            # 기존 커버 구간에 이어붙이는 경우: 겹침 창으로 소급 수정 감지.
            # 겹침 창은 인접 커버 구간 안으로만 한정(다른 구간의 결손을 불일치로
            # 오판하지 않게).
            f0 = g0
            adj = [s for s, e in ranges if e == g0 - timedelta(days=1)]
            if df is not None and adj:
                f0 = max(g0 - timedelta(days=OVERLAP_DAYS), adj[0])
            fresh = _normalize(fetcher(ticker, f0, g1), ticker)
            if f0 < g0 and _overlap_mismatch(df, fresh, f0, g0 - timedelta(days=1)):
                logger.warning("price_cache %s 수정주가 소급 변경 감지 — 전체 재조회",
                               ticker)
                refetch_full = True
                break
            pieces.append(fresh[fresh["거래일자"] >= g0])
            new_ranges.append((g0, g1))
        if refetch_full:
            df = _normalize(fetcher(ticker, start, end), ticker)
            new_ranges = [(start, end)]
        else:
            df = pd.concat([p for p in pieces if len(p)], ignore_index=True) \
                if any(len(p) for p in pieces) else pd.DataFrame(columns=_COLUMNS)
        _store(ticker, df, _merge_ranges(new_ranges))

    if df is None or len(df) == 0:
        return pd.DataFrame(columns=_COLUMNS)
    return df[(df["거래일자"] >= start) & (df["거래일자"] <= end)]


def get_ohlcv(tickers, start: date, end: date, fetcher=None) -> pd.DataFrame:
    """종목들의 [start, end] OHLCV — 캐시 우선, 부족 구간만 fetcher 호출.

    조회 실패 종목은 경고 후 건너뜀(해당 종목 시장 컨텍스트 결측 → 마스크,
    layer3 기존 정책). 전 종목 실패면 빈 DataFrame."""
    fetcher = fetcher or _default_fetcher
    frames = []
    for tk in tickers:
        try:
            with _lock_for(tk):
                got = _get_one(tk, start, end, fetcher)
        except Exception as e:  # noqa: BLE001 — 종목 단위 격리
            logger.warning("price_cache %s 조회 실패 — 건너뜀: %r", tk, e)
            continue
        if len(got):
            frames.append(got)
    if not frames:
        return pd.DataFrame(columns=_COLUMNS)
    return pd.concat(frames, ignore_index=True)
