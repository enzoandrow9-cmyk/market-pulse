# ─────────────────────────────────────────────────────────────────────────────
# layouts.py  —  Bloomberg Terminal Dashboard  •  Enzo Market Pulse
# All Dash component layouts — returns dash HTML/component trees
# ─────────────────────────────────────────────────────────────────────────────

from dash import html, dcc
import dash_bootstrap_components as dbc

from config import C, CHART, PORTFOLIO_TICKERS, TICKER_NAMES, TICKER_SECTOR, PRESET_TICKERS, DEFAULT_SETTINGS

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

_NAV_TABS = [
    ("◈", "PORTFOLIO",    "portfolio"),
    ("⊕", "DEEP DIVE",    "deepdive"),
    ("▦", "MARKET",       "market"),
    ("⬡", "QUANT LAB",   "quantlab"),
    ("◆", "INTELLIGENCE", "intelligence"),
    ("▧", "CALENDAR",     "calendar"),
    ("≡", "NEWS",         "news"),
    ("⚙", "SETTINGS",    "settings"),
]

NAV_BTN_STYLE = {
    "display":       "flex",
    "alignItems":    "center",
    "gap":           "10px",
    "width":         "100%",
    "padding":       "13px 20px",
    "fontFamily":    FONT_MONO,
    "fontSize":      "10px",
    "fontWeight":    "600",
    "letterSpacing": "0.10em",
    "textTransform": "uppercase",
    "color":         C["text_secondary"],
    "background":    "transparent",
    "border":        "none",
    "borderLeft":    "3px solid transparent",
    "cursor":        "pointer",
    "textAlign":     "left",
    "whiteSpace":    "nowrap",
    "boxSizing":     "border-box",
}

NAV_BTN_ACTIVE_STYLE = {
    **NAV_BTN_STYLE,
    "color":       "var(--accent)",
    "borderLeft":  "3px solid var(--accent)",
    "background":  C["bg_hover"],
}


def build_navbar() -> html.Div:
    """Topbar — clock + refresh only. Offset right of the fixed sidebar."""
    return html.Div([
        html.Span(id="clock-display",
                  style={"color": C["text_secondary"], "fontFamily": FONT_MONO,
                         "fontSize": "11px", "marginRight": "16px"}),
        html.Button("⟳ REFRESH", id="refresh-btn",
                    style={
                        "background":   "transparent",
                        "border":       "1px solid var(--accent)",
                        "color":        "var(--accent)",
                        "fontFamily":   FONT_MONO,
                        "fontSize":     "10px",
                        "padding":      "5px 12px",
                        "cursor":       "pointer",
                        "borderRadius": "2px",
                        "letterSpacing":"0.08em",
                    }),
    ], style={
        "display":        "flex",
        "alignItems":     "center",
        "justifyContent": "flex-end",
        "background":     C["bg_panel"],
        "borderBottom":   f"1px solid {C['border']}",
        "padding":        "0 20px",
        "height":         "46px",
        "position":       "sticky",
        "top":            "0",
        "zIndex":         "999",
        "marginLeft":     "160px",
    })


def build_sidebar() -> html.Div:
    """Fixed left sidebar — brand block + nav buttons."""
    return html.Div([
        # Brand block — same 46px height as topbar
        html.Div([
            html.Span("◈", style={"color": "var(--accent)", "fontSize": "18px",
                                   "marginRight": "10px"}),
            html.Div([
                html.Div("MARKET PULSE", style={
                    "color": C["text_white"], "fontFamily": FONT_MONO,
                    "fontSize": "11px", "fontWeight": "900", "letterSpacing": "0.12em",
                }),
                html.Div("TERMINAL", style={
                    "color": C["text_dim"], "fontFamily": FONT_MONO,
                    "fontSize": "8px", "letterSpacing": "0.18em", "marginTop": "2px",
                }),
            ]),
        ], style={
            "display": "flex", "alignItems": "center",
            "height": "46px", "padding": "0 16px",
            "borderBottom": f"1px solid {C['border']}",
            "flexShrink": "0", "boxSizing": "border-box",
        }),

        # 28px spacer — aligns with ticker tape strip height
        html.Div(style={
            "height": "28px",
            "borderBottom": f"1px solid {C['border']}",
            "flexShrink": "0",
        }),

        # Nav buttons
        *[html.Button(
            [
                html.Span(icon, style={"fontSize": "13px", "width": "18px",
                                        "textAlign": "center", "flexShrink": "0"}),
                html.Span(label),
            ],
            id=f"nav-btn-{val}",
            n_clicks=0,
            style=NAV_BTN_ACTIVE_STYLE if val == "portfolio" else NAV_BTN_STYLE,
        ) for icon, label, val in _NAV_TABS],

    ], style={
        "position":    "fixed",
        "top":         "0",
        "left":        "0",
        "width":       "160px",
        "height":      "100vh",
        "background":  C["bg_panel"],
        "borderRight": f"1px solid {C['border']}",
        "display":     "flex",
        "flexDirection":"column",
        "zIndex":      "1000",
        "overflowY":   "auto",
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
        # Fear & Greed + Futures strip — side by side, full width
        html.Div([
            # Fear & Greed gauge
            html.Div([
                html.Div("FEAR & GREED INDEX", style={**SECTION_TITLE, "marginBottom": "6px"}),
                dcc.Graph(
                    id="fear-greed-gauge",
                    config={"displayModeBar": False},
                    style={"height": "200px"},
                ),
                # Sub-labels: previous close / week / month
                html.Div(id="fear-greed-labels", style={
                    "display": "flex", "justifyContent": "space-around",
                    "marginTop": "4px",
                }),
            ], style={
                "background":   C["bg_panel"],
                "border":       f"1px solid {C['border']}",
                "borderLeft":   f"3px solid var(--accent)",
                "borderRadius": "4px",
                "padding":      "12px 16px",
                "flex":         "0 0 280px",
            }),

            # Futures strip
            html.Div([
                html.Div("FUTURES  ·  EXTENDED HOURS", style={**SECTION_TITLE, "marginBottom": "10px"}),
                html.Div(id="market-futures"),
            ], style={
                "background":   C["bg_panel"],
                "border":       f"1px solid {C['border']}",
                "borderLeft":   f"3px solid {C['blue']}",
                "borderRadius": "4px",
                "padding":      "12px 16px",
                "flex":         "1",
            }),
        ], style={
            "display": "flex", "gap": "14px", "marginBottom": "14px",
            "alignItems": "stretch",
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
                html.Div("BONDS  ·  US TREASURIES", style=SECTION_TITLE),
                html.Div(id="market-bonds"),
            ], width=6),
            dbc.Col([
                html.Div("FOREX", style=SECTION_TITLE),
                html.Div(id="market-fx"),
            ], width=6),
        ], style={"marginBottom":"14px"}),
        dbc.Row([
            dbc.Col([
                html.Div("COMMODITIES", style=SECTION_TITLE),
                html.Div(id="market-commodities"),
            ], width=12),
        ], style={"marginBottom":"14px"}),

        # Sector heatmap — full width, static Graph ID for clickData
        html.Div([
            html.Div("S&P 500 SECTORS  ·  DAILY PERFORMANCE", style={**SECTION_TITLE, "marginBottom":"10px"}),
            dcc.Graph(
                id     = "sector-heatmap-graph",
                config = {"displayModeBar": False},
                style  = {"height": "220px"},
            ),
            # Drill-down panel — revealed on tile click
            html.Div(id="sector-drill-down", style={"display": "none"}),
        ], style={
            "background":   C["bg_panel"],
            "border":       f"1px solid {C['border']}",
            "borderLeft":   f"3px solid var(--accent)",
            "borderRadius": "4px",
            "padding":      "12px 16px",
        }),
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


def build_sector_drill_down(etf_symbol: str, sector_name: str, holdings: list) -> html.Div:
    """
    Panel shown below the heatmap when a sector tile is clicked.
    Displays the top holdings with live price, daily change, and market cap.
    """
    def _fmt_mcap(v):
        if not v:
            return "N/A"
        if v >= 1e12:
            return f"${v/1e12:.2f}T"
        if v >= 1e9:
            return f"${v/1e9:.1f}B"
        return f"${v/1e6:.0f}M"

    cards = []
    for h in holdings:
        chg_color = C["green"] if h["chg_pct"] >= 0 else C["red"]
        sign      = "+" if h["chg_pct"] >= 0 else ""
        cards.append(html.Div([
            # Ticker
            html.Div(h["symbol"], style={
                "color":        "var(--accent)",
                "fontFamily":   FONT_MONO,
                "fontSize":     "13px",
                "fontWeight":   "700",
                "letterSpacing":"0.08em",
                "marginBottom": "2px",
            }),
            # Company name
            html.Div(h["name"], style={
                "color":       C["text_secondary"],
                "fontFamily":  FONT_MONO,
                "fontSize":    "9px",
                "letterSpacing":"0.04em",
                "marginBottom":"6px",
                "overflow":    "hidden",
                "textOverflow":"ellipsis",
                "whiteSpace":  "nowrap",
            }),
            # Price
            html.Div(f"${h['price']:,.2f}", style={
                "color":      C["text_white"],
                "fontFamily": FONT_MONO,
                "fontSize":   "13px",
                "fontWeight": "600",
                "marginBottom":"2px",
            }),
            # Daily change
            html.Div(f"{sign}{h['chg_pct']:.2f}%  {sign}{h['chg_abs']:.2f}", style={
                "color":      chg_color,
                "fontFamily": FONT_MONO,
                "fontSize":   "11px",
                "fontWeight": "600",
                "marginBottom":"4px",
            }),
            # Market cap
            html.Div(f"MCAP  {_fmt_mcap(h['mkt_cap'])}", style={
                "color":        C["text_dim"],
                "fontFamily":   FONT_MONO,
                "fontSize":     "9px",
                "letterSpacing":"0.06em",
            }),
        ], style={
            "background":   C["bg"],
            "border":       f"1px solid {C['border']}",
            "borderRadius": "3px",
            "padding":      "10px 12px",
            "flex":         "1",
            "minWidth":     "120px",
        }))

    return html.Div([
        # Sub-header
        html.Div([
            html.Span(f"▼ {sector_name.upper()}  ·  TOP HOLDINGS", style={
                "color":        "var(--accent)",
                "fontFamily":   FONT_MONO,
                "fontSize":     "10px",
                "fontWeight":   "700",
                "letterSpacing":"0.12em",
            }),
            html.Span("BY MARKET CAP", style={
                "color":        C["text_dim"],
                "fontFamily":   FONT_MONO,
                "fontSize":     "9px",
                "letterSpacing":"0.10em",
                "marginLeft":   "10px",
            }),
        ], style={"marginBottom": "10px", "marginTop": "14px",
                  "borderTop": f"1px solid {C['border']}", "paddingTop": "12px"}),
        # Holdings cards
        html.Div(cards, style={
            "display":   "flex",
            "gap":       "8px",
            "flexWrap":  "wrap",
        }),
    ])


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
# Calendar tab
# ─────────────────────────────────────────────────────────────────────────────

_CAL_CATEGORIES = [
    ("EARNINGS", "var(--accent)",  "EARNINGS"),
    ("ECONOMIC", "#38bdf8",        "ECONOMIC"),
    ("FED",      "#a78bfa",        "FED"),
    ("IPO",      "#22c55e",        "IPO"),
]

_CAL_CAT_COLORS = {
    "EARNINGS": "var(--accent)",
    "ECONOMIC": "#38bdf8",
    "FED":      "#a78bfa",
    "IPO":      "#22c55e",
}

_CAL_IMPACT_COLORS = {
    "HIGH":   "#ef4444",
    "MEDIUM": "var(--accent)",
    "LOW":    "#475569",
}

# ── Event info lookup: (display_name, description, market_impact) ─────────────
# Key = substring to match against event title (case-insensitive)
_EVENT_INFO = {
    # ── Inflation ──────────────────────────────────────────────────────────────
    "Core CPI": (
        "Core Consumer Price Index",
        "CPI stripped of food and energy — the Fed's favored read on underlying inflation due to its lower volatility.",
        "Persistent core CPI above the Fed's target is the single biggest obstacle to rate cuts. A surprise to the upside resets the rate-cut timeline, punishes growth/tech multiples, and drives yields sharply higher. A downside surprise can trigger a broad risk-on rally and a meaningful bond bid.",
    ),
    "CPI": (
        "Consumer Price Index",
        "Measures monthly price changes across a basket of goods and services paid by consumers.",
        "The most market-moving inflation print. A hot reading pressures the Fed to stay hawkish — equities sell off (especially rate-sensitive growth), yields spike, and the dollar strengthens. A cool reading rallies risk assets and can trigger sharp bond moves as rate-cut bets reprice.",
    ),
    "PCE": (
        "Personal Consumption Expenditures",
        "The Fed's preferred inflation gauge, tracking price changes in consumer spending.",
        "Because the Fed explicitly targets PCE at 2%, this print directly drives rate expectations. A hot reading can reset rate-cut timelines across the curve; a cool one can accelerate them and fuel broad equity upside.",
    ),
    "PPI": (
        "Producer Price Index",
        "Tracks selling-price changes received by domestic producers — a leading indicator for consumer inflation.",
        "A leading signal for future CPI direction. Rising PPI suggests pipeline inflation that will eventually reach consumers. Markets use it to front-run CPI surprises, making it especially relevant when the Fed is already watching inflation closely.",
    ),
    # ── Labor ──────────────────────────────────────────────────────────────────
    "Nonfarm Payrolls": (
        "Nonfarm Payrolls",
        "Monthly change in US employment, excluding the agricultural sector. The single most anticipated economic release.",
        "A blowout number is often bearish in a high-rate environment — it signals the Fed won't cut soon. A weak print raises recession fears but can also spark rate-cut bets, making equities' reaction complex. The 'bad news is good news' dynamic frequently applies. Wage growth within the report is a critical secondary read.",
    ),
    "NFP": (
        "Nonfarm Payrolls",
        "Monthly change in US employment, excluding the agricultural sector.",
        "Strong jobs data keeps the Fed on hold; weak data raises recession fears but can also price in cuts. The headline number, unemployment rate, and average hourly earnings all matter for the full picture.",
    ),
    "Unemployment": (
        "Unemployment Rate",
        "The percentage of the labor force that is jobless and actively seeking employment.",
        "Rising unemployment signals economic weakness, potentially pushing the Fed toward cuts. Falling unemployment in a hot economy can signal the opposite. Market reaction depends heavily on whether the move is driven by layoffs versus labor force growth.",
    ),
    "JOLTS": (
        "Job Openings and Labor Turnover Survey",
        "Measures job openings, hires, and separations — a detailed view of labor market health.",
        "High job openings signal tight labor markets and wage pressure, keeping the Fed hawkish. Declining openings suggest cooling demand, supporting rate-cut expectations. Often viewed as an early signal ahead of payrolls.",
    ),
    "ADP": (
        "ADP Employment Report",
        "Private-sector employment estimate released two days before the official NFP.",
        "Used as a directional preview for NFP. Large divergences between ADP and the official print can cause sharp mid-week moves and reset positioning ahead of Friday's report.",
    ),
    # ── Growth ─────────────────────────────────────────────────────────────────
    "GDP": (
        "Gross Domestic Product",
        "The broadest measure of US economic output — total value of goods and services produced.",
        "Strong GDP is generally risk-on but creates a Fed dilemma: a hot economy may mean rates stay higher for longer. A contraction (negative print) signals recession risk, hammers equities, and drives a flight into bonds and defensive assets.",
    ),
    "Retail Sales": (
        "Retail Sales",
        "Monthly change in total receipts at retail stores — a direct proxy for consumer spending strength.",
        "Consumer spending drives ~70% of US GDP, making this a key economic health check. A strong print is bullish for corporate revenues but in a high-inflation context signals the Fed needs to stay tight. A weak print suggests the consumer is cracking under rate pressure.",
    ),
    # ── Manufacturing & Services ───────────────────────────────────────────────
    "PMI": (
        "Purchasing Managers' Index",
        "Survey-based index of business activity. Above 50 = expansion, below 50 = contraction.",
        "A leading indicator of economic momentum. PMI above 50 is broadly bullish; sustained readings below 50 signal contraction. Flash PMI (preliminary estimate) is especially market-moving since it arrives before other growth data.",
    ),
    "ISM": (
        "ISM Manufacturing / Services Index",
        "Monthly survey of US purchasing managers measuring business conditions and future expectations.",
        "A key forward-looking indicator. ISM Manufacturing below 50 for multiple months signals industrial recession. The prices-paid component in Services ISM is closely watched for inflationary pressure that may spill into CPI.",
    ),
    # ── Housing ────────────────────────────────────────────────────────────────
    "Housing": (
        "Housing Market Data",
        "Covers starts, permits, existing home sales, and new home sales across the US housing market.",
        "Housing is the most rate-sensitive sector in the economy. Persistent weakness signals Fed tightening is biting the real economy and supports the case for cuts. Strength signals resilience but can keep inflation elevated via shelter costs in CPI.",
    ),
    # ── Fed ────────────────────────────────────────────────────────────────────
    "FOMC": (
        "FOMC Rate Decision",
        "The Federal Open Market Committee meets to set the federal funds rate target range — one of the most anticipated events on the financial calendar.",
        "Rate decisions move every asset class simultaneously. Hikes compress equity multiples (especially growth/tech), strengthen the dollar, and raise yields across the curve. Cuts do the opposite. The post-meeting press conference and the quarterly 'dot plot' projections often move markets more than the decision itself. Watch for hawkish/dovish pivots in language.",
    ),
    "Fed": (
        "Federal Reserve Announcement",
        "An official communication or decision from the Federal Reserve, including speeches and minutes.",
        "Any Fed communication is market-moving. Shifts in language around inflation, employment, and the rate path can reprice bond markets and equity multiples significantly. Fed Chair press conferences and surprise speeches at conferences are especially high-impact.",
    ),
    # ── Trade & Policy ─────────────────────────────────────────────────────────
    "Tariff": (
        "Trade Tariff Announcement",
        "A government decision to impose or change tariffs on imported goods.",
        "Tariffs raise input costs for businesses and consumer prices, acting as a tax on economic activity. Affected sectors (autos, semiconductors, agriculture) react sharply. Retaliatory measures from trading partners can escalate into broader market risk-off moves.",
    ),
    "Sanctions": (
        "Economic Sanctions",
        "Government-imposed economic restrictions on a country, entity, or individual.",
        "Sanctions can cut off commodity supplies, restrict trade flows, and elevate geopolitical risk premiums. Energy and commodity markets are often most directly affected, with spillover into inflation expectations and affected-country currencies.",
    ),
}

# Category-level fallbacks when no keyword matches
_CAT_INFO = {
    "EARNINGS": (
        "Quarterly Earnings Release",
        "The company reports quarterly revenue, earnings per share (EPS), and forward guidance.",
        "Earnings beats on both revenue and EPS typically drive the stock higher; misses trigger sell-offs. Forward guidance is often more important than the headline numbers — a beat with weak guidance can still push the stock lower. Bellwether reports (Apple, NVIDIA, JPMorgan) carry sector-wide contagion risk. Watch the options implied move heading in for expected volatility.",
    ),
    "IPO": (
        "Initial Public Offering",
        "The company lists on a public exchange for the first time, offering shares to institutional and retail investors.",
        "High-profile IPOs can affect sector valuations and draw capital rotation from competing names. First-day performance sets near-term sentiment. Key secondary event: lock-up expiration (typically 90–180 days post-IPO) when insiders can first sell, often creating selling pressure.",
    ),
    "ECONOMIC": (
        "Economic Data Release",
        "A scheduled release of macroeconomic data by a government agency or research body.",
        "Economic data shapes market expectations for Fed policy, corporate earnings, and growth trajectory. Surprises relative to consensus estimates drive the immediate reaction; the trend across multiple releases matters more for sustained directional moves.",
    ),
    "FED": (
        "Federal Reserve Event",
        "A scheduled Federal Reserve meeting, speech, or publication.",
        "Fed communications are the single largest driver of short-term bond and equity volatility. Markets dissect every word for signals on the rate path, balance sheet policy, and the Fed's economic outlook.",
    ),
}


def build_cal_modal_body(event: dict) -> list:
    """Build the children list for the calendar event detail modal."""
    import datetime as _dt

    cat      = event.get("cat",      event.get("category", ""))
    title    = event.get("title",    "")
    subtitle = event.get("subtitle", "")
    impact   = event.get("impact",   "")
    ticker   = event.get("ticker",   "")
    date_str = event.get("date",     "")

    # Look up description + market impact by matching title keywords
    name, desc, mkt_impact = None, None, None
    title_lower = title.lower()
    for key, info in _EVENT_INFO.items():
        if key.lower() in title_lower:
            name, desc, mkt_impact = info
            break
    if not name:
        name, desc, mkt_impact = _CAT_INFO.get(cat, _CAT_INFO["ECONOMIC"])

    color     = _CAL_CAT_COLORS.get(cat, C["text_secondary"])
    imp_color = _CAL_IMPACT_COLORS.get(impact, C["text_dim"])

    try:
        date_display = _dt.date.fromisoformat(date_str).strftime("%A, %B %-d, %Y")
    except Exception:
        date_display = date_str

    return [
        # ── Category + impact badges ───────────────────────────────────────────
        html.Div([
            html.Span(cat, style={
                "background":    f"color-mix(in srgb, {color} 18%, transparent)",
                "color":         color,
                "border":        f"1px solid color-mix(in srgb, {color} 40%, transparent)",
                "borderRadius":  "3px",
                "padding":       "2px 9px",
                "fontSize":      "9px",
                "fontFamily":    FONT_MONO,
                "fontWeight":    "700",
                "letterSpacing": "0.06em",
                "marginRight":   "8px",
            }),
            html.Span(f"● {impact}", style={
                "color":      imp_color,
                "fontFamily": FONT_MONO,
                "fontSize":   "9px",
                "fontWeight": "600",
            }) if impact else None,
        ], style={"display": "flex", "alignItems": "center", "marginBottom": "14px"}),

        # ── Title ─────────────────────────────────────────────────────────────
        html.Div(title, style={
            "color":         C["text_white"],
            "fontFamily":    FONT_MONO,
            "fontSize":      "17px",
            "fontWeight":    "700",
            "letterSpacing": "0.02em",
            "marginBottom":  "6px",
        }),

        # ── Date + ticker ──────────────────────────────────────────────────────
        html.Div([
            html.Span(date_display, style={
                "color":      C["text_secondary"],
                "fontFamily": FONT_MONO,
                "fontSize":   "10px",
                "marginRight":"12px",
            }),
            html.Span(f"${ticker}", style={
                "color":      "var(--accent)",
                "fontFamily": FONT_MONO,
                "fontSize":   "10px",
                "fontWeight": "700",
            }) if ticker else None,
        ], style={"display": "flex", "alignItems": "center", "marginBottom": "14px"}),

        # ── Subtitle chip (actual / forecast / prev) ──────────────────────────
        html.Div(subtitle, style={
            "background":   f"color-mix(in srgb, {C['border']} 50%, transparent)",
            "borderRadius": "3px",
            "padding":      "7px 12px",
            "color":        C["text_secondary"],
            "fontFamily":   FONT_MONO,
            "fontSize":     "10px",
            "marginBottom": "16px",
        }) if subtitle else None,

        html.Hr(style={
            "border": "none",
            "borderTop": f"1px solid {C['border']}",
            "margin": "0 0 16px",
        }),

        # ── What is it ────────────────────────────────────────────────────────
        html.Div("WHAT IS IT", style={
            "color":         C["text_dim"],
            "fontFamily":    FONT_MONO,
            "fontSize":      "9px",
            "fontWeight":    "700",
            "letterSpacing": "0.12em",
            "marginBottom":  "7px",
        }),
        html.Div(desc, style={
            "color":        C["text_primary"],
            "fontFamily":   FONT_MONO,
            "fontSize":     "11px",
            "lineHeight":   "1.75",
            "marginBottom": "18px",
        }),

        # ── Market impact ─────────────────────────────────────────────────────
        html.Div("MARKET IMPACT", style={
            "color":         C["text_dim"],
            "fontFamily":    FONT_MONO,
            "fontSize":      "9px",
            "fontWeight":    "700",
            "letterSpacing": "0.12em",
            "marginBottom":  "7px",
        }),
        html.Div(mkt_impact, style={
            "color":        C["text_primary"],
            "fontFamily":   FONT_MONO,
            "fontSize":     "11px",
            "lineHeight":   "1.75",
            "borderLeft":   f"3px solid {color}",
            "paddingLeft":  "12px",
        }),
    ]


def build_calendar_tab() -> html.Div:
    """Calendar tab — month grid with filter pills and prev/next navigation."""
    import datetime as _dt
    now         = _dt.date.today()
    month_label = now.strftime("%B %Y").upper()

    _nav_btn = {
        "background":    "transparent",
        "border":        f"1px solid {C['border']}",
        "borderRadius":  "3px",
        "color":         C["text_secondary"],
        "fontFamily":    FONT_MONO,
        "fontSize":      "12px",
        "fontWeight":    "700",
        "padding":       "3px 10px",
        "cursor":        "pointer",
        "lineHeight":    "1",
    }

    filter_btns = []
    for cat, color, label in _CAL_CATEGORIES:
        filter_btns.append(html.Button(
            label,
            id={"type": "cal-filter-btn", "index": cat},
            n_clicks=0,
            style={
                "background":    f"color-mix(in srgb, {color} 18%, transparent)",
                "border":        f"1px solid {color}",
                "borderRadius":  "2px",
                "color":         color,
                "fontFamily":    FONT_MONO,
                "fontSize":      "10px",
                "fontWeight":    "700",
                "padding":       "4px 14px",
                "cursor":        "pointer",
                "letterSpacing": "0.06em",
                "whiteSpace":    "nowrap",
            },
        ))

    _modal_panel_style = {
        "display":        "none",
        "position":       "fixed",
        "top":            "50%",
        "left":           "50%",
        "transform":      "translate(-50%, -50%)",
        "width":          "540px",
        "maxWidth":       "92vw",
        "maxHeight":      "80vh",
        "overflowY":      "auto",
        "background":     C["bg_panel"],
        "border":         f"1px solid {C['border']}",
        "borderRadius":   "6px",
        "padding":        "22px 24px 24px",
        "zIndex":         "1000",
        "boxShadow":      "0 24px 60px rgba(0,0,0,0.7)",
    }

    return html.Div([
        dcc.Store(id="cal-filter",      data=["EARNINGS", "ECONOMIC", "FED", "IPO"]),
        dcc.Store(id="cal-month",       data={"year": now.year, "month": now.month}),
        dcc.Store(id="cal-modal-event", data=None),

        # Top bar: filter pills left, month nav right
        html.Div([
            html.Div(filter_btns, style={"display": "flex", "gap": "6px", "flexWrap": "wrap"}),
            html.Div([
                html.Button("◄", id="cal-prev-month", n_clicks=0, style=_nav_btn),
                html.Span(month_label, id="cal-month-label", style={
                    "color":         C["text_white"],
                    "fontFamily":    FONT_MONO,
                    "fontSize":      "11px",
                    "fontWeight":    "700",
                    "letterSpacing": "0.12em",
                    "minWidth":      "140px",
                    "textAlign":     "center",
                }),
                html.Button("►", id="cal-next-month", n_clicks=0, style=_nav_btn),
            ], style={"display": "flex", "alignItems": "center", "gap": "8px"}),
        ], style={
            "display":        "flex",
            "alignItems":     "center",
            "justifyContent": "space-between",
            "marginBottom":   "14px",
            "flexWrap":       "wrap",
            "gap":            "10px",
        }),

        html.Div(id="calendar-content",
                 children=html.Div("Loading calendar…", style=LABEL_STYLE)),

        # ── Modal overlay — always in DOM, shown/hidden by callback ───────────
        # Dark backdrop (click to close)
        html.Div(id="cal-modal-backdrop", n_clicks=0, style={
            "display":    "none",
            "position":   "fixed",
            "top":        "0",
            "left":       "0",
            "right":      "0",
            "bottom":     "0",
            "background": "rgba(0, 6, 20, 0.80)",
            "zIndex":     "999",
            "cursor":     "pointer",
        }),
        # Modal panel — static shell (close button always in DOM)
        html.Div(id="cal-modal-panel", style={**_modal_panel_style,
                 "display": "none", "flexDirection": "column"}, children=[
            # Static header: always rendered so cal-modal-close is always in DOM
            html.Div([
                html.Span("EVENT DETAIL", style={
                    "color":         C["text_dim"],
                    "fontFamily":    FONT_MONO,
                    "fontSize":      "9px",
                    "fontWeight":    "700",
                    "letterSpacing": "0.12em",
                }),
                html.Button("✕", id="cal-modal-close", n_clicks=0, style={
                    "background": "transparent",
                    "border":     "none",
                    "color":      C["text_secondary"],
                    "fontSize":   "18px",
                    "cursor":     "pointer",
                    "padding":    "0",
                    "lineHeight": "1",
                }),
            ], style={
                "display":        "flex",
                "justifyContent": "space-between",
                "alignItems":     "center",
                "marginBottom":   "14px",
                "paddingBottom":  "10px",
                "borderBottom":   f"1px solid {C['border']}",
            }),
            # Dynamic content filled by callback
            html.Div(id="cal-modal-body"),
        ]),

    ], style={"padding": "14px 20px"})


def build_calendar_view(events: list, active_cats: list,
                        year: int, month: int) -> html.Div:
    """Render a monthly calendar grid with event pills in each day cell."""
    import datetime as _dt
    import calendar as _cal_lib
    from collections import defaultdict

    active_cats = active_cats or ["EARNINGS", "ECONOMIC", "FED", "IPO"]
    today       = _dt.date.today()

    # Filter to this month + active categories
    filtered = [
        e for e in events
        if e.get("category") in active_cats
        and e["date"].year  == year
        and e["date"].month == month
    ]

    # Group by day-of-month
    by_day = defaultdict(list)
    for e in filtered:
        by_day[e["date"].day].append(e)

    # Calendar matrix — Sunday first
    cal   = _cal_lib.Calendar(firstweekday=6)
    weeks = cal.monthdayscalendar(year, month)

    # ── Day-of-week header row ────────────────────────────────────────────────
    dow_header = html.Div([
        html.Div(d, style={
            "textAlign":     "center",
            "color":         C["text_dim"],
            "fontFamily":    FONT_MONO,
            "fontSize":      "9px",
            "fontWeight":    "700",
            "letterSpacing": "0.10em",
            "padding":       "6px 0 5px",
            "background":    f"color-mix(in srgb, {C['border']} 60%, transparent)",
            "borderRadius":  "2px",
        }) for d in ["SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT"]
    ], style={
        "display":             "grid",
        "gridTemplateColumns": "repeat(7, 1fr)",
        "gap":                 "2px",
        "marginBottom":        "2px",
    })

    # ── Event pill inside a cell ──────────────────────────────────────────────
    import json as _json
    _pill_counter = [0]   # mutable counter for unique indices

    def _pill(e):
        cat    = e.get("category", "")
        color  = _CAL_CAT_COLORS.get(cat, C["text_secondary"])
        ticker = e.get("ticker", "")
        title  = e.get("title", "")

        if cat == "EARNINGS" and ticker:
            label = ticker
        elif cat == "FED":
            label = "FOMC"
        elif cat == "IPO":
            label = (ticker or title)[:10]
        else:
            label = title[:14]

        # Serialize event fields into the pattern-matching ID index
        event_key = _json.dumps({
            "cat":      cat,
            "title":    title,
            "subtitle": e.get("subtitle", ""),
            "impact":   e.get("impact", ""),
            "ticker":   ticker,
            "date":     e["date"].isoformat(),
        }, separators=(",", ":"))

        _pill_counter[0] += 1

        return html.Div(label,
            id={"type": "cal-event-pill", "index": event_key},
            n_clicks=0,
            style={
                "background":   f"color-mix(in srgb, {color} 18%, transparent)",
                "color":        color,
                "border":       f"1px solid color-mix(in srgb, {color} 32%, transparent)",
                "borderRadius": "2px",
                "padding":      "1px 5px",
                "fontSize":     "8px",
                "fontFamily":   FONT_MONO,
                "fontWeight":   "600",
                "whiteSpace":   "nowrap",
                "overflow":     "hidden",
                "textOverflow": "ellipsis",
                "marginBottom": "2px",
                "maxWidth":     "100%",
                "cursor":       "pointer",
                "userSelect":   "none",
            }
        )

    # ── Build day cells ───────────────────────────────────────────────────────
    cells = []
    for week in weeks:
        for day_num in week:
            if day_num == 0:
                # Filler cell (day belongs to adjacent month)
                cells.append(html.Div(style={
                    "minHeight":    "88px",
                    "background":   f"color-mix(in srgb, {C['bg']} 70%, transparent)",
                    "border":       f"1px solid {C['border']}20",
                    "borderRadius": "3px",
                }))
                continue

            day_date  = _dt.date(year, month, day_num)
            is_today  = (day_date == today)
            is_past   = (day_date < today)
            day_evts  = by_day.get(day_num, [])
            visible   = day_evts[:3]
            overflow  = len(day_evts) - 3

            # Day number element
            if is_today:
                num_el = html.Div(str(day_num), style={
                    "width":          "20px",
                    "height":         "20px",
                    "background":     "var(--accent)",
                    "borderRadius":   "50%",
                    "display":        "inline-flex",
                    "alignItems":     "center",
                    "justifyContent": "center",
                    "color":          C["bg"],
                    "fontFamily":     FONT_MONO,
                    "fontSize":       "9px",
                    "fontWeight":     "700",
                })
            else:
                num_el = html.Span(str(day_num), style={
                    "color":      C["text_dim"] if is_past else C["text_secondary"],
                    "fontFamily": FONT_MONO,
                    "fontSize":   "10px",
                    "fontWeight": "600",
                })

            cell_children = [
                html.Div(num_el, style={"marginBottom": "5px"}),
                *[_pill(e) for e in visible],
            ]
            if overflow > 0:
                cell_children.append(html.Div(f"+{overflow} more", style={
                    "color":      C["text_dim"],
                    "fontFamily": FONT_MONO,
                    "fontSize":   "8px",
                    "marginTop":  "1px",
                }))

            cells.append(html.Div(cell_children, style={
                "minHeight":  "88px",
                "background": (
                    f"color-mix(in srgb, var(--accent) 7%, {C['bg_panel']})"
                    if is_today else
                    f"color-mix(in srgb, {C['bg']} 30%, {C['bg_panel']})"
                    if is_past else
                    C["bg_panel"]
                ),
                "border": (
                    f"1px solid var(--accent)"
                    if is_today else
                    f"1px solid {C['border']}55"
                    if is_past else
                    f"1px solid {C['border']}"
                ),
                "borderRadius": "3px",
                "padding":      "6px 7px",
                "overflow":     "hidden",
            }))

    grid = html.Div(cells, style={
        "display":             "grid",
        "gridTemplateColumns": "repeat(7, 1fr)",
        "gap":                 "2px",
    })

    # Footer: event count for this month
    total = sum(len(v) for v in by_day.values())
    footer = html.Div(
        f"{total} event{'s' if total != 1 else ''}  ·  "
        f"{_dt.datetime(year, month, 1).strftime('%B %Y')}",
        style={**LABEL_STYLE, "fontSize": "9px", "marginTop": "10px"},
    ) if total else html.Div(
        "No events this month for selected filters.",
        style={**LABEL_STYLE, "fontSize": "9px", "marginTop": "10px",
               "fontStyle": "italic"},
    )

    return html.Div([dow_header, grid, footer])


# ─────────────────────────────────────────────────────────────────────────────
# News Feed tab
# ─────────────────────────────────────────────────────────────────────────────

_NEWS_CATEGORIES = [
    ("ALL",          C["amber"],   "ALL NEWS"),
    ("PORTFOLIO",    C["amber"],   "PORTFOLIO"),
    ("GEOPOLITICAL", "#ef4444",    "GEOPOLITICAL"),
    ("MACRO",        "#3b82f6",    "MACRO / POLICY"),
    ("MARKETS",      "#22c55e",    "MARKETS"),
    ("COMMODITIES",  "#f97316",    "COMMODITIES"),
]

_CAT_COLORS = {
    "PORTFOLIO":    C["amber"],
    "GEOPOLITICAL": "#ef4444",
    "MACRO":        "#3b82f6",
    "MARKETS":      "#22c55e",
    "COMMODITIES":  "#f97316",
}


def build_newsfeed_tab() -> html.Div:
    """News feed tab with category filter bar."""
    filter_btns = []
    for cat, color, label in _NEWS_CATEGORIES:
        active = cat == "ALL"
        filter_btns.append(html.Button(
            label,
            id={"type": "news-filter-btn", "index": cat},
            n_clicks=0,
            style={
                "background":    f"color-mix(in srgb, {color} 18%, transparent)" if active else "transparent",
                "border":        f"1px solid {color}" if active else f"1px solid {C['border']}",
                "borderRadius":  "2px",
                "color":         color if active else C["text_secondary"],
                "fontFamily":    FONT_MONO,
                "fontSize":      "10px",
                "fontWeight":    "700" if active else "600",
                "padding":       "4px 12px",
                "cursor":        "pointer",
                "letterSpacing": "0.06em",
                "whiteSpace":    "nowrap",
            },
        ))

    return html.Div([
        dcc.Store(id="news-filter", data="ALL"),

        # Header + filter bar
        html.Div([
            html.Div("NEWS FEED", style={**SECTION_TITLE, "marginBottom": "0"}),
            html.Div(filter_btns, style={
                "display": "flex", "gap": "6px", "flexWrap": "wrap",
            }),
        ], style={
            "display":       "flex",
            "alignItems":    "center",
            "justifyContent":"space-between",
            "marginBottom":  "14px",
            "flexWrap":      "wrap",
            "gap":           "10px",
        }),

        html.Div(id="news-feed-content"),
    ], style={"padding": "14px 20px"})


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


def _category_badge(category: str) -> html.Span:
    color = _CAT_COLORS.get(category, C["text_secondary"])
    return html.Span(category, style={
        "background":    f"color-mix(in srgb, {color} 15%, transparent)",
        "color":         color,
        "border":        f"1px solid color-mix(in srgb, {color} 35%, transparent)",
        "borderRadius":  "3px",
        "padding":       "1px 7px",
        "fontSize":      "9px",
        "fontFamily":    FONT_MONO,
        "fontWeight":    "700",
        "letterSpacing": "0.06em",
        "marginRight":   "6px",
        "whiteSpace":    "nowrap",
    })


def _news_article_card(a: dict) -> html.Div:
    ticker       = a.get("ticker", "")
    source_tag   = a.get("source_tag",   a.get("publisher", "NEWS"))
    source_color = a.get("source_color", C["text_secondary"])
    summary      = a.get("summary", "")
    category     = a.get("category", "")

    # Left border uses category colour — immediately signals article type
    border_color = _CAT_COLORS.get(category, source_color)

    badges = []
    if category:
        badges.append(_category_badge(category))
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
        # Summary snippet
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
        "borderLeft":   f"3px solid {border_color}",
        "borderRadius": "3px",
        "marginBottom": "6px",
    })


def build_news_feed(
    portfolio_news: list = None,
    rss_news: list = None,
    filter_cat: str = "ALL",
) -> html.Div:
    """
    Unified news feed filtered by category.
    All articles (portfolio + RSS) are merged, sorted newest-first, and
    filtered by the selected category pill.
    """
    portfolio_news = portfolio_news or []
    rss_news       = rss_news or []

    # Merge into one list
    all_articles = list(portfolio_news) + list(rss_news)

    # Apply category filter
    if filter_cat and filter_cat != "ALL":
        all_articles = [a for a in all_articles if a.get("category") == filter_cat]

    # Sort newest-first using _raw_time if present
    import time as _time
    def _sort_key(a):
        t = a.get("_raw_time")
        if t:
            try:
                return -_time.mktime(t)
            except Exception:
                pass
        return 0

    all_articles.sort(key=_sort_key)

    if not all_articles:
        cat_label = filter_cat if filter_cat != "ALL" else ""
        return html.Div(
            f"No {cat_label + ' ' if cat_label else ''}news available.",
            style={**LABEL_STYLE, "padding": "20px 0"},
        )

    # Cap at 80 articles so the DOM doesn't get huge
    cards = [_news_article_card(a) for a in all_articles[:80]]

    # Article count label
    count_label = html.Div(
        f"{len(all_articles[:80])} articles  ·  {filter_cat}",
        style={**LABEL_STYLE, "fontSize": "9px", "marginBottom": "10px"},
    )

    return html.Div([
        count_label,
        html.Div(cards, style={"overflowY": "auto", "maxHeight": "82vh"}),
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

    # ── Section: Chart Indicators ─────────────────────────────────────────────
    ind = settings.get("indicators", DEFAULT_SETTINGS["indicators"])

    def _ind_btn(key, label, color):
        active = ind.get(key, True)
        return html.Button(label,
            id={"type": "ind-toggle-btn", "index": key},
            n_clicks=0,
            style={
                "background":    f"color-mix(in srgb, {color} 20%, transparent)" if active else "transparent",
                "border":        f"1px solid {color}" if active else f"1px solid {C['border']}",
                "borderRadius":  "3px",
                "color":         color if active else C["text_dim"],
                "fontFamily":    FONT_MONO,
                "fontSize":      "10px",
                "fontWeight":    "700" if active else "400",
                "padding":       "5px 12px",
                "cursor":        "pointer",
                "letterSpacing": "0.05em",
                "whiteSpace":    "nowrap",
            },
        )

    indicators_section = html.Div([
        html.Div("CHART INDICATORS", style=SECTION_TITLE),

        html.Div("Overlays", style={**LABEL_STYLE, "marginBottom": "8px"}),
        html.Div([
            _ind_btn("ma20",  "MA 20",          CHART["ma20"]),
            _ind_btn("ma50",  "MA 50",          CHART["ma50"]),
            _ind_btn("ma200", "MA 200",         CHART["ma200"]),
            _ind_btn("ema9",  "EMA 9",          CHART["ema9"]),
            _ind_btn("ema21", "EMA 21",         CHART["ema21"]),
            _ind_btn("bb",    "Bollinger Bands","#64748b"),
            _ind_btn("vwap",  "VWAP",           CHART["vwap"]),
        ], style={"display": "flex", "gap": "6px", "flexWrap": "wrap", "marginBottom": "16px"}),

        html.Div("Sub-panels", style={**LABEL_STYLE, "marginBottom": "8px"}),
        html.Div([
            _ind_btn("volume", "Volume", C["blue"]),
            _ind_btn("obv",    "OBV",    "#22d3ee"),
            _ind_btn("rsi",    "RSI",    CHART["rsi"]),
            _ind_btn("macd",   "MACD",   CHART["macd_line"]),
            _ind_btn("adx",    "ADX",    CHART["adx"]),
        ], style={"display": "flex", "gap": "6px", "flexWrap": "wrap", "marginBottom": "8px"}),

        html.Div(id="settings-indicators-status", style={
            **LABEL_STYLE, "color": C["green"], "fontSize": "10px",
        }),
    ], style={**CARD_STYLE, "marginBottom": "12px"})

    return html.Div([
        dbc.Row([
            dbc.Col(appearance_section,  width=3),
            dbc.Col(portfolio_section,   width=3),
            dbc.Col(ticker_section,      width=6),
        ]),
        dbc.Row([
            dbc.Col(indicators_section, width=12),
        ], style={"marginTop": "12px"}),
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
        # Intelligence system data store
        dcc.Store(id="store-intelligence", data=None),

        # Hidden dcc.Tabs — used purely as a value store for routing callbacks
        dcc.Tabs(id="main-tabs", value="portfolio", children=[],
                 style={"display":"none"}),

        # Fixed left sidebar
        build_sidebar(),

        # Topbar (clock + refresh, offset right of sidebar)
        build_navbar(),

        # Scrolling ticker tape (offset right of sidebar)
        html.Div(build_ticker_tape(), style={"marginLeft": "160px"}),

        # Notifications banner (fixed bottom-right)
        build_notifications_banner(),

        # Page content (offset right of sidebar)
        html.Div(id="page-content", style={
            "marginLeft": "160px",
            "minHeight":  "calc(100vh - 74px)",
        }),

    ], style={
        "background":  C["bg"],
        "minHeight":   "100vh",
        "fontFamily":  FONT_MONO,
    })


# ─────────────────────────────────────────────────────────────────────────────
# INTELLIGENCE TAB  —  Smart Money Operating System
# ─────────────────────────────────────────────────────────────────────────────

def build_intelligence_tab() -> html.Div:
    """
    Shell layout for the Intelligence tab.
    Five panels populated via the update_intelligence_panels() callback.
    """
    _panel = {
        "background":   C["bg_panel"],
        "border":       f"1px solid {C['border']}",
        "borderRadius": "4px",
        "padding":      "14px 16px",
    }
    return html.Div([
        # Header row
        html.Div([
            html.Span("◈ ", style={"color": "var(--accent)", "fontSize": "14px"}),
            html.Span("SMART MONEY OPERATING SYSTEM", style={
                "color": C["text_white"], "fontFamily": FONT_MONO,
                "fontSize": "12px", "fontWeight": "900", "letterSpacing": "0.12em",
            }),
            html.Span("  ·  Institutional-grade analysis on public data", style={
                "color": C["text_dim"], "fontFamily": FONT_MONO, "fontSize": "10px",
                "letterSpacing": "0.08em",
            }),
        ], style={"display": "flex", "alignItems": "center", "marginBottom": "14px"}),

        # Row 1: Regime + Cross-Asset (2 columns)
        html.Div([
            html.Div(id="intel-regime-panel",    style={**_panel, "minHeight": "180px"}),
            html.Div(id="intel-crossasset-panel",style={**_panel, "minHeight": "180px"}),
        ], style={"display": "grid", "gridTemplateColumns": "1fr 1fr",
                  "gap": "10px", "marginBottom": "10px"}),

        # Row 2: Smart Money Leaderboard + Trade Ideas (2 columns)
        html.Div([
            html.Div(id="intel-sm-panel",    style={**_panel, "minHeight": "220px"}),
            html.Div(id="intel-trade-panel", style={**_panel, "minHeight": "220px"}),
        ], style={"display": "grid", "gridTemplateColumns": "1fr 1fr",
                  "gap": "10px", "marginBottom": "10px"}),

        # Row 3: Signal Feed (full width)
        html.Div(id="intel-signal-feed", style={**_panel, "minHeight": "160px"}),

    ], style={
        "padding":    "16px 20px",
        "background": C["bg"],
        "minHeight":  "calc(100vh - 74px)",
    })


# ── Panel builders called from main.py callbacks ──────────────────────────────

def _intel_section_title(text: str) -> html.Div:
    return html.Div(text, style={
        "color": "var(--accent)", "fontFamily": FONT_MONO, "fontSize": "10px",
        "fontWeight": "700", "letterSpacing": "0.14em", "textTransform": "uppercase",
        "borderBottom": f"1px solid {C['border']}", "paddingBottom": "6px",
        "marginBottom": "10px",
    })


def build_intel_regime_panel(regime: dict) -> html.Div:
    """Market regime status panel."""
    if not regime:
        return html.Div("Loading…", style={"color": C["text_dim"], "fontFamily": FONT_MONO, "fontSize": "11px"})

    rname  = regime.get("regime", "Unknown")
    rconf  = regime.get("confidence", 0)
    rcolor = regime.get("color", C["amber"])
    vix    = regime.get("vix_level", 0)
    spy_t  = regime.get("spy_trend", "sideways")
    btc_t  = regime.get("btc_trend", "sideways")
    drivers= regime.get("key_drivers", [])
    votes  = regime.get("vote_breakdown", {})

    trend_color = {"uptrend": C["green"], "downtrend": C["red"], "sideways": C["amber"]}

    # Vote bar
    vote_bars = []
    vote_colors_map = {
        "Risk-On": "#22c55e", "Risk-Off": "#ef4444",
        "Transition": "#fbbf24", "High Volatility": "#f97316", "Low Liquidity": "#a78bfa",
    }
    for vname, vpct in sorted(votes.items(), key=lambda x: -x[1]):
        vc = vote_colors_map.get(vname, C["amber"])
        vote_bars.append(html.Div([
            html.Span(vname, style={"color": C["text_secondary"], "fontFamily": FONT_MONO,
                                    "fontSize": "9px", "width": "110px", "display": "inline-block"}),
            html.Div(style={
                "display": "inline-block", "height": "6px", "width": f"{vpct}%",
                "background": vc, "borderRadius": "2px", "verticalAlign": "middle",
                "maxWidth": "120px",
            }),
            html.Span(f" {vpct}%", style={"color": C["text_dim"], "fontFamily": FONT_MONO, "fontSize": "9px"}),
        ], style={"marginBottom": "3px", "display": "flex", "alignItems": "center", "gap": "6px"}))

    return html.Div([
        _intel_section_title("Market Regime"),
        # Regime badge
        html.Div([
            html.Span(rname, style={
                "color": rcolor, "fontFamily": FONT_MONO, "fontSize": "20px",
                "fontWeight": "900", "letterSpacing": "0.06em", "marginRight": "12px",
            }),
            html.Span(f"{rconf}% confidence", style={
                "color": C["text_secondary"], "fontFamily": FONT_MONO, "fontSize": "11px",
            }),
        ], style={"marginBottom": "10px", "display": "flex", "alignItems": "baseline"}),

        # Key stats row
        html.Div([
            html.Div([
                html.Span("VIX ", style={"color": C["text_secondary"], "fontFamily": FONT_MONO, "fontSize": "10px"}),
                html.Span(f"{vix:.1f}", style={"color": C["text_primary"], "fontFamily": FONT_MONO, "fontSize": "13px", "fontWeight": "700"}),
            ], style={"marginRight": "18px"}),
            html.Div([
                html.Span("SPY ", style={"color": C["text_secondary"], "fontFamily": FONT_MONO, "fontSize": "10px"}),
                html.Span(spy_t.upper(), style={"color": trend_color.get(spy_t, C["amber"]),
                                                "fontFamily": FONT_MONO, "fontSize": "11px", "fontWeight": "700"}),
            ], style={"marginRight": "18px"}),
            html.Div([
                html.Span("BTC ", style={"color": C["text_secondary"], "fontFamily": FONT_MONO, "fontSize": "10px"}),
                html.Span(btc_t.upper(), style={"color": trend_color.get(btc_t, C["amber"]),
                                                "fontFamily": FONT_MONO, "fontSize": "11px", "fontWeight": "700"}),
            ]),
        ], style={"display": "flex", "marginBottom": "10px"}),

        # Vote breakdown
        html.Div(vote_bars, style={"marginBottom": "10px"}),

        # Key drivers
        html.Div([
            html.Div(f"• {d}", style={
                "color": C["text_secondary"], "fontFamily": FONT_MONO,
                "fontSize": "9.5px", "marginBottom": "3px", "lineHeight": "1.4",
            }) for d in drivers[:4]
        ]),
    ])


def build_intel_crossasset_panel(cross_intel: dict) -> html.Div:
    """Cross-asset intelligence panel."""
    if not cross_intel:
        return html.Div("Loading…", style={"color": C["text_dim"], "fontFamily": FONT_MONO, "fontSize": "11px"})

    corr_regime    = cross_intel.get("correlation_regime", "normal")
    leading        = cross_intel.get("leading_asset", "—")
    lagging        = cross_intel.get("lagging_assets", [])
    rotation       = cross_intel.get("asset_rotation", "—")
    momentum_map   = cross_intel.get("momentum_map", {})
    correlations   = cross_intel.get("correlations", {})
    signals        = cross_intel.get("signals", [])

    regime_color   = {"normal": "#22c55e", "diverging": "#fbbf24", "unstable": "#ef4444"}
    corr_reg_color = regime_color.get(corr_regime, C["amber"])

    # Momentum mini-table
    asset_order = ["SPY", "QQQ", "BTC-USD", "GC=F", "CL=F", "DX-Y.NYB", "^TNX"]
    asset_names = {"SPY": "SPY", "QQQ": "QQQ", "BTC-USD": "BTC", "GC=F": "GOLD",
                   "CL=F": "OIL", "DX-Y.NYB": "DXY", "^TNX": "10Y"}
    mom_rows = []
    for sym in asset_order:
        if sym not in momentum_map:
            continue
        m5  = momentum_map[sym]["5d"]
        m20 = momentum_map[sym]["20d"]
        c5  = C["green"] if m5  >= 0 else C["red"]
        c20 = C["green"] if m20 >= 0 else C["red"]
        mom_rows.append(html.Div([
            html.Span(asset_names.get(sym, sym), style={
                "color": C["text_secondary"], "fontFamily": FONT_MONO,
                "fontSize": "10px", "width": "42px", "display": "inline-block",
            }),
            html.Span(f"{m5:+.1f}%", style={
                "color": c5, "fontFamily": FONT_MONO, "fontSize": "10px",
                "fontWeight": "700", "width": "56px", "display": "inline-block",
            }),
            html.Span(f"{m20:+.1f}%", style={
                "color": c20, "fontFamily": FONT_MONO, "fontSize": "10px",
                "width": "56px", "display": "inline-block",
            }),
        ], style={"display": "flex", "alignItems": "center", "marginBottom": "2px"}))

    # SPY correlations mini-bar
    corr_rows = []
    for sym, val in correlations.items():
        bar_w  = int(abs(val) * 60)
        bar_clr= C["green"] if val >= 0 else C["red"]
        name   = asset_names.get(sym, sym)
        corr_rows.append(html.Div([
            html.Span(name, style={"color": C["text_secondary"], "fontFamily": FONT_MONO,
                                   "fontSize": "9px", "width": "38px", "display": "inline-block"}),
            html.Div(style={"display": "inline-block", "height": "5px", "width": f"{bar_w}px",
                            "background": bar_clr, "borderRadius": "2px",
                            "verticalAlign": "middle", "maxWidth": "60px"}),
            html.Span(f"  {val:+.2f}", style={"color": C["text_dim"], "fontFamily": FONT_MONO, "fontSize": "9px"}),
        ], style={"display": "flex", "alignItems": "center", "gap": "5px", "marginBottom": "2px"}))

    return html.Div([
        _intel_section_title("Cross-Asset Intelligence"),

        html.Div([
            # Left: momentum table
            html.Div([
                html.Div([
                    html.Span("ASSET", style={"color": C["text_dim"], "fontFamily": FONT_MONO,
                                              "fontSize": "9px", "width": "42px", "display": "inline-block"}),
                    html.Span("5D", style={"color": C["text_dim"], "fontFamily": FONT_MONO,
                                           "fontSize": "9px", "width": "56px", "display": "inline-block"}),
                    html.Span("20D", style={"color": C["text_dim"], "fontFamily": FONT_MONO,
                                            "fontSize": "9px"}),
                ], style={"display": "flex", "marginBottom": "4px"}),
                *mom_rows,
            ], style={"flex": "1", "marginRight": "16px"}),

            # Right: correlations vs SPY + regime
            html.Div([
                html.Div("VS SPY CORR", style={"color": C["text_dim"], "fontFamily": FONT_MONO,
                                                "fontSize": "9px", "marginBottom": "4px"}),
                *corr_rows,
                html.Div([
                    html.Span("REGIME  ", style={"color": C["text_dim"], "fontFamily": FONT_MONO, "fontSize": "9px"}),
                    html.Span(corr_regime.upper(), style={"color": corr_reg_color,
                                                          "fontFamily": FONT_MONO, "fontSize": "10px",
                                                          "fontWeight": "700"}),
                ], style={"marginTop": "8px"}),
            ], style={"flex": "1"}),
        ], style={"display": "flex", "marginBottom": "8px"}),

        # Leading / rotation
        html.Div([
            html.Span("LEADING  ", style={"color": C["text_dim"], "fontFamily": FONT_MONO, "fontSize": "9px"}),
            html.Span(leading, style={"color": C["green"], "fontFamily": FONT_MONO,
                                      "fontSize": "10px", "fontWeight": "600"}),
        ], style={"marginBottom": "3px"}),
        html.Div([
            html.Span("ROTATION  ", style={"color": C["text_dim"], "fontFamily": FONT_MONO, "fontSize": "9px"}),
            html.Span(rotation, style={"color": C["amber"], "fontFamily": FONT_MONO,
                                       "fontSize": "10px", "fontWeight": "600"}),
        ]),
    ])


def build_intel_sm_leaderboard(sm_scores: dict, predictions: dict) -> html.Div:
    """Smart Money Score leaderboard."""
    if not sm_scores:
        return html.Div("Loading…", style={"color": C["text_dim"], "fontFamily": FONT_MONO, "fontSize": "11px"})

    # Sort by score descending
    ranked = sorted(sm_scores.items(), key=lambda x: x[1].get("score", 50), reverse=True)

    def _score_color(sc):
        if sc >= 65: return C["green"]
        if sc >= 52: return "#86efac"
        if sc <= 35: return C["red"]
        if sc <= 48: return "#fca5a5"
        return C["amber"]

    rows = []
    for ticker, sms in ranked:
        sc    = sms.get("score", 50)
        grade = sms.get("grade", "C")
        pred  = predictions.get(ticker, {})
        bias  = pred.get("directional_bias", "neutral")
        prob  = pred.get("probability", 50)
        bc    = C["green"] if bias == "bullish" else (C["red"] if bias == "bearish" else C["amber"])
        sclr  = _score_color(sc)
        bar_w = int(sc * 0.9)  # max ~90px for score=100

        rows.append(html.Div([
            # Ticker
            html.Span(ticker, style={"color": C["text_white"], "fontFamily": FONT_MONO,
                                     "fontSize": "11px", "fontWeight": "700",
                                     "width": "54px", "display": "inline-block"}),
            # Score bar
            html.Div([
                html.Div(style={
                    "height": "7px", "width": f"{bar_w}px",
                    "background": sclr, "borderRadius": "2px",
                }),
            ], style={"flex": "1", "margin": "0 10px"}),
            # Score + grade
            html.Span(f"{sc}", style={"color": sclr, "fontFamily": FONT_MONO,
                                       "fontSize": "12px", "fontWeight": "700",
                                       "width": "30px", "display": "inline-block"}),
            html.Span(grade, style={"color": C["text_dim"], "fontFamily": FONT_MONO,
                                    "fontSize": "10px", "width": "24px",
                                    "display": "inline-block"}),
            # Directional bias
            html.Span(f"{bias[:4].upper()}  {prob}%", style={
                "color": bc, "fontFamily": FONT_MONO, "fontSize": "9px",
                "fontWeight": "700", "width": "70px", "display": "inline-block",
                "textAlign": "right",
            }),
        ], style={"display": "flex", "alignItems": "center", "marginBottom": "6px",
                  "padding": "5px 8px",
                  "background": C["bg"], "borderRadius": "3px",
                  "border": f"1px solid {C['border']}"}))

    # Signal stats footer
    return html.Div([
        _intel_section_title("Smart Money Leaders"),
        *rows,
    ])


def build_intel_trade_ideas(trade_ideas: list) -> html.Div:
    """Trade idea cards."""
    if not trade_ideas:
        return html.Div([
            _intel_section_title("Trade Ideas"),
            html.Div("No high-confidence setups at current signal alignment.", style={
                "color": C["text_dim"], "fontFamily": FONT_MONO,
                "fontSize": "11px", "fontStyle": "italic",
            }),
        ])

    cards = []
    for idea in trade_ideas[:4]:
        ticker   = idea["ticker"]
        dir_     = idea["direction"]
        setup    = idea["setup_type"]
        entry    = idea["entry_zone"]
        inval    = idea["invalidation"]
        targets  = idea["target_levels"]
        rr       = idea["risk_reward"]
        conf     = idea["confidence"]
        reasons  = idea.get("reasoning", [])

        dir_color  = C["green"] if dir_ == "bullish" else C["red"]
        dir_label  = "LONG" if dir_ == "bullish" else "SHORT"
        setup_map  = {"breakout": "BRKOUT", "reversal": "REV", "accumulation": "ACCUM"}
        setup_lbl  = setup_map.get(setup, setup[:6].upper())

        cards.append(html.Div([
            # Header row
            html.Div([
                html.Span(ticker, style={"color": C["text_white"], "fontFamily": FONT_MONO,
                                         "fontSize": "13px", "fontWeight": "900", "marginRight": "8px"}),
                html.Span(dir_label, style={"color": dir_color, "fontFamily": FONT_MONO,
                                             "fontSize": "10px", "fontWeight": "700",
                                             "border": f"1px solid {dir_color}",
                                             "padding": "1px 5px", "borderRadius": "2px",
                                             "marginRight": "6px"}),
                html.Span(setup_lbl, style={"color": C["text_dim"], "fontFamily": FONT_MONO,
                                             "fontSize": "9px", "marginRight": "auto"}),
                html.Span(f"{conf}%  CONF", style={"color": C["amber"], "fontFamily": FONT_MONO,
                                                    "fontSize": "9px", "fontWeight": "700"}),
            ], style={"display": "flex", "alignItems": "center", "marginBottom": "5px"}),

            # Entry / inval / targets
            html.Div([
                html.Span("ENTRY  ", style={"color": C["text_dim"], "fontFamily": FONT_MONO, "fontSize": "9px"}),
                html.Span(f"${entry[0]}–${entry[1]}", style={"color": C["text_primary"],
                                                               "fontFamily": FONT_MONO, "fontSize": "10px",
                                                               "fontWeight": "600", "marginRight": "10px"}),
                html.Span("STOP  ", style={"color": C["text_dim"], "fontFamily": FONT_MONO, "fontSize": "9px"}),
                html.Span(f"${inval}", style={"color": C["red"], "fontFamily": FONT_MONO,
                                               "fontSize": "10px", "fontWeight": "600",
                                               "marginRight": "10px"}),
                html.Span(f"R/R {rr}x", style={"color": C["green"], "fontFamily": FONT_MONO,
                                                 "fontSize": "10px", "fontWeight": "700"}),
            ], style={"marginBottom": "3px"}),

            html.Div([
                html.Span("TARGETS  ", style={"color": C["text_dim"], "fontFamily": FONT_MONO, "fontSize": "9px"}),
                *[html.Span(f"${t}  ", style={"color": C["green"] if dir_ == "bullish" else C["red"],
                                               "fontFamily": FONT_MONO, "fontSize": "10px", "fontWeight": "600"})
                  for t in targets],
            ], style={"marginBottom": "4px"}),

            # Top reason
            html.Div(reasons[0] if reasons else "", style={
                "color": C["text_secondary"], "fontFamily": FONT_MONO,
                "fontSize": "9px", "fontStyle": "italic",
            }),
        ], style={
            "background":   C["bg"],
            "border":       f"1px solid {dir_color}33",
            "borderLeft":   f"3px solid {dir_color}",
            "borderRadius": "3px",
            "padding":      "8px 10px",
            "marginBottom": "6px",
        }))

    return html.Div([
        _intel_section_title("Trade Ideas"),
        *cards,
    ])


def build_intel_signal_feed(signal_feed: list, signal_stats: dict) -> html.Div:
    """Live signal feed with accuracy stats footer."""
    rows = []
    for sig in signal_feed:
        time_  = sig.get("time", "")
        type_  = sig.get("type", "")
        ticker = sig.get("ticker", "")
        msg    = sig.get("message", "")
        color  = sig.get("color", C["text_secondary"])
        rows.append(html.Div([
            html.Span(time_, style={"color": C["text_dim"], "fontFamily": FONT_MONO,
                                    "fontSize": "10px", "width": "44px",
                                    "display": "inline-block", "flexShrink": "0"}),
            html.Span(ticker, style={"color": C["amber"], "fontFamily": FONT_MONO,
                                     "fontSize": "10px", "fontWeight": "700",
                                     "width": "80px", "display": "inline-block", "flexShrink": "0"}),
            html.Span(f"[{type_}]", style={"color": color, "fontFamily": FONT_MONO,
                                            "fontSize": "9px", "fontWeight": "700",
                                            "width": "84px", "display": "inline-block", "flexShrink": "0"}),
            html.Span(msg, style={"color": C["text_secondary"], "fontFamily": FONT_MONO,
                                   "fontSize": "10px", "lineHeight": "1.4"}),
        ], style={"display": "flex", "alignItems": "flex-start", "gap": "4px",
                  "padding": "4px 6px", "borderBottom": f"1px solid {C['border']}"}))

    # Stats footer
    stats_parts = []
    if signal_stats:
        total = signal_stats.get("total", 0)
        acc   = signal_stats.get("accuracy")
        grade = signal_stats.get("grade", "N/A")
        stats_parts.append(html.Span(f"SIGNAL HISTORY: {total} predictions", style={
            "color": C["text_dim"], "fontFamily": FONT_MONO, "fontSize": "9px",
        }))
        if acc is not None:
            stats_parts.append(html.Span(f"  ·  ACCURACY: {acc}% [{grade}]", style={
                "color": C["green"] if acc >= 60 else C["amber"],
                "fontFamily": FONT_MONO, "fontSize": "9px", "fontWeight": "700",
            }))

    return html.Div([
        _intel_section_title("Signal Feed  —  Institutional Activity Log"),
        html.Div(rows, style={"maxHeight": "200px", "overflowY": "auto", "marginBottom": "8px"}),
        html.Div(stats_parts, style={"display": "flex", "alignItems": "center",
                                      "paddingTop": "6px", "borderTop": f"1px solid {C['border']}"}),
    ])
