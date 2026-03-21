from __future__ import annotations


class SquareRootImpactModel:
    def __init__(self, coefficient: float = 0.1) -> None:
        self.coefficient = float(coefficient)

    def impact_bps(self, order_size: float, average_daily_volume: float) -> float:
        if average_daily_volume <= 0:
            return 0.0
        return self.coefficient * (abs(order_size) / average_daily_volume) * 10_000.0

    def estimate(self, quantity: float, price: float, average_daily_volume: float) -> float:
        bps = self.impact_bps(quantity, average_daily_volume)
        return abs(quantity) * price * bps / 10_000.0
