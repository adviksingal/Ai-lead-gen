"""
FastAPI REST API
─────────────────
Exposes the lead generation pipeline as a secure, production-ready REST service.

Authentication:
    Set API_KEY in .env to require authentication.
    Clients pass:  X-API-Key: <key>  or  Authorization: Bearer <key>
    If API_KEY is not set, auth is disabled (useful for self-hosted dev).

Rate limiting:
    Default: 60 requests/minute per IP. Adjust via RATE_LIMIT_PER_MINUTE.

Endpoints:
    GET  /health                        liveness + readiness check
    GET  /api/stats                     aggregate stats across all runs
    POST /api/runs                      start a new lead gen run (async)
    GET  /api/runs                      list recent runs (paginated)
    GET  /api/runs/{id}                 get run status + summary
    GET  /api/runs/{id}/leads           get leads for a run (paginated)
    POST /api/runs/{id}/outreach        regenerate outreach emails for a run
    GET  /api/leads                     list all leads with filters
    GET  /api/leads/{id}                get single lead
    POST /api/leads/export              export leads to CSV/JSON (download)
"""

import json
import logging
import os
import sys
import time
from contextlib import asynccontextmanager
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from src.auth import require_api_key
from src.database import (
    init_db, get_run, list_runs, get_leads_for_run,
    list_leads, get_lead, get_stats,
)
from src.agent import RunConfig, run_lead_gen, regenerate_outreach
from src.export import export_leads
from src.search import active_provider

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Rate limiter
# ---------------------------------------------------------------------------

_rate_limit = os.getenv("RATE_LIMIT_PER_MINUTE", "60") + "/minute"
limiter = Limiter(key_func=get_remote_address, default_limits=[_rate_limit])

# Thread pool for background runs (max concurrent runs)
_max_runs = int(os.getenv("MAX_CONCURRENT_RUNS", "3"))
_executor = ThreadPoolExecutor(max_workers=_max_runs)
_active_runs: dict[str, str] = {}


# ---------------------------------------------------------------------------
# App lifecycle
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    logger.info(
        "Lead Gen API starting | search=%s | auth=%s",
        active_provider(),
        "enabled" if os.getenv("API_KEY") else "disabled",
    )
    yield
    _executor.shutdown(wait=False)
    logger.info("Lead Gen API shutting down")


app = FastAPI(
    title="AI Lead Generation Agent",
    description=(
        "Autonomously finds, enriches, scores, and writes personalised cold emails "
        "for B2B leads using web scraping + Claude AI.\n\n"
        "**Auth:** Pass `X-API-Key: <key>` or `Authorization: Bearer <key>` when `API_KEY` is set."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS — allow all origins by default; restrict via CORS_ORIGINS env var
_cors_origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# GZip compression for large responses
app.add_middleware(GZipMiddleware, minimum_size=1000)


# ---------------------------------------------------------------------------
# Request logging middleware
# ---------------------------------------------------------------------------

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = round((time.perf_counter() - start) * 1000)
    logger.info(
        "%s %s → %d  [%dms]  ip=%s",
        request.method,
        request.url.path,
        response.status_code,
        elapsed_ms,
        request.client.host if request.client else "unknown",
    )
    return response


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class StartRunRequest(BaseModel):
    industry: str = Field(..., examples=["B2B SaaS"])
    titles: list[str] = Field(..., examples=[["Head of Sales", "VP Sales"]])
    location: str = Field("", examples=["UK"])
    keywords: list[str] = Field(default_factory=list, examples=[["Series A", "fintech"]])
    company_size: Optional[str] = Field(None, examples=["50-200"])
    limit: int = Field(30, ge=1, le=200)
    sender_name: str = Field("Alex", examples=["Alex"])
    sender_company: str = Field("YourCo", examples=["Acme Inc"])
    skip_outreach: bool = False
    webhook_url: Optional[str] = Field(
        None,
        description="Optional URL to POST run.completed / run.failed events to",
        examples=["https://hooks.example.com/lead-gen"],
    )


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
    """Execute the full lead gen pipeline in a thread pool worker."""
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

@app.get("/health", tags=["meta"], summary="Liveness + readiness probe")
def health():
    """Returns service status, search provider, and auth configuration."""
    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "1.0.0",
        "anthropic_key_set": bool(os.getenv("ANTHROPIC_API_KEY")),
        "search_provider": active_provider(),
        "auth_enabled": bool(os.getenv("API_KEY")),
    }


@app.get("/api/stats", tags=["meta"], summary="Aggregate stats across all runs and leads")
@limiter.limit("30/minute")
def get_stats_endpoint(
    request: Request,
    _auth=Depends(require_api_key),
):
    """Returns counts of leads by tier, email coverage, average score, etc."""
    return get_stats()


# ── Runs ─────────────────────────────────────────────────────────────────────

@app.post("/api/runs", status_code=202, tags=["runs"], summary="Start a new lead gen run")
@limiter.limit("10/minute")
def start_run(
    request: Request,
    req: StartRunRequest,
    _auth=Depends(require_api_key),
):
    """
    Starts a lead generation run asynchronously.

    Returns `run_id` immediately. Poll `GET /api/runs/{run_id}` to check
    progress. When `status` is `done`, the `leads` array is populated.
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
        webhook_url=req.webhook_url,
        concurrency=int(os.getenv("ENRICHMENT_CONCURRENCY", "3")),
    )
    _active_runs[run_id] = "running"
    _executor.submit(_run_in_background, run_id, config)

    return {
        "run_id": run_id,
        "status": "running",
        "message": f"Run started. Poll GET /api/runs/{run_id} for progress.",
    }


@app.get("/api/runs", tags=["runs"], summary="List recent runs")
@limiter.limit("60/minute")
def list_runs_endpoint(
    request: Request,
    limit: int = Query(20, ge=1, le=100),
    _auth=Depends(require_api_key),
):
    runs = list_runs(limit=limit)
    return {"runs": runs, "count": len(runs)}


@app.get("/api/runs/{run_id}", tags=["runs"], summary="Get run status and summary")
@limiter.limit("60/minute")
def get_run_endpoint(
    request: Request,
    run_id: str,
    include_leads: bool = Query(False, description="Include leads in response (may be large)"),
    _auth=Depends(require_api_key),
):
    """
    Returns run status, config, and summary stats.
    Once `status` is `done`, set `include_leads=true` or use
    `GET /api/runs/{id}/leads` for paginated lead access.
    """
    run = get_run(run_id)
    if not run:
        if run_id in _active_runs:
            return {"run_id": run_id, "status": _active_runs[run_id]}
        raise HTTPException(status_code=404, detail="Run not found")

    if isinstance(run.get("config"), str):
        run["config"] = json.loads(run["config"])
    if isinstance(run.get("summary"), str):
        run["summary"] = json.loads(run["summary"])

    if include_leads and run.get("status") == "done":
        run["leads"] = get_leads_for_run(run_id)

    return run


@app.get("/api/runs/{run_id}/leads", tags=["runs"], summary="Get paginated leads for a run")
@limiter.limit("60/minute")
def get_run_leads(
    request: Request,
    run_id: str,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    tier: Optional[str] = Query(None, pattern="^(Hot|Warm|Cold)$"),
    _auth=Depends(require_api_key),
):
    """Paginated lead listing for a specific run. Supports tier filtering."""
    run = get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    all_leads = get_leads_for_run(run_id)
    if tier:
        all_leads = [l for l in all_leads if l.get("tier") == tier]

    total = len(all_leads)
    page = all_leads[offset: offset + limit]

    return {
        "run_id": run_id,
        "leads": page,
        "total": total,
        "limit": limit,
        "offset": offset,
        "has_more": (offset + limit) < total,
    }


@app.post("/api/runs/{run_id}/outreach", tags=["runs"], summary="Regenerate outreach emails")
@limiter.limit("10/minute")
def regenerate_outreach_endpoint(
    request: Request,
    run_id: str,
    req: RegenerateOutreachRequest,
    _auth=Depends(require_api_key),
):
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


# ── Leads ────────────────────────────────────────────────────────────────────

@app.get("/api/leads", tags=["leads"], summary="List leads with optional filters")
@limiter.limit("60/minute")
def list_leads_endpoint(
    request: Request,
    tier: Optional[str] = Query(None, pattern="^(Hot|Warm|Cold)$"),
    min_score: Optional[int] = Query(None, ge=1, le=100),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    _auth=Depends(require_api_key),
):
    leads = list_leads(tier=tier, min_score=min_score, limit=limit, offset=offset)
    return {"leads": leads, "count": len(leads), "limit": limit, "offset": offset}


@app.get("/api/leads/{lead_id}", tags=["leads"], summary="Get a single lead")
@limiter.limit("60/minute")
def get_lead_endpoint(
    request: Request,
    lead_id: str,
    _auth=Depends(require_api_key),
):
    lead = get_lead(lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead


# ── Export ───────────────────────────────────────────────────────────────────

@app.post("/api/leads/export", tags=["leads"], summary="Export leads to CSV or JSON")
@limiter.limit("20/minute")
def export_endpoint(
    request: Request,
    req: ExportRequest,
    _auth=Depends(require_api_key),
):
    """
    Downloads a CSV or JSON file of matching leads.

    Supply `run_id` to export a specific run, or use `tier`/`min_score` to
    filter across all leads.
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


# ---------------------------------------------------------------------------
# Serve built React frontend (production)
# Mount AFTER all API routes so they take priority.
# ---------------------------------------------------------------------------

_frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"

if _frontend_dist.exists():
    # Serve /assets/* (JS, CSS, images built by Vite)
    app.mount(
        "/assets",
        StaticFiles(directory=str(_frontend_dist / "assets")),
        name="frontend-assets",
    )

    @app.get("/{full_path:path}", include_in_schema=False)
    def serve_spa(full_path: str) -> FileResponse:
        """Catch-all: return index.html for all non-API paths (React Router)."""
        return FileResponse(str(_frontend_dist / "index.html"))
