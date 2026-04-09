"""
Lead Discovery Module
─────────────────────
Uses Google search scraping (no API key) to find leads matching a
target profile. Searches for LinkedIn profiles and company pages using
carefully crafted queries.

Respects rate limits with random delays and rotates user-agents to
reduce the chance of being blocked.
"""

import logging
import random
import re
import time
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

try:
    from googlesearch import search as google_search
    GOOGLESEARCH_AVAILABLE = True
except ImportError:
    GOOGLESEARCH_AVAILABLE = False

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# User-agent pool
# ---------------------------------------------------------------------------

USER_AGENTS = [
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


def _random_headers() -> dict:
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }


def _polite_sleep(min_s: float = 2.0, max_s: float = 5.0) -> None:
    delay = random.uniform(min_s, max_s)
    logger.debug("Sleeping %.1fs between requests", delay)
    time.sleep(delay)


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class RawLead:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    run_id: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    name: Optional[str] = None
    title: Optional[str] = None
    company: Optional[str] = None
    linkedin_url: Optional[str] = None
    website: Optional[str] = None
    location: Optional[str] = None
    source: Optional[str] = None
    raw_snippet: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# Query builders
# ---------------------------------------------------------------------------

def build_linkedin_queries(
    titles: list[str],
    industry: str,
    location: str,
    keywords: list[str],
) -> list[str]:
    """
    Build Google queries targeting public LinkedIn profile pages.
    Example: site:linkedin.com/in "VP of Sales" "B2B SaaS" London
    """
    queries = []
    for title in titles:
        base = f'site:linkedin.com/in "{title}"'
        if industry:
            base += f' "{industry}"'
        if location:
            base += f' "{location}"'
        if keywords:
            base += " " + " ".join(f'"{k}"' for k in keywords[:2])
        queries.append(base)

    # Also build company-level queries (to find websites)
    if industry and location:
        company_q = f'"{industry}" company {location} -site:linkedin.com -site:indeed.com'
        queries.append(company_q)

    return queries


def build_company_queries(
    industry: str,
    location: str,
    keywords: list[str],
    company_size: Optional[str] = None,
) -> list[str]:
    """Queries to find company websites directly."""
    queries = []
    base = f'"{industry}" startup'
    if location:
        base += f" {location}"
    if company_size:
        base += f" {company_size}"
    base += " -site:linkedin.com -site:crunchbase.com -site:glassdoor.com"
    queries.append(base)

    for kw in keywords[:3]:
        q = f'"{kw}" {industry} company {location} about -site:linkedin.com'
        queries.append(q)

    return queries


# ---------------------------------------------------------------------------
# Google search wrapper
# ---------------------------------------------------------------------------

def google_search_safe(query: str, num_results: int = 10) -> list[dict]:
    """
    Run a Google search query and return list of {url, title, description}.
    Falls back to direct HTTP scraping of google.com if googlesearch-python
    is blocked or unavailable.
    """
    results = []

    if GOOGLESEARCH_AVAILABLE:
        try:
            _polite_sleep(2.0, 4.0)
            urls = list(google_search(query, num_results=num_results, sleep_interval=2))
            for url in urls:
                results.append({"url": url, "title": "", "description": ""})
            logger.info("googlesearch returned %d results for: %s", len(results), query[:80])
            return results
        except Exception as exc:
            logger.warning("googlesearch-python failed (%s), falling back to HTTP scrape", exc)

    # Fallback: scrape google.com directly
    return _scrape_google_http(query, num_results)


def _scrape_google_http(query: str, num_results: int = 10) -> list[dict]:
    """Scrape Google search results page directly."""
    _polite_sleep(2.0, 5.0)
    url = "https://www.google.com/search"
    params = {"q": query, "num": min(num_results, 10), "hl": "en"}
    try:
        resp = requests.get(
            url, params=params, headers=_random_headers(), timeout=15
        )
        resp.raise_for_status()
    except requests.RequestException as exc:
        logger.error("Google HTTP scrape failed: %s", exc)
        return []

    soup = BeautifulSoup(resp.text, "lxml")
    results = []

    # Google search result containers vary; try multiple selectors
    for container in soup.select("div.g, div[data-sokoban-container]"):
        a_tag = container.find("a", href=True)
        if not a_tag:
            continue
        href = a_tag["href"]
        if not href.startswith("http"):
            continue
        title_tag = container.find("h3")
        title = title_tag.get_text(strip=True) if title_tag else ""
        desc_tag = container.find("div", {"data-sncf": True}) or container.find("span")
        description = desc_tag.get_text(strip=True) if desc_tag else ""
        results.append({"url": href, "title": title, "description": description})
        if len(results) >= num_results:
            break

    logger.info("HTTP scrape returned %d results for: %s", len(results), query[:80])
    return results


# ---------------------------------------------------------------------------
# LinkedIn profile parser
# ---------------------------------------------------------------------------

_NAME_RE = re.compile(
    r"(?:(?P<name>[A-Z][a-zA-Z'\-]+(?:\s[A-Z][a-zA-Z'\-]+)+))"
)
_TITLE_RE = re.compile(
    r"(?:VP|Head|Director|Manager|CEO|CTO|CMO|CPO|Founder|Co-Founder|"
    r"President|Partner|Principal|Lead|Senior|Engineer|Consultant|Advisor)"
    r"[\w\s,\-&|]+",
    re.IGNORECASE,
)


def parse_linkedin_result(result: dict) -> Optional[RawLead]:
    """
    Extract structured data from a LinkedIn search result.
    LinkedIn URLs look like: linkedin.com/in/john-doe
    Snippets contain name, title, and company info.
    """
    url = result.get("url", "")
    if "linkedin.com/in/" not in url:
        return None

    title_text = result.get("title", "")
    description = result.get("description", "")
    combined = f"{title_text} {description}"

    lead = RawLead(linkedin_url=url, source="google_linkedin")

    # Extract name from LinkedIn URL slug (most reliable)
    slug_match = re.search(r"linkedin\.com/in/([^/?]+)", url)
    if slug_match:
        slug = slug_match.group(1)
        # Convert slug like "john-doe-123abc" → "John Doe"
        parts = slug.split("-")
        name_parts = [p.capitalize() for p in parts if p.isalpha() and len(p) > 1]
        if name_parts:
            lead.name = " ".join(name_parts[:3])

    # Also try extracting from title text (e.g. "John Doe - VP Sales at Acme")
    if " - " in title_text:
        name_candidate = title_text.split(" - ")[0].strip()
        if 2 <= len(name_candidate.split()) <= 4:
            lead.name = name_candidate

    # Extract job title
    title_match = _TITLE_RE.search(combined)
    if title_match:
        lead.title = title_match.group(0).strip()[:80]

    # Extract company from "at Company" pattern
    at_match = re.search(r"\bat\s+([A-Z][A-Za-z0-9\s\-&\.]+?)(?:\s*[-|·]|\s*$)", combined)
    if at_match:
        lead.company = at_match.group(1).strip()[:80]

    lead.raw_snippet = combined[:500]
    return lead


def parse_company_result(result: dict) -> Optional[dict]:
    """Extract company name and website from a generic search result."""
    url = result.get("url", "")
    title = result.get("title", "")
    if not url or not title:
        return None

    parsed = urlparse(url)
    domain = parsed.netloc.replace("www.", "")
    if not domain or any(x in domain for x in ["google", "linkedin", "facebook", "twitter"]):
        return None

    return {"company": title.split("|")[0].split("-")[0].strip()[:80], "website": url, "domain": domain}


# ---------------------------------------------------------------------------
# Main discovery function
# ---------------------------------------------------------------------------

def discover_leads(
    run_id: str,
    industry: str,
    titles: list[str],
    location: str = "",
    keywords: list[str] | None = None,
    company_size: Optional[str] = None,
    limit: int = 30,
    delay_min: float = 2.0,
    delay_max: float = 5.0,
) -> list[RawLead]:
    """
    Orchestrate Google searches to find leads matching the target profile.

    Returns a deduplicated list of RawLead objects (no enrichment yet).
    """
    keywords = keywords or []
    leads: dict[str, RawLead] = {}  # keyed by linkedin_url to deduplicate

    # ---- LinkedIn profile searches ----
    linkedin_queries = build_linkedin_queries(titles, industry, location, keywords)
    logger.info("Running %d LinkedIn discovery queries", len(linkedin_queries))

    for query in linkedin_queries:
        if len(leads) >= limit:
            break
        logger.info("Searching: %s", query)
        results = google_search_safe(query, num_results=10)
        _polite_sleep(delay_min, delay_max)

        for result in results:
            if len(leads) >= limit:
                break
            lead = parse_linkedin_result(result)
            if lead and lead.linkedin_url and lead.linkedin_url not in leads:
                lead.run_id = run_id
                leads[lead.linkedin_url] = lead
                logger.debug("Discovered lead: %s @ %s", lead.name, lead.company)

    # ---- Company-level searches (to fill in leads without LinkedIn) ----
    if len(leads) < limit:
        company_queries = build_company_queries(industry, location, keywords, company_size)
        logger.info("Running %d company discovery queries", len(company_queries))

        for query in company_queries:
            if len(leads) >= limit:
                break
            results = google_search_safe(query, num_results=10)
            _polite_sleep(delay_min, delay_max)

            for result in results:
                if len(leads) >= limit:
                    break
                company_data = parse_company_result(result)
                if not company_data:
                    continue
                # Create a stub lead for this company (name unknown yet)
                stub = RawLead(
                    run_id=run_id,
                    company=company_data["company"],
                    website=company_data["website"],
                    source="google_company",
                    raw_snippet=result.get("description", "")[:500],
                )
                key = company_data["website"]
                if key not in leads:
                    leads[key] = stub
                    logger.debug("Discovered company: %s (%s)", stub.company, stub.website)

    result_list = list(leads.values())[:limit]
    logger.info(
        "Discovery complete: %d leads found (limit=%d)", len(result_list), limit
    )
    return result_list
