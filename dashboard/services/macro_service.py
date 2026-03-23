# ─────────────────────────────────────────────────────────────────────────────
# services/macro_service.py  —  Bloomberg Terminal Dashboard  •  Market Pulse
#
# Macro intelligence data layer.
#
# Data sources:
#   • FRED (St. Louis Fed) — free CSV endpoint (no API key required for most series)
#   • US Treasury — public JSON API for yield curve data
#   • yfinance — supplementary market proxies
#
# Series fetched:
#   T10Y2Y   — 10Y-2Y yield spread (yield curve inversion indicator)
#   T10YIE   — 10Y breakeven inflation expectations
#   BAMLH0A0HYM2 — ICE HY corporate credit spread (OAS)
#   WALCL    — Fed balance sheet (total assets, weekly)
#   FEDFUNDS — Effective federal funds rate
#   DGS10    — 10-year Treasury constant maturity yield
#   DGS2     — 2-year Treasury
#   DGS30    — 30-year Treasury
#   DGS3MO   — 3-month Treasury
# ─────────────────────────────────────────────────────────────────────────────

from __future__ import annotations

import logging
from typing import Dict, List, Optional

import pandas as pd
import requests
import yfinance as yf
from cachetools import TTLCache

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Cache — macro data changes slowly; 30-min TTL is fine
# ─────────────────────────────────────────────────────────────────────────────

_macro_cache: TTLCache = TTLCache(maxsize=30, ttl=1800)   # 30-min cache

_FRED_CSV_BASE = "https://fred.stlouisfed.org/graph/fredgraph.csv"

# ─────────────────────────────────────────────────────────────────────────────
# FRED helpers
# ─────────────────────────────────────────────────────────────────────────────

def _fetch_fred_series(series_id: str, limit_rows: int = 252) -> Optional[pd.Series]:
    """
    Fetch a FRED series via the public CSV endpoint (no API key required).

    Returns a pd.Series indexed by date, or None on failure.
    Data is cached for 30 minutes.
    """
    cache_key = f"fred_{series_id}"
    if cache_key in _macro_cache:
        return _macro_cache[cache_key]

    try:
        url  = f"{_FRED_CSV_BASE}?id={series_id}"
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        df   = pd.read_csv(pd.io.common.StringIO(resp.text), index_col=0, parse_dates=True)
        df.columns = [series_id]
        df[series_id] = pd.to_numeric(df[series_id], errors="coerce")
        df   = df.dropna()
        if df.empty:
            return None
        s = df[series_id].iloc[-limit_rows:]
        _macro_cache[cache_key] = s
        return s
    except Exception as exc:
        logger.debug("macro_service: FRED fetch failed %s — %s", series_id, exc)
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Yield curve
# ─────────────────────────────────────────────────────────────────────────────

_YIELD_SERIES: Dict[str, str] = {
    "3M":  "DGS3MO",
    "2Y":  "DGS2",
    "5Y":  "DGS5",
    "10Y": "DGS10",
    "30Y": "DGS30",
}


def get_yield_curve() -> Optional[Dict]:
    """
    Return current yield curve snapshot and historical 10Y-2Y spread.

    Returns
    -------
    dict:
        points     — list of {tenor, yield} for the current yield curve
        spread_10_2 — pd.Series of historical 10Y-2Y spread
        spread_now — float (current spread value)
        inverted   — bool
    """
    cache_key = "yield_curve"
    if cache_key in _macro_cache:
        return _macro_cache[cache_key]

    points = []
    latest_yields: Dict[str, float] = {}

    for tenor, fred_id in _YIELD_SERIES.items():
        s = _fetch_fred_series(fred_id, limit_rows=252)
        if s is not None and not s.empty:
            val = float(s.iloc[-1])
            points.append({"tenor": tenor, "yield": val})
            latest_yields[tenor] = val

    if not points:
        return None

    spread_series = _fetch_fred_series("T10Y2Y", limit_rows=252)
    spread_now    = float(spread_series.iloc[-1]) if spread_series is not None else None

    result = {
        "points":      points,
        "spread_10_2": spread_series,
        "spread_now":  spread_now,
        "inverted":    spread_now < 0 if spread_now is not None else False,
    }
    _macro_cache[cache_key] = result
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Inflation expectations
# ─────────────────────────────────────────────────────────────────────────────

def get_inflation_expectations() -> Optional[pd.Series]:
    """
    Return the 10-year breakeven inflation rate series (FRED T10YIE).
    Proxy for market-implied inflation expectations.
    """
    return _fetch_fred_series("T10YIE", limit_rows=252)


# ─────────────────────────────────────────────────────────────────────────────
# Credit spreads
# ─────────────────────────────────────────────────────────────────────────────

def get_credit_spreads() -> Optional[Dict]:
    """
    Return high-yield and investment-grade credit spread series.

    Returns
    -------
    dict:
        hy_spread  — pd.Series (ICE BofA HY OAS, FRED BAMLH0A0HYM2)
        hy_now     — float (latest value in bps)
    """
    cache_key = "credit_spreads"
    if cache_key in _macro_cache:
        return _macro_cache[cache_key]

    hy = _fetch_fred_series("BAMLH0A0HYM2", limit_rows=252)
    if hy is None:
        return None

    result = {
        "hy_spread": hy,
        "hy_now":    float(hy.iloc[-1]),
    }
    _macro_cache[cache_key] = result
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Fed balance sheet
# ─────────────────────────────────────────────────────────────────────────────

def get_fed_balance_sheet() -> Optional[pd.Series]:
    """
    Return the Federal Reserve total assets series (FRED WALCL).
    Weekly data, in millions of USD. Convert to trillions for display.
    """
    s = _fetch_fred_series("WALCL", limit_rows=156)   # ~3 years of weekly data
    if s is None:
        return None
    return s / 1_000_000   # millions → trillions


# ─────────────────────────────────────────────────────────────────────────────
# Dollar liquidity proxy
# ─────────────────────────────────────────────────────────────────────────────

def get_dollar_liquidity() -> Optional[Dict]:
    """
    Dollar liquidity = Fed Balance Sheet − Treasury General Account (TGA) − Reverse Repo (RRPONTSYD).
    Approximation: uses Fed total assets as a proxy when TGA data is unavailable.

    Returns dict with 'series' (pd.Series) and 'current' (float, trillions).
    """
    cache_key = "dollar_liquidity"
    if cache_key in _macro_cache:
        return _macro_cache[cache_key]

    walcl  = _fetch_fred_series("WALCL",    limit_rows=156)
    rrp    = _fetch_fred_series("RRPONTSYD",limit_rows=156)

    if walcl is None:
        return None

    # Convert to trillions
    walcl_t = walcl / 1_000_000

    if rrp is not None:
        rrp_t = rrp / 1_000   # billions → trillions
        # Align on common dates
        combined = pd.concat([walcl_t, rrp_t], axis=1).ffill().dropna()
        combined.columns = ["walcl", "rrp"]
        liquidity = combined["walcl"] - combined["rrp"]
    else:
        liquidity = walcl_t

    result = {
        "series":  liquidity,
        "current": float(liquidity.iloc[-1]) if not liquidity.empty else None,
    }
    _macro_cache[cache_key] = result
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Macro summary — single call for the Intelligence tab macro panel
# ─────────────────────────────────────────────────────────────────────────────

def get_macro_summary() -> Dict:
    """
    Fetch all macro data series in one call.

    Returns
    -------
    dict with keys: yield_curve, inflation, credit, fed_bs, liquidity
    Each value is the result of the individual getter (may be None on failure).
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    tasks = {
        "yield_curve": get_yield_curve,
        "inflation":   get_inflation_expectations,
        "credit":      get_credit_spreads,
        "fed_bs":      get_fed_balance_sheet,
        "liquidity":   get_dollar_liquidity,
    }

    results: Dict = {}
    with ThreadPoolExecutor(max_workers=5) as pool:
        futs = {pool.submit(fn): key for key, fn in tasks.items()}
        for fut in as_completed(futs):
            key = futs[fut]
            try:
                results[key] = fut.result()
            except Exception as exc:
                logger.debug("macro_service: %s failed — %s", key, exc)
                results[key] = None

    return results
