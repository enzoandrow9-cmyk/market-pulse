# ─────────────────────────────────────────────────────────────────────────────
# services/market_data_service.py  —  Bloomberg Terminal Dashboard  •  Market Pulse
#
# Wraps yfinance for all market price / OHLCV data needs.
# Provides a single, cached, error-resilient interface used by Dash callbacks.
# ─────────────────────────────────────────────────────────────────────────────

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Tuple

import pandas as pd
import yfinance as yf
from cachetools import TTLCache

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Caches
# ─────────────────────────────────────────────────────────────────────────────

_ohlcv_cache:  TTLCache = TTLCache(maxsize=200, ttl=300)   # 5-min OHLCV cache
_quote_cache:  TTLCache = TTLCache(maxsize=200, ttl=60)    # 1-min quote cache
_info_cache:   TTLCache = TTLCache(maxsize=200, ttl=3600)  # 1-hour info cache


# ─────────────────────────────────────────────────────────────────────────────
# OHLCV data
# ─────────────────────────────────────────────────────────────────────────────

def get_ohlcv(
    symbol: str,
    period: str = "6mo",
    interval: str = "1d",
) -> Optional[pd.DataFrame]:
    """
    Fetch adjusted OHLCV data for *symbol*.

    Parameters
    ----------
    symbol   : Ticker symbol.
    period   : yfinance period string ('1d', '5d', '1mo', '3mo', '6mo', '1y', '2y').
    interval : Bar interval ('1m', '5m', '30m', '1h', '1d', '1wk').

    Returns
    -------
    DataFrame with columns [Open, High, Low, Close, Volume] indexed by datetime,
    or None on failure.
    """
    cache_key = f"{symbol}_{period}_{interval}"
    if cache_key in _ohlcv_cache:
        return _ohlcv_cache[cache_key]

    try:
        df = yf.Ticker(symbol).history(period=period, interval=interval, auto_adjust=True)
        if df is None or df.empty:
            return None
        df.index = pd.to_datetime(df.index).tz_localize(None)
        result = df[["Open", "High", "Low", "Close", "Volume"]].copy()
        _ohlcv_cache[cache_key] = result
        return result
    except Exception as exc:
        logger.debug("market_data_service: OHLCV fetch failed %s — %s", symbol, exc)
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Real-time quote (latest price + change)
# ─────────────────────────────────────────────────────────────────────────────

def get_quote(symbol: str) -> Optional[Dict]:
    """
    Return the latest quote for *symbol*.

    Returns
    -------
    dict: {symbol, price, prev_close, chg, chg_pct, volume, market_cap}
    """
    if symbol in _quote_cache:
        return _quote_cache[symbol]

    try:
        tk = yf.Ticker(symbol)
        df = tk.history(period="5d", interval="1d", auto_adjust=True)
        if df is None or len(df) < 2:
            return None

        price     = float(df["Close"].iloc[-1])
        prev      = float(df["Close"].iloc[-2])
        chg       = price - prev
        chg_pct   = chg / prev * 100 if prev else 0.0
        volume    = int(df["Volume"].iloc[-1]) if "Volume" in df.columns else 0

        result = {
            "symbol":     symbol,
            "price":      price,
            "prev_close": prev,
            "chg":        chg,
            "chg_pct":    chg_pct,
            "volume":     volume,
        }
        _quote_cache[symbol] = result
        return result
    except Exception as exc:
        logger.debug("market_data_service: quote failed %s — %s", symbol, exc)
        return None


def get_quotes_batch(symbols: List[str]) -> Dict[str, Dict]:
    """
    Fetch quotes for multiple symbols (checks cache first, fetches misses together).

    Returns
    -------
    dict: {symbol → quote_dict}
    """
    results: Dict[str, Dict] = {}
    missing = []
    for sym in symbols:
        if sym in _quote_cache:
            results[sym] = _quote_cache[sym]
        else:
            missing.append(sym)

    if not missing:
        return results

    # Batch download for cache misses
    try:
        raw = yf.download(
            missing, period="5d", interval="1d",
            auto_adjust=True, progress=False, threads=True,
        )
        if not raw.empty:
            for sym in missing:
                try:
                    if len(missing) == 1:
                        closes = raw["Close"].dropna()
                        vols   = raw["Volume"].dropna() if "Volume" in raw else None
                    else:
                        closes = raw["Close"][sym].dropna() if ("Close", sym) in raw.columns else None
                        vols   = raw["Volume"][sym].dropna() if ("Volume", sym) in raw.columns else None

                    if closes is None or len(closes) < 2:
                        continue

                    price   = float(closes.iloc[-1])
                    prev    = float(closes.iloc[-2])
                    chg     = price - prev
                    chg_pct = chg / prev * 100 if prev else 0.0
                    volume  = int(vols.iloc[-1]) if vols is not None and len(vols) else 0

                    q = {"symbol": sym, "price": price, "prev_close": prev,
                         "chg": chg, "chg_pct": chg_pct, "volume": volume}
                    _quote_cache[sym] = q
                    results[sym] = q
                except Exception:
                    pass
    except Exception as exc:
        logger.debug("market_data_service: batch quote failed — %s", exc)

    return results


# ─────────────────────────────────────────────────────────────────────────────
# Ticker metadata
# ─────────────────────────────────────────────────────────────────────────────

def get_ticker_info(symbol: str) -> Optional[Dict]:
    """
    Return yfinance .info dict for *symbol*, cached 1 hour.
    Returns None on failure.
    """
    if symbol in _info_cache:
        return _info_cache[symbol]
    try:
        info = yf.Ticker(symbol).info
        if info:
            _info_cache[symbol] = info
            return info
    except Exception as exc:
        logger.debug("market_data_service: info failed %s — %s", symbol, exc)
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Multi-asset return series (for correlation / comparison charts)
# ─────────────────────────────────────────────────────────────────────────────

def get_return_series(
    symbols: List[str],
    period: str = "1y",
    normalise: bool = True,
) -> Optional[pd.DataFrame]:
    """
    Fetch aligned close prices and return a DataFrame of cumulative returns.

    Parameters
    ----------
    symbols   : List of ticker symbols.
    period    : yfinance period string.
    normalise : If True, returns are normalised to 1.0 at the start (rebased).

    Returns
    -------
    DataFrame with datetime index and symbols as columns (returns / rebased prices),
    or None on failure.
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed
    series_map: Dict[str, pd.Series] = {}

    def _fetch_one(sym: str) -> Tuple[str, Optional[pd.Series]]:
        df = get_ohlcv(sym, period=period, interval="1d")
        if df is None or df.empty:
            return sym, None
        s = df["Close"].copy()
        s.name = sym
        return sym, s

    with ThreadPoolExecutor(max_workers=min(len(symbols), 8)) as pool:
        futs = {pool.submit(_fetch_one, s): s for s in symbols}
        for fut in as_completed(futs):
            sym, s = fut.result()
            if s is not None:
                series_map[sym] = s

    if not series_map:
        return None

    df = pd.DataFrame(series_map).dropna(thresh=2)
    if normalise:
        df = df / df.iloc[0]   # rebase to 1.0 at start

    return df
