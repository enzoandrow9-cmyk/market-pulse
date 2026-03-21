from __future__ import annotations


class SlippageModel:
    def __init__(self, slippage_bps: float = 2.0) -> None:
        self.slippage_bps = float(slippage_bps)

    def estimate(self, quantity: float, price: float) -> float:
        return abs(quantity) * price * self.slippage_bps / 10_000.0
