from __future__ import annotations

import plotly.graph_objects as go

from quantlab.visualization.charts import apply_terminal_theme


def build_drawdown_figure(equity_curve):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=equity_curve.index, y=equity_curve["drawdown"], mode="lines", name="Drawdown", line={"color": "#ef4444"}))
    return apply_terminal_theme(fig)
