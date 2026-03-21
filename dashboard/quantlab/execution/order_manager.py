from __future__ import annotations

from quantlab.execution.order_types import OrderRequest
from quantlab.strategy.signal import StrategySignal


class OrderManager:
    def __init__(self, rebalance_threshold_shares: float = 1.0) -> None:
        self.rebalance_threshold_shares = float(rebalance_threshold_shares)

    def from_target_weight(
        self,
        signal: StrategySignal,
        portfolio_state: dict,
        current_price: float,
        current_quantity: float,
    ) -> OrderRequest | None:
        equity = portfolio_state.get("equity", 0.0)
        if current_price <= 0 or equity <= 0:
            return None
        desired_quantity = (signal.target_weight * equity) / current_price
        delta = desired_quantity - current_quantity
        if abs(delta) < self.rebalance_threshold_shares:
            return None
        side = "BUY" if delta > 0 else "SELL"
        return OrderRequest(
            strategy_id=signal.strategy_id,
            symbol=signal.symbol,
            timestamp=signal.timestamp,
            quantity=abs(delta),
            side=side,
            reference_price=current_price,
            metadata={"target_weight": signal.target_weight, "reason": signal.reason},
        )
