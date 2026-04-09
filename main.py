import time
from datetime import datetime
from broker.korea_investment import get_broker, fetch_current_price
from strategy.ma_crossover import MACrossoverStrategy
from portfolio.portfolio import Portfolio
from detector.rule import detect_by_rule

SYMBOL = "005930"
INTERVAL = 1

def main():
    broker = get_broker()
    strategy = MACrossoverStrategy(short=5, long=20)
    portfolio = Portfolio()
    prices = []
    signal_count = 0
    minute_start = time.time()

    print("=" * 60)
    print(f"전략 모니터링 시작 | 종목: {SYMBOL}")
    print("=" * 60)

    while True:
        loop_start = time.time()

        if time.time() - minute_start >= 60:
            signal_count = 0
            minute_start = time.time()

        try:
            current_price = fetch_current_price(broker, SYMBOL)
            prices.append(current_price)
        except Exception as e:
            print(f"[ERROR] {e}")
            time.sleep(INTERVAL)
            continue

        signal = strategy.calculate_signal(prices)
        if signal in ["BUY", "SELL"]:
            signal_count += 1
            portfolio.update(signal, current_price)

        result = detect_by_rule(portfolio.mdd, signal_count)
        now = datetime.now().strftime("%H:%M:%S")

        print(
            f"{now} | {current_price:,}원 | "
            f"신호: {signal or '대기'} | "
            f"PnL: {portfolio.pnl:,}원 | "
            f"MDD: {portfolio.mdd:,}원 | "
            f"{result['status']} - {result['reason']}"
        )

        elapsed = time.time() - loop_start
        if INTERVAL - elapsed > 0:
            time.sleep(INTERVAL - elapsed)

if __name__ == "__main__":
    main()