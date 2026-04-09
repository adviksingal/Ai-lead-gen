"""
Main Orchestration Agent
─────────────────────────
Ties the entire pipeline together:

  1. Discovery  — find leads via Google scraping
  2. Enrichment — scrape company websites + Claude analysis
  3. Email      — find / verify email addresses
  4. Scoring    — Claude rates each lead 1-100
  5. Outreach   — Claude writes personalised cold emails (Hot + Warm)
  6. Persist    — save everything to SQLite

Progress is logged at each step. The run can be polled via the REST API
or watched live via the CLI.
"""

import logging
import os
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Optional

from dotenv import load_dotenv

from .database import init_db, create_run, update_run_status, upsert_lead, get_leads_for_run
from .discovery import discover_leads
from .enrichment import enrich_lead
from .email_finder import find_email
from .scoring import score_lead
from .outreach import generate_outreach_email

load_dotenv()

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Run configuration
# ---------------------------------------------------------------------------

@dataclass
class RunConfig:
    industry: str
    titles: list[str]
    location: str = ""
    keywords: list[str] = field(default_factory=list)
    company_size: Optional[str] = None
    limit: int = 30
    concurrency: int = 3
    delay_min: float = 2.0
    delay_max: float = 5.0
    sender_name: str = "Alex"
    sender_company: str = "YourCo"
    skip_outreach: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# Progress tracker
# ---------------------------------------------------------------------------

class RunProgress:
    def __init__(self, run_id: str, total: int = 0):
        self.run_id = run_id
        self.total = total
        self.discovered = 0
        self.enriched = 0
        self.emails_found = 0
        self.scored = 0
        self.outreach_written = 0
        self.errors = 0
        self._start = datetime.now(timezone.utc)

    @property
    def elapsed_seconds(self) -> float:
        return (datetime.now(timezone.utc) - self._start).total_seconds()

    def summary(self) -> dict:
        return {
            "run_id": self.run_id,
            "total_leads": self.total,
            "discovered": self.discovered,
            "enriched": self.enriched,
            "emails_found": self.emails_found,
            "scored": self.scored,
            "outreach_written": self.outreach_written,
            "errors": self.errors,
            "elapsed_seconds": round(self.elapsed_seconds, 1),
        }

    def log(self, message: str) -> None:
        logger.info("[run=%s] %s | %s", self.run_id[:8], message, self.summary())


# ---------------------------------------------------------------------------
# Pipeline steps (designed to be called in a thread pool)
# ---------------------------------------------------------------------------

def _enrich_email_score_outreach(
    lead_dict: dict,
    config: RunConfig,
    progress: RunProgress,
) -> dict:
    """
    Run enrichment → email finding → scoring → outreach for a single lead.
    This is the per-lead worker function.
    """
    try:
        # Enrichment
        lead_dict = enrich_lead(lead_dict)
        progress.enriched += 1
        logger.debug("[run=%s] Enriched %s @ %s",
                     progress.run_id[:8], lead_dict.get("name"), lead_dict.get("company"))

        # Email finding
        lead_dict = find_email(lead_dict)
        if lead_dict.get("email"):
            progress.emails_found += 1

        # Scoring
        lead_dict = score_lead(lead_dict, run_config=config.to_dict())
        progress.scored += 1

        # Outreach (Hot + Warm only)
        if not config.skip_outreach and lead_dict.get("tier") in ("Hot", "Warm"):
            lead_dict = generate_outreach_email(
                lead_dict,
                sender_name=config.sender_name,
                sender_company=config.sender_company,
            )
            if lead_dict.get("email_subject"):
                progress.outreach_written += 1

        # Persist to DB
        upsert_lead(lead_dict)

    except Exception as exc:
        progress.errors += 1
        logger.error(
            "[run=%s] Pipeline error for %s @ %s: %s",
            progress.run_id[:8], lead_dict.get("name"), lead_dict.get("company"), exc,
            exc_info=True,
        )

    return lead_dict


# ---------------------------------------------------------------------------
# Main run function
# ---------------------------------------------------------------------------

def run_lead_gen(config: RunConfig) -> tuple[str, list[dict]]:
    """
    Execute a complete lead generation run.

    Args:
        config: RunConfig with all parameters

    Returns:
        (run_id, list of fully-enriched lead dicts)
    """
    # Initialise DB
    init_db()

    run_id = str(uuid.uuid4())
    progress = RunProgress(run_id)

    logger.info(
        "Starting lead gen run %s | industry=%s titles=%s location=%s limit=%d",
        run_id, config.industry, config.titles, config.location, config.limit,
    )

    # Persist run record
    create_run(run_id, config.to_dict())

    try:
        # ---- Step 1: Discovery ----
        logger.info("[run=%s] Phase 1: Discovery", run_id[:8])
        raw_leads = discover_leads(
            run_id=run_id,
            industry=config.industry,
            titles=config.titles,
            location=config.location,
            keywords=config.keywords,
            company_size=config.company_size,
            limit=config.limit,
            delay_min=config.delay_min,
            delay_max=config.delay_max,
        )
        progress.discovered = len(raw_leads)
        progress.total = len(raw_leads)
        progress.log(f"Discovery complete: {len(raw_leads)} leads found")

        if not raw_leads:
            logger.warning("[run=%s] No leads discovered — check search queries", run_id[:8])
            update_run_status(run_id, "done", progress.summary())
            return run_id, []

        # Convert RawLead dataclasses to dicts
        lead_dicts = [rl.to_dict() for rl in raw_leads]

        # ---- Steps 2-5: Enrich / Email / Score / Outreach (parallel) ----
        logger.info("[run=%s] Phase 2-5: Enrich + Email + Score + Outreach (%d workers)",
                    run_id[:8], config.concurrency)

        results: list[dict] = []
        with ThreadPoolExecutor(max_workers=config.concurrency) as executor:
            futures = {
                executor.submit(
                    _enrich_email_score_outreach, lead, config, progress
                ): lead
                for lead in lead_dicts
            }
            for future in as_completed(futures):
                result = future.result()
                results.append(result)
                progress.log(
                    f"Processed {len(results)}/{progress.total}: "
                    f"{result.get('name', '?')} @ {result.get('company', '?')} "
                    f"→ {result.get('tier', '?')} ({result.get('score', '?')})"
                )

        # Sort by score descending
        results.sort(key=lambda x: x.get("score") or 0, reverse=True)

        # Finalise run
        summary = progress.summary()
        update_run_status(run_id, "done", summary)
        logger.info("[run=%s] Run complete: %s", run_id[:8], summary)

        return run_id, results

    except Exception as exc:
        logger.error("[run=%s] Fatal run error: %s", run_id[:8], exc, exc_info=True)
        update_run_status(run_id, "failed", {"error": str(exc), **progress.summary()})
        raise


# ---------------------------------------------------------------------------
# Convenience: re-run outreach for a specific run
# ---------------------------------------------------------------------------

def regenerate_outreach(run_id: str, tier_filter: Optional[list[str]] = None) -> list[dict]:
    """Re-generate outreach emails for leads in an existing run."""
    leads = get_leads_for_run(run_id)
    tiers = tier_filter or ["Hot", "Warm"]
    updated = []
    for lead in leads:
        if lead.get("tier") in tiers:
            lead = generate_outreach_email(lead)
            upsert_lead(lead)
            updated.append(lead)
    logger.info("Regenerated outreach for %d leads in run %s", len(updated), run_id)
    return updated
