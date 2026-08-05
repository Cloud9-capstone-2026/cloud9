"""
유니버스 재생성 스크립트 (유지보수용, 일회성 실행).

config.UNIVERSE_TICKERS를 만들 때 쓴 도구. 시가총액 API(get_market_cap_by_ticker)는
KRX 정보데이터시스템 로그인이 필요하므로, 저장소 루트의 .env에서 KRX_ID/KRX_PW를
python-dotenv로 로드한다. (정상 실행 경로인 get_price_data는 공개 OHLCV라 자격증명 불필요.)

실행:  python -m synthetic_data.market.regenerate_universe
출력:  (1) config.SIM_START_DATE 기준 KOSPI 시총 상위 N개를 종목명과 함께 출력하고,
           config.UNIVERSE_TICKERS에 붙여넣을 파이썬 리스트 블록.
       (2) 현재 config.UNIVERSE_TICKERS 각 종목의 시가총액을 뽑아
           config.MARKETCAP_20200302에 붙여넣을 dict 블록(초과보유비중 벤치마크용).
       (3) 각 종목의 기관+외국인 거래대금(시뮬 기간 합산)을 뽑아
           config.INST_FOREIGN_TRADEVALUE에 붙여넣을 dict 블록(초과거래비중 벤치마크용).
           KCMI 그림 Ⅳ-13의 벤치마크 = "개인 제외 기관·외국인 거래비중"에 대응.

주의: config를 자동으로 덮어쓰지 않는다 — 리스트/딕셔너리를 '제안'만 한다(정적 프리즈
      원칙: 사람이 확인하고 붙여넣는다).
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# 저장소 루트의 .env(= 이 파일 기준 세 단계 위)를 명시적으로 로드 → cwd와 무관하게 동작.
_ENV_PATH = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(_ENV_PATH)

if not os.environ.get("KRX_ID") or not os.environ.get("KRX_PW"):
    raise SystemExit(
        f"KRX_ID/KRX_PW를 찾을 수 없습니다. {_ENV_PATH} 에 두 값이 설정돼 있는지 확인하세요."
    )

import time  # noqa: E402

from pykrx import stock  # noqa: E402  (dotenv 로드 후 import)

from .. import config  # noqa: E402

# pykrx가 requests에 timeout을 안 걸어 KRX 무응답 시 무한 행(hang)에 빠질 수 있다
# (6-1에서 실제 발생: 30분 CPU 정지). 전역 기본 timeout 패치는 net.py로 통합.
from ..net import ensure_timeout_patch  # noqa: E402

ensure_timeout_patch()

MARKET = "KOSPI"
TOP_N = 30

# --- 6-1 계층화 샘플링 설정 ---
STRAT_TOTAL = 200          # 목표 종목 수
STRAT_QUANTILES = 5        # 시총 분위 수 (KOSPI+KOSDAQ 합산 기준)
STRAT_SEED = 42            # 샘플링 재현용
# 생존 정책(승인됨): 전 기간 데이터 존재 종목만 — 생존편향 수용·명시.
# 커버리지 판정은 아래 3개 거래일의 시장 전체 스냅샷 교집합으로 근사 —
# 종목당 OHLCV를 수백 회 fetch하는 방식은 KRX 쓰로틀링/무한 행으로 실패(실측).
COVERAGE_SNAPSHOT_DATES = ["20191104", "20200602", "20201026"]  # 시작·중간·끝 거래일


def _covered_tickers() -> set:
    """전 기간 커버리지 근사: 3개 날짜의 시장 전체 OHLCV 스냅샷(거래량>0)에 모두
    존재하는 종목 집합. 총 6콜. (하필 그날 거래정지인 종목이 탈락하는 미세 과잉배제는
    수용 — 생존 정책 자체가 근사임을 이미 명시.)"""
    sets = []
    for d in COVERAGE_SNAPSHOT_DATES:
        s: set = set()
        for mkt in ("KOSPI", "KOSDAQ"):
            df = stock.get_market_ohlcv_by_ticker(d, market=mkt)
            if df.empty:
                raise SystemExit(f"스냅샷 {d} {mkt} 비어 있음 — 네트워크/날짜 확인.")
            s |= set(df[df["거래량"] > 0].index)
            time.sleep(0.3)
        sets.append(s)
        print(f"# 스냅샷 {d}: {len(s)}종목", flush=True)
    covered = sets[0] & sets[1] & sets[2]
    print(f"# 3일 교집합(커버리지 통과): {len(covered)}종목", flush=True)
    return covered


def stratified_universe() -> list[str]:
    """KOSPI+KOSDAQ 시총 5분위 × 시장(10셀) 비례 계층화 샘플링 (6-1).

    KCMI 표본(양 시장 보통주+우선주, SPAC·코넥스 제외)과 정합. 시총 상위 확장만으론
    소형주·복권형 스프레드가 안 벌어지므로 전 분위를 비례 대표. 셀 내 무작위(시드 고정),
    커버리지 탈락 시 같은 셀에서 재추출(생존편향 수용·명시).
    """
    import random as _random

    import pandas as pd

    date = config.SIM_START_DATE
    frames = []
    for mkt in ("KOSPI", "KOSDAQ"):
        cap = stock.get_market_cap_by_ticker(date, market=mkt)
        if cap.empty:
            raise SystemExit(f"{mkt} 시총 비어 있음 — KRX 로그인 확인.")
        f = cap[["시가총액"]].copy()
        f["시장"] = mkt
        frames.append(f)
    allcap = pd.concat(frames)
    # 시총 분위: 양 시장 합산 기준 (KOSDAQ이 하위 분위에 자연스럽게 몰림)
    allcap["분위"] = pd.qcut(allcap["시가총액"].rank(method="first"),
                           STRAT_QUANTILES, labels=False)

    rng = _random.Random(STRAT_SEED)
    total = len(allcap)
    covered = _covered_tickers()
    picked: list[str] = []
    print(f"# 계층화 샘플링: 후보 {total}종목 → 목표 {STRAT_TOTAL}", flush=True)
    for (mkt, q), cell in allcap.groupby(["시장", "분위"]):
        quota = round(STRAT_TOTAL * len(cell) / total)
        cands = [t for t in cell.index if t in covered]
        rng.shuffle(cands)
        got = 0
        for t in cands:
            if got >= quota:
                break
            name = stock.get_market_ticker_name(t)
            time.sleep(0.05)
            if not isinstance(name, str) or "스팩" in name:
                continue  # SPAC 제외 (KCMI와 동일)
            picked.append(t)
            got += 1
        print(f"#   {mkt} 분위{q}: {got}/{quota} (셀 {len(cell)}, 커버 {len(cands)})",
              flush=True)
    return picked


def dump_frozen(tickers: list[str], write: bool):
    """선정 유니버스의 시총·기관외국인 거래대금까지 뽑아 universe_frozen.py 생성."""
    date = config.SIM_START_DATE
    caps = {}
    for mkt in ("KOSPI", "KOSDAQ"):
        c = stock.get_market_cap_by_ticker(date, market=mkt)
        for t in tickers:
            if t in c.index:
                caps[t] = int(c.loc[t, "시가총액"])

    inst = {}
    for i, t in enumerate(tickers):
        for attempt in (1, 2):  # timeout 등 일시 오류 1회 재시도
            try:
                inv = stock.get_market_trading_value_by_investor(
                    config.SIM_START_DATE, config.SIM_END_DATE, t
                )
                rows = [r for r in ("기관합계", "외국인", "기타외국인") if r in inv.index]
                if rows:
                    inst[t] = int(
                        inv.loc[rows, "매도"].sum() + inv.loc[rows, "매수"].sum()
                    )
                break
            except Exception as e:  # noqa: BLE001
                if attempt == 2:
                    print(f"#   {t} 실패(2회): {e!r} — 건너뜀", flush=True)
                else:
                    time.sleep(2.0)
        time.sleep(0.2)  # KRX 쓰로틀링 방지
        if (i + 1) % 25 == 0:
            print(f"#   기관외국인 거래대금 {i + 1}/{len(tickers)}", flush=True)

    lines = [
        '"""6-1 계층화 유니버스 프리즈 데이터 (생성 모듈 — 손으로 편집 금지).',
        "",
        "regenerate_universe.py --stratified --write 로 생성. KOSPI+KOSDAQ 시총 5분위",
        f"비례 샘플링(시드 {STRAT_SEED}), SPAC 제외, 전 기간 커버리지 필터(생존편향 수용·명시).",
        f"기준일 {date}. config가 import해 재노출한다.",
        '"""',
        "",
        f"UNIVERSE_TICKERS = {tickers!r}",
        "",
        f"MARKETCAP_20200302 = {caps!r}",
        "",
        f"INST_FOREIGN_TRADEVALUE = {inst!r}",
        "",
    ]
    body = "\n".join(lines)
    if write:
        out = Path(__file__).resolve().parent / "universe_frozen.py"
        out.write_text(body, encoding="utf-8")
        print(f"# 저장: {out} (종목 {len(tickers)}, 시총 {len(caps)}, 기관외 {len(inst)})")
    else:
        print(body)


def main():
    date = config.SIM_START_DATE
    cap = stock.get_market_cap_by_ticker(date, market=MARKET)
    if cap.empty:
        raise SystemExit(
            "시가총액 데이터가 비어 있습니다 — KRX 로그인 실패(자격증명/네트워크) 가능성."
        )

    codes = list(cap.sort_values("시가총액", ascending=False).head(TOP_N).index)

    print(f"# {date} 기준 {MARKET} 시가총액 상위 {TOP_N}")
    for code in codes:
        print(f"#   {code}  {stock.get_market_ticker_name(code)}")

    print("\n# ↓ config.py의 UNIVERSE_TICKERS에 붙여넣기")
    print("UNIVERSE_TICKERS = [")
    for i in range(0, len(codes), 6):
        row = ", ".join(f'"{c}"' for c in codes[i : i + 6])
        print(f"    {row},")
    print("]")

    # (2) 현재 프리즈된 유니버스 각 종목의 시총 → 초과보유비중(그림 Ⅳ-12) 벤치마크 dict.
    #     상위 N과 별개로, 실제 시뮬이 쓰는 config.UNIVERSE_TICKERS 기준으로 뽑는다.
    print(f"\n# ↓ config.py의 MARKETCAP_20200302에 붙여넣기 ({date} 기준, 원 단위)")
    print("MARKETCAP_20200302 = {")
    for code in config.UNIVERSE_TICKERS:
        if code in cap.index:
            print(f'    "{code}": {int(cap.loc[code, "시가총액"])},')
        else:
            print(f'    # "{code}": 시총 데이터 없음 — 확인 필요')
    print("}")

    # (3) 기관+외국인 거래대금(시뮬 기간 합산) → 초과거래비중(그림 Ⅳ-13) 벤치마크 dict.
    #     get_market_trading_value_by_investor: 종목별·투자자유형별 매도/매수 거래대금.
    #     벤치마크 = 기관합계 + 외국인 + 기타외국인의 (매도+매수). 개인·기타법인 제외.
    dfrom, dto = config.SIM_START_DATE, config.SIM_END_DATE
    print(
        f"\n# ↓ config.py의 INST_FOREIGN_TRADEVALUE에 붙여넣기 "
        f"({dfrom}~{dto} 합산, 기관+외국인, 매도+매수, 원 단위)"
    )
    print("INST_FOREIGN_TRADEVALUE = {")
    for code in config.UNIVERSE_TICKERS:
        inv = stock.get_market_trading_value_by_investor(dfrom, dto, code)
        if inv.empty:
            print(f'    # "{code}": 투자자별 거래대금 없음 — 확인 필요')
            continue
        rows = [r for r in ("기관합계", "외국인", "기타외국인") if r in inv.index]
        val = int(inv.loc[rows, "매도"].sum() + inv.loc[rows, "매수"].sum())
        print(f'    "{code}": {val},')
    print("}")


if __name__ == "__main__":
    import sys

    if "--stratified" in sys.argv:
        tickers = stratified_universe()
        dump_frozen(tickers, write="--write" in sys.argv)
    else:
        main()
