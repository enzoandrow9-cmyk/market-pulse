# ─────────────────────────────────────────────────────────────────────────────
# profiles.py  —  Hybrid per-user settings storage
#
# Storage priority:
#   1. Supabase  — used when SUPABASE_URL + SUPABASE_KEY are set (production)
#   2. SQLite    — automatic fallback; self-creates at startup, zero config
#
# The SQLite database is created automatically at first run.
# Location (in priority order):
#   - PROFILES_DB env var  (e.g. /data/profiles.db on Render persistent disk)
#   - ~/.marketpulse/profiles.db  (local default)
#
# No manual table creation or Supabase setup required for local development.
# ─────────────────────────────────────────────────────────────────────────────

import copy
import json
import logging
import os
import sqlite3

from config import DEFAULT_SETTINGS

logger = logging.getLogger(__name__)

# ── SQLite path ───────────────────────────────────────────────────────────────

def _sqlite_path() -> str:
    """Return the SQLite database path, creating parent dirs if needed."""
    path = os.environ.get("PROFILES_DB")
    if not path:
        home = os.path.expanduser("~")
        path = os.path.join(home, ".marketpulse", "profiles.db")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    return path


def _sqlite_conn() -> sqlite3.Connection:
    """Open (and auto-provision) the SQLite profiles database."""
    conn = sqlite3.connect(_sqlite_path(), check_same_thread=False)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS user_settings (
            username   TEXT PRIMARY KEY,
            settings   TEXT NOT NULL,
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    conn.commit()
    return conn


# ── Supabase client (lazy init) ───────────────────────────────────────────────

_supa_client = None
_supa_checked = False


def _get_supa():
    """Lazy-init Supabase client. Returns None if not configured or unavailable."""
    global _supa_client, _supa_checked
    if _supa_checked:
        return _supa_client

    _supa_checked = True
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    if not url or not key:
        logger.info("profiles: Supabase not configured — using SQLite")
        return None

    try:
        from supabase import create_client
        client = create_client(url, key)
        # Probe to confirm the table exists
        client.table("user_settings").select("username").limit(1).execute()
        _supa_client = client
        logger.info("profiles: Supabase connected")
    except Exception as e:
        logger.warning(f"profiles: Supabase unavailable ({e}) — falling back to SQLite")
        _supa_client = None

    return _supa_client


# ── Internal helpers ──────────────────────────────────────────────────────────

def _merge(saved: dict) -> dict:
    """Merge saved settings onto DEFAULT_SETTINGS so new keys always exist."""
    merged = copy.deepcopy(DEFAULT_SETTINGS)
    merged.update(saved)
    merged["indicators"] = {
        **DEFAULT_SETTINGS.get("indicators", {}),
        **saved.get("indicators", {}),
    }
    return merged


# ── Public API ────────────────────────────────────────────────────────────────

def load_settings(username: str) -> dict:
    """
    Load settings for `username`. Tries Supabase first, then SQLite.
    Returns DEFAULT_SETTINGS if no saved settings exist.
    """
    if not username:
        return copy.deepcopy(DEFAULT_SETTINGS)

    # ── Supabase ──────────────────────────────────────────────────────────────
    client = _get_supa()
    if client:
        try:
            resp = (
                client.table("user_settings")
                .select("settings")
                .eq("username", username)
                .maybe_single()
                .execute()
            )
            if resp.data and resp.data.get("settings"):
                return _merge(resp.data["settings"])
            return copy.deepcopy(DEFAULT_SETTINGS)
        except Exception as e:
            logger.warning(f"profiles: Supabase load failed ({e}) — trying SQLite")

    # ── SQLite fallback ───────────────────────────────────────────────────────
    try:
        conn = _sqlite_conn()
        row = conn.execute(
            "SELECT settings FROM user_settings WHERE username = ?", (username,)
        ).fetchone()
        conn.close()
        if row:
            return _merge(json.loads(row[0]))
    except Exception as e:
        logger.warning(f"profiles: SQLite load failed: {e}")

    return copy.deepcopy(DEFAULT_SETTINGS)


def save_settings(username: str, settings: dict) -> bool:
    """
    Upsert settings for `username`. Tries Supabase first, then SQLite.
    Returns True on success.
    """
    if not username:
        return False

    # ── Supabase ──────────────────────────────────────────────────────────────
    client = _get_supa()
    if client:
        try:
            client.table("user_settings").upsert({
                "username":   username,
                "settings":   settings,
                "updated_at": "now()",
            }).execute()
            return True
        except Exception as e:
            logger.warning(f"profiles: Supabase save failed ({e}) — trying SQLite")

    # ── SQLite fallback ───────────────────────────────────────────────────────
    try:
        conn = _sqlite_conn()
        conn.execute(
            """
            INSERT INTO user_settings (username, settings, updated_at)
            VALUES (?, ?, datetime('now'))
            ON CONFLICT(username) DO UPDATE SET
                settings   = excluded.settings,
                updated_at = excluded.updated_at
            """,
            (username, json.dumps(settings)),
        )
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.warning(f"profiles: SQLite save failed: {e}")
        return False


def get_username_from_request():
    """
    Extract the authenticated username from the current Flask request.
    Returns None if not authenticated or running locally without auth.
    """
    try:
        from flask import request
        auth = request.authorization
        if auth and auth.username:
            return auth.username
    except Exception:
        pass
    return None
