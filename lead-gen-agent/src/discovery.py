"""
Lead Discovery Module
─────────────────────
Uses the best available search provider (Tavily → Brave → Google) to find
leads matching a target profile. Searches for LinkedIn profiles and company
pages using carefully crafted queries.

Cross-run deduplication: leads already stored in the database are skipped.
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

from .search import web_search, _polite_sleep, active_provider
from .database import lead_exists

logger = logging.getLogger(__name__)


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
    Build search queries targeting public LinkedIn profile pages.
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

    # Company-level queries to find websites alongside LinkedIn profiles
    if industry and location:
        company_q = (
            f'"{industry}" company {location} '
            f'-site:linkedin.com -site:indeed.com'
        )
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
# LinkedIn profile parser
# ---------------------------------------------------------------------------

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

    return {
        "company": title.split("|")[0].split("-")[0].strip()[:80],
        "website": url,
        "domain": domain,
    }


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
    Orchestrate searches to find leads matching the target profile.

    Uses the best available provider (Tavily → Brave → Google).
    Skips leads already stored in the database (cross-run deduplication).

    Returns a deduplicated list of RawLead objects (no enrichment yet).
    """
    keywords = keywords or []
    leads: dict[str, RawLead] = {}  # keyed by linkedin_url or website to deduplicate
    provider = active_provider()
    logger.info("Discovery using search provider: %s", provider)

    # ---- LinkedIn profile searches ----
    linkedin_queries = build_linkedin_queries(titles, industry, location, keywords)
    logger.info("Running %d LinkedIn discovery queries", len(linkedin_queries))

    for query in linkedin_queries:
        if len(leads) >= limit:
            break
        logger.info("Searching: %s", query[:100])
        results = web_search(query, num_results=10)

        # Only sleep between queries for Google (Tavily/Brave handle it server-side)
        if provider == "google":
            _polite_sleep(delay_min, delay_max)

        for result in results:
            if len(leads) >= limit:
                break
            lead = parse_linkedin_result(result)
            if not lead or not lead.linkedin_url:
                continue
            if lead.linkedin_url in leads:
                continue
            # Cross-run dedup: skip leads seen in previous runs
            if lead_exists(linkedin_url=lead.linkedin_url, name=lead.name, company=lead.company):
                logger.debug("Skipping known lead: %s (already in DB)", lead.linkedin_url)
                continue
            lead.run_id = run_id
            leads[lead.linkedin_url] = lead
            logger.debug("Discovered: %s @ %s", lead.name, lead.company)

    # ---- Company-level searches (fills in leads without LinkedIn) ----
    if len(leads) < limit:
        company_queries = build_company_queries(industry, location, keywords, company_size)
        logger.info("Running %d company discovery queries", len(company_queries))

        for query in company_queries:
            if len(leads) >= limit:
                break
            results = web_search(query, num_results=10)
            if provider == "google":
                _polite_sleep(delay_min, delay_max)

            for result in results:
                if len(leads) >= limit:
                    break
                company_data = parse_company_result(result)
                if not company_data:
                    continue
                key = company_data["website"]
                if key in leads:
                    continue
                stub = RawLead(
                    run_id=run_id,
                    company=company_data["company"],
                    website=company_data["website"],
                    source="google_company",
                    raw_snippet=result.get("description", "")[:500],
                )
                leads[key] = stub
                logger.debug("Discovered company: %s (%s)", stub.company, stub.website)

    result_list = list(leads.values())[:limit]
    logger.info("Discovery complete: %d leads (provider=%s, limit=%d)",
                len(result_list), provider, limit)
    return result_list
