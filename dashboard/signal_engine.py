# ─────────────────────────────────────────────────────────────────────────────
# signal_engine.py  —  Bloomberg Terminal Dashboard  •  Enzo Market Pulse
#
# Market signal scanner — scans a universe of tickers for technical signals.
#
# Signals detected:
#   • RSI oversold  (< 30)
#   • RSI overbought (> 70)
#   • MACD bullish crossover (MACD crosses above Signal)
#   • MACD bearish crossover (MACD crosses below Signal)
#   • 20-day price breakout (close > 20-day high)
#   • 50-day price breakout (close > 50-day high)
#   • Unusual volume (current vol > 2× 20-day avg)
#   • Strong relative strength vs SPY (1-month rs > 1.05)
#
# Architecture:
#   - Background thread runs every 5 minutes (SCAN_INTERVAL_SECONDS)
#   - Results stored in module-level _scan_results dict
#   - Dash callback polls _scan_results via dcc.Interval — never blocks the UI
#   - scan_universe() is the public entry point called by the background thread
# ─────────────────────────────────────────────────────────────────────────────

from __future__ import annotations

import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
import yfinance as yf
from cachetools import TTLCache

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Scan interval
# ─────────────────────────────────────────────────────────────────────────────

SCAN_INTERVAL_SECONDS = 300   # 5 minutes

# ─────────────────────────────────────────────────────────────────────────────
# Default universe — top S&P 500 + NASDAQ 100 names
# Extended with crypto proxies and popular growth names
# ─────────────────────────────────────────────────────────────────────────────

SP500_UNIVERSE: List[str] = [
    "AAPL", "MSFT", "NVDA", "AMZN", "META", "GOOGL", "TSLA", "AVGO",
    "UNH",  "JPM",  "V",    "XOM",  "LLY",  "MA",    "JNJ",  "PG",
    "HD",   "ABBV", "MRK",  "COST", "CVX",  "ORCL",  "CRM",  "BAC",
    "AMD",  "NFLX", "ADBE", "TMO",  "CSCO", "ABT",   "PFE",  "MCD",
    "ACN",  "DHR",  "VZ",   "QCOM", "RTX",  "T",     "INTU", "WFC",
    "NEE",  "UNP",  "PM",   "HON",  "IBM",  "CAT",   "SPGI", "GE",
    "LOW",  "AMAT", "SBUX", "TXN",  "BA",   "SCHW",  "ELV",  "MS",
    "BLK",  "AXP",  "GS",   "ISRG", "NOW",  "BMY",   "GILD", "AMGN",
    "DE",   "SYK",  "CB",   "REGN", "LMT",  "LRCX",  "ADI",  "PANW",
    "KLAC", "MU",   "PYPL", "SQ",   "PLTR", "SOFI",  "COIN", "MSTR",
]

NASDAQ100_EXTRA: List[str] = [
    "ASML", "MELI", "CDNS", "SNPS", "MRVL", "CRWD", "DDOG", "ZS",
    "TEAM", "WDAY", "TTD",  "SGEN", "IDXX", "ILMN", "BIIB",
]

FULL_UNIVERSE: List[str] = list(dict.fromkeys(SP500_UNIVERSE + NASDAQ100_EXTRA))

# ─────────────────────────────────────────────────────────────────────────────
# Cache
# ─────────────────────────────────────────────────────────────────────────────

_price_cache: TTLCache = TTLCache(maxsize=200, ttl=360)   # 6 min raw price cache

# ─────────────────────────────────────────────────────────────────────────────
# Module-level scan state — updated by background thread
# ─────────────────────────────────────────────────────────────────────────────

_scan_results: Dict[str, list] = {
    "rsi_oversold":    [],
    "rsi_overbought":  [],
    "macd_bullish":    [],
    "macd_bearish":    [],
    "breakout_20":     [],
    "breakout_50":     [],
    "unusual_volume":  [],
    "strong_rs":       [],
    "last_scan":       [],   # single-element list: ISO timestamp string
}

_scan_lock     = threading.Lock()
_scan_running  = threading.Event()   # set while a scan is in progress
_scan_thread: Optional[threading.Thread] = None


# ─────────────────────────────────────────────────────────────────────────────
# Data fetch helpers
# ─────────────────────────────────────────────────────────────────────────────

def _fetch_ticker_data(symbol: str) -> Optional[pd.DataFrame]:
    """
    Fetch 3-month daily OHLCV for *symbol*.
    Result cached for 6 minutes to avoid hammering yfinance during a full scan.
    """
    if symbol in _price_cache:
        return _price_cache[symbol]

    try:
        df = yf.Ticker(symbol).history(period="3mo", interval="1d", auto_adjust=True)
        if df is None or len(df) < 20:
            return None
        df.index = pd.to_datetime(df.index).tz_localize(None)
        _price_cache[symbol] = df
        return df
    except Exception as exc:
        logger.debug("signal_engine: fetch failed for %s — %s", symbol, exc)
        return None


def _fetch_spy_data() -> Optional[pd.DataFrame]:
    """Fetch SPY for relative-strength calculation."""
    return _fetch_ticker_data("SPY")


# ─────────────────────────────────────────────────────────────────────────────
# Signal computation helpers
# ─────────────────────────────────────────────────────────────────────────────

def _calc_rsi(close: pd.Series, period: int = 14) -> float:
    """Return the most-recent RSI value (0–100) using Wilder's smoothing."""
    if len(close) < period + 1:
        return float("nan")
    delta = close.diff()
    gain  = delta.clip(lower=0).ewm(alpha=1 / period, adjust=False).mean()
    loss  = (-delta.clip(upper=0)).ewm(alpha=1 / period, adjust=False).mean()
    rs    = gain / loss.replace(0, np.nan)
    rsi   = 100 - (100 / (1 + rs))
    return float(rsi.iloc[-1])


def _calc_macd(close: pd.Series) -> tuple:
    """
    Return (macd, signal, prev_macd, prev_signal) for crossover detection.
    Uses 12/26/9 standard parameters.
    """
    if len(close) < 35:
        return None, None, None, None
    ema12  = close.ewm(span=12, adjust=False).mean()
    ema26  = close.ewm(span=26, adjust=False).mean()
    macd   = ema12 - ema26
    signal = macd.ewm(span=9, adjust=False).mean()
    return (
        float(macd.iloc[-1]),
        float(signal.iloc[-1]),
        float(macd.iloc[-2]),
        float(signal.iloc[-2]),
    )


def _analyse_ticker(symbol: str, spy_return_1m: float) -> Optional[Dict]:
    """
    Run all signal checks on *symbol* and return a signal dict or None.

    Returns
    -------
    dict with keys: symbol, price, chg_pct, rsi, volume_ratio,
                    signals (list of signal-type strings)
    """
    df = _fetch_ticker_data(symbol)
    if df is None or len(df) < 21:
        return None

    close  = df["Close"]
    volume = df["Volume"] if "Volume" in df.columns else None

    price   = float(close.iloc[-1])
    chg_pct = float((close.iloc[-1] - close.iloc[-2]) / close.iloc[-2] * 100) if len(close) >= 2 else 0.0

    # RSI
    rsi = _calc_rsi(close)

    # MACD
    macd, sig, prev_macd, prev_sig = _calc_macd(close)

    # Breakouts
    high_20 = float(close.iloc[-21:-1].max()) if len(close) >= 21 else None
    high_50 = float(close.iloc[-51:-1].max()) if len(close) >= 51 else None

    # Volume ratio
    vol_ratio = 1.0
    if volume is not None and len(volume) >= 21:
        avg_vol  = float(volume.iloc[-21:-1].mean())
        curr_vol = float(volume.iloc[-1])
        vol_ratio = curr_vol / avg_vol if avg_vol > 0 else 1.0

    # Relative strength vs SPY (1-month return comparison)
    ticker_return_1m = float((close.iloc[-1] - close.iloc[-22]) / close.iloc[-22]) if len(close) >= 22 else 0.0
    rs_ratio = (1 + ticker_return_1m) / (1 + spy_return_1m) if spy_return_1m != -1 else 1.0

    signals: List[str] = []

    if not np.isnan(rsi):
        if rsi < 30:
            signals.append("rsi_oversold")
        if rsi > 70:
            signals.append("rsi_overbought")

    if macd is not None and sig is not None and prev_macd is not None and prev_sig is not None:
        if prev_macd < prev_sig and macd > sig:
            signals.append("macd_bullish")
        if prev_macd > prev_sig and macd < sig:
            signals.append("macd_bearish")

    if high_20 is not None and price > high_20:
        signals.append("breakout_20")
    if high_50 is not None and price > high_50:
        signals.append("breakout_50")

    if vol_ratio >= 2.0:
        signals.append("unusual_volume")

    if rs_ratio >= 1.05:
        signals.append("strong_rs")

    if not signals:
        return None

    return {
        "symbol":      symbol,
        "price":       price,
        "chg_pct":     chg_pct,
        "rsi":         rsi if not np.isnan(rsi) else None,
        "vol_ratio":   vol_ratio,
        "rs_ratio":    rs_ratio,
        "signals":     signals,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Main scan function
# ─────────────────────────────────────────────────────────────────────────────

def scan_universe(extra_tickers: Optional[List[str]] = None) -> Dict[str, list]:
    """
    Scan the full universe for technical signals.

    Parameters
    ----------
    extra_tickers : list, optional
        Additional tickers (e.g. user portfolio) merged into the scan universe.

    Returns
    -------
    Dict mapping signal category → sorted list of result dicts.
    Cached result also stored in module-level _scan_results.
    """
    universe = list(FULL_UNIVERSE)
    if extra_tickers:
        for t in extra_tickers:
            if t not in universe:
                universe.append(t)

    # Fetch SPY return for RS calculation
    spy_df = _fetch_spy_data()
    spy_return_1m = 0.0
    if spy_df is not None and len(spy_df) >= 22:
        spy_return_1m = float(
            (spy_df["Close"].iloc[-1] - spy_df["Close"].iloc[-22]) / spy_df["Close"].iloc[-22]
        )

    results: List[Dict] = []
    max_workers = min(len(universe), 20)

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(_analyse_ticker, sym, spy_return_1m): sym for sym in universe}
        for fut in as_completed(futures):
            try:
                r = fut.result()
                if r:
                    results.append(r)
            except Exception as exc:
                logger.debug("signal_engine: analysis error — %s", exc)

    # Bucket results into signal categories
    buckets: Dict[str, list] = {
        "rsi_oversold":   [],
        "rsi_overbought": [],
        "macd_bullish":   [],
        "macd_bearish":   [],
        "breakout_20":    [],
        "breakout_50":    [],
        "unusual_volume": [],
        "strong_rs":      [],
    }

    for r in results:
        for sig in r["signals"]:
            if sig in buckets:
                buckets[sig].append(r)

    # Sort each bucket by magnitude (most extreme first)
    _sort_key_map: Dict[str, str] = {
        "rsi_oversold":   "rsi",          # lowest RSI first
        "rsi_overbought": "rsi",          # highest RSI first
        "macd_bullish":   "chg_pct",
        "macd_bearish":   "chg_pct",
        "breakout_20":    "chg_pct",
        "breakout_50":    "chg_pct",
        "unusual_volume": "vol_ratio",
        "strong_rs":      "rs_ratio",
    }

    _sort_reverse_map: Dict[str, bool] = {
        "rsi_oversold":   False,  # ascending — lowest RSI = most oversold
        "rsi_overbought": True,
        "macd_bullish":   True,
        "macd_bearish":   False,
        "breakout_20":    True,
        "breakout_50":    True,
        "unusual_volume": True,
        "strong_rs":      True,
    }

    for key, items in buckets.items():
        sort_field = _sort_key_map.get(key, "chg_pct")
        reverse    = _sort_reverse_map.get(key, True)
        items.sort(
            key=lambda x: x.get(sort_field) if x.get(sort_field) is not None else 0.0,
            reverse=reverse,
        )
        buckets[key] = items[:10]   # cap at top-10 per category

    import datetime
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    buckets["last_scan"] = [ts]  # type: ignore[assignment]

    with _scan_lock:
        _scan_results.update(buckets)

    logger.info("signal_engine: scan complete — %d signals found across %d tickers",
                sum(len(v) for k, v in buckets.items() if k != "last_scan"),
                len(results))

    return buckets


# ─────────────────────────────────────────────────────────────────────────────
# Public accessor — read cached results without triggering a scan
# ─────────────────────────────────────────────────────────────────────────────

def get_scan_results() -> Dict[str, list]:
    """Return the latest cached scan results (thread-safe read)."""
    with _scan_lock:
        return dict(_scan_results)


def get_last_scan_time() -> Optional[str]:
    """Return the ISO timestamp of the last completed scan, or None."""
    with _scan_lock:
        ts_list = _scan_results.get("last_scan", [])
        return ts_list[0] if ts_list else None


def is_scan_running() -> bool:
    """Return True if a background scan is currently in progress."""
    return _scan_running.is_set()


# ─────────────────────────────────────────────────────────────────────────────
# Background worker thread
# ─────────────────────────────────────────────────────────────────────────────

def _worker_loop(extra_tickers: Optional[List[str]] = None) -> None:
    """Background loop: scan every SCAN_INTERVAL_SECONDS."""
    while True:
        try:
            _scan_running.set()
            scan_universe(extra_tickers)
        except Exception as exc:
            logger.exception("signal_engine: scan loop error — %s", exc)
        finally:
            _scan_running.clear()
        time.sleep(SCAN_INTERVAL_SECONDS)


def start_background_scanner(extra_tickers: Optional[List[str]] = None) -> None:
    """
    Start the background signal scanner daemon thread (idempotent — safe to call
    multiple times; the thread is only created once).

    Parameters
    ----------
    extra_tickers : list, optional
        Portfolio or watchlist tickers merged into every scan run.
    """
    global _scan_thread
    if _scan_thread is not None and _scan_thread.is_alive():
        return   # already running

    _scan_thread = threading.Thread(
        target=_worker_loop,
        args=(extra_tickers,),
        daemon=True,
        name="signal-scanner",
    )
    _scan_thread.start()
    logger.info("signal_engine: background scanner started (interval=%ds)", SCAN_INTERVAL_SECONDS)
