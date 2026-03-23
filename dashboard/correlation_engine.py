# ─────────────────────────────────────────────────────────────────────────────
# correlation_engine.py  —  Bloomberg Terminal Dashboard  •  Enzo Market Pulse
#
# Cross-asset correlation analysis.
#
# Produces:
#   1. Full correlation matrix (N×N) over selectable lookback window
#   2. Rolling pairwise correlation series (for any two assets)
#   3. Correlation change (30d vs 90d) to detect regime shifts
#
# Default universe: SPY, QQQ, BTC-USD, ETH-USD, GLD, DX-Y.NYB, TLT, CL=F
# Cache: 10 minutes (heavy computation, infrequent change)
# ─────────────────────────────────────────────────────────────────────────────

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import yfinance as yf
from cachetools import TTLCache

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Universe
# ─────────────────────────────────────────────────────────────────────────────

DEFAULT_ASSETS: List[Tuple[str, str]] = [
    ("SPY",       "S&P 500"),
    ("QQQ",       "NASDAQ 100"),
    ("BTC-USD",   "Bitcoin"),
    ("ETH-USD",   "Ethereum"),
    ("GLD",       "Gold"),
    ("DX-Y.NYB",  "US Dollar"),
    ("TLT",       "20Y Treasury"),
    ("CL=F",      "Crude Oil"),
]

DEFAULT_SYMBOLS: List[str] = [sym for sym, _ in DEFAULT_ASSETS]
ASSET_LABELS:   Dict[str, str] = {sym: lbl for sym, lbl in DEFAULT_ASSETS}

# ─────────────────────────────────────────────────────────────────────────────
# Caches
# ─────────────────────────────────────────────────────────────────────────────

_raw_cache:   TTLCache = TTLCache(maxsize=20, ttl=600)   # 10-min raw price cache
_corr_cache:  TTLCache = TTLCache(maxsize=10, ttl=600)   # 10-min correlation matrix cache

# ─────────────────────────────────────────────────────────────────────────────
# Data fetch
# ─────────────────────────────────────────────────────────────────────────────

def _fetch_one(symbol: str, period: str = "1y") -> Optional[pd.Series]:
    """Fetch adjusted close series for *symbol*."""
    cache_key = f"{symbol}_{period}"
    if cache_key in _raw_cache:
        return _raw_cache[cache_key]

    try:
        df = yf.Ticker(symbol).history(period=period, interval="1d", auto_adjust=True)
        if df is None or df.empty or "Close" not in df.columns:
            return None
        s = df["Close"].copy()
        s.index = pd.to_datetime(s.index).tz_localize(None)
        s.name  = symbol
        _raw_cache[cache_key] = s
        return s
    except Exception as exc:
        logger.debug("correlation_engine: fetch failed %s — %s", symbol, exc)
        return None


def fetch_price_matrix(
    symbols: Optional[List[str]] = None,
    period: str = "1y",
) -> pd.DataFrame:
    """
    Fetch and align daily close prices for all *symbols*.

    Returns a DataFrame with dates as index and symbols as columns.
    Only rows with at least 2 non-null values are kept.
    """
    if symbols is None:
        symbols = DEFAULT_SYMBOLS

    series_map: Dict[str, pd.Series] = {}
    with ThreadPoolExecutor(max_workers=min(len(symbols), 8)) as pool:
        futures = {pool.submit(_fetch_one, sym, period): sym for sym in symbols}
        for fut in as_completed(futures):
            sym = futures[fut]
            try:
                s = fut.result()
                if s is not None:
                    series_map[sym] = s
            except Exception:
                pass

    if not series_map:
        return pd.DataFrame()

    df = pd.DataFrame(series_map)
    df = df.dropna(thresh=2)   # drop dates where all but 1 series is NaN
    return df


# ─────────────────────────────────────────────────────────────────────────────
# Correlation matrix
# ─────────────────────────────────────────────────────────────────────────────

def compute_correlation_matrix(
    symbols: Optional[List[str]] = None,
    period: str = "1y",
    method: str = "pearson",
) -> Optional[pd.DataFrame]:
    """
    Compute return-based correlation matrix for *symbols* over *period*.

    Parameters
    ----------
    symbols : list, optional
        Ticker symbols. Defaults to DEFAULT_SYMBOLS.
    period : str
        yfinance period string ('3mo', '6mo', '1y', '2y').
    method : str
        Correlation method: 'pearson' (default) or 'spearman'.

    Returns
    -------
    DataFrame with symbols as both index and columns (values in [-1, 1]).
    Cached for 10 minutes.
    """
    if symbols is None:
        symbols = DEFAULT_SYMBOLS

    cache_key = f"matrix_{','.join(sorted(symbols))}_{period}_{method}"
    if cache_key in _corr_cache:
        return _corr_cache[cache_key]

    prices = fetch_price_matrix(symbols, period)
    if prices.empty:
        return None

    returns = prices.pct_change().dropna(how="all")
    if len(returns) < 10:
        return None

    corr = returns.corr(method=method).round(3)

    # Rename columns/index to friendly labels
    friendly_cols = [ASSET_LABELS.get(c, c) for c in corr.columns]
    corr.columns  = friendly_cols
    corr.index    = friendly_cols

    _corr_cache[cache_key] = corr
    return corr


# ─────────────────────────────────────────────────────────────────────────────
# Rolling correlation between two assets
# ─────────────────────────────────────────────────────────────────────────────

def compute_rolling_correlation(
    sym_a: str,
    sym_b: str,
    window: int = 30,
    period: str = "1y",
) -> Optional[pd.DataFrame]:
    """
    Compute rolling *window*-day pairwise correlation between sym_a and sym_b.

    Returns
    -------
    DataFrame with columns ['date', 'correlation'] or None on failure.
    Cached for 10 minutes.
    """
    cache_key = f"rolling_{sym_a}_{sym_b}_{window}_{period}"
    if cache_key in _corr_cache:
        return _corr_cache[cache_key]

    prices = fetch_price_matrix([sym_a, sym_b], period)
    if prices.empty or sym_a not in prices.columns or sym_b not in prices.columns:
        return None

    returns = prices.pct_change().dropna()
    if len(returns) < window + 5:
        return None

    rolling = (
        returns[sym_a]
        .rolling(window)
        .corr(returns[sym_b])
        .dropna()
        .reset_index()
    )
    rolling.columns = ["date", "correlation"]
    rolling["correlation"] = rolling["correlation"].round(3)

    _corr_cache[cache_key] = rolling
    return rolling


# ─────────────────────────────────────────────────────────────────────────────
# Correlation regime shift detector
# ─────────────────────────────────────────────────────────────────────────────

def compute_correlation_change(
    symbols: Optional[List[str]] = None,
) -> Optional[pd.DataFrame]:
    """
    Compute how correlation has changed between the 90-day and 30-day windows.

    Returns a DataFrame of (asset_a, asset_b, corr_90d, corr_30d, delta).
    Positive delta means correlations are increasing (risk-on convergence).
    """
    if symbols is None:
        symbols = DEFAULT_SYMBOLS

    cache_key = f"change_{','.join(sorted(symbols))}"
    if cache_key in _corr_cache:
        return _corr_cache[cache_key]

    prices = fetch_price_matrix(symbols, "6mo")
    if prices.empty:
        return None

    returns = prices.pct_change().dropna(how="all")
    if len(returns) < 90:
        return None

    corr_90 = returns.iloc[-90:].corr().round(3)
    corr_30 = returns.iloc[-30:].corr().round(3)

    rows = []
    cols = [c for c in corr_90.columns if c in corr_30.columns]
    for i, a in enumerate(cols):
        for b in cols[i + 1:]:
            c90 = float(corr_90.loc[a, b])
            c30 = float(corr_30.loc[a, b])
            rows.append({
                "asset_a":  ASSET_LABELS.get(a, a),
                "asset_b":  ASSET_LABELS.get(b, b),
                "corr_90d": c90,
                "corr_30d": c30,
                "delta":    round(c30 - c90, 3),
            })

    if not rows:
        return None

    df_out = pd.DataFrame(rows).sort_values("delta", key=abs, ascending=False).reset_index(drop=True)
    _corr_cache[cache_key] = df_out
    return df_out


# ─────────────────────────────────────────────────────────────────────────────
# Add extra symbols to the universe for the current session
# ─────────────────────────────────────────────────────────────────────────────

def get_extended_universe(extra_tickers: Optional[List[str]] = None) -> List[str]:
    """
    Return DEFAULT_SYMBOLS merged with *extra_tickers* (deduped, order-preserved).
    """
    universe = list(DEFAULT_SYMBOLS)
    if extra_tickers:
        for t in extra_tickers:
            if t not in universe:
                universe.append(t)
    return universe
