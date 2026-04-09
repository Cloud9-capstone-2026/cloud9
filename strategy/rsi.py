from strategy.base import BaseStrategy

class RSIStrategy(BaseStrategy):
    def __init__(self, period: int = 14, oversold: int = 30, overbought: int = 70):
        self.period = period
        self.oversold = oversold
        self.overbought = overbought

    def calculate_signal(self, prices: list) -> str | None:
        if len(prices) < self.period + 1:
            return None

        deltas = [prices[i] - prices[i-1] for i in range(-self.period, 0)]
        gains = [d for d in deltas if d > 0]
        losses = [-d for d in deltas if d < 0]

        avg_gain = sum(gains) / self.period if gains else 0
        avg_loss = sum(losses) / self.period if losses else 0

        if avg_loss == 0:
            rsi = 100
        else:
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))

        if rsi < self.oversold:
            return "BUY"
        elif rsi > self.overbought:
            return "SELL"
        return "HOLD"