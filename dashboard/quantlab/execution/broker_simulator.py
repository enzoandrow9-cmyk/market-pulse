from __future__ import annotations

from quantlab.execution.fill_engine import FillEngine
from quantlab.execution.order_types import OrderRequest


class BrokerSimulator:
    def __init__(self, fill_engine: FillEngine) -> None:
        self.fill_engine = fill_engine

    def execute(self, order: OrderRequest, timestamp: str, bar: dict):
        return self.fill_engine.fill(order, timestamp, bar)
