"""
Search Abstraction Layer
─────────────────────────
Auto-selects the best available search provider based on API keys present.

Priority:
  1. Tavily API   — most reliable, deep content extraction, ~$0.001/search
  2. Brave Search — clean JSON API, generous free tier
  3. Google scraping — no API key needed, but subject to rate limiting

Usage:
    from src.search import web_search

    results = web_search("VP Sales B2B SaaS London site:linkedin.com/in", num_results=10)
    for r in results:
        print(r["url"], r["title"])

Each result is a dict: {url, title, description, provider}
"""

import logging
import os
import random
import re
import time
from typing import Optional

import requests
from bs4 import BeautifulSoup

try:
    from tavily import TavilyClient
    _TAVILY_AVAILABLE = True
except ImportError:
    _TAVILY_AVAILABLE = False

try:
    from googlesearch import search as _googlesearch
    _GOOGLESEARCH_AVAILABLE = True
except ImportError:
    _GOOGLESEARCH_AVAILABLE = False

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Rate limiting helpers
# ---------------------------------------------------------------------------

_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.4 Safari/605.1.15",
]


def _random_ua() -> str:
    return random.choice(_USER_AGENTS)


def _polite_sleep(min_s: float = 2.0, max_s: float = 5.0) -> None:
    delay = random.uniform(min_s, max_s)
    logger.debug("Search rate-limit delay: %.1fs", delay)
    time.sleep(delay)


def _with_retry(fn, retries: int = 3, base_delay: float = 2.0):
    """Call fn with exponential backoff on exception."""
    for attempt in range(retries):
        try:
            return fn()
        except Exception as exc:
            if attempt == retries - 1:
                raise
            wait = base_delay * (2 ** attempt) + random.uniform(0, 1)
            logger.warning("Search attempt %d/%d failed: %s — retrying in %.1fs",
                           attempt + 1, retries, exc, wait)
            time.sleep(wait)


# ---------------------------------------------------------------------------
# Provider: Tavily
# ---------------------------------------------------------------------------

def _tavily_search(query: str, num_results: int = 10) -> list[dict]:
    """Search via Tavily API. Returns structured, high-quality results."""
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key or not _TAVILY_AVAILABLE:
        raise RuntimeError("Tavily not configured")

    client = TavilyClient(api_key=api_key)
    def _call():
        resp = client.search(
            query=query,
            max_results=min(num_results, 20),
            search_depth="basic",
            include_answer=False,
        )
        return resp.get("results", [])

    raw = _with_retry(_call)
    results = [
        {
            "url": r.get("url", ""),
            "title": r.get("title", ""),
            "description": r.get("content", "")[:300],
            "provider": "tavily",
        }
        for r in raw
        if r.get("url")
    ]
    logger.info("Tavily returned %d results for: %s", len(results), query[:80])
    return results


# ---------------------------------------------------------------------------
# Provider: Brave Search API
# ---------------------------------------------------------------------------

_BRAVE_SEARCH_URL = "https://api.search.brave.com/res/v1/web/search"


def _brave_search(query: str, num_results: int = 10) -> list[dict]:
    """Search via Brave Search API."""
    api_key = os.getenv("BRAVE_API_KEY")
    if not api_key:
        raise RuntimeError("Brave Search not configured")

    headers = {
        "Accept": "application/json",
        "Accept-Encoding": "gzip",
        "X-Subscription-Token": api_key,
    }

    def _call():
        resp = requests.get(
            _BRAVE_SEARCH_URL,
            headers=headers,
            params={"q": query, "count": min(num_results, 20), "search_lang": "en"},
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()

    data = _with_retry(_call)
    raw = data.get("web", {}).get("results", [])
    results = [
        {
            "url": r.get("url", ""),
            "title": r.get("title", ""),
            "description": r.get("description", "")[:300],
            "provider": "brave",
        }
        for r in raw
        if r.get("url")
    ]
    logger.info("Brave returned %d results for: %s", len(results), query[:80])
    return results


# ---------------------------------------------------------------------------
# Provider: Google scraping (free fallback)
# ---------------------------------------------------------------------------

def _google_search(query: str, num_results: int = 10) -> list[dict]:
    """Scrape Google search results. Free but rate-limited."""
    results = []

    # Try googlesearch-python first (simpler)
    if _GOOGLESEARCH_AVAILABLE:
        try:
            _polite_sleep(2.0, 4.0)
            urls = list(_googlesearch(query, num_results=num_results, sleep_interval=2))
            results = [{"url": u, "title": "", "description": "", "provider": "google"} for u in urls]
            logger.info("googlesearch returned %d results for: %s", len(results), query[:80])
            return results
        except Exception as exc:
            logger.warning("googlesearch-python failed (%s), falling back to HTTP scrape", exc)

    # HTTP scrape fallback
    return _google_http_scrape(query, num_results)


def _google_http_scrape(query: str, num_results: int = 10) -> list[dict]:
    """Direct HTTP scrape of Google SERP."""
    _polite_sleep(2.0, 5.0)
    try:
        resp = requests.get(
            "https://www.google.com/search",
            params={"q": query, "num": min(num_results, 10), "hl": "en"},
            headers={
                "User-Agent": _random_ua(),
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "en-US,en;q=0.5",
                "DNT": "1",
            },
            timeout=15,
        )
        resp.raise_for_status()
    except requests.RequestException as exc:
        logger.error("Google HTTP scrape failed: %s", exc)
        return []

    soup = BeautifulSoup(resp.text, "lxml")
    results = []
    for container in soup.select("div.g, div[data-sokoban-container]"):
        a_tag = container.find("a", href=True)
        if not a_tag or not a_tag["href"].startswith("http"):
            continue
        title_tag = container.find("h3")
        title = title_tag.get_text(strip=True) if title_tag else ""
        desc_tag = container.find("div", {"data-sncf": True}) or container.find("span")
        description = desc_tag.get_text(strip=True) if desc_tag else ""
        results.append({
            "url": a_tag["href"],
            "title": title,
            "description": description[:300],
            "provider": "google",
        })
        if len(results) >= num_results:
            break

    logger.info("Google HTTP scrape returned %d results for: %s", len(results), query[:80])
    return results


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def active_provider() -> str:
    """Return the name of the search provider that will be used."""
    if os.getenv("TAVILY_API_KEY") and _TAVILY_AVAILABLE:
        return "tavily"
    if os.getenv("BRAVE_API_KEY"):
        return "brave"
    return "google"


def web_search(query: str, num_results: int = 10) -> list[dict]:
    """
    Search using the best available provider.

    Returns:
        List of dicts: [{url, title, description, provider}, ...]
    """
    provider = active_provider()

    if provider == "tavily":
        try:
            return _tavily_search(query, num_results)
        except Exception as exc:
            logger.warning("Tavily search failed (%s), falling back to Google", exc)

    if provider == "brave" or os.getenv("BRAVE_API_KEY"):
        try:
            return _brave_search(query, num_results)
        except Exception as exc:
            logger.warning("Brave search failed (%s), falling back to Google", exc)

    return _google_search(query, num_results)
