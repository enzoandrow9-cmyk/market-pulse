from __future__ import annotations

import re

from dash import dcc, html
import dash_bootstrap_components as dbc
import plotly.graph_objects as go

from config import C
from quantlab.visualization.charts import apply_terminal_theme
from quantlab.visualization.factor_analysis_plots import build_factor_bar_figure


FONT_MONO = "'IBM Plex Mono', 'Courier New', monospace"
FIELD_LABEL = {
    "color": C["text_secondary"],
    "fontFamily": FONT_MONO,
    "fontSize": "9px",
    "letterSpacing": "0.08em",
    "textTransform": "uppercase",
    "marginBottom": "6px",
}
INPUT_STYLE = {
    "width": "100%",
    "background": C["bg_chart"],
    "border": f"1px solid {C['border']}",
    "color": C["text_primary"],
    "fontFamily": FONT_MONO,
    "fontSize": "11px",
    "padding": "10px 12px",
}
FIELD_STYLE = {"display": "block"}
HIDDEN_FIELD_STYLE = {"display": "none"}

ACTION_OPTIONS = [
    {"label": "Backtest", "value": "backtest"},
    {"label": "Research", "value": "research"},
    {"label": "Regime", "value": "regime"},
    {"label": "Optimize", "value": "optimize"},
]
STRATEGY_OPTIONS = [
    {"label": "SMA Crossover", "value": "sma_crossover"},
    {"label": "Mean Reversion", "value": "mean_reversion"},
    {"label": "Momentum Breakout", "value": "momentum_breakout"},
    {"label": "Volatility Targeting", "value": "volatility_targeting"},
]
MODE_OPTIONS = [
    {"label": "Event-Driven", "value": "event"},
    {"label": "Vectorized", "value": "vectorized"},
]
INTERVAL_OPTIONS = [
    {"label": "Daily", "value": "1d"},
    {"label": "Hourly", "value": "1h"},
]
OPTIMIZER_OPTIONS = [
    {"label": "Grid", "value": "grid"},
    {"label": "Random", "value": "random"},
    {"label": "Bayesian", "value": "bayesian"},
    {"label": "Genetic", "value": "genetic"},
]
WORKFLOW_VALUES = {item["value"] for item in ACTION_OPTIONS}
STRATEGY_VALUES = {item["value"] for item in STRATEGY_OPTIONS}
MODE_VALUES = {item["value"] for item in MODE_OPTIONS}
INTERVAL_VALUES = {item["value"] for item in INTERVAL_OPTIONS}


def _panel(children, min_height: str = "180px"):
    return html.Div(
        children,
        style={
            "background": C["bg_panel"],
            "border": f"1px solid {C['border']}",
            "borderRadius": "4px",
            "padding": "14px 16px",
            "minHeight": min_height,
        },
    )


def _section_title(text: str):
    return html.Div(
        text,
        style={
            "color": "var(--accent)",
            "fontFamily": FONT_MONO,
            "fontSize": "10px",
            "fontWeight": "700",
            "letterSpacing": "0.14em",
            "textTransform": "uppercase",
            "borderBottom": f"1px solid {C['border']}",
            "paddingBottom": "6px",
            "marginBottom": "10px",
        },
    )


def blank_figure(title: str) -> go.Figure:
    fig = go.Figure()
    fig.update_layout(title=title)
    return apply_terminal_theme(fig)


def _field(label: str, child, field_id: str | None = None, style: dict | None = None) -> html.Div:
    props = {"style": style or FIELD_STYLE}
    if field_id is not None:
        props["id"] = field_id
    return html.Div([html.Div(label, style=FIELD_LABEL), child], **props)


def _segmented_control(component_id: str, options: list[dict], value: str):
    return dbc.RadioItems(
        id=component_id,
        options=options,
        value=value,
        inline=True,
        className="btn-group quantlab-segmented",
        inputClassName="btn-check",
        labelClassName="btn quantlab-seg-btn btn-sm",
        labelCheckedClassName="active",
        style={"display": "flex", "flexWrap": "wrap", "gap": "6px"},
    )


def _clean_symbols(raw: str | None) -> list[str]:
    if not raw:
        return []
    return [token.upper() for token in re.split(r"[\s,]+", raw.strip()) if token]

def build_command_from_form(
    action: str | None,
    symbols: str | None,
    strategies: list[str] | None,
    start_date: str | None,
    end_date: str | None,
    simulation_mode: str | None,
    capital: float | int | None,
    interval: str | None,
    optimization_method: str | None,
) -> str:
    action = action or "backtest"
    clean_symbols = _clean_symbols(symbols) or ["AAPL"]
    strategy_list = strategies or ["sma_crossover"]
    start_date = start_date or "2018-01-01"
    end_date = end_date or "2024-01-01"

    if action == "research":
        parts = ["research", ",".join(clean_symbols), start_date, end_date]
        if interval:
            parts.append(f"interval={interval}")
        return " ".join(parts)

    if action == "regime":
        parts = ["regime", clean_symbols[0], start_date, end_date]
        if interval:
            parts.append(f"interval={interval}")
        return " ".join(parts)

    if action == "optimize":
        method = optimization_method or "grid"
        parts = ["optimize", clean_symbols[0], strategy_list[0], start_date, end_date, f"method={method}"]
        if simulation_mode:
            parts.append(f"mode={simulation_mode}")
        if capital not in (None, ""):
            if isinstance(capital, float) and capital.is_integer():
                capital = int(capital)
            parts.append(f"capital={capital}")
        if interval:
            parts.append(f"interval={interval}")
        return " ".join(str(part) for part in parts if str(part).strip())

    parts = [
        "backtest",
        ",".join(clean_symbols),
        ",".join(strategy_list),
        start_date,
        end_date,
    ]
    if simulation_mode:
        parts.append(f"mode={simulation_mode}")
    if capital not in (None, ""):
        if isinstance(capital, float) and capital.is_integer():
            capital = int(capital)
        parts.append(f"capital={capital}")
    if interval:
        parts.append(f"interval={interval}")
    return " ".join(str(part) for part in parts if str(part).strip())


def builder_hint(action: str | None) -> str:
    hints = {
        "backtest": "Backtest uses the selected simulation engine and interval directly. The command preview stays editable for advanced overrides.",
        "research": "Research mode runs factor and regime analysis across the symbol list and now honors the selected interval.",
        "regime": "Regime mode focuses on the first symbol and now honors the selected interval.",
        "optimize": "Optimize mode uses the first symbol and first strategy, and now respects simulation mode, capital, interval, and optimizer selection.",
    }
    return hints.get(action or "backtest", hints["backtest"])


def render_workflow_display(action: str | None):
    label = (action or "backtest").replace("_", " ").upper()
    return html.Div(
        [
            html.Div("ACTIVE WORKFLOW", style={"color": C["text_dim"], "fontFamily": FONT_MONO, "fontSize": "9px", "letterSpacing": "0.08em", "marginBottom": "6px"}),
            html.Div(label, style={"color": "var(--accent)", "fontFamily": FONT_MONO, "fontSize": "14px", "fontWeight": "800", "letterSpacing": "0.10em"}),
        ],
        style={
            "background": C["bg_chart"],
            "border": f"1px solid {C['border']}",
            "borderLeft": "3px solid var(--accent)",
            "padding": "10px 12px",
            "borderRadius": "3px",
            "minHeight": "58px",
            "display": "flex",
            "flexDirection": "column",
            "justifyContent": "center",
        },
    )


def build_quantlab_tab() -> html.Div:
    return html.Div(
        [
            html.Div(
                [
                    html.Span("◈ ", style={"color": "var(--accent)", "fontSize": "14px"}),
                    html.Span(
                        "QUANT LAB",
                        style={
                            "color": C["text_white"],
                            "fontFamily": FONT_MONO,
                            "fontSize": "12px",
                            "fontWeight": "900",
                            "letterSpacing": "0.12em",
                        },
                    ),
                    html.Span(
                        "  ·  Institutional research, backtesting, and experiment registry",
                        style={
                            "color": C["text_dim"],
                            "fontFamily": FONT_MONO,
                            "fontSize": "10px",
                            "letterSpacing": "0.08em",
                        },
                    ),
                ],
                style={"display": "flex", "alignItems": "center", "marginBottom": "14px"},
            ),
            _panel(
                [
                    _section_title("Test Builder"),
                    html.Div(
                        [
                            _field(
                                "Workflow",
                                _segmented_control(
                                    component_id="quantlab-action",
                                    options=ACTION_OPTIONS,
                                    value="backtest",
                                ),
                            ),
                            _field(
                                "Symbols",
                                dcc.Input(
                                    id="quantlab-symbols",
                                    type="text",
                                    value="AAPL",
                                    placeholder="AAPL, MSFT, NVDA",
                                    style=INPUT_STYLE,
                                ),
                            ),
                            _field(
                                "Strategies",
                                dcc.Dropdown(
                                    id="quantlab-strategies",
                                    options=STRATEGY_OPTIONS,
                                    value=["sma_crossover"],
                                    multi=True,
                                    clearable=False,
                                    className="bloomberg-dropdown",
                                ),
                                field_id="quantlab-strategies-field",
                            ),
                            _field(
                                "Simulation",
                                _segmented_control(
                                    component_id="quantlab-simulation-mode",
                                    options=MODE_OPTIONS,
                                    value="event",
                                ),
                                field_id="quantlab-simulation-field",
                            ),
                        ],
                        style={"display": "grid", "gridTemplateColumns": "1fr 1.2fr 1.4fr 1fr", "gap": "10px", "marginBottom": "10px"},
                    ),
                    html.Div(
                        [
                            _field(
                                "Start Date",
                                dcc.Input(
                                    id="quantlab-start-date",
                                    type="text",
                                    value="2018-01-01",
                                    placeholder="YYYY-MM-DD",
                                    style=INPUT_STYLE,
                                ),
                            ),
                            _field(
                                "End Date",
                                dcc.Input(
                                    id="quantlab-end-date",
                                    type="text",
                                    value="2024-01-01",
                                    placeholder="YYYY-MM-DD",
                                    style=INPUT_STYLE,
                                ),
                            ),
                            _field(
                                "Capital",
                                dcc.Input(
                                    id="quantlab-capital",
                                    type="number",
                                    value=250000,
                                    min=1000,
                                    step=1000,
                                    style=INPUT_STYLE,
                                ),
                                field_id="quantlab-capital-field",
                            ),
                            _field(
                                "Interval",
                                _segmented_control(
                                    component_id="quantlab-interval",
                                    options=INTERVAL_OPTIONS,
                                    value="1d",
                                ),
                                field_id="quantlab-interval-field",
                            ),
                        ],
                        style={"display": "grid", "gridTemplateColumns": "1fr 1fr 1fr 1fr", "gap": "10px", "marginBottom": "10px"},
                    ),
                    html.Div(
                        [
                            _field(
                                "Optimizer",
                                dcc.Dropdown(
                                    id="quantlab-optimizer-method",
                                    options=OPTIMIZER_OPTIONS,
                                    value="grid",
                                    clearable=False,
                                    className="bloomberg-dropdown",
                                ),
                                field_id="quantlab-optimizer-field",
                                style=HIDDEN_FIELD_STYLE,
                            ),
                            html.Div(
                                [
                                    html.Div("Selected Workflow", style=FIELD_LABEL),
                                    html.Div(
                                        id="quantlab-workflow-display",
                                        children=render_workflow_display("backtest"),
                                    ),
                                ]
                            ),
                            html.Div(
                                [
                                    html.Div("Builder Notes", style=FIELD_LABEL),
                                    html.Div(
                                        id="quantlab-builder-hint",
                                        children=builder_hint("backtest"),
                                        style={
                                            "color": C["text_secondary"],
                                            "fontFamily": FONT_MONO,
                                            "fontSize": "10px",
                                            "lineHeight": "1.6",
                                            "paddingTop": "10px",
                                        },
                                    ),
                                ],
                            ),
                            html.Div(
                                [
                                    html.Div("Run", style=FIELD_LABEL),
                                    html.Button(
                                        "RUN TEST",
                                        id="quantlab-run-btn",
                                        n_clicks=0,
                                        style={
                                            "width": "100%",
                                            "background": "transparent",
                                            "border": "1px solid var(--accent)",
                                            "color": "var(--accent)",
                                            "fontFamily": FONT_MONO,
                                            "fontSize": "10px",
                                            "padding": "10px 16px",
                                            "cursor": "pointer",
                                            "letterSpacing": "0.08em",
                                        },
                                    ),
                                ],
                            ),
                        ],
                        style={"display": "grid", "gridTemplateColumns": "1fr 1fr 1.4fr 0.8fr", "gap": "10px", "marginBottom": "12px"},
                    ),
                    _section_title("Advanced Command Preview"),
                    dcc.Textarea(
                        id="quantlab-command",
                        value=build_command_from_form(
                            action="backtest",
                            symbols="AAPL",
                            strategies=["sma_crossover"],
                            start_date="2018-01-01",
                            end_date="2024-01-01",
                            simulation_mode="event",
                            capital=250000,
                            interval="1d",
                            optimization_method="grid",
                        ),
                        style={
                            **INPUT_STYLE,
                            "minHeight": "74px",
                            "resize": "vertical",
                        },
                    ),
                    html.Div(
                        "Use the builder for clean test setup. The command preview is still editable for advanced parameters and nonstandard workflows.",
                        style={
                            "color": C["text_secondary"],
                            "fontFamily": FONT_MONO,
                            "fontSize": "10px",
                            "lineHeight": "1.6",
                            "marginTop": "10px",
                        },
                    ),
                    html.Div(
                        id="quantlab-status",
                        children="Ready. Configure a test and run Quant Lab.",
                        style={"color": C["text_dim"], "fontFamily": FONT_MONO, "fontSize": "11px", "marginTop": "10px"},
                    ),
                ],
                min_height="260px",
            ),
            html.Div(
                [
                    _panel([_section_title("Run Summary"), html.Div(id="quantlab-summary")], min_height="220px"),
                    _panel([_section_title("Metrics"), html.Div(id="quantlab-metrics")], min_height="220px"),
                    _panel([_section_title("Risk / Capacity"), html.Div(id="quantlab-risk-panel")], min_height="220px"),
                ],
                style={"display": "grid", "gridTemplateColumns": "1.1fr 1fr 1fr", "gap": "10px", "marginTop": "10px"},
            ),
            html.Div(
                [
                    _panel([_section_title("Experiment Registry"), html.Div(id="quantlab-experiment")], min_height="220px"),
                    _panel([_section_title("Trade Blotter"), html.Div(id="quantlab-trades-table")], min_height="220px"),
                ],
                style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "10px", "marginTop": "10px"},
            ),
            html.Div(
                [
                    _panel([dcc.Graph(id="quantlab-equity-graph", figure=blank_figure("Equity Curve"), config={"displayModeBar": False})], min_height="280px"),
                    _panel([dcc.Graph(id="quantlab-drawdown-graph", figure=blank_figure("Drawdown"), config={"displayModeBar": False})], min_height="280px"),
                ],
                style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "10px", "marginTop": "10px"},
            ),
            html.Div(
                [
                    _panel([dcc.Graph(id="quantlab-rolling-graph", figure=blank_figure("Rolling Sharpe"), config={"displayModeBar": False})], min_height="280px"),
                    _panel([dcc.Graph(id="quantlab-factor-graph", figure=blank_figure("Factor Ranking"), config={"displayModeBar": False})], min_height="280px"),
                ],
                style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "10px", "marginTop": "10px"},
            ),
            _panel([_section_title("Signal Feed"), html.Div(id="quantlab-signals-feed")], min_height="220px"),
        ],
        style={"padding": "16px 20px", "background": C["bg"], "minHeight": "calc(100vh - 74px)"},
    )


def render_key_value_block(data: dict, value_fmt: str | None = None):
    if not data:
        return html.Div("No data", style={"color": C["text_dim"], "fontFamily": FONT_MONO, "fontSize": "11px"})
    rows = []
    for key, value in data.items():
        display = value
        if isinstance(value, float):
            if value_fmt == "pct":
                display = f"{value:.2%}"
            else:
                display = f"{value:,.4f}"
        rows.append(
            html.Div(
                [
                    html.Span(key.replace("_", " ").upper(), style={"color": C["text_secondary"], "fontFamily": FONT_MONO, "fontSize": "9px", "width": "160px", "display": "inline-block"}),
                    html.Span(str(display), style={"color": C["text_primary"], "fontFamily": FONT_MONO, "fontSize": "10px", "fontWeight": "600"}),
                ],
                style={"marginBottom": "4px"},
            )
        )
    return html.Div(rows)


def render_summary(result: dict):
    lines = [
        ("MODE", result.get("mode", "backtest")),
        ("COMMAND", result.get("command", "")),
    ]
    if "config" in result:
        cfg = result["config"]
        lines.extend(
            [
                ("SYMBOLS", ", ".join(cfg.get("symbols", []))),
                ("STRATEGIES", ", ".join(cfg.get("strategies", []))),
                ("PERIOD", f"{cfg.get('start_date')} -> {cfg.get('end_date')}"),
                ("SIMULATION", cfg.get("simulation_mode", "event")),
                ("REGIME", result.get("regime", {}).get("regime", "unknown")),
            ]
        )
    return html.Div(
        [
            html.Div(
                [
                    html.Span(f"{label}: ", style={"color": C["text_secondary"]}),
                    html.Span(value, style={"color": C["text_primary"]}),
                ],
                style={"fontFamily": FONT_MONO, "fontSize": "10px", "marginBottom": "6px", "lineHeight": "1.5"},
            )
            for label, value in lines
        ]
    )


def render_experiment(result: dict):
    experiment = result.get("experiment", {})
    lines = [
        ("EXPERIMENT ID", experiment.get("experiment_id", "n/a")),
        ("RESULTS PATH", experiment.get("results_path", "n/a")),
        ("DATASET", result.get("dataset_version", "n/a")),
    ]
    report = result.get("report_markdown")
    body = [
        html.Div(
            [
                html.Span(f"{label}: ", style={"color": C["text_secondary"]}),
                html.Span(value, style={"color": C["text_primary"]}),
            ],
            style={"fontFamily": FONT_MONO, "fontSize": "10px", "marginBottom": "6px", "lineHeight": "1.5"},
        )
        for label, value in lines
    ]
    if report:
        body.append(
            html.Pre(
                report,
                style={
                    "background": C["bg_chart"],
                    "border": f"1px solid {C['border']}",
                    "color": C["text_primary"],
                    "fontFamily": FONT_MONO,
                    "fontSize": "10px",
                    "padding": "10px",
                    "marginTop": "10px",
                    "whiteSpace": "pre-wrap",
                },
            )
        )
    return html.Div(body)


def render_trade_blotter(rows: list[dict], max_rows: int = 10):
    if not rows:
        return html.Div("No closed trades yet", style={"color": C["text_dim"], "fontFamily": FONT_MONO, "fontSize": "11px"})
    header = html.Div(
        [
            html.Span(text, style={"width": width, "display": "inline-block", "color": C["text_dim"], "fontFamily": FONT_MONO, "fontSize": "9px"})
            for text, width in [("TIME", "150px"), ("SYMBOL", "70px"), ("SIDE", "60px"), ("QTY", "80px"), ("PNL", "90px")]
        ],
        style={"marginBottom": "6px"},
    )
    body = []
    for row in rows[:max_rows]:
        pnl = float(row.get("pnl", 0.0))
        body.append(
            html.Div(
                [
                    html.Span(str(row.get("timestamp", ""))[:19], style={"width": "150px", "display": "inline-block"}),
                    html.Span(str(row.get("symbol", "")), style={"width": "70px", "display": "inline-block"}),
                    html.Span(str(row.get("side", "")), style={"width": "60px", "display": "inline-block"}),
                    html.Span(f"{float(row.get('quantity', 0.0)):,.2f}", style={"width": "80px", "display": "inline-block"}),
                    html.Span(f"{pnl:,.2f}", style={"width": "90px", "display": "inline-block", "color": C["green"] if pnl >= 0 else C["red"]}),
                ],
                style={"fontFamily": FONT_MONO, "fontSize": "10px", "marginBottom": "5px", "color": C["text_primary"]},
            )
        )
    return html.Div([header, *body])


def render_signal_feed(signals: list[dict], risk_events: list[dict], max_rows: int = 12):
    rows = []
    for signal in signals[:max_rows]:
        rows.append(
            html.Div(
                f"{str(signal.get('timestamp', ''))[:19]}  {signal.get('strategy_id', '')}  {signal.get('symbol', '')}  tw={signal.get('target_weight', 0.0):+.3f}  {signal.get('reason', '')}",
                style={"color": C["text_primary"], "fontFamily": FONT_MONO, "fontSize": "10px", "marginBottom": "4px"},
            )
        )
    for event in risk_events[: max(0, max_rows - len(rows))]:
        rows.append(
            html.Div(
                f"{str(event.get('timestamp', ''))[:19]}  RISK  {event.get('symbol', '')}  {event.get('reason', '')}",
                style={"color": C["red"], "fontFamily": FONT_MONO, "fontSize": "10px", "marginBottom": "4px"},
            )
        )
    if not rows:
        rows = [html.Div("No signals generated", style={"color": C["text_dim"], "fontFamily": FONT_MONO, "fontSize": "11px"})]
    return html.Div(rows)


def render_factor_figure(ranking):
    if hasattr(ranking, "empty"):
        return build_factor_bar_figure(ranking)
    return blank_figure("Factor Ranking")
