# ─────────────────────────────────────────────────────────────────────────────
# auth.py  —  Bloomberg Terminal Dashboard  •  Enzo Market Pulse
#
# Full authentication module:
#   • Supabase Auth  (bcrypt passwords, email verification, JWT)
#   • Flask sessions (signed, httponly, samesite=Strict, 8-hour TTL)
#   • CSRF protection  (cryptographic token in session, constant-time compare)
#   • Rate limiting    (Flask-Limiter: 10/min login, 5/min register)
#   • Account lockout  (5 failures → 30-min cooldown, in-memory per worker)
#   • Security headers (CSP, X-Frame-Options, Referrer-Policy, etc.)
#   • Audit logging    (stdout + optional Supabase login_events table)
#   • Password-reset   (Supabase sends email with reset link)
#
# Exposes:
#   init_auth(flask_app)  — call once after app creation in main.py
#   get_current_user()    — returns email string or None
# ─────────────────────────────────────────────────────────────────────────────

from __future__ import annotations

import logging
import os
import re
import secrets
from datetime import datetime, timedelta
from typing import Optional

from flask import (
    Blueprint, jsonify, redirect,
    render_template_string, request, session,
)

logger = logging.getLogger(__name__)

# ─── Rate limiter (built-in, no external dependency) ─────────────────────────
import time
from collections import defaultdict
from functools import wraps

_rl_store: dict = defaultdict(list)


def _rate_limit(max_calls: int, window_seconds: int):
    """Sliding-window in-memory rate limiter decorator."""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            key = f"{f.__name__}:{request.remote_addr}"
            now = time.time()
            cutoff = now - window_seconds
            _rl_store[key] = [t for t in _rl_store[key] if t > cutoff]
            if len(_rl_store[key]) >= max_calls:
                return "Too many requests — slow down.", 429
            _rl_store[key].append(now)
            return f(*args, **kwargs)
        return wrapper
    return decorator

# ─── Blueprint ────────────────────────────────────────────────────────────────
auth_bp = Blueprint("auth", __name__)

# ─── Paths exempt from the auth gate ─────────────────────────────────────────
_PUBLIC_EXACT = {"/login", "/register", "/logout", "/forgot-password", "/auth/callback"}
_PUBLIC_PREFIX = (
    "/_dash-component-suites/",
    "/assets/",
    "/_favicon",
)

# ─── Validation patterns ──────────────────────────────────────────────────────
_EMAIL_RE = re.compile(
    r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$"
)
# ≥8 chars, at least one lower, upper, digit, and special character
_PW_RE = re.compile(
    r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)"
    r"(?=.*[!@#$%^&*()\-_=+\[\]{};:'\",.<>/?\\|`~]).{8,72}$"
)

# ─── CSRF ─────────────────────────────────────────────────────────────────────

def _csrf_token() -> str:
    """Return (creating if absent) a 64-hex CSRF token stored in the session."""
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(32)
    return session["csrf_token"]


def _csrf_valid(submitted: Optional[str]) -> bool:
    """Constant-time comparison against session CSRF token."""
    expected = session.get("csrf_token", "")
    if not submitted or not expected:
        return False
    return secrets.compare_digest(submitted.encode(), expected.encode())


# ─── Account lockout (in-memory) ──────────────────────────────────────────────
_failures: dict[str, list[datetime]] = {}
_LOCK_THRESHOLD = 5               # failures before lockout
_LOCK_RELEASE   = timedelta(minutes=30)


def _is_locked(email: str) -> bool:
    now    = datetime.utcnow()
    recent = [t for t in _failures.get(email, []) if now - t < _LOCK_RELEASE]
    _failures[email] = recent
    return len(recent) >= _LOCK_THRESHOLD


def _record_failure(email: str) -> None:
    _failures.setdefault(email, []).append(datetime.utcnow())


def _clear_failures(email: str) -> None:
    _failures.pop(email, None)


# ─── Supabase auth client (lazy) ──────────────────────────────────────────────
_supa: Optional[object] = None
_supa_ready = False


def _get_supa():
    global _supa, _supa_ready
    if _supa_ready:
        return _supa
    _supa_ready = True
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    if not (url and key):
        logger.warning("auth: SUPABASE_URL/KEY not configured — auth disabled")
        return None
    try:
        from supabase import create_client
        _supa = create_client(url, key)
        logger.info("auth: Supabase client ready")
    except Exception as exc:
        logger.error(f"auth: Supabase init failed: {exc}")
    return _supa


# ─── Audit log helper ─────────────────────────────────────────────────────────

def _audit(event: str, email: str, ok: bool) -> None:
    """Log auth event to stdout (always) and Supabase login_events (if table exists)."""
    ip = request.remote_addr or "unknown"
    logger.info(f"auth_event event={event} ok={ok} email={email} ip={ip}")
    supa = _get_supa()
    if not supa:
        return
    try:
        supa.table("login_events").insert({
            "event":      event,
            "email":      email,
            "ip_address": ip,
            "success":    ok,
            "created_at": datetime.utcnow().isoformat(),
        }).execute()
    except Exception:
        pass  # table may not exist yet; stdout log is sufficient


# ─── Security headers ─────────────────────────────────────────────────────────
_SEC_HEADERS: dict[str, str] = {
    "X-Content-Type-Options":  "nosniff",
    "X-Frame-Options":         "DENY",
    "X-XSS-Protection":        "1; mode=block",
    "Referrer-Policy":         "strict-origin-when-cross-origin",
    "Permissions-Policy":      "geolocation=(), microphone=(), camera=()",
    # Generous CSP — Dash needs unsafe-inline for its injected scripts/styles
    "Content-Security-Policy": (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdn.plot.ly "
        "https://cdnjs.cloudflare.com; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com data:; "
        "img-src 'self' data: https:; "
        "connect-src 'self' https://*.supabase.co;"
    ),
}


# ─── Public helper ────────────────────────────────────────────────────────────

def get_current_user() -> Optional[str]:
    """Return the logged-in user's email, or None."""
    try:
        return session.get("user_email") or None
    except Exception:
        return None


# ─── init_auth ────────────────────────────────────────────────────────────────

def init_auth(app) -> None:
    """
    Attach authentication to the Flask/Dash app.
    Call once in main.py immediately after `server = app.server`.
    """
    app.register_blueprint(auth_bp)

    is_prod = os.environ.get("PRODUCTION", "").lower() in ("1", "true", "yes")

    app.config.update(
        SESSION_COOKIE_NAME      = "mps",
        SESSION_COOKIE_HTTPONLY  = True,
        SESSION_COOKIE_SECURE    = is_prod,   # True in prod (HTTPS only)
        SESSION_COOKIE_SAMESITE  = "Strict",
        PERMANENT_SESSION_LIFETIME = timedelta(hours=8),
    )

    # ── Request gate: require login for everything except public paths ─────────
    @app.before_request
    def _auth_gate():
        path = request.path
        if path in _PUBLIC_EXACT:
            return None
        if any(path.startswith(p) for p in _PUBLIC_PREFIX):
            return None
        if not session.get("user_email"):
            # Dash XHR / JSON requests → 401 (Dash will surface a generic error)
            if (path.startswith("/_dash") or
                    "application/json" in request.headers.get("Accept", "")):
                return jsonify({"error": "Authentication required"}), 401
            return redirect("/login")
        return None

    # ── Attach security headers to every response ─────────────────────────────
    @app.after_request
    def _security_headers(response):
        for key, val in _SEC_HEADERS.items():
            response.headers.setdefault(key, val)
        return response


# ─── HTML login/register page ─────────────────────────────────────────────────

_PAGE_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="robots" content="noindex,nofollow">
  <title>Market Pulse Terminal — Auth</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@300;400;600;700&display=swap" rel="stylesheet">
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    :root {
      --bg:       #060b19;
      --panel:    #0d1526;
      --input-bg: #0a1020;
      --border:   #1e2d4a;
      --accent:   #fbbf24;
      --text:     #e2e8f0;
      --dim:      #4a6080;
      --secondary:#94a3b8;
      --green:    #22c55e;
      --red:      #f87171;
      --orange:   #fb923c;
      --font:     'IBM Plex Mono', 'Courier New', monospace;
    }
    body {
      background: var(--bg);
      color: var(--text);
      font-family: var(--font);
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 24px;
    }
    /* ── Header ──────────────────────────────────────────────────────────── */
    .hdr { text-align: center; margin-bottom: 28px; }
    .hdr-logo {
      color: var(--accent);
      font-size: 12px; font-weight: 700;
      letter-spacing: .20em; text-transform: uppercase; margin-bottom: 6px;
    }
    .hdr-sub {
      color: var(--dim);
      font-size: 9px; letter-spacing: .15em; text-transform: uppercase;
    }
    /* ── Card ────────────────────────────────────────────────────────────── */
    .card {
      background: var(--panel);
      border: 1px solid var(--accent);
      border-radius: 6px;
      width: 100%; max-width: 420px;
      box-shadow: 0 24px 80px rgba(0,0,0,.65);
      overflow: hidden;
    }
    /* ── Tab bar ─────────────────────────────────────────────────────────── */
    .tabs { display: flex; border-bottom: 1px solid var(--border); }
    .tab {
      flex: 1;
      background: transparent; border: none;
      color: var(--dim);
      font-family: var(--font); font-size: 10px; font-weight: 700;
      letter-spacing: .12em; text-transform: uppercase;
      padding: 14px; cursor: pointer;
      border-bottom: 2px solid transparent;
      transition: color .1s, border-color .1s, background .1s;
    }
    .tab.active {
      color: var(--accent);
      border-bottom: 2px solid var(--accent);
      background: rgba(251,191,36,.04);
    }
    .tab:hover:not(.active) { color: var(--secondary); }
    /* ── Panels ──────────────────────────────────────────────────────────── */
    .panel { display: none; padding: 28px; }
    .panel.active { display: block; }
    /* ── Form elements ───────────────────────────────────────────────────── */
    label {
      display: block; margin-top: 18px; margin-bottom: 6px;
      color: var(--dim); font-size: 9px; font-weight: 600;
      letter-spacing: .12em; text-transform: uppercase;
    }
    label:first-of-type { margin-top: 0; }
    input[type="email"],
    input[type="password"] {
      width: 100%;
      background: var(--input-bg);
      border: 1px solid var(--border); border-radius: 3px;
      color: var(--text); font-family: var(--font);
      font-size: 13px; padding: 10px 12px; outline: none;
      transition: border-color .15s;
    }
    input:focus { border-color: var(--accent); }
    /* ── Password strength meter ─────────────────────────────────────────── */
    .pw-track {
      height: 3px; border-radius: 2px;
      background: var(--border); overflow: hidden; margin-top: 7px;
    }
    .pw-fill {
      height: 100%; width: 0%; border-radius: 2px;
      transition: width .3s, background .3s;
    }
    .pw-hint {
      font-size: 9px; color: var(--dim);
      margin-top: 5px; letter-spacing: .06em; min-height: 14px;
    }
    /* ── Submit button ───────────────────────────────────────────────────── */
    .btn {
      display: block; width: 100%; margin-top: 24px; padding: 12px;
      background: var(--accent); color: #060b19;
      border: none; border-radius: 3px;
      font-family: var(--font); font-size: 11px; font-weight: 700;
      letter-spacing: .12em; text-transform: uppercase;
      cursor: pointer; transition: opacity .15s;
    }
    .btn:hover { opacity: .85; }
    .btn:active { opacity: .7; }
    /* ── Alerts ──────────────────────────────────────────────────────────── */
    .alert {
      padding: 10px 14px; border-radius: 3px;
      font-size: 11px; line-height: 1.5; margin-bottom: 16px;
    }
    .alert-err { background: rgba(248,113,113,.12); border: 1px solid rgba(248,113,113,.3); color: var(--red); }
    .alert-ok  { background: rgba(34,197,94,.10);  border: 1px solid rgba(34,197,94,.25);  color: var(--green); }
    /* ── Footer links ────────────────────────────────────────────────────── */
    .ftr { margin-top: 18px; text-align: center; font-size: 9px; color: var(--dim); letter-spacing: .08em; }
    .ftr a { color: var(--accent); text-decoration: none; }
    .ftr a:hover { text-decoration: underline; }
    /* ── Page footer ─────────────────────────────────────────────────────── */
    .pg-ftr { margin-top: 20px; font-size: 9px; color: var(--dim); letter-spacing: .08em; text-align: center; }
  </style>
</head>
<body>
  <div class="hdr">
    <div class="hdr-logo">▦ &nbsp;Market Pulse Terminal</div>
    <div class="hdr-sub">⌘ &nbsp;Authentication required</div>
  </div>

  <div class="card">
    <div class="tabs">
      <button class="tab {% if mode == 'login' %}active{% endif %}"
              onclick="switchTab('login')">Sign In</button>
      <button class="tab {% if mode == 'register' %}active{% endif %}"
              onclick="switchTab('register')">Register</button>
    </div>

    <!-- ── Login panel ──────────────────────────────────────────────────── -->
    <div class="panel {% if mode == 'login' %}active{% endif %}" id="p-login">
      {% if success %}<div class="alert alert-ok">{{ success }}</div>{% endif %}
      {% if error and mode == 'login' %}<div class="alert alert-err">{{ error }}</div>{% endif %}
      <form method="POST" action="/login" autocomplete="on">
        <input type="hidden" name="csrf_token" value="{{ csrf }}">
        <label for="l-email">Email address</label>
        <input type="email" id="l-email" name="email"
               placeholder="you@example.com" required autocomplete="email">
        <label for="l-pw">Password</label>
        <input type="password" id="l-pw" name="password"
               placeholder="••••••••" required autocomplete="current-password">
        <button class="btn" type="submit">→ &nbsp;Sign In</button>
      </form>
      <div class="ftr">
        <a href="/forgot-password">Forgot password?</a>
      </div>
    </div>

    <!-- ── Register panel ─────────────────────────────────────────────────── -->
    <div class="panel {% if mode == 'register' %}active{% endif %}" id="p-register">
      {% if error and mode == 'register' %}<div class="alert alert-err">{{ error }}</div>{% endif %}
      <form method="POST" action="/register" autocomplete="off">
        <input type="hidden" name="csrf_token" value="{{ csrf }}">
        <label for="r-email">Email address</label>
        <input type="email" id="r-email" name="email"
               placeholder="you@example.com" required autocomplete="email">
        <label for="r-pw">Password</label>
        <input type="password" id="r-pw" name="password"
               placeholder="≥8 chars, upper, lower, digit, symbol"
               required autocomplete="new-password"
               oninput="pwStrength(this.value)">
        <div class="pw-track"><div class="pw-fill" id="pw-fill"></div></div>
        <div class="pw-hint" id="pw-hint">Enter a password</div>
        <label for="r-confirm">Confirm password</label>
        <input type="password" id="r-confirm" name="confirm"
               placeholder="••••••••" required autocomplete="new-password">
        <button class="btn" type="submit">→ &nbsp;Create Account</button>
      </form>
      <div class="ftr">
        A verification link will be sent to your email.
      </div>
    </div>
  </div>

  <div class="pg-ftr">
    Secured by Supabase Auth &nbsp;·&nbsp; TLS enforced in production
  </div>

  <script>
    function switchTab(mode) {
      ['login','register'].forEach(function(m) {
        var isActive = (m === mode);
        document.getElementById('p-' + m).classList.toggle('active', isActive);
        document.querySelectorAll('.tab')[m === 'login' ? 0 : 1].classList.toggle('active', isActive);
      });
    }

    function pwStrength(val) {
      var score = 0;
      if (val.length >= 8)                                                    score++;
      if (/[A-Z]/.test(val) && /[a-z]/.test(val))                           score++;
      if (/[0-9]/.test(val))                                                  score++;
      if (/[!@#$%^&*()\\_=+\[\]{};:'",.<>/?|`~-]/.test(val))               score++;
      var cfg = [
        { pct:  0, bg: 'var(--border)',  label: 'Enter a password',     color: 'var(--dim)' },
        { pct: 25, bg: 'var(--red)',     label: 'WEAK',                  color: 'var(--red)' },
        { pct: 50, bg: 'var(--orange)',  label: 'FAIR',                  color: 'var(--orange)' },
        { pct: 75, bg: 'var(--accent)',  label: 'GOOD',                  color: 'var(--accent)' },
        { pct:100, bg: 'var(--green)',   label: 'STRONG',                color: 'var(--green)' },
      ][score];
      document.getElementById('pw-fill').style.width      = cfg.pct + '%';
      document.getElementById('pw-fill').style.background = cfg.bg;
      document.getElementById('pw-hint').textContent      = cfg.label;
      document.getElementById('pw-hint').style.color      = cfg.color;
    }
  </script>
</body>
</html>"""

# ─── Forgot-password page (minimal) ──────────────────────────────────────────

_FORGOT_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Market Pulse — Password Reset</title>
  <link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600;700&display=swap" rel="stylesheet">
  <style>
    *{box-sizing:border-box;margin:0;padding:0}
    :root{--bg:#060b19;--panel:#0d1526;--input-bg:#0a1020;--border:#1e2d4a;
          --accent:#fbbf24;--text:#e2e8f0;--dim:#4a6080;--green:#22c55e;
          --red:#f87171;--font:'IBM Plex Mono','Courier New',monospace}
    body{background:var(--bg);color:var(--text);font-family:var(--font);
         min-height:100vh;display:flex;flex-direction:column;
         align-items:center;justify-content:center;padding:24px}
    .hdr{text-align:center;margin-bottom:28px}
    .hdr-logo{color:var(--accent);font-size:12px;font-weight:700;letter-spacing:.20em;text-transform:uppercase;margin-bottom:6px}
    .hdr-sub{color:var(--dim);font-size:9px;letter-spacing:.15em;text-transform:uppercase}
    .card{background:var(--panel);border:1px solid var(--border);border-radius:6px;
          width:100%;max-width:380px;padding:28px;box-shadow:0 24px 80px rgba(0,0,0,.65)}
    label{display:block;margin-bottom:6px;color:var(--dim);font-size:9px;font-weight:600;
          letter-spacing:.12em;text-transform:uppercase}
    input{width:100%;background:var(--input-bg);border:1px solid var(--border);
          border-radius:3px;color:var(--text);font-family:var(--font);
          font-size:13px;padding:10px 12px;outline:none;transition:border-color .15s}
    input:focus{border-color:var(--accent)}
    .btn{display:block;width:100%;margin-top:20px;padding:12px;
         background:var(--accent);color:#060b19;border:none;border-radius:3px;
         font-family:var(--font);font-size:11px;font-weight:700;
         letter-spacing:.12em;text-transform:uppercase;cursor:pointer}
    .btn:hover{opacity:.85}
    .alert{padding:10px 14px;border-radius:3px;font-size:11px;
           line-height:1.5;margin-bottom:16px}
    .alert-ok{background:rgba(34,197,94,.10);border:1px solid rgba(34,197,94,.25);color:var(--green)}
    .alert-err{background:rgba(248,113,113,.12);border:1px solid rgba(248,113,113,.3);color:var(--red)}
    .back{margin-top:18px;text-align:center;font-size:9px;color:var(--dim);letter-spacing:.08em}
    .back a{color:var(--accent);text-decoration:none}
  </style>
</head>
<body>
  <div class="hdr">
    <div class="hdr-logo">▦ &nbsp;Market Pulse Terminal</div>
    <div class="hdr-sub">Password Reset</div>
  </div>
  <div class="card">
    {% if msg %}<div class="alert alert-{{ msg_type }}">{{ msg }}</div>{% endif %}
    {% if not sent %}
    <form method="POST" action="/forgot-password">
      <input type="hidden" name="csrf_token" value="{{ csrf }}">
      <label for="fp-email">Your email address</label>
      <input type="email" id="fp-email" name="email"
             placeholder="you@example.com" required autocomplete="email">
      <button class="btn" type="submit">→ &nbsp;Send Reset Link</button>
    </form>
    {% endif %}
    <div class="back"><a href="/login">← Back to login</a></div>
  </div>
</body>
</html>"""


# ─── Email verification callback page ────────────────────────────────────────

_CALLBACK_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Market Pulse — Email Verified</title>
  <link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600;700&display=swap" rel="stylesheet">
  <style>
    *{box-sizing:border-box;margin:0;padding:0}
    :root{--bg:#060b19;--panel:#0d1526;--border:#1e2d4a;--accent:#fbbf24;
          --text:#e2e8f0;--dim:#4a6080;--green:#22c55e;--red:#f87171;
          --font:'IBM Plex Mono','Courier New',monospace}
    body{background:var(--bg);color:var(--text);font-family:var(--font);
         min-height:100vh;display:flex;flex-direction:column;
         align-items:center;justify-content:center;padding:24px;text-align:center}
    .logo{color:var(--accent);font-size:12px;font-weight:700;letter-spacing:.20em;
          text-transform:uppercase;margin-bottom:8px}
    .card{background:var(--panel);border:1px solid var(--border);border-radius:6px;
          width:100%;max-width:380px;padding:36px 28px;
          box-shadow:0 24px 80px rgba(0,0,0,.65);margin-top:24px}
    .icon{font-size:32px;margin-bottom:16px}
    .title{font-size:13px;font-weight:700;letter-spacing:.10em;
           text-transform:uppercase;margin-bottom:10px}
    .title.ok{color:var(--green)}
    .title.err{color:var(--red)}
    .msg{font-size:11px;color:var(--dim);line-height:1.7;letter-spacing:.04em}
    .btn{display:inline-block;margin-top:24px;padding:12px 28px;
         background:var(--accent);color:#060b19;border-radius:3px;
         font-family:var(--font);font-size:11px;font-weight:700;
         letter-spacing:.12em;text-transform:uppercase;text-decoration:none}
    .btn:hover{opacity:.85}
  </style>
</head>
<body>
  <div class="logo">▦ &nbsp;Market Pulse Terminal</div>
  <div class="card">
    {% if error %}
      <div class="icon">✗</div>
      <div class="title err">Verification Failed</div>
      <div class="msg">{{ error }}<br><br>
        The link may have expired — registration links are valid for 24 hours.
        Try registering again to receive a fresh link.
      </div>
      <a class="btn" href="/login">← Back to login</a>
    {% else %}
      <div class="icon" style="color:var(--green)">✓</div>
      <div class="title ok">Email Verified</div>
      <div class="msg">Your account has been confirmed.<br>
        You can now sign in with your credentials.
      </div>
      <a class="btn" href="/login">→ &nbsp;Sign In</a>
    {% endif %}
  </div>
</body>
</html>"""


# ─── Route handlers ───────────────────────────────────────────────────────────

def _render(mode: str, error=None, success=None):
    return render_template_string(
        _PAGE_HTML, mode=mode, error=error, success=success, csrf=_csrf_token()
    )


@auth_bp.route("/auth/callback", methods=["GET"])
def auth_callback():
    """
    Landing page after Supabase email verification link is clicked.
    Supabase verifies the OTP server-side, then redirects here.
    If there's an error param in the URL, show the failure page.
    Otherwise show success and let the user sign in normally.
    """
    error_code = request.args.get("error_code") or request.args.get("error")
    if error_code:
        desc = request.args.get("error_description", "Verification failed.")
        desc = desc.replace("+", " ")
        return render_template_string(_CALLBACK_HTML, error=desc), 400
    return render_template_string(_CALLBACK_HTML, error=None)


@auth_bp.route("/login", methods=["GET"])
def login_get():
    if session.get("user_email"):
        return redirect("/")
    return _render("login")


@auth_bp.route("/login", methods=["POST"])
@_rate_limit(10, 60)
def login_post():
    if not _csrf_valid(request.form.get("csrf_token")):
        return _render("login", error="Invalid request token — please refresh and try again.")

    email    = (request.form.get("email") or "").strip().lower()
    password = request.form.get("password") or ""

    if not email or not password:
        return _render("login", error="Email and password are required.")

    if _is_locked(email):
        _audit("login", email, False)
        return _render("login",
            error="Too many failed attempts — account temporarily locked for 30 minutes.")

    supa = _get_supa()
    if not supa:
        return _render("login", error="Authentication service unavailable. Contact admin.")

    try:
        res  = supa.auth.sign_in_with_password({"email": email, "password": password})
        user = res.user
        if not user:
            raise ValueError("no user returned")

        # Enforce email verification
        if not user.email_confirmed_at:
            return _render("login",
                error="Email not yet verified. Check your inbox for the confirmation link.")

        # ── Success ──
        _clear_failures(email)
        session.permanent     = True
        session["user_email"] = user.email
        session["user_id"]    = str(user.id)
        session["login_at"]   = datetime.utcnow().isoformat()
        _audit("login", email, True)
        return redirect("/")

    except Exception as exc:
        _record_failure(email)
        _audit("login", email, False)
        logger.debug(f"auth: login exc: {exc}")
        return _render("login", error="Incorrect email or password.")


@auth_bp.route("/register", methods=["GET"])
def register_get():
    if session.get("user_email"):
        return redirect("/")
    return _render("register")


@auth_bp.route("/register", methods=["POST"])
@_rate_limit(5, 60)
def register_post():
    if not _csrf_valid(request.form.get("csrf_token")):
        return _render("register", error="Invalid request token — please refresh and try again.")

    email   = (request.form.get("email") or "").strip().lower()
    pw      = request.form.get("password") or ""
    confirm = request.form.get("confirm") or ""

    if not _EMAIL_RE.match(email):
        return _render("register", error="Invalid email address.")
    if not _PW_RE.match(pw):
        return _render("register",
            error="Password must be ≥8 characters and include uppercase, lowercase, "
                  "a number, and a special character (!@#$%^&* etc.).")
    # Constant-time comparison prevents timing attacks on password confirmation
    if not secrets.compare_digest(pw.encode(), confirm.encode()):
        return _render("register", error="Passwords do not match.")

    supa = _get_supa()
    if not supa:
        return _render("register", error="Authentication service unavailable. Contact admin.")

    try:
        callback_url = request.host_url.rstrip("/") + "/auth/callback"
        res = supa.auth.sign_up({
            "email": email,
            "password": pw,
            "options": {"email_redirect_to": callback_url},
        })
        if not res.user:
            raise ValueError("no user returned")
        _audit("register", email, True)
        return _render("login",
            success="Account created! Check your email for a verification link, then sign in.")

    except Exception as exc:
        err = str(exc).lower()
        if any(k in err for k in ("already registered", "already exists", "email address is already")):
            msg = "An account with that email already exists."
        elif "rate limit" in err or "over_email_send_rate_limit" in err or "429" in err:
            msg = ("Email rate limit reached — Supabase allows 2 verification emails per hour. "
                   "Wait an hour and try again, or contact the admin to set up custom SMTP.")
        else:
            logger.error(f"auth: register error email={email} exc={exc}")
            msg = "Registration failed — please try again."
        _audit("register", email, False)
        return _render("register", error=msg)


@auth_bp.route("/logout")
def logout():
    email = session.get("user_email", "unknown")
    supa  = _get_supa()
    if supa:
        try:
            supa.auth.sign_out()
        except Exception:
            pass
    session.clear()
    _audit("logout", email, True)
    resp = redirect("/login")
    resp.delete_cookie("mps")
    return resp


@auth_bp.route("/forgot-password", methods=["GET"])
def forgot_get():
    return render_template_string(
        _FORGOT_HTML, csrf=_csrf_token(), msg=None, msg_type=None, sent=False
    )


@auth_bp.route("/forgot-password", methods=["POST"])
@_rate_limit(5, 60)
def forgot_post():
    if not _csrf_valid(request.form.get("csrf_token")):
        return render_template_string(
            _FORGOT_HTML, csrf=_csrf_token(),
            msg="Invalid request — refresh and try again.", msg_type="err", sent=False
        )
    email = (request.form.get("email") or "").strip().lower()
    # Always return success to prevent email enumeration
    supa  = _get_supa()
    if supa and _EMAIL_RE.match(email):
        try:
            redirect_url = os.environ.get(
                "PASSWORD_RESET_URL",
                "https://your-domain.com/login"  # update in Render env vars
            )
            supa.auth.reset_password_email(email, options={"redirect_to": redirect_url})
        except Exception as exc:
            logger.debug(f"auth: reset_password_email exc: {exc}")
    _audit("forgot_password", email, True)
    return render_template_string(
        _FORGOT_HTML, csrf=_csrf_token(),
        msg="If that email is registered, a reset link is on its way.",
        msg_type="ok", sent=True
    )
