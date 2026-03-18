"""
Market Pulse Report
=================================
Indicators: Moving Averages, RSI, MACD, Bollinger Bands
Output: Multi-page PDF — Cover | Global Indices | Commodities | Per-ticker charts

SETUP (run once in your terminal):
    pip3 install yfinance pandas matplotlib ta

USAGE:
    python3 stock_analysis.py
"""

import os
import io
import urllib.request
import xml.etree.ElementTree as ET
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import FancyBboxPatch
import warnings
warnings.filterwarnings("ignore")

try:
    import yfinance as yf
    import ta as ta_lib
except ImportError:
    print("Missing libraries. Please run:")
    print("  pip3 install yfinance pandas matplotlib ta")
    exit(1)


# ─────────────────────────────────────────────
#  SETTINGS
# ─────────────────────────────────────────────
TICKERS  = ["NVDA", "PLTR", "SMHX", "XLF", "MSTR", "IBM", "MU"]
PERIOD   = "1y"
INTERVAL = "1d"

MA_SHORT       = 50
MA_LONG        = 200
RSI_PERIOD     = 14
RSI_OVERBOUGHT = 70
RSI_OVERSOLD   = 30
BB_PERIOD      = 20
BB_STD         = 2.0

INDICES = {
    "^GSPC":  ("S&P 500",    "USA"),
    "^DJI":   ("Dow Jones",  "USA"),
    "^IXIC":  ("NASDAQ",     "USA"),
    "^FTSE":  ("FTSE 100",   "UK"),
    "^GDAXI": ("DAX",        "Germany"),
    "^N225":  ("Nikkei 225", "Japan"),
    "^HSI":   ("Hang Seng",  "Hong Kong"),
}

COMMODITIES = {
    "GC=F": ("Gold",        "Metals"),
    "SI=F": ("Silver",      "Metals"),
    "CL=F": ("Crude Oil",   "Energy"),
    "BZ=F": ("Brent Crude", "Energy"),
    "NG=F": ("Natural Gas", "Energy"),
    "HG=F": ("Copper",      "Metals"),
    "ZW=F": ("Wheat",       "Grains"),
    "ZC=F": ("Corn",        "Grains"),
}

CRYPTO = {
    "BTC-USD":  ("Bitcoin",   "Layer 1"),
    "ETH-USD":  ("Ethereum",  "Layer 1"),
    "SOL-USD":  ("Solana",    "Layer 1"),
    "XRP-USD":  ("XRP",       "Payments"),
    "BNB-USD":  ("BNB",       "Exchange"),
    "DOGE-USD": ("Dogecoin",  "Meme"),
    "ADA-USD":  ("Cardano",   "Layer 1"),
}

SECTOR_COLORS = {
    "Metals":   "#B8860B",
    "Energy":   "#CC4400",
    "Grains":   "#2E7D32",
    "Layer 1":  "#7C3AED",
    "Payments": "#0369A1",
    "Exchange": "#B45309",
    "Meme":     "#B91C1C",
}

# Display names for ticker pages
TICKER_NAMES = {
    "NVDA": "NVIDIA Corporation",
    "PLTR": "Palantir Technologies",
    "MSTR": "MicroStrategy",
    "IBM":  "IBM Corporation",
    "MU":   "Micron Technology",
    "XLF":  "Financial Select SPDR",
    "SMHX": "VanEck Semi ETF (Hdg)",
}

# Sector label + pill color for each individual ticker page
TICKER_SECTOR_MAP = {
    "NVDA": ("Semiconductors",  "#7C3AED"),
    "PLTR": ("Software",        "#0369A1"),
    "MSTR": ("Bitcoin Proxy",   "#F59E0B"),
    "IBM":  ("IT Services",     "#1E40AF"),
    "MU":   ("Semiconductors",  "#7C3AED"),
    "SMHX": ("Semi ETF",        "#6B7280"),
    "XLF":  ("Financials ETF",  "#059669"),
}

OUTPUT_DIR = os.path.expanduser("~/Financials")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Design tokens
NAVY   = "#1B2A4A"
GRAY_L = "#F8FAFC"
GRAY_M = "#E2E8F0"
GRAY_D = "#64748B"
GREEN  = "#16A34A"
RED    = "#DC2626"
AMBER  = "#D97706"
WHITE  = "#FFFFFF"
BG     = "#F1F5F9"


# ─────────────────────────────────────────────
#  SHARED HELPERS
# ─────────────────────────────────────────────
def draw_page_header(fig, title, subtitle, right_text=None, right_color=NAVY, logo_img=None, title_fontsize=22):
    """White header band with left accent stripe and bold bottom border."""
    ax_h = fig.add_axes([0, 0.925, 1, 0.075])
    ax_h.set_facecolor(WHITE)
    ax_h.axis("off")
    # Navy bottom border — patch so corners are mathematically exact
    ax_h.add_patch(FancyBboxPatch((0, 0), 1.0, 0.06, boxstyle="square,pad=0",
                                  facecolor=NAVY, edgecolor="none",
                                  transform=ax_h.transAxes, zorder=1))
    # Gray separator just above the navy strip (starts after the accent bar)
    ax_h.add_patch(FancyBboxPatch((0.005, 0.06), 0.995, 0.015, boxstyle="square,pad=0",
                                  facecolor=GRAY_M, edgecolor="none",
                                  transform=ax_h.transAxes, zorder=1))
    # Left accent bar — shares exact origin (0,0) with the navy border: perfect corner
    ax_h.add_patch(FancyBboxPatch((0, 0), 0.005, 1.0, boxstyle="square,pad=0",
                                  facecolor=NAVY, edgecolor="none",
                                  transform=ax_h.transAxes, zorder=2))
    # Optional logo — placed as a tight inset axes to the right of the accent bar
    title_x = 0.020
    if logo_img is not None:
        try:
            ax_logo = fig.add_axes([0.010, 0.9305, 0.052, 0.062])
            ax_logo.imshow(logo_img, aspect="equal", interpolation="lanczos")
            ax_logo.axis("off")
            ax_logo.set_facecolor(WHITE)
            title_x = 0.090
        except Exception:
            title_x = 0.020

    ax_h.text(title_x, 0.68, title, color=NAVY, fontsize=title_fontsize, fontweight="bold",
              transform=ax_h.transAxes, va="center")
    ax_h.text(title_x, 0.22, subtitle, color=GRAY_D, fontsize=11,
              transform=ax_h.transAxes, va="center")
    if right_text:
        ax_h.text(0.978, 0.50, right_text, color=right_color,
                  fontsize=13, fontweight="bold",
                  transform=ax_h.transAxes, va="center", ha="right")


def add_page_footer(fig, label):
    fig.text(0.5, 0.010, label, color=GRAY_D, fontsize=9, ha="center", va="bottom")


def draw_section_title(ax, x, y, text):
    """Section header with a left accent bar."""
    ax.add_patch(FancyBboxPatch((x, y - 0.011), 0.005, 0.026,
                                boxstyle="square,pad=0",
                                facecolor=NAVY, edgecolor="none", zorder=2))
    ax.text(x + 0.013, y, text, color=NAVY, fontsize=12,
            fontweight="bold", va="center", zorder=3)


def draw_table_header(ax, lm, rm, y, row_h, columns):
    """Draw a styled column-header row."""
    ax.add_patch(FancyBboxPatch((lm, y), rm - lm, row_h,
                                boxstyle="square,pad=0",
                                facecolor=NAVY, edgecolor="none", zorder=1))
    for cx, label, ha in columns:
        ax.text(cx, y + row_h * 0.5, label,
                color=WHITE, fontsize=9.5, fontweight="bold",
                va="center", ha=ha, zorder=2)


def draw_table_row(ax, lm, rm, y, row_h, i, left_bar_color=None):
    """Draw an alternating-shaded table row with optional left color bar."""
    bg = WHITE if i % 2 == 0 else GRAY_L
    ax.add_patch(FancyBboxPatch((lm, y), rm - lm, row_h,
                                boxstyle="square,pad=0",
                                facecolor=bg, edgecolor="none", zorder=1))
    # Hairline bottom border
    ax.plot([lm, rm], [y, y], color=GRAY_M, linewidth=0.4, zorder=2)
    if left_bar_color:
        ax.add_patch(FancyBboxPatch((lm, y), 0.004, row_h,
                                    boxstyle="square,pad=0",
                                    facecolor=left_bar_color, edgecolor="none", zorder=2))


# ─────────────────────────────────────────────
#  FETCH MARKET NEWS
# ─────────────────────────────────────────────
def fetch_market_news(max_headlines=6, max_per_source=2):
    feeds = [
        ("Reuters",       "https://feeds.reuters.com/reuters/businessNews"),
        ("CNBC Markets",  "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=15839135"),
        ("MarketWatch",   "https://feeds.marketwatch.com/marketwatch/realtimeheadlines/"),
        ("Yahoo Finance", "https://finance.yahoo.com/news/rssindex"),
    ]
    headlines = []
    for source_name, feed_url in feeds:
        if len(headlines) >= max_headlines:
            break
        count = 0
        try:
            req = urllib.request.Request(feed_url,
                headers={"User-Agent": "Mozilla/5.0 (compatible; market-pulse/1.0)"})
            with urllib.request.urlopen(req, timeout=6) as resp:
                content = resp.read()
            root = ET.fromstring(content)
            for item in root.findall(".//item"):
                if len(headlines) >= max_headlines or count >= max_per_source:
                    break
                title = item.findtext("title", "").strip()
                title = title.replace("<![CDATA[", "").replace("]]>", "").strip()
                if title:
                    if len(title) > 85:
                        title = title[:82] + "..."
                    headlines.append({"title": title, "source": source_name})
                    count += 1
        except Exception:
            continue
    if not headlines:
        headlines = [{"title": "Unable to fetch live headlines.", "source": ""}]
    return headlines


# ─────────────────────────────────────────────
#  FETCH COMMODITY NEWS
# ─────────────────────────────────────────────
def fetch_commodity_news(max_headlines=5, max_per_source=2):
    """Pull commodity-focused headlines from specialist RSS feeds."""
    feeds = [
        ("Reuters Commodities", "https://feeds.reuters.com/reuters/commoditiesNews"),
        ("OilPrice.com",        "https://oilprice.com/rss/main"),
        ("Kitco",               "https://www.kitco.com/news/rss/feed.rss"),
        ("MarketWatch",         "https://feeds.marketwatch.com/marketwatch/realtimeheadlines/"),
    ]
    source_colors = {
        "Reuters Commodities": "#E65C00",
        "OilPrice.com":        "#8B0000",
        "Kitco":               "#B8860B",
        "MarketWatch":         "#006B3C",
    }
    headlines = []
    for source_name, feed_url in feeds:
        if len(headlines) >= max_headlines:
            break
        count = 0
        try:
            req = urllib.request.Request(feed_url,
                headers={"User-Agent": "Mozilla/5.0 (compatible; market-pulse/1.0)"})
            with urllib.request.urlopen(req, timeout=6) as resp:
                content = resp.read()
            root = ET.fromstring(content)
            for item in root.findall(".//item"):
                if len(headlines) >= max_headlines or count >= max_per_source:
                    break
                title = item.findtext("title", "").strip()
                title = title.replace("<![CDATA[", "").replace("]]>", "").strip()
                if title:
                    if len(title) > 85:
                        title = title[:82] + "..."
                    headlines.append({
                        "title":  title,
                        "source": source_name,
                        "color":  source_colors.get(source_name, GRAY_D),
                    })
                    count += 1
        except Exception:
            continue
    if not headlines:
        headlines = [{"title": "Unable to fetch commodity headlines.", "source": "", "color": GRAY_D}]
    return headlines


# ─────────────────────────────────────────────
#  FETCH CRYPTO NEWS
# ─────────────────────────────────────────────
def fetch_crypto_news(max_headlines=5, max_per_source=2):
    """Pull crypto-focused headlines from specialist RSS feeds."""
    feeds = [
        ("CoinDesk",      "https://www.coindesk.com/arc/outboundfeeds/rss/"),
        ("Bitcoin.com",   "https://news.bitcoin.com/feed/"),
        ("Decrypt",       "https://decrypt.co/feed"),
        ("CoinTelegraph", "https://cointelegraph.com/rss"),
    ]
    source_colors = {
        "CoinDesk":      "#0066CC",
        "Bitcoin.com":   "#F7931A",
        "Decrypt":       "#1A1A2E",
        "CoinTelegraph": "#2B9348",
    }
    headlines = []
    for source_name, feed_url in feeds:
        if len(headlines) >= max_headlines:
            break
        count = 0
        try:
            req = urllib.request.Request(feed_url,
                headers={"User-Agent": "Mozilla/5.0 (compatible; market-pulse/1.0)"})
            with urllib.request.urlopen(req, timeout=6) as resp:
                content = resp.read()
            root = ET.fromstring(content)
            for item in root.findall(".//item"):
                if len(headlines) >= max_headlines or count >= max_per_source:
                    break
                title = item.findtext("title", "").strip()
                title = title.replace("<![CDATA[", "").replace("]]>", "").strip()
                if title:
                    if len(title) > 85:
                        title = title[:82] + "..."
                    headlines.append({
                        "title":  title,
                        "source": source_name,
                        "color":  source_colors.get(source_name, GRAY_D),
                    })
                    count += 1
        except Exception:
            continue
    if not headlines:
        headlines = [{"title": "Unable to fetch crypto headlines.", "source": "", "color": GRAY_D}]
    return headlines


# ─────────────────────────────────────────────
#  FETCH COMPANY LOGO
# ─────────────────────────────────────────────
def fetch_ticker_logo(ticker):
    """Return a numpy RGBA image array for the ticker's logo, or None.
    Uses a hardcoded domain map first, then falls back to yfinance website field.
    Fetches via Google's favicon service at 256 px."""
    import numpy as np

    # Hardcoded domain map — most reliable, covers all current holdings
    DOMAIN_MAP = {
        "NVDA":  "nvidia.com",
        "PLTR":  "palantir.com",
        "MSTR":  "bitcoin.org",
        "IBM":   "ibm.com",
        "MU":    "micron.com",
        "XLF":   "sectorspdr.com",   # State Street SPDR Financials ETF
        "SMHX":  "vaneck.com",        # VanEck Semiconductor ETF (hedged)
    }

    try:
        import numpy as np
        domain = DOMAIN_MAP.get(ticker)

        if not domain:
            # Try yfinance website field as fallback
            info    = yf.Ticker(ticker).info
            website = info.get("website", "")
            if website:
                domain = (website
                          .replace("https://", "")
                          .replace("http://", "")
                          .replace("www.", "")
                          .split("/")[0])

        if not domain:
            print(f"  Logo {ticker}: no domain found")
            return None

        logo_url = f"https://www.google.com/s2/favicons?domain={domain}&sz=256"
        req = urllib.request.Request(
            logo_url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; market-pulse/1.0)"})
        with urllib.request.urlopen(req, timeout=6) as resp:
            img_data = resp.read()

        from PIL import Image
        img = Image.open(io.BytesIO(img_data)).convert("RGBA")
        arr = np.array(img)
        print(f"  Logo {ticker}: ✅ {arr.shape}")
        return arr

    except Exception as e:
        print(f"  Logo {ticker}: ❌ {e}")
        return None


# ─────────────────────────────────────────────
#  FETCH INDICES / COMMODITIES
# ─────────────────────────────────────────────
def fetch_price_series(symbol_map):
    """Generic fetcher for indices or commodities dict."""
    data = {}
    for symbol, meta in symbol_map.items():
        try:
            df = yf.download(symbol, period=PERIOD, interval=INTERVAL, progress=False)
            if df.empty:
                continue
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            df.dropna(inplace=True)
            data[symbol] = {"df": df, "meta": meta}
        except Exception:
            continue
    return data


# ─────────────────────────────────────────────
#  RATING + OUTLOOK HELPERS
# ─────────────────────────────────────────────
def score_to_rating(score):
    """Convert numeric score to (stars, advisory_label, color)."""
    if score >= 4:    return 5, "STRONG BUY",  GREEN
    elif score >= 2:  return 4, "BUY",          "#16A34A"
    elif score >= 0:  return 3, "HOLD",          AMBER
    elif score >= -2: return 2, "SELL",          "#EA580C"
    else:             return 1, "STRONG SELL",   RED


def _build_outlook_text(result, df):
    """Generate a 2–3 sentence outlook summary from indicator signals."""
    score   = result["score"]
    signals = result["signals"]
    rsi_val = round(float(df["RSI"].iloc[-1]), 1)

    if score >= 4:
        tone = "The technical setup is strongly bullish with broad indicator agreement."
    elif score >= 2:
        tone = "Indicators lean bullish with more buy signals than sell signals."
    elif score >= 0:
        tone = "The technical picture is mixed — no clear directional conviction."
    elif score >= -2:
        tone = "Indicators lean bearish with more sell signals than buy signals."
    else:
        tone = "The technical setup is broadly bearish across key indicators."

    if rsi_val >= 70:
        rsi_txt = f"RSI at {rsi_val} is overbought — momentum is extended and a pullback is possible."
    elif rsi_val <= 30:
        rsi_txt = f"RSI at {rsi_val} is oversold — a relief bounce may be near."
    elif rsi_val >= 55:
        rsi_txt = f"RSI at {rsi_val} shows positive momentum without being overbought."
    elif rsi_val <= 45:
        rsi_txt = f"RSI at {rsi_val} reflects mild bearish pressure."
    else:
        rsi_txt = f"RSI at {rsi_val} sits in neutral territory."

    vol_sig = next((s for s in signals if s[1] == "Volume"), None)
    if vol_sig and "BUY" in vol_sig[0]:
        vol_txt = "Volume confirms the move with strong participation."
    elif vol_sig and "SELL" in vol_sig[0]:
        vol_txt = "Volume shows heavy selling conviction on the decline."
    else:
        vol_txt = "Volume is near average — no strong conviction either way."

    return f"{tone} {rsi_txt} {vol_txt}"


def fetch_ticker_news(ticker, max_items=3):
    """Return list of recent news dicts {title, source} for the ticker."""
    try:
        items = yf.Ticker(ticker).news or []
        return [{"title": i.get("title", ""), "source": i.get("publisher", "")}
                for i in items[:max_items] if i.get("title")]
    except Exception:
        return []


# ─────────────────────────────────────────────
#  FETCH & ANALYZE TICKER
# ─────────────────────────────────────────────
def fetch_and_analyze(ticker):
    print(f"  Fetching {ticker}...")
    df = yf.download(ticker, period=PERIOD, interval=INTERVAL, progress=False)
    if df.empty:
        return None, None
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.dropna(inplace=True)

    df[f"MA{MA_SHORT}"] = df["Close"].rolling(window=MA_SHORT).mean()
    df[f"MA{MA_LONG}"]  = df["Close"].rolling(window=MA_LONG).mean()
    df["RSI"]           = ta_lib.momentum.RSIIndicator(close=df["Close"], window=RSI_PERIOD).rsi()
    m                   = ta_lib.trend.MACD(close=df["Close"], window_slow=26, window_fast=12, window_sign=9)
    df["MACD"]          = m.macd()
    df["MACD_Signal"]   = m.macd_signal()
    df["MACD_Hist"]     = m.macd_diff()
    bb                  = ta_lib.volatility.BollingerBands(close=df["Close"], window=BB_PERIOD, window_dev=BB_STD)
    df["BB_Upper"]      = bb.bollinger_hband()
    df["BB_Mid"]        = bb.bollinger_mavg()
    df["BB_Lower"]      = bb.bollinger_lband()
    try:
        adx_ind         = ta_lib.trend.ADXIndicator(high=df["High"], low=df["Low"], close=df["Close"], window=14)
        df["ADX"]       = adx_ind.adx()
        df["ADX_pos"]   = adx_ind.adx_pos()
        df["ADX_neg"]   = adx_ind.adx_neg()
    except Exception:
        pass
    df.dropna(inplace=True)

    latest = df.iloc[-1]
    prev   = df.iloc[-2]
    signals, score = [], 0

    if latest[f"MA{MA_SHORT}"] > latest[f"MA{MA_LONG}"]:
        signals.append(("✅ BUY",     "Moving Averages", f"MA{MA_SHORT} ABOVE MA{MA_LONG}")); score += 1
    else:
        signals.append(("🔴 SELL",    "Moving Averages", f"MA{MA_SHORT} BELOW MA{MA_LONG}")); score -= 1
    if prev[f"MA{MA_SHORT}"] <= prev[f"MA{MA_LONG}"] and latest[f"MA{MA_SHORT}"] > latest[f"MA{MA_LONG}"]:
        signals.append(("⚡ ALERT", "Moving Averages", "GOLDEN CROSS just occurred!")); score += 1
    elif prev[f"MA{MA_SHORT}"] >= prev[f"MA{MA_LONG}"] and latest[f"MA{MA_SHORT}"] < latest[f"MA{MA_LONG}"]:
        signals.append(("⚡ ALERT", "Moving Averages", "DEATH CROSS just occurred!")); score -= 1

    rsi_val = round(float(latest["RSI"]), 2)
    if rsi_val < RSI_OVERSOLD:
        signals.append(("✅ BUY",     "RSI", f"RSI={rsi_val} Oversold")); score += 1
    elif rsi_val > RSI_OVERBOUGHT:
        signals.append(("🔴 SELL",    "RSI", f"RSI={rsi_val} Overbought")); score -= 1
    else:
        signals.append(("⚪ NEUTRAL", "RSI", f"RSI={rsi_val} Neutral"))

    mv, sv = round(float(latest["MACD"]), 4), round(float(latest["MACD_Signal"]), 4)
    if latest["MACD"] > latest["MACD_Signal"]:
        signals.append(("✅ BUY",  "MACD", f"MACD({mv}) ABOVE Signal({sv})")); score += 1
    else:
        signals.append(("🔴 SELL", "MACD", f"MACD({mv}) BELOW Signal({sv})")); score -= 1
    if prev["MACD_Hist"] < 0 and latest["MACD_Hist"] > 0:
        signals.append(("⚡ ALERT", "MACD", "Histogram crossed above zero")); score += 1
    elif prev["MACD_Hist"] > 0 and latest["MACD_Hist"] < 0:
        signals.append(("⚡ ALERT", "MACD", "Histogram crossed below zero")); score -= 1

    close    = round(float(latest["Close"]), 2)
    bb_upper = round(float(latest["BB_Upper"]), 2)
    bb_lower = round(float(latest["BB_Lower"]), 2)
    if float(latest["Close"]) < float(latest["BB_Lower"]):
        signals.append(("✅ BUY",     "Bollinger Bands", f"Below lower band")); score += 1
    elif float(latest["Close"]) > float(latest["BB_Upper"]):
        signals.append(("🔴 SELL",    "Bollinger Bands", f"Above upper band")); score -= 1
    else:
        signals.append(("⚪ NEUTRAL", "Bollinger Bands", f"Inside bands"))

    # Volume signal
    if "Volume" in df.columns:
        vol_ma20  = df["Volume"].rolling(20).mean()
        vol_ratio = float(df["Volume"].iloc[-1]) / max(float(vol_ma20.iloc[-1]), 1)
        price_up  = float(df["Close"].iloc[-1]) > float(df["Close"].iloc[-2])
        if vol_ratio >= 1.3 and price_up:
            signals.append(("✅ BUY",     "Volume", f"High-vol up day ({vol_ratio:.1f}× avg)")); score += 1
        elif vol_ratio >= 1.3 and not price_up:
            signals.append(("🔴 SELL",    "Volume", f"High-vol down day ({vol_ratio:.1f}× avg)")); score -= 1
        else:
            signals.append(("⚪ NEUTRAL", "Volume", f"Volume {vol_ratio:.1f}× 20-day avg"))

    # ADX signal
    if "ADX" in df.columns:
        adx_val = round(float(df["ADX"].iloc[-1]), 1)
        pos_val = float(df["ADX_pos"].iloc[-1])
        neg_val = float(df["ADX_neg"].iloc[-1])
        if adx_val >= 25 and pos_val > neg_val:
            signals.append(("✅ BUY",     "ADX", f"Strong uptrend (ADX={adx_val})")); score += 1
        elif adx_val >= 25 and pos_val < neg_val:
            signals.append(("🔴 SELL",    "ADX", f"Strong downtrend (ADX={adx_val})")); score -= 1
        else:
            signals.append(("⚪ NEUTRAL", "ADX", f"No strong trend (ADX={adx_val})"))

    verdict = "📈 BULLISH" if score >= 2 else ("📉 BEARISH" if score <= -2 else "📊 MIXED")
    return df, {"ticker": ticker, "score": score, "verdict": verdict,
                "price": close, "date": df.index[-1].date(), "signals": signals}


def fetch_earnings(ticker):
    try:
        cal = yf.Ticker(ticker).calendar
        if cal is None:
            return "N/A"
        if isinstance(cal, dict):
            ed = cal.get("Earnings Date", None)
            if ed:
                return str(ed[0])[:10] if isinstance(ed, list) else str(ed)[:10]
        elif hasattr(cal, "loc") and "Earnings Date" in cal.index:
            ed = cal.loc["Earnings Date"]
            return str(ed.iloc[0])[:10] if hasattr(ed, "iloc") else str(ed)[:10]
    except Exception:
        pass
    return "N/A"


# ─────────────────────────────────────────────
#  PAGE 1: COVER
# ─────────────────────────────────────────────
def build_cover_page(all_data, all_results, extra_info, market_news, page_num, total_pages, pdf):
    fig = plt.figure(figsize=(16, 14))
    fig.patch.set_facecolor(BG)

    report_date = all_results[0]["date"]

    # ── CUSTOM COVER HEADER ──────────────────────────────
    ax_h = fig.add_axes([0, 0.915, 1, 0.085])
    ax_h.set_xlim(0, 1); ax_h.set_ylim(0, 1)
    ax_h.axis("off")

    # Full navy background
    ax_h.add_patch(FancyBboxPatch((0, 0), 1, 1, boxstyle="square,pad=0",
                                  facecolor=NAVY, edgecolor="none",
                                  transform=ax_h.transAxes, zorder=1))
    # Amber accent bar on left
    ax_h.add_patch(FancyBboxPatch((0, 0), 0.005, 1, boxstyle="square,pad=0",
                                  facecolor=AMBER, edgecolor="none",
                                  transform=ax_h.transAxes, zorder=2))
    # Thin amber bottom rule
    ax_h.add_patch(FancyBboxPatch((0, 0), 1, 0.045, boxstyle="square,pad=0",
                                  facecolor=AMBER, edgecolor="none",
                                  transform=ax_h.transAxes, zorder=2))

    # Title
    ax_h.text(0.022, 0.64, "MARKET PULSE REPORT",
              color=WHITE, fontsize=26, fontweight="bold",
              transform=ax_h.transAxes, va="center", zorder=3)
    # Tagline
    ax_h.text(0.022, 0.22, "D A I L Y   M A R K E T   I N T E L L I G E N C E",
              color=AMBER, fontsize=9, fontweight="bold",
              transform=ax_h.transAxes, va="center", zorder=3)

    # Vertical divider before date box
    ax_h.add_patch(FancyBboxPatch((0.74, 0.12), 0.002, 0.76, boxstyle="square,pad=0",
                                  facecolor="#FFFFFF22", edgecolor="none",
                                  transform=ax_h.transAxes, zorder=2))
    # Date box background
    ax_h.add_patch(FancyBboxPatch((0.745, 0.08), 0.25, 0.84, boxstyle="square,pad=0",
                                  facecolor="#FFFFFF11", edgecolor="none",
                                  transform=ax_h.transAxes, zorder=2))
    # Day of week
    day_str  = report_date.strftime("%A").upper()
    ax_h.text(0.870, 0.72, day_str,
              color=AMBER, fontsize=9, fontweight="bold",
              transform=ax_h.transAxes, va="center", ha="center", zorder=3)
    # Full date
    date_str = report_date.strftime("%B %d,  %Y").upper()
    ax_h.text(0.870, 0.28, date_str,
              color=WHITE, fontsize=15, fontweight="bold",
              transform=ax_h.transAxes, va="center", ha="center", zorder=3)

    add_page_footer(fig, f"Page {page_num} of {total_pages}   ·   Cover")

    ax = fig.add_axes([0, 0.03, 1, 0.88])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.set_facecolor(BG)

    lm, rm = 0.04, 0.97

    # ── PERFORMANCE TABLE ────────────────────────────────
    ax.text(lm, 0.976, "YESTERDAY'S PERFORMANCE",
            color=NAVY, fontsize=11, fontweight="bold", va="center", zorder=3)

    cx = {"ticker": lm + 0.012, "price": 0.230, "change": 0.355,
          "pct": 0.470, "score": 0.556, "signal": 0.635, "earnings": rm - 0.012}
    row_h   = 0.058
    tbl_top = 0.950

    draw_table_header(ax, lm, rm, tbl_top, 0.030,
        [(cx["ticker"],   "TICKER",   "left"),
         (cx["price"],    "PRICE",    "right"),
         (cx["change"],   "CHANGE",   "right"),
         (cx["pct"],      "% CHG",    "right"),
         (cx["score"],    "SCORE",    "center"),
         (cx["signal"],   "SIGNAL",   "left"),
         (cx["earnings"], "EARNINGS", "right")])

    # Sort by daily % change
    def pct_chg(r):
        d = all_data[r["ticker"]]
        return (float(d.iloc[-1]["Close"]) - float(d.iloc[-2]["Close"])) / float(d.iloc[-2]["Close"]) * 100

    for i, result in enumerate(sorted(all_results, key=pct_chg, reverse=True)):
        ticker     = result["ticker"]
        df         = all_data[ticker]
        prev_close = float(df.iloc[-2]["Close"])
        last_close = result["price"]
        change     = last_close - prev_close
        pct        = (change / prev_close) * 100
        chg_color  = GREEN if change >= 0 else RED
        arrow      = "+" if change >= 0 else ""
        score      = result["score"]
        v_short    = "BULLISH" if score >= 2 else ("BEARISH" if score <= -2 else "MIXED")
        v_color    = GREEN if score >= 2 else (RED if score <= -2 else AMBER)
        earnings   = extra_info.get(ticker, "N/A")

        row_y  = tbl_top - (i + 1) * row_h
        row_cy = row_y + row_h * 0.5
        draw_table_row(ax, lm, rm, row_y, row_h, i, left_bar_color=chg_color)

        ax.text(cx["ticker"],   row_cy, ticker,                       color=NAVY,      fontsize=13, fontweight="bold", va="center", ha="left",   zorder=3)
        ax.text(cx["price"],    row_cy, f"${last_close:,.2f}",        color="#1E293B", fontsize=12, va="center", ha="right",  zorder=3)
        ax.text(cx["change"],   row_cy, f"{arrow}${abs(change):.2f}", color=chg_color, fontsize=12, fontweight="bold", va="center", ha="right",  zorder=3)
        ax.text(cx["pct"],      row_cy, f"{arrow}{pct:.2f}%",         color=chg_color, fontsize=12, fontweight="bold", va="center", ha="right",  zorder=3)
        # Score circle badge
        sc_r = row_h * 0.36
        ax.add_patch(FancyBboxPatch(
            (cx["score"] - sc_r, row_cy - sc_r), sc_r * 2, sc_r * 2,
            boxstyle="round,pad=0.004",
            facecolor=v_color, alpha=0.15,
            edgecolor=v_color, linewidth=0.8, zorder=2))
        ax.text(cx["score"], row_cy, f"{score:+d}",
                color=v_color, fontsize=11, fontweight="bold",
                va="center", ha="center", zorder=3)

        # Signal pill badge
        sig_w = len(v_short) * 0.0078 + 0.022
        sig_x = cx["signal"]
        ax.add_patch(FancyBboxPatch(
            (sig_x, row_cy - row_h * 0.30), sig_w, row_h * 0.60,
            boxstyle="round,pad=0.003",
            facecolor=v_color, alpha=0.13,
            edgecolor=v_color, linewidth=0.7, zorder=2))
        ax.text(sig_x + sig_w / 2, row_cy, v_short,
                color=v_color, fontsize=10, fontweight="bold",
                va="center", ha="center", zorder=3)
        ax.text(cx["earnings"], row_cy, earnings,                     color=GRAY_D,    fontsize=11, va="center", ha="right",  zorder=3)

    hdr_h        = 0.030
    table_bottom = tbl_top - len(all_results) * row_h
    # Outer border rectangle around the whole table
    ax.add_patch(FancyBboxPatch((lm, table_bottom), rm - lm,
                                hdr_h + len(all_results) * row_h,
                                boxstyle="square,pad=0",
                                facecolor="none", edgecolor=GRAY_M,
                                linewidth=0.8, zorder=4))

    # ── MARKET HEADLINES ────────────────────────────────
    source_colors = {
        "Reuters":       "#E65C00",
        "CNBC Markets":  "#CC0000",
        "MarketWatch":   "#006B3C",
        "Yahoo Finance": "#5B21B6",
    }

    hl_top = table_bottom - 0.032
    draw_section_title(ax, lm, hl_top + 0.006, "MARKET HEADLINES")
    ax.plot([lm, rm], [hl_top - 0.010, hl_top - 0.010], color=GRAY_M, linewidth=0.6)

    card_h, card_gap = 0.055, 0.007
    y_card = hl_top - 0.040

    for article in market_news:
        title     = article.get("title", "")
        source    = article.get("source", "")
        src_color = source_colors.get(source, GRAY_D)
        card_bot  = y_card - card_h

        # Left color bar (drawn first, no border)
        ax.add_patch(FancyBboxPatch((lm, card_bot), 0.005, card_h,
                                    boxstyle="square,pad=0",
                                    facecolor=src_color, edgecolor="none", zorder=2))
        # Card body starts after the bar so border never overlaps it
        ax.add_patch(FancyBboxPatch((lm + 0.005, card_bot), rm - lm - 0.005, card_h,
                                    boxstyle="square,pad=0",
                                    facecolor=WHITE, edgecolor=GRAY_M,
                                    linewidth=0.5, zorder=1))

        card_cy = card_bot + card_h * 0.5
        ax.text(lm + 0.016, card_cy, title,
                color="#1E293B", fontsize=11, va="center", zorder=3)

        # Source pill
        badge_w = len(source) * 0.0060 + 0.018
        ax.add_patch(FancyBboxPatch((rm - badge_w - 0.004, card_cy - 0.013),
                                    badge_w, 0.026,
                                    boxstyle="round,pad=0.003",
                                    facecolor=src_color, alpha=0.10,
                                    edgecolor=src_color, linewidth=0.5, zorder=2))
        ax.text(rm - badge_w * 0.5 - 0.004, card_cy, source,
                color=src_color, fontsize=9, fontweight="bold",
                ha="center", va="center", zorder=3)

        y_card -= (card_h + card_gap)

    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)
    print("  Added page: Cover")


# ─────────────────────────────────────────────
#  SHARED: TABLE + CHART PAGE (Indices / Commodities)
# ─────────────────────────────────────────────
def build_market_overview_page(data, symbol_map, page_title, subtitle, color_key_idx,
                                chart_title, page_num, total_pages, footer_label, pdf,
                                news=None):
    fig = plt.figure(figsize=(16, 14))
    fig.patch.set_facecolor(BG)

    draw_page_header(fig, title=page_title, subtitle=subtitle)
    add_page_footer(fig, f"Page {page_num} of {total_pages}   ·   {footer_label}")

    if not data:
        fig.text(0.5, 0.5, "No data available.", ha="center", va="center", fontsize=14)
        pdf.savefig(fig, bbox_inches="tight")
        plt.close(fig)
        return

    if news:
        gs = gridspec.GridSpec(3, 1, figure=fig, top=0.910, bottom=0.09,
                               left=0.05, right=0.97,
                               hspace=0.40, height_ratios=[1, 1.2, 0.75])
    else:
        gs = gridspec.GridSpec(2, 1, figure=fig, top=0.910, bottom=0.09,
                               left=0.05, right=0.97,
                               hspace=0.35, height_ratios=[1, 1.5])

    # ── TABLE ───────────────────────────────────────────
    ax_t = fig.add_subplot(gs[0])
    ax_t.set_facecolor(BG)
    ax_t.set_xlim(0, 1)
    ax_t.set_ylim(0, 1)
    ax_t.axis("off")

    lm, rm = 0.01, 0.97
    cx = {"name": lm + 0.012, "cat": 0.34, "price": 0.54,
          "change": 0.68, "pct": 0.80, "ytd": rm - 0.008}
    row_h   = min(0.80 / (len(data) + 1), 0.115)
    tbl_top = 0.96

    draw_table_header(ax_t, lm, rm, tbl_top, 0.040 if row_h > 0.070 else row_h * 0.55,
        [(cx["name"],   "NAME",    "left"),
         (cx["cat"],    "CATEGORY","left"),
         (cx["price"],  "LEVEL",   "right"),
         (cx["change"], "CHANGE",  "right"),
         (cx["pct"],    "% CHG",   "right"),
         (cx["ytd"],    "YTD %",   "right")])

    # Compute % changes and sort descending
    rows = []
    report_year = list(data.values())[0]["df"].index[-1].year
    ytd_start   = f"{report_year}-01-01"
    for sym, info in data.items():
        df   = info["df"]
        meta = info["meta"]
        name = meta[0]
        cat  = meta[1]
        last = float(df.iloc[-1]["Close"])
        prev = float(df.iloc[-2]["Close"])
        chg  = last - prev
        pct  = (chg / prev) * 100
        ytd_pct = None
        try:
            ytd_df = df[df.index >= ytd_start]
            if not ytd_df.empty:
                ytd_pct = (last - float(ytd_df.iloc[0]["Close"])) / float(ytd_df.iloc[0]["Close"]) * 100
        except Exception:
            pass
        rows.append((sym, name, cat, last, chg, pct, ytd_pct))

    rows.sort(key=lambda r: r[5], reverse=True)

    hdr_h = 0.040 if row_h > 0.070 else row_h * 0.55
    for i, (sym, name, cat, last, chg, pct, ytd_pct) in enumerate(rows):
        chg_color  = GREEN if chg >= 0 else RED
        arrow      = "+" if chg >= 0 else ""
        cat_color  = SECTOR_COLORS.get(cat, GRAY_D)
        row_y      = tbl_top - hdr_h - (i + 1) * row_h
        row_cy     = row_y + row_h * 0.5

        draw_table_row(ax_t, lm, rm, row_y, row_h, i, left_bar_color=cat_color)

        ax_t.text(cx["name"],   row_cy, name,                      color=NAVY,      fontsize=12, fontweight="bold", va="center", ha="left",  zorder=3)
        ax_t.text(cx["cat"],    row_cy, cat,                       color=cat_color, fontsize=11, fontweight="bold", va="center", ha="left",  zorder=3)
        ax_t.text(cx["price"],  row_cy, f"{last:,.2f}",            color="#1E293B", fontsize=12, va="center", ha="right", zorder=3)
        ax_t.text(cx["change"], row_cy, f"{arrow}{abs(chg):,.2f}", color=chg_color, fontsize=12, fontweight="bold", va="center", ha="right", zorder=3)
        ax_t.text(cx["pct"],    row_cy, f"{arrow}{pct:.2f}%",      color=chg_color, fontsize=12, fontweight="bold", va="center", ha="right", zorder=3)
        if ytd_pct is not None:
            ytd_c = GREEN if ytd_pct >= 0 else RED
            ax_t.text(cx["ytd"], row_cy, f"{'+'if ytd_pct>=0 else ''}{ytd_pct:.1f}%",
                      color=ytd_c, fontsize=12, fontweight="bold", va="center", ha="right", zorder=3)
        else:
            ax_t.text(cx["ytd"], row_cy, "N/A", color=GRAY_D, fontsize=11, va="center", ha="right", zorder=3)

    # ── NORMALIZED CHART ────────────────────────────────
    ax_c = fig.add_subplot(gs[1])
    ax_c.set_facecolor("#FAFAFA")
    ax_c.set_title(chart_title, fontsize=12, fontweight="bold",
                   color=NAVY, pad=10, loc="left")

    palette = ["#1f77b4","#ff7f0e","#2ca02c","#d62728",
               "#9467bd","#8c564b","#e377c2","#17becf"]
    for idx, (sym, name, cat, *_) in enumerate(rows):
        df     = data[sym]["df"]
        closes = df["Close"].dropna()
        norm   = closes / float(closes.iloc[0]) * 100
        ax_c.plot(df.index[-len(norm):], norm, linewidth=1.8,
                  label=name, color=palette[idx % len(palette)])

    ax_c.axhline(100, color=GRAY_M, linewidth=1.0, linestyle="--")
    ax_c.set_ylabel("Base = 100", fontsize=10, color=GRAY_D)
    leg = ax_c.legend(loc="upper left", fontsize=9, framealpha=0.9, ncol=2, handlelength=4.0)
    for handle in leg.legend_handles:
        handle.set_linewidth(3.0)
    ax_c.grid(True, alpha=0.25, color=GRAY_M)
    ax_c.tick_params(labelsize=9, colors=GRAY_D)
    for spine in ax_c.spines.values():
        spine.set_edgecolor(GRAY_M)
        spine.set_linewidth(0.6)

    # ── COMMODITY NEWS PANEL (only when news provided) ──
    if news:
        ax_n = fig.add_subplot(gs[2])
        ax_n.set_facecolor(BG)
        ax_n.set_xlim(0, 1)
        ax_n.set_ylim(0, 1)
        ax_n.axis("off")

        nlm, nrm = 0.01, 0.99
        # Section title
        ax_n.add_patch(FancyBboxPatch((nlm, 0.88), 0.005, 0.10,
                                      boxstyle="square,pad=0",
                                      facecolor=NAVY, edgecolor="none", zorder=2))
        ax_n.text(nlm + 0.013, 0.935, "COMMODITY HEADLINES",
                  color=NAVY, fontsize=11, fontweight="bold", va="center", zorder=3)
        ax_n.plot([nlm, nrm], [0.87, 0.87], color=GRAY_M, linewidth=0.6, zorder=1)

        n_items  = len(news)
        card_h   = min(0.75 / n_items - 0.02, 0.13)
        card_gap = 0.015
        y_card   = 0.84

        for article in news:
            title     = article.get("title", "")
            source    = article.get("source", "")
            src_color = article.get("color", GRAY_D)
            card_bot  = y_card - card_h
            if card_bot < 0:
                break

            ax_n.add_patch(FancyBboxPatch((nlm, card_bot), 0.005, card_h,
                                          boxstyle="square,pad=0",
                                          facecolor=src_color, edgecolor="none", zorder=2))
            ax_n.add_patch(FancyBboxPatch((nlm + 0.005, card_bot), nrm - nlm - 0.005, card_h,
                                          boxstyle="square,pad=0",
                                          facecolor=WHITE, edgecolor=GRAY_M,
                                          linewidth=0.5, zorder=1))
            card_cy = card_bot + card_h * 0.5
            short_title = title[:62] + "..." if len(title) > 65 else title
            ax_n.text(nlm + 0.016, card_cy, short_title,
                      color="#1E293B", fontsize=9, va="center", zorder=3,
                      clip_on=True)
            badge_w = len(source) * 0.0058 + 0.018
            ax_n.add_patch(FancyBboxPatch((nrm - badge_w - 0.004, card_cy - 0.012),
                                          badge_w, 0.024,
                                          boxstyle="round,pad=0.003",
                                          facecolor=src_color, alpha=0.10,
                                          edgecolor=src_color, linewidth=0.5, zorder=2))
            ax_n.text(nrm - badge_w * 0.5 - 0.004, card_cy, source,
                      color=src_color, fontsize=8.5, fontweight="bold",
                      ha="center", va="center", zorder=3)
            y_card -= (card_h + card_gap)

    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)
    print(f"  Added page: {footer_label}")


# ─────────────────────────────────────────────
#  PAGES 4+: INDIVIDUAL TICKER CHARTS
# ─────────────────────────────────────────────
def build_ticker_page(ticker, df, result, page_num, total_pages, pdf):
    score                  = result["score"]
    stars, advisory, adv_color = score_to_rating(score)
    price      = result["price"]
    prev_close = float(df.iloc[-2]["Close"])
    chg_abs    = price - prev_close
    chg_pct    = chg_abs / prev_close * 100
    chg_sign   = "+" if chg_pct >= 0 else ""
    chg_color  = GREEN if chg_pct >= 0 else RED
    company    = TICKER_NAMES.get(ticker, ticker)

    fig = plt.figure(figsize=(16, 14))
    fig.patch.set_facecolor(BG)

    # ── HEADER ──────────────────────────────────────────────
    logo_img = fetch_ticker_logo(ticker)
    draw_page_header(fig,
        title          = company,
        subtitle       = f"{ticker}   ·   {result['date']}   ·   Period: {PERIOD}",
        logo_img       = logo_img,
        title_fontsize = 17)
    add_page_footer(fig, f"Page {page_num} of {total_pages}   ·   {ticker}")

    ax_h  = fig.axes[0]
    px    = 0.32 if logo_img is not None else 0.26
    ax_h.text(px,        0.68, f"${price:,.2f}",
              color=NAVY,      fontsize=15, fontweight="bold",
              transform=ax_h.transAxes, va="center")
    ax_h.text(px + 0.11, 0.68, f"{chg_sign}${abs(chg_abs):.2f}",
              color=chg_color, fontsize=13, fontweight="bold",
              transform=ax_h.transAxes, va="center")
    ax_h.text(px + 0.21, 0.68, f"{chg_sign}{chg_pct:.2f}%",
              color=chg_color, fontsize=13, fontweight="bold",
              transform=ax_h.transAxes, va="center")

    # Sector pill centered under % change
    sector_label, sector_color = TICKER_SECTOR_MAP.get(ticker, ("Equity", GRAY_D))
    sect_w     = len(sector_label) * 0.0058 + 0.022
    pct_center = px + 0.21 + 0.025
    sect_x     = pct_center - sect_w / 2
    ax_h.add_patch(FancyBboxPatch(
        (sect_x, 0.10), sect_w, 0.32,
        boxstyle="round,pad=0.003", facecolor=sector_color, alpha=0.15,
        edgecolor=sector_color, linewidth=0.8,
        transform=ax_h.transAxes, zorder=3, clip_on=False))
    ax_h.text(pct_center, 0.26, sector_label,
              color=sector_color, fontsize=9, fontweight="bold",
              transform=ax_h.transAxes, va="center", ha="center", zorder=4)

    # ── BODY: 5-row × 2-col grid ────────────────────────────
    gs = gridspec.GridSpec(5, 2, figure=fig,
                           top=0.910, bottom=0.05,
                           left=0.06, right=0.97,
                           hspace=0.50, wspace=0.10,
                           width_ratios=[1.1, 0.9],
                           height_ratios=[2.5, 1, 1, 1, 1])

    def style_ax(ax, title):
        ax.set_facecolor("#FAFAFA")
        ax.set_title(title, fontsize=9, color=NAVY, pad=4, loc="left", fontweight="bold")
        ax.grid(True, alpha=0.20, color=GRAY_M)
        ax.tick_params(labelsize=7.5, colors=GRAY_D)
        for sp in ax.spines.values():
            sp.set_edgecolor(GRAY_M); sp.set_linewidth(0.5)

    # Chart 1 — Price + MA + BB
    ax1 = fig.add_subplot(gs[0, 0])
    style_ax(ax1, "Price  ·  MA50 / MA200  ·  Bollinger Bands")
    ax1.plot(df.index, df["Close"],          "#2563EB", lw=1.6, label="Close",       zorder=3)
    ax1.plot(df.index, df[f"MA{MA_SHORT}"],  "#F59E0B", lw=1.1, label=f"MA{MA_SHORT}", ls="--")
    ax1.plot(df.index, df[f"MA{MA_LONG}"],   "#DC2626", lw=1.1, label=f"MA{MA_LONG}",  ls="--")
    ax1.plot(df.index, df["BB_Upper"],       "#475569", lw=1.5, ls="--", label="BB Upper")
    ax1.plot(df.index, df["BB_Lower"],       "#475569", lw=1.5, ls="--", label="BB Lower")
    ax1.fill_between(df.index, df["BB_Upper"], df["BB_Lower"], alpha=0.05, color="#94A3B8")
    leg1 = ax1.legend(loc="upper left", fontsize=7, framealpha=0.9, ncol=3, handlelength=2.5)
    for h in leg1.legend_handles: h.set_linewidth(2.0)

    # Chart 2 — Volume
    ax2 = fig.add_subplot(gs[1, 0])
    style_ax(ax2, "Volume")
    vol_colors = [GREEN if c >= o else RED
                  for c, o in zip(df["Close"], df["Open"])]
    ax2.bar(df.index, df["Volume"], color=vol_colors, alpha=0.65, width=0.8)
    ax2.plot(df.index, df["Volume"].rolling(20).mean(),
             color=NAVY, lw=1.0, ls="--", label="20d avg")
    ax2.yaxis.set_major_formatter(
        plt.FuncFormatter(lambda x, _: f"{x/1e6:.0f}M"))
    ax2.legend(fontsize=7, loc="upper left")

    # Chart 3 — RSI
    ax3 = fig.add_subplot(gs[2, 0])
    style_ax(ax3, "RSI (14)")
    ax3.plot(df.index, df["RSI"], "#7C3AED", lw=1.2)
    ax3.axhline(70, color=RED,    lw=0.8, ls="--", alpha=0.7, label="70")
    ax3.axhline(30, color=GREEN,  lw=0.8, ls="--", alpha=0.7, label="30")
    ax3.axhline(50, color=GRAY_D, lw=0.5, ls=":",  alpha=0.4)
    ax3.fill_between(df.index, df["RSI"], 70, where=(df["RSI"] >= 70), alpha=0.12, color=RED)
    ax3.fill_between(df.index, df["RSI"], 30, where=(df["RSI"] <= 30), alpha=0.12, color=GREEN)
    ax3.set_ylim(0, 100)
    ax3.text(0.99, 70, "Overbought", transform=ax3.get_yaxis_transform(),
             fontsize=6.5, color=RED, ha="right", va="bottom", fontstyle="italic")
    ax3.text(0.99, 30, "Oversold",   transform=ax3.get_yaxis_transform(),
             fontsize=6.5, color=GREEN, ha="right", va="top",    fontstyle="italic")
    ax3.legend(fontsize=7, loc="upper left", ncol=2)

    # Chart 4 — MACD
    ax4 = fig.add_subplot(gs[3, 0])
    style_ax(ax4, "MACD (12 / 26 / 9)")
    ax4.plot(df.index, df["MACD"],        "#2563EB", lw=1.2, label="MACD")
    ax4.plot(df.index, df["MACD_Signal"], "#F59E0B", lw=1.0, ls="--", label="Signal")
    ax4.bar(df.index, df["MACD_Hist"],
            color=[GREEN if v >= 0 else RED for v in df["MACD_Hist"]],
            alpha=0.45, width=0.8)
    ax4.axhline(0, color=GRAY_D, lw=0.5)
    ax4.legend(fontsize=7, loc="upper left", ncol=2)

    # Chart 5 — ADX
    ax5 = fig.add_subplot(gs[4, 0])
    style_ax(ax5, "ADX  ·  Trend Strength")
    if "ADX" in df.columns:
        ax5.plot(df.index, df["ADX"],     NAVY,  lw=1.4, label="ADX")
        ax5.plot(df.index, df["ADX_pos"], GREEN, lw=1.0, ls="--", label="+DI")
        ax5.plot(df.index, df["ADX_neg"], RED,   lw=1.0, ls="--", label="-DI")
        ax5.axhline(25, color=AMBER, lw=0.8, ls=":", alpha=0.8, label="25")
        ax5.legend(fontsize=7, loc="upper left", ncol=4)

    # ── RIGHT PANEL — OUTLOOK ────────────────────────────────
    ax_r = fig.add_subplot(gs[:, 1])
    ax_r.set_xlim(0, 1); ax_r.set_ylim(0, 1)
    ax_r.axis("off")
    ax_r.add_patch(FancyBboxPatch((0, 0), 1, 1, boxstyle="square,pad=0",
                                   facecolor=WHITE, edgecolor=GRAY_M,
                                   linewidth=0.8, zorder=0))

    lm, rm = 0.07, 0.93
    y = 0.965

    # Advisory badge
    adv_w = len(advisory) * 0.036 + 0.08
    adv_x = 0.5 - adv_w / 2
    ax_r.add_patch(FancyBboxPatch((adv_x, y - 0.065), adv_w, 0.075,
                                   boxstyle="round,pad=0.005",
                                   facecolor=adv_color, alpha=0.18,
                                   edgecolor=adv_color, linewidth=1.8, zorder=2))
    ax_r.text(0.5, y - 0.028, advisory,
              color=adv_color, fontsize=15, fontweight="bold",
              va="center", ha="center", zorder=3)
    y -= 0.085

    # Stars
    star_str = "★" * stars + "☆" * (5 - stars)
    ax_r.text(0.5, y, star_str,
              color=AMBER, fontsize=24, fontweight="bold",
              va="center", ha="center", zorder=3)
    y -= 0.048
    ax_r.text(0.5, y, f"Score  {score:+d}   ·   {stars} / 5 stars",
              color=GRAY_D, fontsize=8, va="center", ha="center", zorder=3)
    y -= 0.026
    ax_r.plot([lm, rm], [y, y], color=GRAY_M, lw=0.8)
    y -= 0.022

    # Outlook text
    ax_r.add_patch(FancyBboxPatch((lm, y - 0.010), 0.004, 0.020,
                                   boxstyle="square,pad=0",
                                   facecolor=NAVY, edgecolor="none", zorder=2))
    ax_r.text(lm + 0.013, y, "OUTLOOK",
              color=NAVY, fontsize=9, fontweight="bold", va="center", zorder=3)
    y -= 0.030
    outlook = _build_outlook_text(result, df)
    words, lines_out, line = outlook.split(), [], ""
    for w in words:
        test = (line + " " + w).strip()
        if len(test) > 48:
            lines_out.append(line); line = w
        else:
            line = test
    if line: lines_out.append(line)
    for lt in lines_out[:4]:
        ax_r.text(lm, y, lt, color="#334155", fontsize=8, va="top", zorder=3)
        y -= 0.030
    y -= 0.008
    ax_r.plot([lm, rm], [y, y], color=GRAY_M, lw=0.8)
    y -= 0.022

    # Indicator signals
    ax_r.add_patch(FancyBboxPatch((lm, y - 0.010), 0.004, 0.020,
                                   boxstyle="square,pad=0",
                                   facecolor=NAVY, edgecolor="none", zorder=2))
    ax_r.text(lm + 0.013, y, "INDICATOR SIGNALS",
              color=NAVY, fontsize=9, fontweight="bold", va="center", zorder=3)
    y -= 0.032

    sig_colors = {"✅ BUY": GREEN, "🔴 SELL": RED,
                  "⚪ NEUTRAL": GRAY_D, "⚡ ALERT": AMBER}
    main_sigs = [s for s in result["signals"] if "ALERT" not in s[0]]
    for sig_type, indicator, detail in main_sigs[:7]:
        sc = sig_colors.get(sig_type, GRAY_D)
        ax_r.add_patch(FancyBboxPatch((lm, y - 0.009), 0.016, 0.018,
                                       boxstyle="round,pad=0.002",
                                       facecolor=sc, alpha=0.20,
                                       edgecolor=sc, linewidth=0.5, zorder=2))
        ax_r.text(lm + 0.008, y, "●", color=sc, fontsize=7,
                  va="center", ha="center", zorder=3)
        ax_r.text(lm + 0.026, y + 0.006, indicator,
                  color=NAVY, fontsize=8, fontweight="bold", va="center", zorder=3)
        ax_r.text(lm + 0.026, y - 0.012, detail,
                  color=GRAY_D, fontsize=7, va="center", zorder=3)
        y -= 0.038
    y -= 0.006
    ax_r.plot([lm, rm], [y, y], color=GRAY_M, lw=0.8)
    y -= 0.022

    # Recent news
    ax_r.add_patch(FancyBboxPatch((lm, y - 0.010), 0.004, 0.020,
                                   boxstyle="square,pad=0",
                                   facecolor=NAVY, edgecolor="none", zorder=2))
    ax_r.text(lm + 0.013, y, "RECENT NEWS",
              color=NAVY, fontsize=9, fontweight="bold", va="center", zorder=3)
    y -= 0.030
    card_h = 0.076
    for item in fetch_ticker_news(ticker):
        if y - card_h < 0.02:
            break
        title  = item.get("title", "")
        source = item.get("source", "")
        short  = title[:50] + "…" if len(title) > 53 else title
        ax_r.add_patch(FancyBboxPatch((lm, y - card_h), 0.004, card_h,
                                       boxstyle="square,pad=0",
                                       facecolor=NAVY, edgecolor="none", zorder=2))
        ax_r.add_patch(FancyBboxPatch((lm + 0.004, y - card_h), rm - lm - 0.004, card_h,
                                       boxstyle="square,pad=0",
                                       facecolor="#F8FAFC", edgecolor=GRAY_M,
                                       linewidth=0.5, zorder=1))
        cy = y - card_h / 2
        ax_r.text(lm + 0.016, cy + 0.016, short,
                  color="#1E293B", fontsize=7.5, va="center", zorder=3)
        ax_r.text(lm + 0.016, cy - 0.016, source,
                  color=GRAY_D, fontsize=7, fontweight="bold", va="center", zorder=3)
        y -= (card_h + 0.010)

    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)
    print(f"  Added page: {ticker}")


# ─────────────────────────────────────────────
#  RUN
# ─────────────────────────────────────────────
print(f"\nFetching holdings data: {', '.join(TICKERS)}\n")
all_data, all_results = {}, []
for ticker in TICKERS:
    df, result = fetch_and_analyze(ticker)
    if df is not None:
        all_data[ticker] = df
        all_results.append(result)

print("\nFetching earnings dates...")
extra_info = {t: fetch_earnings(t) for t in all_data}

print("Fetching global indices...")
indices_data = fetch_price_series(INDICES)

print("Fetching commodities...")
commodities_data = fetch_price_series(COMMODITIES)

print("Fetching cryptocurrency...")
crypto_data = fetch_price_series(CRYPTO)

print("Fetching market headlines...")
market_news = fetch_market_news(max_headlines=6)

print("Fetching commodity headlines...")
commodity_news = fetch_commodity_news(max_headlines=5)

print("Fetching crypto headlines...")
crypto_news = fetch_crypto_news(max_headlines=5)

# Terminal summary
for result in all_results:
    print(f"  {result['ticker']:<6} {result['verdict']}  Score: {result['score']:+d}")
print(f"\n⚠️  Educational purposes only.\n")

# Build PDF
total_pages = 4 + len(all_data)
pdf_file    = os.path.join(OUTPUT_DIR, "market_pulse_report.pdf")

with PdfPages(pdf_file) as pdf:
    build_cover_page(all_data, all_results, extra_info, market_news,
                     page_num=1, total_pages=total_pages, pdf=pdf)

    build_market_overview_page(
        data         = indices_data,
        symbol_map   = INDICES,
        page_title   = "GLOBAL MARKET INDICES",
        subtitle     = f"Major world indices — daily performance & 1-year comparison   ·   {PERIOD}",
        color_key_idx= 1,
        chart_title  = "1-Year Relative Performance (Normalized to 100)",
        page_num     = 2,
        total_pages  = total_pages,
        footer_label = "Global Indices",
        pdf          = pdf)

    build_market_overview_page(
        data         = commodities_data,
        symbol_map   = COMMODITIES,
        page_title   = "COMMODITIES",
        subtitle     = f"Global commodities — daily performance & 1-year comparison   ·   {PERIOD}",
        color_key_idx= 1,
        chart_title  = "1-Year Relative Performance (Normalized to 100)",
        page_num     = 3,
        total_pages  = total_pages,
        footer_label = "Commodities",
        pdf          = pdf,
        news         = commodity_news)

    build_market_overview_page(
        data         = crypto_data,
        symbol_map   = CRYPTO,
        page_title   = "CRYPTOCURRENCY",
        subtitle     = f"Major cryptocurrencies — daily performance & 1-year comparison   ·   {PERIOD}",
        color_key_idx= 1,
        chart_title  = "1-Year Relative Performance (Normalized to 100)",
        page_num     = 4,
        total_pages  = total_pages,
        footer_label = "Cryptocurrency",
        pdf          = pdf,
        news         = crypto_news)

    for page, (ticker, df) in enumerate(all_data.items(), start=5):
        result = next(r for r in all_results if r["ticker"] == ticker)
        build_ticker_page(ticker, df, result,
                          page_num=page, total_pages=total_pages, pdf=pdf)

print(f"\nReport saved: {pdf_file}  ({total_pages} pages)")

# ── AUTO-SYNC TO GITHUB ──────────────────────────────────────
import subprocess, datetime
try:
    today = datetime.date.today().strftime("%Y-%m-%d")
    subprocess.run(["git", "-C", OUTPUT_DIR, "add", "stock_analysis.py"], check=True)
    subprocess.run(["git", "-C", OUTPUT_DIR, "commit", "-m", f"Auto-sync: {today}"], check=True)
    subprocess.run(["git", "-C", OUTPUT_DIR, "push"], check=True)
    print("GitHub synced ✅")
except subprocess.CalledProcessError:
    print("GitHub sync skipped (no changes or not configured)")
