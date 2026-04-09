class Portfolio:
    def __init__(self):
        self.position = None
        self.entry_price = 0
        self.pnl = 0
        self.peak_pnl = 0
        self.mdd = 0

    def update(self, signal: str, current_price: int):
        if signal == "BUY" and self.position != "LONG":
            self.position = "LONG"
            self.entry_price = current_price
        elif signal == "SELL" and self.position == "LONG":
            self.pnl += current_price - self.entry_price
            self.position = None
            self.peak_pnl = max(self.peak_pnl, self.pnl)
            self.mdd = max(self.mdd, self.peak_pnl - self.pnl)

    def status(self) -> dict:
        return {
            "position": self.position,
            "entry_price": self.entry_price,
            "pnl": self.pnl,
            "mdd": self.mdd,
        }