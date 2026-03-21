# ─────────────────────────────────────────────────────────────────────────────
# data_manager.py  —  Bloomberg Terminal Dashboard  •  Enzo Market Pulse
# Handles all data fetching, indicator calculation, signal scoring, and caching
# ─────────────────────────────────────────────────────────────────────────────

import os
import time
import datetime
import warnings
import traceback

import numpy as np
import pandas as pd
import yfinance as yf
import requests

# Load .env file if present (keeps API keys out of source code)
def _load_env_file():
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    try:
        with open(env_path) as _f:
            for _line in _f:
                _line = _line.strip()
                if _line and not _line.startswith("#") and "=" in _line:
                    _k, _v = _line.split("=", 1)
                    os.environ.setdefault(_k.strip(), _v.strip())
    except Exception:
        pass

_load_env_file()

try:
    import ta as ta_lib
    TA_AVAILABLE = True
except ImportError:
    TA_AVAILABLE = False
    warnings.warn("'ta' library not installed — indicators will be unavailable. "
                  "Run: pip install ta")

from cachetools import TTLCache
from config import (
    PORTFOLIO_TICKERS, TICKER_NAMES, TICKER_SECTOR,
    INDICES, COMMODITIES, CRYPTO, FX, FUTURES, BONDS, SECTORS,
    PERIOD, INTERVAL, CACHE_TTL, NEWS_SOURCES,
)

# ── Cache stores ──────────────────────────────────────────────────────────────
_ticker_cache       = TTLCache(maxsize=50,  ttl=CACHE_TTL)
_market_cache       = TTLCache(maxsize=10,  ttl=CACHE_TTL)
_news_cache         = TTLCache(maxsize=50,  ttl=300)        # 5-min news cache
_briefing_cache     = TTLCache(maxsize=5,   ttl=900)        # 15-min AI briefing cache
_fundamentals_cache = TTLCache(maxsize=50,  ttl=3600)       # 1-hour fundamentals cache
_options_cache      = TTLCache(maxsize=30,  ttl=120)        # 2-min options cache (live during market hours)
_meta_cache         = TTLCache(maxsize=200, ttl=86400)      # 24-hour name/sector cache for unknown tickers
_calendar_cache     = TTLCache(maxsize=10,  ttl=1800)       # 30-min calendar cache
_sector_cache       = TTLCache(maxsize=5,   ttl=300)        # 5-min sector heatmap cache

# ── Sector → colour map for auto-detected tickers ─────────────────────────────
_SECTOR_COLORS = {
    "Technology":             "#7C3AED",
    "Information Technology": "#7C3AED",
    "Communication Services": "#0369A1",
    "Financials":             "#059669",
    "Financial Services":     "#059669",
    "Healthcare":             "#0891B2",
    "Health Care":            "#0891B2",
    "Energy":                 "#D97706",
    "Consumer Discretionary": "#DC2626",
    "Consumer Staples":       "#16A34A",
    "Industrials":            "#1D4ED8",
    "Materials":              "#B45309",
    "Real Estate":            "#7E22CE",
    "Utilities":              "#0F766E",
    "ETF":                    "#6B7280",
    "Index":                  "#6B7280",
    "Currency":               "#6B7280",
    "Cryptocurrency":         "#F59E0B",
}


def _resolve_ticker_meta(ticker: str) -> tuple:
    """
    Return (display_name, (sector_label, sector_color)) for any ticker.
    Checks the hardcoded config dicts first (instant); for unknown tickers
    falls back to yfinance .info (result cached 24 h so it only fires once).
    """
    # Fast path — already in config
    if ticker in TICKER_NAMES and ticker in TICKER_SECTOR:
        return TICKER_NAMES[ticker], TICKER_SECTOR[ticker]

    # Cached lookup from a previous call
    if ticker in _meta_cache:
        return _meta_cache[ticker]

    # Live lookup via yfinance
    name   = TICKER_NAMES.get(ticker, ticker)   # symbol as safe default
    sector = TICKER_SECTOR.get(ticker, ("Unknown", "#64748b"))

    try:
        info = yf.Ticker(ticker).info

        # Name: prefer longName → shortName → symbol
        raw_name = info.get("longName") or info.get("shortName") or ticker
        # Trim common suffixes that bloat card labels
        for suffix in (" Inc.", " Inc", " Corp.", " Corp", " Ltd.", " Ltd",
                       " plc", " PLC", " N.V.", " S.A.", " LLC"):
            if raw_name.endswith(suffix):
                raw_name = raw_name[: -len(suffix)]
                break
        name = raw_name[:28]   # cap at 28 chars so cards stay tidy

        # Sector
        raw_sector = (
            info.get("sector")
            or info.get("sectorDisp")
            or info.get("quoteType", "Unknown")
        )
        color  = _SECTOR_COLORS.get(raw_sector, "#64748b")
        sector = (raw_sector, color)

    except Exception:
        pass   # keep defaults if yfinance fails

    _meta_cache[ticker] = (name, sector)
    return name, sector

# ─────────────────────────────────────────────────────────────────────────────
# Low-level helpers
# ─────────────────────────────────────────────────────────────────────────────

def _safe_float(val, fallback=0.0):
    try:
        return float(val)
    except (TypeError, ValueError):
        return fallback


def _pct_change(curr, prev):
    if prev == 0:
        return 0.0
    return (curr - prev) / abs(prev) * 100


# ─────────────────────────────────────────────────────────────────────────────
# Indicator calculation
# ─────────────────────────────────────────────────────────────────────────────

def _add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Add technical indicators to a OHLCV DataFrame. Returns enriched df."""
    if not TA_AVAILABLE or df is None or len(df) < 30:
        return df

    close = df["Close"]
    high  = df["High"]
    low   = df["Low"]
    vol   = df["Volume"] if "Volume" in df.columns else None

    # Moving averages
    df["MA20"]  = close.rolling(20).mean()
    df["MA50"]  = close.rolling(50).mean()
    df["MA200"] = close.rolling(200).mean()

    # Bollinger Bands
    try:
        bb = ta_lib.volatility.BollingerBands(close=close, window=20, window_dev=2)
        df["BB_Upper"] = bb.bollinger_hband()
        df["BB_Mid"]   = bb.bollinger_mavg()
        df["BB_Lower"] = bb.bollinger_lband()
    except Exception:
        pass

    # RSI
    try:
        df["RSI"] = ta_lib.momentum.RSIIndicator(close=close, window=14).rsi()
    except Exception:
        pass

    # MACD
    try:
        macd = ta_lib.trend.MACD(close=close)
        df["MACD"]        = macd.macd()
        df["MACD_Signal"] = macd.macd_signal()
        df["MACD_Hist"]   = macd.macd_diff()
    except Exception:
        pass

    # ADX
    try:
        adx = ta_lib.trend.ADXIndicator(high=high, low=low, close=close, window=14)
        df["ADX"]     = adx.adx()
        df["ADX_pos"] = adx.adx_pos()
        df["ADX_neg"] = adx.adx_neg()
    except Exception:
        pass

    # Volume MA
    if vol is not None:
        df["Vol_MA20"] = vol.rolling(20).mean()

    # VWAP (anchored to start of displayed period)
    try:
        if vol is not None and (vol > 0).any():
            typical = (high + low + close) / 3
            df["VWAP"] = (typical * vol).cumsum() / vol.cumsum()
    except Exception:
        pass

    # OBV (On-Balance Volume) — cumulative buying/selling pressure
    try:
        if vol is not None:
            obv = ta_lib.volume.OnBalanceVolumeIndicator(close=close, volume=vol)
            df["OBV"] = obv.on_balance_volume()
    except Exception:
        try:
            direction = close.diff().apply(lambda x: 1 if x > 0 else (-1 if x < 0 else 0))
            df["OBV"] = (vol * direction).cumsum()
        except Exception:
            pass

    return df


# ─────────────────────────────────────────────────────────────────────────────
# Signal scoring
# ─────────────────────────────────────────────────────────────────────────────

def _score_signals(df: pd.DataFrame) -> dict:
    """
    Evaluate technical signals from the last row of enriched df.
    Returns dict: {score, signals, stars, advisory, adv_color}
    """
    if df is None or len(df) < 2:
        return {"score": 0, "signals": [], "stars": 3,
                "advisory": "HOLD", "adv_color": "#fbbf24"}

    row  = df.iloc[-1]
    prev = df.iloc[-2]
    signals = []
    score   = 0

    # ── RSI ──────────────────────────────────────────────────────────────────
    if "RSI" in df.columns and not pd.isna(row.get("RSI")):
        rsi = round(_safe_float(row["RSI"]), 1)
        if rsi < 30:
            signals.append(("BUY",     "RSI",  f"Oversold ({rsi})"));   score += 1
        elif rsi > 70:
            signals.append(("SELL",    "RSI",  f"Overbought ({rsi})")); score -= 1
        else:
            signals.append(("NEUTRAL", "RSI",  f"Neutral ({rsi})"))

    # ── MACD ─────────────────────────────────────────────────────────────────
    if "MACD" in df.columns and "MACD_Signal" in df.columns:
        macd_val  = _safe_float(row.get("MACD"))
        sig_val   = _safe_float(row.get("MACD_Signal"))
        prev_macd = _safe_float(prev.get("MACD"))
        prev_sig  = _safe_float(prev.get("MACD_Signal"))
        if macd_val > sig_val and prev_macd <= prev_sig:
            signals.append(("BUY",     "MACD", "Bullish crossover")); score += 2
        elif macd_val < sig_val and prev_macd >= prev_sig:
            signals.append(("SELL",    "MACD", "Bearish crossover")); score -= 2
        elif macd_val > sig_val:
            signals.append(("BUY",     "MACD", f"Above signal ({macd_val:.2f})")); score += 1
        else:
            signals.append(("SELL",    "MACD", f"Below signal ({macd_val:.2f})")); score -= 1

    # ── Bollinger Bands ───────────────────────────────────────────────────────
    if "BB_Upper" in df.columns and "BB_Lower" in df.columns:
        price = _safe_float(row.get("Close"))
        upper = _safe_float(row.get("BB_Upper"))
        lower = _safe_float(row.get("BB_Lower"))
        if price > upper:
            signals.append(("SELL",    "BB",   "Price above upper band")); score -= 1
        elif price < lower:
            signals.append(("BUY",     "BB",   "Price below lower band")); score += 1
        else:
            signals.append(("NEUTRAL", "BB",   "Price within bands"))

    # ── Moving Average alignment ──────────────────────────────────────────────
    if "MA20" in df.columns and "MA50" in df.columns:
        ma20 = _safe_float(row.get("MA20"))
        ma50 = _safe_float(row.get("MA50"))
        price = _safe_float(row.get("Close"))
        if price > ma20 > ma50:
            signals.append(("BUY",     "MA",   "Price > MA20 > MA50")); score += 1
        elif price < ma20 < ma50:
            signals.append(("SELL",    "MA",   "Price < MA20 < MA50")); score -= 1
        else:
            signals.append(("NEUTRAL", "MA",   "Mixed MA alignment"))

    # ── Volume ────────────────────────────────────────────────────────────────
    if "Volume" in df.columns and "Vol_MA20" in df.columns:
        vol_now = _safe_float(row.get("Volume"))
        vol_ma  = _safe_float(row.get("Vol_MA20"), 1)
        ratio   = vol_now / max(vol_ma, 1)
        up_day  = _safe_float(row.get("Close")) > _safe_float(prev.get("Close"))
        if ratio >= 1.3 and up_day:
            signals.append(("BUY",     "Vol",  f"High-vol up ({ratio:.1f}× avg)")); score += 1
        elif ratio >= 1.3 and not up_day:
            signals.append(("SELL",    "Vol",  f"High-vol down ({ratio:.1f}× avg)")); score -= 1
        else:
            signals.append(("NEUTRAL", "Vol",  f"{ratio:.1f}× 20-day avg"))

    # ── ADX ───────────────────────────────────────────────────────────────────
    if "ADX" in df.columns:
        adx_v = round(_safe_float(row.get("ADX")), 1)
        pos_v = _safe_float(row.get("ADX_pos"))
        neg_v = _safe_float(row.get("ADX_neg"))
        if adx_v >= 25 and pos_v > neg_v:
            signals.append(("BUY",     "ADX",  f"Strong uptrend (ADX={adx_v})")); score += 1
        elif adx_v >= 25 and pos_v < neg_v:
            signals.append(("SELL",    "ADX",  f"Strong downtrend (ADX={adx_v})")); score -= 1
        else:
            signals.append(("NEUTRAL", "ADX",  f"No strong trend (ADX={adx_v})"))

    # ── Map score → stars + advisory ─────────────────────────────────────────
    if score >= 4:
        stars, advisory, adv_color = 5, "STRONG BUY",  "#22c55e"
    elif score >= 2:
        stars, advisory, adv_color = 4, "BUY",          "#16a34a"
    elif score >= 0:
        stars, advisory, adv_color = 3, "HOLD",          "#fbbf24"
    elif score >= -2:
        stars, advisory, adv_color = 2, "SELL",          "#ea580c"
    else:
        stars, advisory, adv_color = 1, "STRONG SELL",  "#ef4444"

    return {
        "score":     score,
        "signals":   signals,
        "stars":     stars,
        "advisory":  advisory,
        "adv_color": adv_color,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Ticker data fetch
# ─────────────────────────────────────────────────────────────────────────────

def get_ticker_data(ticker: str, force_refresh: bool = False) -> dict:
    """
    Fetch OHLCV data, calculate indicators, score signals for one ticker.
    Returns a rich dict with df, price, change, pct, signals, advisory, etc.
    Cached for CACHE_TTL seconds.
    """
    cache_key = f"{ticker}_{PERIOD}"
    if not force_refresh and cache_key in _ticker_cache:
        return _ticker_cache[cache_key]

    _name, _sector = _resolve_ticker_meta(ticker)
    result = {
        "ticker":   ticker,
        "name":     _name,
        "sector":   _sector,
        "df":       None,
        "price":    None,
        "prev":     None,
        "chg_abs":  0.0,
        "chg_pct":  0.0,
        "date":     "N/A",
        "score":    0,
        "signals":  [],
        "stars":    3,
        "advisory": "HOLD",
        "adv_color":"#fbbf24",
        "error":    None,
    }

    try:
        yf_obj = yf.Ticker(ticker)
        df = yf_obj.history(period=PERIOD, interval=INTERVAL, auto_adjust=True)

        if df is None or len(df) < 30:
            result["error"] = f"Insufficient data ({len(df) if df is not None else 0} rows)"
            return result

        df.index = pd.to_datetime(df.index).tz_localize(None)
        df = _add_indicators(df)
        df.dropna(subset=["Close"], inplace=True)

        last = df.iloc[-1]
        prev = df.iloc[-2]

        price    = _safe_float(last["Close"])
        prev_cl  = _safe_float(prev["Close"])
        chg_abs  = price - prev_cl
        chg_pct  = _pct_change(price, prev_cl)

        # YTD calculation
        today    = datetime.date.today()
        ytd_start = datetime.date(today.year, 1, 1)
        ytd_df   = df[df.index.date >= ytd_start]
        if len(ytd_df) > 0:
            ytd_first = _safe_float(ytd_df.iloc[0]["Close"])
            ytd_pct   = _pct_change(price, ytd_first)
        else:
            ytd_pct   = 0.0

        scored   = _score_signals(df)

        # 52-week range from the fetched df (up to 1 year)
        week52_high = _safe_float(df["High"].max())
        week52_low  = _safe_float(df["Low"].min())
        avg_vol     = _safe_float(df["Volume"].mean()) if "Volume" in df.columns else 0.0
        cur_vol     = _safe_float(last.get("Volume", 0))

        result.update({
            "df":           df,
            "price":        price,
            "prev":         prev_cl,
            "chg_abs":      chg_abs,
            "chg_pct":      chg_pct,
            "ytd_pct":      ytd_pct,
            "week52_high":  week52_high,
            "week52_low":   week52_low,
            "avg_volume":   avg_vol,
            "cur_volume":   cur_vol,
            "vol_ratio":    round(cur_vol / avg_vol, 2) if avg_vol > 0 else 1.0,
            "date":         str(last.name.date()) if hasattr(last.name, "date") else str(last.name)[:10],
            **scored,
        })

        # ── Pre / Post-market data via fast_info ──────────────────────────────
        try:
            fi = yf_obj.fast_info
            post_px  = getattr(fi, "post_market_price",  None)
            pre_px   = getattr(fi, "pre_market_price",   None)
            post_chg = (((post_px - price) / price) * 100) if post_px and price else None
            pre_chg  = (((pre_px  - price) / price) * 100) if pre_px  and price else None
            result["post_market_price"]  = round(post_px,  2) if post_px  else None
            result["pre_market_price"]   = round(pre_px,   2) if pre_px   else None
            result["post_market_chg_pct"] = round(post_chg, 2) if post_chg else None
            result["pre_market_chg_pct"]  = round(pre_chg,  2) if pre_chg  else None
        except Exception:
            pass

    except Exception as e:
        result["error"] = str(e)
        traceback.print_exc()

    _ticker_cache[cache_key] = result
    return result


_chart_cache = TTLCache(maxsize=100, ttl=CACHE_TTL)  # per (ticker, period, interval)

# Short display periods don't have enough bars for MACD/ADX/BB on their own.
# We fetch a longer "warmup" window, compute all indicators on that, then trim
# back to the requested display window so the chart always has the full set.
_WARMUP_FETCH = {
    # (display_period, interval) → (fetch_period, fetch_interval)
    ("1d",  "5m"):  ("60d", "5m"),    # 1-day view: fetch 60 days of 5-min bars
    ("5d",  "30m"): ("60d", "30m"),   # 5-day view: fetch 60 days of 30-min bars
    ("1mo", "1d"):  ("6mo", "1d"),    # 1-month view: fetch 6 months of daily bars
}

# How far back to keep after trimming (generous buffer to handle weekends/holidays)
_TRIM_DELTA = {
    "1d":  pd.Timedelta(hours=28),    # last trading session (~6.5 h + buffer)
    "5d":  pd.Timedelta(days=8),      # 5 trading days + weekend buffer
    "1mo": pd.Timedelta(days=33),     # 1 calendar month + buffer
}


def get_chart_data(ticker: str, period: str = "6mo", interval: str = "1d") -> pd.DataFrame:
    """
    Fetch OHLCV + full indicators for any period/interval combination.
    For short windows (1D, 5D, 1M) a longer warmup dataset is fetched so
    MACD, ADX, BB, and RSI are fully computed, then the result is trimmed
    to the requested display window.
    Returns the enriched DataFrame (or None on failure).
    """
    cache_key = f"chart_{ticker}_{period}_{interval}"
    if cache_key in _chart_cache:
        return _chart_cache[cache_key]

    try:
        fetch_period, fetch_interval = _WARMUP_FETCH.get(
            (period, interval), (period, interval)
        )

        df = yf.Ticker(ticker).history(
            period=fetch_period, interval=fetch_interval, auto_adjust=True
        )
        if df is None or len(df) < 2:
            return None

        df.index = pd.to_datetime(df.index).tz_localize(None)
        df = _add_indicators(df)        # computed on the full warmup window
        df.dropna(subset=["Close"], inplace=True)

        # Trim to display window (only needed for short periods)
        trim_delta = _TRIM_DELTA.get(period)
        if trim_delta is not None and len(df) > 0:
            cutoff = df.index[-1] - trim_delta
            df = df[df.index > cutoff]

        if df is None or len(df) < 2:
            return None

        _chart_cache[cache_key] = df
        return df
    except Exception:
        return None


def get_all_portfolio_data(force_refresh: bool = False) -> dict:
    """Fetch data for all portfolio tickers. Returns dict keyed by ticker."""
    return {t: get_ticker_data(t, force_refresh=force_refresh)
            for t in PORTFOLIO_TICKERS}


# ─────────────────────────────────────────────────────────────────────────────
# Market monitor (indices, commodities, crypto, FX)
# ─────────────────────────────────────────────────────────────────────────────

def _fetch_market_row(symbol: str, name: str, category: str) -> dict:
    """Fetch a single market row (price, change, % change, YTD)."""
    try:
        df = yf.Ticker(symbol).history(period="1y", interval="1d", auto_adjust=True)
        if df is None or len(df) < 2:
            return None

        df.index = pd.to_datetime(df.index).tz_localize(None)
        price    = _safe_float(df.iloc[-1]["Close"])
        prev     = _safe_float(df.iloc[-2]["Close"])
        chg_abs  = price - prev
        chg_pct  = _pct_change(price, prev)

        today     = datetime.date.today()
        ytd_df    = df[df.index.date >= datetime.date(today.year, 1, 1)]
        ytd_pct   = _pct_change(price, _safe_float(ytd_df.iloc[0]["Close"])) if len(ytd_df) > 0 else 0.0

        return {
            "symbol":   symbol,
            "name":     name,
            "category": category,
            "price":    price,
            "chg_abs":  chg_abs,
            "chg_pct":  chg_pct,
            "ytd_pct":  ytd_pct,
        }
    except Exception:
        return None


def get_market_data(section: str, force_refresh: bool = False) -> list:
    """
    section: "indices" | "commodities" | "crypto" | "fx" | "futures"
    Returns list of row dicts.
    """
    cache_key = f"market_{section}"
    if not force_refresh and cache_key in _market_cache:
        return _market_cache[cache_key]

    mapping = {
        "indices":     INDICES,
        "commodities": COMMODITIES,
        "crypto":      CRYPTO,
        "fx":          FX,
        "futures":     FUTURES,
        "bonds":       BONDS,
    }
    symbols = mapping.get(section, [])
    rows = [r for r in (_fetch_market_row(*s) for s in symbols) if r is not None]
    rows.sort(key=lambda r: r["chg_pct"], reverse=True)
    _market_cache[cache_key] = rows
    return rows


def get_sector_data(force_refresh: bool = False) -> list:
    """
    Fetch daily % change for each S&P 500 sector ETF.
    Returns list of row dicts suitable for the sector heatmap.
    """
    cache_key = "sectors"
    if not force_refresh and cache_key in _sector_cache:
        return _sector_cache[cache_key]

    rows = []
    for symbol, name, category in SECTORS:
        row = _fetch_market_row(symbol, name, category)
        if row is not None:
            rows.append(row)

    _sector_cache[cache_key] = rows
    return rows


# Top 6 holdings by market-cap weight for each SPDR sector ETF
_SECTOR_TOP_HOLDINGS = {
    "XLK":  ["AAPL",  "MSFT",  "NVDA",  "AVGO",  "ORCL",  "CRM"],
    "XLF":  ["BRK-B", "JPM",   "V",     "MA",    "BAC",   "GS"],
    "XLV":  ["LLY",   "UNH",   "JNJ",   "ABBV",  "MRK",   "TMO"],
    "XLY":  ["AMZN",  "TSLA",  "HD",    "BKNG",  "LOW",   "TJX"],
    "XLP":  ["WMT",   "COST",  "PG",    "KO",    "PEP",   "PM"],
    "XLI":  ["GE",    "RTX",   "HON",   "CAT",   "UNP",   "ETN"],
    "XLE":  ["XOM",   "CVX",   "COP",   "EOG",   "SLB",   "PSX"],
    "XLC":  ["GOOGL", "META",  "NFLX",  "DIS",   "TMUS",  "VZ"],
    "XLRE": ["PLD",   "AMT",   "EQIX",  "WELL",  "SPG",   "DLR"],
    "XLB":  ["LIN",   "SHW",   "ECL",   "APD",   "FCX",   "NEM"],
    "XLU":  ["NEE",   "SO",    "DUK",   "AEP",   "SRE",   "EXC"],
}

# Cache for holdings drill-down data (15-min TTL — same as briefing)
_holdings_cache = TTLCache(maxsize=20, ttl=900)


def get_sector_holdings_data(etf_symbol: str, force_refresh: bool = False) -> list:
    """
    Return live price/change/market-cap data for the top holdings of a sector ETF.
    Each dict contains: symbol, name, price, chg_pct, chg_abs, mkt_cap.
    """
    cache_key = f"holdings_{etf_symbol}"
    if not force_refresh and cache_key in _holdings_cache:
        return _holdings_cache[cache_key]

    tickers = _SECTOR_TOP_HOLDINGS.get(etf_symbol, [])
    results = []
    for sym in tickers:
        try:
            t  = yf.Ticker(sym)
            fi = t.fast_info

            df = t.history(period="5d", interval="1d", auto_adjust=True)
            if df is None or len(df) < 2:
                continue
            df.index = pd.to_datetime(df.index).tz_localize(None)
            price    = _safe_float(df.iloc[-1]["Close"])
            prev     = _safe_float(df.iloc[-2]["Close"])
            chg_abs  = price - prev
            chg_pct  = _pct_change(price, prev)

            # Market cap from fast_info
            mkt_cap  = getattr(fi, "market_cap", None) or 0

            # Company name — use meta cache to avoid repeat lookups
            name_key = f"name_{sym}"
            if name_key in _meta_cache:
                name = _meta_cache[name_key]
            else:
                try:
                    name = t.info.get("shortName") or t.info.get("longName") or sym
                except Exception:
                    name = sym
                _meta_cache[name_key] = name

            results.append({
                "symbol":  sym,
                "name":    name,
                "price":   price,
                "chg_abs": chg_abs,
                "chg_pct": chg_pct,
                "mkt_cap": mkt_cap,
            })
        except Exception:
            continue

    _holdings_cache[cache_key] = results
    return results


def get_futures_data(force_refresh: bool = False) -> list:
    """
    Fetch index/commodity futures with extended-hours awareness.
    Enriches each row with a 'session' label (LIVE / CLOSED) and
    the most recent price including any pre/post-market move.
    """
    cache_key = "futures_extended"
    if not force_refresh and cache_key in _market_cache:
        return _market_cache[cache_key]

    rows = []
    for symbol, name, category in FUTURES:
        try:
            t  = yf.Ticker(symbol)
            fi = t.fast_info

            # Regular-hours close (last bar)
            df = t.history(period="5d", interval="1d", auto_adjust=True)
            if df is None or len(df) < 2:
                continue
            df.index = pd.to_datetime(df.index).tz_localize(None)
            reg_close = _safe_float(df.iloc[-1]["Close"])
            prev_close = _safe_float(df.iloc[-2]["Close"])

            # Try to get the most current price (futures trade near 24/7)
            live_price = None
            try:
                m1 = t.history(period="1d", interval="1m", prepost=True)
                if m1 is not None and len(m1) > 0:
                    live_price = _safe_float(m1.iloc[-1]["Close"])
            except Exception:
                pass

            current_price = live_price if live_price else reg_close
            chg_abs = current_price - prev_close
            chg_pct = _pct_change(current_price, prev_close)

            today     = datetime.date.today()
            ytd_df    = df[df.index.date >= datetime.date(today.year, 1, 1)]
            ytd_pct   = _pct_change(current_price, _safe_float(ytd_df.iloc[0]["Close"])) if len(ytd_df) > 0 else 0.0

            # Session label: futures are "LIVE" if we have a minute-bar price
            session = "LIVE" if live_price else "SETTLED"

            rows.append({
                "symbol":   symbol,
                "name":     name,
                "category": category,
                "price":    current_price,
                "chg_abs":  chg_abs,
                "chg_pct":  chg_pct,
                "ytd_pct":  ytd_pct,
                "session":  session,
            })
        except Exception:
            continue

    _market_cache[cache_key] = rows
    return rows


# ─────────────────────────────────────────────────────────────────────────────
# News — ticker-specific (yfinance) + multi-source RSS
# ─────────────────────────────────────────────────────────────────────────────

# Keywords used to auto-classify articles. Priority order: GEOPOLITICAL > MACRO
# > COMMODITIES > MARKETS. Articles from sources with a fixed "category" field
# skip keyword detection and keep that source category as the default.
_CATEGORY_KEYWORDS = {
    "GEOPOLITICAL": [
        "war", "conflict", "sanction", "military", "troops", "missile", "attack",
        "invasion", "geopolit", "tariff", "trade war", "diplomat", "nato",
        "russia", "ukraine", "china", "iran", "north korea", "taiwan",
        "middle east", "israel", "hamas", "hezbollah", "treaty", "nuclear",
        "ceasefire", "refugee", "occupation", "coup", "insurgent", "terror",
        "arms deal", "embargo", "protest", "riot", "civil war", "airstrike",
        "pentagon", "department of defense", "foreign minister", "g7", "g20",
    ],
    "MACRO": [
        "federal reserve", "fed rate", "interest rate", "inflation", " cpi",
        " ppi", " gdp", "recession", "central bank", "ecb ", "bank of england",
        "monetary policy", "treasury yield", "bond yield", "unemployment",
        "jobs report", "nonfarm payroll", "rate hike", "rate cut", "fomc",
        "jerome powell", "quantitative easing", "quantitative tightening",
        "fiscal policy", "debt ceiling", "imf ", "world bank", "trade deficit",
        "balance of payments", "stagflation", "hyperinflation", "deflation",
    ],
    "COMMODITIES": [
        "crude oil", "brent", " wti ", "opec", "natural gas", " lng ",
        "gold price", "silver price", "copper price", "platinum",
        "wheat price", "corn price", "soybean", "commodity", "energy price",
        "oil price", "fuel price", "gasoline price", "lithium", "rare earth",
        "iron ore", " coal ", "lumber price", "oil supply", "oil demand",
    ],
    "MARKETS": [
        "stock market", "wall street", "s&p 500", "nasdaq", "dow jones",
        "earnings report", "quarterly results", "ipo ", "merger", "acquisition",
        "share price", "dividend", "buyback", "analyst upgrade", "analyst downgrade",
        "hedge fund", "private equity", "trading", "rally", "selloff", "correction",
        "bull market", "bear market", "market cap", "valuation",
    ],
}

_CATEGORY_PRIORITY = ["GEOPOLITICAL", "MACRO", "COMMODITIES", "MARKETS"]


def _classify_article(title: str, summary: str = "", source_category: str = "") -> str:
    """
    Classify a news article into one of: GEOPOLITICAL, MACRO, COMMODITIES,
    MARKETS.  Keyword scan runs on title + summary (lowercased). The source's
    own category is used as a fallback when no keywords match.
    """
    text = (title + " " + summary).lower()
    for cat in _CATEGORY_PRIORITY:
        for kw in _CATEGORY_KEYWORDS[cat]:
            if kw in text:
                return cat
    # Fall back to the source's declared category, then MARKETS
    return source_category if source_category else "MARKETS"


def _parse_rss_date(entry) -> str:
    """Best-effort parse of RSS published date to a readable string."""
    try:
        import time as _time
        t = entry.get("published_parsed") or entry.get("updated_parsed")
        if t:
            dt = datetime.datetime.fromtimestamp(_time.mktime(t))
            age = datetime.datetime.now() - dt
            if age.days == 0:
                hrs = int(age.seconds / 3600)
                return f"{hrs}h ago" if hrs > 0 else "Just now"
            elif age.days == 1:
                return "Yesterday"
            else:
                return dt.strftime("%b %d")
    except Exception:
        pass
    return ""


def get_ticker_news(ticker: str, max_items: int = 8) -> list:
    """
    Fetch recent news for one ticker.
    Tries yfinance first; supplements with keyword search in RSS if thin.
    """
    cache_key = f"ticker_news_{ticker}"
    if cache_key in _news_cache:
        return _news_cache[cache_key]

    articles = []

    # ── yfinance native news ──────────────────────────────────────────────────
    try:
        raw = yf.Ticker(ticker).news or []
        for a in raw[:max_items]:
            title = a.get("title", "").strip()
            if not title:
                continue
            articles.append({
                "title":        title,
                "publisher":    a.get("publisher", "Yahoo Finance"),
                "source_tag":   "YAHOO FIN",
                "source_color": "#6001d2",
                "link":         a.get("link", "#"),
                "time":         datetime.datetime.fromtimestamp(
                                    a.get("providerPublishTime", 0)
                                ).strftime("%b %d  %H:%M")
                                if a.get("providerPublishTime") else "",
                "ticker":       ticker,
                "category":     "PORTFOLIO",
            })
    except Exception:
        pass

    _news_cache[cache_key] = articles
    return articles


def get_rss_news(max_per_source: int = 12) -> list:
    """
    Fetch headlines from all configured RSS sources.
    Returns a flat list sorted newest-first.
    """
    cache_key = "rss_market_news"
    if cache_key in _news_cache:
        return _news_cache[cache_key]

    try:
        import feedparser
    except ImportError:
        _news_cache[cache_key] = []
        return []

    all_articles = []
    for source in NEWS_SOURCES:
        try:
            feed = feedparser.parse(source["url"])
            for entry in feed.entries[:max_per_source]:
                title = (entry.get("title") or "").strip()
                link  = entry.get("link") or entry.get("id") or "#"
                if not title or title.lower() in ("", "none"):
                    continue
                # Brief summary if available
                summary = ""
                if entry.get("summary"):
                    import re
                    summary = re.sub(r"<[^>]+>", "", entry["summary"])[:180].strip()

                src_cat  = source.get("category", "")
                category = _classify_article(title, summary, src_cat)
                all_articles.append({
                    "title":        title,
                    "summary":      summary,
                    "publisher":    source["name"],
                    "source_tag":   source["tag"],
                    "source_color": source["color"],
                    "link":         link,
                    "time":         _parse_rss_date(entry),
                    "ticker":       "",
                    "category":     category,
                    "_raw_time":    entry.get("published_parsed") or entry.get("updated_parsed"),
                })
        except Exception:
            continue

    # Sort: entries with parsed time first (newest first), then the rest
    def _sort_key(a):
        t = a.get("_raw_time")
        if t:
            import time as _time
            return -_time.mktime(t)
        return 0

    all_articles.sort(key=_sort_key)

    # Remove duplicates by title similarity
    seen, unique = set(), []
    for a in all_articles:
        key = a["title"][:60].lower()
        if key not in seen:
            seen.add(key)
            unique.append(a)

    _news_cache[cache_key] = unique
    return unique


def get_portfolio_news(tickers: list = None, max_per_ticker: int = 4) -> list:
    """
    Aggregate ticker-specific news from yfinance for the given tickers.
    Falls back to PORTFOLIO_TICKERS if none provided.
    """
    ticker_list = tickers or PORTFOLIO_TICKERS
    all_news    = []
    seen        = set()

    for t in ticker_list:
        for article in get_ticker_news(t, max_items=max_per_ticker):
            key = article["title"][:60].lower()
            if key not in seen:
                seen.add(key)
                article["ticker"] = t
                all_news.append(article)

    return all_news


# ─────────────────────────────────────────────────────────────────────────────
# Fundamental data  —  P/E, market cap, analyst consensus, earnings, etc.
# ─────────────────────────────────────────────────────────────────────────────

def get_ticker_fundamentals(ticker: str) -> dict:
    """
    Fetch fundamental + analyst data for a ticker via yfinance .info dict.
    Cached for 1 hour (fundamentals don't change minute-to-minute).
    Returns a flat dict of formatted strings ready for display.
    """
    if ticker in _fundamentals_cache:
        return _fundamentals_cache[ticker]

    result = {
        "market_cap":        None,
        "pe_ttm":            None,
        "pe_forward":        None,
        "eps_ttm":           None,
        "beta":              None,
        "dividend_yield":    None,
        "week52_high":       None,
        "week52_low":        None,
        "target_price":      None,
        "analyst_count":     None,
        "rec_mean":          None,   # 1.0=strong buy … 5.0=strong sell
        "buy_count":         None,
        "hold_count":        None,
        "sell_count":        None,
        "short_float":       None,
        "inst_held":         None,
        "avg_volume":        None,
        "day_open":          None,
        "day_high":          None,
        "day_low":           None,
        "earnings_date":     None,
        "error":             None,
    }

    try:
        info = yf.Ticker(ticker).info

        def _fmt_cap(v):
            if v is None: return None
            if v >= 1e12: return f"${v/1e12:.2f}T"
            if v >= 1e9:  return f"${v/1e9:.2f}B"
            if v >= 1e6:  return f"${v/1e6:.1f}M"
            return f"${v:,.0f}"

        result["market_cap"]     = _fmt_cap(info.get("marketCap"))
        result["pe_ttm"]         = f"{info['trailingPE']:.1f}x"      if info.get("trailingPE")             else "N/A"
        result["pe_forward"]     = f"{info['forwardPE']:.1f}x"       if info.get("forwardPE")              else "N/A"
        result["eps_ttm"]        = f"${info['trailingEps']:.2f}"     if info.get("trailingEps")            else "N/A"
        result["beta"]           = f"{info['beta']:.2f}"             if info.get("beta")                   else "N/A"
        result["dividend_yield"] = f"{info['dividendYield']*100:.2f}%" if info.get("dividendYield")        else "0%"
        result["week52_high"]    = info.get("fiftyTwoWeekHigh")
        result["week52_low"]     = info.get("fiftyTwoWeekLow")
        result["target_price"]   = f"${info['targetMeanPrice']:.2f}" if info.get("targetMeanPrice")       else "N/A"
        result["analyst_count"]  = info.get("numberOfAnalystOpinions", 0)
        result["rec_mean"]       = info.get("recommendationMean")     # 1=strong buy, 5=strong sell
        result["short_float"]    = f"{info['shortPercentOfFloat']*100:.1f}%" if info.get("shortPercentOfFloat") else "N/A"
        result["inst_held"]      = f"{info['institutionsPercentHeld']*100:.1f}%" if info.get("institutionsPercentHeld") else "N/A"
        result["avg_volume"]     = info.get("averageVolume")
        result["day_open"]       = info.get("regularMarketOpen") or info.get("open")
        result["day_high"]       = info.get("regularMarketDayHigh") or info.get("dayHigh")
        result["day_low"]        = info.get("regularMarketDayLow")  or info.get("dayLow")

        # Analyst breakdown (buy/hold/sell counts)
        try:
            recs = yf.Ticker(ticker).recommendations
            if recs is not None and len(recs) > 0:
                latest = recs.tail(1).iloc[0]
                result["buy_count"]  = int(latest.get("strongBuy", 0) + latest.get("buy", 0))
                result["hold_count"] = int(latest.get("hold", 0))
                result["sell_count"] = int(latest.get("sell", 0) + latest.get("strongSell", 0))
        except Exception:
            pass

        # Next earnings date
        try:
            cal = yf.Ticker(ticker).calendar
            if cal is not None and not cal.empty:
                ed = cal.columns[0] if hasattr(cal, 'columns') else None
                if ed:
                    result["earnings_date"] = str(ed)[:10]
        except Exception:
            pass

    except Exception as e:
        result["error"] = str(e)

    _fundamentals_cache[ticker] = result
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Options Flow  —  P/C ratio, max pain, unusual activity, ATM IV
# ─────────────────────────────────────────────────────────────────────────────

def get_options_flow(ticker: str) -> dict:
    """
    Fetch nearest-expiration options chain and derive order flow signals:
      - Put/call volume ratio + OI ratio
      - Max pain strike price
      - ATM implied volatility (calls + puts)
      - Unusual activity: strikes where vol >> open interest (new positioning)
    Cached for 2 minutes (refreshes during market hours).
    """
    cache_key = f"options_{ticker}"
    if cache_key in _options_cache:
        return _options_cache[cache_key]

    result = {
        "pc_vol_ratio":   None,
        "pc_oi_ratio":    None,
        "max_pain":       None,
        "atm_iv_call":    None,
        "atm_iv_put":     None,
        "total_call_vol": None,
        "total_put_vol":  None,
        "total_call_oi":  None,
        "total_put_oi":   None,
        "unusual_calls":  [],
        "unusual_puts":   [],
        "expiration":     None,
        "current_price":  None,
        "error":          None,
    }

    try:
        t            = yf.Ticker(ticker)
        expirations  = t.options
        if not expirations:
            result["error"] = "No options data"
            _options_cache[cache_key] = result
            return result

        # Use the nearest expiration with non-trivial OI
        exp   = expirations[0]
        chain = t.option_chain(exp)
        calls = chain.calls.copy()
        puts  = chain.puts.copy()

        result["expiration"] = exp

        # Sanitise
        for df_opt in [calls, puts]:
            df_opt["volume"]       = df_opt["volume"].fillna(0).astype(float)
            df_opt["openInterest"] = df_opt["openInterest"].fillna(0).astype(float)
            df_opt["impliedVolatility"] = df_opt["impliedVolatility"].fillna(0).astype(float)

        # ── Put/Call ratios ───────────────────────────────────────────────────
        call_vol = calls["volume"].sum()
        put_vol  = puts["volume"].sum()
        call_oi  = calls["openInterest"].sum()
        put_oi   = puts["openInterest"].sum()

        result["total_call_vol"] = int(call_vol)
        result["total_put_vol"]  = int(put_vol)
        result["total_call_oi"]  = int(call_oi)
        result["total_put_oi"]   = int(put_oi)
        result["pc_vol_ratio"]   = round(put_vol / call_vol, 2) if call_vol > 0 else None
        result["pc_oi_ratio"]    = round(put_oi  / call_oi,  2) if call_oi  > 0 else None

        # ── Current price for ATM detection ──────────────────────────────────
        try:
            current_price = float(t.fast_info.last_price)
        except Exception:
            hist = t.history(period="1d", interval="1m")
            current_price = float(hist["Close"].iloc[-1]) if hist is not None and len(hist) > 0 else 0.0
        result["current_price"] = current_price

        # ── ATM implied volatility ────────────────────────────────────────────
        if current_price > 0:
            c_atm = calls.iloc[(calls["strike"] - current_price).abs().argsort()[:1]]
            p_atm = puts.iloc[(puts["strike"]  - current_price).abs().argsort()[:1]]
            if not c_atm.empty and c_atm["impliedVolatility"].iloc[0] > 0:
                result["atm_iv_call"] = round(c_atm["impliedVolatility"].iloc[0] * 100, 1)
            if not p_atm.empty and p_atm["impliedVolatility"].iloc[0] > 0:
                result["atm_iv_put"]  = round(p_atm["impliedVolatility"].iloc[0] * 100, 1)

        # ── Max pain ─────────────────────────────────────────────────────────
        # For each strike S: sum losses for call writers (calls ITM) + put writers (puts ITM)
        all_strikes = sorted(set(calls["strike"].tolist() + puts["strike"].tolist()))
        pain = {}
        for s in all_strikes:
            c_itm = calls[calls["strike"] <= s]
            p_itm = puts[puts["strike"]  >= s]
            c_pain = ((s - c_itm["strike"]) * c_itm["openInterest"]).sum()
            p_pain = ((p_itm["strike"] - s) * p_itm["openInterest"]).sum()
            pain[s] = c_pain + p_pain
        if pain:
            result["max_pain"] = min(pain, key=pain.get)

        # ── Unusual activity: vol >> OI (fresh positioning, not hedging) ──────
        min_vol = 50
        for label, df_opt, key in [("calls", calls, "unusual_calls"),
                                    ("puts",  puts,  "unusual_puts")]:
            unusual = df_opt[
                (df_opt["volume"] >= min_vol) &
                (df_opt["openInterest"] > 0) &
                (df_opt["volume"] / df_opt["openInterest"] >= 1.5)
            ].copy()
            unusual = unusual.sort_values("volume", ascending=False).head(5)
            for _, row in unusual.iterrows():
                result[key].append({
                    "strike":  row["strike"],
                    "volume":  int(row["volume"]),
                    "oi":      int(row["openInterest"]),
                    "vol_oi":  round(row["volume"] / max(row["openInterest"], 1), 1),
                    "iv":      round(row["impliedVolatility"] * 100, 1),
                    "last":    round(float(row.get("lastPrice", 0)), 2),
                })

    except Exception as e:
        result["error"] = str(e)

    _options_cache[cache_key] = result
    return result


# ─────────────────────────────────────────────────────────────────────────────
# AI Morning Briefing  —  powered by Groq (free tier, Llama 3.3 70B)
# ─────────────────────────────────────────────────────────────────────────────

_GROQ_URL   = "https://api.groq.com/openai/v1/chat/completions"
_GROQ_MODEL = "llama-3.3-70b-versatile"


def get_ai_briefing(portfolio_data: dict, news_headlines: list = None) -> dict:
    """
    Generate a 3-4 sentence analyst-style morning briefing using Groq (free).
    portfolio_data: dict of {ticker: data_dict} from get_ticker_data()
    news_headlines: list of article dicts (title, publisher) from get_rss_news()

    Returns: {"text": str, "generated_at": str, "error": str|None}
    """
    # Build a stable cache key from the tickers + rough timestamp (15-min bucket)
    tickers_key = "_".join(sorted(portfolio_data.keys()))
    bucket      = int(datetime.datetime.now().timestamp() // 900)  # 15-min buckets
    cache_key   = f"briefing_{tickers_key}_{bucket}"

    if cache_key in _briefing_cache:
        return _briefing_cache[cache_key]

    api_key = os.environ.get("GROQ_API_KEY", "")
    if not api_key:
        result = {
            "text":         "AI Briefing unavailable — GROQ_API_KEY not set in .env file.",
            "generated_at": "",
            "error":        "missing_key",
        }
        return result

    # ── Build the prompt ──────────────────────────────────────────────────────
    lines = []
    for ticker, d in portfolio_data.items():
        if d.get("price") is None:
            continue
        chg   = d.get("chg_pct", 0)
        sign  = "+" if chg >= 0 else ""
        rsi   = ""
        for sig in d.get("signals", []):
            if sig[1] == "RSI":
                rsi = f"  RSI: {sig[2]}"
                break
        lines.append(
            f"  {ticker} ({d.get('sector', ('?',))[0]}): "
            f"${d.get('price', 0):.2f}  {sign}{chg:.2f}%  "
            f"[{d.get('advisory','HOLD')}]{rsi}"
        )

    portfolio_block = "\n".join(lines) if lines else "  No portfolio data available."

    # Top 5 headlines
    headlines_block = ""
    if news_headlines:
        top = [a["title"] for a in news_headlines[:5] if a.get("title")]
        headlines_block = "\n".join(f"  - {h}" for h in top)
    else:
        headlines_block = "  (No headlines available)"

    today_str = datetime.datetime.now().strftime("%A, %B %d, %Y  %H:%M")

    prompt = f"""You are a senior equity analyst writing a concise morning market briefing.
Today is {today_str}.

PORTFOLIO POSITIONS:
{portfolio_block}

TOP MARKET HEADLINES:
{headlines_block}

Write a 3-4 sentence briefing in the style of a Bloomberg terminal analyst note.
Be specific: reference actual tickers, % moves, and relevant headlines.
Do not use bullet points. Do not use markdown formatting.
Keep it under 80 words. Start directly with the market context — no greeting, no sign-off."""

    # ── Call Groq API ─────────────────────────────────────────────────────────
    try:
        response = requests.post(
            _GROQ_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type":  "application/json",
            },
            json={
                "model":       _GROQ_MODEL,
                "messages":    [{"role": "user", "content": prompt}],
                "max_tokens":  180,
                "temperature": 0.4,
            },
            timeout=12,
        )
        response.raise_for_status()
        data  = response.json()
        text  = data["choices"][0]["message"]["content"].strip()
        result = {
            "text":         text,
            "generated_at": datetime.datetime.now().strftime("%H:%M"),
            "error":        None,
        }
    except requests.exceptions.Timeout:
        result = {"text": "AI Briefing timed out — Groq API did not respond in time.",
                  "generated_at": "", "error": "timeout"}
    except Exception as exc:
        result = {"text": f"AI Briefing unavailable ({type(exc).__name__}).",
                  "generated_at": "", "error": str(exc)}

    _briefing_cache[cache_key] = result
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Utility
# ─────────────────────────────────────────────────────────────────────────────

def last_updated() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d  %H:%M:%S")


# ─────────────────────────────────────────────────────────────────────────────
# Calendar  —  earnings, economic events, FOMC, IPOs
# ─────────────────────────────────────────────────────────────────────────────

# Published FOMC meeting dates (decision day = second day of each 2-day meeting)
_FOMC_DATES = [
    "2025-05-07", "2025-06-18", "2025-07-30",
    "2025-09-17", "2025-10-29", "2025-12-10",
    "2026-01-28", "2026-03-18", "2026-04-29", "2026-06-17",
    "2026-07-29", "2026-09-16", "2026-10-28", "2026-12-09",
]


def get_earnings_calendar(tickers: list) -> list:
    """Get upcoming earnings dates for the given tickers (60-day window)."""
    cache_key = f"earnings_cal_{'_'.join(sorted(tickers))}"
    if cache_key in _calendar_cache:
        return _calendar_cache[cache_key]

    events = []
    today     = datetime.date.today()
    lookahead = today + datetime.timedelta(days=60)

    for ticker in tickers:
        try:
            t   = yf.Ticker(ticker)
            cal = t.calendar
            if cal is None:
                continue

            # yfinance returns a dict: {'Earnings Date': [...], 'EPS Estimate': x, ...}
            earnings_dates = cal.get("Earnings Date", [])
            if not isinstance(earnings_dates, list):
                earnings_dates = [earnings_dates]

            eps_est = cal.get("EPS Estimate")
            rev_est = cal.get("Revenue Estimate")

            for ed in earnings_dates:
                try:
                    if hasattr(ed, "date"):
                        ed = ed.date()
                    elif isinstance(ed, str):
                        ed = datetime.datetime.strptime(ed[:10], "%Y-%m-%d").date()
                    if not (today <= ed <= lookahead):
                        continue
                except Exception:
                    continue

                parts = []
                if eps_est is not None:
                    parts.append(f"EPS est: ${eps_est:.2f}")
                if rev_est is not None:
                    if rev_est >= 1e9:
                        parts.append(f"Rev est: ${rev_est/1e9:.1f}B")
                    elif rev_est >= 1e6:
                        parts.append(f"Rev est: ${rev_est/1e6:.0f}M")

                events.append({
                    "date":     ed,
                    "category": "EARNINGS",
                    "title":    f"{ticker}  Earnings",
                    "subtitle": "  ·  ".join(parts),
                    "impact":   "HIGH",
                    "ticker":   ticker,
                })
        except Exception:
            continue

    events.sort(key=lambda e: e["date"])
    _calendar_cache[cache_key] = events
    return events


def get_economic_calendar() -> list:
    """Fetch high/medium-impact USD economic events from ForexFactory (this + next week)."""
    cache_key = "economic_cal"
    if cache_key in _calendar_cache:
        return _calendar_cache[cache_key]

    today  = datetime.date.today()
    events = []
    urls   = [
        "https://nfs.faireconomy.media/ff_calendar_thisweek.json",
        "https://nfs.faireconomy.media/ff_calendar_nextweek.json",
    ]

    for url in urls:
        try:
            resp = requests.get(url, timeout=8,
                                headers={"User-Agent": "Mozilla/5.0"})
            if resp.status_code != 200:
                continue
            for item in resp.json():
                if item.get("country", "").upper() != "USD":
                    continue
                impact = item.get("impact", "").lower()
                if impact not in ("high", "medium"):
                    continue

                date_str = item.get("date", "")
                try:
                    event_date = datetime.datetime.fromisoformat(date_str[:19]).date()
                except Exception:
                    continue
                if event_date < today:
                    continue

                actual   = item.get("actual")   or ""
                forecast = item.get("forecast") or ""
                previous = item.get("previous") or ""
                parts = []
                if actual:
                    parts.append(f"Actual: {actual}")
                elif forecast:
                    parts.append(f"Forecast: {forecast}")
                if previous:
                    parts.append(f"Prev: {previous}")

                events.append({
                    "date":     event_date,
                    "category": "ECONOMIC",
                    "title":    item.get("title", "Economic Event"),
                    "subtitle": "  ·  ".join(parts),
                    "impact":   "HIGH" if impact == "high" else "MEDIUM",
                    "ticker":   "",
                })
        except Exception:
            continue

    # Deduplicate by (date, title)
    seen, deduped = set(), []
    for e in events:
        key = (e["date"], e["title"])
        if key not in seen:
            seen.add(key)
            deduped.append(e)
    deduped.sort(key=lambda e: e["date"])
    _calendar_cache[cache_key] = deduped
    return deduped


def get_fomc_calendar() -> list:
    """Return upcoming FOMC decision dates."""
    today  = datetime.date.today()
    events = []
    for date_str in _FOMC_DATES:
        dt = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
        if dt >= today:
            events.append({
                "date":     dt,
                "category": "FED",
                "title":    "FOMC Rate Decision",
                "subtitle": "Federal Open Market Committee meeting",
                "impact":   "HIGH",
                "ticker":   "",
            })
    return events


def get_ipo_calendar() -> list:
    """Fetch upcoming IPOs from the NASDAQ public API."""
    cache_key = "ipo_cal"
    if cache_key in _calendar_cache:
        return _calendar_cache[cache_key]

    today  = datetime.date.today()
    events = []
    try:
        url  = "https://api.nasdaq.com/api/ipo/alldata?type=upcoming&limit=20"
        hdrs = {
            "User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                           "AppleWebKit/537.36 Chrome/120.0 Safari/537.36"),
            "Accept": "application/json",
        }
        resp = requests.get(url, headers=hdrs, timeout=8)
        if resp.status_code == 200:
            rows = (resp.json()
                    .get("data", {}) or {})
            rows = rows.get("upcomingTable", {}).get("rows", []) or []
            for row in rows:
                date_str = (row.get("pricedDate") or
                            row.get("expectedPriceDate") or "")
                if not date_str:
                    continue
                dt = None
                for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%b %d, %Y"):
                    try:
                        dt = datetime.datetime.strptime(date_str.strip(), fmt).date()
                        break
                    except ValueError:
                        continue
                if dt is None or dt < today:
                    continue

                company = row.get("companyName", "Unknown")
                symbol  = row.get("proposedTickerSymbol", "")
                lo      = row.get("priceRangeLow",  "")
                hi      = row.get("priceRangeHigh", "")
                parts   = []
                if symbol:
                    parts.append(f"Ticker: {symbol}")
                if lo and hi:
                    parts.append(f"Range: ${lo}–${hi}")
                elif lo:
                    parts.append(f"Est. price: ${lo}")

                events.append({
                    "date":     dt,
                    "category": "IPO",
                    "title":    f"{company}",
                    "subtitle": "  ·  ".join(parts),
                    "impact":   "MEDIUM",
                    "ticker":   symbol,
                })
    except Exception:
        pass

    events.sort(key=lambda e: e["date"])
    _calendar_cache[cache_key] = events
    return events


def get_full_calendar(tickers: list) -> list:
    """Merge all calendar sources into a single date-sorted list."""
    from concurrent.futures import ThreadPoolExecutor, as_completed
    results = []
    fns = [
        lambda: get_earnings_calendar(tickers),
        get_economic_calendar,
        get_fomc_calendar,
        get_ipo_calendar,
    ]
    with ThreadPoolExecutor(max_workers=4) as ex:
        futures = {ex.submit(fn): fn for fn in fns}
        for fut in as_completed(futures):
            try:
                results.extend(fut.result())
            except Exception:
                pass
    results.sort(key=lambda e: e["date"])
    return results


def clear_cache():
    _ticker_cache.clear()
    _market_cache.clear()
    _chart_cache.clear()
    _news_cache.clear()
    _briefing_cache.clear()
    _fundamentals_cache.clear()
    _options_cache.clear()
    _meta_cache.clear()
    _calendar_cache.clear()
