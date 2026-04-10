"""
Tests for api/server.py — all REST endpoints.
Uses httpx AsyncClient with ASGI transport (no network calls).
"""

import json
import uuid
from datetime import datetime, timezone

import pytest


# ── Helpers ───────────────────────────────────────────────────────────────────

def _seed_run_and_leads(db_mod, n_leads: int = 3) -> str:
    rid = str(uuid.uuid4())
    db_mod.create_run(rid, {"industry": "B2B SaaS", "titles": ["VP Sales"]})
    db_mod.update_run_status(rid, "done", {"total_leads": n_leads})
    tiers = ["Hot", "Warm", "Cold"]
    for i in range(n_leads):
        db_mod.upsert_lead({
            "id": str(uuid.uuid4()),
            "run_id": rid,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "name": f"Lead {i}",
            "title": "VP Sales",
            "company": f"Co {i}",
            "website": f"https://co{i}.com",
            "linkedin_url": f"https://linkedin.com/in/lead-{i}-{rid[:8]}",
            "score": 90 - (i * 20),
            "tier": tiers[i % 3],
            "email": f"lead{i}@co{i}.com",
            "email_verified": 0,
            "pain_points": ["Pain A"],
            "tech_signals": ["Salesforce"],
        })
    return rid


# ── Health ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_health_endpoint(api_client):
    async with api_client as client:
        resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "search_provider" in data
    assert "version" in data


# ── Stats ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_stats_endpoint_empty(api_client):
    async with api_client as client:
        resp = await client.get("/api/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_leads"] == 0
    assert data["total_runs"] == 0


@pytest.mark.asyncio
async def test_stats_endpoint_with_data(api_client, isolated_db):
    _seed_run_and_leads(isolated_db, 3)
    async with api_client as client:
        resp = await client.get("/api/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_leads"] == 3


# ── Runs ──────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_start_run_returns_run_id(api_client, mocker):
    mocker.patch("api.server._executor")
    async with api_client as client:
        resp = await client.post("/api/runs", json={
            "industry": "B2B SaaS",
            "titles": ["VP Sales"],
            "location": "UK",
            "limit": 5,
        })
    assert resp.status_code == 202
    data = resp.json()
    assert "run_id" in data
    assert data["status"] == "running"


@pytest.mark.asyncio
async def test_list_runs_empty(api_client):
    async with api_client as client:
        resp = await client.get("/api/runs")
    assert resp.status_code == 200
    assert resp.json()["count"] == 0


@pytest.mark.asyncio
async def test_list_runs_with_data(api_client, isolated_db):
    for _ in range(3):
        isolated_db.create_run(str(uuid.uuid4()), {})
    async with api_client as client:
        resp = await client.get("/api/runs?limit=10")
    assert resp.status_code == 200
    assert resp.json()["count"] == 3


@pytest.mark.asyncio
async def test_get_run_not_found(api_client):
    async with api_client as client:
        resp = await client.get(f"/api/runs/{uuid.uuid4()}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_run_done_with_leads(api_client, isolated_db):
    rid = _seed_run_and_leads(isolated_db, 2)
    async with api_client as client:
        resp = await client.get(f"/api/runs/{rid}?include_leads=true")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "done"
    assert len(data["leads"]) == 2


@pytest.mark.asyncio
async def test_get_run_leads_paginated(api_client, isolated_db):
    rid = _seed_run_and_leads(isolated_db, 3)
    async with api_client as client:
        resp = await client.get(f"/api/runs/{rid}/leads?limit=2&offset=0")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 3
    assert len(data["leads"]) == 2
    assert data["has_more"] is True


@pytest.mark.asyncio
async def test_get_run_leads_tier_filter(api_client, isolated_db):
    rid = _seed_run_and_leads(isolated_db, 3)
    async with api_client as client:
        resp = await client.get(f"/api/runs/{rid}/leads?tier=Hot")
    assert resp.status_code == 200
    data = resp.json()
    assert all(l["tier"] == "Hot" for l in data["leads"])


# ── Leads ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_leads_empty(api_client):
    async with api_client as client:
        resp = await client.get("/api/leads")
    assert resp.status_code == 200
    assert resp.json()["count"] == 0


@pytest.mark.asyncio
async def test_list_leads_with_data(api_client, isolated_db):
    _seed_run_and_leads(isolated_db, 3)
    async with api_client as client:
        resp = await client.get("/api/leads")
    assert resp.status_code == 200
    assert resp.json()["count"] == 3


@pytest.mark.asyncio
async def test_get_lead_not_found(api_client):
    async with api_client as client:
        resp = await client.get(f"/api/leads/{uuid.uuid4()}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_lead_found(api_client, isolated_db):
    rid = _seed_run_and_leads(isolated_db, 1)
    leads = isolated_db.get_leads_for_run(rid)
    lead_id = leads[0]["id"]
    async with api_client as client:
        resp = await client.get(f"/api/leads/{lead_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == lead_id


# ── Export ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_export_run_csv(api_client, isolated_db):
    rid = _seed_run_and_leads(isolated_db, 2)
    async with api_client as client:
        resp = await client.post("/api/leads/export", json={
            "run_id": rid,
            "format": "csv",
        })
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]


@pytest.mark.asyncio
async def test_export_run_json(api_client, isolated_db):
    rid = _seed_run_and_leads(isolated_db, 2)
    async with api_client as client:
        resp = await client.post("/api/leads/export", json={
            "run_id": rid,
            "format": "json",
        })
    assert resp.status_code == 200
    assert "application/json" in resp.headers["content-type"]


@pytest.mark.asyncio
async def test_export_no_leads_404(api_client):
    async with api_client as client:
        resp = await client.post("/api/leads/export", json={
            "run_id": str(uuid.uuid4()),
            "format": "csv",
        })
    assert resp.status_code == 404


# ── Auth ──────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_auth_disabled_when_no_api_key(api_client, monkeypatch):
    monkeypatch.delenv("API_KEY", raising=False)
    async with api_client as client:
        resp = await client.get("/api/leads")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_auth_rejects_missing_key(api_client, monkeypatch):
    monkeypatch.setenv("API_KEY", "secret-key-123")
    async with api_client as client:
        resp = await client.get("/api/leads")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_auth_accepts_valid_xapikey(api_client, monkeypatch):
    monkeypatch.setenv("API_KEY", "secret-key-123")
    async with api_client as client:
        resp = await client.get("/api/leads", headers={"X-API-Key": "secret-key-123"})
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_auth_accepts_bearer_token(api_client, monkeypatch):
    monkeypatch.setenv("API_KEY", "secret-key-123")
    async with api_client as client:
        resp = await client.get(
            "/api/leads",
            headers={"Authorization": "Bearer secret-key-123"},
        )
    assert resp.status_code == 200


# ── CORS ──────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_cors_headers_present(api_client):
    async with api_client as client:
        resp = await client.options(
            "/health",
            headers={"Origin": "https://app.example.com", "Access-Control-Request-Method": "GET"},
        )
    # Should have CORS header
    assert resp.headers.get("access-control-allow-origin") is not None
