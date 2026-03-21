from __future__ import annotations

import numpy as np
import plotly.graph_objects as go

from quantlab.visualization.charts import apply_terminal_theme


def build_rolling_sharpe_figure(equity_curve, window: int = 20):
    returns = equity_curve["equity"].pct_change().fillna(0.0)
    rolling_std = returns.rolling(window).std().replace(0.0, np.nan)
    rolling = returns.rolling(window).mean() / rolling_std * np.sqrt(252)
    rolling = rolling.fillna(0.0)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=equity_curve.index, y=rolling, mode="lines", name="Rolling Sharpe", line={"color": "#38bdf8"}))
    return apply_terminal_theme(fig)
