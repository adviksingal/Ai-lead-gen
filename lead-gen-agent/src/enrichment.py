"""
Lead Enrichment Module
──────────────────────
Scrapes company websites and uses Claude to extract:
  - Company summary (what they do)
  - Likely pain points
  - Tech signals (job listings, blog posts, tools mentioned)

All scrape results are cached in SQLite to avoid redundant requests.
"""

import logging
import os
import re
import time
import random
from typing import Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
import anthropic

from .database import cache_get, cache_set

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64; rv:124.0) Gecko/20100101 Firefox/124.0",
]

REQUEST_TIMEOUT = 15
MAX_CONTENT_LEN = 50_000  # chars to pass to Claude


def _get_with_retry(url: str, retries: int = 3) -> Optional[requests.Response]:
    """GET with exponential backoff and user-agent rotation."""
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }
    for attempt in range(retries):
        try:
            resp = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT, allow_redirects=True)
            resp.raise_for_status()
            return resp
        except requests.RequestException as exc:
            wait = 2 ** attempt + random.uniform(0, 1)
            logger.warning("GET %s failed (attempt %d/%d): %s — retrying in %.1fs",
                           url, attempt + 1, retries, exc, wait)
            if attempt < retries - 1:
                time.sleep(wait)
    return None


# ---------------------------------------------------------------------------
# Scraping helpers
# ---------------------------------------------------------------------------

def _clean_text(soup: BeautifulSoup) -> str:
    """Remove scripts/styles and return visible text."""
    for tag in soup(["script", "style", "nav", "header", "footer", "aside"]):
        tag.decompose()
    text = soup.get_text(separator=" ", strip=True)
    # Collapse whitespace
    text = re.sub(r"\s{3,}", "  ", text)
    return text.strip()


def scrape_url(url: str) -> Optional[str]:
    """
    Scrape a URL and return cleaned text content.
    Checks the SQLite cache first; stores result on miss.
    """
    cached = cache_get(url)
    if cached:
        logger.debug("Cache hit: %s", url)
        return cached["content"]

    resp = _get_with_retry(url)
    if not resp:
        cache_set(url, "", 0)
        return None

    soup = BeautifulSoup(resp.text, "lxml")
    text = _clean_text(soup)
    cache_set(url, text, resp.status_code)
    logger.debug("Scraped %d chars from %s", len(text), url)
    return text


def _find_subpages(base_url: str, soup: BeautifulSoup, keywords: list[str]) -> list[str]:
    """Find internal links matching keywords like 'about', 'team', 'contact'."""
    found = []
    parsed_base = urlparse(base_url)
    for a in soup.find_all("a", href=True):
        href = a["href"].lower()
        if any(kw in href for kw in keywords):
            full_url = urljoin(base_url, a["href"])
            parsed = urlparse(full_url)
            if parsed.netloc == parsed_base.netloc:
                found.append(full_url)
    return list(dict.fromkeys(found))  # deduplicate, preserve order


def scrape_company_website(website: str) -> dict:
    """
    Scrape a company's homepage + about/contact pages.
    Returns dict with: homepage_text, about_text, meta_description, raw_emails
    """
    result = {
        "homepage_text": "",
        "about_text": "",
        "meta_description": "",
        "raw_emails": [],
        "contact_page_text": "",
    }
    if not website:
        return result

    # Normalise URL
    if not website.startswith("http"):
        website = "https://" + website

    # Scrape homepage
    homepage_resp = _get_with_retry(website)
    if not homepage_resp:
        return result

    soup = BeautifulSoup(homepage_resp.text, "lxml")

    # Meta description
    meta = soup.find("meta", attrs={"name": re.compile(r"description", re.I)})
    if meta and meta.get("content"):
        result["meta_description"] = meta["content"][:500]

    result["homepage_text"] = _clean_text(soup)[:MAX_CONTENT_LEN]

    # Cache homepage
    cache_set(website, result["homepage_text"], homepage_resp.status_code)

    # Find and scrape about / team / contact pages
    about_links = _find_subpages(website, soup, ["about", "team", "company", "who-we-are"])
    contact_links = _find_subpages(website, soup, ["contact", "reach", "talk"])

    for link in about_links[:2]:
        text = scrape_url(link)
        if text:
            result["about_text"] += text[:MAX_CONTENT_LEN // 2] + "\n\n"

    for link in contact_links[:1]:
        text = scrape_url(link)
        if text:
            result["contact_page_text"] += text[:MAX_CONTENT_LEN // 2]

    # Extract raw email addresses from all scraped text
    all_text = " ".join([
        result["homepage_text"],
        result["about_text"],
        result["contact_page_text"],
    ])
    result["raw_emails"] = list(set(re.findall(
        r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", all_text
    )))

    return result


# ---------------------------------------------------------------------------
# Claude enrichment
# ---------------------------------------------------------------------------

def _get_claude_client() -> anthropic.Anthropic:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable not set")
    return anthropic.Anthropic(api_key=api_key)


def enrich_with_claude(lead: dict, scraped: dict) -> dict:
    """
    Send company scraped content to Claude and extract structured enrichment.
    Returns dict with: company_summary, pain_points (list), tech_signals (list)
    """
    model = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514")

    # Build context from scraped content
    context_parts = []
    if scraped.get("meta_description"):
        context_parts.append(f"Meta description: {scraped['meta_description']}")
    if scraped.get("homepage_text"):
        context_parts.append(f"Homepage text (truncated):\n{scraped['homepage_text'][:3000]}")
    if scraped.get("about_text"):
        context_parts.append(f"About page text (truncated):\n{scraped['about_text'][:2000]}")

    if not context_parts:
        logger.warning("No scraped content for %s — skipping Claude enrichment", lead.get("company"))
        return {"company_summary": "", "pain_points": [], "tech_signals": []}

    context = "\n\n".join(context_parts)

    prompt = f"""You are analysing a company for a B2B sales team. Based on the scraped website content below, extract structured information.

Company: {lead.get('company', 'Unknown')}
Website: {lead.get('website', 'Unknown')}

--- SCRAPED CONTENT ---
{context}
--- END CONTENT ---

Respond with ONLY a valid JSON object (no markdown, no explanation) in this exact format:
{{
  "company_summary": "2-3 sentence description of what this company does and their target market",
  "pain_points": ["pain point 1", "pain point 2", "pain point 3"],
  "tech_signals": ["signal 1", "signal 2"]
}}

For pain_points: infer likely business challenges from their product/service, size, and market.
For tech_signals: list any technologies, tools, job roles, or growth signals mentioned.
Keep each item concise (under 15 words). Return 2-4 items per list."""

    client = _get_claude_client()
    try:
        response = client.messages.create(
            model=model,
            max_tokens=600,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip()
        # Strip any accidental markdown fences
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
        import json
        data = json.loads(raw)
        logger.info("Claude enriched company: %s", lead.get("company"))
        return {
            "company_summary": data.get("company_summary", ""),
            "pain_points": data.get("pain_points", []),
            "tech_signals": data.get("tech_signals", []),
        }
    except Exception as exc:
        logger.error("Claude enrichment failed for %s: %s", lead.get("company"), exc)
        return {"company_summary": "", "pain_points": [], "tech_signals": []}


# ---------------------------------------------------------------------------
# Public entrypoint
# ---------------------------------------------------------------------------

def enrich_lead(lead: dict) -> dict:
    """
    Full enrichment pipeline for one lead.
    1. Scrape company website
    2. Extract raw emails
    3. Run Claude analysis

    Returns the lead dict with enrichment fields populated.
    """
    import json
    from datetime import datetime, timezone

    website = lead.get("website") or _guess_website(lead.get("company", ""))
    if website:
        lead["website"] = website

    logger.info("Enriching lead: %s @ %s (%s)", lead.get("name"), lead.get("company"), website)

    scraped = scrape_company_website(website) if website else {}

    # Store raw emails found on the site (email_finder will use these)
    lead["_raw_emails_from_site"] = scraped.get("raw_emails", [])

    # Claude analysis
    enrichment = enrich_with_claude(lead, scraped)
    lead["company_summary"] = enrichment["company_summary"]
    lead["pain_points"] = enrichment["pain_points"]
    lead["tech_signals"] = enrichment["tech_signals"]
    lead["enriched_at"] = datetime.now(timezone.utc).isoformat()

    return lead


def _guess_website(company_name: str) -> Optional[str]:
    """
    Last-resort: guess a company website from its name.
    Only used when no website was discovered.
    """
    if not company_name:
        return None
    slug = re.sub(r"[^a-z0-9]", "", company_name.lower().replace(" ", ""))
    return f"https://{slug}.com" if slug else None
