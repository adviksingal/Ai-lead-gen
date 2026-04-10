"""
Shared pytest fixtures for the lead gen agent test suite.
"""

import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest

# ── Force test DB to a temp file ─────────────────────────────────────────────


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    """Each test gets its own empty SQLite database and dummy env vars."""
    db_path = tmp_path / "test_leads.db"
    monkeypatch.setenv("DATABASE_URL", str(db_path))
    # Dummy API key so _get_client() guards don't fire before mocks kick in
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key")
    # Re-import so the module picks up the new path
    import importlib
    import src.database as db_mod
    importlib.reload(db_mod)
    db_mod.init_db()
    yield db_mod
    # Cleanup is handled by tmp_path


@pytest.fixture()
def sample_lead() -> dict:
    """A minimal, fully-populated lead dict for testing."""
    return {
        "id": str(uuid.uuid4()),
        "run_id": str(uuid.uuid4()),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "name": "Sarah Chen",
        "title": "VP of Sales",
        "company": "Growthly",
        "website": "https://growthly.io",
        "location": "London, UK",
        "linkedin_url": "https://linkedin.com/in/sarah-chen-growthly",
        "source": "google_linkedin",
        "email": "sarah.chen@growthly.io",
        "email_verified": 0,
        "email_source": "pattern_guess_unverified",
        "company_summary": "Growthly is a B2B SaaS platform for revenue teams.",
        "pain_points": ["Manual CRM entry", "Low pipeline accuracy"],
        "tech_signals": ["Salesforce integration", "Hiring sales engineers"],
        "enriched_at": datetime.now(timezone.utc).isoformat(),
        "score": 82,
        "tier": "Hot",
        "score_reasoning": "Strong ICP match — VP Sales at Series B SaaS in UK.",
        "scored_at": datetime.now(timezone.utc).isoformat(),
        "email_subject": "Quick question about Growthly's outbound motion",
        "email_body": (
            "Hi Sarah,\n\n"
            "I noticed Growthly is scaling its pipeline management product and recently "
            "posted for 3 Sales Engineers — a classic signal of a team ready to move up-market.\n\n"
            "At SalesForge, we help Series B revenue leaders build repeatable outbound "
            "playbooks in 6 weeks. Happy to share what's worked for similar teams.\n\n"
            "Worth a 15-min call this week?\n\nBest,\nAlex"
        ),
        "outreach_at": datetime.now(timezone.utc).isoformat(),
    }


@pytest.fixture()
def run_id(isolated_db) -> str:
    """Create a test run and return its ID."""
    rid = str(uuid.uuid4())
    isolated_db.create_run(rid, {"industry": "B2B SaaS", "titles": ["VP Sales"], "limit": 10})
    return rid


@pytest.fixture()
def mock_claude(mocker):
    """
    Mock the Anthropic client so tests don't make real API calls.
    Returns a mock that can be configured per test.
    """
    mock_response = mocker.MagicMock()
    mock_response.content = [mocker.MagicMock(text='{"score": 75, "tier": "Hot", "reasoning": "Good fit."}')]

    mock_client = mocker.MagicMock()
    mock_client.messages.create.return_value = mock_response

    mocker.patch("anthropic.Anthropic", return_value=mock_client)
    return mock_client


@pytest.fixture()
def api_client(isolated_db):
    """FastAPI test client with the full app."""
    import importlib
    import sys

    # Ensure fresh imports with the test DB
    for mod_name in list(sys.modules.keys()):
        if "src." in mod_name or "api." in mod_name:
            sys.modules.pop(mod_name, None)

    from httpx import AsyncClient
    import importlib
    import api.server as server_mod
    importlib.reload(server_mod)

    from httpx import AsyncClient
    from httpx._transports.asgi import ASGITransport

    return AsyncClient(
        transport=ASGITransport(app=server_mod.app),
        base_url="http://test",
    )
