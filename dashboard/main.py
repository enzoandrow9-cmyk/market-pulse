# ─────────────────────────────────────────────────────────────────────────────
# main.py  —  Bloomberg Terminal Dashboard  •  Enzo Market Pulse
# Entry point: Dash app, callbacks, server
#
# Run:  python3 main.py
# Then open: http://127.0.0.1:8050
# ─────────────────────────────────────────────────────────────────────────────

import datetime
import json
import threading
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import dash
from dash import Input, Output, State, ALL, MATCH, callback_context, dcc
import dash_bootstrap_components as dbc
import plotly.graph_objects as go

from config import C, PORTFOLIO_TICKERS, DEFAULT_SETTINGS
import data_manager as dm
import chart_builders as cb
import layouts as ly
import intelligence as intel
import quantlab_ui as ql_ui
from quantlab.runner import QuantLabRunner

# ─────────────────────────────────────────────────────────────────────────────
# App init
# ─────────────────────────────────────────────────────────────────────────────

app = dash.Dash(
    __name__,
    external_stylesheets=[
        dbc.themes.DARKLY,
        # IBM Plex Mono font
        "https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@300;400;600;700;900&display=swap",
    ],
    suppress_callback_exceptions=True,
    title="Market Pulse Terminal",
    update_title=None,
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}],
)
server = app.server  # for deployment if needed
quantlab_runner = QuantLabRunner(output_root=str(Path(__file__).resolve().parent / "quantlab_runs"))

# Custom CSS injected globally
app.index_string = """
<!DOCTYPE html>
<html>
  <head>
    {%metas%}
    <title>{%title%}</title>
    {%favicon%}
    {%css%}
    <style>
      :root { --accent: """ + C["amber"] + """; }
      * { box-sizing: border-box; margin: 0; padding: 0; }
      body { background: """ + C["bg"] + """; }
      ::-webkit-scrollbar { width: 6px; height: 6px; }
      ::-webkit-scrollbar-track { background: """ + C["bg"] + """; }
      ::-webkit-scrollbar-thumb { background: """ + C["border"] + """; border-radius: 3px; }
      ::-webkit-scrollbar-thumb:hover { background: var(--accent); opacity: 0.5; }
      .Select-control, .Select-menu-outer {
        background-color: """ + C["bg_panel"] + """ !important;
        border-color: """ + C["border"] + """ !important;
        color: """ + C["text_primary"] + """ !important;
      }
      .Select-value-label, .Select-option { color: """ + C["text_primary"] + """ !important; }
      .Select-option.is-focused { background: """ + C["bg_hover"] + """ !important; }
      .bloomberg-dropdown .Select-control { font-family: 'IBM Plex Mono', monospace; }
      /* Dash tab overrides */
      .tab-content { background: transparent !important; border: none !important; }
      .rc-tabs-nav-wrap { border-bottom: none !important; }
      /* Ticker card hover effect — uses --accent so it responds to the accent setting */
      .ticker-card-wrap:hover > div:first-child {
        border-color: var(--accent) !important;
        background: """ + C["bg_hover"] + """ !important;
      }
      /* Accent highlight helper — applied to active nav items, selected states, etc. */
      .accent-glow { color: var(--accent) !important; }
      .accent-border { border-color: var(--accent) !important; }
      /* ── Light mode overrides ── */
      body.light-mode { background: #f0f4f8 !important; }
      body.light-mode #_pages_content, body.light-mode > div { background: #f0f4f8; }
      body.light-mode [style*="background: rgb(6, 11, 25)"],
      body.light-mode [style*="background: rgb(13, 21, 38)"] {
        background: #ffffff !important;
      }
      body.light-mode span, body.light-mode div, body.light-mode p {
        color: #1e293b;
      }
      body.light-mode [style*="border:"] {
        border-color: #cbd5e1 !important;
      }
      body.light-mode .ticker-card-wrap > div:first-child {
        background: #ffffff !important;
        border-color: #cbd5e1 !important;
      }
      body.light-mode .ticker-card-wrap:hover > div:first-child {
        background: #f1f5f9 !important;
        border-color: """ + C["amber"] + """88 !important;
      }
      /* ── Ticker tape scroll animation ── */
      @keyframes tape-scroll {
        0%   { transform: translateX(0); }
        100% { transform: translateX(-50%); }
      }
      .tape-scroll {
        animation: tape-scroll 60s linear infinite;
        display: inline-flex;
        will-change: transform;
      }
      .tape-scroll:hover { animation-play-state: paused; }
    </style>
  </head>
  <body>
    {%app_entry%}
    <footer>
      {%config%}
      {%scripts%}
      {%renderer%}
    </footer>
  </body>
</html>
"""

app.layout = ly.build_app_layout()

# ─────────────────────────────────────────────────────────────────────────────
# Navbar tab buttons → switch active tab
# ─────────────────────────────────────────────────────────────────────────────

@app.callback(
    Output("main-tabs", "value", allow_duplicate=True),
    Input("nav-btn-portfolio",    "n_clicks"),
    Input("nav-btn-deepdive",     "n_clicks"),
    Input("nav-btn-market",       "n_clicks"),
    Input("nav-btn-quantlab",     "n_clicks"),
    Input("nav-btn-intelligence", "n_clicks"),
    Input("nav-btn-calendar",     "n_clicks"),
    Input("nav-btn-news",         "n_clicks"),
    Input("nav-btn-settings",     "n_clicks"),
    prevent_initial_call=True,
)
def nav_tab_clicked(*_):
    ctx = callback_context
    if not ctx.triggered:
        return dash.no_update
    btn_id = ctx.triggered[0]["prop_id"].split(".")[0]
    return btn_id.replace("nav-btn-", "")


@app.callback(
    Output("nav-btn-portfolio",    "style"),
    Output("nav-btn-deepdive",     "style"),
    Output("nav-btn-market",       "style"),
    Output("nav-btn-quantlab",     "style"),
    Output("nav-btn-intelligence", "style"),
    Output("nav-btn-calendar",     "style"),
    Output("nav-btn-news",         "style"),
    Output("nav-btn-settings",     "style"),
    Input("main-tabs", "value"),
)
def update_nav_styles(active_tab):
    vals = ["portfolio", "deepdive", "market", "quantlab", "intelligence", "calendar", "news", "settings"]
    return [
        ly.NAV_BTN_ACTIVE_STYLE if v == active_tab else ly.NAV_BTN_STYLE
        for v in vals
    ]


# ─────────────────────────────────────────────────────────────────────────────
# Background Deep Dive cache pre-warmer
# ─────────────────────────────────────────────────────────────────────────────

def _bg_prewarm_deepdive(tickers: list):
    """
    Pre-fetch fundamentals, options flow, and news for every portfolio ticker
    so the Deep Dive tab loads instantly (all three sources are cached).
    Runs in a daemon thread — never blocks the main portfolio refresh.
    """
    try:
        n = max(1, min(len(tickers) * 3, 16))
        with ThreadPoolExecutor(max_workers=n) as pool:
            futs = []
            for t in tickers:
                futs.append(pool.submit(dm.get_ticker_fundamentals, t))
                futs.append(pool.submit(dm.get_options_flow, t))
                futs.append(pool.submit(dm.get_ticker_news, t, 8))
            for f in as_completed(futs):
                try:
                    f.result()
                except Exception:
                    pass
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────────────────────
# Helper: serialize / deserialize data for dcc.Store
# ─────────────────────────────────────────────────────────────────────────────

def _serialize_portfolio(all_data: dict) -> dict:
    """Strip DataFrames (not JSON-serializable) for dcc.Store."""
    out = {}
    for t, d in all_data.items():
        row = {k: v for k, v in d.items() if k != "df"}
        out[t] = row
    return out


# ─────────────────────────────────────────────────────────────────────────────
# Clock callback (1-second interval)
# ─────────────────────────────────────────────────────────────────────────────

@app.callback(
    Output("clock-display", "children"),
    Input("interval-1s", "n_intervals"),
)
def update_clock(_):
    return datetime.datetime.now().strftime("%Y-%m-%d  %H:%M:%S")


# ─────────────────────────────────────────────────────────────────────────────
# Ticker tape — scrolling price strip below navbar
# ─────────────────────────────────────────────────────────────────────────────

@app.callback(
    Output("ticker-tape-inner", "children"),
    Output("ticker-tape-inner", "className"),
    Input("store-portfolio",    "data"),
    Input("store-refresh-ts",   "data"),
    prevent_initial_call=False,
)
def update_ticker_tape(store_data, ts):
    from dash import html as _html
    FONT = "'IBM Plex Mono', monospace"

    def _chip(label, price, chg_pct, color):
        sign = "+" if chg_pct >= 0 else ""
        return _html.Span([
            _html.Span(label, style={"color": C["text_secondary"], "marginRight": "5px",
                                     "fontFamily": FONT, "fontSize": "10px", "fontWeight": "700"}),
            _html.Span(f"${price:,.2f}" if price else "N/A",
                       style={"color": C["text_white"], "fontFamily": FONT, "fontSize": "10px",
                              "marginRight": "4px"}),
            _html.Span(f"{sign}{chg_pct:.2f}%",
                       style={"color": color, "fontFamily": FONT, "fontSize": "10px",
                              "fontWeight": "600", "marginRight": "20px"}),
        ], style={"display":"inline-flex","alignItems":"center","padding":"0 4px"})

    chips = []

    # Portfolio tickers from store
    if store_data:
        for ticker, d in store_data.items():
            price   = d.get("price")
            chg_pct = d.get("chg_pct", 0.0)
            color   = C["green"] if chg_pct >= 0 else C["red"]
            chips.append(_chip(ticker, price, chg_pct, color))

    # Key indices from market data
    try:
        for section in ["indices", "crypto"]:
            rows = dm.get_market_data(section)
            for r in rows[:3]:
                color = C["green"] if r["chg_pct"] >= 0 else C["red"]
                chips.append(_chip(r["name"], r["price"], r["chg_pct"], color))
    except Exception:
        pass

    # Separator
    sep = _html.Span("│", style={"color": C["border"], "margin": "0 8px",
                                  "fontFamily": FONT, "fontSize": "12px"})

    # Duplicate chips so scroll appears seamless (CSS animation scrolls -50%)
    all_chips = list(chips) + [sep] + list(chips) + [sep]
    return all_chips, "tape-scroll"


# ─────────────────────────────────────────────────────────────────────────────
# Data fetch: triggered by interval OR refresh button
# ─────────────────────────────────────────────────────────────────────────────

@app.callback(
    Output("store-portfolio",   "data"),
    Output("store-refresh-ts",  "data"),
    Input("interval-data",      "n_intervals"),
    Input("refresh-btn",        "n_clicks"),
    Input("user-settings",      "data"),
    State("store-refresh-ts",   "data"),
    prevent_initial_call=False,
)
def fetch_portfolio_data(n_intervals, n_clicks, settings, last_ts):
    ctx    = callback_context
    forced = ctx.triggered and "refresh-btn" in ctx.triggered[0]["prop_id"]

    # Pull tickers from active portfolio in settings
    tickers = PORTFOLIO_TICKERS  # fallback
    try:
        if settings:
            port_key   = settings.get("active_portfolio", "default")
            portfolios = settings.get("portfolios", {})
            port       = portfolios.get(port_key, {})
            t_list     = port.get("tickers", [])
            if t_list:
                tickers = t_list
    except Exception:
        pass

    try:
        # Fetch all tickers in parallel — cuts startup from ~5 s to ~1 s
        force = bool(forced)
        n_workers = max(1, min(12, len(tickers)))
        all_data = {}
        with ThreadPoolExecutor(max_workers=n_workers) as pool:
            future_to_t = {
                pool.submit(dm.get_ticker_data, t, force): t
                for t in tickers
            }
            for fut in as_completed(future_to_t):
                t = future_to_t[fut]
                try:
                    all_data[t] = fut.result()
                except Exception:
                    pass

        serial = _serialize_portfolio(all_data)
        ts     = int(datetime.datetime.now().timestamp())

        # Fire-and-forget: pre-warm Deep Dive caches so tab switch is instant
        threading.Thread(
            target=_bg_prewarm_deepdive,
            args=(tickers,),
            daemon=True,
        ).start()

        return serial, ts
    except Exception:
        traceback.print_exc()
        return dash.no_update, last_ts


# ─────────────────────────────────────────────────────────────────────────────
# Card click → set selected ticker + switch to Deep Dive tab
# ─────────────────────────────────────────────────────────────────────────────

@app.callback(
    Output("selected-ticker", "data"),
    Output("main-tabs",       "value", allow_duplicate=True),
    Input({"type": "ticker-card", "index": ALL}, "n_clicks"),
    State("main-tabs", "value"),
    prevent_initial_call=True,
)
def card_clicked(n_clicks_list, current_tab):
    ctx = callback_context
    if not ctx.triggered or not any(n_clicks_list):
        return dash.no_update, dash.no_update

    # Find which card was actually clicked (n_clicks just went up)
    triggered_id = ctx.triggered[0]["prop_id"]
    # triggered_id looks like: '{"index":"NVDA","type":"ticker-card"}.n_clicks'
    try:
        import json as _json
        id_part = triggered_id.split(".n_clicks")[0]
        parsed  = _json.loads(id_part)
        ticker  = parsed["index"]
    except Exception:
        return dash.no_update, dash.no_update

    return ticker, "deepdive"


# ─────────────────────────────────────────────────────────────────────────────
# Page routing: render correct tab content
# ─────────────────────────────────────────────────────────────────────────────

@app.callback(
    Output("page-content",  "children"),
    Input("main-tabs",      "value"),
    Input("user-settings",  "data"),   # re-render settings tab when store changes
    State("selected-ticker","data"),
)
def render_page(tab, settings, selected_ticker):
    ctx = callback_context
    triggered = ctx.triggered[0]["prop_id"] if ctx.triggered else ""

    # If user-settings changed but we're NOT on the settings tab, don't re-render
    # (avoids disrupting portfolio cards, deep dive ticker, etc.)
    if "user-settings" in triggered and tab != "settings":
        return dash.no_update

    ticker = selected_ticker or "NVDA"

    # Resolve the active portfolio's ticker list from settings
    active_tickers = PORTFOLIO_TICKERS
    try:
        if settings:
            port_key = settings.get("active_portfolio", "default")
            port     = settings.get("portfolios", {}).get(port_key, {})
            t_list   = port.get("tickers", [])
            if t_list:
                active_tickers = t_list
    except Exception:
        pass

    if tab == "portfolio":
        return ly.build_portfolio_tab()
    elif tab == "deepdive":
        return ly.build_deepdive_tab(initial_ticker=ticker, tickers=active_tickers)
    elif tab == "market":
        return ly.build_market_tab()
    elif tab == "quantlab":
        return ql_ui.build_quantlab_tab()
    elif tab == "intelligence":
        return ly.build_intelligence_tab()
    elif tab == "calendar":
        return ly.build_calendar_tab()
    elif tab == "news":
        return ly.build_newsfeed_tab()
    elif tab == "settings":
        return ly.build_settings_tab(settings or DEFAULT_SETTINGS)
    return ly.build_portfolio_tab()


@app.callback(
    Output("quantlab-strategies-field", "style"),
    Output("quantlab-simulation-field", "style"),
    Output("quantlab-capital-field", "style"),
    Output("quantlab-interval-field", "style"),
    Output("quantlab-optimizer-field", "style"),
    Input("quantlab-action", "value"),
)
def update_quantlab_builder_visibility(action):
    visible = dict(ql_ui.FIELD_STYLE)
    hidden = dict(ql_ui.HIDDEN_FIELD_STYLE)
    if action == "backtest":
        return visible, visible, visible, visible, hidden
    if action == "research":
        return hidden, hidden, hidden, visible, hidden
    if action == "regime":
        return hidden, hidden, hidden, visible, hidden
    if action == "optimize":
        return visible, visible, visible, visible, visible
    return visible, visible, visible, visible, hidden


@app.callback(
    Output("quantlab-command", "value"),
    Output("quantlab-builder-hint", "children"),
    Output("quantlab-workflow-display", "children"),
    Input("quantlab-action", "value"),
    Input("quantlab-symbols", "value"),
    Input("quantlab-strategies", "value"),
    Input("quantlab-start-date", "value"),
    Input("quantlab-end-date", "value"),
    Input("quantlab-simulation-mode", "value"),
    Input("quantlab-capital", "value"),
    Input("quantlab-interval", "value"),
    Input("quantlab-optimizer-method", "value"),
)
def sync_quantlab_command_preview(
    action,
    symbols,
    strategies,
    start_date,
    end_date,
    simulation_mode,
    capital,
    interval,
    optimizer_method,
):
    command = ql_ui.build_command_from_form(
        action=action,
        symbols=symbols,
        strategies=strategies,
        start_date=start_date,
        end_date=end_date,
        simulation_mode=simulation_mode,
        capital=capital,
        interval=interval,
        optimization_method=optimizer_method,
    )
    return command, ql_ui.builder_hint(action), ql_ui.render_workflow_display(action)


@app.callback(
    Output("quantlab-status", "children"),
    Output("quantlab-summary", "children"),
    Output("quantlab-metrics", "children"),
    Output("quantlab-risk-panel", "children"),
    Output("quantlab-experiment", "children"),
    Output("quantlab-equity-graph", "figure"),
    Output("quantlab-drawdown-graph", "figure"),
    Output("quantlab-rolling-graph", "figure"),
    Output("quantlab-factor-graph", "figure"),
    Output("quantlab-trades-table", "children"),
    Output("quantlab-signals-feed", "children"),
    Input("quantlab-run-btn", "n_clicks"),
    State("quantlab-command", "value"),
    prevent_initial_call=True,
)
def run_quantlab_command(n_clicks, command):
    del n_clicks
    blank_equity = ql_ui.blank_figure("Equity Curve")
    blank_drawdown = ql_ui.blank_figure("Drawdown")
    blank_rolling = ql_ui.blank_figure("Rolling Sharpe")
    blank_factor = ql_ui.blank_figure("Factor Ranking")

    if not command or not str(command).strip():
        msg = "Quant Lab command is empty."
        placeholder = dash.html.Div(msg, style={"color": C["text_dim"], "fontFamily": "'IBM Plex Mono', monospace", "fontSize": "11px"})
        return msg, placeholder, placeholder, placeholder, placeholder, blank_equity, blank_drawdown, blank_rolling, blank_factor, placeholder, placeholder

    try:
        result = quantlab_runner.run_command(command)
    except Exception as exc:
        err = f"Quant Lab error: {exc}"
        body = dash.html.Pre(
            traceback.format_exc(),
            style={
                "background": C["bg_chart"],
                "border": f"1px solid {C['border']}",
                "color": C["red"],
                "fontFamily": "'IBM Plex Mono', monospace",
                "fontSize": "10px",
                "padding": "10px",
                "whiteSpace": "pre-wrap",
            },
        )
        return err, body, body, body, body, blank_equity, blank_drawdown, blank_rolling, blank_factor, body, body

    mode = result.get("mode", "backtest")
    summary = ql_ui.render_summary(result)

    if mode == "backtest":
        metrics = dash.html.Div(
            [
                dash.html.Div("PERFORMANCE", style={"color": "var(--accent)", "fontFamily": "'IBM Plex Mono', monospace", "fontSize": "10px", "marginBottom": "6px"}),
                ql_ui.render_key_value_block(result.get("performance_metrics", {})),
                dash.html.Div("TRADES", style={"color": "var(--accent)", "fontFamily": "'IBM Plex Mono', monospace", "fontSize": "10px", "marginTop": "12px", "marginBottom": "6px"}),
                ql_ui.render_key_value_block(result.get("trade_statistics", {})),
            ]
        )
        risk_panel = dash.html.Div(
            [
                dash.html.Div("RISK", style={"color": "var(--accent)", "fontFamily": "'IBM Plex Mono', monospace", "fontSize": "10px", "marginBottom": "6px"}),
                ql_ui.render_key_value_block(result.get("risk_metrics", {})),
                dash.html.Div("CAPACITY", style={"color": "var(--accent)", "fontFamily": "'IBM Plex Mono', monospace", "fontSize": "10px", "marginTop": "12px", "marginBottom": "6px"}),
                ql_ui.render_key_value_block(result.get("capacity_analysis", {})),
                dash.html.Div("STRESS", style={"color": "var(--accent)", "fontFamily": "'IBM Plex Mono', monospace", "fontSize": "10px", "marginTop": "12px", "marginBottom": "6px"}),
                ql_ui.render_key_value_block(result.get("stress_tests", {})),
            ]
        )
        experiment = ql_ui.render_experiment(result)
        tearsheet = result.get("tearsheet", {})
        status = (
            f"Completed backtest for {', '.join(result.get('config', {}).get('symbols', []))} "
            f"with {', '.join(result.get('config', {}).get('strategies', []))}. "
            f"Experiment {result.get('experiment', {}).get('experiment_id', 'n/a')} recorded."
        )
        return (
            status,
            summary,
            metrics,
            risk_panel,
            experiment,
            tearsheet.get("equity_curve_figure", blank_equity),
            tearsheet.get("drawdown_figure", blank_drawdown),
            tearsheet.get("rolling_sharpe_figure", blank_rolling),
            tearsheet.get("factor_figure", blank_factor),
            ql_ui.render_trade_blotter(result.get("trades", [])),
            ql_ui.render_signal_feed(result.get("signals", []), result.get("risk_events", [])),
        )

    if mode == "research":
        metrics = ql_ui.render_key_value_block(result.get("regimes", {}))
        status = "Research factor evaluation completed."
        return (
            status,
            summary,
            metrics,
            dash.html.Div("Cross-sectional factor ranking generated.", style={"color": C["text_primary"], "fontFamily": "'IBM Plex Mono', monospace", "fontSize": "11px"}),
            dash.html.Div("No experiment stored for ad hoc research mode.", style={"color": C["text_dim"], "fontFamily": "'IBM Plex Mono', monospace", "fontSize": "11px"}),
            blank_equity,
            blank_drawdown,
            blank_rolling,
            ql_ui.render_factor_figure(result.get("factor_ranking")),
            ql_ui.render_trade_blotter([]),
            ql_ui.render_signal_feed([], []),
        )

    if mode == "regime":
        regime_block = ql_ui.render_key_value_block(result.get("regime", {}))
        return (
            "Regime analysis completed.",
            summary,
            regime_block,
            regime_block,
            dash.html.Div("No experiment stored for regime mode.", style={"color": C["text_dim"], "fontFamily": "'IBM Plex Mono', monospace", "fontSize": "11px"}),
            blank_equity,
            blank_drawdown,
            blank_rolling,
            blank_factor,
            ql_ui.render_trade_blotter([]),
            ql_ui.render_signal_feed([], []),
        )

    optimization = result.get("optimization", {})
    metrics = ql_ui.render_key_value_block({"best_score": optimization.get("best_score", 0.0), **optimization.get("best_params", {})})
    return (
        f"Optimization completed via {result.get('method', 'grid')} search.",
        summary,
        metrics,
        dash.html.Div(f"{len(optimization.get('results', []))} parameter evaluations completed.", style={"color": C["text_primary"], "fontFamily": "'IBM Plex Mono', monospace", "fontSize": "11px"}),
        dash.html.Div("Optimization runs are returned interactively; storeable experiment support can be layered in next.", style={"color": C["text_dim"], "fontFamily": "'IBM Plex Mono', monospace", "fontSize": "11px"}),
        blank_equity,
        blank_drawdown,
        blank_rolling,
        blank_factor,
        ql_ui.render_trade_blotter([]),
        ql_ui.render_signal_feed([], []),
    )


# ─────────────────────────────────────────────────────────────────────────────
# AI Briefing  —  updates when portfolio data refreshes
# ─────────────────────────────────────────────────────────────────────────────

@app.callback(
    Output("briefing-text", "children"),
    Output("briefing-time", "children"),
    Input("store-portfolio",  "data"),
    prevent_initial_call=False,
)
def update_ai_briefing(store_data):
    if not store_data:
        return "Waiting for portfolio data…", ""
    try:
        # Get fresh headlines to give the AI real context
        headlines = dm.get_rss_news()
        result    = dm.get_ai_briefing(store_data, headlines)
        time_str  = f"Generated {result['generated_at']}" if result.get("generated_at") else ""
        return result["text"], time_str
    except Exception as exc:
        return f"AI Briefing unavailable ({exc})", ""


# ─────────────────────────────────────────────────────────────────────────────
# Intelligence tab — all five panels
# ─────────────────────────────────────────────────────────────────────────────

@app.callback(
    Output("intel-regime-panel",     "children"),
    Output("intel-crossasset-panel", "children"),
    Output("intel-sm-panel",         "children"),
    Output("intel-trade-panel",      "children"),
    Output("intel-signal-feed",      "children"),
    Input("store-refresh-ts",        "data"),
    Input("main-tabs",               "value"),
    State("store-portfolio",         "data"),
    State("user-settings",           "data"),
    prevent_initial_call=False,
)
def update_intelligence_panels(ts, active_tab, portfolio_store, settings):
    """
    Runs all intelligence layers and populates the five panels.
    Only computes when the intelligence tab is active (skips otherwise).
    """
    if active_tab != "intelligence":
        return (dash.no_update,) * 5

    # Resolve active tickers
    tickers = PORTFOLIO_TICKERS
    try:
        if settings:
            port_key = settings.get("active_portfolio", "default")
            port     = settings.get("portfolios", {}).get(port_key, {})
            t_list   = port.get("tickers", [])
            if t_list:
                tickers = t_list
    except Exception:
        pass

    # Re-hydrate portfolio data with full DataFrames (store strips them)
    portfolio_data = {}
    try:
        for t in tickers:
            portfolio_data[t] = dm.get_ticker_data(t)
    except Exception:
        pass

    try:
        report = intel.get_full_intelligence(tickers, portfolio_data)
    except Exception as e:
        traceback.print_exc()
        err = dash.html.Div(f"Intelligence engine error: {e}",
                            style={"color": C["red"], "fontFamily": "'IBM Plex Mono'", "fontSize": "11px"})
        return err, err, err, err, err

    regime      = report.get("regime",             {})
    cross_intel = report.get("cross_intel",        {})
    sm_scores   = report.get("smart_money_scores", {})
    predictions = report.get("predictions",        {})
    trade_ideas = report.get("trade_ideas",        [])
    signal_feed = report.get("signal_feed",        [])
    stats       = report.get("signal_stats",       {})

    # Record new predictions for learning system (fire-and-forget)
    try:
        for ticker, pred in predictions.items():
            intel.record_prediction(pred, sm_scores.get(ticker, {}))
    except Exception:
        pass

    return (
        ly.build_intel_regime_panel(regime),
        ly.build_intel_crossasset_panel(cross_intel),
        ly.build_intel_sm_leaderboard(sm_scores, predictions),
        ly.build_intel_trade_ideas(trade_ideas),
        ly.build_intel_signal_feed(signal_feed, stats),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Portfolio tab: ticker cards
# ─────────────────────────────────────────────────────────────────────────────

@app.callback(
    Output("portfolio-cards", "children"),
    Input("store-portfolio",  "data"),
    State("user-settings",    "data"),
    prevent_initial_call=False,
)
def update_portfolio_cards(store_data, settings):
    if not store_data:
        return [dash.html.Div("Loading data…",
                              style={"color": C["text_dim"], "fontFamily": "'IBM Plex Mono', monospace",
                                     "padding": "20px"})]
    # Use the tickers present in store (driven by settings)
    tickers = list(store_data.keys())
    cards   = []
    for t in tickers:
        d = dict(store_data.get(t, {}))
        d["ticker"] = t
        cards.append(ly.build_portfolio_card(d))
    return cards


@app.callback(
    Output("ytd-bar", "figure"),
    Input("store-portfolio", "data"),
    prevent_initial_call=False,
)
def update_ytd_bar(store_data):
    if not store_data:
        return cb._empty_chart("Loading…")
    return cb.build_portfolio_bar(store_data)


@app.callback(
    Output("correlation-heatmap", "figure"),
    Input("store-refresh-ts", "data"),
    State("user-settings",    "data"),
    prevent_initial_call=False,
)
def update_correlation(ts, settings):
    try:
        # Use the active portfolio's tickers (same list as the cards)
        tickers = PORTFOLIO_TICKERS
        try:
            if settings:
                port_key = settings.get("active_portfolio", "default")
                port     = settings.get("portfolios", {}).get(port_key, {})
                t_list   = port.get("tickers", [])
                if t_list:
                    tickers = t_list
        except Exception:
            pass
        all_data = {t: dm.get_ticker_data(t) for t in tickers}
        return cb.build_correlation_heatmap(all_data)
    except Exception:
        return cb._empty_chart("Correlation unavailable")


# ─────────────────────────────────────────────────────────────────────────────
# Portfolio sparklines (pattern-matching callback)
# ─────────────────────────────────────────────────────────────────────────────

@app.callback(
    Output({"type": "sparkline", "index": ALL}, "figure"),
    Input("store-portfolio", "data"),
    prevent_initial_call=False,
)
def update_sparklines(store_data):
    if not store_data:
        return []
    figures = []
    for t in store_data.keys():
        try:
            d     = dm.get_ticker_data(t)
            df    = d.get("df")
            chg   = d.get("chg_pct", 0.0)
            color = C["green"] if chg >= 0 else C["red"]
            figures.append(cb.build_sparkline(df, color=color))
        except Exception:
            figures.append(cb._empty_chart(""))
    return figures


# ─────────────────────────────────────────────────────────────────────────────
# Deep Dive tab callbacks
# ─────────────────────────────────────────────────────────────────────────────

# ─────────────────────────────────────────────────────────────────────────────
# Period selector — update store + highlight active button
# ─────────────────────────────────────────────────────────────────────────────

@app.callback(
    Output("deepdive-period", "data"),
    Output({"type": "period-btn", "index": ALL}, "style"),
    Input({"type": "period-btn", "index": ALL}, "n_clicks"),
    State("deepdive-period", "data"),
    prevent_initial_call=True,
)
def select_period(n_clicks_list, current_period):
    ctx = callback_context
    if not ctx.triggered or not any(n_clicks_list):
        return dash.no_update, dash.no_update

    triggered_id = ctx.triggered[0]["prop_id"]
    try:
        parsed = json.loads(triggered_id.split(".n_clicks")[0])
        new_period = parsed["index"]
    except Exception:
        return dash.no_update, dash.no_update

    periods = ["1D", "5D", "1M", "3M", "6M", "1Y", "5Y"]
    styles  = []
    for p in periods:
        active = p == new_period
        styles.append({
            "background":    "color-mix(in srgb, var(--accent) 13%, transparent)" if active else "transparent",
            "border":        f"1px solid {'var(--accent)' if active else C['border']}",
            "borderRadius":  "2px",
            "color":         "var(--accent)" if active else C["text_secondary"],
            "fontFamily":    "'IBM Plex Mono', monospace",
            "fontSize":      "10px",
            "fontWeight":    "700" if active else "600",
            "padding":       "4px 10px",
            "cursor":        "pointer",
            "letterSpacing": "0.06em",
        })
    return new_period, styles


# Period → (yfinance period, interval) mapping
_PERIOD_MAP = {
    "1D":  ("1d",  "5m"),
    "5D":  ("5d",  "30m"),
    "1M":  ("1mo", "1d"),
    "3M":  ("3mo", "1d"),
    "6M":  ("6mo", "1d"),
    "1Y":  ("1y",  "1d"),
    "5Y":  ("5y",  "1wk"),
}

@app.callback(
    Output("deepdive-chart",   "figure"),
    Output("deepdive-outlook", "children"),
    Input("deepdive-ticker",   "value"),
    Input("deepdive-period",   "data"),
    Input("store-refresh-ts",  "data"),
    State("user-settings",     "data"),
    prevent_initial_call=False,
)
def update_deepdive(ticker, period, ts, settings):
    if not ticker:
        return cb._empty_chart("Select a ticker"), dash.html.Div()

    try:
        yf_period, yf_interval = _PERIOD_MAP.get(period or "6M", ("6mo", "1d"))

        indicators = (settings or {}).get("indicators", {})

        # Fetch chart data + the three panel data sources in parallel
        with ThreadPoolExecutor(max_workers=4) as pool:
            fut_chart = pool.submit(dm.get_chart_data, ticker, yf_period, yf_interval)
            fut_fund  = pool.submit(dm.get_ticker_fundamentals, ticker)
            fut_opts  = pool.submit(dm.get_options_flow, ticker)
            fut_news  = pool.submit(dm.get_ticker_news, ticker, 8)

            chart_df     = fut_chart.result()
            fundamentals = fut_fund.result()
            options_flow = fut_opts.result()
            news_articles= fut_news.result()

        # Signal data still comes from the standard 6mo daily cache (unchanged)
        data    = dm.get_ticker_data(ticker)
        signals = data.get("signals", [])

        chart   = cb.build_main_chart(chart_df, ticker, indicators=indicators)
        radar   = cb.build_signal_radar(signals)
        outlook = ly.build_outlook_panel(data,
                                         radar_fig=radar,
                                         news_articles=news_articles,
                                         fundamentals=fundamentals,
                                         options_flow=options_flow)
        return chart, outlook

    except Exception as e:
        traceback.print_exc()
        return cb._empty_chart(f"Error: {e}"), dash.html.Div(str(e))


# ─────────────────────────────────────────────────────────────────────────────
# Market Monitor tab callbacks
# ─────────────────────────────────────────────────────────────────────────────

@app.callback(
    Output("market-futures",       "children"),
    Output("market-indices",       "children"),
    Output("market-crypto",        "children"),
    Output("market-bonds",         "children"),
    Output("market-commodities",   "children"),
    Output("market-fx",            "children"),
    Output("sector-heatmap-graph", "figure"),
    Input("store-refresh-ts",      "data"),
    prevent_initial_call=False,
)
def update_market_monitor(ts):
    # Futures strip
    try:
        futures_rows = dm.get_futures_data()
        futures_out  = ly.build_futures_table(futures_rows)
    except Exception as e:
        futures_out = dash.html.Div(f"Error: {e}",
                      style={"color": C["red"], "fontFamily": "'IBM Plex Mono'",
                             "fontSize": "11px"})

    # Standard market table sections
    sections = ["indices", "crypto", "bonds", "commodities", "fx"]
    results  = [futures_out]
    for section in sections:
        try:
            rows = dm.get_market_data(section)
            results.append(ly.build_market_table(rows))
        except Exception as e:
            results.append(dash.html.Div(f"Error: {e}",
                           style={"color": C["red"], "fontFamily": "'IBM Plex Mono'",
                                  "fontSize": "11px"}))

    # Sector heatmap figure — output directly to dcc.Graph.figure
    try:
        sector_data = dm.get_sector_data()
        sector_fig  = cb.build_sector_heatmap(sector_data)
    except Exception:
        sector_fig  = go.Figure()

    results.append(sector_fig)
    return results


# ─────────────────────────────────────────────────────────────────────────────
# Sector heatmap tile click → drill-down panel
# ─────────────────────────────────────────────────────────────────────────────

_SECTOR_NAME_MAP = {
    "XLK":  "Technology",          "XLF":  "Financials",
    "XLV":  "Health Care",         "XLY":  "Cons. Discretionary",
    "XLP":  "Cons. Staples",       "XLI":  "Industrials",
    "XLE":  "Energy",              "XLC":  "Comm. Services",
    "XLRE": "Real Estate",         "XLB":  "Materials",
    "XLU":  "Utilities",
}

@app.callback(
    Output("sector-drill-down", "children"),
    Output("sector-drill-down", "style"),
    Input("sector-heatmap-graph", "clickData"),
    prevent_initial_call=True,
)
def show_sector_drilldown(click_data):
    if not click_data:
        return [], {"display": "none"}

    try:
        # customdata holds the clean ETF symbol (e.g. "XLK")
        # label holds the formatted HTML tile text — don't use it for lookup
        etf_symbol = click_data["points"][0]["customdata"]
    except (KeyError, IndexError):
        return [], {"display": "none"}

    if not etf_symbol or etf_symbol not in _SECTOR_NAME_MAP:
        return [], {"display": "none"}

    sector_name = _SECTOR_NAME_MAP[etf_symbol]
    holdings    = dm.get_sector_holdings_data(etf_symbol)

    if not holdings:
        return [dash.html.Div("No holdings data available.",
                style={"color": C["text_dim"], "fontFamily": "'IBM Plex Mono'",
                       "fontSize": "11px", "padding": "12px 0"})], {"display": "block"}

    panel = ly.build_sector_drill_down(etf_symbol, sector_name, holdings)
    return panel, {"display": "block"}


# ─────────────────────────────────────────────────────────────────────────────
# Calendar tab — filter toggles + content
# ─────────────────────────────────────────────────────────────────────────────

_CAL_CATS   = ["EARNINGS", "ECONOMIC", "FED", "IPO"]
_CAL_COLORS = {
    "EARNINGS": C["amber"],
    "ECONOMIC": "#38bdf8",
    "FED":      "#a78bfa",
    "IPO":      "#22c55e",
}


@app.callback(
    Output("cal-filter",                             "data"),
    Output({"type": "cal-filter-btn", "index": ALL}, "style"),
    Input({"type":  "cal-filter-btn", "index": ALL}, "n_clicks"),
    State("cal-filter",                              "data"),
    prevent_initial_call=True,
)
def toggle_cal_filter(n_clicks_list, active_cats):
    ctx = callback_context
    if not ctx.triggered or not any(n_clicks_list):
        return dash.no_update, dash.no_update

    try:
        triggered_id = ctx.triggered[0]["prop_id"]
        parsed       = json.loads(triggered_id.split(".n_clicks")[0])
        clicked_cat  = parsed["index"]
    except Exception:
        return dash.no_update, dash.no_update

    active_cats = list(active_cats or _CAL_CATS)
    if clicked_cat in active_cats:
        # Don't allow deselecting the last category
        if len(active_cats) > 1:
            active_cats.remove(clicked_cat)
    else:
        active_cats.append(clicked_cat)

    styles = []
    for cat in _CAL_CATS:
        color  = _CAL_COLORS.get(cat, C["amber"])
        active = cat in active_cats
        styles.append({
            "background":    f"color-mix(in srgb, {color} 18%, transparent)" if active else "transparent",
            "border":        f"1px solid {color}" if active else f"1px solid {C['border']}",
            "borderRadius":  "2px",
            "color":         color if active else C["text_secondary"],
            "fontFamily":    "'IBM Plex Mono', monospace",
            "fontSize":      "10px",
            "fontWeight":    "700" if active else "600",
            "padding":       "4px 14px",
            "cursor":        "pointer",
            "letterSpacing": "0.06em",
            "whiteSpace":    "nowrap",
        })
    return active_cats, styles


@app.callback(
    Output("cal-month",       "data"),
    Output("cal-month-label", "children"),
    Input("cal-prev-month",   "n_clicks"),
    Input("cal-next-month",   "n_clicks"),
    State("cal-month",        "data"),
    prevent_initial_call=True,
)
def navigate_cal_month(prev_clicks, next_clicks, month_data):
    import calendar as _cal_lib
    ctx       = callback_context
    triggered = ctx.triggered[0]["prop_id"] if ctx.triggered else ""

    year  = (month_data or {}).get("year",  datetime.date.today().year)
    month = (month_data or {}).get("month", datetime.date.today().month)

    if "prev" in triggered:
        month -= 1
        if month < 1:
            month = 12
            year -= 1
    else:
        month += 1
        if month > 12:
            month = 1
            year += 1

    label = datetime.datetime(year, month, 1).strftime("%B %Y").upper()
    return {"year": year, "month": month}, label


@app.callback(
    Output("calendar-content", "children"),
    Input("store-refresh-ts",  "data"),
    Input("cal-filter",        "data"),
    Input("cal-month",         "data"),
    State("user-settings",     "data"),
    prevent_initial_call=False,
)
def update_calendar(ts, active_cats, month_data, settings):
    active_cats = active_cats or _CAL_CATS
    today       = datetime.date.today()
    year        = (month_data or {}).get("year",  today.year)
    month       = (month_data or {}).get("month", today.month)

    # Resolve portfolio tickers for earnings lookup
    tickers = PORTFOLIO_TICKERS
    try:
        if settings:
            port_key = settings.get("active_portfolio", "default")
            port     = settings.get("portfolios", {}).get(port_key, {})
            t_list   = port.get("tickers", [])
            if t_list:
                tickers = t_list
    except Exception:
        pass

    try:
        events = dm.get_full_calendar(tickers)
        return ly.build_calendar_view(events, active_cats, year, month)
    except Exception as e:
        return dash.html.Div(f"Calendar error: {e}",
                             style={"color": C["red"], "fontFamily": "'IBM Plex Mono'",
                                    "fontSize": "11px"})


# ─────────────────────────────────────────────────────────────────────────────
# Calendar — event modal open / close
# ─────────────────────────────────────────────────────────────────────────────

@app.callback(
    Output("cal-modal-event",    "data"),
    Input({"type": "cal-event-pill", "index": ALL}, "n_clicks"),
    Input("cal-modal-close",     "n_clicks"),
    Input("cal-modal-backdrop",  "n_clicks"),
    prevent_initial_call=True,
)
def select_cal_event(pill_clicks, close_clicks, backdrop_clicks):
    ctx       = callback_context
    triggered = ctx.triggered[0]["prop_id"] if ctx.triggered else ""

    # Close on backdrop or X button
    if "cal-modal-close" in triggered or "cal-modal-backdrop" in triggered:
        return None

    # Ignore if no pill was actually clicked
    if not any(pill_clicks):
        return dash.no_update

    try:
        raw_index = json.loads(triggered.split(".n_clicks")[0])["index"]
        return json.loads(raw_index)
    except Exception:
        return dash.no_update


@app.callback(
    Output("cal-modal-backdrop", "style"),
    Output("cal-modal-panel",    "style"),
    Output("cal-modal-body",     "children"),
    Input("cal-modal-event",     "data"),
    prevent_initial_call=False,
)
def render_cal_modal(event_data):
    _hidden = {"display": "none"}
    _panel_base = {
        "position":     "fixed",
        "top":          "50%",
        "left":         "50%",
        "transform":    "translate(-50%, -50%)",
        "width":        "540px",
        "maxWidth":     "92vw",
        "maxHeight":    "80vh",
        "overflowY":    "auto",
        "background":   C["bg_panel"],
        "border":       f"1px solid {C['border']}",
        "borderRadius": "6px",
        "padding":      "22px 24px 24px",
        "zIndex":       "1000",
        "boxShadow":    "0 24px 60px rgba(0,0,0,0.7)",
    }

    if not event_data:
        return _hidden, {**_panel_base, "display": "none"}, []

    backdrop_style = {
        "display":    "block",
        "position":   "fixed",
        "top":        "0",
        "left":       "0",
        "right":      "0",
        "bottom":     "0",
        "background": "rgba(0, 6, 20, 0.80)",
        "zIndex":     "999",
        "cursor":     "pointer",
    }

    return (
        backdrop_style,
        {**_panel_base, "display": "flex", "flexDirection": "column"},
        ly.build_cal_modal_body(event_data),
    )


# ─────────────────────────────────────────────────────────────────────────────
# News Feed tab — category filter + feed update
# ─────────────────────────────────────────────────────────────────────────────

_NEWS_CAT_META = {
    "ALL":          C["amber"],
    "PORTFOLIO":    C["amber"],
    "GEOPOLITICAL": "#ef4444",
    "MACRO":        "#3b82f6",
    "MARKETS":      "#22c55e",
    "COMMODITIES":  "#f97316",
}
_NEWS_CAT_LABELS = ["ALL", "PORTFOLIO", "GEOPOLITICAL", "MACRO", "MARKETS", "COMMODITIES"]


@app.callback(
    Output("news-filter", "data"),
    Output({"type": "news-filter-btn", "index": ALL}, "style"),
    Input({"type": "news-filter-btn", "index": ALL}, "n_clicks"),
    State("news-filter", "data"),
    prevent_initial_call=True,
)
def select_news_filter(n_clicks_list, current_filter):
    ctx = callback_context
    if not ctx.triggered or not any(n_clicks_list):
        return dash.no_update, dash.no_update

    try:
        triggered_id = ctx.triggered[0]["prop_id"]
        parsed       = json.loads(triggered_id.split(".n_clicks")[0])
        new_filter   = parsed["index"]
    except Exception:
        return dash.no_update, dash.no_update

    styles = []
    for cat in _NEWS_CAT_LABELS:
        color  = _NEWS_CAT_META.get(cat, C["amber"])
        active = cat == new_filter
        styles.append({
            "background":    f"color-mix(in srgb, {color} 18%, transparent)" if active else "transparent",
            "border":        f"1px solid {color}" if active else f"1px solid {C['border']}",
            "borderRadius":  "2px",
            "color":         color if active else C["text_secondary"],
            "fontFamily":    "'IBM Plex Mono', monospace",
            "fontSize":      "10px",
            "fontWeight":    "700" if active else "600",
            "padding":       "4px 12px",
            "cursor":        "pointer",
            "letterSpacing": "0.06em",
            "whiteSpace":    "nowrap",
        })
    return new_filter, styles


@app.callback(
    Output("news-feed-content", "children"),
    Input("store-refresh-ts",   "data"),
    Input("news-filter",        "data"),
    State("user-settings",      "data"),
    prevent_initial_call=False,
)
def update_news_feed(ts, filter_cat, settings):
    try:
        # Active portfolio tickers
        tickers = PORTFOLIO_TICKERS
        if settings:
            port_key = settings.get("active_portfolio", "default")
            port     = settings.get("portfolios", {}).get(port_key, {})
            t_list   = port.get("tickers", [])
            if t_list:
                tickers = t_list

        portfolio_news = dm.get_portfolio_news(tickers=tickers, max_per_ticker=4)
        rss_news       = dm.get_rss_news(max_per_source=8)
        return ly.build_news_feed(portfolio_news, rss_news, filter_cat=filter_cat or "ALL")
    except Exception as e:
        traceback.print_exc()
        return dash.html.Div(f"Error fetching news: {e}",
                             style={"color": C["red"], "fontFamily": "'IBM Plex Mono'",
                                    "fontSize": "11px"})


# ─────────────────────────────────────────────────────────────────────────────
# Settings callbacks
# ─────────────────────────────────────────────────────────────────────────────

# Theme + accent — clientside for instant response (no server round-trip)
app.clientside_callback(
    """
    function(settings) {
        if (!settings) return window.dash_clientside.no_update;

        // Theme class
        var theme = settings.theme || 'dark';
        if (theme === 'light') {
            document.body.classList.add('light-mode');
        } else {
            document.body.classList.remove('light-mode');
        }

        // Accent colour — set CSS variable so all var(--accent) rules update instantly
        var accent = settings.accent || '#fbbf24';
        document.documentElement.style.setProperty('--accent', accent);

        return window.dash_clientside.no_update;
    }
    """,
    Output("user-settings", "id"),   # dummy output — we just need the side-effect
    Input("user-settings", "data"),
)


@app.callback(
    Output("user-settings",            "data"),
    Output("settings-save-status",     "children"),
    Output("settings-active-tickers",  "children"),
    # Theme buttons
    Input({"type": "theme-btn",   "index": ALL}, "n_clicks"),
    # Accent swatches
    Input({"type": "accent-btn",  "index": ALL}, "n_clicks"),
    # Add custom ticker button
    Input("settings-add-ticker-btn",   "n_clicks"),
    # Remove ticker chips
    Input({"type": "remove-ticker-btn","index": ALL}, "n_clicks"),
    # Preset ticker quick-add
    Input({"type": "preset-ticker-btn","index": ALL}, "n_clicks"),
    # Save button
    Input("settings-save-btn",         "n_clicks"),
    # Portfolio name change
    Input("settings-portfolio-name",   "value"),
    # Portfolio switcher dropdown
    Input("settings-portfolio-select", "value"),
    # Current state
    State("settings-custom-ticker-input", "value"),
    State("user-settings", "data"),
    prevent_initial_call=True,
)
def handle_settings(theme_clicks, accent_clicks, add_clicks, remove_clicks,
                    preset_clicks, save_clicks, port_name, portfolio_select,
                    custom_ticker, settings):
    ctx     = callback_context
    if not ctx.triggered:
        return dash.no_update, "", dash.no_update

    import copy
    settings   = copy.deepcopy(settings or DEFAULT_SETTINGS)
    portfolios = settings.setdefault("portfolios", DEFAULT_SETTINGS["portfolios"])
    port_key   = settings.get("active_portfolio", "default")
    portfolio  = portfolios.setdefault(port_key, {"name": "My Portfolio", "tickers": []})
    tickers    = portfolio.setdefault("tickers", [])

    triggered_id  = ctx.triggered[0]["prop_id"]
    triggered_val = ctx.triggered[0]["value"]
    status_msg    = ""

    # ── Portfolio switcher ────────────────────────────────────────────────────
    if "settings-portfolio-select" in triggered_id and triggered_val:
        if triggered_val in portfolios:
            settings["active_portfolio"] = triggered_val
            switched = portfolios[triggered_val]
            tickers  = switched.get("tickers", [])
            status_msg = f"Switched to \"{switched.get('name', triggered_val)}\"."
            return settings, status_msg, ly._render_active_tickers(tickers)

    # ── Theme toggle ──────────────────────────────────────────────────────────
    elif "theme-btn" in triggered_id and triggered_val:
        try:
            parsed = json.loads(triggered_id.split(".n_clicks")[0])
            settings["theme"] = parsed["index"]
            status_msg = f"Theme set to {parsed['index']}."
        except Exception:
            pass

    # ── Accent color ──────────────────────────────────────────────────────────
    elif "accent-btn" in triggered_id and triggered_val:
        try:
            parsed = json.loads(triggered_id.split(".n_clicks")[0])
            settings["accent"] = parsed["index"]
            status_msg = "Accent color updated."
        except Exception:
            pass

    # ── Add custom ticker ─────────────────────────────────────────────────────
    elif "settings-add-ticker-btn" in triggered_id and triggered_val:
        t = (custom_ticker or "").strip().upper()
        if t and t not in tickers:
            tickers.append(t)
            status_msg = f"{t} added."
        elif t in tickers:
            status_msg = f"{t} already in portfolio."
        else:
            status_msg = "Enter a ticker symbol first."

    # ── Remove ticker chip ────────────────────────────────────────────────────
    elif "remove-ticker-btn" in triggered_id and triggered_val:
        try:
            parsed = json.loads(triggered_id.split(".n_clicks")[0])
            t = parsed["index"]
            if t in tickers:
                tickers.remove(t)
                status_msg = f"{t} removed."
        except Exception:
            pass

    # ── Preset ticker toggle ──────────────────────────────────────────────────
    elif "preset-ticker-btn" in triggered_id and triggered_val:
        try:
            parsed = json.loads(triggered_id.split(".n_clicks")[0])
            t = parsed["index"]
            if t in tickers:
                tickers.remove(t)
                status_msg = f"{t} removed."
            else:
                tickers.append(t)
                status_msg = f"{t} added."
        except Exception:
            pass

    # ── Portfolio name ────────────────────────────────────────────────────────
    elif "settings-portfolio-name" in triggered_id and port_name:
        portfolio["name"] = port_name
        status_msg = "Portfolio name saved."

    # ── Save button ───────────────────────────────────────────────────────────
    elif "settings-save-btn" in triggered_id:
        status_msg = f"✓ Saved — {len(tickers)} tickers in \"{portfolio['name']}\""

    portfolio["tickers"] = tickers
    return settings, status_msg, ly._render_active_tickers(tickers)


@app.callback(
    Output("user-settings",        "data",     allow_duplicate=True),
    Output("settings-portfolio-msg","children", allow_duplicate=True),
    Input("settings-new-portfolio-btn", "n_clicks"),
    State("user-settings", "data"),
    prevent_initial_call=True,
)
def new_portfolio(n_clicks, settings):
    if not n_clicks:
        return dash.no_update, ""
    import copy, uuid
    settings   = copy.deepcopy(settings or DEFAULT_SETTINGS)
    portfolios = settings.setdefault("portfolios", {})
    new_key    = f"portfolio_{uuid.uuid4().hex[:6]}"
    portfolios[new_key] = {"name": f"Portfolio {len(portfolios)+1}", "tickers": []}
    settings["active_portfolio"] = new_key
    return settings, "✓ New portfolio created. Add tickers below."


@app.callback(
    Output("user-settings",        "data",     allow_duplicate=True),
    Output("settings-portfolio-msg","children", allow_duplicate=True),
    Input("settings-delete-portfolio-btn", "n_clicks"),
    State("user-settings", "data"),
    prevent_initial_call=True,
)
def delete_portfolio(n_clicks, settings):
    if not n_clicks:
        return dash.no_update, ""
    import copy
    settings   = copy.deepcopy(settings or DEFAULT_SETTINGS)
    portfolios = settings.get("portfolios", {})
    port_key   = settings.get("active_portfolio", "default")
    if len(portfolios) <= 1:
        return dash.no_update, "⚠ Can't delete the only portfolio."
    portfolios.pop(port_key, None)
    settings["active_portfolio"] = next(iter(portfolios))
    return settings, "✓ Portfolio deleted."


# ─────────────────────────────────────────────────────────────────────────────
# Alerts — add / remove alert definitions
# ─────────────────────────────────────────────────────────────────────────────

@app.callback(
    Output("user-settings",              "data",     allow_duplicate=True),
    Output("settings-indicators-status", "children", allow_duplicate=True),
    Output({"type": "ind-toggle-btn", "index": ALL}, "style"),
    Input({"type": "ind-toggle-btn", "index": ALL}, "n_clicks"),
    State("user-settings", "data"),
    prevent_initial_call=True,
)
def toggle_indicator(n_clicks_list, settings):
    ctx = callback_context
    if not ctx.triggered or not any(n_clicks_list):
        return dash.no_update, dash.no_update, dash.no_update

    try:
        triggered_id = ctx.triggered[0]["prop_id"]
        key = json.loads(triggered_id.split(".n_clicks")[0])["index"]
    except Exception:
        return dash.no_update, dash.no_update, dash.no_update

    import copy
    settings = copy.deepcopy(settings or DEFAULT_SETTINGS)
    ind = settings.setdefault("indicators", dict(DEFAULT_SETTINGS["indicators"]))
    ind[key] = not ind.get(key, True)
    settings["indicators"] = ind

    # Rebuild button styles — order must match DOM order in layouts.py
    from config import CHART as _CHART
    _color_map = {
        "ma20":   _CHART["ma20"],
        "ma50":   _CHART["ma50"],
        "ma200":  _CHART["ma200"],
        "ema9":   _CHART["ema9"],
        "ema21":  _CHART["ema21"],
        "bb":     "#64748b",
        "vwap":   _CHART["vwap"],
        "volume": C["blue"],
        "obv":    "#22d3ee",
        "rsi":    _CHART["rsi"],
        "macd":   _CHART["macd_line"],
        "adx":    _CHART["adx"],
    }
    _label_map = {
        "ma20":   "MA 20",
        "ma50":   "MA 50",
        "ma200":  "MA 200",
        "ema9":   "EMA 9",
        "ema21":  "EMA 21",
        "bb":     "Bollinger Bands",
        "vwap":   "VWAP",
        "volume": "Volume",
        "obv":    "OBV",
        "rsi":    "RSI",
        "macd":   "MACD",
        "adx":    "ADX",
    }
    # Must match the button order in layouts.py Settings tab
    _keys = ["ma20", "ma50", "ma200", "ema9", "ema21", "bb", "vwap",
             "volume", "obv", "rsi", "macd", "adx"]
    styles = []
    for k in _keys:
        color  = _color_map.get(k, C["amber"])
        active = ind.get(k, True)
        styles.append({
            "background":    f"color-mix(in srgb, {color} 20%, transparent)" if active else "transparent",
            "border":        f"1px solid {color}" if active else f"1px solid {C['border']}",
            "borderRadius":  "3px",
            "color":         color if active else C["text_dim"],
            "fontFamily":    "'IBM Plex Mono', monospace",
            "fontSize":      "10px",
            "fontWeight":    "700" if active else "400",
            "padding":       "5px 12px",
            "cursor":        "pointer",
            "letterSpacing": "0.05em",
            "whiteSpace":    "nowrap",
        })

    label = _label_map.get(key, key.upper())
    status = f"{'ON' if ind[key] else 'OFF'}  —  {label}"
    return settings, status, styles


@app.callback(
    Output("user-settings",   "data",     allow_duplicate=True),
    Output("alert-status-msg","children", allow_duplicate=True),
    Input("alert-add-btn",    "n_clicks"),
    Input({"type": "alert-remove-btn", "index": ALL}, "n_clicks"),
    State("alert-ticker-input",    "value"),
    State("alert-type-select",     "value"),
    State("alert-threshold-input", "value"),
    State("user-settings",         "data"),
    prevent_initial_call=True,
)
def handle_alert_crud(add_clicks, remove_clicks, ticker, atype, threshold, settings):
    ctx = callback_context
    if not ctx.triggered:
        return dash.no_update, ""

    import copy, uuid
    settings = copy.deepcopy(settings or DEFAULT_SETTINGS)
    alerts   = settings.setdefault("alerts", [])
    triggered_id = ctx.triggered[0]["prop_id"]

    # ── Remove alert ──────────────────────────────────────────────────────────
    if "alert-remove-btn" in triggered_id and ctx.triggered[0]["value"]:
        try:
            parsed  = json.loads(triggered_id.split(".n_clicks")[0])
            alert_id = parsed["index"]
            settings["alerts"] = [a for a in alerts if a.get("id") != alert_id]
            return settings, "Alert removed."
        except Exception:
            return dash.no_update, ""

    # ── Add alert ─────────────────────────────────────────────────────────────
    if "alert-add-btn" in triggered_id and add_clicks:
        t = (ticker or "").strip().upper()
        if not t:
            return dash.no_update, "⚠ Enter a ticker symbol."
        if threshold is None or threshold <= 0:
            return dash.no_update, "⚠ Enter a valid threshold value."

        # Prevent exact duplicates
        for a in alerts:
            if a["ticker"] == t and a["type"] == atype and a["threshold"] == threshold:
                return dash.no_update, f"⚠ Identical alert already exists."

        alerts.append({
            "id":        uuid.uuid4().hex[:8],
            "ticker":    t,
            "type":      atype,
            "threshold": float(threshold),
            "active":    True,
        })
        label = {"above": f"above ${threshold:,.2f}",
                 "below": f"below ${threshold:,.2f}",
                 "pct_change": f"±{threshold}% daily"}
        return settings, f"✓ Alert set: {t} {label.get(atype, '')}."

    return dash.no_update, ""


# ─────────────────────────────────────────────────────────────────────────────
# Alerts — check prices on every data refresh, fire notifications
# ─────────────────────────────────────────────────────────────────────────────

@app.callback(
    Output("store-notifications", "data"),
    Input("store-portfolio",      "data"),
    State("user-settings",        "data"),
    State("store-notifications",  "data"),
    prevent_initial_call=True,
)
def check_alerts(store_data, settings, existing_notifications):
    if not store_data or not settings:
        return dash.no_update

    alerts       = settings.get("alerts", [])
    existing     = existing_notifications or []
    # Track which alerts already have an active (undismissed) notification
    active_ids   = {n["alert_id"] for n in existing}
    new_notifs   = list(existing)

    TYPE_LABELS  = {"above": "▲ above", "below": "▼ below", "pct_change": "± moved"}

    for alert in alerts:
        if not alert.get("active", True):
            continue
        alert_id  = alert.get("id", "")
        if alert_id in active_ids:
            continue   # already showing — don't duplicate

        ticker    = alert["ticker"]
        atype     = alert["type"]
        threshold = float(alert["threshold"])

        d = store_data.get(ticker, {})
        price     = d.get("price")
        chg_pct   = d.get("chg_pct", 0.0)

        if price is None:
            continue

        triggered = False
        if atype == "above"      and price >= threshold:
            triggered = True
            msg = f"{ticker} {TYPE_LABELS[atype]} ${threshold:,.2f}  —  now ${price:,.2f}"
        elif atype == "below"    and price <= threshold:
            triggered = True
            msg = f"{ticker} {TYPE_LABELS[atype]} ${threshold:,.2f}  —  now ${price:,.2f}"
        elif atype == "pct_change" and abs(chg_pct) >= threshold:
            triggered = True
            sign = "+" if chg_pct >= 0 else ""
            msg = f"{ticker} {TYPE_LABELS[atype]} {sign}{chg_pct:.2f}% today  —  ${price:,.2f}"

        if triggered:
            new_notifs.append({
                "id":       f"notif_{alert_id}_{int(datetime.datetime.now().timestamp())}",
                "alert_id": alert_id,
                "ticker":   ticker,
                "msg":      msg,
                "color":    C["green"] if atype != "below" else C["red"],
            })

    return new_notifs if new_notifs != existing else dash.no_update


# ─────────────────────────────────────────────────────────────────────────────
# Alerts — render in-app notification banner
# ─────────────────────────────────────────────────────────────────────────────

@app.callback(
    Output("notifications-banner", "children"),
    Input("store-notifications",   "data"),
    prevent_initial_call=False,
)
def render_notifications(notifications):
    from dash import html as _html
    if not notifications:
        return []

    chips = []
    for n in notifications:
        chips.append(_html.Div([
            _html.Span("🔔 ", style={"marginRight": "4px"}),
            _html.Span(n["msg"], style={
                "fontFamily": "'IBM Plex Mono', monospace",
                "fontSize":   "11px",
                "color":      C["text_white"],
                "flex":       "1",
            }),
            _html.Span("×", id={"type": "dismiss-notif-btn", "index": n["id"]},
                       n_clicks=0,
                       style={"cursor":"pointer","fontFamily":"'IBM Plex Mono',monospace",
                              "fontSize":"14px","marginLeft":"10px","color":C["text_dim"],
                              "userSelect":"none","lineHeight":"1"}),
        ], style={
            "display":      "flex",
            "alignItems":   "center",
            "background":   C["bg_panel"],
            "border":       f"1px solid {n.get('color', C['amber'])}",
            "borderLeft":   f"4px solid {n.get('color', C['amber'])}",
            "borderRadius": "4px",
            "padding":      "10px 14px",
            "boxShadow":    "0 4px 12px rgba(0,0,0,0.4)",
        }))
    return chips


@app.callback(
    Output("store-notifications", "data",    allow_duplicate=True),
    Input({"type": "dismiss-notif-btn", "index": ALL}, "n_clicks"),
    State("store-notifications",  "data"),
    prevent_initial_call=True,
)
def dismiss_notification(n_clicks_list, notifications):
    ctx = callback_context
    if not ctx.triggered or not any(n_clicks_list):
        return dash.no_update
    try:
        triggered_id = ctx.triggered[0]["prop_id"]
        parsed  = json.loads(triggered_id.split(".n_clicks")[0])
        notif_id = parsed["index"]
        return [n for n in (notifications or []) if n["id"] != notif_id]
    except Exception:
        return dash.no_update


# ─────────────────────────────────────────────────────────────────────────────
# Alerts — clientside browser notification (native Mac popup)
# ─────────────────────────────────────────────────────────────────────────────

app.clientside_callback(
    """
    function(notifications) {
        if (!notifications || notifications.length === 0)
            return window.dash_clientside.no_update;

        // Request permission on first alert
        if (Notification.permission === 'default') {
            Notification.requestPermission();
        }

        // Fire a native notification for each new item
        // Track fired IDs in window so we don't repeat on re-render
        if (!window._firedNotifIds) window._firedNotifIds = new Set();

        notifications.forEach(function(n) {
            if (!window._firedNotifIds.has(n.id) && Notification.permission === 'granted') {
                new Notification('Market Pulse Alert', {
                    body: n.msg,
                    icon: '',
                    tag:  n.id,
                });
                window._firedNotifIds.add(n.id);
            }
        });

        return window.dash_clientside.no_update;
    }
    """,
    Output("store-notifications", "id"),   # dummy output
    Input("store-notifications",  "data"),
)


# ─────────────────────────────────────────────────────────────────────────────
# Run
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n" + "═" * 60)
    print("  ◈  MARKET PULSE TERMINAL  —  starting up…")
    print("═" * 60)
    print("  Open your browser at:  http://127.0.0.1:8050")
    print("  Press Ctrl+C to stop.\n")
    app.run(debug=False, host="127.0.0.1", port=8050)
