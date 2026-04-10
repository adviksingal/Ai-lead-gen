"""
Tests for src/database.py — CRUD, cache, deduplication, stats.
"""

import uuid
from datetime import datetime, timezone


def _now():
    return datetime.now(timezone.utc).isoformat()


def _make_lead(run_id: str, **kwargs) -> dict:
    base = {
        "id": str(uuid.uuid4()),
        "run_id": run_id,
        "created_at": _now(),
        "name": "Jane Doe",
        "title": "Head of Sales",
        "company": "TestCo",
        "linkedin_url": "https://linkedin.com/in/jane-doe-testco",
        "website": "https://testco.com",
        "location": "London, UK",
        "source": "google_linkedin",
        "pain_points": ["Manual CRM entry", "Low pipeline"],
        "tech_signals": ["Salesforce"],
        "score": 75,
        "tier": "Hot",
        "email": "jane.doe@testco.com",
        "email_verified": 0,
    }
    base.update(kwargs)
    return base


# ── Runs ──────────────────────────────────────────────────────────────────────

def test_create_and_get_run(isolated_db):
    rid = str(uuid.uuid4())
    isolated_db.create_run(rid, {"industry": "SaaS", "titles": ["CRO"]})
    run = isolated_db.get_run(rid)
    assert run is not None
    assert run["id"] == rid
    assert run["status"] == "running"


def test_update_run_status(isolated_db):
    rid = str(uuid.uuid4())
    isolated_db.create_run(rid, {})
    isolated_db.update_run_status(rid, "done", {"total_leads": 5})
    run = isolated_db.get_run(rid)
    assert run["status"] == "done"


def test_list_runs(isolated_db):
    for _ in range(3):
        isolated_db.create_run(str(uuid.uuid4()), {})
    runs = isolated_db.list_runs(limit=10)
    assert len(runs) == 3


# ── Leads ─────────────────────────────────────────────────────────────────────

def test_upsert_and_get_lead(isolated_db):
    rid = str(uuid.uuid4())
    isolated_db.create_run(rid, {})
    lead = _make_lead(rid)
    isolated_db.upsert_lead(lead)
    stored = isolated_db.get_lead(lead["id"])
    assert stored is not None
    assert stored["name"] == "Jane Doe"


def test_pain_points_roundtrip(isolated_db):
    """Lists are serialised to JSON in SQLite and deserialised back."""
    rid = str(uuid.uuid4())
    isolated_db.create_run(rid, {})
    lead = _make_lead(rid, pain_points=["Problem A", "Problem B", "Problem C"])
    isolated_db.upsert_lead(lead)
    stored = isolated_db.get_lead(lead["id"])
    assert isinstance(stored["pain_points"], list)
    assert stored["pain_points"] == ["Problem A", "Problem B", "Problem C"]


def test_list_leads_by_tier(isolated_db):
    rid = str(uuid.uuid4())
    isolated_db.create_run(rid, {})
    for tier, score in [("Hot", 85), ("Warm", 55), ("Cold", 20)]:
        isolated_db.upsert_lead(_make_lead(
            rid,
            id=str(uuid.uuid4()),
            tier=tier,
            score=score,
            linkedin_url=f"https://linkedin.com/in/test-{tier.lower()}",
        ))
    hot = isolated_db.list_leads(tier="Hot")
    assert len(hot) == 1
    assert hot[0]["tier"] == "Hot"

    warm = isolated_db.list_leads(tier="Warm")
    assert len(warm) == 1


def test_list_leads_by_min_score(isolated_db):
    rid = str(uuid.uuid4())
    isolated_db.create_run(rid, {})
    for score in [90, 60, 30]:
        isolated_db.upsert_lead(_make_lead(
            rid,
            id=str(uuid.uuid4()),
            score=score,
            tier="Hot" if score >= 70 else ("Warm" if score >= 40 else "Cold"),
            linkedin_url=f"https://linkedin.com/in/test-score-{score}",
        ))
    high = isolated_db.list_leads(min_score=70)
    assert all(l["score"] >= 70 for l in high)


def test_get_leads_for_run(isolated_db):
    rid = str(uuid.uuid4())
    isolated_db.create_run(rid, {})
    other_rid = str(uuid.uuid4())
    isolated_db.create_run(other_rid, {})

    for i in range(3):
        isolated_db.upsert_lead(_make_lead(
            rid, id=str(uuid.uuid4()),
            linkedin_url=f"https://linkedin.com/in/run-lead-{i}"
        ))
    isolated_db.upsert_lead(_make_lead(
        other_rid, id=str(uuid.uuid4()),
        linkedin_url="https://linkedin.com/in/other-run"
    ))

    run_leads = isolated_db.get_leads_for_run(rid)
    assert len(run_leads) == 3


# ── Deduplication ─────────────────────────────────────────────────────────────

def test_lead_exists_by_linkedin_url(isolated_db):
    rid = str(uuid.uuid4())
    isolated_db.create_run(rid, {})
    lead = _make_lead(rid, linkedin_url="https://linkedin.com/in/unique-person")
    isolated_db.upsert_lead(lead)
    assert isolated_db.lead_exists(linkedin_url="https://linkedin.com/in/unique-person") is True
    assert isolated_db.lead_exists(linkedin_url="https://linkedin.com/in/nobody") is False


def test_lead_exists_by_name_company(isolated_db):
    rid = str(uuid.uuid4())
    isolated_db.create_run(rid, {})
    isolated_db.upsert_lead(_make_lead(rid, linkedin_url="https://li.com/in/x", name="Alice Smith", company="Acme"))
    assert isolated_db.lead_exists(name="alice smith", company="ACME") is True
    assert isolated_db.lead_exists(name="Bob Jones", company="Acme") is False


# ── Scrape cache ──────────────────────────────────────────────────────────────

def test_scrape_cache_miss(isolated_db):
    assert isolated_db.cache_get("https://example.com") is None


def test_scrape_cache_set_and_get(isolated_db):
    isolated_db.cache_set("https://example.com", "some content", 200)
    result = isolated_db.cache_get("https://example.com")
    assert result is not None
    assert result["content"] == "some content"
    assert result["status_code"] == 200


def test_scrape_cache_overwrite(isolated_db):
    isolated_db.cache_set("https://example.com", "v1", 200)
    isolated_db.cache_set("https://example.com", "v2", 200)
    assert isolated_db.cache_get("https://example.com")["content"] == "v2"


# ── Stats ─────────────────────────────────────────────────────────────────────

def test_get_stats_empty(isolated_db):
    stats = isolated_db.get_stats()
    assert stats["total_leads"] == 0
    assert stats["total_runs"] == 0


def test_get_stats_with_data(isolated_db):
    rid = str(uuid.uuid4())
    isolated_db.create_run(rid, {})
    isolated_db.upsert_lead(_make_lead(rid, tier="Hot", score=85,
                                       linkedin_url="li.com/in/a", email="a@a.com"))
    isolated_db.upsert_lead(_make_lead(rid, tier="Warm", score=55,
                                       linkedin_url="li.com/in/b", email=None))
    stats = isolated_db.get_stats()
    assert stats["total_leads"] == 2
    assert stats["hot_leads"] == 1
    assert stats["warm_leads"] == 1
    assert stats["leads_with_email"] == 1
