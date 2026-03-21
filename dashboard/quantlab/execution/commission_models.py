from __future__ import annotations


class CommissionModel:
    def __init__(self, commission_bps: float = 1.0, minimum_ticket_fee: float = 0.0) -> None:
        self.commission_bps = float(commission_bps)
        self.minimum_ticket_fee = float(minimum_ticket_fee)

    def estimate(self, quantity: float, price: float) -> float:
        notional = abs(quantity) * price
        fee = notional * self.commission_bps / 10_000.0
        return max(self.minimum_ticket_fee, fee)
