# ─────────────────────────────────────────────────────────────────────────────
# intelligence.py  —  Smart Money Operating System  •  Enzo Market Pulse
#
# Replicates institutional-grade market analysis using only free/public data.
# Layers:
#   1. Smart Money Score      — dark pool proxy, accumulation/distribution
#   2. Cross-Asset Intelligence — correlations, rotation, lead-lag
#   3. Market Regime Detection  — risk-on/off, volatility, liquidity
#   4. Predictive Signal Engine — probabilistic forecasts
#   5. Trade Idea Generation    — concrete setups with R/R
#   6. Learning / Adaptation    — outcome tracking + accuracy stats
# ─────────────────────────────────────────────────────────────────────────────

import datetime
import json
import os
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

import numpy as np
import pandas as pd
import yfinance as yf
from cachetools import TTLCache

# ─────────────────────────────────────────────────────────────────────────────
# Cross-asset universe
# ─────────────────────────────────────────────────────────────────────────────

CROSS_ASSET = {
    "SPY":       ("US Equities",   "equity"),
    "QQQ":       ("Tech Equities", "equity"),
    "BTC-USD":   ("Bitcoin",       "crypto"),
    "GC=F":      ("Gold",          "commodity"),
    "CL=F":      ("Crude Oil",     "commodity"),
    "DX-Y.NYB":  ("US Dollar",     "fx"),
    "^TNX":      ("10Y Yield",     "bonds"),
    "^VIX":      ("Volatility",    "volatility"),
}

_cross_cache = TTLCache(maxsize=5,  ttl=600)   # 10 min — cross-asset data
_intel_cache = TTLCache(maxsize=30, ttl=600)   # 10 min — per-ticker scores

_HISTORY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "signal_history.json")


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _safe(val, default=0.0):
    try:
        v = float(val)
        return v if np.isfinite(v) else default
    except (TypeError, ValueError):
        return default


# ─────────────────────────────────────────────────────────────────────────────
# Cross-asset data fetcher
# ─────────────────────────────────────────────────────────────────────────────

def _fetch_one_cross(symbol: str) -> Optional[pd.DataFrame]:
    try:
        df = yf.Ticker(symbol).history(period="6mo", interval="1d", auto_adjust=True)
        if df is None or len(df) < 30:
            return None
        df.index = pd.to_datetime(df.index).tz_localize(None)
        cols = [c for c in ["Close", "Volume", "High", "Low", "Open"] if c in df.columns]
        return df[cols].copy()
    except Exception:
        return None


def get_cross_asset_data() -> dict:
    """
    Fetch 6-month daily data for all 8 cross-asset symbols in parallel.
    Returns {symbol: DataFrame}. Cached 10 minutes.
    """
    if "cross_asset" in _cross_cache:
        return _cross_cache["cross_asset"]

    result = {}
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(_fetch_one_cross, sym): sym for sym in CROSS_ASSET}
        for fut in as_completed(futures):
            sym = futures[fut]
            try:
                df = fut.result()
                if df is not None:
                    result[sym] = df
            except Exception:
                pass

    _cross_cache["cross_asset"] = result
    return result


# ─────────────────────────────────────────────────────────────────────────────
# LAYER 1 — Smart Money Score
# ─────────────────────────────────────────────────────────────────────────────

def _compute_cmf(df: pd.DataFrame, window: int = 20) -> float:
    """
    Chaikin Money Flow — volume-weighted buying/selling pressure.
    Range [-1, 1]. Positive = accumulation, negative = distribution.
    """
    if len(df) < window:
        return 0.0
    tail = df.tail(window).copy()
    rng  = (tail["High"] - tail["Low"]).replace(0, np.nan)
    mfm  = ((tail["Close"] - tail["Low"]) - (tail["High"] - tail["Close"])) / rng
    mfm  = mfm.fillna(0)
    denom = tail["Volume"].sum()
    if denom == 0:
        return 0.0
    return float(np.clip((mfm * tail["Volume"]).sum() / denom, -1, 1))


def _compute_obv_divergence(df: pd.DataFrame, window: int = 20) -> float:
    """
    OBV divergence score.
    Compares OBV momentum to price momentum over the window.
    +1 = strong accumulation (OBV rising faster than price)
    -1 = strong distribution (OBV falling while price holds/rises)
    """
    if len(df) < window + 5:
        return 0.0
    tail = df.tail(window).copy()

    direction = tail["Close"].diff().apply(lambda x: 1 if x > 0 else (-1 if x < 0 else 0))
    obv = (tail["Volume"] * direction).cumsum()

    price_roc = _safe(tail["Close"].iloc[-1] / max(tail["Close"].iloc[0], 0.01) - 1)
    obv_start = obv.iloc[0]
    obv_roc   = _safe((obv.iloc[-1] - obv_start) / max(abs(obv_start), 1))

    # Divergence: OBV outpacing price = accumulation
    return float(np.clip((obv_roc - price_roc) * 3, -1, 1))


def _compute_block_trade_score(df: pd.DataFrame, window: int = 20) -> float:
    """
    Dark pool proxy: detects days with high volume + narrow price range.
    This is the hallmark of institutional block trading — large orders
    executed without tipping the market (stealth accumulation/distribution).
    Range [-1, 1]. Positive = net institutional buying detected.
    """
    if len(df) < window + 5:
        return 0.0
    tail = df.tail(window).copy()

    avg_vol   = tail["Volume"].mean()
    avg_range = (tail["High"] - tail["Low"]).mean()
    if avg_vol == 0 or avg_range == 0:
        return 0.0

    vol_ratio   = tail["Volume"] / avg_vol
    range_ratio = (tail["High"] - tail["Low"]) / avg_range

    # Block trade day: volume spike + tight range (price suppressed by large orders)
    block_mask = (vol_ratio > 1.4) & (range_ratio < 0.75)
    if block_mask.sum() == 0:
        return 0.0

    block_df = tail[block_mask]
    intensity = min(block_mask.sum() / window * 3, 1.0)

    # Directional: were block days net up or down?
    if "Open" in block_df.columns:
        up   = (block_df["Close"] > block_df["Open"]).sum()
    else:
        up   = (block_df["Close"] > block_df["Close"].shift(1).fillna(block_df["Close"])).sum()
    down = block_mask.sum() - up
    direction = (up - down) / max(block_mask.sum(), 1)

    return float(np.clip(direction * intensity, -1, 1))


def _compute_vol_accumulation(df: pd.DataFrame, window: int = 20) -> float:
    """
    Volume accumulation: ratio of high-volume up days vs high-volume down days.
    Measures whether institutional-sized volume is going into or out of a stock.
    Range [-1, 1].
    """
    if len(df) < window + 1:
        return 0.0
    tail    = df.tail(window).copy()
    avg_vol = tail["Volume"].mean()
    if avg_vol == 0:
        return 0.0

    high_vol = tail["Volume"] > avg_vol * 1.2
    up_day   = tail["Close"] > tail["Close"].shift(1)

    buy_pressure  = (high_vol & up_day).sum()
    sell_pressure = (high_vol & ~up_day).sum()
    total         = buy_pressure + sell_pressure
    if total == 0:
        return 0.0
    return float(np.clip((buy_pressure - sell_pressure) / total, -1, 1))


def compute_smart_money_score(
    ticker: str,
    df: pd.DataFrame,
    options_flow: dict = None,
) -> dict:
    """
    Compute the Smart Money Score (0–100) from four institutional-signal components:
      - OBV Divergence   (30%): volume trend vs price trend
      - Block Trade Proxy(25%): dark pool / stealth accumulation detection
      - Chaikin MF       (25%): volume-weighted directional pressure
      - Vol Accumulation (20%): high-vol up vs down day imbalance

    Options flow (if available) adds a ±5 pt bonus.
    Returns: {score, grade, signals, component breakdown}
    """
    cache_key = f"sms_{ticker}"
    if cache_key in _intel_cache:
        return _intel_cache[cache_key]

    if df is None or len(df) < 25:
        return {
            "ticker": ticker, "score": 50, "grade": "C",
            "signals": [], "error": "insufficient data",
            "obv_div": 0, "block_score": 0, "cmf": 0, "vol_acc": 0,
        }

    obv_div     = _compute_obv_divergence(df)
    block_score = _compute_block_trade_score(df)
    cmf         = _compute_cmf(df)
    vol_acc     = _compute_vol_accumulation(df)

    # Weighted composite [-1, 1]
    raw = (
        obv_div     * 0.30 +
        block_score * 0.25 +
        cmf         * 0.25 +
        vol_acc     * 0.20
    )

    # Map to [0, 100]
    score = int(round((raw + 1) / 2 * 100))
    score = max(0, min(100, score))

    # Options flow bonus ±5 pts
    options_bonus  = 0
    options_signal = None
    if options_flow and not options_flow.get("error"):
        pc             = options_flow.get("pc_vol_ratio")
        unusual_calls  = options_flow.get("unusual_calls", [])
        unusual_puts   = options_flow.get("unusual_puts",  [])
        if pc is not None:
            if pc < 0.7:
                options_bonus  = 5
                options_signal = ("BUY",  "OPTIONS", f"P/C vol ratio {pc:.2f} — calls dominating (bullish flow)")
            elif pc > 1.3:
                options_bonus  = -5
                options_signal = ("SELL", "OPTIONS", f"P/C vol ratio {pc:.2f} — puts dominating (bearish flow)")
        if unusual_calls:
            options_bonus += 3
            if not options_signal:
                options_signal = ("BUY", "OPTIONS", f"Unusual call activity at {len(unusual_calls)} strikes")
        if unusual_puts:
            options_bonus -= 3
        score = max(0, min(100, score + options_bonus))

    # Grade
    if   score >= 75: grade = "A+"
    elif score >= 65: grade = "A"
    elif score >= 55: grade = "B+"
    elif score >= 45: grade = "B"
    elif score >= 35: grade = "C"
    elif score >= 25: grade = "D"
    else:             grade = "F"

    # Build human-readable signal list
    signals = []
    if obv_div > 0.15:
        signals.append(("BUY",     "OBV",    f"OBV rising faster than price — stealth accumulation"))
    elif obv_div < -0.15:
        signals.append(("SELL",    "OBV",    f"OBV diverging negatively — distribution in progress"))
    else:
        signals.append(("NEUTRAL", "OBV",    f"OBV in line with price action"))

    if block_score > 0.15:
        signals.append(("BUY",     "BLOCK",  f"Block trade clustering — institutional buying on quiet ranges"))
    elif block_score < -0.15:
        signals.append(("SELL",    "BLOCK",  f"Block distribution — large sellers using price stability to exit"))
    else:
        signals.append(("NEUTRAL", "BLOCK",  f"No significant block trade activity"))

    if cmf > 0.10:
        signals.append(("BUY",     "CMF",    f"Chaikin MF {cmf:+.3f} — sustained buying pressure"))
    elif cmf < -0.10:
        signals.append(("SELL",    "CMF",    f"Chaikin MF {cmf:+.3f} — sustained selling pressure"))
    else:
        signals.append(("NEUTRAL", "CMF",    f"Neutral money flow ({cmf:+.3f})"))

    if vol_acc > 0.15:
        signals.append(("BUY",     "VOLPRO", f"High-volume up days dominating — institutional demand"))
    elif vol_acc < -0.15:
        signals.append(("SELL",    "VOLPRO", f"High-volume down days dominating — institutional supply"))
    else:
        signals.append(("NEUTRAL", "VOLPRO", f"Balanced volume profile"))

    if options_signal:
        signals.append(options_signal)

    result = {
        "ticker":        ticker,
        "score":         score,
        "grade":         grade,
        "signals":       signals,
        "obv_div":       round(obv_div, 3),
        "block_score":   round(block_score, 3),
        "cmf":           round(cmf, 3),
        "vol_acc":       round(vol_acc, 3),
        "options_bonus": options_bonus,
        "raw_composite": round(raw, 3),
    }
    _intel_cache[cache_key] = result
    return result


# ─────────────────────────────────────────────────────────────────────────────
# LAYER 2 — Cross-Asset Intelligence
# ─────────────────────────────────────────────────────────────────────────────

def compute_cross_asset_intelligence(cross_data: dict) -> dict:
    """
    Analyze relationships across equities, crypto, bonds, commodities, FX.

    Detects:
    - Correlation regime (normal / diverging / unstable)
    - Lead-lag (which asset is moving first)
    - Capital rotation (where money is flowing)

    Returns:
    {
        asset_rotation, leading_asset, lagging_assets,
        correlation_regime, correlations, momentum_map,
        flow_summary, signals
    }
    """
    if "cross_intel" in _cross_cache:
        return _cross_cache["cross_intel"]

    result = {
        "asset_rotation":     "No data",
        "leading_asset":      "Unknown",
        "lagging_assets":     [],
        "correlation_regime": "normal",
        "correlations":       {},
        "momentum_map":       {},
        "flow_summary":       "Insufficient data",
        "signals":            [],
    }
    if len(cross_data) < 3:
        return result

    # Build aligned daily returns matrix
    closes = {}
    for sym, df in cross_data.items():
        closes[sym] = df["Close"].resample("D").last().dropna()
    returns_df = pd.DataFrame(closes).pct_change().dropna(how="all").fillna(0)
    if len(returns_df) < 20:
        return result

    # 5-day and 20-day momentum (used for rotation detection)
    momentum_5d  = {}
    momentum_20d = {}
    for sym in returns_df.columns:
        s = returns_df[sym]
        if len(s) >= 5:
            momentum_5d[sym]  = float(s.tail(5).sum()  * 100)
        if len(s) >= 20:
            momentum_20d[sym] = float(s.tail(20).sum() * 100)

    result["momentum_map"] = {
        sym: {"5d": round(momentum_5d.get(sym, 0), 2),
              "20d": round(momentum_20d.get(sym, 0), 2)}
        for sym in CROSS_ASSET if sym in returns_df.columns
    }

    # ── Correlation regime ────────────────────────────────────────────────────
    core = [s for s in ["SPY", "QQQ", "BTC-USD", "GC=F"] if s in returns_df.columns]
    if len(core) >= 3:
        recent_corr   = returns_df[core].tail(20).corr()
        baseline_corr = returns_df[core].tail(60).corr() if len(returns_df) >= 60 else recent_corr

        def _avg_offdiag(m):
            vals = [m.iloc[i, j] for i in range(len(m)) for j in range(i + 1, len(m))
                    if np.isfinite(m.iloc[i, j])]
            return float(np.mean(vals)) if vals else 0.0

        avg_recent   = _avg_offdiag(recent_corr)
        avg_baseline = _avg_offdiag(baseline_corr)
        corr_shift   = avg_recent - avg_baseline

        if "SPY" in core:
            for sym in core:
                if sym != "SPY" and sym in recent_corr.columns:
                    result["correlations"][sym] = round(float(recent_corr.loc["SPY", sym]), 2)

        # High positive correlations = everything falling together = risk-off
        if avg_recent > 0.55:
            result["correlation_regime"] = "unstable"
        elif abs(corr_shift) > 0.25:
            result["correlation_regime"] = "diverging"
        else:
            result["correlation_regime"] = "normal"

    # ── Lead-lag: BTC vs SPY (BTC known to lead risk sentiment) ──────────────
    lead_lag_signal = None
    if "BTC-USD" in returns_df.columns and "SPY" in returns_df.columns:
        btc = returns_df["BTC-USD"].tail(60)
        spy = returns_df["SPY"].tail(60)
        best_lag, best_corr = 0, 0.0
        for lag in [1, 2, 3]:
            if len(btc) > lag:
                c = float(btc.iloc[:-lag].corr(spy.iloc[lag:]))
                if np.isfinite(c) and abs(c) > abs(best_corr):
                    best_lag, best_corr = lag, c
        if abs(best_corr) > 0.25:
            direction = "leads" if best_corr > 0 else "inversely leads"
            lead_lag_signal = f"BTC {direction} SPY by ~{best_lag}d (r={best_corr:.2f})"

    # ── Capital rotation ──────────────────────────────────────────────────────
    tech_mom   = momentum_5d.get("QQQ",       0)
    energy_mom = momentum_5d.get("CL=F",      0)
    safe_mom   = (momentum_5d.get("GC=F", 0) + momentum_5d.get("^TNX", 0)) / 2
    equity_mom = momentum_5d.get("SPY",       0)
    crypto_mom = momentum_5d.get("BTC-USD",   0)
    dxy_mom    = momentum_5d.get("DX-Y.NYB",  0)

    rotation_parts = []
    if abs(energy_mom - tech_mom) > 1.5:
        rotation_parts.append("Tech → Energy" if energy_mom > tech_mom else "Energy → Tech")
    if safe_mom > equity_mom + 1.0:
        rotation_parts.append("Equities → Safe Havens")
    elif equity_mom > safe_mom + 1.0:
        rotation_parts.append("Safe Havens → Equities")
    if crypto_mom > equity_mom + 3.0:
        rotation_parts.append("Equities → Crypto")
    elif equity_mom > crypto_mom + 3.0:
        rotation_parts.append("Crypto → Equities")
    if dxy_mom > 1.5:
        rotation_parts.append("DXY strengthening — EM/commodity headwind")

    result["asset_rotation"] = "  |  ".join(rotation_parts) if rotation_parts else "No significant rotation"

    # ── Leading asset (highest 5d momentum, non-VIX) ─────────────────────────
    candidates = {s: m for s, m in momentum_5d.items() if s != "^VIX" and abs(m) > 0}
    if candidates:
        leading = max(candidates, key=lambda s: candidates[s])
        name    = CROSS_ASSET.get(leading, (leading,))[0]
        result["leading_asset"]  = f"{leading} ({name})  {candidates[leading]:+.1f}%"
        result["lagging_assets"] = [
            f"{s} ({CROSS_ASSET.get(s, ('',))[0]})  {candidates[s]:+.1f}%"
            for s in sorted(candidates, key=lambda s: candidates[s])[:3]
            if s != leading
        ]

    # ── Signals ───────────────────────────────────────────────────────────────
    signals = []
    regime = result["correlation_regime"]
    if regime == "unstable":
        signals.append(("WARN", "CORR", "High cross-asset correlation — risk-off dynamics active, diversification failing"))
    elif regime == "diverging":
        signals.append(("INFO", "CORR", "Correlation structure shifting — watch for regime transition"))
    else:
        signals.append(("OK",   "CORR", "Normal correlation regime — cross-asset diversification intact"))

    if lead_lag_signal:
        signals.append(("INFO", "LEAD", lead_lag_signal))
    for r in rotation_parts:
        signals.append(("INFO", "ROTATE", r))

    result["signals"]      = signals
    result["flow_summary"] = (
        f"Leading: {result['leading_asset']}  ·  "
        f"Rotation: {result['asset_rotation']}  ·  "
        f"Corr: {result['correlation_regime'].upper()}"
    )

    _cross_cache["cross_intel"] = result
    return result


# ─────────────────────────────────────────────────────────────────────────────
# LAYER 3 — Market Regime Detection
# ─────────────────────────────────────────────────────────────────────────────

def detect_market_regime(cross_data: dict, cross_intel: dict) -> dict:
    """
    Classify current market environment using VIX, trend, correlations, gold/equity ratio.

    Returns:
    {
        regime:      "Risk-On" | "Risk-Off" | "Transition" | "High Volatility" | "Low Liquidity"
        confidence:  0–100
        key_drivers: list[str]
        vix_level:   float
        spy_trend:   "uptrend" | "downtrend" | "sideways"
        btc_trend:   "uptrend" | "downtrend" | "sideways"
        color:       hex string
    }
    """
    if "regime" in _cross_cache:
        return _cross_cache["regime"]

    result = {
        "regime":      "Transition",
        "confidence":  45,
        "key_drivers": [],
        "vix_level":   20.0,
        "spy_trend":   "sideways",
        "btc_trend":   "sideways",
        "color":       "#fbbf24",
    }

    drivers      = []
    regime_votes = []  # (regime_name, weight)

    # ── VIX ───────────────────────────────────────────────────────────────────
    vix_df = cross_data.get("^VIX")
    vix    = 20.0
    if vix_df is not None and len(vix_df) >= 2:
        vix = _safe(vix_df["Close"].iloc[-1], 20.0)
        result["vix_level"] = round(vix, 1)
        if vix < 15:
            regime_votes.append(("Risk-On",        35))
            drivers.append(f"VIX {vix:.1f} — extreme complacency, strong risk-on signal")
        elif vix < 20:
            regime_votes.append(("Risk-On",        20))
            drivers.append(f"VIX {vix:.1f} — low volatility, benign environment")
        elif vix < 27:
            regime_votes.append(("Transition",     20))
            drivers.append(f"VIX {vix:.1f} — moderate volatility, mixed signals")
        elif vix < 35:
            regime_votes.append(("Risk-Off",       25))
            drivers.append(f"VIX {vix:.1f} — elevated fear, defensive positioning warranted")
        else:
            regime_votes.append(("High Volatility",45))
            drivers.append(f"VIX {vix:.1f} — FEAR spike, crisis-level volatility")

    # ── SPY trend ─────────────────────────────────────────────────────────────
    spy_df  = cross_data.get("SPY")
    spy_5d  = 0.0
    if spy_df is not None and len(spy_df) >= 50:
        close   = spy_df["Close"]
        ma20    = _safe(close.rolling(20).mean().iloc[-1])
        ma50    = _safe(close.rolling(50).mean().iloc[-1])
        price   = _safe(close.iloc[-1])
        spy_5d  = _safe(close.pct_change(5).iloc[-1] * 100)
        spy_20d = _safe(close.pct_change(20).iloc[-1] * 100)

        if price > ma20 > ma50:
            result["spy_trend"] = "uptrend"
            regime_votes.append(("Risk-On",  25))
            drivers.append(f"SPY above MA20 & MA50 (uptrend, +{spy_20d:.1f}% 20d)")
        elif price < ma20 < ma50:
            result["spy_trend"] = "downtrend"
            regime_votes.append(("Risk-Off", 25))
            drivers.append(f"SPY below MA20 & MA50 (downtrend, {spy_20d:.1f}% 20d)")
        else:
            result["spy_trend"] = "sideways"
            regime_votes.append(("Transition", 18))
            drivers.append(f"SPY mixed MA alignment ({spy_20d:+.1f}% 20d)")

    # ── BTC trend (risk appetite barometer) ───────────────────────────────────
    btc_df = cross_data.get("BTC-USD")
    if btc_df is not None and len(btc_df) >= 20:
        btc_5d  = _safe(btc_df["Close"].pct_change(5).iloc[-1]  * 100)
        btc_20d = _safe(btc_df["Close"].pct_change(20).iloc[-1] * 100)
        if btc_5d > 4:
            result["btc_trend"] = "uptrend"
            regime_votes.append(("Risk-On",  15))
            drivers.append(f"BTC +{btc_5d:.1f}% (5d) — crypto risk appetite elevated")
        elif btc_5d < -4:
            result["btc_trend"] = "downtrend"
            regime_votes.append(("Risk-Off", 15))
            drivers.append(f"BTC {btc_5d:.1f}% (5d) — crypto risk appetite declining")

    # ── Gold vs equities (flight-to-safety signal) ────────────────────────────
    gold_df = cross_data.get("GC=F")
    if gold_df is not None and spy_df is not None and len(gold_df) >= 10:
        gold_5d = _safe(gold_df["Close"].pct_change(5).iloc[-1] * 100)
        if gold_5d > 2.0 and spy_5d < -1.0:
            regime_votes.append(("Risk-Off", 20))
            drivers.append(f"Gold +{gold_5d:.1f}% while SPY {spy_5d:.1f}% — classic flight to safety")
        elif gold_5d < -0.5 and spy_5d > 1.0:
            regime_votes.append(("Risk-On",  15))
            drivers.append(f"Gold retreating, equities advancing — risk-on rotation")

    # ── Cross-asset correlation ───────────────────────────────────────────────
    corr_regime = cross_intel.get("correlation_regime", "normal")
    if corr_regime == "unstable":
        regime_votes.append(("Risk-Off", 20))
        drivers.append("Cross-asset correlations converging — systemic risk-off (everything moving together)")
    elif corr_regime == "diverging":
        regime_votes.append(("Transition", 12))
        drivers.append("Correlation structure in flux — potential regime transition")

    # ── SPY volume (liquidity) ────────────────────────────────────────────────
    if spy_df is not None and "Volume" in spy_df.columns and len(spy_df) >= 20:
        vol_5d  = _safe(spy_df["Volume"].tail(5).mean())
        vol_20d = _safe(spy_df["Volume"].tail(20).mean(), 1)
        vol_r   = vol_5d / vol_20d
        if vol_r < 0.55:
            regime_votes.append(("Low Liquidity", 25))
            drivers.append(f"SPY volume at {vol_r:.1f}x 20d avg — thin market, low institutional participation")

    # ── Tally votes ───────────────────────────────────────────────────────────
    vote_totals = {}
    for name, weight in regime_votes:
        vote_totals[name] = vote_totals.get(name, 0) + weight

    if vote_totals:
        winner     = max(vote_totals, key=vote_totals.get)
        total_wgt  = sum(vote_totals.values())
        confidence = min(int(vote_totals[winner] / max(total_wgt, 1) * 130), 92)
    else:
        winner, confidence = "Transition", 40

    regime_colors = {
        "Risk-On":        "#22c55e",
        "Risk-Off":       "#ef4444",
        "Transition":     "#fbbf24",
        "High Volatility":"#f97316",
        "Low Liquidity":  "#a78bfa",
    }
    result.update({
        "regime":      winner,
        "confidence":  confidence,
        "key_drivers": drivers[:5],
        "color":       regime_colors.get(winner, "#fbbf24"),
        "vote_breakdown": {k: round(v / max(sum(vote_totals.values()), 1) * 100) for k, v in vote_totals.items()},
    })

    _cross_cache["regime"] = result
    return result


# ─────────────────────────────────────────────────────────────────────────────
# LAYER 4 — Predictive Signal Engine
# ─────────────────────────────────────────────────────────────────────────────

def generate_prediction(
    ticker: str,
    smart_money: dict,
    regime: dict,
    cross_intel: dict,
    ticker_data: dict,
) -> dict:
    """
    Combine Smart Money Score, regime, cross-asset context, and technicals
    to generate a probabilistic directional forecast.

    Returns:
    {
        ticker, directional_bias ("bullish"|"bearish"|"neutral"),
        probability (35–90), timeframe ("intraday"|"swing"|"position"),
        reasoning, signal_count_bull, signal_count_bear
    }
    """
    bull, bear = 0, 0
    reasoning  = []

    # ── Smart Money ───────────────────────────────────────────────────────────
    sms = smart_money.get("score", 50)
    if sms >= 70:
        bull += 3
        reasoning.append(f"SMS {sms}/100 [{smart_money.get('grade','?')}] — strong institutional accumulation")
    elif sms >= 60:
        bull += 2
        reasoning.append(f"SMS {sms}/100 — moderate institutional accumulation bias")
    elif sms >= 52:
        bull += 1
        reasoning.append(f"SMS {sms}/100 — slight accumulation tilt")
    elif sms <= 30:
        bear += 3
        reasoning.append(f"SMS {sms}/100 [{smart_money.get('grade','?')}] — strong distribution signals")
    elif sms <= 40:
        bear += 2
        reasoning.append(f"SMS {sms}/100 — moderate distribution bias")
    elif sms <= 48:
        bear += 1
        reasoning.append(f"SMS {sms}/100 — slight distribution tilt")
    else:
        reasoning.append(f"SMS {sms}/100 — neutral institutional positioning")

    # ── Regime ────────────────────────────────────────────────────────────────
    rn   = regime.get("regime", "Transition")
    rc   = regime.get("confidence", 50)
    if rn == "Risk-On" and rc >= 65:
        bull += 2
        reasoning.append(f"Risk-On regime ({rc}% conf) — macro tailwind for risk assets")
    elif rn == "Risk-On":
        bull += 1
        reasoning.append(f"Tentative Risk-On ({rc}% conf)")
    elif rn == "Risk-Off" and rc >= 65:
        bear += 2
        reasoning.append(f"Risk-Off regime ({rc}% conf) — macro headwind, reduce risk")
    elif rn == "Risk-Off":
        bear += 1
        reasoning.append(f"Tentative Risk-Off ({rc}% conf)")
    elif rn == "High Volatility":
        bear += 1
        reasoning.append(f"High Volatility regime — binary outcomes, lower conviction")
    else:
        reasoning.append(f"{rn} — directional uncertainty elevated")

    # ── Technical signals (from existing scoring) ─────────────────────────────
    for sig_dir, sig_type, sig_text in ticker_data.get("signals", []):
        if sig_dir == "BUY":
            bull += 1
            reasoning.append(f"[{sig_type}] {sig_text}")
        elif sig_dir == "SELL":
            bear += 1
            reasoning.append(f"[{sig_type}] {sig_text}")

    # ── Cross-asset context ───────────────────────────────────────────────────
    rotation = cross_intel.get("asset_rotation", "")
    if "Safe Haven" in rotation or "→ Gold" in rotation:
        bear += 1
        reasoning.append("Capital rotating to safe havens — risk assets under pressure")
    elif "→ Equities" in rotation or "→ Tech" in rotation:
        bull += 1
        reasoning.append("Capital rotating into equities — institutional risk appetite intact")

    # ── Determine bias + probability ──────────────────────────────────────────
    total = bull + bear
    if total == 0:
        bias, prob = "neutral", 50
    else:
        bull_pct = bull / total
        if bull_pct >= 0.70:
            bias, prob = "bullish", int(50 + bull_pct * 40)
        elif bull_pct >= 0.57:
            bias, prob = "bullish", int(50 + bull_pct * 25)
        elif bull_pct <= 0.30:
            bias, prob = "bearish", int(50 + (1 - bull_pct) * 40)
        elif bull_pct <= 0.43:
            bias, prob = "bearish", int(50 + (1 - bull_pct) * 25)
        else:
            bias, prob = "neutral", 50

    prob = max(38, min(88, prob))

    # ── Timeframe ─────────────────────────────────────────────────────────────
    vix = regime.get("vix_level", 20)
    if vix > 28:
        timeframe = "intraday"
    elif abs(bull - bear) >= 4:
        timeframe = "position"
    else:
        timeframe = "swing"

    return {
        "ticker":            ticker,
        "directional_bias":  bias,
        "probability":       prob,
        "timeframe":         timeframe,
        "reasoning":         reasoning[:6],
        "signal_count_bull": bull,
        "signal_count_bear": bear,
    }


# ─────────────────────────────────────────────────────────────────────────────
# LAYER 5 — Trade Idea Generation
# ─────────────────────────────────────────────────────────────────────────────

def generate_trade_idea(
    ticker: str,
    prediction: dict,
    ticker_data: dict,
    smart_money: dict,
    confidence_threshold: float = 63.0,
) -> Optional[dict]:
    """
    Generate a concrete trade setup when signal quality crosses the threshold.
    Uses ATR for entry zones and stops; swing high/low for invalidation levels.

    Returns None if: neutral bias, low confidence, bad R/R, or insufficient data.

    Returns:
    {
        ticker, direction, setup_type, entry_zone, invalidation,
        target_levels, risk_reward, confidence, reasoning
    }
    """
    bias = prediction.get("directional_bias", "neutral")
    prob = prediction.get("probability", 50)
    sms  = smart_money.get("score", 50)

    if bias == "neutral" or prob < confidence_threshold:
        return None

    df    = ticker_data.get("df")
    price = _safe(ticker_data.get("price", 0))
    if df is None or price <= 0:
        return None

    tail     = df.tail(14)
    atr      = _safe((tail["High"] - tail["Low"]).mean(), price * 0.02)
    high_52w = _safe(ticker_data.get("week52_high", price * 1.1))
    low_52w  = _safe(ticker_data.get("week52_low",  price * 0.9))
    swing_hi = _safe(df.tail(10)["High"].max(), high_52w)
    swing_lo = _safe(df.tail(10)["Low"].min(),  low_52w)

    near_high = price >= high_52w * 0.96
    near_low  = price <= low_52w  * 1.06
    obv_acc   = smart_money.get("obv_div", 0) > 0.10
    cmf_acc   = smart_money.get("cmf",     0) > 0.05

    # Extract RSI from existing signals
    rsi_val = None
    for _, sig_type, sig_text in ticker_data.get("signals", []):
        if sig_type == "RSI" and "(" in sig_text:
            try:
                rsi_val = float(sig_text.split("(")[1].rstrip(")"))
            except Exception:
                pass

    if bias == "bullish":
        if near_high and sms >= 62:
            setup_type = "breakout"
        elif (rsi_val is not None and rsi_val < 38) or near_low:
            setup_type = "reversal"
        elif obv_acc and cmf_acc:
            setup_type = "accumulation"
        else:
            setup_type = "breakout"

        entry_low    = round(price - atr * 0.25, 2)
        entry_high   = round(price + atr * 0.25, 2)
        invalidation = round(swing_lo - atr * 0.5, 2)
        r_dist       = max(price - invalidation, atr * 0.5)
        target1      = round(price + r_dist * 1.5, 2)
        target2      = round(price + r_dist * 2.5, 2)
        target3      = round(price + r_dist * 4.0, 2)

    else:  # bearish
        setup_type   = "reversal" if near_high else "breakout"
        entry_low    = round(price - atr * 0.25, 2)
        entry_high   = round(price + atr * 0.25, 2)
        invalidation = round(swing_hi + atr * 0.5, 2)
        r_dist       = max(invalidation - price, atr * 0.5)
        target1      = round(price - r_dist * 1.5, 2)
        target2      = round(price - r_dist * 2.5, 2)
        target3      = round(price - r_dist * 4.0, 2)

    risk   = abs(price - invalidation)
    reward = abs(target2 - price)
    rr     = round(reward / max(risk, 0.01), 1)
    if rr < 1.5:
        return None

    reasoning = []
    type_labels = {
        "breakout":     "Price action near key level — breakout/breakdown setup",
        "reversal":     "Mean reversion — oversold/overbought extreme with SM confirmation",
        "accumulation": "Stealth accumulation pattern — institutional positioning detected",
    }
    reasoning.append(type_labels.get(setup_type, "Pattern detected"))
    reasoning.append(f"Smart Money Score {sms}/100 ({smart_money.get('grade','?')}) — {'accumulation' if sms > 50 else 'distribution'}")
    reasoning.append(f"Regime supports {'long' if bias == 'bullish' else 'short'} bias")
    if obv_acc:
        reasoning.append("OBV divergence confirms institutional buying pressure")
    if cmf_acc:
        reasoning.append(f"Chaikin MF {smart_money.get('cmf',0):+.3f} — sustained volume-weighted demand")

    return {
        "ticker":        ticker,
        "direction":     bias,
        "setup_type":    setup_type,
        "entry_zone":    [entry_low, entry_high],
        "invalidation":  invalidation,
        "target_levels": [target1, target2, target3],
        "risk_reward":   rr,
        "confidence":    prob,
        "reasoning":     reasoning,
    }


# ─────────────────────────────────────────────────────────────────────────────
# LAYER 6 — Learning / Adaptation
# ─────────────────────────────────────────────────────────────────────────────

def record_prediction(prediction: dict, smart_money: dict):
    """Persist a prediction to disk for later outcome evaluation."""
    entry = {
        "timestamp":   datetime.datetime.now().isoformat(),
        "ticker":      prediction["ticker"],
        "bias":        prediction["directional_bias"],
        "probability": prediction["probability"],
        "sms":         smart_money.get("score", 50),
        "outcome":     None,
    }
    try:
        history = _load_history()
        history.append(entry)
        with open(_HISTORY_FILE, "w") as f:
            json.dump(history[-500:], f, indent=2)
    except Exception:
        pass


def _load_history() -> list:
    try:
        with open(_HISTORY_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return []


def get_signal_stats() -> dict:
    """Compute accuracy stats from persisted prediction history."""
    history      = _load_history()
    with_outcome = [h for h in history if h.get("outcome") is not None]
    if not with_outcome:
        return {
            "total": len(history), "with_outcome": 0,
            "accuracy": None, "avg_probability": None, "grade": "N/A",
        }
    correct  = sum(1 for h in with_outcome if h.get("outcome") == "correct")
    accuracy = correct / len(with_outcome) * 100
    avg_prob = sum(h.get("probability", 50) for h in with_outcome) / len(with_outcome)
    return {
        "total":           len(history),
        "with_outcome":    len(with_outcome),
        "accuracy":        round(accuracy, 1),
        "avg_probability": round(avg_prob, 1),
        "grade":           "A" if accuracy >= 70 else ("B" if accuracy >= 55 else "C"),
    }


def update_outcomes(portfolio_data: dict):
    """
    Check predictions made 3–14 days ago and mark them correct/incorrect
    based on subsequent price direction. Called on every intelligence refresh.
    """
    try:
        history = _load_history()
        now     = datetime.datetime.now()
        changed = False
        for entry in history:
            if entry.get("outcome") is not None:
                continue
            try:
                ts   = datetime.datetime.fromisoformat(entry["timestamp"])
                age  = (now - ts).days
                if 3 <= age <= 14:
                    d    = portfolio_data.get(entry["ticker"], {})
                    chg  = _safe(d.get("chg_pct", 0))
                    bias = entry.get("bias", "neutral")
                    if   bias == "bullish" and chg >  0.5:
                        entry["outcome"] = "correct"; changed = True
                    elif bias == "bearish" and chg < -0.5:
                        entry["outcome"] = "correct"; changed = True
                    elif bias != "neutral" and age >= 7:
                        entry["outcome"] = "incorrect"; changed = True
            except Exception:
                continue
        if changed:
            with open(_HISTORY_FILE, "w") as f:
                json.dump(history[-500:], f, indent=2)
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────────────────────
# Master intelligence report
# ─────────────────────────────────────────────────────────────────────────────

def get_full_intelligence(tickers: list, portfolio_data: dict) -> dict:
    """
    Main entry point. Runs all 6 layers and returns a complete intelligence report.

    Returns:
    {
        regime, cross_intel, smart_money_scores, predictions,
        trade_ideas, signal_feed, signal_stats, generated_at
    }
    """
    cache_key = f"full_intel_{'_'.join(sorted(tickers))}"
    if cache_key in _intel_cache:
        return _intel_cache[cache_key]

    # Layer 2 + 3: cross-asset data → intelligence → regime
    cross_data  = get_cross_asset_data()
    cross_intel = compute_cross_asset_intelligence(cross_data)
    regime      = detect_market_regime(cross_data, cross_intel)

    # Layer 1: Smart Money Scores (lazy import to avoid circular at module level)
    from data_manager import get_options_flow as _get_opts
    smart_money_scores = {}
    for ticker in tickers:
        d   = portfolio_data.get(ticker, {})
        df  = d.get("df")
        try:
            opts = _get_opts(ticker)
        except Exception:
            opts = {}
        smart_money_scores[ticker] = compute_smart_money_score(ticker, df, opts)

    # Layer 4: Predictions
    predictions = {}
    for ticker in tickers:
        d    = portfolio_data.get(ticker, {})
        sms  = smart_money_scores.get(ticker, {})
        predictions[ticker] = generate_prediction(ticker, sms, regime, cross_intel, d)

    # Layer 5: Trade Ideas
    trade_ideas = []
    for ticker in tickers:
        d    = portfolio_data.get(ticker, {})
        pred = predictions.get(ticker, {})
        sms  = smart_money_scores.get(ticker, {})
        idea = generate_trade_idea(ticker, pred, d, sms)
        if idea:
            trade_ideas.append(idea)
    trade_ideas.sort(key=lambda x: x["confidence"], reverse=True)

    # Build signal feed
    now_str    = datetime.datetime.now().strftime("%H:%M")
    signal_feed = []

    signal_feed.append({
        "time": now_str, "type": "REGIME", "ticker": "MARKET",
        "message": f"{regime['regime']} regime — {regime['confidence']}% confidence",
        "color": regime["color"],
    })
    for sig_type, sig_cat, sig_msg in cross_intel.get("signals", [])[:3]:
        clr = "#22c55e" if sig_type in ("OK", "BUY") else ("#ef4444" if sig_type == "WARN" else "#38bdf8")
        signal_feed.append({"time": now_str, "type": sig_cat, "ticker": "CROSS-ASSET", "message": sig_msg, "color": clr})

    # Most interesting SM signals (furthest from 50 = strongest signal)
    for ticker, sms in sorted(smart_money_scores.items(), key=lambda x: abs(x[1].get("score", 50) - 50), reverse=True)[:4]:
        sc, gr = sms.get("score", 50), sms.get("grade", "C")
        if sc >= 65:
            signal_feed.append({"time": now_str, "type": "SMART MONEY", "ticker": ticker,
                                 "message": f"Accumulation detected — SMS {sc}/100 [{gr}]", "color": "#22c55e"})
        elif sc <= 35:
            signal_feed.append({"time": now_str, "type": "SMART MONEY", "ticker": ticker,
                                 "message": f"Distribution detected — SMS {sc}/100 [{gr}]", "color": "#ef4444"})

    for idea in trade_ideas[:3]:
        clr = "#22c55e" if idea["direction"] == "bullish" else "#ef4444"
        signal_feed.append({
            "time": now_str, "type": idea["setup_type"].upper(), "ticker": idea["ticker"],
            "message": f"{idea['setup_type'].capitalize()} — entry ${idea['entry_zone'][0]}–${idea['entry_zone'][1]}  R/R {idea['risk_reward']}x",
            "color": clr,
        })

    # Layer 6: update outcomes + stats
    update_outcomes(portfolio_data)
    signal_stats = get_signal_stats()

    result = {
        "regime":             regime,
        "cross_intel":        cross_intel,
        "smart_money_scores": smart_money_scores,
        "predictions":        predictions,
        "trade_ideas":        trade_ideas,
        "signal_feed":        signal_feed,
        "signal_stats":       signal_stats,
        "generated_at":       datetime.datetime.now().strftime("%H:%M:%S"),
    }
    _intel_cache[cache_key] = result
    return result


def clear_intelligence_cache():
    _cross_cache.clear()
    _intel_cache.clear()
