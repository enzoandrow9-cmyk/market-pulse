# ─────────────────────────────────────────────────────────────────────────────
# command_parser.py  —  Bloomberg Terminal Dashboard  •  Enzo Market Pulse
#
# Bloomberg-style command palette parser.
#
# Parses shorthand commands like:
#   AAPL          → Deep Dive on AAPL
#   AAPL DD       → Deep Dive on AAPL
#   AAPL NEWS     → News tab filtered to AAPL
#   AAPL OPT      → Deep Dive (Options panel) on AAPL
#   SPX HEAT      → Market heatmap
#   BTC CORR      → Correlations tab
#   FED CAL       → Calendar tab
#   SIGNALS       → Signals scanner tab
# ─────────────────────────────────────────────────────────────────────────────

from __future__ import annotations

import logging
import re
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Tab routing map — command keyword → tab value
# ─────────────────────────────────────────────────────────────────────────────

_COMMAND_ROUTES: Dict[str, str] = {
    # Deep Dive
    "DD":           "deepdive",
    "DEEPDIVE":     "deepdive",
    "CHART":        "deepdive",
    "OPT":          "deepdive",
    "OPTIONS":      "deepdive",
    "TECH":         "deepdive",
    # Market
    "HEAT":         "market",
    "MARKET":       "market",
    "MKT":          "market",
    "FUTURES":      "market",
    "FX":           "market",
    # News
    "NEWS":         "news",
    "NWS":          "news",
    # Calendar
    "CAL":          "calendar",
    "CALENDAR":     "calendar",
    "FED":          "calendar",
    "EARNINGS":     "calendar",
    # Portfolio
    "PORT":         "portfolio",
    "PORTFOLIO":    "portfolio",
    # Intelligence
    "INTL":         "intelligence",
    "INTEL":        "intelligence",
    "INTELLIGENCE": "intelligence",
    "SMART":        "intelligence",
    # Quant Lab
    "QUANT":        "quantlab",
    "LAB":          "quantlab",
    "QUANTLAB":     "quantlab",
    "BACKTEST":     "quantlab",
    # Signals scanner
    "SIG":          "signals",
    "SIGNALS":      "signals",
    "SCAN":         "signals",
    "SCANNER":      "signals",
    "RSI":          "signals",
    "MACD":         "signals",
    # Correlations
    "CORR":         "correlations",
    "CORRELATION":  "correlations",
    "CORRELATIONS": "correlations",
    "HEAT2":        "correlations",
    # Settings
    "SETTINGS":     "settings",
    "CONFIG":       "settings",
}

# Tab names expressed as full words — for direct tab-name routing
_TAB_DIRECT: Dict[str, str] = {
    "PORTFOLIO":    "portfolio",
    "DEEPDIVE":     "deepdive",
    "MARKET":       "market",
    "QUANTLAB":     "quantlab",
    "INTELLIGENCE": "intelligence",
    "CALENDAR":     "calendar",
    "NEWS":         "news",
    "SETTINGS":     "settings",
    "SIGNALS":      "signals",
    "CORRELATIONS": "correlations",
}

# Known ticker pattern — 1-5 uppercase letters (or common crypto / index formats)
_TICKER_RE = re.compile(r"^[A-Z]{1,5}(-[A-Z]{1,3})?$|^\^[A-Z]{1,5}$|^[A-Z]{1,4}=F$|^[A-Z]{3,4}-USD$")

# Alias overrides: command inputs to canonical ticker
_TICKER_ALIASES: Dict[str, str] = {
    "SPX":   "^GSPC",
    "SPY":   "SPY",
    "NDX":   "^IXIC",
    "QQQ":   "QQQ",
    "DJI":   "^DJI",
    "DOW":   "^DJI",
    "VIX":   "^VIX",
    "BTC":   "BTC-USD",
    "ETH":   "ETH-USD",
    "SOL":   "SOL-USD",
    "GOLD":  "GC=F",
    "OIL":   "CL=F",
    "DXY":   "DX-Y.NYB",
}

# ─────────────────────────────────────────────────────────────────────────────
# Suggestion corpus — shown in the palette before user types
# ─────────────────────────────────────────────────────────────────────────────

SUGGESTIONS: List[Dict[str, str]] = [
    {"cmd": "AAPL DD",       "desc": "Deep Dive — Apple"},
    {"cmd": "NVDA DD",       "desc": "Deep Dive — NVIDIA"},
    {"cmd": "BTC CORR",      "desc": "Correlations — Bitcoin vs assets"},
    {"cmd": "SPX HEAT",      "desc": "Market heatmap"},
    {"cmd": "AAPL NEWS",     "desc": "News — Apple"},
    {"cmd": "AAPL OPT",      "desc": "Options flow — Apple"},
    {"cmd": "FED CAL",       "desc": "Economic calendar"},
    {"cmd": "SIGNALS",       "desc": "Market signal scanner"},
    {"cmd": "CORRELATIONS",  "desc": "Cross-asset correlations"},
    {"cmd": "INTELLIGENCE",  "desc": "Smart Money panel"},
    {"cmd": "QUANTLAB",      "desc": "Quant Lab backtester"},
    {"cmd": "PORTFOLIO",     "desc": "Portfolio overview"},
    {"cmd": "MARKET",        "desc": "Market monitor"},
    {"cmd": "RSI SCAN",      "desc": "Scan for RSI signals"},
    {"cmd": "MACD SCAN",     "desc": "Scan for MACD crossovers"},
]


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

class ParsedCommand:
    """Result of parsing a command palette string."""

    def __init__(
        self,
        tab: str,
        ticker: Optional[str] = None,
        raw: str = "",
        action: Optional[str] = None,
    ) -> None:
        self.tab = tab          # destination tab value (e.g. "deepdive")
        self.ticker = ticker    # resolved ticker symbol if extracted
        self.raw = raw          # original input string
        self.action = action    # sub-action hint (e.g. "options", "news")

    def __repr__(self) -> str:  # pragma: no cover
        return f"ParsedCommand(tab={self.tab!r}, ticker={self.ticker!r}, action={self.action!r})"


def parse(raw: str) -> Optional[ParsedCommand]:
    """
    Parse a Bloomberg-style command string and return a ParsedCommand.

    Returns None if the input is empty or unrecognisable.

    Examples
    --------
    >>> parse("AAPL DD")
    ParsedCommand(tab='deepdive', ticker='AAPL', action=None)
    >>> parse("BTC CORR")
    ParsedCommand(tab='correlations', ticker='BTC-USD', action=None)
    >>> parse("SPX HEAT")
    ParsedCommand(tab='market', ticker='^GSPC', action=None)
    """
    if not raw:
        return None

    tokens = raw.strip().upper().split()
    if not tokens:
        return None

    ticker: Optional[str] = None
    tab: Optional[str] = None
    action: Optional[str] = None

    # ── Extract ticker and command tokens ─────────────────────────────────────

    command_tokens: List[str] = []
    ticker_tokens:  List[str] = []

    for tok in tokens:
        # Check against command map first so "SIGNALS" doesn't look like a ticker
        if tok in _COMMAND_ROUTES or tok in _TAB_DIRECT:
            command_tokens.append(tok)
        elif tok in _TICKER_ALIASES:
            ticker_tokens.append(_TICKER_ALIASES[tok])
        elif _TICKER_RE.match(tok):
            ticker_tokens.append(tok)
        else:
            # Could be a partial ticker or unknown command — treat as command
            command_tokens.append(tok)

    # Resolve ticker (first one wins)
    if ticker_tokens:
        ticker = ticker_tokens[0]

    # Resolve tab from command tokens
    for tok in command_tokens:
        resolved = _COMMAND_ROUTES.get(tok) or _TAB_DIRECT.get(tok)
        if resolved:
            tab = resolved
            action = _map_action(tok)
            break

    # If no command found, default to deepdive when a ticker is present
    if tab is None and ticker:
        tab = "deepdive"

    # If only a tab keyword with no ticker
    if tab is None and command_tokens:
        tok = command_tokens[0]
        tab = _COMMAND_ROUTES.get(tok) or _TAB_DIRECT.get(tok)

    if tab is None:
        return None

    return ParsedCommand(tab=tab, ticker=ticker, raw=raw, action=action)


def _map_action(cmd_token: str) -> Optional[str]:
    """Return a sub-action hint for certain command keywords."""
    mapping: Dict[str, str] = {
        "OPT":     "options",
        "OPTIONS": "options",
        "NEWS":    "news",
        "NWS":     "news",
        "CORR":    "correlation",
    }
    return mapping.get(cmd_token)


def fuzzy_search(query: str, corpus: Optional[List[Dict[str, str]]] = None) -> List[Dict[str, str]]:
    """
    Filter the suggestion corpus by a fuzzy substring match on the cmd and desc fields.

    Parameters
    ----------
    query : str
        User's current input.
    corpus : list, optional
        List of ``{"cmd": ..., "desc": ...}`` dicts.  Defaults to SUGGESTIONS.

    Returns
    -------
    Filtered and scored list of matching suggestions (up to 8).
    """
    if corpus is None:
        corpus = SUGGESTIONS

    if not query:
        return corpus[:8]

    q = query.strip().upper()
    scored: List[Tuple[int, Dict[str, str]]] = []

    for item in corpus:
        cmd  = item["cmd"].upper()
        desc = item["desc"].upper()
        score = 0

        if cmd.startswith(q):
            score = 100
        elif q in cmd:
            score = 80
        elif q in desc:
            score = 60
        elif all(c in cmd for c in q.split()):
            score = 40

        if score:
            scored.append((score, item))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [item for _, item in scored[:8]]
