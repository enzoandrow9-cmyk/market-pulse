from __future__ import annotations


class LiquidityConstraint:
    def __init__(self, max_adv_percent: float = 0.05) -> None:
        self.max_adv_percent = float(max_adv_percent)

    def cap_quantity(self, requested_quantity: float, average_daily_volume: float) -> float:
        if average_daily_volume <= 0:
            return 0.0
        max_qty = abs(average_daily_volume) * self.max_adv_percent
        return min(abs(requested_quantity), max_qty)
