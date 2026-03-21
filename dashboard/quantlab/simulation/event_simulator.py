from __future__ import annotations

from dataclasses import asdict

import pandas as pd

from quantlab.execution.broker_simulator import BrokerSimulator
from quantlab.execution.order_manager import OrderManager
from quantlab.portfolio.capital_allocator import CapitalAllocator
from quantlab.portfolio.portfolio_manager import PortfolioManager
from quantlab.risk.risk_engine import RiskEngine
from quantlab.risk.portfolio_limits import PortfolioLimits
from quantlab.simulation.market_environment import MarketEnvironment
from quantlab.simulation.simulation_clock import SimulationClock


class EventDrivenSimulator:
    def __init__(self, broker: BrokerSimulator, order_manager: OrderManager) -> None:
        self.broker = broker
        self.order_manager = order_manager

    def run(self, config, loaded_data, strategies: list) -> dict:
        environment = MarketEnvironment(loaded_data.pit_db)
        portfolio = PortfolioManager(config.initial_capital)
        risk = RiskEngine(
            PortfolioLimits(
                max_position_weight=config.max_position_weight,
                max_gross_leverage=config.max_gross_leverage,
                max_drawdown=config.max_drawdown,
            )
        )
        allocator = CapitalAllocator()
        allocations = allocator.allocate([strategy.strategy_id for strategy in strategies])

        orders: list[dict] = []
        fills: list[dict] = []
        trades: list[dict] = []
        risk_events: list[dict] = []
        signal_log: list[dict] = []
        equity_rows: list[dict] = []
        weight_rows: list[dict] = []

        for timestamp in SimulationClock(loaded_data.pit_db.timeline()):
            for symbol in loaded_data.pit_db.symbols():
                environment.update(symbol, timestamp)
            price_map = environment.price_map()
            if not price_map:
                continue

            portfolio_state = portfolio.state(price_map)
            aggregated_targets: dict[str, float] = {}

            for strategy in sorted(strategies, key=lambda item: item.strategy_id):
                budget = allocations.get(strategy.strategy_id, 0.0)
                for symbol in sorted(config.symbols):
                    history = loaded_data.pit_db.history_until(symbol, timestamp)
                    if history.empty:
                        continue
                    signals = strategy.generate_signals(timestamp, symbol, history, portfolio_state)
                    for signal in signals:
                        target_weight = budget * signal.target_weight
                        aggregated_targets[symbol] = aggregated_targets.get(symbol, 0.0) + target_weight
                        signal_log.append(
                            {
                                "timestamp": signal.timestamp,
                                "symbol": signal.symbol,
                                "strategy_id": signal.strategy_id,
                                "target_weight": target_weight,
                                "reason": signal.reason,
                                "confidence": signal.confidence,
                            }
                        )

            for symbol in sorted(aggregated_targets):
                target_weight = aggregated_targets[symbol]
                valid, reason = risk.validate_target_weight(
                    target_weight,
                    gross_exposure=portfolio_state.get("gross_exposure", 0.0),
                    current_equity=portfolio_state.get("equity", 0.0),
                )
                if not valid:
                    risk_events.append({"timestamp": timestamp.isoformat(), "symbol": symbol, "reason": reason})
                    continue

                current_qty = portfolio.positions.get(symbol).quantity if symbol in portfolio.positions else 0.0
                current_price = price_map.get(symbol, 0.0)
                synthetic_signal = type(
                    "SyntheticSignal",
                    (),
                    {
                        "strategy_id": "portfolio",
                        "symbol": symbol,
                        "timestamp": timestamp.isoformat(),
                        "target_weight": target_weight,
                        "reason": "aggregated_target",
                    },
                )()
                order = self.order_manager.from_target_weight(
                    synthetic_signal,
                    portfolio_state=portfolio_state,
                    current_price=current_price,
                    current_quantity=current_qty,
                )
                if order is None:
                    continue

                orders.append(asdict(order))
                bar = loaded_data.pit_db.bar_at(symbol, timestamp)
                fill = self.broker.execute(order, timestamp.isoformat(), bar.to_dict())
                if fill is None:
                    continue

                realized_before = sum(position.realized_pnl for position in portfolio.positions.values())
                signed_quantity = fill.quantity if fill.side == "BUY" else -fill.quantity
                portfolio.apply_fill(fill.symbol, signed_quantity, fill.fill_price, fill.fees)
                realized_after = sum(position.realized_pnl for position in portfolio.positions.values())
                fills.append(asdict(fill))
                if realized_after != realized_before:
                    trades.append(
                        {
                            "timestamp": fill.timestamp,
                            "symbol": fill.symbol,
                            "side": fill.side,
                            "quantity": fill.quantity,
                            "fill_price": fill.fill_price,
                            "pnl": realized_after - realized_before,
                            "strategy_id": fill.strategy_id,
                        }
                    )

            snapshot = portfolio.mark(timestamp.isoformat(), price_map)
            drawdown = risk.update_drawdown(snapshot.equity)
            equity_rows.append(
                {
                    "timestamp": timestamp,
                    "cash": snapshot.cash,
                    "equity": snapshot.equity,
                    "gross_exposure": snapshot.gross_exposure,
                    "net_exposure": snapshot.net_exposure,
                    "drawdown": drawdown,
                }
            )
            row = {"timestamp": timestamp}
            row.update(snapshot.symbol_weights)
            weight_rows.append(row)

        return {
            "equity_curve": pd.DataFrame(equity_rows).set_index("timestamp") if equity_rows else pd.DataFrame(),
            "weight_history": pd.DataFrame(weight_rows).set_index("timestamp").fillna(0.0) if weight_rows else pd.DataFrame(),
            "orders": orders,
            "fills": fills,
            "trades": trades,
            "signals": signal_log,
            "risk_events": risk_events,
            "portfolio_history": [snapshot.__dict__ for snapshot in portfolio.history],
        }
