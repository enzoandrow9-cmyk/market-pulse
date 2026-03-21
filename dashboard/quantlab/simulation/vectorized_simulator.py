from __future__ import annotations

import pandas as pd

from quantlab.portfolio.capital_allocator import CapitalAllocator


class VectorizedSimulator:
    def run(self, config, loaded_data, strategies: list) -> dict:
        allocator = CapitalAllocator()
        allocations = allocator.allocate([strategy.strategy_id for strategy in strategies])
        symbol_returns = pd.DataFrame({symbol: loaded_data.prices[symbol]["Return"] for symbol in config.symbols if symbol in loaded_data.prices}).fillna(0.0)
        weights = pd.DataFrame(0.0, index=symbol_returns.index, columns=symbol_returns.columns)

        for strategy in strategies:
            budget = allocations.get(strategy.strategy_id, 0.0)
            for symbol in config.symbols:
                frame = loaded_data.prices[symbol]
                if frame.empty:
                    continue
                series = strategy.vectorized_weights(frame).reindex(symbol_returns.index).ffill().fillna(0.0)
                weights[symbol] = weights[symbol] + series * budget

        weights = weights.clip(lower=-config.max_position_weight, upper=config.max_position_weight)
        gross = weights.abs().sum(axis=1)
        scaling = pd.Series(1.0, index=gross.index)
        scaling.loc[gross > config.max_gross_leverage] = config.max_gross_leverage / gross.loc[gross > config.max_gross_leverage]
        scaling = scaling.fillna(1.0)
        weights = weights.mul(scaling, axis=0)

        transaction_cost_bps = config.commission_bps + config.slippage_bps
        turnover = weights.diff().abs().sum(axis=1).fillna(0.0)
        portfolio_returns = (weights.shift(1).fillna(0.0) * symbol_returns).sum(axis=1) - turnover * transaction_cost_bps / 10_000.0
        equity = config.initial_capital * (1.0 + portfolio_returns).cumprod()
        drawdown = equity / equity.cummax() - 1.0

        equity_curve = pd.DataFrame(
            {
                "equity": equity,
                "cash": config.initial_capital - (weights.abs().sum(axis=1) * config.initial_capital),
                "gross_exposure": weights.abs().sum(axis=1),
                "net_exposure": weights.sum(axis=1),
                "drawdown": drawdown,
            }
        )
        return {
            "equity_curve": equity_curve,
            "weight_history": weights,
            "orders": [],
            "fills": [],
            "trades": [],
            "signals": [],
            "risk_events": [],
            "portfolio_history": [],
        }
