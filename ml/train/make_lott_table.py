"""
시장 전체 종목의 월별 복권성(LOTT) 순위표 생성 → data/lott_ranks.csv

왜: 실계좌 분석은 사용자 종목 몇 개의 시세만 갖고 있어 그 자리에서 LOTT를 계산하면
랭크 모집단이 사용자 종목뿐이고 FF3 요인 재료(시총·PBR)도 2020 스냅샷에 묶여 결측이
난다. 그래서 코스피+코스닥 전 종목 시세로 월별 순위표를 미리 만들어 두고, 추론과
합성 생성기 모두 (적용연, 적용월, 종목코드)로 찾기만 한다(학습·추론 동일 방식).

자료 출처 (전부 공식 API — KRX 웹사이트 자동 조회는 약관 위반·IP 차단이라 쓰지 않음):
- KRX Open API (openapi.krx.co.kr, .env KRX_API_KEY): 유가증권·코스닥 일별매매정보
  (종가·거래량·시총), 종목기본정보(주식종류·증권그룹·소속부), 코스피 지수. 일 1만 콜.
- OpenDART (.env OPENDART_API_KEY): 자본총계 → PBR = 시총/자본총계  [L-2b에서 연결]

실행:  python ml/train/make_lott_table.py --start 2020-01 [--end 2026-08]
운영:  매월 초 1회 실행 → 새로 끝난 달이 추가된 CSV를 커밋. 받은 자료는 전부
       ml/cache/lott_raw/ 에 날짜별로 캐시되므로 재실행 시 새 날짜만 요청한다.
       KRX Open API 서비스 승인에는 이용 기간이 있어 만료 시 재신청.

계산 규약은 synthetic_data.market.lott 와 동일(창 60거래일, 모멘텀 252/21, 창 내
관측 15일 미만 종목은 그 달 결측). 순위 모집단 = 그 달 코스피+코스닥의
주식종류 '보통주' ∧ 증권그룹 '주권' ∧ 소속부 SPAC 아님(우선주·리츠·외국주권·코넥스 제외).
근사: 전종목 일별 시세는 수정주가가 아니라 액면분할·증자일의 수익률이 튄다. KRX
    가격제한폭(±30%)으로 그런 날은 드물고 해당 종목의 그 달 전후 변동성만 과대
    평가되므로 보정 없이 둔다.
"""

import argparse
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO))
load_dotenv(_REPO / ".env")

from synthetic_data.market.lott import apply_month_rank, compute_monthly_lott  # noqa: E402

CACHE = _REPO / "ml" / "cache" / "lott_raw"
OUT = _REPO / "data" / "lott_ranks.csv"
KRX_API = "https://data-dbg.krx.co.kr/svc/apis/"
PACE_SEC = 0.2  # 호출 간격 (일 1만 콜 한도와 별개로 서버 부담 완화)
WORKERS = 4  # 캐시 채우기 동시 요청 수


def _cached(kind: str, key: str, fetch):
    """kind/key.parquet 이 있으면 읽고 없으면 fetch()로 받아 저장. 실패는 백오프 재시도."""
    path = CACHE / kind / f"{key}.parquet"
    if path.exists():
        return pd.read_parquet(path)
    for wait in (10, 30, 60, 180, None):
        try:
            df = fetch()
            break
        except Exception as e:  # noqa: BLE001 — 네트워크·JSON·한도 초과 등
            if wait is None:
                raise
            print(f"  {kind}/{key} 실패({type(e).__name__}: {e}) — {wait}초 후 재시도", flush=True)
            time.sleep(wait)
    time.sleep(PACE_SEC)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path)
    return df


def _krx(path: str, bas_dd: str) -> list[dict]:
    r = requests.get(KRX_API + path, params={"basDd": bas_dd},
                     headers={"AUTH_KEY": os.environ["KRX_API_KEY"]}, timeout=30)
    r.raise_for_status()
    return r.json()["OutBlock_1"]


def _num(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s.astype(str).str.replace(",", ""), errors="coerce")


def _ymd(d: date) -> str:
    return d.strftime("%Y%m%d")


def _month_end(y: int, m: int) -> date:
    return date(y + (m == 12), m % 12 + 1, 1) - timedelta(days=1)


def _add_months(y: int, m: int, k: int):
    n = y * 12 + (m - 1) + k
    return n // 12, n % 12 + 1


def daily_prices(d: date) -> pd.DataFrame:
    """코스피+코스닥 전 종목 그날 시세. 휴장일이면 빈 DataFrame(캐시됨 — 캘린더 역할)."""
    def fetch():
        s = _ymd(d)
        rows = _krx("sto/stk_bydd_trd", s) + _krx("sto/ksq_bydd_trd", s)
        if not rows:
            return pd.DataFrame(columns=["종목코드", "종가", "거래량", "시가총액"])
        raw = pd.DataFrame(rows)
        return pd.DataFrame({
            "종목코드": raw["ISU_CD"].astype(str),
            "종가": _num(raw["TDD_CLSPRC"]),
            "거래량": _num(raw["ACC_TRDVOL"]),
            "시가총액": _num(raw["MKTCAP"]),
        })
    return _cached("krx_daily", _ymd(d), fetch)


def index_close(d: date) -> float:
    def fetch():
        rows = [r for r in _krx("idx/kospi_dd_trd", _ymd(d)) if r["IDX_NM"] == "코스피"]
        if not rows:
            raise RuntimeError(f"{d} 코스피 지수 행 없음")
        return pd.DataFrame({"종가": [float(str(rows[0]["CLSPRC_IDX"]).replace(",", ""))]})
    return float(_cached("krx_index", _ymd(d), fetch)["종가"].iloc[0])


def base_info(d: date) -> pd.DataFrame:
    """그날의 종목기본정보(월말 스냅샷용): 종목코드·보통주·주권·스팩·코스닥."""
    def fetch():
        s = _ymd(d)
        raw = pd.DataFrame(_krx("sto/stk_isu_base_info", s) + _krx("sto/ksq_isu_base_info", s))
        return pd.DataFrame({
            "종목코드": raw["ISU_SRT_CD"].astype(str),
            "보통주": raw["KIND_STKCERT_TP_NM"] == "보통주",
            "주권": raw["SECUGRP_NM"] == "주권",
            "스팩": raw["SECT_TP_NM"].astype(str).str.contains("SPAC"),
            "코스닥": raw["MKT_TP_NM"] == "KOSDAQ",
        })
    return _cached("krx_base", _ymd(d), fetch)


def month_pbr(d: date, tickers: list[str], caps: pd.Series) -> pd.Series:
    """월말 d 기준 PBR = 시총 / 공시된 최근 분기 자본총계. [L-2b: OpenDART 연결 예정]"""
    return pd.Series(float("nan"), index=tickers)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--start", default="2020-01", help="순위표 첫 적용월 YYYY-MM")
    ap.add_argument("--end", default=None, help="마지막 적용월 YYYY-MM (기본: 이번 달)")
    ap.add_argument("--out", default=str(OUT))
    a = ap.parse_args()
    today = date.today()
    sy, sm = map(int, a.start.split("-"))
    ey, em = map(int, a.end.split("-")) if a.end else (today.year, today.month)

    # 적용월 M의 랭크는 M-1 달 말에 계산 → 계산 첫 달 = 시작월-1.
    # 룩백 = 창 60 + 모멘텀 273(lott.py _MOM_LONG+_MOM_SKIP) ≈ 333거래일 → 여유 있게 20개월 전부터.
    cy, cm = _add_months(sy, sm, -1)
    fetch_start = _month_end(*_add_months(cy, cm, -20))
    fetch_end = min(_month_end(*_add_months(ey, em, -1)), today - timedelta(days=1))

    # 평일마다 시세 요청 — 빈 응답이면 휴장일. 거래일 캘린더는 여기서 나온다.
    # 호출당 1~2초라 캐시 채우기는 스레드 4개로 (한도는 일 콜 수 기준, 동시성 제한 없음).
    weekdays = [fetch_start + timedelta(days=i) for i in range((fetch_end - fetch_start).days + 1)]
    weekdays = [d for d in weekdays if d.weekday() < 5]

    def fill(d):
        if len(daily_prices(d)):
            index_close(d)
        return d

    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        for i, _ in enumerate(ex.map(fill, weekdays), 1):
            if i % 100 == 0:
                print(f"  수집 {i}/{len(weekdays)}일", flush=True)

    frames, days, idx_rows = [], [], []
    for d in weekdays:
        df = daily_prices(d)
        if len(df):
            days.append(d)
            df = df[df["거래량"] > 0]  # 거래정지일 제거 (market_data.py와 동일 규약)
            frames.append(df.assign(거래일자=d))
            idx_rows.append({"거래일자": d, "종가": index_close(d)})
    price = pd.concat(frames, ignore_index=True)
    index_df = pd.DataFrame(idx_rows)
    print(f"거래일 {len(days)}일 ({days[0]} ~ {days[-1]})")

    # 계산 대상 달 = 시작월-1 ~ 종료월-1 중 끝난 달. 월말 스냅샷 = 그 달 마지막 거래일.
    month_last = {}
    for d in days:
        month_last[(d.year, d.month)] = d
    snapshots, universe_by_month = {}, {}
    y, m = cy, cm
    while (y, m) in month_last and _month_end(y, m) <= fetch_end:
        d = month_last[(y, m)]
        info = base_info(d)
        ok = info["보통주"] & info["주권"] & ~info["스팩"]
        tickers = info.loc[ok, "종목코드"].tolist()
        kosdaq = set(info.loc[ok & info["코스닥"], "종목코드"])
        caps = price[price["거래일자"] == d].set_index("종목코드")["시가총액"].reindex(tickers)
        snapshots[(y, m)] = (caps, month_pbr(d, tickers, caps), kosdaq)
        universe_by_month[(y, m)] = tickers
        y, m = _add_months(y, m, 1)
    if not snapshots:
        sys.exit("계산할 달이 없습니다 (--start/--end 확인)")
    print(f"계산 달 {len(snapshots)}개: {min(snapshots)} ~ {max(snapshots)}")
    if all(s[1].isna().all() for s in snapshots.values()):
        print("경고: PBR 없음 — HML 요인 없이 계산됨 (L-2b 전 트라이얼 전용)")

    all_tickers = sorted({t for ts in universe_by_month.values() for t in ts})
    price = price[price["종목코드"].isin(all_tickers)]
    monthly = compute_monthly_lott(price[["종목코드", "거래일자", "종가"]], index_df, all_tickers, snapshots)
    # 순위 모집단을 그 달 유니버스로 한정(상장폐지·시장 이동 등 그 달에 없는 종목 제외).
    monthly = {k: {t: v for t, v in sc.items() if t in set(universe_by_month[k])} for k, sc in monthly.items()}
    ranks = apply_month_rank(monthly)

    rows = []
    for (ay, am), s in sorted(ranks.items()):
        n_univ = len(universe_by_month[_add_months(ay, am, -1)])
        print(f"  적용 {ay}-{am:02d}: 랭크 {len(s)}종목 / 모집단 {n_univ} (결측 {1 - len(s) / n_univ:.1%})")
        rows.append(pd.DataFrame({"적용연": ay, "적용월": am, "종목코드": s.index, "lott_rank": s.values.round(6)}))
    out = pd.concat(rows, ignore_index=True)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(a.out, index=False, encoding="utf-8")
    print(f"저장: {a.out} ({len(out)}행)")


if __name__ == "__main__":
    main()
