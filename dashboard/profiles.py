# ─────────────────────────────────────────────────────────────────────────────
# profiles.py  —  Supabase-backed per-user settings storage
#
# Each user's settings are stored as a JSONB row in the `user_settings` table:
#   username TEXT PRIMARY KEY
#   settings JSONB
#   updated_at TIMESTAMPTZ
#
# Falls back gracefully if Supabase env vars are not set (e.g. local dev).
# ─────────────────────────────────────────────────────────────────────────────

import os
import copy
import logging

from config import DEFAULT_SETTINGS

logger = logging.getLogger(__name__)

# ── Supabase client (lazy init) ───────────────────────────────────────────────

_client = None

def _get_client():
    global _client
    if _client is not None:
        return _client

    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    if not url or not key:
        return None

    try:
        from supabase import create_client
        _client = create_client(url, key)
        logger.info("Supabase client initialised")
    except Exception as e:
        logger.warning(f"Supabase init failed: {e}")
        _client = None

    return _client


# ── Public API ────────────────────────────────────────────────────────────────

def load_settings(username: str) -> dict:
    """
    Load settings for `username` from Supabase.
    Returns DEFAULT_SETTINGS if the user has no saved settings or Supabase
    is unavailable.
    """
    client = _get_client()
    if not client or not username:
        return copy.deepcopy(DEFAULT_SETTINGS)

    try:
        resp = (
            client.table("user_settings")
            .select("settings")
            .eq("username", username)
            .maybe_single()
            .execute()
        )
        if resp.data and resp.data.get("settings"):
            # Merge with defaults so new keys added after account creation exist
            merged = copy.deepcopy(DEFAULT_SETTINGS)
            merged.update(resp.data["settings"])
            # Ensure indicators dict is also fully merged
            merged["indicators"] = {
                **DEFAULT_SETTINGS.get("indicators", {}),
                **resp.data["settings"].get("indicators", {}),
            }
            return merged
    except Exception as e:
        logger.warning(f"Failed to load settings for {username}: {e}")

    return copy.deepcopy(DEFAULT_SETTINGS)


def save_settings(username: str, settings: dict) -> bool:
    """
    Upsert settings for `username` into Supabase.
    Returns True on success, False on failure.
    """
    client = _get_client()
    if not client or not username:
        return False

    try:
        client.table("user_settings").upsert({
            "username": username,
            "settings": settings,
            "updated_at": "now()",
        }).execute()
        return True
    except Exception as e:
        logger.warning(f"Failed to save settings for {username}: {e}")
        return False


def get_username_from_request() -> str | None:
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
