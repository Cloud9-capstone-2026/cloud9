"""
시장 전체 종목의 월별 복권성(LOTT) 순위표 생성 → data/lott_ranks.csv

왜: 실계좌 분석은 사용자 종목 몇 개의 시세만 갖고 있어 그 자리에서 LOTT를 계산하면
랭크 모집단이 사용자 종목뿐이고 FF3 요인 재료(시총·PBR)도 2020 스냅샷에 묶여 결측이
난다. 그래서 코스피+코스닥 전 종목 시세로 월별 순위표를 미리 만들어 두고, 추론과
합성 생성기 모두 (적용연, 적용월, 종목코드)로 찾기만 한다(학습·추론 동일 방식).

자료 출처 (전부 공식 API — KRX 웹사이트 자동 조회는 약관 위반·IP 차단이라 쓰지 않음):
- KRX Open API (synthetic_data/market/krx_api.py, .env KRX_API_KEY): 유가증권·코스닥
  일별매매정보(수정주가는 krx_api.adjust_prices로 보정)·종목기본정보·코스피 지수.
  날짜별 캐시 ml/cache/krx/ 는 생성기 시세(market_data)·실계좌 시세(price_cache)와 공유.
- OpenDART (.env OPENDART_API_KEY): 분기 재무상태표 자본총계 → PBR = 월말 시총/자본총계.
  분기 종료 후 3개월 뒤 월말부터 적용(공시 시차, 룩어헤드 방지). 일 1만 콜.

실행:  python ml/train/make_lott_table.py --start 2020-01 [--end 2026-08]
운영:  매월 초 1회 실행 → 새로 끝난 달이 추가된 CSV를 모델 Release 자산으로 교체
       (표는 커밋하지 않음). 받은 자료는 전부 캐시되므로 재실행 시 새 날짜만 요청한다.
       KRX Open API 서비스 승인에는 이용 기간이 있어 만료 시 재신청.

계산 규약은 synthetic_data.market.lott 와 동일(창 60거래일, 모멘텀 252/21, 창 내
관측 15일 미만 종목은 그 달 결측). 순위 모집단 = KCMI 22-02 p.24 정의 그대로
"SPAC 및 코넥스 제외, 유가증권·코스닥 보통주 및 우선주" — 소속부 SPAC만 걸러낸다
(코넥스는 주식 API에 없음). 실계좌의 우선주도 그대로 표에서 조회된다. 참고 옵션:
표에 없는 우선주가 생기면 같은 회사 보통주 순위로 대체하는 방법도 가능(미구현).
근사: 수정주가 보정은 분할·무상증자만(유상증자 권리락 이론가 미보정), 장부가는 분기
갱신, 비12월 결산 법인은 분기 매핑이 어긋날 수 있음(소수).
"""

import argparse
import io
import os
import sys
import time
import xml.etree.ElementTree as ET
import zipfile
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import requests

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO))

from synthetic_data.market import krx_api  # noqa: E402  (.env 로드 포함)
from synthetic_data.market.lott import apply_month_rank, compute_monthly_lott  # noqa: E402

OUT = _REPO / "data" / "lott_ranks.csv"
DART_API = "https://opendart.fss.or.kr/api/"
PACE_SEC = 0.2
WORKERS = 4

_cached = krx_api._cached  # 날짜/분기별 parquet 캐시 + 백오프 재시도 (ml/cache/krx/{kind}/)
_num = krx_api._num


def _month_end(y: int, m: int) -> date:
    return date(y + (m == 12), m % 12 + 1, 1) - timedelta(days=1)


def _add_months(y: int, m: int, k: int):
    n = y * 12 + (m - 1) + k
    return n // 12, n % 12 + 1


# ─────────────────────────── OpenDART (장부가) ───────────────────────────

def _dart(path: str, **params) -> requests.Response:
    r = requests.get(DART_API + path, params={"crtfc_key": os.environ["OPENDART_API_KEY"], **params}, timeout=60)
    r.raise_for_status()
    return r


def corp_codes() -> dict:
    """종목코드 -> DART 고유번호(corp_code). 상장사만. 1회 받아 캐시."""
    def fetch():
        z = zipfile.ZipFile(io.BytesIO(_dart("corpCode.xml").content))
        root = ET.fromstring(z.read(z.namelist()[0]))
        rows = [(c.findtext("stock_code", "").strip(), c.findtext("corp_code", "").strip())
                for c in root.iter("list")]
        return pd.DataFrame([r for r in rows if r[0]], columns=["종목코드", "corp_code"])
    df = _cached("dart", "corp_codes", fetch)
    return dict(zip(df["종목코드"], df["corp_code"]))


# 분기말 월 -> 보고서 코드 (1분기·반기·3분기·사업보고서)
_REPRT = {3: "11013", 6: "11012", 9: "11014", 12: "11011"}


def equity_by_quarter(year: int, qmonth: int, codes: list[str]) -> pd.Series:
    """분기말 (year, qmonth) 재무상태표 자본총계 {corp_code -> 원}. 연결(CFS) 우선, 없으면 개별(OFS).

    OpenDART 다중회사 주요계정 API — 회사 100개씩 1콜. 미공시·비12월결산 회사는 결측.
    """
    def fetch():
        out = {}
        for i in range(0, len(codes), 100):
            chunk = codes[i:i + 100]
            j = _dart("fnlttMultiAcnt.json", corp_code=",".join(chunk), bsns_year=str(year),
                      reprt_code=_REPRT[qmonth]).json()
            if j.get("status") not in ("000", "013"):  # 013 = 조회 결과 없음
                raise RuntimeError(f"DART {j.get('status')}: {j.get('message')}")
            for row in j.get("list", []):
                if row.get("sj_div") != "BS" or row.get("account_nm") != "자본총계":
                    continue
                key = (row["corp_code"], 0 if row.get("fs_div") == "CFS" else 1)
                out[key] = row.get("thstrm_amount", "")
            time.sleep(PACE_SEC)
        best = {}
        for (c, pri), v in sorted(out.items(), key=lambda kv: kv[0][1], reverse=True):
            best[c] = v  # CFS(0)가 마지막에 덮어써 우선
        return pd.DataFrame({"corp_code": list(best), "자본총계": _num(list(best.values()))})
    df = _cached("dart_equity", f"{year}{qmonth:02d}", fetch)
    return df.set_index("corp_code")["자본총계"]


def _latest_quarter(d: date) -> tuple[int, int]:
    """월말 d에 공시돼 있다고 볼 수 있는 최근 분기말 (연, 월) — 분기 종료 후 3개월 뒤 월말부터 적용.
    (1분기 보고서 제출기한 45일, 사업보고서 90일 — 둘 다 덮는 보수적 규칙, 룩어헤드 방지)"""
    y, m = _add_months(d.year, d.month, -3)
    qm = (m // 3) * 3  # 그 시점 이전 마지막 분기말 월
    return (y - 1, 12) if qm == 0 else (y, qm)


def month_pbr(d: date, tickers: list[str], caps: pd.Series) -> pd.Series:
    """월말 d 기준 PBR = 시총 / 공시된 최근 분기 자본총계. 자본총계 결측·0 이하는 NaN(요인 구축 제외)."""
    cmap = corp_codes()
    codes = sorted(set(cmap.values()))  # 상장사 전체 — 분기 캐시가 그 달 유니버스에 묶이지 않게
    y, qm = _latest_quarter(d)
    eq = equity_by_quarter(y, qm, codes)
    book = pd.Series([eq.get(cmap.get(t), float("nan")) for t in tickers], index=tickers, dtype=float)
    pbr = caps.reindex(tickers) / book
    return pbr.where(book > 0)


# ─────────────────────────── 본체 ───────────────────────────

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

    days = krx_api.prefetch(fetch_start, fetch_end)  # 캐시 채우기(4스레드) + 거래일 캘린더
    raw = krx_api.load_daily(days)
    price = krx_api.adjust_prices(raw)  # 분할·무상증자 보정 (실계좌·생성기와 같은 규약)
    price = price[price["거래량"] > 0][["종목코드", "거래일자", "종가", "시가총액"]]
    index_df = pd.DataFrame({"거래일자": days, "종가": [krx_api.index_close(d) for d in days]})
    print(f"거래일 {len(days)}일 ({days[0]} ~ {days[-1]})")

    # 계산 대상 달 = 시작월-1 ~ 종료월-1 중 끝난 달. 월말 스냅샷 = 그 달 마지막 거래일.
    month_last = {}
    for d in days:
        month_last[(d.year, d.month)] = d
    calc_months = []
    y, m = cy, cm
    while (y, m) in month_last and _month_end(y, m) <= fetch_end:
        calc_months.append((y, m))
        y, m = _add_months(y, m, 1)
    if not calc_months:
        sys.exit("계산할 달이 없습니다 (--start/--end 확인)")

    # DART 분기 자본총계를 먼저 병렬로 캐시 (분기당 약 40콜 × 30분기 — 순차면 12분).
    all_codes = sorted(set(corp_codes().values()))
    quarters = sorted({_latest_quarter(month_last[ym]) for ym in calc_months})
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        list(ex.map(lambda q: equity_by_quarter(q[0], q[1], all_codes), quarters))

    snapshots, universe_by_month = {}, {}
    for (y, m) in calc_months:
        d = month_last[(y, m)]
        info = krx_api.base_info(d)
        ok = ~info["소속부"].str.contains("SPAC")  # KCMI 정의: SPAC만 제외 (보통주+우선주, 리츠·외국주권 포함)
        tickers = info.loc[ok, "종목코드"].tolist()
        kosdaq = set(info.loc[ok & (info["시장"] == "KOSDAQ"), "종목코드"])
        caps = price[price["거래일자"] == d].set_index("종목코드")["시가총액"].reindex(tickers)
        snapshots[(y, m)] = (caps, month_pbr(d, tickers, caps), kosdaq)
        universe_by_month[(y, m)] = tickers
    print(f"계산 달 {len(snapshots)}개: {min(snapshots)} ~ {max(snapshots)}")
    if all(s[1].isna().all() for s in snapshots.values()):
        print("경고: PBR 없음 — HML 요인 없이 계산됨")

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
