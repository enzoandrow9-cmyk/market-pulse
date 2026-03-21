from __future__ import annotations

from quantlab.core.event_types import EventType, FillEvent
from quantlab.execution.commission_models import CommissionModel
from quantlab.execution.liquidity_constraints import LiquidityConstraint
from quantlab.execution.market_impact_models import SquareRootImpactModel
from quantlab.execution.order_types import OrderRequest
from quantlab.execution.slippage_models import SlippageModel


class FillEngine:
    def __init__(
        self,
        commission_model: CommissionModel,
        slippage_model: SlippageModel,
        impact_model: SquareRootImpactModel,
        liquidity_constraint: LiquidityConstraint,
    ) -> None:
        self.commission_model = commission_model
        self.slippage_model = slippage_model
        self.impact_model = impact_model
        self.liquidity_constraint = liquidity_constraint

    def fill(self, order: OrderRequest, timestamp: str, bar: dict) -> FillEvent | None:
        adv = float(bar.get("ADV20", bar.get("Volume", 0.0)) or 0.0)
        fillable = self.liquidity_constraint.cap_quantity(order.quantity, adv)
        if fillable <= 0:
            return None

        ref_price = float(order.reference_price or bar["Close"])
        slippage_cost = self.slippage_model.estimate(fillable, ref_price)
        impact_cost = self.impact_model.estimate(fillable, ref_price, adv)
        fee = self.commission_model.estimate(fillable, ref_price)
        price_adjustment = (slippage_cost + impact_cost) / max(fillable, 1e-9)
        signed_adjustment = price_adjustment if order.side == "BUY" else -price_adjustment
        fill_price = ref_price + signed_adjustment

        return FillEvent(
            event_type=EventType.FILL_EVENT,
            timestamp=timestamp,
            strategy_id=order.strategy_id,
            symbol=order.symbol,
            quantity=fillable,
            side=order.side,
            fill_price=fill_price,
            fees=fee,
            slippage_cost=slippage_cost,
            market_impact_cost=impact_cost,
            status="partial" if fillable < order.quantity else "filled",
            metadata=order.metadata,
        )
