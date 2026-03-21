from __future__ import annotations

import plotly.graph_objects as go

from quantlab.visualization.charts import apply_terminal_theme


def build_equity_curve_figure(equity_curve):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=equity_curve.index, y=equity_curve["equity"], mode="lines", name="Equity", line={"color": "#fbbf24"}))
    return apply_terminal_theme(fig)
