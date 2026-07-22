"""
유니버스 재생성 스크립트 (유지보수용, 일회성 실행).

config.UNIVERSE_TICKERS를 만들 때 쓴 도구. 시가총액 API(get_market_cap_by_ticker)는
KRX 정보데이터시스템 로그인이 필요하므로, 저장소 루트의 .env에서 KRX_ID/KRX_PW를
python-dotenv로 로드한다. (정상 실행 경로인 get_price_data는 공개 OHLCV라 자격증명 불필요.)

실행:  python -m synthetic_data.regenerate_universe
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

# 저장소 루트의 .env(= 이 파일 부모의 부모)를 명시적으로 로드 → cwd와 무관하게 동작.
_ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_ENV_PATH)

if not os.environ.get("KRX_ID") or not os.environ.get("KRX_PW"):
    raise SystemExit(
        f"KRX_ID/KRX_PW를 찾을 수 없습니다. {_ENV_PATH} 에 두 값이 설정돼 있는지 확인하세요."
    )

from pykrx import stock  # noqa: E402  (dotenv 로드 후 import)

from . import config  # noqa: E402

MARKET = "KOSPI"
TOP_N = 30


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
    main()
