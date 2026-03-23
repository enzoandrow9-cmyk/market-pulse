# ─────────────────────────────────────────────────────────────────────────────
# alert_engine.py  —  Bloomberg Terminal Dashboard  •  Enzo Market Pulse
#
# Server-side persistent alert evaluation engine.
#
# Alert types:
#   • above       — price crosses above threshold
#   • below       — price crosses below threshold
#   • pct_change  — absolute 1-day % change exceeds threshold
#   • volume      — volume ratio vs 20-day avg exceeds threshold
#
# Notification channels:
#   • Email  — via smtplib (SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS env vars)
#   • Webhook — POST to a Discord/Slack/custom URL (ALERT_WEBHOOK_URL env var)
#
# Storage:
#   • Primary   — Supabase `alerts` table (if SUPABASE_URL + SUPABASE_KEY set)
#   • Fallback  — in-memory list (survives server restart only if stored in dcc.Store)
#
# Background thread evaluates all active alerts every 60 seconds.
# ─────────────────────────────────────────────────────────────────────────────

from __future__ import annotations

import datetime
import logging
import os
import smtplib
import threading
import time
import uuid
from email.mime.text import MIMEText
from typing import Any, Dict, List, Optional

import requests
import yfinance as yf
from cachetools import TTLCache

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

EVAL_INTERVAL_SECONDS = 60   # background evaluation cadence
_COOLDOWN_SECONDS     = 3600 # minimum seconds between repeated triggers for the same alert

# ─────────────────────────────────────────────────────────────────────────────
# In-memory stores (fallback when Supabase is not available)
# ─────────────────────────────────────────────────────────────────────────────

_alerts_lock:   threading.Lock = threading.Lock()
_alerts:        List[Dict]     = []          # list of alert rule dicts
_trigger_log:   List[Dict]     = []          # history of triggered alerts
_cooldown_map:  Dict[str, float] = {}        # alert_id → last triggered timestamp

# ─────────────────────────────────────────────────────────────────────────────
# Price cache (reuse across evaluations)
# ─────────────────────────────────────────────────────────────────────────────

_price_cache: TTLCache = TTLCache(maxsize=100, ttl=60)   # 1-min price TTL


# ─────────────────────────────────────────────────────────────────────────────
# Supabase helpers
# ─────────────────────────────────────────────────────────────────────────────

_supa_client = None

def _get_supa():
    """Lazy-init Supabase client. Returns None if not configured."""
    global _supa_client
    if _supa_client is not None:
        return _supa_client
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    if not url or not key:
        return None
    try:
        from supabase import create_client
        _supa_client = create_client(url, key)
    except Exception as exc:
        logger.warning("alert_engine: Supabase init failed — %s", exc)
    return _supa_client


def _load_alerts_from_supabase() -> List[Dict]:
    """Load active alert rules from Supabase."""
    client = _get_supa()
    if client is None:
        return []
    try:
        resp = client.table("alerts").select("*").eq("active", True).execute()
        return resp.data or []
    except Exception as exc:
        logger.warning("alert_engine: failed to load alerts from Supabase — %s", exc)
        return []


def _save_alert_to_supabase(alert: Dict) -> bool:
    """Upsert an alert rule into Supabase. Returns True on success."""
    client = _get_supa()
    if client is None:
        return False
    try:
        client.table("alerts").upsert(alert).execute()
        return True
    except Exception as exc:
        logger.warning("alert_engine: failed to save alert — %s", exc)
        return False


def _log_trigger_to_supabase(trigger: Dict) -> None:
    """Write a trigger event to the alert_triggers table."""
    client = _get_supa()
    if client is None:
        return
    try:
        client.table("alert_triggers").insert(trigger).execute()
    except Exception as exc:
        logger.debug("alert_engine: trigger log failed — %s", exc)


# ─────────────────────────────────────────────────────────────────────────────
# Alert CRUD
# ─────────────────────────────────────────────────────────────────────────────

def create_alert(
    ticker:    str,
    alert_type: str,
    threshold: float,
    label:     str = "",
    email:     Optional[str] = None,
    webhook:   Optional[str] = None,
) -> Dict:
    """
    Create and register a new alert rule.

    Parameters
    ----------
    ticker      : Ticker symbol (e.g. 'AAPL').
    alert_type  : One of 'above', 'below', 'pct_change', 'volume'.
    threshold   : Numeric threshold value.
    label       : Optional human-readable name.
    email       : Optional override email address for this alert.
    webhook     : Optional override webhook URL for this alert.

    Returns
    -------
    The new alert dict (includes generated id).
    """
    alert: Dict[str, Any] = {
        "id":         str(uuid.uuid4()),
        "ticker":     ticker.upper().strip(),
        "type":       alert_type,
        "threshold":  float(threshold),
        "label":      label or f"{ticker} {alert_type} {threshold}",
        "active":     True,
        "email":      email,
        "webhook":    webhook,
        "created_at": datetime.datetime.utcnow().isoformat(),
    }

    with _alerts_lock:
        _alerts.append(alert)

    _save_alert_to_supabase(alert)
    logger.info("alert_engine: created alert %s — %s %s %.4f", alert["id"],
                ticker, alert_type, threshold)
    return alert


def delete_alert(alert_id: str) -> bool:
    """Deactivate an alert by id. Returns True if found."""
    with _alerts_lock:
        for a in _alerts:
            if a["id"] == alert_id:
                a["active"] = False
                _save_alert_to_supabase(a)
                return True
    return False


def get_all_alerts() -> List[Dict]:
    """Return all currently active alert rules."""
    with _alerts_lock:
        return [a for a in _alerts if a.get("active", True)]


def get_trigger_log(limit: int = 50) -> List[Dict]:
    """Return recent trigger events (most recent first)."""
    return list(reversed(_trigger_log[-limit:]))


def sync_alerts_from_settings(settings_alerts: List[Dict]) -> None:
    """
    Merge alert rules from the user-settings dcc.Store into the engine.
    Called on startup / when settings change.
    """
    with _alerts_lock:
        existing_ids = {a["id"] for a in _alerts}
        for sa in settings_alerts:
            if sa.get("id") and sa["id"] not in existing_ids and sa.get("active", True):
                _alerts.append(sa)


# ─────────────────────────────────────────────────────────────────────────────
# Price helpers
# ─────────────────────────────────────────────────────────────────────────────

def _get_current_price(ticker: str) -> Optional[Dict]:
    """
    Return {'price': float, 'chg_pct': float, 'volume': int} for *ticker*.
    Cached 60 seconds.
    """
    if ticker in _price_cache:
        return _price_cache[ticker]
    try:
        tk = yf.Ticker(ticker)
        df = tk.history(period="5d", interval="1d", auto_adjust=True)
        if df is None or len(df) < 2:
            return None
        price     = float(df["Close"].iloc[-1])
        prev      = float(df["Close"].iloc[-2])
        chg_pct   = (price - prev) / prev * 100 if prev else 0.0
        volume    = int(df["Volume"].iloc[-1]) if "Volume" in df.columns else 0
        avg_vol20 = float(df["Volume"].iloc[-21:-1].mean()) if len(df) >= 21 else volume
        vol_ratio = volume / avg_vol20 if avg_vol20 > 0 else 1.0
        result    = {"price": price, "chg_pct": chg_pct, "volume": volume, "vol_ratio": vol_ratio}
        _price_cache[ticker] = result
        return result
    except Exception as exc:
        logger.debug("alert_engine: price fetch failed %s — %s", ticker, exc)
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Alert evaluation
# ─────────────────────────────────────────────────────────────────────────────

def _is_triggered(alert: Dict, market: Dict) -> bool:
    """Check if *alert* condition is satisfied given *market* data dict."""
    atype = alert.get("type", "")
    thr   = float(alert.get("threshold", 0))

    if atype == "above":
        return market["price"] >= thr
    if atype == "below":
        return market["price"] <= thr
    if atype == "pct_change":
        return abs(market["chg_pct"]) >= thr
    if atype == "volume":
        return market.get("vol_ratio", 1.0) >= thr
    return False


def _in_cooldown(alert_id: str) -> bool:
    """Return True if this alert fired too recently."""
    last = _cooldown_map.get(alert_id)
    if last is None:
        return False
    return (time.time() - last) < _COOLDOWN_SECONDS


# ─────────────────────────────────────────────────────────────────────────────
# Notification dispatch
# ─────────────────────────────────────────────────────────────────────────────

def _send_email(to_addr: str, subject: str, body: str) -> None:
    """Send an alert email via SMTP (env-var configured)."""
    host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    port = int(os.environ.get("SMTP_PORT", "587"))
    user = os.environ.get("SMTP_USER", "")
    pwd  = os.environ.get("SMTP_PASS", "")
    if not user or not pwd:
        logger.debug("alert_engine: SMTP not configured — skipping email")
        return
    try:
        msg           = MIMEText(body)
        msg["Subject"] = subject
        msg["From"]    = user
        msg["To"]      = to_addr
        with smtplib.SMTP(host, port, timeout=10) as srv:
            srv.ehlo()
            srv.starttls()
            srv.login(user, pwd)
            srv.sendmail(user, [to_addr], msg.as_string())
        logger.info("alert_engine: email sent to %s — %s", to_addr, subject)
    except Exception as exc:
        logger.warning("alert_engine: email failed — %s", exc)


def _send_webhook(url: str, payload: Dict) -> None:
    """POST alert payload to a Discord/Slack/custom webhook URL."""
    try:
        # Discord / Slack both accept {"content": "..."} or {"text": "..."}
        discord_body = {"content": payload.get("message", str(payload))}
        requests.post(url, json=discord_body, timeout=8)
        logger.info("alert_engine: webhook dispatched to %s", url[:40])
    except Exception as exc:
        logger.warning("alert_engine: webhook failed — %s", exc)


def _dispatch_notification(alert: Dict, market: Dict) -> None:
    """Build and send all configured notifications for a triggered alert."""
    ticker  = alert.get("ticker", "")
    atype   = alert.get("type", "")
    thr     = alert.get("threshold", 0)
    price   = market.get("price", 0)
    chg_pct = market.get("chg_pct", 0)
    sign    = "+" if chg_pct >= 0 else ""

    message = (
        f"MARKET PULSE ALERT\n"
        f"Ticker:    {ticker}\n"
        f"Condition: {atype} {thr}\n"
        f"Price:     ${price:,.4f}\n"
        f"Change:    {sign}{chg_pct:.2f}%\n"
        f"Time:      {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )

    # 1. Email
    email_to = alert.get("email") or os.environ.get("ALERT_EMAIL_TO", "")
    if email_to:
        _send_email(email_to, f"Alert: {ticker} {atype}", message)

    # 2. Webhook (per-alert override → global env)
    webhook_url = alert.get("webhook") or os.environ.get("ALERT_WEBHOOK_URL", "")
    if webhook_url:
        _send_webhook(webhook_url, {"message": message, "ticker": ticker,
                                     "type": atype, "price": price})


# ─────────────────────────────────────────────────────────────────────────────
# Main evaluation pass
# ─────────────────────────────────────────────────────────────────────────────

def evaluate_all_alerts() -> List[Dict]:
    """
    Evaluate all active alert rules against current market prices.

    Returns list of triggered alert dicts from this evaluation pass.
    """
    with _alerts_lock:
        active = [a for a in _alerts if a.get("active", True)]

    if not active:
        return []

    # Collect unique tickers
    tickers = list({a["ticker"] for a in active})

    # Fetch prices (could be parallel but keep simple — 60s interval is enough)
    market_map: Dict[str, Dict] = {}
    for t in tickers:
        data = _get_current_price(t)
        if data:
            market_map[t] = data

    triggered_this_pass: List[Dict] = []

    for alert in active:
        ticker = alert["ticker"]
        mkt    = market_map.get(ticker)
        if mkt is None:
            continue
        if _in_cooldown(alert["id"]):
            continue
        if _is_triggered(alert, mkt):
            event = {
                "alert_id":    alert["id"],
                "ticker":      ticker,
                "type":        alert["type"],
                "threshold":   alert["threshold"],
                "price":       mkt["price"],
                "chg_pct":     mkt["chg_pct"],
                "triggered_at": datetime.datetime.utcnow().isoformat(),
            }
            triggered_this_pass.append(event)
            _trigger_log.append(event)
            _cooldown_map[alert["id"]] = time.time()
            _log_trigger_to_supabase(event)
            _dispatch_notification(alert, mkt)
            logger.info("alert_engine: triggered — %s %s @ %.4f",
                        ticker, alert["type"], mkt["price"])

    return triggered_this_pass


# ─────────────────────────────────────────────────────────────────────────────
# Background worker thread
# ─────────────────────────────────────────────────────────────────────────────

_alert_thread: Optional[threading.Thread] = None


def _worker_loop() -> None:
    """Evaluate alerts every EVAL_INTERVAL_SECONDS."""
    # Load persisted alerts from Supabase on first run
    supa_alerts = _load_alerts_from_supabase()
    with _alerts_lock:
        existing_ids = {a["id"] for a in _alerts}
        for sa in supa_alerts:
            if sa.get("id") not in existing_ids:
                _alerts.append(sa)

    while True:
        try:
            evaluate_all_alerts()
        except Exception as exc:
            logger.exception("alert_engine: evaluation loop error — %s", exc)
        time.sleep(EVAL_INTERVAL_SECONDS)


def start_alert_engine() -> None:
    """
    Start the background alert evaluation daemon (idempotent).
    Safe to call from main.py at startup.
    """
    global _alert_thread
    if _alert_thread is not None and _alert_thread.is_alive():
        return

    _alert_thread = threading.Thread(
        target=_worker_loop,
        daemon=True,
        name="alert-engine",
    )
    _alert_thread.start()
    logger.info("alert_engine: started (eval interval=%ds)", EVAL_INTERVAL_SECONDS)
