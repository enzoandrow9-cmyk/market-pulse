from __future__ import annotations

import plotly.graph_objects as go

from quantlab.visualization.charts import apply_terminal_theme


def build_factor_bar_figure(ranking_frame):
    fig = go.Figure()
    if ranking_frame is not None and not ranking_frame.empty:
        top = ranking_frame.head(8)
        fig.add_trace(go.Bar(x=top["symbol"], y=top["momentum_rank"], marker_color="#22c55e", name="Momentum Rank"))
    return apply_terminal_theme(fig)
