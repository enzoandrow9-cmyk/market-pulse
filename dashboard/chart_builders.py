# ─────────────────────────────────────────────────────────────────────────────
# chart_builders.py  —  Bloomberg Terminal Dashboard  •  Enzo Market Pulse
# All Plotly chart-building functions — returns go.Figure objects
# ─────────────────────────────────────────────────────────────────────────────

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from config import C, CHART

# ─────────────────────────────────────────────────────────────────────────────
# Shared layout helpers
# ─────────────────────────────────────────────────────────────────────────────

TRANSPARENT = "rgba(0,0,0,0)"

def _base_layout(**kwargs) -> dict:
    """Common layout settings for all charts. kwargs override defaults."""
    base = dict(
        paper_bgcolor = C["bg_chart"],
        plot_bgcolor  = C["bg_chart"],
        font          = dict(family="'IBM Plex Mono', 'Courier New', monospace",
                             color=C["text_primary"], size=11),
        margin        = dict(l=55, r=18, t=30, b=35),
        legend        = dict(
            bgcolor     = TRANSPARENT,
            font        = dict(size=10, color=C["text_secondary"]),
            orientation = "h",
            x=0, y=1.02,
        ),
        hoverlabel    = dict(
            bgcolor     = C["bg_panel"],
            font        = dict(color=C["text_primary"], size=11),
            bordercolor = C["border"],
        ),
        hovermode     = "x unified",
        dragmode      = "zoom",
    )
    base.update(kwargs)   # callers can override any key without duplicate-key errors
    return base


def _axis_style(title: str = "", show_grid: bool = True, **kwargs) -> dict:
    return dict(
        title           = dict(text=title, font=dict(color=C["text_secondary"], size=10)),
        gridcolor       = CHART["grid"],
        gridwidth       = 1,
        showgrid        = show_grid,
        zeroline        = True,
        zerolinecolor   = CHART["zero_line"],
        zerolinewidth   = 1,
        tickfont        = dict(color=C["text_secondary"], size=10),
        linecolor       = C["border"],
        linewidth       = 1,
        showline        = True,
        **kwargs,
    )


def _rangeslider_off() -> dict:
    return dict(rangeslider=dict(visible=False))


# ─────────────────────────────────────────────────────────────────────────────
# Candlestick + indicators chart (main ticker chart)
# ─────────────────────────────────────────────────────────────────────────────

def build_main_chart(df: pd.DataFrame, ticker: str) -> go.Figure:
    """
    5-row subplot chart:
      Row 1 (large): Candlestick + MA20/MA50 + Bollinger Bands
      Row 2 (small): Volume bars
      Row 3 (small): RSI  (with overbought/oversold zones)
      Row 4 (small): MACD (histogram + lines)
      Row 5 (small): ADX  (+DI / -DI)
    """
    if df is None or len(df) < 5:
        return _empty_chart("No data available")

    # Subplot labels pinned to left so they don't overlap y-axis tick labels
    subplot_titles = ["", "VOLUME", "RSI (14)", "MACD (12,26,9)", "ADX (14)"]

    fig = make_subplots(
        rows=5, cols=1,
        shared_xaxes=True,
        row_heights=[0.45, 0.12, 0.15, 0.15, 0.13],
        vertical_spacing=0.022,
        subplot_titles=subplot_titles,
    )

    x = df.index

    # ── Row 1: Candlestick + MAs + BBands ────────────────────────────────────
    fig.add_trace(go.Candlestick(
        x=x,
        open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"],
        increasing=dict(line=dict(color=CHART["candle_up"],   width=1),
                        fillcolor=CHART["candle_up"]),
        decreasing=dict(line=dict(color=CHART["candle_down"], width=1),
                        fillcolor=CHART["candle_down"]),
        name="Price", showlegend=False,
        hoverlabel=dict(bgcolor=C["bg_panel"]),
    ), row=1, col=1)

    # Bollinger Bands (drawn before MAs so MAs sit on top)
    if "BB_Upper" in df.columns and "BB_Lower" in df.columns:
        fig.add_trace(go.Scatter(
            x=x, y=df["BB_Upper"], name="BB Upper",
            line=dict(color="rgba(100,116,139,0.5)", width=1.2, dash="dash"),
            showlegend=True, legendgroup="bb",
            hovertemplate="BB Upper: %{y:.2f}<extra></extra>",
        ), row=1, col=1)
        fig.add_trace(go.Scatter(
            x=x, y=df["BB_Lower"], name="BB Lower",
            line=dict(color="rgba(100,116,139,0.5)", width=1.2, dash="dash"),
            fill="tonexty", fillcolor="rgba(100,116,139,0.05)",
            showlegend=False, legendgroup="bb",
            hovertemplate="BB Lower: %{y:.2f}<extra></extra>",
        ), row=1, col=1)

    # Moving Averages
    for ma_col, color, label, dash in [
        ("MA20",  CHART["ma20"],  "MA 20",  "solid"),
        ("MA50",  CHART["ma50"],  "MA 50",  "solid"),
        ("MA200", CHART["ma200"], "MA 200", "dot"),
    ]:
        if ma_col in df.columns:
            fig.add_trace(go.Scatter(
                x=x, y=df[ma_col], name=label,
                line=dict(color=color, width=1.3, dash=dash),
                opacity=0.9,
                hovertemplate=f"{label}: %{{y:.2f}}<extra></extra>",
            ), row=1, col=1)

    # VWAP (anchored to period start — key institutional reference line)
    if "VWAP" in df.columns:
        fig.add_trace(go.Scatter(
            x=x, y=df["VWAP"], name="VWAP",
            line=dict(color="#e879f9", width=1.5, dash="dashdot"),
            opacity=0.85,
            hovertemplate="VWAP: %{y:.2f}<extra></extra>",
        ), row=1, col=1)

    # ── Row 2: Volume + OBV overlay ───────────────────────────────────────────
    if "Volume" in df.columns:
        vol_colors = [
            CHART["volume_up"] if float(c) >= float(o) else CHART["volume_down"]
            for c, o in zip(df["Close"], df["Open"])
        ]
        fig.add_trace(go.Bar(
            x=x, y=df["Volume"], name="Volume",
            marker_color=vol_colors, showlegend=False,
            hovertemplate="Vol: %{y:,.0f}<extra></extra>",
        ), row=2, col=1)
        if "Vol_MA20" in df.columns:
            fig.add_trace(go.Scatter(
                x=x, y=df["Vol_MA20"],
                line=dict(color=CHART["ma20"], width=1.2),
                showlegend=False, name="Vol MA20",
                hovertemplate="Vol MA20: %{y:,.0f}<extra></extra>",
            ), row=2, col=1)

    # OBV — overlaid on volume panel with independent scale (right axis)
    if "OBV" in df.columns:
        fig.add_trace(go.Scatter(
            x=x, y=df["OBV"], name="OBV",
            line=dict(color="#22d3ee", width=1.4),
            showlegend=True,
            hovertemplate="OBV: %{y:,.0f}<extra></extra>",
            opacity=0.9,
            yaxis="y6",
        ), row=2, col=1)

    # ── Row 3: RSI ────────────────────────────────────────────────────────────
    if "RSI" in df.columns:
        # Shaded zones
        fig.add_hrect(y0=70, y1=100, fillcolor="rgba(239,68,68,0.07)",
                      line_width=0, row=3, col=1)
        fig.add_hrect(y0=0,  y1=30,  fillcolor="rgba(34,197,94,0.07)",
                      line_width=0, row=3, col=1)
        # Reference lines
        for lvl, col in [(70, CHART["candle_down"]), (30, CHART["candle_up"])]:
            fig.add_hline(y=lvl, line_dash="dot", line_color=col,
                          line_width=1, opacity=0.6, row=3, col=1)
        fig.add_trace(go.Scatter(
            x=x, y=df["RSI"], name="RSI",
            line=dict(color=CHART["rsi"], width=1.8),
            showlegend=False,
            hovertemplate="RSI: %{y:.1f}<extra></extra>",
        ), row=3, col=1)

    # ── Row 4: MACD ───────────────────────────────────────────────────────────
    if "MACD" in df.columns:
        if "MACD_Hist" in df.columns:
            hist = df["MACD_Hist"].fillna(0)
            hist_colors = [
                CHART["candle_up"] if v >= 0 else CHART["candle_down"]
                for v in hist
            ]
            fig.add_trace(go.Bar(
                x=x, y=hist, marker_color=hist_colors,
                opacity=0.55, showlegend=False, name="Hist",
                hovertemplate="Hist: %{y:.3f}<extra></extra>",
            ), row=4, col=1)
        fig.add_trace(go.Scatter(
            x=x, y=df["MACD"], name="MACD",
            line=dict(color=CHART["macd_line"], width=1.6),
            showlegend=False,
            hovertemplate="MACD: %{y:.3f}<extra></extra>",
        ), row=4, col=1)
        if "MACD_Signal" in df.columns:
            fig.add_trace(go.Scatter(
                x=x, y=df["MACD_Signal"], name="Signal",
                line=dict(color=CHART["macd_signal"], width=1.3, dash="dot"),
                showlegend=False,
                hovertemplate="Signal: %{y:.3f}<extra></extra>",
            ), row=4, col=1)

    # ── Row 5: ADX ────────────────────────────────────────────────────────────
    if "ADX" in df.columns:
        fig.add_hline(y=25, line_dash="dot", line_color=C["text_dim"],
                      line_width=1, opacity=0.5, row=5, col=1)
        fig.add_trace(go.Scatter(
            x=x, y=df["ADX"], name="ADX",
            line=dict(color=CHART["adx"], width=1.8),
            showlegend=False,
            hovertemplate="ADX: %{y:.1f}<extra></extra>",
        ), row=5, col=1)
        for di_col, di_color, di_name in [
            ("ADX_pos", CHART["adx_pos"], "+DI"),
            ("ADX_neg", CHART["adx_neg"], "-DI"),
        ]:
            if di_col in df.columns:
                fig.add_trace(go.Scatter(
                    x=x, y=df[di_col], name=di_name,
                    line=dict(color=di_color, width=1, dash="dot"),
                    showlegend=False,
                    hovertemplate=f"{di_name}: %{{y:.1f}}<extra></extra>",
                ), row=5, col=1)

    # ── Global layout ─────────────────────────────────────────────────────────
    fig.update_layout(**_base_layout(
        margin   = dict(l=60, r=14, t=36, b=10),
        legend   = dict(
            orientation = "h", x=0, y=1.01,
            bgcolor     = TRANSPARENT,
            font        = dict(size=10, color=C["text_secondary"]),
            itemclick   = "toggleothers",
        ),
        hovermode    = "x unified",
        hoverdistance = 50,
    ))

    # X-axes: hide rangeslider, style ticks on bottom panel only
    for i in range(1, 6):
        show_ticks = (i == 5)
        fig.update_xaxes(
            rangeslider_visible = False,
            showticklabels      = show_ticks,
            tickfont            = dict(color=C["text_secondary"], size=9),
            gridcolor           = CHART["grid"],
            showgrid            = True,
            linecolor           = C["border"],
            row=i, col=1,
        )

    # Y-axes per panel
    _ya = dict(gridcolor=CHART["grid"], tickfont=dict(color=C["text_secondary"], size=9),
               linecolor=C["border"], zerolinecolor=CHART["zero_line"])
    fig.update_yaxes(**_ya, row=1, col=1)
    fig.update_yaxes(**_ya, tickformat=".2s", showgrid=False, row=2, col=1)
    fig.update_yaxes(**_ya, range=[0, 100], dtick=20, row=3, col=1)
    fig.update_yaxes(**_ya, zeroline=True, zerolinewidth=1, row=4, col=1)
    fig.update_yaxes(**_ya, range=[0, 55], dtick=25, row=5, col=1)

    # OBV secondary y-axis on volume panel (row 2) — independent scale, right side
    fig.update_layout(**{
        "yaxis6": dict(
            overlaying = "y2",
            side       = "right",
            showgrid   = False,
            showticklabels = False,
            tickfont   = dict(color="#22d3ee", size=8),
        )
    })

    # Subplot label styling — small, left-aligned, dimmed
    for ann in fig.layout.annotations:
        ann.update(font=dict(color=C["text_dim"], size=9),
                   x=0.0, xanchor="left")

    return fig


# ─────────────────────────────────────────────────────────────────────────────
# Mini sparkline for portfolio cards
# ─────────────────────────────────────────────────────────────────────────────

def build_sparkline(df: pd.DataFrame, color: str = None) -> go.Figure:
    """Simple 30-day close line for portfolio cards."""
    if df is None or len(df) < 5:
        return _empty_chart("")

    last30 = df.tail(30)
    c      = color or C["amber"]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=last30.index, y=last30["Close"],
        line=dict(color=c, width=2),
        fill="tozeroy",
        fillcolor=f"rgba({_hex_to_rgb(c)},0.10)",
        hoverinfo="skip",
        showlegend=False,
    ))

    fig.update_layout(
        paper_bgcolor = TRANSPARENT,
        plot_bgcolor  = TRANSPARENT,
        margin        = dict(l=0, r=0, t=0, b=0),
        xaxis         = dict(visible=False),
        yaxis         = dict(visible=False),
        height        = 60,
    )
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# Portfolio overview bar chart
# ─────────────────────────────────────────────────────────────────────────────

def build_portfolio_bar(all_data: dict) -> go.Figure:
    """
    Horizontal bar: YTD % performance for all portfolio tickers.
    Color-coded green/red.
    """
    tickers = list(all_data.keys())
    ytd_pcts = [all_data[t].get("ytd_pct", 0.0) for t in tickers]

    colors = [C["green"] if v >= 0 else C["red"] for v in ytd_pcts]
    labels = [f"{v:+.1f}%" for v in ytd_pcts]

    fig = go.Figure(go.Bar(
        x=ytd_pcts,
        y=tickers,
        orientation="h",
        marker_color=colors,
        text=labels,
        textposition="outside",
        textfont=dict(color=C["text_primary"], size=10),
        hovertemplate="%{y}: %{x:.2f}%<extra></extra>",
    ))

    fig.add_vline(x=0, line_dash="solid", line_color=C["border"], line_width=2)

    fig.update_layout(
        **_base_layout(
            title=dict(text="YTD Performance", font=dict(color=C["amber"], size=13)),
            margin=dict(l=60, r=60, t=40, b=20),
            height=280,
            bargap=0.4,
        ),
        xaxis=_axis_style(title="YTD %", ticksuffix="%"),
        yaxis=dict(tickfont=dict(color=C["text_primary"], size=11),
                   linecolor=C["border"]),
    )
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# Market monitor mini-chart (30-day line for indices etc.)
# ─────────────────────────────────────────────────────────────────────────────

def build_market_mini_chart(symbol: str, name: str) -> go.Figure:
    """Compact 30-day line for market monitor section."""
    import yfinance as yf
    try:
        df = yf.Ticker(symbol).history(period="1mo", interval="1d", auto_adjust=True)
        if df is None or len(df) < 5:
            return _empty_chart(name)
        df.index = pd.to_datetime(df.index).tz_localize(None)
        color = C["green"] if df.iloc[-1]["Close"] >= df.iloc[0]["Close"] else C["red"]
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df.index, y=df["Close"],
            line=dict(color=color, width=1.5),
            fill="tozeroy",
            fillcolor=f"rgba({_hex_to_rgb(color)},0.08)",
            hovertemplate="%{y:.2f}<extra></extra>",
            showlegend=False,
        ))
        fig.update_layout(
            paper_bgcolor = TRANSPARENT,
            plot_bgcolor  = TRANSPARENT,
            margin        = dict(l=0, r=0, t=2, b=2),
            xaxis         = dict(visible=False),
            yaxis         = dict(visible=False),
            height        = 40,
        )
        return fig
    except Exception:
        return _empty_chart(name)


# ─────────────────────────────────────────────────────────────────────────────
# Correlation heatmap
# ─────────────────────────────────────────────────────────────────────────────

def build_correlation_heatmap(all_data: dict) -> go.Figure:
    """Build a ticker-to-ticker return correlation heatmap."""
    closes = {}
    for t, d in all_data.items():
        if d.get("df") is not None:
            closes[t] = d["df"]["Close"].pct_change().dropna()

    if len(closes) < 2:
        return _empty_chart("Not enough data for correlation")

    df_ret = pd.DataFrame(closes).dropna()
    corr   = df_ret.corr()
    ticks  = list(corr.columns)

    fig = go.Figure(go.Heatmap(
        z    = corr.values,
        x    = ticks,
        y    = ticks,
        colorscale = [
            [0.0,  C["red"]],
            [0.5,  C["bg_panel"]],
            [1.0,  C["green"]],
        ],
        zmid         = 0,
        zmin         = -1,
        zmax         = 1,
        text         = np.round(corr.values, 2),
        texttemplate = "%{text}",
        textfont     = dict(color=C["text_primary"], size=11),
        hovertemplate = "%{x} × %{y}: %{z:.2f}<extra></extra>",
        showscale    = True,
        colorbar     = dict(
            tickfont  = dict(color=C["text_secondary"], size=9),
            outlinecolor = C["border"],
        ),
    ))

    fig.update_layout(
        **_base_layout(
            title=dict(text="Return Correlation", font=dict(color=C["amber"], size=13)),
            margin=dict(l=60, r=20, t=45, b=55),
            height=300,
        ),
        xaxis=dict(tickfont=dict(color=C["text_primary"], size=10),
                   side="bottom"),
        yaxis=dict(tickfont=dict(color=C["text_primary"], size=10),
                   autorange="reversed"),
    )
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# Signal radar (spider) chart
# ─────────────────────────────────────────────────────────────────────────────

def build_signal_radar(signals: list) -> go.Figure:
    """Small radar chart showing signal strength across indicators."""
    LABEL_MAP = {
        "RSI":  "RSI",
        "MACD": "MACD",
        "BB":   "Bollinger",
        "MA":   "Moving Avg",
        "Vol":  "Volume",
        "ADX":  "ADX",
    }
    DIRECTION_MAP = {"BUY": 1, "NEUTRAL": 0, "SELL": -1}

    categories = list(LABEL_MAP.values())
    values_map = {v: 0 for v in LABEL_MAP.values()}

    for direction, indicator, _ in signals:
        label = LABEL_MAP.get(indicator)
        if label:
            values_map[label] = DIRECTION_MAP.get(direction, 0)

    vals = [values_map[c] for c in categories] + [values_map[categories[0]]]
    cats = categories + [categories[0]]

    colors_vals = ["green" if v > 0 else ("red" if v < 0 else "amber")
                   for v in [values_map[c] for c in categories]]

    fig = go.Figure(go.Scatterpolar(
        r     = vals,
        theta = cats,
        fill  = "toself",
        fillcolor = "rgba(251,191,36,0.12)",
        line  = dict(color=C["amber"], width=2),
        name  = "Signal",
    ))

    fig.update_layout(
        paper_bgcolor = C["bg_chart"],
        plot_bgcolor  = C["bg_chart"],
        font          = dict(color=C["text_primary"], size=10),
        polar=dict(
            bgcolor     = C["bg_chart"],
            angularaxis = dict(
                tickfont  = dict(color=C["text_secondary"], size=9),
                linecolor = C["border"],
                gridcolor = C["border"],
            ),
            radialaxis  = dict(
                range     = [-1.2, 1.2],
                tickvals  = [-1, 0, 1],
                ticktext  = ["SELL", "N", "BUY"],
                tickfont  = dict(color=C["text_dim"], size=8),
                gridcolor = C["border"],
                linecolor = C["border"],
            ),
        ),
        margin  = dict(l=20, r=20, t=20, b=20),
        height  = 220,
        showlegend = False,
    )
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# Utility
# ─────────────────────────────────────────────────────────────────────────────

def _empty_chart(msg: str = "No data") -> go.Figure:
    fig = go.Figure()
    fig.update_layout(
        paper_bgcolor = C["bg_chart"],
        plot_bgcolor  = C["bg_chart"],
        annotations=[dict(
            text      = msg,
            x=0.5, y=0.5,
            xref="paper", yref="paper",
            showarrow = False,
            font      = dict(color=C["text_dim"], size=13),
        )],
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        margin=dict(l=10, r=10, t=10, b=10),
    )
    return fig


def _hex_to_rgb(hex_color: str) -> str:
    """Convert #rrggbb to 'r,g,b' string for rgba()."""
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"{r},{g},{b}"
