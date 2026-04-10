"""
SQLite database layer — schema, CRUD, and scrape cache.
All tables are created on first import; re-runs never re-scrape cached URLs.
"""

import sqlite3
import json
import hashlib
import logging
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Generator, Optional

logger = logging.getLogger(__name__)

# Default DB path; overridden via env var DATABASE_URL
DEFAULT_DB_PATH = Path("leads.db")


def _db_path() -> Path:
    import os
    return Path(os.getenv("DATABASE_URL", str(DEFAULT_DB_PATH)))


@contextmanager
def get_conn() -> Generator[sqlite3.Connection, None, None]:
    """Context manager that yields a connection with row_factory and WAL mode."""
    conn = sqlite3.connect(str(_db_path()), timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

DDL = """
CREATE TABLE IF NOT EXISTS runs (
    id          TEXT PRIMARY KEY,
    created_at  TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'running',   -- running | done | failed
    config      TEXT NOT NULL,                      -- JSON of RunConfig
    summary     TEXT                                -- JSON summary on completion
);

CREATE TABLE IF NOT EXISTS leads (
    id              TEXT PRIMARY KEY,
    run_id          TEXT NOT NULL REFERENCES runs(id),
    created_at      TEXT NOT NULL,
    -- Discovery
    name            TEXT,
    title           TEXT,
    company         TEXT,
    linkedin_url    TEXT,
    website         TEXT,
    location        TEXT,
    source          TEXT,
    -- Enrichment
    company_summary TEXT,
    pain_points     TEXT,   -- JSON list
    tech_signals    TEXT,   -- JSON list
    enriched_at     TEXT,
    -- Email
    email           TEXT,
    email_verified  INTEGER DEFAULT 0,
    email_source    TEXT,
    -- Scoring
    score           INTEGER,
    tier            TEXT,   -- Hot | Warm | Cold
    score_reasoning TEXT,
    scored_at       TEXT,
    -- Outreach
    email_subject   TEXT,
    email_body      TEXT,
    outreach_at     TEXT,
    -- Meta
    raw_data        TEXT    -- full JSON blob for debugging
);

CREATE INDEX IF NOT EXISTS idx_leads_run_id  ON leads(run_id);
CREATE INDEX IF NOT EXISTS idx_leads_score   ON leads(score);
CREATE INDEX IF NOT EXISTS idx_leads_tier    ON leads(tier);

-- Scrape cache — avoids hitting the same URL twice across runs
CREATE TABLE IF NOT EXISTS scrape_cache (
    url_hash    TEXT PRIMARY KEY,
    url         TEXT NOT NULL,
    content     TEXT,
    status_code INTEGER,
    cached_at   TEXT NOT NULL
);
"""


def init_db() -> None:
    """Create all tables if they don't exist."""
    with get_conn() as conn:
        conn.executescript(DDL)
    logger.debug("Database initialised at %s", _db_path())


# ---------------------------------------------------------------------------
# Runs
# ---------------------------------------------------------------------------

def create_run(run_id: str, config: dict) -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO runs (id, created_at, status, config) VALUES (?,?,?,?)",
            (run_id, _now(), "running", json.dumps(config)),
        )


def update_run_status(run_id: str, status: str, summary: Optional[dict] = None) -> None:
    with get_conn() as conn:
        conn.execute(
            "UPDATE runs SET status=?, summary=? WHERE id=?",
            (status, json.dumps(summary) if summary else None, run_id),
        )


def get_run(run_id: str) -> Optional[dict]:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
        if row:
            return dict(row)
    return None


def list_runs(limit: int = 20) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM runs ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Leads
# ---------------------------------------------------------------------------

def upsert_lead(lead: dict) -> None:
    """Insert or replace a lead record."""
    fields = [
        "id", "run_id", "created_at", "name", "title", "company",
        "linkedin_url", "website", "location", "source",
        "company_summary", "pain_points", "tech_signals", "enriched_at",
        "email", "email_verified", "email_source",
        "score", "tier", "score_reasoning", "scored_at",
        "email_subject", "email_body", "outreach_at",
        "raw_data",
    ]
    # Serialise list fields
    for f in ("pain_points", "tech_signals"):
        if isinstance(lead.get(f), list):
            lead[f] = json.dumps(lead[f])

    values = [lead.get(f) for f in fields]
    placeholders = ", ".join("?" * len(fields))
    cols = ", ".join(fields)
    with get_conn() as conn:
        conn.execute(
            f"INSERT OR REPLACE INTO leads ({cols}) VALUES ({placeholders})",
            values,
        )


def get_lead(lead_id: str) -> Optional[dict]:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM leads WHERE id=?", (lead_id,)).fetchone()
        return _deserialise_lead(dict(row)) if row else None


def get_leads_for_run(run_id: str) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM leads WHERE run_id=? ORDER BY score DESC NULLS LAST",
            (run_id,),
        ).fetchall()
        return [_deserialise_lead(dict(r)) for r in rows]


def list_leads(
    tier: Optional[str] = None,
    min_score: Optional[int] = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict]:
    query = "SELECT * FROM leads WHERE 1=1"
    params: list[Any] = []
    if tier:
        query += " AND tier=?"
        params.append(tier)
    if min_score is not None:
        query += " AND score>=?"
        params.append(min_score)
    query += " ORDER BY score DESC NULLS LAST LIMIT ? OFFSET ?"
    params += [limit, offset]
    with get_conn() as conn:
        rows = conn.execute(query, params).fetchall()
        return [_deserialise_lead(dict(r)) for r in rows]


def lead_exists(linkedin_url: Optional[str] = None, name: Optional[str] = None, company: Optional[str] = None) -> bool:
    """
    Return True if a lead matching the given identifiers already exists
    in any previous run — used to skip duplicates during discovery.

    Checks in order:
      1. LinkedIn URL (exact match)
      2. name + company (case-insensitive)
    """
    with get_conn() as conn:
        if linkedin_url:
            row = conn.execute(
                "SELECT id FROM leads WHERE linkedin_url = ?", (linkedin_url,)
            ).fetchone()
            if row:
                return True
        if name and company:
            row = conn.execute(
                "SELECT id FROM leads WHERE lower(name) = lower(?) AND lower(company) = lower(?)",
                (name, company),
            ).fetchone()
            if row:
                return True
    return False


def get_stats() -> dict:
    """Return aggregate statistics across all runs and leads."""
    with get_conn() as conn:
        total_leads = conn.execute("SELECT COUNT(*) FROM leads").fetchone()[0]
        total_runs = conn.execute("SELECT COUNT(*) FROM runs").fetchone()[0]
        tier_counts = dict(
            conn.execute(
                "SELECT tier, COUNT(*) FROM leads WHERE tier IS NOT NULL GROUP BY tier"
            ).fetchall()
        )
        with_email = conn.execute(
            "SELECT COUNT(*) FROM leads WHERE email IS NOT NULL AND email != ''"
        ).fetchone()[0]
        verified_email = conn.execute(
            "SELECT COUNT(*) FROM leads WHERE email_verified = 1"
        ).fetchone()[0]
        with_outreach = conn.execute(
            "SELECT COUNT(*) FROM leads WHERE email_subject IS NOT NULL AND email_subject != ''"
        ).fetchone()[0]
        avg_score = conn.execute(
            "SELECT ROUND(AVG(score), 1) FROM leads WHERE score IS NOT NULL"
        ).fetchone()[0]
        cache_size = conn.execute("SELECT COUNT(*) FROM scrape_cache").fetchone()[0]
    return {
        "total_leads": total_leads,
        "total_runs": total_runs,
        "hot_leads": tier_counts.get("Hot", 0),
        "warm_leads": tier_counts.get("Warm", 0),
        "cold_leads": tier_counts.get("Cold", 0),
        "leads_with_email": with_email,
        "leads_with_verified_email": verified_email,
        "leads_with_outreach": with_outreach,
        "average_score": avg_score,
        "scrape_cache_entries": cache_size,
    }


def _deserialise_lead(lead: dict) -> dict:
    for f in ("pain_points", "tech_signals"):
        if isinstance(lead.get(f), str):
            try:
                lead[f] = json.loads(lead[f])
            except (json.JSONDecodeError, TypeError):
                lead[f] = []
    return lead


# ---------------------------------------------------------------------------
# Scrape cache
# ---------------------------------------------------------------------------

def cache_get(url: str) -> Optional[dict]:
    url_hash = _hash(url)
    with get_conn() as conn:
        row = conn.execute(
            "SELECT content, status_code FROM scrape_cache WHERE url_hash=?",
            (url_hash,),
        ).fetchone()
        return dict(row) if row else None


def cache_set(url: str, content: str, status_code: int) -> None:
    url_hash = _hash(url)
    with get_conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO scrape_cache (url_hash, url, content, status_code, cached_at) "
            "VALUES (?,?,?,?,?)",
            (url_hash, url, content, status_code, _now()),
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()
