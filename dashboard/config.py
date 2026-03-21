# ─────────────────────────────────────────────────────────────────────────────
# config.py  —  Bloomberg Terminal Dashboard  •  Enzo Market Pulse
# ─────────────────────────────────────────────────────────────────────────────

# ── Tickers ──────────────────────────────────────────────────────────────────
PORTFOLIO_TICKERS = ["NVDA", "PLTR", "MSTR", "IBM", "MU", "XLF", "SMHX"]

TICKER_NAMES = {
    "NVDA":  "NVIDIA Corporation",
    "PLTR":  "Palantir Technologies",
    "MSTR":  "MicroStrategy",
    "IBM":   "IBM Corporation",
    "MU":    "Micron Technology",
    "XLF":   "Financial Select SPDR",
    "SMHX":  "VanEck Semiconductor ETF",
}

TICKER_SECTOR = {
    "NVDA":  ("Semiconductors",    "#7C3AED"),
    "PLTR":  ("Software",          "#0369A1"),
    "MSTR":  ("Bitcoin Proxy",     "#F59E0B"),
    "IBM":   ("IT Services",       "#1E40AF"),
    "MU":    ("Semiconductors",    "#7C3AED"),
    "XLF":   ("Financials ETF",    "#059669"),
    "SMHX":  ("Semi ETF (Hedged)", "#6B7280"),
}

DOMAIN_MAP = {
    "NVDA":  "nvidia.com",
    "PLTR":  "palantir.com",
    "MSTR":  "bitcoin.org",
    "IBM":   "ibm.com",
    "MU":    "micron.com",
    "XLF":   "sectorspdr.com",
    "SMHX":  "vaneck.com",
}

# ── Market Monitor Symbols ────────────────────────────────────────────────────
INDICES = [
    ("^GSPC",  "S&P 500",    "US Equities"),
    ("^DJI",   "Dow Jones",  "US Equities"),
    ("^IXIC",  "NASDAQ",     "US Equities"),
    ("^RUT",   "Russell 2K", "US Equities"),
    ("^VIX",   "VIX",        "Volatility"),
]

COMMODITIES = [
    ("GC=F",   "Gold",       "Precious Metals"),
    ("SI=F",   "Silver",     "Precious Metals"),
    ("PL=F",   "Platinum",   "Precious Metals"),
    ("CL=F",   "Crude Oil",  "Energy"),
    ("BZ=F",   "Brent Oil",  "Energy"),
    ("NG=F",   "Nat Gas",    "Energy"),
    ("HG=F",   "Copper",     "Industrial"),
]

BONDS = [
    ("^TNX",   "US 10Y",     "Treasury"),
    ("^IRX",   "US 3M",      "Treasury"),
    ("^TYX",   "US 30Y",     "Treasury"),
    ("^FVX",   "US 5Y",      "Treasury"),
]

CRYPTO = [
    ("BTC-USD", "Bitcoin",   "Crypto"),
    ("ETH-USD", "Ethereum",  "Crypto"),
    ("SOL-USD", "Solana",    "Crypto"),
    ("BNB-USD", "BNB",       "Crypto"),
]

FX = [
    ("EURUSD=X", "EUR/USD", "FX"),
    ("GBPUSD=X", "GBP/USD", "FX"),
    ("JPY=X",    "USD/JPY", "FX"),
    ("DX-Y.NYB", "DXY",     "FX"),
]

FUTURES = [
    ("ES=F",  "S&P 500 Futures",  "Futures"),
    ("NQ=F",  "NASDAQ Futures",   "Futures"),
    ("YM=F",  "Dow Futures",      "Futures"),
    ("RTY=F", "Russell 2K Fut",   "Futures"),
    ("CL=F",  "Crude Oil Fut",    "Futures"),
    ("GC=F",  "Gold Futures",     "Futures"),
]

# ── S&P 500 Sector ETFs ───────────────────────────────────────────────────────
SECTORS = [
    ("XLK",  "Technology",       "Sector"),
    ("XLF",  "Financials",       "Sector"),
    ("XLV",  "Health Care",      "Sector"),
    ("XLY",  "Cons. Discret.",   "Sector"),
    ("XLP",  "Cons. Staples",    "Sector"),
    ("XLI",  "Industrials",      "Sector"),
    ("XLE",  "Energy",           "Sector"),
    ("XLC",  "Comm. Services",   "Sector"),
    ("XLRE", "Real Estate",      "Sector"),
    ("XLB",  "Materials",        "Sector"),
    ("XLU",  "Utilities",        "Sector"),
]

# ── Color Palette  (Bloomberg dark terminal aesthetic) ───────────────────────
C = {
    # Backgrounds
    "bg":           "#060b19",   # deep navy-black
    "bg_panel":     "#0d1526",   # card/panel background
    "bg_chart":     "#0a1020",   # chart background
    "bg_hover":     "#151f35",   # hover state
    "border":       "#1e2d4a",   # subtle border

    # Accent
    "amber":        "#fbbf24",   # Bloomberg orange/amber — primary accent
    "amber_dim":    "#92670c",   # dimmed amber for less prominent text
    "green":        "#22c55e",   # positive / buy
    "green_dim":    "#15803d",
    "red":          "#ef4444",   # negative / sell
    "red_dim":      "#b91c1c",
    "blue":         "#38bdf8",   # info / neutral links
    "purple":       "#a78bfa",   # secondary accent
    "cyan":         "#22d3ee",

    # Text
    "text_primary":   "#e2e8f0",
    "text_secondary": "#94a3b8",
    "text_dim":       "#475569",
    "text_white":     "#ffffff",
}

# ── Chart colors ──────────────────────────────────────────────────────────────
CHART = {
    "candle_up":    "#22c55e",
    "candle_down":  "#ef4444",
    "ma20":         "#fbbf24",
    "ma50":         "#38bdf8",
    "ma200":        "#a78bfa",
    "bb_upper":     "#64748b",
    "bb_lower":     "#64748b",
    "volume_up":    "rgba(34,197,94,0.5)",
    "volume_down":  "rgba(239,68,68,0.5)",
    "rsi":          "#fbbf24",
    "macd_line":    "#38bdf8",
    "macd_signal":  "#f97316",
    "adx":          "#a78bfa",
    "adx_pos":      "#22c55e",
    "adx_neg":      "#ef4444",
    "grid":         "rgba(30,45,74,0.6)",
    "zero_line":    "rgba(100,116,139,0.4)",
}

# ── Light theme overrides (CSS class-based) ───────────────────────────────────
C_LIGHT = {
    "bg":             "#f0f4f8",
    "bg_panel":       "#ffffff",
    "bg_chart":       "#f8fafc",
    "bg_hover":       "#e8eef5",
    "border":         "#cbd5e1",
    "text_primary":   "#1e293b",
    "text_secondary": "#475569",
    "text_dim":       "#94a3b8",
    "text_white":     "#0f172a",
}

# ── Preset popular tickers users can add to portfolios ────────────────────────
PRESET_TICKERS = {
    "Tech":        ["AAPL", "MSFT", "GOOGL", "META", "AMZN", "TSLA", "NVDA", "AMD", "INTC"],
    "Finance":     ["JPM", "BAC", "GS", "MS", "V", "MA", "AXP", "BLK", "XLF"],
    "Crypto":      ["MSTR", "COIN", "RIOT", "MARA", "HUT"],
    "Energy":      ["XOM", "CVX", "COP", "SLB", "OXY"],
    "Healthcare":  ["JNJ", "UNH", "PFE", "MRK", "ABBV", "LLY"],
    "ETFs":        ["SPY", "QQQ", "IWM", "VTI", "ARKK", "SMHX"],
    "Semis":       ["NVDA", "AMD", "MU", "QCOM", "AVGO", "TSM", "AMAT", "KLAC"],
}

# ── Default user settings (stored in browser localStorage via dcc.Store) ──────
DEFAULT_SETTINGS = {
    "theme": "dark",
    "active_portfolio": "default",
    "portfolios": {
        "default": {
            "name":    "My Portfolio",
            "tickers": ["NVDA", "PLTR", "MSTR", "IBM", "MU", "XLF", "SMHX"],
        }
    },
    # Alert definitions — each dict: {id, ticker, type, threshold, active}
    # type: "above" | "below" | "pct_change"
    "alerts": [],
    # Chart indicator visibility
    "indicators": {
        "ma20":   True,
        "ma50":   True,
        "ma200":  True,
        "bb":     True,
        "volume": True,
        "rsi":    True,
        "macd":   True,
        "adx":    True,
    },
}

# ── Data settings ─────────────────────────────────────────────────────────────
PERIOD           = "6mo"      # yfinance period for charts
INTERVAL         = "1d"       # daily bars
REFRESH_SECONDS  = 60         # auto-refresh interval (seconds)
CACHE_TTL        = 300        # cache time-to-live in seconds (5 min)

# ── News RSS sources ──────────────────────────────────────────────────────────
NEWS_SOURCES = [
    # ── Market & Finance ──────────────────────────────────────────────────────
    {
        "name":     "Reuters Business",
        "url":      "https://feeds.reuters.com/reuters/businessNews",
        "color":    "#ff8000",
        "tag":      "REUTERS",
        "category": "MARKETS",
    },
    {
        "name":     "CNBC",
        "url":      "https://www.cnbc.com/id/100003114/device/rss/rss.html",
        "color":    "#005594",
        "tag":      "CNBC",
        "category": "MARKETS",
    },
    {
        "name":     "MarketWatch",
        "url":      "https://feeds.content.dowjones.io/public/rss/mw_realtimeheadlines",
        "color":    "#006400",
        "tag":      "MKTWATCH",
        "category": "MARKETS",
    },
    {
        "name":     "Yahoo Finance",
        "url":      "https://finance.yahoo.com/rss/topstories",
        "color":    "#6001d2",
        "tag":      "YAHOO FIN",
        "category": "MARKETS",
    },
    {
        "name":     "The Economist",
        "url":      "https://www.economist.com/finance-and-economics/rss.xml",
        "color":    "#e3120b",
        "tag":      "ECONOMIST",
        "category": "MACRO",
    },
    {
        "name":     "Investopedia",
        "url":      "https://www.investopedia.com/feedbuilder/feed/getfeed?feedName=rss_headline",
        "color":    "#0066cc",
        "tag":      "INVSTPDIA",
        "category": "MARKETS",
    },
    {
        "name":     "CNN Business",
        "url":      "https://rss.cnn.com/rss/money_latest.rss",
        "color":    "#cc0000",
        "tag":      "CNN BIZ",
        "category": "MARKETS",
    },
    # ── Macro & Policy ────────────────────────────────────────────────────────
    {
        "name":     "Federal Reserve",
        "url":      "https://www.federalreserve.gov/feeds/press_all.xml",
        "color":    "#1d4ed8",
        "tag":      "FED",
        "category": "MACRO",
    },
    {
        "name":     "BBC Business",
        "url":      "https://feeds.bbci.co.uk/news/business/rss.xml",
        "color":    "#bb1919",
        "tag":      "BBC BIZ",
        "category": "MACRO",
    },
    # ── Geopolitical & Global ─────────────────────────────────────────────────
    {
        "name":     "Reuters World",
        "url":      "https://feeds.reuters.com/Reuters/worldNews",
        "color":    "#ff6600",
        "tag":      "REUTERS WLD",
        "category": "GEOPOLITICAL",
    },
    {
        "name":     "BBC World",
        "url":      "https://feeds.bbci.co.uk/news/world/rss.xml",
        "color":    "#bb1919",
        "tag":      "BBC WORLD",
        "category": "GEOPOLITICAL",
    },
    {
        "name":     "Al Jazeera",
        "url":      "https://www.aljazeera.com/xml/rss/all.xml",
        "color":    "#6f8f1e",
        "tag":      "AL JAZEERA",
        "category": "GEOPOLITICAL",
    },
    {
        "name":     "Deutsche Welle",
        "url":      "https://rss.dw.com/rdf/rss-en-world",
        "color":    "#c8001e",
        "tag":      "DW",
        "category": "GEOPOLITICAL",
    },
    # ── Commodities & Energy ──────────────────────────────────────────────────
    {
        "name":     "OilPrice.com",
        "url":      "https://oilprice.com/rss/main",
        "color":    "#78350f",
        "tag":      "OILPRICE",
        "category": "COMMODITIES",
    },
]

# ── Advisory thresholds ───────────────────────────────────────────────────────
ADVISORY_THRESHOLDS = [
    (4,  5, "STRONG BUY",  C["green"]),
    (2,  4, "BUY",         "#16a34a"),
    (0,  2, "HOLD",        C["amber"]),
    (-2, 0, "SELL",        "#ea580c"),
    (None, -2, "STRONG SELL", C["red"]),
]
