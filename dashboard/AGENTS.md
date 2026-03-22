# Market Pulse Terminal — Agent Context

A Bloomberg-style financial terminal built with Plotly Dash. Runs locally on Mac at `http://127.0.0.1:8050` and is deployed on Render.com. Started and built entirely by Claude (Anthropic) in Cowork mode.

To run locally:
```bash
cd ~/Financials/dashboard && /usr/bin/python3 main.py
```
The `marketpulse` alias in `~/.zshrc` also works.

---

## Tech Stack

- **Framework:** Plotly Dash + Dash Bootstrap Components
- **Data:** `yfinance`, `requests`, `feedparser` (RSS)
- **Auth:** `dash-auth` BasicAuth — credentials via `DASH_AUTH_USERS` env var (JSON dict)
- **User profiles:** Supabase (PostgreSQL) — per-user settings stored in `user_settings` table
- **Caching:** `cachetools.TTLCache` — different TTLs per data type
- **Charts:** Plotly (candlestick + subplots via `make_subplots`)
- **Styling:** Bloomberg dark terminal aesthetic — deep navy/black, accent color driven by `var(--accent)` CSS variable
- **Font:** IBM Plex Mono throughout
- **Deployment:** Render.com (Docker), gunicorn 1 worker / 8 threads

---

## File Structure (`dashboard/`)

| File | Role |
|---|---|
| `main.py` | App entry point, all Dash callbacks |
| `layouts.py` | All `html.Div` / component trees |
| `data_manager.py` | All data fetching, caching, processing |
| `chart_builders.py` | Plotly figure construction |
| `config.py` | Tickers, symbols, colors, settings defaults |
| `profiles.py` | Supabase read/write for per-user settings |
| `quantlab_ui.py` | Quant Lab tab UI components |
| `intelligence.py` | Intelligence tab logic |
| `assets/custom.css` | Global CSS overrides |
| `Dockerfile` | Render.com container config |
| `render.yaml` | Render.com service config |
| `requirements.txt` | Python dependencies |

---

## Navigation

The app uses a **fixed left sidebar** (160px wide) instead of top tabs. All page content has `marginLeft: 160px`. The topbar contains only the clock and refresh button.

- `build_sidebar()` in `layouts.py` — fixed left panel, brand block + nav buttons
- `build_navbar()` — topbar only, clock + refresh
- Nav buttons use pattern `id=f"nav-btn-{val}"` — callbacks in `main.py` handle routing
- Hidden `dcc.Tabs(id="main-tabs")` retained as state holder for routing callbacks
- `_NAV_TABS` is a list of 3-tuples: `(icon, label, value)`

---

## Tabs & Features

### PORTFOLIO
- Cards per ticker: price, daily change, YTD, sparkline, advisory rating
- Advisory score computed from RSI, MACD, ADX, Bollinger Band position
- AI Briefing panel (Claude-generated summary via Anthropic API)
- Price alert system (above/below/pct_change thresholds)
- Ticker tape strip

### DEEP DIVE
- 5-panel chart: candlestick + overlays, Volume, RSI, MACD, ADX
- Period selector: 1D / 5D / 1M / 3M / 6M / 1Y / 3Y
- Fundamentals panel: P/E, EPS, market cap, 52w range, beta, dividend yield
- Options flow panel: calls vs puts OI, put/call ratio, unusual activity
- Ticker-specific news panel
- Warmup fetch pattern: short periods fetch more data than displayed so indicators are never gapped

### MARKET
- **Fear & Greed Index** — gauge at top of page, pulls from CNN endpoint with VIX-based fallback, 30-min cache
- Futures strip (S&P, NASDAQ, Dow, Russell, Crude) with LIVE/SETTLED badge
- Indices, Crypto, Bonds, FOREX, Commodities grids — sorted by % change
- **Sector Heatmap** — S&P 500 sector ETF treemap; click a tile to show top 6 holdings by market cap

### QUANT LAB
- Test builder: workflow selector, symbol input, strategy picker, date range, capital, interval
- Segmented controls use custom `.quantlab-seg-btn` CSS class (responds to `var(--accent)`)
- Runs backtests, research, regime detection, optimization via `QuantLabRunner`
- Results panels: equity curve, drawdown, rolling Sharpe, factor ranking, trade blotter, signal feed
- Experiment registry with run history

### INTELLIGENCE
- Smart Money Operating System
- Market regime detection, cross-asset analysis, trade ideas, smart money leaderboard

### CALENDAR
- Monthly grid calendar (Sunday-first)
- Four data sources: Earnings (yfinance), Economic (ForexFactory), FED (hardcoded FOMC dates), IPO (NASDAQ API)
- Filter pills (multi-select): EARNINGS / ECONOMIC / FED / IPO
- Click any event to open detail modal

### NEWS
- Unified feed: portfolio ticker news + 15 RSS sources
- Categories: PORTFOLIO, GEOPOLITICAL, MACRO, MARKETS, COMMODITIES
- Auto-classification via keyword scanning

### SETTINGS
- Theme toggle (dark/light), accent color picker (Amber/Blue/Green/Purple/Orange)
- Portfolio manager: add/remove tickers, multiple named portfolios
- **Chart Indicators** — toggleable per-indicator buttons, two groups:
  - Overlays: MA 20, MA 50, MA 200, EMA 9, EMA 21, Bollinger Bands, VWAP
  - Sub-panels: Volume, OBV, RSI, MACD, ADX
- Alert manager

---

## Key Architecture Decisions

### Accent Color
All accent colors use `var(--accent)` CSS variable — never hardcoded. Set via inline `<style>` in `app.index_string`. Responds instantly to the Settings accent picker without page reload.

### Caching (data_manager.py)
```python
_ticker_cache       = TTLCache(maxsize=50,  ttl=300)    # 5-min
_market_cache       = TTLCache(maxsize=10,  ttl=300)    # 5-min
_news_cache         = TTLCache(maxsize=50,  ttl=300)    # 5-min
_fundamentals_cache = TTLCache(maxsize=50,  ttl=3600)   # 1-hour
_options_cache      = TTLCache(maxsize=30,  ttl=120)    # 2-min
_calendar_cache     = TTLCache(maxsize=10,  ttl=1800)   # 30-min
_briefing_cache     = TTLCache(maxsize=5,   ttl=900)    # 15-min
_meta_cache         = TTLCache(maxsize=200, ttl=86400)  # 24-hour
_sector_cache       = TTLCache(maxsize=5,   ttl=300)    # 5-min
_fng_cache          = TTLCache(maxsize=1,   ttl=1800)   # 30-min
```

### dcc.Store pattern
State passed between components via `dcc.Store`, never via `dcc.Tabs` value:
- `dcc.Store(id="deepdive-period", data="3mo")`
- `dcc.Store(id="news-filter", data="ALL")`
- `dcc.Store(id="cal-filter", data=["EARNINGS","ECONOMIC","FED","IPO"])`
- `dcc.Store(id="cal-month", data={"year": 2026, "month": 3})`
- `dcc.Store(id="user-settings", storage_type="local", data=DEFAULT_SETTINGS)`

### Per-User Profiles (profiles.py)
- `get_username_from_request()` — reads `request.authorization.username` from Flask context
- `load_settings(username)` — fetches from Supabase, merges with DEFAULT_SETTINGS
- `save_settings(username, settings)` — upserts to Supabase
- Falls back to DEFAULT_SETTINGS gracefully when Supabase env vars are not set (local dev)
- Settings loaded on first interval tick; saved when user clicks Save in Settings

### Multi-user Auth
`DASH_AUTH_USERS` env var holds a JSON dict: `{"username": "password", ...}`
Falls back to legacy `DASH_AUTH_USER` / `DASH_AUTH_PASS` single-user vars.
Auth is skipped entirely when no env vars are set (local dev).

### Chart Warmup Pattern
Short periods fetch more data than displayed to ensure indicators have enough history:
```python
_WARMUP_FETCH = {
    ("1d",  "5m"):  ("60d", "5m"),
    ("5d",  "30m"): ("60d", "30m"),
    ("1mo", "1d"):  ("6mo", "1d"),
}
```

### Pattern-matching callbacks
- News filter pills: `id={"type":"news-filter-btn","index":cat}`
- Calendar filter pills: `id={"type":"cal-filter-btn","index":cat}`
- Calendar event pills: `id={"type":"cal-event-pill","index":event_json}`
- Indicator toggles: `id={"type":"ind-toggle-btn","index":key}`

### Modal pattern (Calendar tab)
Static shell always in DOM (backdrop + panel + close button). Only `cal-modal-body` children are updated dynamically. Required so `cal-modal-close` exists at callback registration time.

### Indicator toggle order
The `_keys` list in `toggle_indicator` callback must match the DOM order of buttons in `layouts.py`:
```python
_keys = ["ma20", "ma50", "ma200", "ema9", "ema21", "bb", "vwap",
         "volume", "obv", "rsi", "macd", "adx"]
```

### Sector Heatmap click
`clickData["points"][0]["customdata"]` holds the clean ETF symbol.
`label` holds formatted HTML display text — do NOT use label for lookup.

---

## Config Reference (config.py)

- `PORTFOLIO_TICKERS` — default ticker list
- `INDICES`, `COMMODITIES`, `BONDS`, `CRYPTO`, `FX`, `FUTURES`, `SECTORS` — Market tab symbol lists
- `PRESET_TICKERS` — grouped ticker suggestions for Settings (Tech, Finance, Crypto, Energy, Healthcare, ETFs, Semis)
- `NEWS_SOURCES` — RSS source dicts
- `C` — color dict (Bloomberg dark palette)
- `CHART` — chart-specific colors including `ema9`, `ema21`, `vwap`
- `DEFAULT_SETTINGS` — default user settings including all 12 indicator flags

---

## Style Conventions
- Font: `'IBM Plex Mono', 'Courier New', monospace` (stored as `FONT_MONO` in layouts.py)
- Accent: always `var(--accent)` — never hardcode amber
- Colors from `C` dict: `C["green"]`, `C["red"]`, `C["amber"]`, etc.
- Borders: `C["border"]` = `#1e2d4a`
- Backgrounds: `C["bg"]`, `C["bg_panel"]`, `C["bg_chart"]`
- Section titles: `SECTION_TITLE` style dict
- All layouts return `html.Div` trees

---

## Environment Variables

| Variable | Purpose |
|---|---|
| `DASH_AUTH_USERS` | JSON dict of `{"username": "password"}` for all users |
| `DASH_AUTH_USER` | Legacy single-user username (fallback) |
| `DASH_AUTH_PASS` | Legacy single-user password (fallback) |
| `SECRET_KEY` | Flask session secret key |
| `ANTHROPIC_API_KEY` | For AI Briefing in Portfolio tab |
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_KEY` | Supabase anon public key |

---

## Python Version Note
The codebase runs on Python 3.9 (macOS system Python at `/usr/bin/python3`).
Do not use `X | Y` union type hints — use `Optional[X]` or omit the annotation.
