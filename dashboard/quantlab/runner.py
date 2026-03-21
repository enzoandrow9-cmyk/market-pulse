from __future__ import annotations

import shlex
from pathlib import Path
from typing import Any

import pandas as pd

from quantlab.analytics.capacity_analysis import estimate_capacity
from quantlab.analytics.factor_exposure import compute_factor_exposure
from quantlab.analytics.performance_attribution import attribute_performance
from quantlab.analytics.performance_metrics import compute_performance_metrics
from quantlab.analytics.risk_metrics import compute_risk_metrics
from quantlab.analytics.trade_statistics import compute_trade_statistics
from quantlab.analytics.turnover_analysis import compute_turnover
from quantlab.core.deterministic_runtime import seed_everything
from quantlab.data.data_handler import MarketDataHandler
from quantlab.execution.broker_simulator import BrokerSimulator
from quantlab.execution.commission_models import CommissionModel
from quantlab.execution.fill_engine import FillEngine
from quantlab.execution.liquidity_constraints import LiquidityConstraint
from quantlab.execution.market_impact_models import SquareRootImpactModel
from quantlab.execution.order_manager import OrderManager
from quantlab.execution.slippage_models import SlippageModel
from quantlab.experiments.experiment_tracker import ExperimentTracker
from quantlab.optimization.bayesian_optimizer import bayesian_search
from quantlab.optimization.genetic_optimizer import genetic_search
from quantlab.optimization.monte_carlo_simulation import bootstrap_trade_sequences
from quantlab.optimization.parameter_search import grid_search, random_search
from quantlab.reporting.research_report_generator import build_markdown_report
from quantlab.reporting.tearsheet_builder import build_tearsheet
from quantlab.research.factor_decay import compute_factor_decay
from quantlab.research.factor_engine import FactorEngine
from quantlab.research.regime_detection import detect_market_regime
from quantlab.risk.scenario_stress_testing import run_stress_tests
from quantlab.simulation.event_simulator import EventDrivenSimulator
from quantlab.simulation.simulation_engine import SimulationEngine
from quantlab.simulation.vectorized_simulator import VectorizedSimulator
from quantlab.strategies.mean_reversion import MeanReversionStrategy
from quantlab.strategies.momentum_breakout import MomentumBreakoutStrategy
from quantlab.strategies.sma_crossover import SMACrossoverStrategy
from quantlab.strategies.volatility_targeting import VolatilityTargetingStrategy
from quantlab.types import BacktestConfig


STRATEGY_REGISTRY = {
    "sma_crossover": SMACrossoverStrategy,
    "mean_reversion": MeanReversionStrategy,
    "momentum_breakout": MomentumBreakoutStrategy,
    "volatility_targeting": VolatilityTargetingStrategy,
}


def _coerce_value(value: str) -> Any:
    lowered = value.lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        return value


def _jsonable_frame(frame: pd.DataFrame) -> list[dict[str, Any]]:
    if frame is None or frame.empty:
        return []
    serial = frame.reset_index().copy()
    serial[serial.columns[0]] = serial[serial.columns[0]].astype(str)
    return serial.to_dict("records")


class QuantLabRunner:
    def __init__(self, output_root: str | None = None) -> None:
        base = Path(output_root or Path(__file__).resolve().parents[1] / "quantlab_runs")
        self.output_root = base
        self.output_root.mkdir(parents=True, exist_ok=True)
        self.data_handler = MarketDataHandler()
        self.factor_engine = FactorEngine()
        fill_engine = FillEngine(
            commission_model=CommissionModel(),
            slippage_model=SlippageModel(),
            impact_model=SquareRootImpactModel(),
            liquidity_constraint=LiquidityConstraint(),
        )
        broker = BrokerSimulator(fill_engine)
        order_manager = OrderManager()
        self.simulation_engine = SimulationEngine(
            event_simulator=EventDrivenSimulator(broker, order_manager),
            vectorized_simulator=VectorizedSimulator(),
        )
        self.experiments = ExperimentTracker(str(base / "experiments"))

    def parse_command(self, command: str) -> dict[str, Any]:
        tokens = shlex.split(command.strip())
        if not tokens:
            raise ValueError("Empty Quant Lab command")
        action = tokens[0].lower()
        if action == "backtest":
            if len(tokens) < 5:
                raise ValueError("Usage: backtest SYMBOL[,SYMBOL] STRATEGY[,STRATEGY] START_DATE END_DATE [key=value ...]")
            symbols = [token.strip().upper() for token in tokens[1].split(",") if token.strip()]
            strategies = [token.strip().lower() for token in tokens[2].split(",") if token.strip()]
            args = {"action": action, "symbols": symbols, "strategies": strategies, "start_date": tokens[3], "end_date": tokens[4]}
            extras = {}
            for token in tokens[5:]:
                if "=" in token:
                    key, value = token.split("=", 1)
                    extras[key] = _coerce_value(value)
            args["extras"] = extras
            return args
        if action == "research":
            if len(tokens) < 4:
                raise ValueError("Usage: research SYMBOL[,SYMBOL] START_DATE END_DATE")
            return {"action": action, "symbols": tokens[1].split(","), "start_date": tokens[2], "end_date": tokens[3]}
        if action == "regime":
            if len(tokens) < 4:
                raise ValueError("Usage: regime SYMBOL START_DATE END_DATE")
            return {"action": action, "symbol": tokens[1], "start_date": tokens[2], "end_date": tokens[3]}
        if action == "optimize":
            if len(tokens) < 5:
                raise ValueError("Usage: optimize SYMBOL STRATEGY START_DATE END_DATE [method=grid|random|bayesian|genetic]")
            extras = {}
            for token in tokens[5:]:
                if "=" in token:
                    key, value = token.split("=", 1)
                    extras[key] = _coerce_value(value)
            return {"action": action, "symbol": tokens[1], "strategy": tokens[2], "start_date": tokens[3], "end_date": tokens[4], "extras": extras}
        raise ValueError(f"Unknown Quant Lab command: {action}")

    def run_command(self, command: str) -> dict[str, Any]:
        parsed = self.parse_command(command)
        action = parsed["action"]
        if action == "backtest":
            return self.run_backtest(parsed["symbols"], parsed["strategies"], parsed["start_date"], parsed["end_date"], parsed.get("extras", {}), command)
        if action == "research":
            loaded = self.data_handler.load(parsed["symbols"], parsed["start_date"], parsed["end_date"], interval="1d")
            factor_pack = self.factor_engine.evaluate(loaded.prices)
            return {
                "command": command,
                "mode": "research",
                "factor_ranking": factor_pack["ranking"],
                "regimes": {symbol: detect_market_regime(frame) for symbol, frame in loaded.prices.items()},
            }
        if action == "regime":
            loaded = self.data_handler.load([parsed["symbol"]], parsed["start_date"], parsed["end_date"], interval="1d")
            frame = loaded.prices[parsed["symbol"]]
            return {"command": command, "mode": "regime", "regime": detect_market_regime(frame)}
        if action == "optimize":
            return self.run_optimization(parsed["symbol"], parsed["strategy"], parsed["start_date"], parsed["end_date"], parsed.get("extras", {}), command)
        raise ValueError(f"Unhandled action: {action}")

    def run_backtest(
        self,
        symbols: list[str],
        strategies: list[str],
        start_date: str,
        end_date: str,
        extras: dict[str, Any] | None = None,
        raw_command: str | None = None,
    ) -> dict[str, Any]:
        extras = extras or {}
        strategy_parameters = {strategy: self._strategy_defaults(strategy) for strategy in strategies}
        for strategy in strategies:
            for key, value in extras.items():
                if key in strategy_parameters[strategy]:
                    strategy_parameters[strategy][key] = value

        config = BacktestConfig(
            symbols=list(symbols),
            strategies=list(strategies),
            start_date=start_date,
            end_date=end_date,
            interval=str(extras.get("interval", "1d")),
            simulation_mode=str(extras.get("mode", "event")),
            initial_capital=float(extras.get("capital", 1_000_000.0)),
            commission_bps=float(extras.get("commission_bps", 1.0)),
            slippage_bps=float(extras.get("slippage_bps", 2.0)),
            market_impact_coefficient=float(extras.get("impact_k", 0.1)),
            max_adv_percent=float(extras.get("max_adv_pct", 0.05)),
            max_position_weight=float(extras.get("max_pos", 0.15)),
            max_gross_leverage=float(extras.get("max_lev", 1.5)),
            max_drawdown=float(extras.get("max_dd", 0.2)),
            seed=int(extras.get("seed", 42)),
            parameters=strategy_parameters,
            metadata={"raw_command": raw_command or ""},
        )
        seed_everything(config.seed)
        loaded = self.data_handler.load(config.symbols + [config.benchmark], config.start_date, config.end_date, interval=config.interval)
        strategies_obj = [self._instantiate_strategy(name, config) for name in config.strategies]
        sim = self.simulation_engine.run(config, loaded, strategies_obj)
        equity_curve = sim["equity_curve"]
        if equity_curve.empty:
            raise ValueError("Simulation produced no equity curve")

        factor_pack = self.factor_engine.evaluate({symbol: frame for symbol, frame in loaded.prices.items() if symbol in config.symbols})
        primary_symbol = config.symbols[0]
        factor_decay = compute_factor_decay(factor_pack["time_series"].get(primary_symbol, pd.DataFrame()), loaded.prices[primary_symbol]["Close"])
        regime = detect_market_regime(loaded.prices[primary_symbol])
        performance_metrics = compute_performance_metrics(equity_curve["equity"])
        risk_metrics = compute_risk_metrics(equity_curve["equity"])
        trade_statistics = compute_trade_statistics(sim["trades"])
        turnover = compute_turnover(sim["weight_history"])
        capacity = estimate_capacity({symbol: loaded.prices[symbol] for symbol in config.symbols}, config.max_adv_percent)
        stress = run_stress_tests(equity_curve["equity"])

        symbol_returns = pd.DataFrame({symbol: loaded.prices[symbol]["Return"] for symbol in config.symbols}).fillna(0.0)
        attribution = attribute_performance(symbol_returns, sim["weight_history"])
        factor_frame = factor_pack["time_series"].get(primary_symbol, pd.DataFrame()).copy()
        factor_frame.index = factor_frame.index.astype("datetime64[ns]")
        strategy_returns = equity_curve["equity"].pct_change().fillna(0.0)
        strategy_returns.index = pd.to_datetime(strategy_returns.index)
        factor_exposure = compute_factor_exposure(strategy_returns, factor_frame)
        monte_carlo = bootstrap_trade_sequences([float(trade.get("pnl", 0.0)) for trade in sim["trades"]])

        payload = {
            "command": raw_command or "",
            "config": config.__dict__,
            "performance_metrics": performance_metrics,
            "risk_metrics": risk_metrics,
            "trade_statistics": trade_statistics,
            "turnover_analysis": turnover,
            "capacity_analysis": capacity,
            "performance_attribution": attribution,
            "factor_exposure": factor_exposure,
            "factor_decay": factor_decay,
            "regime": regime,
            "stress_tests": stress,
            "monte_carlo": monte_carlo,
            "equity_curve": _jsonable_frame(equity_curve),
            "weight_history": _jsonable_frame(sim["weight_history"]),
            "orders": sim["orders"],
            "fills": sim["fills"],
            "trades": sim["trades"],
            "signals": sim["signals"],
            "risk_events": sim["risk_events"],
            "factor_ranking": factor_pack["ranking"].to_dict("records") if not factor_pack["ranking"].empty else [],
        }
        experiment = self.experiments.record(config, loaded.dataset_version, payload)
        result = {
            **payload,
            "dataset_version": loaded.dataset_version,
            "experiment": experiment,
            "equity_curve_frame": equity_curve,
            "factor_ranking_frame": factor_pack["ranking"],
        }
        result["factor_ranking"] = factor_pack["ranking"]
        result["tearsheet"] = build_tearsheet({"equity_curve": equity_curve, "factor_ranking": factor_pack["ranking"]})
        result["report_markdown"] = build_markdown_report(
            {
                "performance_metrics": performance_metrics,
                "risk_metrics": risk_metrics,
                "trade_statistics": trade_statistics,
                "regime": regime,
                "experiment": experiment,
            }
        )
        return result

    def run_optimization(self, symbol: str, strategy: str, start_date: str, end_date: str, extras: dict[str, Any], raw_command: str) -> dict[str, Any]:
        method = str(extras.get("method", "grid"))
        search_space = self._default_search_space(strategy)

        def objective(params: dict[str, Any]) -> float:
            result = self.run_backtest([symbol], [strategy], start_date, end_date, {"mode": "vectorized", "capital": extras.get("capital", 250_000), **params}, raw_command)
            return float(result["performance_metrics"].get("sharpe_ratio", 0.0))

        if method == "grid":
            optimization = grid_search(search_space, objective)
        elif method == "random":
            optimization = random_search(search_space, objective, iterations=int(extras.get("iterations", 16)))
        elif method == "bayesian":
            optimization = bayesian_search(search_space, objective, iterations=int(extras.get("iterations", 16)))
        else:
            optimization = genetic_search(search_space, objective, population_size=int(extras.get("population", 8)), generations=int(extras.get("generations", 4)))
        return {"command": raw_command, "mode": "optimize", "method": method, "optimization": optimization}

    def _instantiate_strategy(self, name: str, config: BacktestConfig):
        if name not in STRATEGY_REGISTRY:
            raise ValueError(f"Unknown strategy: {name}")
        klass = STRATEGY_REGISTRY[name]
        return klass(
            strategy_id=name,
            parameters=config.strategy_parameters(name),
            max_position_weight=config.max_position_weight,
        )

    def _strategy_defaults(self, name: str) -> dict[str, Any]:
        return {
            "sma_crossover": {"short_window": 20, "long_window": 50, "allow_short": False},
            "mean_reversion": {"lookback": 20, "entry_z": 1.5, "exit_z": 0.5},
            "momentum_breakout": {"lookback": 55, "exit_window": 20},
            "volatility_targeting": {"vol_window": 20, "trend_window": 50, "target_vol": 0.15},
        }.get(name, {})

    def _default_search_space(self, name: str) -> dict[str, list]:
        return {
            "sma_crossover": {"short_window": [10, 20, 30], "long_window": [50, 100, 150]},
            "mean_reversion": {"lookback": [10, 20, 30], "entry_z": [1.0, 1.5, 2.0]},
            "momentum_breakout": {"lookback": [20, 55, 80], "exit_window": [10, 20, 30]},
            "volatility_targeting": {"vol_window": [10, 20, 40], "target_vol": [0.10, 0.15, 0.20]},
        }.get(name, {"lookback": [10, 20, 30]})
