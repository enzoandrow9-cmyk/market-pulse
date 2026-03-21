from __future__ import annotations

import plotly.graph_objects as go


def apply_terminal_theme(fig: go.Figure) -> go.Figure:
    fig.update_layout(
        paper_bgcolor="#060b19",
        plot_bgcolor="#0a1020",
        font={"family": "IBM Plex Mono, monospace", "color": "#e2e8f0", "size": 11},
        margin={"l": 40, "r": 20, "t": 30, "b": 30},
        xaxis={"gridcolor": "rgba(30,45,74,0.4)"},
        yaxis={"gridcolor": "rgba(30,45,74,0.4)"},
    )
    return fig
