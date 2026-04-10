# AI Lead Generation Agent

> Autonomously finds, enriches, scores, and writes personalised cold emails for B2B leads.  
> One API key. Zero scraping subscriptions. Fully self-hosted.

```
Discovery → Enrichment → Email Finding → Scoring → Outreach → Export
(Search)   (BeautifulSoup)  (SMTP verify)  (Claude)  (Claude)  (CSV/JSON/Sheets)
```

---

## Features

| | |
|---|---|
| **Lead Discovery** | Search LinkedIn profiles and company sites via Tavily, Brave, or Google |
| **AI Enrichment** | Scrape company websites; Claude extracts summary, pain points, tech signals |
| **Email Finding** | Pattern guessing (7 formats) + SMTP handshake verification — no Hunter.io |
| **AI Scoring** | Claude scores each lead 1–100 and classifies as Hot / Warm / Cold |
| **Outreach Generation** | Personalised cold emails with a quality gate (rejects generic output) |
| **Export** | CSV, JSON, or Google Sheets |
| **REST API** | FastAPI with auth, CORS, rate limiting, pagination, webhooks |
| **CLI** | Full-featured Click CLI with Rich progress display |
| **Docker** | One-command deployment with `docker-compose up` |
| **Tests** | 65 passing unit + integration tests |

---

## Tech Stack

| Layer | Tool | Cost |
|---|---|---|
| AI reasoning | Anthropic Claude (`claude-sonnet-4-20250514`) | ~$0.003/lead |
| Web search | Tavily API *(recommended)* / Brave Search / Google scraping | Free–$0.001/search |
| Web scraping | BeautifulSoup4 + requests | Free |
| Email finding | Pattern guessing + SMTP handshake | Free |
| Storage | SQLite (built-in, zero config) | Free |
| API server | FastAPI + Uvicorn | Free |
| CLI | Click + Rich | Free |

**30 leads ≈ $0.09 | 1,000 leads ≈ $3.00**

---

## Quick Start

### Option A — Docker (recommended for production)

```bash
git clone https://github.com/adviksingal/ai-lead-gen
cd ai-lead-gen/lead-gen-agent

cp .env.example .env
# Edit .env — set ANTHROPIC_API_KEY and (optionally) TAVILY_API_KEY, API_KEY

docker-compose up -d
# API now running at http://localhost:3000
# Docs at http://localhost:3000/docs
```

### Option B — Local install

```bash
cd lead-gen-agent

python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

pip install -e .                  # installs 'agent' CLI entry point
# or: pip install -r requirements.txt

cp .env.example .env              # fill in ANTHROPIC_API_KEY
```

### Run the demo (no scraping needed)

```bash
python demo/run_demo.py
```

Runs the full scoring + outreach pipeline on 10 pre-built mock UK B2B SaaS leads using real Claude API calls (~$0.03). Output lands in `demo/output/`.

---

## CLI Reference

### `agent run` — full lead generation pipeline

```bash
agent run \
  --industry "B2B SaaS" \
  --titles "Head of Sales,VP Sales,CRO" \
  --location "UK" \
  --keywords "Series A,fintech" \
  --company-size "50-200" \
  --limit 30 \
  --sender-name "Alex" \
  --sender-company "SalesForge" \
  --export-csv
```

| Flag | Default | Description |
|---|---|---|
| `--industry` | **required** | Target industry |
| `--titles` | **required** | Comma-separated job titles |
| `--location` | `""` | Geographic filter |
| `--keywords` | `""` | Additional search keywords |
| `--company-size` | `None` | e.g. `"50-200"` |
| `--limit` / `-n` | `30` | Max leads to discover |
| `--concurrency` / `-c` | `3` | Parallel enrichment workers |
| `--sender-name` | `Alex` | Your first name (for emails) |
| `--sender-company` | `YourCo` | Your company name (for emails) |
| `--skip-outreach` | `False` | Skip email generation |
| `--export-csv` | `False` | Auto-export CSV when done |
| `--export-json` | `False` | Auto-export JSON when done |

### `agent export` — export stored leads

```bash
# Export most recent run to CSV
agent export --format csv

# Export a specific run to JSON
agent export --run-id <run-id> --format json

# Export only Hot leads to Google Sheets
agent export --format sheets --tier Hot --sheets-name "Hot Leads Q1"

# Save to a specific path
agent export --format csv --output /tmp/my_leads.csv
```

### `agent leads` — browse the database

```bash
agent leads --tier Hot --limit 20
agent leads --min-score 70
```

### `agent runs` — list past runs

```bash
agent runs --limit 10
```

### `agent serve` — start the REST API

```bash
agent serve --port 3000 --host 0.0.0.0

# Dev mode with auto-reload
agent serve --port 3000 --reload
```

---

## REST API Reference

Base URL: `http://localhost:3000`  
Interactive docs: `http://localhost:3000/docs`

### Authentication

Set `API_KEY` in `.env` to enable. All protected endpoints require one of:

```
X-API-Key: your-secret-key
Authorization: Bearer your-secret-key
```

If `API_KEY` is unset, auth is disabled (safe for self-hosted / local use).

---

### `GET /health`

Liveness + readiness probe. No auth required.

```bash
curl http://localhost:3000/health
```

```json
{
  "status": "ok",
  "version": "1.0.0",
  "anthropic_key_set": true,
  "search_provider": "tavily",
  "auth_enabled": true
}
```

---

### `GET /api/stats`

Aggregate stats across all runs and leads.

```bash
curl -H "X-API-Key: $API_KEY" http://localhost:3000/api/stats
```

```json
{
  "total_leads": 147,
  "total_runs": 8,
  "hot_leads": 41,
  "warm_leads": 63,
  "cold_leads": 43,
  "leads_with_email": 129,
  "leads_with_verified_email": 31,
  "leads_with_outreach": 104,
  "average_score": 58.3,
  "scrape_cache_entries": 312
}
```

---

### `POST /api/runs` — Start a run

```bash
curl -X POST http://localhost:3000/api/runs \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "industry": "B2B SaaS",
    "titles": ["Head of Sales", "VP Sales", "CRO"],
    "location": "UK",
    "keywords": ["Series A", "fintech"],
    "limit": 30,
    "sender_name": "Alex",
    "sender_company": "SalesForge",
    "webhook_url": "https://hooks.yourco.com/lead-gen"
  }'
```

Returns `202 Accepted` immediately:

```json
{
  "run_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "running",
  "message": "Run started. Poll GET /api/runs/550e8400... for progress."
}
```

---

### `GET /api/runs/{run_id}` — Poll run status

```bash
curl -H "X-API-Key: $API_KEY" \
  "http://localhost:3000/api/runs/550e8400-...?include_leads=true"
```

When `status` is `done`:

```json
{
  "id": "550e8400-...",
  "status": "done",
  "config": { "industry": "B2B SaaS", "titles": [...], ... },
  "summary": {
    "total_leads": 30,
    "discovered": 30,
    "enriched": 30,
    "emails_found": 22,
    "scored": 30,
    "outreach_written": 18,
    "elapsed_seconds": 142.3
  },
  "leads": [...]
}
```

---

### `GET /api/runs/{run_id}/leads` — Paginated leads

```bash
# Page 1: Hot leads only
curl -H "X-API-Key: $API_KEY" \
  "http://localhost:3000/api/runs/550e.../leads?tier=Hot&limit=10&offset=0"
```

```json
{
  "run_id": "550e8400-...",
  "leads": [...],
  "total": 12,
  "limit": 10,
  "offset": 0,
  "has_more": true
}
```

---

### `GET /api/leads` — List all leads

```bash
# All Hot leads with score ≥ 75
curl -H "X-API-Key: $API_KEY" \
  "http://localhost:3000/api/leads?tier=Hot&min_score=75&limit=50"
```

---

### `POST /api/leads/export` — Download CSV or JSON

```bash
# Download Hot leads as CSV
curl -X POST http://localhost:3000/api/leads/export \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"tier": "Hot", "format": "csv"}' \
  --output hot_leads.csv

# Download a specific run as JSON
curl -X POST http://localhost:3000/api/leads/export \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"run_id": "550e8400-...", "format": "json"}' \
  --output run_results.json
```

---

### `POST /api/runs/{run_id}/outreach` — Regenerate emails

```bash
curl -X POST http://localhost:3000/api/runs/550e.../outreach \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"tiers": ["Hot", "Warm"]}'
```

---

## Webhooks

Set `webhook_url` in your run request and the agent will `POST` a signed payload when the run completes or fails.

### Payload shape

```json
{
  "event": "run.completed",
  "timestamp": "2025-04-10T14:32:00Z",
  "run_id": "550e8400-...",
  "status": "done",
  "summary": {
    "total_leads": 30,
    "hot_leads": 8,
    "outreach_written": 21,
    "elapsed_seconds": 138.4
  }
}
```

Events: `run.completed` | `run.failed`

### Signature verification

Set `WEBHOOK_SECRET` in `.env`. Every request will include:

```
X-Lead-Gen-Signature: sha256=<hmac-sha256-of-body>
```

Verify on your server:

```python
import hmac, hashlib

def verify(body: bytes, header: str, secret: str) -> bool:
    expected = "sha256=" + hmac.new(
        secret.encode(), body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, header)
```

---

## Deployment

### Docker (recommended)

```bash
# 1. Clone and configure
cp .env.example .env
# Set ANTHROPIC_API_KEY, API_KEY, optionally TAVILY_API_KEY

# 2. Start
docker-compose up -d

# 3. Verify
curl http://localhost:3000/health

# View logs
docker-compose logs -f api
```

The SQLite database and exports are stored in named Docker volumes (`lead-data`, `lead-exports`) and persist across restarts.

### Railway

```bash
# Install Railway CLI: https://railway.app
railway login
railway init
railway up

# Set env vars in Railway dashboard:
# ANTHROPIC_API_KEY, API_KEY, TAVILY_API_KEY
```

### Render

1. Connect GitHub repo to Render
2. Set **Start Command**: `agent serve --host 0.0.0.0 --port $PORT`
3. Add env vars in Render dashboard
4. Deploy

### Heroku

```bash
heroku create my-lead-gen-agent
heroku config:set ANTHROPIC_API_KEY=sk-ant-...
heroku config:set API_KEY=your-secret
git push heroku main
```

---

## Search Provider Setup

The agent auto-selects based on available API keys: **Tavily → Brave → Google**.

### Tavily (recommended — $0.001/search, structured results)

1. Sign up at [tavily.com](https://tavily.com)
2. Copy your API key
3. Set `TAVILY_API_KEY=tvly-...` in `.env`

### Brave Search (2,000 free queries/month)

1. Apply at [brave.com/search/api](https://brave.com/search/api/)
2. Set `BRAVE_API_KEY=BSA...` in `.env`

### Google scraping (free, no key needed)

Default fallback. Uses `googlesearch-python` + HTTP scraping with user-agent rotation and random delays. Reliable for low volumes; may hit rate limits on large runs.

---

## Google Sheets Export

Free, takes ~10 minutes to set up.

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Enable **Google Sheets API** and **Google Drive API**
3. Create a **Service Account** → download the JSON key
4. Set `GOOGLE_SHEETS_KEY_FILE=/path/to/service_account.json` in `.env`
5. Share your target spreadsheet with the service account email

```bash
agent export --format sheets --sheets-name "AI Leads Q2 2025"
```

---

## Configuration Reference

| Variable | Required | Default | Description |
|---|---|---|---|
| `ANTHROPIC_API_KEY` | **Yes** | — | Your Anthropic API key |
| `TAVILY_API_KEY` | No | — | Tavily search API key (recommended) |
| `BRAVE_API_KEY` | No | — | Brave Search API key |
| `API_KEY` | No | — | REST API authentication key |
| `WEBHOOK_SECRET` | No | — | HMAC signing secret for webhooks |
| `CLAUDE_MODEL` | No | `claude-sonnet-4-20250514` | Claude model to use |
| `GOOGLE_SHEETS_KEY_FILE` | No | — | Path to service account JSON |
| `DATABASE_URL` | No | `leads.db` | SQLite database path |
| `ENRICHMENT_CONCURRENCY` | No | `3` | Parallel enrichment workers |
| `MAX_CONCURRENT_RUNS` | No | `3` | Max parallel API runs |
| `SCRAPE_DELAY_MIN` | No | `2` | Min seconds between Google requests |
| `SCRAPE_DELAY_MAX` | No | `5` | Max seconds between Google requests |
| `API_PORT` | No | `3000` | REST API server port |
| `CORS_ORIGINS` | No | `*` | Allowed CORS origins (comma-separated) |
| `RATE_LIMIT_PER_MINUTE` | No | `60` | API rate limit per IP |

---

## Example Output

### CLI results table

```
┏━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━┳━━━━━━━┳━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┓
┃ Name             ┃ Title               ┃ Company          ┃ Score ┃ Tier ┃ Email                        ┃ Has Outreach ┃
┡━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━╇━━━━━━━╇━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━┩
│ Priya Sharma     │ Chief Revenue Offic │ FinFlowAI        │   87  │ Hot  │ priya.sharma@finflowai.com   │      ✓       │
│ Sarah Chen       │ VP of Sales         │ Growthly         │   82  │ Hot  │ sarah.chen@growthly.io       │      ✓       │
│ Elena Volkov     │ VP Sales EMEA       │ DataLoom         │   79  │ Hot  │ elena.volkov@dataloom.io     │      ✓       │
│ James Okafor     │ Head of Revenue     │ Stackify         │   71  │ Hot  │ james.okafor@stackify.com    │      ✓       │
│ Charlotte Davies │ Sales Director      │ Payloop          │   65  │ Warm │ charlotte.davies@payloop.co  │      ✓       │
│ Tom Whitfield    │ Director of Sales   │ Claritask        │   58  │ Warm │ tom.whitfield@claritask.co   │      ✓       │
│ Ahmed Hassan     │ Head of Sales       │ Logiqo           │   52  │ Warm │ ahmed.hassan@logiqo.com      │      ✓       │
│ Marcus Lee       │ Head of Partnersh   │ Syntra Health    │   29  │ Cold │ —                            │      —       │
└──────────────────┴─────────────────────┴──────────────────┴───────┴──────┴──────────────────────────────┴──────────────┘

Summary: 8 leads | Hot: 4 | Warm: 3 | Cold: 1 | Emails found: 7
```

### Sample generated cold email

**Subject:** Quick question about FinFlowAI's outbound motion

> Hi Priya,
>
> I came across FinFlowAI's recent funding announcement and noticed you're scaling beyond the founder-led sales motion — a transition that's exciting but often exposes gaps in outbound structure and multi-stakeholder sequencing for CFO buying committees.
>
> At SalesForge, we help Series A fintech revenue leaders build repeatable outbound playbooks in 6 weeks — from ICP definition to sequenced cadences that work for complex buying committees.
>
> Would a 15-minute call this week be worth it? No deck, just a quick conversation.
>
> Alex

---

## File Structure

```
lead-gen-agent/
├── src/
│   ├── agent.py          # Orchestration loop (discovery → enrich → score → outreach)
│   ├── discovery.py      # Lead discovery via web search + deduplication
│   ├── search.py         # Search abstraction (Tavily / Brave / Google)
│   ├── enrichment.py     # Website scraping + Claude AI enrichment
│   ├── email_finder.py   # Email pattern generation + SMTP verification
│   ├── scoring.py        # Claude scoring (1–100, Hot/Warm/Cold)
│   ├── outreach.py       # Claude cold email generation + quality gate
│   ├── export.py         # CSV / JSON / Google Sheets export
│   ├── database.py       # SQLite schema, CRUD, scrape cache, dedup
│   ├── auth.py           # API key authentication middleware
│   └── webhook.py        # Run completion webhook notifier
├── api/
│   └── server.py         # FastAPI REST API (auth, CORS, rate limiting)
├── cli/
│   └── main.py           # Click CLI with Rich output
├── tests/
│   ├── conftest.py       # Shared fixtures (isolated DB, mock Claude)
│   ├── test_database.py  # DB CRUD, dedup, cache, stats (15 tests)
│   ├── test_export.py    # CSV/JSON export correctness (14 tests)
│   ├── test_outreach.py  # Quality gate, email gen, scoring (15 tests)
│   └── test_api.py       # All REST endpoints, auth, CORS (22 tests)
├── demo/
│   ├── run_demo.py       # End-to-end demo with 10 mock leads
│   └── output/           # Demo exports land here
├── Dockerfile
├── docker-compose.yml
├── Makefile
├── pyproject.toml        # Package config + 'agent' CLI entry point
├── requirements.txt
└── .env.example
```

---

## Running Tests

```bash
# Run all 65 tests
make test
# or: pytest tests/ -v

# With coverage report
make test-cov

# Single module
pytest tests/test_api.py -v
pytest tests/test_outreach.py -v -k "quality_gate"
```

---

## Cost Estimation

With `claude-sonnet-4-20250514` (as of April 2025):

| Step | Tokens/lead (approx) | Cost/lead |
|---|---|---|
| Enrichment | ~800 in / ~200 out | ~$0.0012 |
| Scoring | ~600 in / ~150 out | ~$0.0009 |
| Outreach (Hot/Warm) | ~700 in / ~200 out | ~$0.0011 |
| **Total (hot lead)** | ~2,100 in / ~550 out | **~$0.003** |

| Volume | Est. Claude cost |
|---|---|
| 30 leads | ~$0.09 |
| 100 leads | ~$0.30 |
| 500 leads | ~$1.50 |
| 1,000 leads | ~$3.00 |

Search costs (Tavily): ~$0.001/query × ~3 queries/lead = ~$0.003/lead additional.

---

## SaaS Pricing Model

If you're building this into a commercial product:

### Tier 1 — Starter · $49/month
- 200 leads/month
- CSV + JSON export
- AI scoring + outreach emails
- Email support

### Tier 2 — Growth · $149/month
- 750 leads/month
- Google Sheets sync
- REST API access + webhooks
- Priority support
- Custom sender name/company

### Tier 3 — Scale · $399/month
- 2,500 leads/month
- Custom ICP profiles saved
- CRM-ready export formats (HubSpot, Salesforce)
- Dedicated account manager
- SLA: 99.5% uptime

### Usage-based add-on
- $0.05/lead above monthly quota

**Unit economics at Tier 2 ($149/month, 750 leads):**

| Item | Monthly cost |
|---|---|
| Claude API (750 × $0.003) | $2.25 |
| Tavily API (750 × $0.003) | $2.25 |
| Server (Railway/Render) | $5.00 |
| **Total COGS** | **$9.50** |
| **Gross margin** | **~94%** |

---

## Troubleshooting

**`ModuleNotFoundError: No module named 'tavily'`**
```bash
pip install tavily-python
```

**`ModuleNotFoundError: No module named 'dns'`**
```bash
pip install dnspython
```

**Google returns no results / CAPTCHA**
- Switch to Tavily or Brave Search (set API key in `.env`)
- Increase `SCRAPE_DELAY_MIN` and `SCRAPE_DELAY_MAX`
- Reduce `--limit` for smaller runs
- Wait 10–15 minutes or use a different IP

**Claude returns invalid JSON**
- Handled automatically with defaults (score=50, tier=Warm)
- Check logs for the raw Claude response if you need to debug

**SMTP verification always returns False**
- Many mail servers block port 25 SMTP probing — this is normal
- The agent falls back to pattern-guessed (unverified) emails automatically
- SMTP verification works best from a server IP (not residential)

**Rate limit exceeded (API)**
- Increase `RATE_LIMIT_PER_MINUTE` in `.env`
- Or add `X-API-Key` to avoid the default per-IP limit

---

## License

MIT — use freely, build commercially.
