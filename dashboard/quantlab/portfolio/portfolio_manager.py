from __future__ import annotations

from dataclasses import dataclass, field

from quantlab.portfolio.accounting_engine import AccountingEngine
from quantlab.portfolio.exposure_tracker import ExposureTracker
from quantlab.portfolio.position import Position


@dataclass
class PortfolioSnapshot:
    timestamp: str
    cash: float
    equity: float
    realized_pnl: float
    unrealized_pnl: float
    gross_exposure: float
    net_exposure: float
    symbol_weights: dict[str, float] = field(default_factory=dict)


class PortfolioManager:
    def __init__(self, initial_capital: float) -> None:
        self.initial_capital = float(initial_capital)
        self.cash = float(initial_capital)
        self.positions: dict[str, Position] = {}
        self.accounting = AccountingEngine()
        self.exposures = ExposureTracker()
        self.history: list[PortfolioSnapshot] = []

    def state(self, price_map: dict[str, float]) -> dict:
        realized = sum(position.realized_pnl for position in self.positions.values())
        unrealized = sum(position.unrealized_pnl(price_map.get(symbol, position.average_price)) for symbol, position in self.positions.items())
        equity = self.cash + sum(position.market_value(price_map.get(symbol, position.average_price)) for symbol, position in self.positions.items())
        exposure = self.exposures.snapshot(self.positions, price_map, equity)
        return {
            "cash": self.cash,
            "equity": equity,
            "realized_pnl": realized,
            "unrealized_pnl": unrealized,
            **exposure,
        }

    def apply_fill(self, symbol: str, signed_quantity: float, fill_price: float, fees: float) -> None:
        position = self.positions.get(symbol, Position(symbol=symbol))
        self.cash -= signed_quantity * fill_price
        self.cash -= fees
        updated = self.accounting.apply_fill(position, signed_quantity, fill_price)
        self.positions[symbol] = updated

    def mark(self, timestamp: str, price_map: dict[str, float]) -> PortfolioSnapshot:
        state = self.state(price_map)
        snapshot = PortfolioSnapshot(
            timestamp=timestamp,
            cash=state["cash"],
            equity=state["equity"],
            realized_pnl=state["realized_pnl"],
            unrealized_pnl=state["unrealized_pnl"],
            gross_exposure=state["gross_exposure"],
            net_exposure=state["net_exposure"],
            symbol_weights=state["symbol_weights"],
        )
        self.history.append(snapshot)
        return snapshot
