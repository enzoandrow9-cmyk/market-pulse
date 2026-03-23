# ─────────────────────────────────────────────────────────────────────────────
# realtime_data.py  —  Bloomberg Terminal Dashboard  •  Enzo Market Pulse
#
# Real-time market data layer with WebSocket streaming + polling fallback.
#
# Primary provider: Alpaca Markets WebSocket API (free tier, paper trading)
#   Env vars required: ALPACA_API_KEY, ALPACA_API_SECRET
#   WebSocket URL:     wss://stream.data.alpaca.markets/v2/iex
#
# Fallback: yfinance polling every POLL_INTERVAL_SECONDS
#
# Architecture:
#   - Module-level _tick_store dict holds the latest tick for each symbol
#   - WebSocket thread updates _tick_store when connected
#   - Polling thread updates _tick_store when WebSocket is unavailable
#   - Dash callbacks read from get_tick() / get_ticks() — never block
# ─────────────────────────────────────────────────────────────────────────────

from __future__ import annotations

import logging
import os
import threading
import time
from typing import Dict, List, Optional

import yfinance as yf

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

POLL_INTERVAL_SECONDS = 30        # fallback polling cadence
_WS_RECONNECT_DELAY   = 15        # seconds before WS reconnect attempt
_ALPACA_WS_URL        = "wss://stream.data.alpaca.markets/v2/iex"

# ─────────────────────────────────────────────────────────────────────────────
# Tick store  {symbol → tick_dict}
# ─────────────────────────────────────────────────────────────────────────────

_tick_lock:  threading.Lock = threading.Lock()
_tick_store: Dict[str, Dict] = {}

_subscribed_symbols: List[str] = []
_ws_connected        = threading.Event()   # set when WS is alive
_polling_thread:  Optional[threading.Thread] = None
_ws_thread:       Optional[threading.Thread] = None


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def get_tick(symbol: str) -> Optional[Dict]:
    """
    Return the latest tick for *symbol* or None if not available.

    Returns
    -------
    dict with keys: symbol, price, bid, ask, volume, timestamp
    """
    with _tick_lock:
        return _tick_store.get(symbol.upper())


def get_ticks(symbols: Optional[List[str]] = None) -> Dict[str, Dict]:
    """
    Return a snapshot of the tick store for *symbols* (all if None).
    """
    with _tick_lock:
        if symbols is None:
            return dict(_tick_store)
        return {s.upper(): _tick_store[s.upper()] for s in symbols if s.upper() in _tick_store}


def is_streaming() -> bool:
    """Return True if the WebSocket connection is currently active."""
    return _ws_connected.is_set()


def subscribe(symbols: List[str]) -> None:
    """Add *symbols* to the subscription list (takes effect on next WS cycle)."""
    upper = [s.upper() for s in symbols]
    for sym in upper:
        if sym not in _subscribed_symbols:
            _subscribed_symbols.append(sym)


# ─────────────────────────────────────────────────────────────────────────────
# Tick update helper
# ─────────────────────────────────────────────────────────────────────────────

def _update_tick(symbol: str, price: float, bid: float = 0.0, ask: float = 0.0,
                  volume: int = 0, timestamp: str = "") -> None:
    import datetime
    ts = timestamp or datetime.datetime.utcnow().isoformat()
    with _tick_lock:
        _tick_store[symbol.upper()] = {
            "symbol":    symbol.upper(),
            "price":     price,
            "bid":       bid,
            "ask":       ask,
            "volume":    volume,
            "timestamp": ts,
        }


# ─────────────────────────────────────────────────────────────────────────────
# WebSocket thread (Alpaca)
# ─────────────────────────────────────────────────────────────────────────────

def _ws_worker() -> None:
    """
    Connect to Alpaca IEX WebSocket stream and pipe ticks into _tick_store.
    Reconnects automatically on disconnect.
    Silently exits if websocket-client is not installed.
    """
    try:
        import websocket  # type: ignore
        import json
    except ImportError:
        logger.info("realtime_data: websocket-client not installed — WS disabled")
        return

    api_key    = os.environ.get("ALPACA_API_KEY", "")
    api_secret = os.environ.get("ALPACA_API_SECRET", "")
    if not api_key or not api_secret:
        logger.info("realtime_data: ALPACA_API_KEY/SECRET not set — WS disabled")
        return

    def _on_message(ws, raw_msg):
        try:
            msgs = json.loads(raw_msg)
            if not isinstance(msgs, list):
                msgs = [msgs]
            for msg in msgs:
                msg_type = msg.get("T")
                if msg_type == "t":   # trade tick
                    _update_tick(
                        symbol    = msg.get("S", ""),
                        price     = float(msg.get("p", 0)),
                        volume    = int(msg.get("s", 0)),
                        timestamp = msg.get("t", ""),
                    )
                elif msg_type == "q":  # quote
                    sym = msg.get("S", "")
                    existing = _tick_store.get(sym, {})
                    _update_tick(
                        symbol    = sym,
                        price     = existing.get("price", 0.0),
                        bid       = float(msg.get("bp", 0)),
                        ask       = float(msg.get("ap", 0)),
                        volume    = existing.get("volume", 0),
                        timestamp = msg.get("t", ""),
                    )
                elif msg_type == "connected":
                    # Authenticate immediately after connecting
                    ws.send(json.dumps({"action": "auth", "key": api_key, "secret": api_secret}))
                elif msg_type == "authenticated":
                    _ws_connected.set()
                    # Subscribe to ticks for all registered symbols
                    syms = [s for s in _subscribed_symbols if not s.startswith("^") and "=F" not in s]
                    if syms:
                        ws.send(json.dumps({"action": "subscribe", "trades": syms, "quotes": syms}))
                    logger.info("realtime_data: Alpaca WS authenticated, subscribed to %d symbols", len(syms))
        except Exception as exc:
            logger.debug("realtime_data: WS message parse error — %s", exc)

    def _on_error(ws, err):
        logger.warning("realtime_data: WS error — %s", err)

    def _on_close(ws, code, msg):
        _ws_connected.clear()
        logger.info("realtime_data: WS closed (code=%s)", code)

    def _on_open(ws):
        logger.info("realtime_data: WS connection opened")

    while True:
        try:
            ws = websocket.WebSocketApp(
                _ALPACA_WS_URL,
                on_open    = _on_open,
                on_message = _on_message,
                on_error   = _on_error,
                on_close   = _on_close,
            )
            ws.run_forever(ping_interval=20, ping_timeout=10)
        except Exception as exc:
            logger.warning("realtime_data: WS loop exception — %s", exc)
        finally:
            _ws_connected.clear()

        logger.info("realtime_data: reconnecting WS in %ds…", _WS_RECONNECT_DELAY)
        time.sleep(_WS_RECONNECT_DELAY)


# ─────────────────────────────────────────────────────────────────────────────
# Polling fallback thread
# ─────────────────────────────────────────────────────────────────────────────

def _polling_worker() -> None:
    """
    Poll yfinance every POLL_INTERVAL_SECONDS for all subscribed symbols.
    Only active when the WebSocket is NOT connected.
    """
    while True:
        if not _ws_connected.is_set() and _subscribed_symbols:
            _poll_once()
        time.sleep(POLL_INTERVAL_SECONDS)


def _poll_once() -> None:
    """One polling pass — fetch latest prices for all subscribed symbols."""
    syms = list(_subscribed_symbols)
    if not syms:
        return
    try:
        # Batch download is more efficient than individual calls
        batch = yf.download(syms, period="2d", interval="1d",
                             auto_adjust=True, progress=False, threads=True)
        if batch.empty:
            return

        # yfinance returns multi-level columns for multiple tickers
        if isinstance(batch.columns, type(batch.columns)) and hasattr(batch.columns, "levels"):
            for sym in syms:
                try:
                    close_col = ("Close", sym)
                    vol_col   = ("Volume", sym)
                    if close_col not in batch.columns:
                        continue
                    closes = batch[close_col].dropna()
                    if len(closes) < 1:
                        continue
                    price  = float(closes.iloc[-1])
                    volume = int(batch[vol_col].dropna().iloc[-1]) if vol_col in batch.columns else 0
                    _update_tick(sym, price, volume=volume)
                except Exception:
                    pass
        else:
            # Single ticker — flat columns
            sym = syms[0]
            closes = batch["Close"].dropna() if "Close" in batch.columns else None
            if closes is not None and len(closes):
                price  = float(closes.iloc[-1])
                volume = int(batch["Volume"].dropna().iloc[-1]) if "Volume" in batch.columns else 0
                _update_tick(sym, price, volume=volume)

    except Exception as exc:
        logger.debug("realtime_data: polling error — %s", exc)


# ─────────────────────────────────────────────────────────────────────────────
# Startup
# ─────────────────────────────────────────────────────────────────────────────

def start_realtime_layer(symbols: Optional[List[str]] = None) -> None:
    """
    Initialise the real-time data layer (idempotent).

    1. Subscribe *symbols* to both WS and polling feeds.
    2. Start WebSocket thread (connects only if ALPACA keys are set).
    3. Start polling fallback thread (always active as backup).

    Parameters
    ----------
    symbols : list, optional
        Initial set of symbols to track (e.g. portfolio tickers + index symbols).
    """
    global _polling_thread, _ws_thread

    if symbols:
        subscribe(symbols)

    # WebSocket thread (disabled gracefully if keys or package absent)
    if _ws_thread is None or not _ws_thread.is_alive():
        _ws_thread = threading.Thread(
            target=_ws_worker,
            daemon=True,
            name="realtime-ws",
        )
        _ws_thread.start()

    # Polling fallback thread
    if _polling_thread is None or not _polling_thread.is_alive():
        _polling_thread = threading.Thread(
            target=_polling_worker,
            daemon=True,
            name="realtime-poll",
        )
        _polling_thread.start()

    logger.info("realtime_data: layer started (symbols=%d, ws=%s)",
                len(_subscribed_symbols), "alpaca" if os.environ.get("ALPACA_API_KEY") else "disabled")
