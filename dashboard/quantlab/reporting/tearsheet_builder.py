from __future__ import annotations

from quantlab.visualization.drawdown_plots import build_drawdown_figure
from quantlab.visualization.equity_curve import build_equity_curve_figure
from quantlab.visualization.factor_analysis_plots import build_factor_bar_figure
from quantlab.visualization.rolling_metrics import build_rolling_sharpe_figure


def build_tearsheet(result: dict) -> dict:
    return {
        "equity_curve_figure": build_equity_curve_figure(result["equity_curve"]),
        "drawdown_figure": build_drawdown_figure(result["equity_curve"]),
        "rolling_sharpe_figure": build_rolling_sharpe_figure(result["equity_curve"]),
        "factor_figure": build_factor_bar_figure(result["factor_ranking"]),
    }
