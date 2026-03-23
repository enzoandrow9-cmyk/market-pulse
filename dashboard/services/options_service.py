# ─────────────────────────────────────────────────────────────────────────────
# services/options_service.py  —  Bloomberg Terminal Dashboard  •  Market Pulse
#
# Wraps yfinance options data into a clean, cached interface.
# ─────────────────────────────────────────────────────────────────────────────

from __future__ import annotations

import logging
from typing import Dict, List, Optional

import pandas as pd
import yfinance as yf
from cachetools import TTLCache

logger = logging.getLogger(__name__)

_options_cache: TTLCache = TTLCache(maxsize=50, ttl=120)   # 2-min cache


def get_options_chain(symbol: str) -> Optional[Dict]:
    """
    Fetch the nearest-expiry options chain for *symbol*.

    Returns
    -------
    dict:
        calls         — DataFrame (strike, volume, openInterest, impliedVolatility)
        puts          — DataFrame
        expiry        — str  (date string of selected expiry)
        call_oi       — int  (total call open interest)
        put_oi        — int  (total put open interest)
        put_call_ratio — float
        unusual       — list of unusual activity dicts
    """
    if symbol in _options_cache:
        return _options_cache[symbol]

    try:
        tk      = yf.Ticker(symbol)
        expiries = tk.options
        if not expiries:
            return None

        expiry = expiries[0]
        chain  = tk.option_chain(expiry)
        calls  = chain.calls[["strike", "volume", "openInterest", "impliedVolatility"]].copy()
        puts   = chain.puts [["strike", "volume", "openInterest", "impliedVolatility"]].copy()

        call_oi = int(calls["openInterest"].sum())
        put_oi  = int(puts ["openInterest"].sum())
        pc_ratio = put_oi / call_oi if call_oi > 0 else float("inf")

        # Detect unusual activity: OI > 2× average and high volume
        avg_call_oi = calls["openInterest"].mean()
        avg_put_oi  = puts ["openInterest"].mean()

        unusual: List[Dict] = []
        for _, row in calls.iterrows():
            if row["openInterest"] > avg_call_oi * 2 and row["volume"] > 500:
                unusual.append({"type": "CALL", "strike": row["strike"],
                                 "oi": row["openInterest"], "volume": row["volume"]})
        for _, row in puts.iterrows():
            if row["openInterest"] > avg_put_oi * 2 and row["volume"] > 500:
                unusual.append({"type": "PUT", "strike": row["strike"],
                                 "oi": row["openInterest"], "volume": row["volume"]})

        result = {
            "calls":          calls,
            "puts":           puts,
            "expiry":         expiry,
            "call_oi":        call_oi,
            "put_oi":         put_oi,
            "put_call_ratio": round(pc_ratio, 3),
            "unusual":        unusual[:5],
        }
        _options_cache[symbol] = result
        return result
    except Exception as exc:
        logger.debug("options_service: fetch failed %s — %s", symbol, exc)
        return None


def get_iv_rank(symbol: str) -> Optional[float]:
    """
    Estimate IV rank (0–100) by comparing current 30-day IV to the
    52-week range of IV estimates from daily option chain snapshots.

    This is an approximation — true IV rank requires a historical IV series.
    Uses the current ATM implied vol vs the 52-week high/low of historical vol
    estimated from daily returns.

    Returns float in [0, 100] or None on failure.
    """
    try:
        df = yf.Ticker(symbol).history(period="1y", interval="1d", auto_adjust=True)
        if df is None or len(df) < 30:
            return None
        returns     = df["Close"].pct_change().dropna()
        hist_vol    = returns.rolling(30).std() * (252 ** 0.5) * 100
        current_hv  = float(hist_vol.iloc[-1])
        hv_min      = float(hist_vol.min())
        hv_max      = float(hist_vol.max())
        if hv_max <= hv_min:
            return 50.0
        iv_rank = (current_hv - hv_min) / (hv_max - hv_min) * 100
        return round(iv_rank, 1)
    except Exception:
        return None
