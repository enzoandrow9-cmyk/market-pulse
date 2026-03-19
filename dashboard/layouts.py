# ─────────────────────────────────────────────────────────────────────────────
# layouts.py  —  Bloomberg Terminal Dashboard  •  Enzo Market Pulse
# All Dash component layouts — returns dash HTML/component trees
# ─────────────────────────────────────────────────────────────────────────────

from dash import html, dcc
import dash_bootstrap_components as dbc

from config import C, PORTFOLIO_TICKERS, TICKER_NAMES, TICKER_SECTOR, PRESET_TICKERS, DEFAULT_SETTINGS

# ─────────────────────────────────────────────────────────────────────────────
# Shared CSS-in-Python style constants
# ─────────────────────────────────────────────────────────────────────────────

FONT_MONO = "'IBM Plex Mono', 'Courier New', monospace"

CARD_STYLE = {
    "background":    C["bg_panel"],
    "border":        f"1px solid {C['border']}",
    "borderRadius":  "4px",
    "padding":       "14px 16px",
    "marginBottom":  "10px",
}

SECTION_TITLE = {
    "color":        "var(--accent)",
    "fontFamily":   FONT_MONO,
    "fontSize":     "11px",
    "fontWeight":   "700",
    "letterSpacing":"0.12em",
    "textTransform":"uppercase",
    "marginBottom": "8px",
    "borderBottom": f"1px solid {C['border']}",
    "paddingBottom":"5px",
}

LABEL_STYLE = {
    "color":      C["text_secondary"],
    "fontFamily": FONT_MONO,
    "fontSize":   "10px",
    "letterSpacing":"0.06em",
    "textTransform":"uppercase",
}

VALUE_STYLE = {
    "color":      C["text_primary"],
    "fontFamily": FONT_MONO,
    "fontSize":   "13px",
    "fontWeight": "600",
}

# ─────────────────────────────────────────────────────────────────────────────
# Top nav bar
# ─────────────────────────────────────────────────────────────────────────────

def build_navbar() -> html.Div:
    tab_style = {
        "padding":    "8px 18px",
        "fontFamily": FONT_MONO,
        "fontSize":   "11px",
        "fontWeight": "600",
        "letterSpacing": "0.08em",
        "color":      C["text_secondary"],
        "cursor":     "pointer",
        "border":     "none",
        "borderBottom":"2px solid transparent",
        "background": "transparent",
        "textTransform": "uppercase",
    }
    active_tab_style = {**tab_style,
                        "color":       "var(--accent)",
                        "borderBottom":"2px solid var(--accent)"}

    return html.Div([
        # Left: brand
        html.Div([
            html.Span("◈ ", style={"color": "var(--accent)", "fontSize": "16px"}),
            html.Span("MARKET", style={"color": C["text_white"], "fontWeight": "900",
                                       "fontFamily": FONT_MONO, "fontSize": "14px",
                                       "letterSpacing": "0.15em"}),
            html.Span(" PULSE", style={"color": "var(--accent)", "fontWeight": "900",
                                       "fontFamily": FONT_MONO, "fontSize": "14px",
                                       "letterSpacing": "0.15em"}),
            html.Span("  TERMINAL", style={"color": C["text_dim"], "fontWeight": "400",
                                            "fontFamily": FONT_MONO, "fontSize": "10px",
                                            "letterSpacing": "0.18em", "marginLeft": "6px"}),
        ], style={"display":"flex","alignItems":"center","gap":"0px"}),

        # Center: tabs
        dcc.Tabs(
            id="main-tabs",
            value="portfolio",
            children=[
                dcc.Tab(label="PORTFOLIO",  value="portfolio",
                        style=tab_style, selected_style=active_tab_style),
                dcc.Tab(label="DEEP DIVE",  value="deepdive",
                        style=tab_style, selected_style=active_tab_style),
                dcc.Tab(label="MARKET",     value="market",
                        style=tab_style, selected_style=active_tab_style),
                dcc.Tab(label="NEWS",       value="news",
                        style=tab_style, selected_style=active_tab_style),
                dcc.Tab(label="⚙ SETTINGS", value="settings",
                        style=tab_style, selected_style=active_tab_style),
            ],
            style={"border":"none","background":"transparent"},
        ),

        # Right: clock + refresh
        html.Div([
            html.Span(id="clock-display",
                      style={"color":C["text_secondary"],"fontFamily":FONT_MONO,
                             "fontSize":"11px","marginRight":"16px"}),
            html.Button("⟳ REFRESH", id="refresh-btn",
                        style={
                            "background":  "transparent",
                            "border":      "1px solid var(--accent)",
                            "color":       "var(--accent)",
                            "fontFamily":  FONT_MONO,
                            "fontSize":    "10px",
                            "padding":     "5px 12px",
                            "cursor":      "pointer",
                            "borderRadius":"2px",
                            "letterSpacing":"0.08em",
                        }),
        ], style={"display":"flex","alignItems":"center"}),

    ], style={
        "display":       "flex",
        "alignItems":    "center",
        "justifyContent":"space-between",
        "background":    C["bg_panel"],
        "borderBottom":  f"1px solid {C['border']}",
        "padding":       "0 20px",
        "height":        "46px",
        "position":      "sticky",
        "top":           "0",
        "zIndex":        "999",
    })


# ─────────────────────────────────────────────────────────────────────────────
# Portfolio overview tab
# ─────────────────────────────────────────────────────────────────────────────

def build_ai_briefing_banner() -> html.Div:
    """AI morning briefing strip — sits above the portfolio cards."""
    return html.Div([
        # Header row
        html.Div([
            html.Span("◈ AI BRIEFING", style={
                "color":         "var(--accent)",
                "fontFamily":    FONT_MONO,
                "fontSize":      "10px",
                "fontWeight":    "700",
                "letterSpacing": "0.14em",
                "marginRight":   "12px",
                "whiteSpace":    "nowrap",
            }),
            html.Span("LLAMA 3.3 · GROQ", style={
                "color":         C["text_dim"],
                "fontFamily":    FONT_MONO,
                "fontSize":      "9px",
                "letterSpacing": "0.10em",
                "marginRight":   "auto",
            }),
            html.Span(id="briefing-time", children="", style={
                "color":         C["text_dim"],
                "fontFamily":    FONT_MONO,
                "fontSize":      "9px",
                "letterSpacing": "0.08em",
            }),
        ], style={"display": "flex", "alignItems": "center", "marginBottom": "8px"}),

        # Briefing text
        html.Div(
            id="briefing-text",
            children="Generating market briefing…",
            style={
                "color":       C["text_primary"],
                "fontFamily":  FONT_MONO,
                "fontSize":    "12px",
                "lineHeight":  "1.7",
                "fontStyle":   "italic",
                "opacity":     "0.92",
            },
        ),
    ], style={
        "background":    C["bg_panel"],
        "border":        "1px solid var(--accent)",
        "borderLeft":    "3px solid var(--accent)",
        "borderRadius":  "4px",
        "padding":       "12px 16px",
        "marginBottom":  "14px",
    })


def build_portfolio_tab() -> html.Div:
    return html.Div([
        # AI Briefing banner
        build_ai_briefing_banner(),

        # Row 1: ticker cards
        html.Div(id="portfolio-cards", style={
            "display":       "grid",
            "gridTemplateColumns": "repeat(auto-fill, minmax(210px, 1fr))",
            "gap":           "10px",
            "marginBottom":  "14px",
        }),

        # Row 2: YTD bar  +  correlation heatmap
        dbc.Row([
            dbc.Col([
                html.Div("YTD Performance", style=SECTION_TITLE),
                dcc.Graph(id="ytd-bar", config={"displayModeBar": False}),
            ], width=6),
            dbc.Col([
                html.Div("Return Correlation", style=SECTION_TITLE),
                dcc.Graph(id="correlation-heatmap", config={"displayModeBar": False}),
            ], width=6),
        ]),
    ], style={"padding": "14px 20px"})


def _advisory_color(advisory: str) -> str:
    m = {
        "STRONG BUY":  C["green"],
        "BUY":         "#16a34a",
        "HOLD":        "var(--accent)",
        "SELL":        "#ea580c",
        "STRONG SELL": C["red"],
    }
    return m.get(advisory, C["text_secondary"])


def _week52_bar(price, low52, high52) -> html.Div:
    """Thin horizontal range bar showing where price sits in its 52-week range."""
    if not price or not low52 or not high52 or high52 <= low52:
        return html.Div()
    pct = max(0.0, min(1.0, (price - low52) / (high52 - low52)))
    pct_str = f"{pct*100:.0f}%"
    return html.Div([
        html.Div([
            html.Span(f"{low52:,.0f}", style={
                "color": C["text_dim"], "fontFamily": FONT_MONO, "fontSize": "8px",
            }),
            html.Span("52W", style={
                "color": C["text_dim"], "fontFamily": FONT_MONO, "fontSize": "8px",
                "letterSpacing": "0.06em",
            }),
            html.Span(f"{high52:,.0f}", style={
                "color": C["text_dim"], "fontFamily": FONT_MONO, "fontSize": "8px",
            }),
        ], style={"display": "flex", "justifyContent": "space-between", "marginBottom": "2px"}),
        # Track
        html.Div([
            html.Div(style={
                "position":   "absolute",
                "left":       pct_str,
                "transform":  "translateX(-50%)",
                "width":      "6px",
                "height":     "6px",
                "borderRadius":"50%",
                "background": "var(--accent)",
                "top":        "-1px",
            }),
        ], style={
            "position":   "relative",
            "height":     "4px",
            "background": C["border"],
            "borderRadius":"2px",
            "marginBottom":"6px",
        }),
    ])


def _vol_ratio_badge(vol_ratio: float) -> html.Span:
    """Small badge showing volume vs 20-day average."""
    if not vol_ratio:
        return html.Span()
    if vol_ratio >= 2.0:
        color, label = C["red"],    f"VOL {vol_ratio:.1f}×"
    elif vol_ratio >= 1.3:
        color, label = "var(--accent)",  f"VOL {vol_ratio:.1f}×"
    else:
        color, label = C["text_dim"], f"VOL {vol_ratio:.1f}×"
    return html.Span(label, style={
        "background":   color + "18",
        "color":        color,
        "border":       f"1px solid {color}44",
        "borderRadius": "3px",
        "padding":      "1px 5px",
        "fontSize":     "8px",
        "fontFamily":   FONT_MONO,
        "fontWeight":   "700",
        "letterSpacing":"0.05em",
        "marginLeft":   "auto",
    })


def _prepost_badge(data: dict) -> html.Div:
    """After-hours or pre-market mini-badge. Returns empty Div if no data."""
    post_px  = data.get("post_market_price")
    pre_px   = data.get("pre_market_price")
    post_chg = data.get("post_market_chg_pct")
    pre_chg  = data.get("pre_market_chg_pct")

    if post_px and post_chg is not None:
        label, px, chg = "AH", post_px, post_chg
    elif pre_px and pre_chg is not None:
        label, px, chg = "PM", pre_px, pre_chg
    else:
        return html.Div()

    color = C["green"] if chg >= 0 else C["red"]
    sign  = "+" if chg >= 0 else ""
    return html.Div([
        html.Span(label, style={
            "background":  color + "22",
            "color":       color,
            "border":      f"1px solid {color}55",
            "borderRadius":"3px",
            "padding":     "1px 6px",
            "fontSize":    "9px",
            "fontFamily":  FONT_MONO,
            "fontWeight":  "700",
            "letterSpacing":"0.06em",
            "marginRight": "6px",
        }),
        html.Span(f"${px:,.2f}", style={
            "color":      C["text_secondary"],
            "fontFamily": FONT_MONO,
            "fontSize":   "10px",
            "marginRight":"5px",
        }),
        html.Span(f"{sign}{chg:.2f}%", style={
            "color":      color,
            "fontFamily": FONT_MONO,
            "fontSize":   "10px",
            "fontWeight": "600",
        }),
    ], style={"display":"flex","alignItems":"center","marginBottom":"6px"})


def build_portfolio_card(data: dict) -> html.Div:
    """Single ticker card shown in portfolio overview grid."""
    ticker    = data.get("ticker", "?")
    name      = data.get("name", ticker)
    price     = data.get("price")
    chg_pct   = data.get("chg_pct", 0.0)
    chg_abs   = data.get("chg_abs", 0.0)
    advisory  = data.get("advisory", "HOLD")
    stars     = data.get("stars", 3)
    sector, sector_color = data.get("sector", ("Unknown", C["text_dim"]))
    error     = data.get("error")
    vol_ratio = data.get("vol_ratio", 1.0)
    week52_high = data.get("week52_high")
    week52_low  = data.get("week52_low")

    chg_color = C["green"] if chg_pct >= 0 else C["red"]
    adv_color = _advisory_color(advisory)
    stars_str = "★" * stars + "☆" * (5 - stars)

    if error or price is None:
        return html.Div([
            html.Div(ticker, style={**VALUE_STYLE, "color": "var(--accent)"}),
            html.Div(f"Error: {error or 'N/A'}", style={**LABEL_STYLE, "color": C["red"]}),
        ], style={**CARD_STYLE, "opacity": "0.6"})

    card_inner = html.Div([
        # Header row: ticker + sector pill + vol badge + arrow
        html.Div([
            html.Span(ticker, style={
                "color":      "var(--accent)",
                "fontFamily": FONT_MONO,
                "fontSize":   "14px",
                "fontWeight": "800",
            }),
            html.Span(sector, style={
                "background":  sector_color + "22",
                "color":       sector_color,
                "border":      f"1px solid {sector_color}44",
                "borderRadius":"3px",
                "padding":     "1px 7px",
                "fontSize":    "9px",
                "fontFamily":  FONT_MONO,
                "letterSpacing":"0.06em",
                "marginLeft":  "8px",
            }),
            _vol_ratio_badge(vol_ratio),
            # Deep-dive arrow hint (top-right)
            html.Span("→", style={
                "marginLeft":  "8px",
                "color":       C["text_dim"],
                "fontSize":    "13px",
                "transition":  "color 0.15s",
            }),
        ], style={"display":"flex","alignItems":"center","marginBottom":"4px"}),

        # Company name
        html.Div(name, style={**LABEL_STYLE, "marginBottom": "8px",
                               "whiteSpace":"nowrap","overflow":"hidden",
                               "textOverflow":"ellipsis","maxWidth":"190px"}),

        # Price row
        html.Div([
            html.Span(f"${price:,.2f}", style={
                "color":      C["text_white"],
                "fontFamily": FONT_MONO,
                "fontSize":   "18px",
                "fontWeight": "700",
            }),
        ], style={"marginBottom":"4px"}),

        # Change row
        html.Div([
            html.Span(f"{'+' if chg_abs >= 0 else ''}{chg_abs:.2f}", style={
                "color":      chg_color,
                "fontFamily": FONT_MONO,
                "fontSize":   "12px",
                "marginRight":"8px",
            }),
            html.Span(f"({'+' if chg_pct >= 0 else ''}{chg_pct:.2f}%)", style={
                "color":      chg_color,
                "fontFamily": FONT_MONO,
                "fontSize":   "12px",
                "fontWeight": "600",
            }),
        ], style={"marginBottom":"6px"}),

        # After-hours / pre-market badge
        _prepost_badge(data),

        # Sparkline placeholder (filled by callback)
        dcc.Graph(
            id={"type":"sparkline","index":ticker},
            config={"displayModeBar":False},
            style={"height":"50px","margin":"0 -4px"},
        ),

        # 52-week range bar
        _week52_bar(price, week52_low, week52_high),

        # Rating footer
        html.Div([
            html.Span(stars_str, style={
                "color":      "var(--accent)",
                "fontSize":   "12px",
                "marginRight":"8px",
            }),
            html.Span(advisory, style={
                "color":      adv_color,
                "fontFamily": FONT_MONO,
                "fontSize":   "10px",
                "fontWeight": "700",
                "letterSpacing":"0.08em",
            }),
        ], style={"display":"flex","alignItems":"center","marginTop":"6px",
                  "borderTop":f"1px solid {C['border']}","paddingTop":"6px"}),

    ], style={
        **CARD_STYLE,
        "cursor":     "pointer",
        "transition": "border-color 0.15s, background 0.15s",
    })

    # Transparent overlay captures clicks reliably (dcc.Graph absorbs events otherwise)
    overlay = html.Div(
        id={"type": "ticker-card", "index": ticker},
        n_clicks=0,
        style={
            "position":     "absolute",
            "top":          "0",
            "left":         "0",
            "right":        "0",
            "bottom":       "0",
            "cursor":       "pointer",
            "borderRadius": "4px",
            "zIndex":       "10",
        },
    )

    return html.Div(
        [card_inner, overlay],
        className="ticker-card-wrap",
        style={"position": "relative"},
    )


# ─────────────────────────────────────────────────────────────────────────────
# Deep Dive tab
# ─────────────────────────────────────────────────────────────────────────────

def build_deepdive_tab(initial_ticker: str = "NVDA",
                       tickers: list = None) -> html.Div:
    # Build dropdown options from the active portfolio tickers.
    # Falls back to PORTFOLIO_TICKERS if none are provided.
    active = tickers if tickers else PORTFOLIO_TICKERS

    # If the clicked ticker isn't in the active list, prepend it so the
    # dropdown always has a valid selection and the chart can load.
    if initial_ticker and initial_ticker not in active:
        active = [initial_ticker] + list(active)

    ticker_opts = [
        {"label": f"{t}  —  {TICKER_NAMES.get(t, t)}", "value": t}
        for t in active
    ]

    periods = ["1D", "5D", "1M", "3M", "6M", "1Y", "5Y"]

    def _period_btn(p):
        return html.Button(
            p,
            id={"type": "period-btn", "index": p},
            n_clicks=0,
            style={
                "background":    "transparent",
                "border":        f"1px solid {C['border']}",
                "borderRadius":  "2px",
                "color":         C["text_secondary"],
                "fontFamily":    FONT_MONO,
                "fontSize":      "10px",
                "fontWeight":    "600",
                "padding":       "4px 10px",
                "cursor":        "pointer",
                "letterSpacing": "0.06em",
            },
        )

    return html.Div([
        # Ticker + period selector row
        html.Div([
            html.Span("SELECT TICKER:", style={**LABEL_STYLE, "marginRight":"12px",
                                               "lineHeight":"36px"}),
            dcc.Dropdown(
                id        = "deepdive-ticker",
                options   = ticker_opts,
                value     = initial_ticker,
                clearable = False,
                style={
                    "width":       "320px",
                    "fontFamily":  FONT_MONO,
                    "fontSize":    "12px",
                    "background":  C["bg_panel"],
                    "color":       C["text_primary"],
                    "border":      f"1px solid {C['border']}",
                    "borderRadius":"3px",
                },
                className="bloomberg-dropdown",
            ),
            # Period selector buttons
            html.Div([
                html.Span("PERIOD:", style={**LABEL_STYLE, "marginRight":"8px",
                                            "lineHeight":"28px", "whiteSpace":"nowrap"}),
                html.Div([_period_btn(p) for p in periods],
                         style={"display":"flex","gap":"4px"}),
                # Hidden store for active period value
                dcc.Store(id="deepdive-period", data="6M"),
            ], style={"display":"flex","alignItems":"center","marginLeft":"24px"}),
        ], style={"display":"flex","alignItems":"center",
                  "marginBottom":"14px","gap":"0px","flexWrap":"wrap"}),

        # Two-column layout
        dbc.Row([
            # LEFT: charts
            dbc.Col([
                dcc.Graph(id="deepdive-chart",
                          config={"displayModeBar":True,
                                  "modeBarButtonsToRemove": ["lasso2d","select2d"],
                                  "displaylogo":False},
                          style={"height":"640px"}),
            ], width=8),

            # RIGHT: outlook panel
            dbc.Col([
                html.Div(id="deepdive-outlook"),
            ], width=4),
        ]),
    ], style={"padding":"14px 20px"})


def build_outlook_panel(data: dict, radar_fig=None, news_articles: list = None, fundamentals: dict = None, options_flow: dict = None) -> html.Div:
    """Right panel for Deep Dive: advisory, signals, radar, news — all inline."""
    ticker   = data.get("ticker","?")
    name     = data.get("name", ticker)
    price    = data.get("price")
    chg_pct  = data.get("chg_pct", 0.0)
    chg_abs  = data.get("chg_abs", 0.0)
    advisory = data.get("advisory","HOLD")
    stars    = data.get("stars", 3)
    score    = data.get("score", 0)
    signals  = data.get("signals", [])
    sector, sector_color = data.get("sector", ("Unknown", C["text_dim"]))
    adv_color = _advisory_color(advisory)
    chg_color = C["green"] if chg_pct >= 0 else C["red"]
    stars_str = "★" * stars + "☆" * (5 - stars)

    if radar_fig is None:
        radar_fig = {}

    news_section = build_news_section(news_articles or [], f"NEWS — {ticker}")

    # Signal rows
    signal_rows = []
    icon_map = {"BUY":"▲","SELL":"▼","NEUTRAL":"●"}
    col_map  = {"BUY":C["green"],"SELL":C["red"],"NEUTRAL":C["text_dim"]}
    for direction, indicator, desc in signals:
        icon  = icon_map.get(direction, "●")
        color = col_map.get(direction, C["text_dim"])
        signal_rows.append(html.Div([
            html.Span(f"{icon} ", style={"color":color,"fontFamily":FONT_MONO,"fontSize":"11px"}),
            html.Span(f"{indicator:<5}", style={"color":"var(--accent)","fontFamily":FONT_MONO,
                                                 "fontSize":"10px","fontWeight":"700",
                                                 "minWidth":"44px","display":"inline-block"}),
            html.Span(desc, style={"color":C["text_secondary"],"fontFamily":FONT_MONO,
                                   "fontSize":"10px"}),
        ], style={"padding":"3px 0","borderBottom":f"1px solid {C['border']}"}))

    return html.Div([

        # ── Header ────────────────────────────────────────────────────────────
        html.Div([
            html.Div([
                html.Span(ticker, style={"color":"var(--accent)","fontFamily":FONT_MONO,
                                         "fontSize":"20px","fontWeight":"800"}),
                html.Span(f"  {sector}", style={
                    "background":  sector_color + "22",
                    "color":       sector_color,
                    "border":      f"1px solid {sector_color}44",
                    "borderRadius":"3px","padding":"2px 8px",
                    "fontSize":"9px","fontFamily":FONT_MONO,
                    "letterSpacing":"0.06em","marginLeft":"8px",
                }),
            ], style={"display":"flex","alignItems":"center","marginBottom":"2px"}),
            html.Div(name, style={**LABEL_STYLE,"marginBottom":"8px"}),
            html.Div([
                html.Span(f"${price:,.2f} " if price else "N/A",
                          style={"color":C["text_white"],"fontFamily":FONT_MONO,
                                 "fontSize":"22px","fontWeight":"700"}),
                html.Span(f"{'+' if chg_pct>=0 else ''}{chg_pct:.2f}%",
                          style={"color":chg_color,"fontFamily":FONT_MONO,
                                 "fontSize":"14px","fontWeight":"600"}),
            ], style={"marginBottom":"6px"}),
            _prepost_badge(data),
        ], style={**CARD_STYLE, "marginBottom":"10px"}),

        # ── Advisory box ──────────────────────────────────────────────────────
        html.Div([
            html.Div(stars_str, style={
                "color":     "var(--accent)",
                "fontSize":  "22px",
                "textAlign": "center",
                "letterSpacing":"4px",
            }),
            html.Div(advisory, style={
                "color":      adv_color,
                "fontFamily": FONT_MONO,
                "fontSize":   "20px",
                "fontWeight": "900",
                "textAlign":  "center",
                "letterSpacing":"0.12em",
                "marginTop":  "4px",
            }),
            html.Div(f"Composite score: {score:+d}", style={
                **LABEL_STYLE,
                "textAlign":"center","marginTop":"6px",
            }),
        ], style={
            **CARD_STYLE,
            "borderColor": adv_color + "55",
            "background":  adv_color + "11",
            "marginBottom":"10px",
        }),

        # ── Fundamentals ──────────────────────────────────────────────────────
        build_fundamentals_panel(fundamentals or {}, data),

        # ── Options flow ──────────────────────────────────────────────────────
        build_options_flow_panel(options_flow or {}),

        # ── Signal radar ──────────────────────────────────────────────────────
        html.Div([
            html.Div("INDICATOR SIGNALS", style=SECTION_TITLE),
            dcc.Graph(
                figure=radar_fig,
                config={"displayModeBar":False},
                style={"height":"230px"},
            ),
        ], style=CARD_STYLE),

        # ── Signal table ──────────────────────────────────────────────────────
        html.Div([
            html.Div("SIGNAL BREAKDOWN", style=SECTION_TITLE),
            html.Div(signal_rows if signal_rows else
                     [html.Div("No signals", style=LABEL_STYLE)]),
        ], style={**CARD_STYLE, "marginTop":"10px"}),

        # ── News ──────────────────────────────────────────────────────────────
        html.Div(news_section, style={"marginTop":"10px"}),

    ], style={"height":"640px","overflowY":"auto","paddingRight":"4px"})


def build_fundamentals_panel(fund: dict, ticker_data: dict = None) -> html.Div:
    """Bloomberg-style fundamentals panel for Deep Dive right column."""
    if not fund:
        return html.Div()

    def _row(label, value, value_color=None):
        return html.Div([
            html.Span(label, style={**LABEL_STYLE, "flex": "1", "fontSize": "9px"}),
            html.Span(str(value) if value else "N/A", style={
                "color":      value_color or C["text_primary"],
                "fontFamily": FONT_MONO,
                "fontSize":   "11px",
                "fontWeight": "600",
                "textAlign":  "right",
            }),
        ], style={"display":"flex","alignItems":"center","padding":"3px 0",
                  "borderBottom":f"1px solid {C['border']}22"})

    # ── 52W range bar ─────────────────────────────────────────────────────────
    price    = (ticker_data or {}).get("price")
    low52    = fund.get("week52_low") or (ticker_data or {}).get("week52_low")
    high52   = fund.get("week52_high") or (ticker_data or {}).get("week52_high")
    range_bar = _week52_bar(price, low52, high52) if price and low52 and high52 else html.Div()

    # ── Analyst consensus bar ─────────────────────────────────────────────────
    buy_c  = fund.get("buy_count")  or 0
    hold_c = fund.get("hold_count") or 0
    sell_c = fund.get("sell_count") or 0
    total  = buy_c + hold_c + sell_c
    rec_mean = fund.get("rec_mean")

    if total > 0:
        buy_w  = f"{buy_c/total*100:.0f}%"
        hold_w = f"{hold_c/total*100:.0f}%"
        sell_w = f"{sell_c/total*100:.0f}%"
        consensus_bar = html.Div([
            html.Div([
                html.Span("ANALYST CONSENSUS", style={**LABEL_STYLE, "fontSize":"9px"}),
                html.Span(f"{fund.get('analyst_count', total)} analysts", style={
                    "color":C["text_dim"],"fontFamily":FONT_MONO,"fontSize":"9px","marginLeft":"auto",
                }),
            ], style={"display":"flex","marginBottom":"5px"}),
            html.Div([
                html.Div(style={"width":buy_w,  "height":"6px","background":C["green"],  "borderRadius":"2px 0 0 2px" if sell_c>0 else "2px"}),
                html.Div(style={"width":hold_w, "height":"6px","background":"var(--accent)"}),
                html.Div(style={"width":sell_w, "height":"6px","background":C["red"],    "borderRadius":"0 2px 2px 0" if sell_c>0 else "0"}),
            ], style={"display":"flex","borderRadius":"3px","overflow":"hidden","marginBottom":"4px"}),
            html.Div([
                html.Span(f"▲ {buy_c} BUY",  style={"color":C["green"],"fontFamily":FONT_MONO,"fontSize":"9px","marginRight":"8px"}),
                html.Span(f"● {hold_c} HOLD", style={"color":"var(--accent)","fontFamily":FONT_MONO,"fontSize":"9px","marginRight":"8px"}),
                html.Span(f"▼ {sell_c} SELL", style={"color":C["red"],  "fontFamily":FONT_MONO,"fontSize":"9px"}),
            ]),
        ], style={**CARD_STYLE, "marginBottom":"10px"})
    else:
        consensus_bar = html.Div()

    # OHLC today row
    td = ticker_data or {}
    ohlc_rows = []
    for label, key in [("OPEN", "day_open"), ("DAY HIGH", "day_high"), ("DAY LOW", "day_low")]:
        val = fund.get(key)
        if val:
            ohlc_rows.append(_row(label, f"${val:,.2f}"))

    return html.Div([
        html.Div("FUNDAMENTALS", style=SECTION_TITLE),

        # Core metrics grid
        html.Div([
            _row("MARKET CAP",   fund.get("market_cap")),
            _row("P/E (TTM)",    fund.get("pe_ttm")),
            _row("P/E (FWD)",    fund.get("pe_forward")),
            _row("EPS (TTM)",    fund.get("eps_ttm")),
            _row("BETA",         fund.get("beta")),
            _row("DIV YIELD",    fund.get("dividend_yield")),
            _row("SHORT FLOAT",  fund.get("short_float"),
                 C["red"] if fund.get("short_float", "0%") not in ("N/A", "0%") else None),
            _row("INST OWNED",   fund.get("inst_held")),
        ] + ohlc_rows + [
            _row("ANALYST TGT",  fund.get("target_price"), C["blue"]),
            _row("EARNINGS",     fund.get("earnings_date")),
        ], style={**CARD_STYLE, "marginBottom":"10px"}),

        # 52-week range
        html.Div([
            html.Div("52-WEEK RANGE", style={**LABEL_STYLE, "marginBottom":"6px"}),
            range_bar,
            html.Div([
                html.Span(f"L  ${low52:,.2f}" if low52 else "", style={"color":C["red"],"fontFamily":FONT_MONO,"fontSize":"9px"}),
                html.Span(f"H  ${high52:,.2f}" if high52 else "", style={"color":C["green"],"fontFamily":FONT_MONO,"fontSize":"9px"}),
            ], style={"display":"flex","justifyContent":"space-between"}),
        ], style={**CARD_STYLE, "marginBottom":"10px"}),

        consensus_bar,
    ])


def build_options_flow_panel(opt: dict) -> html.Div:
    """Options order flow panel for Deep Dive — P/C ratio, max pain, unusual activity."""
    if not opt or opt.get("error") == "No options data":
        return html.Div([
            html.Div("OPTIONS FLOW", style=SECTION_TITLE),
            html.Div("No options data available for this ticker.",
                     style={**LABEL_STYLE, "fontStyle":"italic"}),
        ], style={**CARD_STYLE, "marginBottom":"10px"})

    pc_vol   = opt.get("pc_vol_ratio")
    pc_oi    = opt.get("pc_oi_ratio")
    max_pain = opt.get("max_pain")
    curr_px  = opt.get("current_price")
    atm_iv_c = opt.get("atm_iv_call")
    atm_iv_p = opt.get("atm_iv_put")
    exp      = opt.get("expiration", "")
    call_vol = opt.get("total_call_vol") or 0
    put_vol  = opt.get("total_put_vol")  or 0
    u_calls  = opt.get("unusual_calls", [])
    u_puts   = opt.get("unusual_puts",  [])

    def _pc_color(ratio):
        if ratio is None: return C["text_dim"]
        if ratio > 1.3:   return C["red"]    # heavy put buying = bearish
        if ratio < 0.7:   return C["green"]  # heavy call buying = bullish
        return C["amber"]

    # Call/Put volume flow bar
    total_flow = call_vol + put_vol
    call_pct = f"{call_vol/total_flow*100:.0f}%" if total_flow > 0 else "50%"
    put_pct  = f"{put_vol/total_flow*100:.0f}%"  if total_flow > 0 else "50%"

    flow_bar = html.Div([
        html.Div([
            html.Span("CALLS", style={"color":C["green"],"fontFamily":FONT_MONO,"fontSize":"9px","fontWeight":"700"}),
            html.Span(f"  {call_vol:,}  {call_pct}", style={"color":C["green"],"fontFamily":FONT_MONO,"fontSize":"9px","marginLeft":"4px"}),
            html.Span("PUTS", style={"color":C["red"],"fontFamily":FONT_MONO,"fontSize":"9px","fontWeight":"700","marginLeft":"auto"}),
            html.Span(f"  {put_vol:,}  {put_pct}", style={"color":C["red"],"fontFamily":FONT_MONO,"fontSize":"9px","marginLeft":"4px"}),
        ], style={"display":"flex","marginBottom":"5px"}),
        html.Div([
            html.Div(style={"width":call_pct,"height":"6px","background":C["green"],"borderRadius":"2px 0 0 2px"}),
            html.Div(style={"width":put_pct, "height":"6px","background":C["red"],  "borderRadius":"0 2px 2px 0"}),
        ], style={"display":"flex","overflow":"hidden","borderRadius":"3px","marginBottom":"8px"}),
    ])

    # Key metrics
    def _row(label, value, color=None):
        return html.Div([
            html.Span(label, style={**LABEL_STYLE,"flex":"1","fontSize":"9px"}),
            html.Span(str(value) if value is not None else "N/A", style={
                "color":      color or C["text_primary"],
                "fontFamily": FONT_MONO, "fontSize":"11px", "fontWeight":"600",
            }),
        ], style={"display":"flex","alignItems":"center","padding":"3px 0",
                  "borderBottom":f"1px solid {C['border']}22"})

    mp_color = None
    if max_pain and curr_px:
        mp_color = C["green"] if max_pain > curr_px else C["red"]

    metrics = html.Div([
        _row("P/C VOL RATIO", f"{pc_vol:.2f}" if pc_vol else "N/A", _pc_color(pc_vol)),
        _row("P/C OI RATIO",  f"{pc_oi:.2f}"  if pc_oi  else "N/A", _pc_color(pc_oi)),
        _row("MAX PAIN",      f"${max_pain:,.2f}" if max_pain else "N/A", mp_color),
        _row("ATM IV CALL",   f"{atm_iv_c:.1f}%" if atm_iv_c else "N/A"),
        _row("ATM IV PUT",    f"{atm_iv_p:.1f}%" if atm_iv_p else "N/A"),
        _row("EXPIRY",        exp[:10] if exp else "N/A"),
    ], style={**CARD_STYLE, "marginBottom":"8px"})

    # Unusual activity tables
    def _unusual_table(rows, label, color):
        if not rows:
            return html.Div()
        hdr = html.Div([
            html.Span("STRIKE", style={**LABEL_STYLE,"flex":"1.5","fontSize":"8px"}),
            html.Span("VOL",    style={**LABEL_STYLE,"flex":"1","textAlign":"right","fontSize":"8px"}),
            html.Span("OI",     style={**LABEL_STYLE,"flex":"1","textAlign":"right","fontSize":"8px"}),
            html.Span("V/OI",   style={**LABEL_STYLE,"flex":"0.8","textAlign":"right","fontSize":"8px"}),
            html.Span("IV%",    style={**LABEL_STYLE,"flex":"0.8","textAlign":"right","fontSize":"8px"}),
        ], style={"display":"flex","padding":"3px 0","borderBottom":f"1px solid {C['border']}"})
        data_rows = [hdr]
        for r in rows:
            data_rows.append(html.Div([
                html.Span(f"${r['strike']:,.0f}", style={"flex":"1.5","fontFamily":FONT_MONO,"fontSize":"10px","color":color,"fontWeight":"700"}),
                html.Span(f"{r['volume']:,}",     style={"flex":"1","fontFamily":FONT_MONO,"fontSize":"10px","color":C["text_primary"],"textAlign":"right"}),
                html.Span(f"{r['oi']:,}",         style={"flex":"1","fontFamily":FONT_MONO,"fontSize":"10px","color":C["text_secondary"],"textAlign":"right"}),
                html.Span(f"{r['vol_oi']:.1f}×",  style={"flex":"0.8","fontFamily":FONT_MONO,"fontSize":"10px","color":"var(--accent)","textAlign":"right","fontWeight":"600"}),
                html.Span(f"{r['iv']:.0f}%",      style={"flex":"0.8","fontFamily":FONT_MONO,"fontSize":"10px","color":C["text_dim"],"textAlign":"right"}),
            ], style={"display":"flex","padding":"3px 0","borderBottom":f"1px solid {C['border']}11"}))
        return html.Div([
            html.Div([
                html.Span("⚡ UNUSUAL ", style={"color":"var(--accent)","fontFamily":FONT_MONO,"fontSize":"9px","fontWeight":"700"}),
                html.Span(label, style={"color":color,"fontFamily":FONT_MONO,"fontSize":"9px","fontWeight":"700"}),
            ], style={"marginBottom":"4px"}),
            html.Div(data_rows),
        ], style={**CARD_STYLE,"marginBottom":"6px"})

    return html.Div([
        html.Div("OPTIONS FLOW", style=SECTION_TITLE),
        flow_bar,
        metrics,
        _unusual_table(u_calls, "CALLS", C["green"]),
        _unusual_table(u_puts,  "PUTS",  C["red"]),
    ], style={"marginBottom":"10px"})


def build_news_card(article: dict) -> html.Div:
    return html.Div([
        html.A(
            article.get("title",""),
            href=article.get("link","#"),
            target="_blank",
            style={
                "color":          C["blue"],
                "fontFamily":     FONT_MONO,
                "fontSize":       "11px",
                "textDecoration": "none",
                "display":        "block",
                "marginBottom":   "3px",
                "lineHeight":     "1.4",
            },
        ),
        html.Div([
            html.Span(article.get("publisher",""), style={**LABEL_STYLE,"fontSize":"9px"}),
            html.Span("  ·  " + article.get("time",""),
                      style={**LABEL_STYLE,"fontSize":"9px","color":C["text_dim"]}),
        ]),
    ], style={
        "padding":      "7px 0",
        "borderBottom": f"1px solid {C['border']}",
    })


def build_news_section(articles: list, title: str = "RECENT NEWS") -> html.Div:
    if not articles:
        return html.Div([
            html.Div(title, style=SECTION_TITLE),
            html.Div("No news available", style=LABEL_STYLE),
        ], style=CARD_STYLE)

    return html.Div([
        html.Div(title, style=SECTION_TITLE),
        html.Div([build_news_card(a) for a in articles]),
    ], style=CARD_STYLE)


# ─────────────────────────────────────────────────────────────────────────────
# Market Monitor tab
# ─────────────────────────────────────────────────────────────────────────────

def build_market_tab() -> html.Div:
    return html.Div([
        # Futures strip — full width, top of page
        html.Div([
            html.Div("FUTURES  ·  EXTENDED HOURS", style={**SECTION_TITLE, "marginBottom":"10px"}),
            html.Div(id="market-futures"),
        ], style={
            "background":   C["bg_panel"],
            "border":       f"1px solid {C['border']}",
            "borderLeft":   f"3px solid {C['blue']}",
            "borderRadius": "4px",
            "padding":      "12px 16px",
            "marginBottom": "14px",
        }),

        dbc.Row([
            dbc.Col([
                html.Div("INDICES", style=SECTION_TITLE),
                html.Div(id="market-indices"),
            ], width=6),
            dbc.Col([
                html.Div("CRYPTO", style=SECTION_TITLE),
                html.Div(id="market-crypto"),
            ], width=6),
        ], style={"marginBottom":"14px"}),
        dbc.Row([
            dbc.Col([
                html.Div("COMMODITIES", style=SECTION_TITLE),
                html.Div(id="market-commodities"),
            ], width=6),
            dbc.Col([
                html.Div("FX", style=SECTION_TITLE),
                html.Div(id="market-fx"),
            ], width=6),
        ]),
    ], style={"padding":"14px 20px"})


def build_market_table(rows: list) -> html.Div:
    """Render a market monitor section table."""
    if not rows:
        return html.Div("Loading…", style=LABEL_STYLE)

    header = html.Div([
        html.Span("NAME",     style={**LABEL_STYLE,"flex":"2"}),
        html.Span("PRICE",    style={**LABEL_STYLE,"flex":"2","textAlign":"right"}),
        html.Span("CHG",      style={**LABEL_STYLE,"flex":"1.5","textAlign":"right"}),
        html.Span("CHG %",    style={**LABEL_STYLE,"flex":"1.5","textAlign":"right"}),
        html.Span("YTD %",    style={**LABEL_STYLE,"flex":"1.5","textAlign":"right"}),
    ], style={"display":"flex","padding":"4px 0","borderBottom":f"1px solid {C['border']}",
              "marginBottom":"4px"})

    data_rows = []
    for r in rows:
        chg_color = C["green"] if r["chg_pct"] >= 0 else C["red"]
        ytd_color = C["green"] if r["ytd_pct"] >= 0 else C["red"]
        sign      = "+" if r["chg_pct"] >= 0 else ""

        data_rows.append(html.Div([
            html.Span(r["name"],
                      style={"flex":"2","fontFamily":FONT_MONO,"fontSize":"11px",
                             "color":C["text_primary"]}),
            html.Span(f"{r['price']:,.2f}",
                      style={"flex":"2","fontFamily":FONT_MONO,"fontSize":"11px",
                             "color":C["text_white"],"textAlign":"right"}),
            html.Span(f"{sign}{r['chg_abs']:,.2f}",
                      style={"flex":"1.5","fontFamily":FONT_MONO,"fontSize":"11px",
                             "color":chg_color,"textAlign":"right"}),
            html.Span(f"{sign}{r['chg_pct']:.2f}%",
                      style={"flex":"1.5","fontFamily":FONT_MONO,"fontSize":"11px",
                             "color":chg_color,"textAlign":"right","fontWeight":"600"}),
            html.Span(f"{'+' if r['ytd_pct']>=0 else ''}{r['ytd_pct']:.1f}%",
                      style={"flex":"1.5","fontFamily":FONT_MONO,"fontSize":"11px",
                             "color":ytd_color,"textAlign":"right"}),
        ], style={"display":"flex","padding":"5px 0",
                  "borderBottom":f"1px solid {C['border']}22"}))

    return html.Div([header] + data_rows,
                    style={**CARD_STYLE, "padding":"10px 14px"})


def build_futures_table(rows: list) -> html.Div:
    """Futures strip — horizontal ticker-tape style with LIVE/SETTLED badge."""
    if not rows:
        return html.Div("Loading futures…", style=LABEL_STYLE)

    chips = []
    for r in rows:
        chg_color = C["green"] if r["chg_pct"] >= 0 else C["red"]
        sign      = "+" if r["chg_pct"] >= 0 else ""
        session   = r.get("session", "")
        sess_color = C["green"] if session == "LIVE" else C["text_dim"]

        chips.append(html.Div([
            # Name + session badge
            html.Div([
                html.Span(r["name"], style={
                    "color":      C["text_primary"],
                    "fontFamily": FONT_MONO,
                    "fontSize":   "11px",
                    "fontWeight": "600",
                    "marginRight":"8px",
                }),
                html.Span(session, style={
                    "background":  sess_color + "22",
                    "color":       sess_color,
                    "border":      f"1px solid {sess_color}55",
                    "borderRadius":"3px",
                    "padding":     "0px 5px",
                    "fontSize":    "8px",
                    "fontFamily":  FONT_MONO,
                    "fontWeight":  "700",
                    "letterSpacing":"0.06em",
                }),
            ], style={"display":"flex","alignItems":"center","marginBottom":"4px"}),
            # Price
            html.Div(f"{r['price']:,.2f}", style={
                "color":      C["text_white"],
                "fontFamily": FONT_MONO,
                "fontSize":   "14px",
                "fontWeight": "700",
            }),
            # Change
            html.Div(f"{sign}{r['chg_pct']:.2f}%", style={
                "color":      chg_color,
                "fontFamily": FONT_MONO,
                "fontSize":   "11px",
                "fontWeight": "600",
            }),
            # YTD
            html.Div(f"YTD {'+' if r['ytd_pct']>=0 else ''}{r['ytd_pct']:.1f}%", style={
                "color":      C["text_dim"],
                "fontFamily": FONT_MONO,
                "fontSize":   "9px",
                "marginTop":  "2px",
            }),
        ], style={
            "background":   C["bg_chart"],
            "border":       f"1px solid {C['border']}",
            "borderRadius": "4px",
            "padding":      "10px 14px",
            "minWidth":     "150px",
            "flex":         "1",
        }))

    return html.Div(chips, style={
        "display":   "flex",
        "gap":       "10px",
        "flexWrap":  "wrap",
    })


# ─────────────────────────────────────────────────────────────────────────────
# News Feed tab
# ─────────────────────────────────────────────────────────────────────────────

def build_newsfeed_tab() -> html.Div:
    return html.Div([
        html.Div("PORTFOLIO NEWS FEED", style=SECTION_TITLE),
        html.Div(id="news-feed-content"),
    ], style={"padding":"14px 20px"})


def _source_badge(tag: str, color: str) -> html.Span:
    return html.Span(tag, style={
        "background":    color + "22",
        "color":         color,
        "border":        f"1px solid {color}55",
        "borderRadius":  "3px",
        "padding":       "1px 7px",
        "fontSize":      "9px",
        "fontFamily":    FONT_MONO,
        "fontWeight":    "700",
        "letterSpacing": "0.06em",
        "marginRight":   "8px",
        "whiteSpace":    "nowrap",
    })


def _ticker_badge(ticker: str) -> html.Span:
    return html.Span(ticker, style={
        "background":    "color-mix(in srgb, var(--accent) 13%, transparent)",
        "color":         "var(--accent)",
        "border":        "1px solid color-mix(in srgb, var(--accent) 27%, transparent)",
        "borderRadius":  "3px",
        "padding":       "1px 7px",
        "fontSize":      "9px",
        "fontFamily":    FONT_MONO,
        "fontWeight":    "700",
        "letterSpacing": "0.06em",
        "marginRight":   "8px",
    })


def _news_article_card(a: dict) -> html.Div:
    ticker       = a.get("ticker", "")
    source_tag   = a.get("source_tag",   a.get("publisher", "NEWS"))
    source_color = a.get("source_color", C["text_secondary"])
    summary      = a.get("summary", "")

    badges = []
    if ticker:
        badges.append(_ticker_badge(ticker))
    badges.append(_source_badge(source_tag, source_color))

    return html.Div([
        # Badge row + time
        html.Div([
            html.Div(badges, style={"display": "flex", "alignItems": "center",
                                    "flexWrap": "wrap", "gap": "4px"}),
            html.Span(a.get("time", ""), style={
                **LABEL_STYLE, "fontSize": "9px", "marginLeft": "auto",
                "whiteSpace": "nowrap",
            }),
        ], style={"display": "flex", "alignItems": "center",
                  "marginBottom": "5px", "gap": "6px"}),
        # Headline
        html.A(
            a.get("title", ""),
            href=a.get("link", "#"), target="_blank",
            style={
                "color":          C["blue"],
                "fontFamily":     FONT_MONO,
                "fontSize":       "12px",
                "fontWeight":     "500",
                "textDecoration": "none",
                "lineHeight":     "1.5",
                "display":        "block",
                "marginBottom":   "4px",
            },
        ),
        # Summary snippet (if available)
        html.Div(summary, style={
            **LABEL_STYLE,
            "fontSize":   "10px",
            "lineHeight": "1.4",
            "display":    "block" if summary else "none",
        }) if summary else None,
    ], style={
        "padding":      "10px 14px",
        "background":   C["bg_panel"],
        "border":       f"1px solid {C['border']}",
        "borderLeft":   f"3px solid {source_color}",
        "borderRadius": "3px",
        "marginBottom": "6px",
        "transition":   "border-color 0.15s",
    })


def build_news_feed(portfolio_news: list = None, rss_news: list = None) -> html.Div:
    """
    Two-column news feed:
      Left  — Portfolio ticker news (from yfinance, ticker-tagged)
      Right — Market news from RSS sources (Reuters, CNBC, MarketWatch, etc.)
    """
    portfolio_news = portfolio_news or []
    rss_news       = rss_news or []

    left_items  = [_news_article_card(a) for a in portfolio_news] if portfolio_news else [
        html.Div("No portfolio news available.", style=LABEL_STYLE)
    ]
    right_items = [_news_article_card(a) for a in rss_news] if rss_news else [
        html.Div("No market news available — check your internet connection.",
                 style=LABEL_STYLE)
    ]

    return dbc.Row([
        dbc.Col([
            html.Div("YOUR PORTFOLIO", style=SECTION_TITLE),
            html.Div(left_items, style={"overflowY": "auto", "maxHeight": "80vh"}),
        ], width=5),
        dbc.Col([
            html.Div("MARKET NEWS", style=SECTION_TITLE),
            html.Div(right_items, style={"overflowY": "auto", "maxHeight": "80vh"}),
        ], width=7),
    ])


# ─────────────────────────────────────────────────────────────────────────────
# Settings tab
# ─────────────────────────────────────────────────────────────────────────────

def _input_style(width="100%") -> dict:
    return {
        "background":   C["bg"],
        "border":       f"1px solid {C['border']}",
        "borderRadius": "3px",
        "color":        C["text_primary"],
        "fontFamily":   FONT_MONO,
        "fontSize":     "12px",
        "padding":      "7px 10px",
        "width":        width,
        "outline":      "none",
    }

def _btn_style(variant="primary") -> dict:
    color  = "var(--accent)" if variant == "primary" else C["text_secondary"]
    return {
        "background":    "transparent",
        "border":        f"1px solid {color}",
        "borderRadius":  "3px",
        "color":         color,
        "fontFamily":    FONT_MONO,
        "fontSize":      "10px",
        "fontWeight":    "700",
        "letterSpacing": "0.08em",
        "padding":       "6px 14px",
        "cursor":        "pointer",
        "textTransform": "uppercase",
    }


def build_settings_tab(settings: dict = None) -> html.Div:
    """Full settings page: appearance, portfolio manager, ticker feed."""
    if settings is None:
        settings = DEFAULT_SETTINGS

    theme            = settings.get("theme", "dark")
    active_port_key  = settings.get("active_portfolio", "default")
    portfolios       = settings.get("portfolios", DEFAULT_SETTINGS["portfolios"])
    active_port      = portfolios.get(active_port_key, list(portfolios.values())[0])
    active_tickers   = active_port.get("tickers", PORTFOLIO_TICKERS)
    active_name      = active_port.get("name", "My Portfolio")
    port_options     = [{"label": v["name"], "value": k} for k, v in portfolios.items()]

    # All known tickers (union of active + presets)
    all_preset = list({t for grp in PRESET_TICKERS.values() for t in grp})

    # ── Section: Appearance ───────────────────────────────────────────────────
    appearance_section = html.Div([
        html.Div("APPEARANCE", style=SECTION_TITLE),

        html.Div("Theme", style={**LABEL_STYLE, "marginBottom": "10px"}),
        html.Div([
            _theme_btn("🌑  DARK",  "dark",  theme),
            _theme_btn("☀  LIGHT", "light", theme),
        ], style={"display": "flex", "gap": "10px", "marginBottom": "20px"}),

        html.Div("Accent Color", style={**LABEL_STYLE, "marginBottom": "10px"}),
        html.Div([
            _accent_swatch("#fbbf24", "Amber",  settings.get("accent", "#fbbf24")),
            _accent_swatch("#38bdf8", "Blue",   settings.get("accent", "#fbbf24")),
            _accent_swatch("#4ade80", "Green",  settings.get("accent", "#fbbf24")),
            _accent_swatch("#a78bfa", "Purple", settings.get("accent", "#fbbf24")),
            _accent_swatch("#f97316", "Orange", settings.get("accent", "#fbbf24")),
        ], style={"display": "flex", "gap": "8px", "marginBottom": "20px"}),

        html.Div(id="settings-appearance-status", style={
            **LABEL_STYLE, "color": C["green"], "fontSize": "10px",
        }),
    ], style={**CARD_STYLE, "marginBottom": "12px"})

    # ── Section: Portfolio Manager ────────────────────────────────────────────
    portfolio_section = html.Div([
        html.Div("PORTFOLIO MANAGER", style=SECTION_TITLE),

        # Active portfolio selector
        html.Div("Active Portfolio", style={**LABEL_STYLE, "marginBottom": "6px"}),
        html.Div([
            dcc.Dropdown(
                id="settings-portfolio-select",
                options=port_options,
                value=active_port_key,
                clearable=False,
                style={**_input_style(), "marginBottom": "10px"},
            ),
        ]),

        # Portfolio name
        html.Div("Portfolio Name", style={**LABEL_STYLE, "marginBottom": "6px"}),
        dcc.Input(
            id="settings-portfolio-name",
            type="text",
            value=active_name,
            placeholder="e.g. Tech Growth",
            debounce=True,
            style={**_input_style(), "marginBottom": "12px"},
        ),

        # New portfolio button
        html.Div([
            html.Button("+ NEW PORTFOLIO", id="settings-new-portfolio-btn",
                        n_clicks=0, style=_btn_style("secondary")),
            html.Button("🗑 DELETE", id="settings-delete-portfolio-btn",
                        n_clicks=0, style={**_btn_style("secondary"),
                                           "color": C["red"], "borderColor": C["red"],
                                           "marginLeft": "8px"}),
        ], style={"marginBottom": "16px"}),

        html.Div(id="settings-portfolio-msg", style={
            **LABEL_STYLE, "color": C["green"], "fontSize": "10px",
        }),
    ], style={**CARD_STYLE, "marginBottom": "12px"})

    # ── Section: Ticker Feed ──────────────────────────────────────────────────
    # Build preset quick-add buttons grouped by category.
    # Track already-rendered tickers so the same symbol never gets two DOM
    # elements with identical Dash pattern-matching IDs (which breaks clicks).
    preset_groups = []
    _seen_presets = set()
    for category, cat_tickers in PRESET_TICKERS.items():
        btns = []
        for t in cat_tickers:
            if t in _seen_presets:
                continue          # skip — already rendered in an earlier group
            _seen_presets.add(t)
            btns.append(
                html.Span(t, id={"type": "preset-ticker-btn", "index": t},
                          n_clicks=0,
                          style={
                              "background":  "color-mix(in srgb, var(--accent) 7%, transparent)" if t in active_tickers else "transparent",
                              "border":      f"1px solid {'var(--accent)' if t in active_tickers else C['border']}",
                              "borderRadius":"3px",
                              "color":       "var(--accent)" if t in active_tickers else C["text_secondary"],
                              "fontFamily":  FONT_MONO,
                              "fontSize":    "10px",
                              "fontWeight":  "600",
                              "padding":     "3px 9px",
                              "cursor":      "pointer",
                              "userSelect":  "none",
                          })
            )
        if btns:
            preset_groups.append(html.Div([
                html.Div(category, style={**LABEL_STYLE, "marginBottom": "6px",
                                          "marginTop": "10px"}),
                html.Div(btns, style={"display": "flex", "flexWrap": "wrap", "gap": "6px"}),
            ]))

    ticker_section = html.Div([
        html.Div("TICKER FEED", style=SECTION_TITLE),

        # Current tickers in active portfolio
        html.Div("Active Tickers", style={**LABEL_STYLE, "marginBottom": "8px"}),
        html.Div(id="settings-active-tickers",
                 children=_render_active_tickers(active_tickers)),

        # Custom ticker input
        html.Div("Add Custom Ticker", style={**LABEL_STYLE,
                                              "marginTop": "14px", "marginBottom": "6px"}),
        html.Div([
            dcc.Input(
                id="settings-custom-ticker-input",
                type="text",
                placeholder="e.g. AAPL",
                debounce=False,
                maxLength=10,
                style={**_input_style("140px"), "textTransform": "uppercase"},
            ),
            html.Button("ADD", id="settings-add-ticker-btn",
                        n_clicks=0,
                        style={**_btn_style("primary"), "marginLeft": "8px"}),
        ], style={"display": "flex", "alignItems": "center", "marginBottom": "14px"}),

        # Preset quick-add
        html.Div("Quick Add by Category", style={**LABEL_STYLE, "marginBottom": "4px"}),
        html.Div(preset_groups),

        html.Div(style={"marginTop": "16px"}),
        html.Button("💾  SAVE CHANGES", id="settings-save-btn",
                    n_clicks=0, style={**_btn_style("primary"), "width": "100%",
                                       "padding": "10px", "fontSize": "11px"}),
        html.Div(id="settings-save-status", style={
            **LABEL_STYLE, "color": C["green"], "fontSize": "10px",
            "marginTop": "8px", "textAlign": "center",
        }),

    ], style={**CARD_STYLE, "marginBottom": "12px"})

    alerts_section = build_alerts_section(settings)

    return html.Div([
        dbc.Row([
            dbc.Col(appearance_section,  width=3),
            dbc.Col(portfolio_section,   width=3),
            dbc.Col(ticker_section,      width=6),
        ]),
        dbc.Row([
            dbc.Col(alerts_section, width=12),
        ], style={"marginTop": "12px"}),
    ], style={"padding": "14px 20px"})


def _theme_btn(label: str, value: str, current: str) -> html.Button:
    active = value == current
    return html.Button(
        label,
        id={"type": "theme-btn", "index": value},
        n_clicks=0,
        style={
            "background":    "color-mix(in srgb, var(--accent) 13%, transparent)" if active else "transparent",
            "border":        f"1px solid {'var(--accent)' if active else C['border']}",
            "borderRadius":  "3px",
            "color":         "var(--accent)" if active else C["text_secondary"],
            "fontFamily":    FONT_MONO,
            "fontSize":      "11px",
            "fontWeight":    "700" if active else "400",
            "padding":       "8px 18px",
            "cursor":        "pointer",
            "letterSpacing": "0.06em",
            "flex":          "1",
            "textAlign":     "center",
        },
    )


def _accent_swatch(color: str, label: str, current: str) -> html.Div:
    active = color == current
    return html.Div(
        id={"type": "accent-btn", "index": color},
        n_clicks=0,
        title=label,
        style={
            "width":        "28px",
            "height":       "28px",
            "borderRadius": "50%",
            "background":   color,
            "cursor":       "pointer",
            "border":       f"3px solid {'white' if active else 'transparent'}",
            "boxShadow":    f"0 0 0 2px {color}" if active else "none",
            "transition":   "box-shadow 0.15s",
        },
    )


def _render_active_tickers(tickers: list) -> list:
    """Render the removable ticker chips for the active portfolio."""
    if not tickers:
        return [html.Div("No tickers added yet.", style=LABEL_STYLE)]
    chips = []
    for t in tickers:
        chips.append(html.Span([
            html.Span(t, style={"marginRight": "4px"}),
            html.Span("×",
                      id={"type": "remove-ticker-btn", "index": t},
                      n_clicks=0,
                      style={"cursor": "pointer", "color": C["red"],
                             "fontWeight": "700", "fontSize": "12px"}),
        ], style={
            "background":   C["bg"],
            "border":       f"1px solid {C['border']}",
            "borderRadius": "3px",
            "color":        C["text_primary"],
            "fontFamily":   FONT_MONO,
            "fontSize":     "11px",
            "fontWeight":   "600",
            "padding":      "4px 10px",
            "display":      "inline-flex",
            "alignItems":   "center",
            "gap":          "4px",
        }))
    return html.Div(chips, style={"display": "flex", "flexWrap": "wrap", "gap": "6px"})


# ─────────────────────────────────────────────────────────────────────────────
# Full page wrapper
# ─────────────────────────────────────────────────────────────────────────────

def build_ticker_tape() -> html.Div:
    """Scrolling live price tape — populated by callback, animates via CSS."""
    return html.Div([
        html.Div([
            html.Span("LIVE  ", style={
                "color":        C["green"],
                "fontFamily":   FONT_MONO,
                "fontSize":     "9px",
                "fontWeight":   "700",
                "letterSpacing":"0.12em",
                "padding":      "0 10px",
                "borderRight":  f"1px solid {C['border']}",
                "whiteSpace":   "nowrap",
            }),
        ], style={"flexShrink":"0","display":"flex","alignItems":"center",
                  "background":C["bg_panel"],"zIndex":"2"}),
        html.Div(
            html.Div(id="ticker-tape-inner", children="Loading…",
                     style={"display":"inline-flex","gap":"0px","whiteSpace":"nowrap"}),
            style={"overflow":"hidden","flex":"1"},
        ),
    ], style={
        "display":      "flex",
        "alignItems":   "center",
        "background":   C["bg_panel"],
        "borderBottom": f"1px solid {C['border']}",
        "height":       "28px",
        "overflow":     "hidden",
    })


def build_alerts_section(settings: dict) -> html.Div:
    """Alerts configuration section for the Settings tab."""
    alerts = settings.get("alerts", [])

    TYPE_LABELS = {
        "above":      "▲ Price Above",
        "below":      "▼ Price Below",
        "pct_change": "± % Change ≥",
    }

    # Render existing alert rows
    alert_rows = []
    for a in alerts:
        t     = a.get("ticker", "")
        atype = a.get("type", "above")
        thr   = a.get("threshold", 0)
        label = TYPE_LABELS.get(atype, atype)
        suffix = "%" if atype == "pct_change" else f"${thr:,.2f}"
        display = f"${thr:,.2f}" if atype != "pct_change" else f"{thr}%"
        alert_rows.append(html.Div([
            html.Span(t, style={"color":"var(--accent)","fontFamily":FONT_MONO,
                                "fontSize":"11px","fontWeight":"700","minWidth":"50px"}),
            html.Span(f"{label}  {display}",
                      style={"color":C["text_secondary"],"fontFamily":FONT_MONO,
                             "fontSize":"10px","flex":"1","marginLeft":"8px"}),
            html.Span("×", id={"type":"alert-remove-btn","index": a.get("id","")},
                      n_clicks=0,
                      style={"color":C["text_dim"],"cursor":"pointer","fontFamily":FONT_MONO,
                             "fontSize":"14px","padding":"0 4px","lineHeight":"1",
                             "userSelect":"none"}),
        ], style={"display":"flex","alignItems":"center","padding":"5px 8px",
                  "borderBottom":f"1px solid {C['border']}",
                  "borderRadius":"3px","marginBottom":"3px",
                  "background":C["bg_hover"]}))

    if not alert_rows:
        alert_rows = [html.Div("No alerts set.", style={
            **LABEL_STYLE,"color":C["text_dim"],"fontStyle":"italic","padding":"6px 0"
        })]

    return html.Div([
        html.Div("PRICE ALERTS", style=SECTION_TITLE),

        # Add alert form
        html.Div([
            dcc.Input(id="alert-ticker-input", type="text", placeholder="Ticker",
                      debounce=False, maxLength=6,
                      style={**_input_style("90px"), "textTransform":"uppercase"}),
            dcc.Dropdown(
                id="alert-type-select",
                options=[
                    {"label": "▲ Price Above",  "value": "above"},
                    {"label": "▼ Price Below",  "value": "below"},
                    {"label": "± Daily % ≥",    "value": "pct_change"},
                ],
                value="above", clearable=False,
                style={"width":"140px","fontFamily":FONT_MONO,"fontSize":"11px",
                       "background":C["bg_panel"],"color":C["text_primary"],
                       "border":f"1px solid {C['border']}","borderRadius":"3px",
                       "marginLeft":"6px"},
                className="bloomberg-dropdown",
            ),
            dcc.Input(id="alert-threshold-input", type="number", placeholder="Value",
                      debounce=False, min=0,
                      style={**_input_style("80px"), "marginLeft":"6px"}),
            html.Button("+ ADD", id="alert-add-btn", n_clicks=0,
                        style={**_btn_style("primary"), "marginLeft":"8px",
                               "padding":"6px 14px"}),
        ], style={"display":"flex","alignItems":"center","marginBottom":"12px",
                  "flexWrap":"wrap","gap":"0px"}),

        # Status message
        html.Div(id="alert-status-msg", style={
            **LABEL_STYLE,"color":C["green"],"fontSize":"10px","marginBottom":"8px"
        }),

        # Active alerts list
        html.Div("Active Alerts", style={**LABEL_STYLE,"marginBottom":"6px"}),
        html.Div(alert_rows, id="alert-list-display"),

    ], style={**CARD_STYLE, "marginBottom":"12px"})


def build_notifications_banner() -> html.Div:
    """Fixed notification strip that appears when alerts trigger."""
    return html.Div(
        id="notifications-banner",
        children=[],
        style={
            "position":   "fixed",
            "bottom":     "16px",
            "right":      "16px",
            "zIndex":     "9999",
            "display":    "flex",
            "flexDirection": "column",
            "gap":        "6px",
            "maxWidth":   "360px",
        }
    )


def build_app_layout() -> html.Div:
    return html.Div([
        # Interval timers
        dcc.Interval(id="interval-1s",  interval=1_000,   n_intervals=0),
        dcc.Interval(id="interval-data",interval=60_000,  n_intervals=0),  # 60s data refresh

        # Stores for cached data
        dcc.Store(id="store-portfolio"),
        dcc.Store(id="store-market"),
        dcc.Store(id="store-refresh-ts", data=0),
        dcc.Store(id="selected-ticker",  data="NVDA"),
        # User settings — persisted in browser localStorage across sessions
        dcc.Store(id="user-settings", storage_type="local", data=DEFAULT_SETTINGS),
        # Active triggered notifications — ephemeral (cleared on reload)
        dcc.Store(id="store-notifications", data=[]),

        # Navbar
        build_navbar(),

        # Scrolling ticker tape (below navbar)
        build_ticker_tape(),

        # Notifications banner (fixed bottom-right)
        build_notifications_banner(),

        # Page content
        html.Div(id="page-content", style={"minHeight":"calc(100vh - 74px)"}),

    ], style={
        "background":  C["bg"],
        "minHeight":   "100vh",
        "fontFamily":  FONT_MONO,
    })
