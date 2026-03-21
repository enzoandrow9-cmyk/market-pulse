from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class EventType(str, Enum):
    MARKET_EVENT = "MARKET_EVENT"
    SIGNAL_EVENT = "SIGNAL_EVENT"
    ORDER_EVENT = "ORDER_EVENT"
    FILL_EVENT = "FILL_EVENT"
    RISK_EVENT = "RISK_EVENT"


@dataclass(frozen=True)
class Event:
    event_type: EventType
    timestamp: str
    sequence: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class MarketEvent(Event):
    symbol: str = ""
    bar: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SignalEvent(Event):
    strategy_id: str = ""
    symbol: str = ""
    direction: int = 0
    target_weight: float = 0.0
    confidence: float = 0.0
    reason: str = ""


@dataclass(frozen=True)
class OrderEvent(Event):
    strategy_id: str = ""
    symbol: str = ""
    quantity: float = 0.0
    order_type: str = "market"
    side: str = "BUY"
    reference_price: float = 0.0
    limit_price: float | None = None
    stop_price: float | None = None


@dataclass(frozen=True)
class FillEvent(Event):
    strategy_id: str = ""
    symbol: str = ""
    quantity: float = 0.0
    side: str = "BUY"
    fill_price: float = 0.0
    fees: float = 0.0
    slippage_cost: float = 0.0
    market_impact_cost: float = 0.0
    status: str = "filled"


@dataclass(frozen=True)
class RiskEvent(Event):
    symbol: str = ""
    status: str = "pass"
    reason: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
