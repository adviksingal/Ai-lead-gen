"""
FastAPI REST API
─────────────────
Exposes the lead generation pipeline as a REST service.

Endpoints:
  GET  /health                  — liveness check
  POST /api/runs                — start a new lead gen run (async)
  GET  /api/runs                — list recent runs
  GET  /api/runs/{id}           — get run status + results
  GET  /api/leads               — list leads with filters
  GET  /api/leads/{id}          — get single lead
  POST /api/leads/export        — export leads to CSV/JSON
  POST /api/runs/{id}/outreach  — regenerate outreach for a run

Runs are executed in a background thread pool so the API stays responsive.
Poll GET /api/runs/{id} to check status.
"""

import logging
import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from concurrent.futures import ThreadPoolExecutor

from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

# Ensure the project root is on the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from src.database import init_db, get_run, list_runs, get_leads_for_run, list_leads, get_lead
from src.agent import RunConfig, run_lead_gen, regenerate_outreach
from src.export import export_leads

logger = logging.getLogger(__name__)

# Thread pool for background runs (max 2 concurrent runs)
_executor = ThreadPoolExecutor(max_workers=2)
_active_runs: dict[str, str] = {}  # run_id → status (in-memory cache)


# ---------------------------------------------------------------------------
# App lifecycle
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    logger.info("Lead Gen API starting up")
    yield
    _executor.shutdown(wait=False)
    logger.info("Lead Gen API shutting down")


app = FastAPI(
    title="AI Lead Generation Agent",
    description="Autonomously finds, enriches, and scores B2B leads using free web scraping + Claude AI.",
    version="1.0.0",
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class StartRunRequest(BaseModel):
    industry: str = Field(..., example="B2B SaaS")
    titles: list[str] = Field(..., example=["Head of Sales", "VP Sales"])
    location: str = Field("", example="UK")
    keywords: list[str] = Field(default_factory=list, example=["Series A", "fintech"])
    company_size: Optional[str] = Field(None, example="50-200")
    limit: int = Field(30, ge=1, le=200)
    sender_name: str = Field("Alex", example="Alex")
    sender_company: str = Field("YourCo", example="Acme Inc")
    skip_outreach: bool = False


class ExportRequest(BaseModel):
    run_id: Optional[str] = None
    tier: Optional[str] = None
    min_score: Optional[int] = None
    format: str = Field("csv", pattern="^(csv|json)$")


class RegenerateOutreachRequest(BaseModel):
    tiers: list[str] = Field(default_factory=lambda: ["Hot", "Warm"])


# ---------------------------------------------------------------------------
# Background runner
# ---------------------------------------------------------------------------

def _run_in_background(run_id: str, config: RunConfig) -> None:
    """Called in thread pool — runs the full pipeline."""
    try:
        _active_runs[run_id] = "running"
        run_lead_gen(config, run_id=run_id)
        _active_runs[run_id] = "done"
    except Exception as exc:
        logger.error("Background run %s failed: %s", run_id, exc)
        _active_runs[run_id] = "failed"


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/health", tags=["meta"])
def health():
    """Liveness / readiness probe."""
    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "anthropic_key_set": bool(os.getenv("ANTHROPIC_API_KEY")),
    }


# ---- Runs ----

@app.post("/api/runs", status_code=202, tags=["runs"])
def start_run(req: StartRunRequest, background_tasks: BackgroundTasks):
    """
    Start a new lead generation run asynchronously.
    Returns run_id immediately; poll GET /api/runs/{id} for status.
    """
    import uuid
    run_id = str(uuid.uuid4())
    config = RunConfig(
        industry=req.industry,
        titles=req.titles,
        location=req.location,
        keywords=req.keywords,
        company_size=req.company_size,
        limit=req.limit,
        sender_name=req.sender_name,
        sender_company=req.sender_company,
        skip_outreach=req.skip_outreach,
        concurrency=int(os.getenv("ENRICHMENT_CONCURRENCY", "3")),
    )
    _active_runs[run_id] = "running"
    _executor.submit(_run_in_background, run_id, config)

    return {
        "run_id": run_id,
        "status": "running",
        "message": f"Run started. Poll GET /api/runs/{run_id} for progress.",
    }


@app.get("/api/runs", tags=["runs"])
def list_runs_endpoint(limit: int = Query(20, ge=1, le=100)):
    """List recent runs."""
    runs = list_runs(limit=limit)
    return {"runs": runs, "count": len(runs)}


@app.get("/api/runs/{run_id}", tags=["runs"])
def get_run_endpoint(run_id: str):
    """Get run status and summary. Once status='done', leads are available."""
    run = get_run(run_id)
    if not run:
        # Check in-memory (run may still be starting)
        if run_id in _active_runs:
            return {"run_id": run_id, "status": _active_runs[run_id], "leads": []}
        raise HTTPException(status_code=404, detail="Run not found")

    import json
    if isinstance(run.get("config"), str):
        run["config"] = json.loads(run["config"])
    if isinstance(run.get("summary"), str):
        run["summary"] = json.loads(run["summary"])

    # Include leads if run is done
    if run.get("status") == "done":
        run["leads"] = get_leads_for_run(run_id)

    return run


# ---- Leads ----

@app.get("/api/leads", tags=["leads"])
def list_leads_endpoint(
    tier: Optional[str] = Query(None, pattern="^(Hot|Warm|Cold)$"),
    min_score: Optional[int] = Query(None, ge=1, le=100),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """List leads with optional filtering."""
    leads = list_leads(tier=tier, min_score=min_score, limit=limit, offset=offset)
    return {"leads": leads, "count": len(leads)}


@app.get("/api/leads/{lead_id}", tags=["leads"])
def get_lead_endpoint(lead_id: str):
    """Get a single lead by ID."""
    lead = get_lead(lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead


# ---- Export ----

@app.post("/api/leads/export", tags=["leads"])
def export_endpoint(req: ExportRequest):
    """
    Export leads to CSV or JSON.
    Returns the file as a download.
    """
    if req.run_id:
        leads = get_leads_for_run(req.run_id)
    else:
        leads = list_leads(tier=req.tier, min_score=req.min_score, limit=500)

    if not leads:
        raise HTTPException(status_code=404, detail="No leads found matching criteria")

    output_path = export_leads(leads, fmt=req.format)
    media_type = "text/csv" if req.format == "csv" else "application/json"
    return FileResponse(
        path=output_path,
        media_type=media_type,
        filename=Path(output_path).name,
    )


# ---- Outreach regeneration ----

@app.post("/api/runs/{run_id}/outreach", tags=["runs"])
def regenerate_outreach_endpoint(run_id: str, req: RegenerateOutreachRequest):
    """Re-generate outreach emails for leads in a completed run."""
    run = get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    if run.get("status") != "done":
        raise HTTPException(status_code=409, detail="Run is not yet complete")

    updated = regenerate_outreach(run_id, tier_filter=req.tiers)
    return {
        "updated": len(updated),
        "run_id": run_id,
        "message": f"Regenerated outreach for {len(updated)} leads.",
    }
