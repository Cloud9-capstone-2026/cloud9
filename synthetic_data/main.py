"""
Canary Base Agent 합성 데이터 생성기 - 엔트리포인트
 
실행: python -m synthetic_data.main  (레포 최상위에서)
이 파일 하나만 실행하면 synthetic_data/ 패키지 전체(가격 데이터 생성 -> agent 시뮬레이션
-> 거래 로그 저장)가 한 번에 돈다.
"""
 
from . import config
from .model import MarketModel
 
 
def main():
    model = MarketModel(
        n_investors=config.N_INVESTORS,
        tickers=config.UNIVERSE_TICKERS,
        seed=config.RANDOM_SEED,
    )
    model.run()
 
    df = model.trades_to_dataframe()
    print(f"생성된 거래 건수: {len(df)}")
    print(df.head(10).to_string())
 
    df.to_csv(config.OUTPUT_CSV_PATH, index=False, encoding="utf-8-sig")
    print(f"\n저장 완료: {config.OUTPUT_CSV_PATH}")
 
    if not df.empty:
        print("\n매수/매도 비율:")
        print(df["거래구분"].value_counts(normalize=True))
 
 
if __name__ == "__main__":
    main()
 





