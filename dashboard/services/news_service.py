# ─────────────────────────────────────────────────────────────────────────────
# services/news_service.py  —  Bloomberg Terminal Dashboard  •  Market Pulse
#
# Wraps feedparser RSS + yfinance ticker news into a clean, cached interface.
# Dash callbacks call this instead of raw feedparser / yfinance directly.
# ─────────────────────────────────────────────────────────────────────────────

from __future__ import annotations

import datetime
import logging
from typing import Dict, List, Optional

import feedparser
import yfinance as yf
from cachetools import TTLCache

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Caches
# ─────────────────────────────────────────────────────────────────────────────

_rss_cache:    TTLCache = TTLCache(maxsize=30, ttl=300)   # 5-min RSS cache
_ticker_cache: TTLCache = TTLCache(maxsize=50, ttl=300)   # 5-min ticker news cache


# ─────────────────────────────────────────────────────────────────────────────
# RSS feed fetcher
# ─────────────────────────────────────────────────────────────────────────────

def fetch_rss(url: str, source_name: str = "", category: str = "MARKETS") -> List[Dict]:
    """
    Fetch and parse an RSS feed.

    Returns
    -------
    List of article dicts: {title, link, published, summary, source, category}
    """
    if url in _rss_cache:
        return _rss_cache[url]

    articles: List[Dict] = []
    try:
        feed = feedparser.parse(url)
        for entry in feed.entries[:20]:
            title  = getattr(entry, "title", "")
            link   = getattr(entry, "link", "")
            summary = getattr(entry, "summary", getattr(entry, "description", ""))
            pub    = getattr(entry, "published", "")

            if not title or not link:
                continue

            articles.append({
                "title":     title,
                "link":      link,
                "published": pub,
                "summary":   summary[:300] if summary else "",
                "source":    source_name,
                "category":  category,
            })
    except Exception as exc:
        logger.debug("news_service: RSS fetch failed %s — %s", url, exc)

    _rss_cache[url] = articles
    return articles


def fetch_all_rss(sources: List[Dict]) -> List[Dict]:
    """
    Fetch all RSS sources in *sources* list (same format as config.NEWS_SOURCES).
    Merges and deduplicates by link.

    Returns
    -------
    Sorted list of article dicts (most recent first, using published field).
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    all_articles: List[Dict] = []
    with ThreadPoolExecutor(max_workers=min(len(sources), 12)) as pool:
        futs = {
            pool.submit(fetch_rss, src["url"], src.get("name", ""), src.get("category", "MARKETS")): src
            for src in sources
        }
        for fut in as_completed(futs):
            try:
                articles = fut.result()
                all_articles.extend(articles)
            except Exception:
                pass

    # Deduplicate by link
    seen: set = set()
    unique: List[Dict] = []
    for a in all_articles:
        if a["link"] not in seen:
            seen.add(a["link"])
            unique.append(a)

    return unique


# ─────────────────────────────────────────────────────────────────────────────
# Ticker-specific news via yfinance
# ─────────────────────────────────────────────────────────────────────────────

def fetch_ticker_news(symbol: str, limit: int = 10) -> List[Dict]:
    """
    Fetch recent news for *symbol* via yfinance.

    Returns
    -------
    List of article dicts: {title, link, published, source, category}
    """
    cache_key = f"{symbol}_{limit}"
    if cache_key in _ticker_cache:
        return _ticker_cache[cache_key]

    articles: List[Dict] = []
    try:
        raw = yf.Ticker(symbol).news or []
        for item in raw[:limit]:
            title = item.get("title", "")
            link  = item.get("link", "") or item.get("url", "")
            pub   = item.get("providerPublishTime", 0)
            src   = item.get("publisher", "")

            if pub:
                pub_str = datetime.datetime.fromtimestamp(pub).strftime("%Y-%m-%d %H:%M")
            else:
                pub_str = ""

            if title:
                articles.append({
                    "title":     title,
                    "link":      link,
                    "published": pub_str,
                    "summary":   "",
                    "source":    src,
                    "category":  "PORTFOLIO",
                    "ticker":    symbol,
                })
    except Exception as exc:
        logger.debug("news_service: ticker news failed %s — %s", symbol, exc)

    _ticker_cache[cache_key] = articles
    return articles


# ─────────────────────────────────────────────────────────────────────────────
# Simple keyword classifier (mirrors existing data_manager logic)
# ─────────────────────────────────────────────────────────────────────────────

_GEO_KW   = {"war", "sanction", "nato", "geopolit", "conflict", "invasion", "nuclear",
              "missile", "terror", "military", "ukraine", "russia", "china", "taiwan"}
_MACRO_KW = {"fed", "federal reserve", "inflation", "cpi", "gdp", "interest rate",
              "recession", "fomc", "powell", "rate hike", "rate cut", "treasury",
              "yield curve", "jobs report", "payroll", "unemployment"}
_COMM_KW  = {"oil", "gold", "silver", "crude", "commodity", "copper", "nat gas",
              "energy", "opec", "barrel", "commodity"}


def classify_article(title: str, summary: str = "") -> str:
    """Classify an article into a category string."""
    text = (title + " " + summary).lower()
    if any(kw in text for kw in _GEO_KW):
        return "GEOPOLITICAL"
    if any(kw in text for kw in _MACRO_KW):
        return "MACRO"
    if any(kw in text for kw in _COMM_KW):
        return "COMMODITIES"
    return "MARKETS"
