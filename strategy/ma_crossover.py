from strategy.base import BaseStrategy

class MACrossoverStrategy(BaseStrategy):
    def __init__(self, short: int = 5, long: int = 20):
        self.short = short
        self.long = long

    def calculate_signal(self, prices: list) -> str | None:
        if len(prices) < self.long:
            return None
        ma_short = sum(prices[-self.short:]) / self.short
        ma_long = sum(prices[-self.long:]) / self.long
        if ma_short > ma_long:
            return "BUY"
        elif ma_short < ma_long:
            return "SELL"
        return "HOLD"