# Enzo Market Pulse — Bloomberg Terminal Dashboard

## What This Is
A Bloomberg-style financial terminal built in Python with Plotly Dash. It runs locally on Enzo's Mac and is accessed via browser at `http://127.0.0.1:8050`. It is **not** a web app — it is a personal desktop tool.

To run it:
```bash
cd ~/Financials/dashboard
python3 main.py
```

---

## Tech Stack
- **Framework:** Plotly Dash + Dash Bootstrap Components (`dbc`)
- **Data:** `yfinance` for all market/portfolio data, `requests` + `feedparser` for news RSS
- **Caching:** `cachetools.TTLCache` — different TTLs per data type (see below)
- **Charts:** Plotly (candlestick + subplots via `make_subplots`)
- **Styling:** Bloomberg dark terminal aesthetic — deep navy/black, amber accent, IBM Plex Mono font throughout
- **Accent color:** Driven by CSS variable `var(--accent)` so it responds to the user's chosen accent in Settings

---

## File Structure (`dashboard/`)

| File | Role |
|---|---|
| `main.py` | App entry point, all Dash callbacks |
| `layouts.py` | All `html.Div` / component trees returned by callbacks |
| `data_manager.py` | All data fetching, caching, and processing logic |
| `chart_builders.py` | Plotly figure construction (main chart + indicators) |
| `config.py` | Tickers, symbols, colors, news sources, settings defaults |

---

## Tabs & Features Built

### PORTFOLIO tab
- Cards for each portfolio ticker: price, daily change, YTD, sparkline, advisory rating
- Advisory score computed from RSI, MACD, ADX, Bollinger Band position
- AI Briefing panel (Claude-generated summary of portfolio)
- Price alert system (above/below/pct_change thresholds)
- Ticker tape strip across the top

### DEEP DIVE tab
- Full 5-panel chart: candlestick + MA20/50/200 + Bollinger Bands, Volume, RSI, MACD, ADX
- Period selector: 1D / 5D / 1M / 3M / 6M / 1Y / 3Y (stored in `dcc.Store`, NOT `dcc.Tabs`)
- Fundamentals panel: P/E, EPS, market cap, 52w range, beta, dividend yield
- Options flow panel: calls vs puts OI, put/call ratio, unusual activity
- News panel: ticker-specific headlines
- **Warmup fetch pattern:** short periods (1D/5D/1M) fetch more data than displayed, compute full indicators on the larger window, then trim — this ensures RSI/MACD/ADX are never gapped at the left edge
- Background pre-warming: after portfolio refresh, a daemon thread pre-fetches fundamentals/options/news for all tickers so Deep Dive loads instantly

### MARKET tab
- Futures strip (full width) — S&P, NASDAQ, Dow, Russell, Crude futures with LIVE/SETTLED badge
- Indices grid — S&P 500, Dow, NASDAQ, Russell 2K, VIX
- Crypto grid — BTC, ETH, SOL, BNB
- Bonds grid — US 10Y (`^TNX`), 3M (`^IRX`), 30Y (`^TYX`), 5Y (`^FVX`)
- FX grid — EUR/USD, GBP/USD, USD/JPY, DXY
- Commodities — Gold, Silver, Platinum, Crude Oil, Brent Oil, Nat Gas, Copper
- All sections sorted by `chg_pct` descending (best performers first)

### CALENDAR tab
- Monthly grid calendar (Sunday-first, 7-column CSS grid)
- Prev/Next month navigation with `◄ MARCH 2026 ►` header
- Four data sources fetched in parallel via `ThreadPoolExecutor`:
  - **EARNINGS** — `yf.Ticker.calendar` for each portfolio ticker (60-day lookahead)
  - **ECONOMIC** — ForexFactory free JSON API (this week + next week, USD High/Medium only)
  - **FED** — Hardcoded FOMC decision dates through end of 2026
  - **IPO** — NASDAQ public API
- Filter pills (multi-select toggle): EARNINGS / ECONOMIC / FED / IPO
- Clicking any event pill opens a modal with: event title, date, category badge, impact level, subtitle (actual/forecast/prev), "WHAT IS IT" description, "MARKET IMPACT" analysis
- Modal has a static shell (close button always in DOM) with dynamic body — this is critical for Dash callback registration
- Click backdrop or ✕ to close modal
- Event descriptions live in `_EVENT_INFO` (keyword lookup) and `_CAT_INFO` (category fallback) dicts in `layouts.py`

### NEWS tab
- Single unified feed merging portfolio ticker news + 15 RSS sources
- Categories: PORTFOLIO, GEOPOLITICAL, MACRO, MARKETS, COMMODITIES
- Auto-classification via `_classify_article()` keyword scanning (priority: GEOPOLITICAL > MACRO > COMMODITIES > MARKETS)
- Single-select filter pills (ALL / category)
- Sources include: Reuters Business & World, CNBC, MarketWatch, Yahoo Finance, The Economist, CNN Business, Federal Reserve, BBC Business & World, Al Jazeera, Deutsche Welle, OilPrice.com, Investopedia

### SETTINGS tab
- Theme toggle (dark/light)
- Accent color picker
- Portfolio manager (add/remove tickers, multiple named portfolios)
- Alert manager

---

## Key Architecture Decisions

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
```

### dcc.Store pattern
- State is passed between components via `dcc.Store`, never via `dcc.Tabs` value
- Period selector: `dcc.Store(id="deepdive-period", data="3mo")` — Input uses `.data` not `.value`
- News filter: `dcc.Store(id="news-filter", data="ALL")`
- Calendar filter: `dcc.Store(id="cal-filter", data=["EARNINGS","ECONOMIC","FED","IPO"])` — multi-select list
- Calendar month: `dcc.Store(id="cal-month", data={"year": 2026, "month": 3})`
- Calendar modal event: `dcc.Store(id="cal-modal-event", data=None)`

### Pattern-matching callbacks
- Used for news filter pills: `id={"type":"news-filter-btn","index":cat}`
- Used for calendar filter pills: `id={"type":"cal-filter-btn","index":cat}`
- Used for calendar event pills: `id={"type":"cal-event-pill","index":event_json}` — the index is compact JSON encoding the full event dict
- **Critical rule:** Any component used as a non-pattern-matched `Input` must exist in the DOM at page load. Dynamic components (created inside callbacks) can only be used as pattern-matched `ALL` inputs.

### Modal pattern (Calendar tab)
- Static shell always in DOM: backdrop div + panel div with close button + empty body div
- Dynamic content: only `cal-modal-body` children are updated by callback
- This is required because `cal-modal-close` must exist at startup to be registered as a callback Input

### Chart warmup pattern (data_manager.py)
Short periods fetch more data than they display to ensure indicators have enough history:
```python
_WARMUP_FETCH = {
    ("1d",  "5m"):  ("60d", "5m"),
    ("5d",  "30m"): ("60d", "30m"),
    ("1mo", "1d"):  ("6mo", "1d"),
}
```
After computing indicators on the full warmup window, the data is trimmed back to the display window using `_TRIM_DELTA`.

---

## Config Reference (config.py)

- `PORTFOLIO_TICKERS` — default ticker list
- `INDICES`, `COMMODITIES`, `BONDS`, `CRYPTO`, `FX`, `FUTURES` — Market Monitor symbol lists (tuples of `(symbol, name, category)`)
- `NEWS_SOURCES` — list of RSS source dicts with `name`, `url`, `color`, `tag`, `category`
- `C` — color dict (Bloomberg dark palette)
- `CHART` — chart-specific color dict
- `DEFAULT_SETTINGS` — default user settings stored in browser via `dcc.Store`
- `ADVISORY_THRESHOLDS` — score ranges for BUY/SELL/HOLD labels

---

## Style Conventions
- Font: `'IBM Plex Mono', 'Courier New', monospace` everywhere (stored as `FONT_MONO` in layouts.py)
- Accent: always `var(--accent)` in CSS strings, never hardcoded amber — this lets the Settings accent picker work
- Colors referenced from `C` dict (imported from config): `C["green"]`, `C["red"]`, `C["amber"]`, etc.
- Borders: `C["border"]` = `#1e2d4a`
- Backgrounds: `C["bg"]` (deepest), `C["bg_panel"]` (cards), `C["bg_chart"]` (charts)
- Section titles use `SECTION_TITLE` style dict (uppercase, letter-spaced, amber accent)
- All layouts return `html.Div` trees — no `.py` files write raw HTML

---

## What's Left / Possible Next Steps
- Sector heatmap (S&P 500 sector performance treemap)
- Portfolio risk analytics (Sharpe ratio, beta vs SPY, max drawdown, rolling return chart)
- Earnings calendar modal: show historical beat/miss record
- Watchlist tab (track tickers without adding to portfolio)
- GitHub backup: repo exists but push must be run from user's Mac terminal (sandbox can't reach GitHub directly)
  ```bash
  cd ~/Financials && git push origin main
  ```
