# AI Lead Generation Agent

A production-ready CLI tool and REST API that autonomously finds, enriches, scores, and writes cold emails for B2B leads — using only **free tools + your Anthropic API key**.

```
 Discovery → Enrichment → Email Finding → Scoring → Outreach → Export
  (Google)    (BeautifulSoup)  (SMTP verify)  (Claude)  (Claude)  (CSV/JSON)
```

---

## Free Stack

| Layer | Tool | Cost |
|---|---|---|
| Web search | `googlesearch-python` (scrapes Google) | Free |
| Web scraping | `BeautifulSoup4` + `requests` | Free |
| Email finding | Pattern guessing + SMTP handshake | Free |
| AI reasoning | **Anthropic Claude** (claude-sonnet-4-20250514) | ~$0.003/lead |
| Storage | SQLite (built-in) | Free |
| API server | FastAPI + Uvicorn | Free |
| Google Sheets | `gspread` + service account | Free |

**No Tavily, no Brave Search, no Apollo, no Hunter.io.**

---

## Quick Start

### 1. Install dependencies

```bash
cd lead-gen-agent
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

> **Note:** `dnspython` is needed for SMTP email verification. It is included in `requirements.txt`.

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env and set ANTHROPIC_API_KEY=sk-ant-...
```

### 3. Run the demo (no scraping needed)

```bash
python demo/run_demo.py
```

This runs the full scoring + outreach pipeline on 10 pre-built mock UK B2B SaaS leads using real Claude API calls. Output appears in `demo/output/`.

---

## CLI Usage

### Run a full lead generation job

```bash
python cli/main.py run \
  --industry "B2B SaaS" \
  --titles "Head of Sales,VP Sales,CRO" \
  --location "UK" \
  --keywords "Series A,fintech" \
  --limit 30 \
  --sender-name "Alex" \
  --sender-company "SalesForge" \
  --export-csv
```

**Options:**

| Flag | Default | Description |
|---|---|---|
| `--industry` | required | Target industry |
| `--titles` | required | Comma-separated job titles |
| `--location` | "" | Geographic filter |
| `--keywords` | "" | Additional search keywords |
| `--company-size` | None | e.g. "50-200" |
| `--limit` | 30 | Max leads to find |
| `--concurrency` | 3 | Parallel enrichment workers |
| `--sender-name` | Alex | Your name (for emails) |
| `--sender-company` | YourCo | Your company (for emails) |
| `--skip-outreach` | False | Skip email generation |
| `--export-csv` | False | Auto-export CSV on completion |
| `--export-json` | False | Auto-export JSON on completion |

### Export results

```bash
# Export last run to CSV
python cli/main.py export --format csv

# Export specific run to JSON
python cli/main.py export --run-id <run-id> --format json

# Export only Hot leads to Google Sheets
python cli/main.py export --tier Hot --format sheets
```

### List leads and runs

```bash
python cli/main.py leads --tier Hot
python cli/main.py leads --min-score 70
python cli/main.py runs
```

### Start the REST API server

```bash
python cli/main.py serve --port 3000
# API docs: http://localhost:3000/docs
```

---

## REST API

### Start the server

```bash
uvicorn api.server:app --host 0.0.0.0 --port 3000
# or
python cli/main.py serve --port 3000
```

### Endpoints

```
GET  /health                    → liveness check
POST /api/runs                  → start a lead gen run (async)
GET  /api/runs                  → list recent runs
GET  /api/runs/{id}             → get run status + results
GET  /api/leads                 → list leads with filters
GET  /api/leads/{id}            → get single lead
POST /api/leads/export          → download CSV/JSON
POST /api/runs/{id}/outreach    → regenerate outreach emails
```

### Example: Start a run

```bash
curl -X POST http://localhost:3000/api/runs \
  -H "Content-Type: application/json" \
  -d '{
    "industry": "B2B SaaS",
    "titles": ["Head of Sales", "VP Sales"],
    "location": "UK",
    "keywords": ["Series A"],
    "limit": 20,
    "sender_name": "Alex",
    "sender_company": "SalesForge"
  }'
```

Response:
```json
{
  "run_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "running",
  "message": "Run started. Poll GET /api/runs/550e... for progress."
}
```

### Example: Poll for results

```bash
curl http://localhost:3000/api/runs/550e8400-e29b-41d4-a716-446655440000
```

### Example: Export

```bash
curl -X POST http://localhost:3000/api/leads/export \
  -H "Content-Type: application/json" \
  -d '{"format": "csv", "tier": "Hot"}' \
  --output hot_leads.csv
```

---

## Example Output

### Lead scoring output

```
Name            Title              Company      Score  Tier   Email
─────────────────────────────────────────────────────────────────────────────
Priya Sharma    CRO                FinFlowAI      87   Hot    priya.sharma@finflowai.com
Sarah Chen      VP of Sales        Growthly       82   Hot    sarah.chen@growthly.io
Elena Volkov    VP Sales EMEA      DataLoom       79   Hot    elena.volkov@dataloom.io
James Okafor    Head of Revenue    Stackify       71   Hot    james.okafor@stackify.com
Charlotte Davies Sales Director    Payloop        65   Warm   charlotte.davies@payloop.co.uk
Tom Whitfield   Director of Sales  Claritask      58   Warm   tom.whitfield@claritask.co
Ahmed Hassan    Head of Sales      Logiqo         52   Warm   ahmed.hassan@logiqo.com
Yuki Tanaka     CEO                Refyne         48   Warm   yuki.tanaka@refyne.ai
Rachel Park     VP Marketing       Contentful UK  41   Warm   rachel.park@contentful.com
Marcus Lee      Head of Parts.     Syntra Health  29   Cold   marcus.lee@syntrahealth.com
```

### Sample generated cold email

**Subject:** Quick question about FinFlowAI's outbound motion

> Hi Priya,
>
> I came across FinFlowAI's recent funding announcement and noticed you're scaling beyond the founder-led sales motion — a transition that's exciting but often exposes gaps in outbound structure and multi-stakeholder sequencing.
>
> At SalesForge, we help Series A fintech revenue leaders build repeatable outbound playbooks in 6 weeks — from ICP definition to sequenced cadences that work for CFO buying committees.
>
> Would a 15-minute call this week be worth it? No deck, just a quick conversation.
>
> Alex

---

## Google Sheets Export Setup

Free, takes ~10 minutes to configure.

### Steps

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or use existing)
3. Enable APIs:
   - `Google Sheets API`
   - `Google Drive API`
4. Create a **Service Account**:
   - IAM & Admin → Service Accounts → Create
   - Download the JSON key file
5. Set env var:
   ```bash
   GOOGLE_SHEETS_KEY_FILE=/path/to/service_account.json
   ```
6. Share your target spreadsheet with the service account email (from the JSON)
7. Export:
   ```bash
   python cli/main.py export --format sheets --sheets-name "My Leads"
   ```

---

## File Structure

```
lead-gen-agent/
├── src/
│   ├── __init__.py
│   ├── agent.py          # Main orchestration loop
│   ├── discovery.py      # Google scraping + lead finding
│   ├── enrichment.py     # Website scraping + Claude enrichment
│   ├── scoring.py        # Claude-powered scoring (1-100)
│   ├── outreach.py       # Claude cold email generation
│   ├── email_finder.py   # Pattern guessing + SMTP verification
│   ├── export.py         # CSV / JSON / Google Sheets
│   └── database.py       # SQLite schema + scrape cache
├── api/
│   ├── __init__.py
│   └── server.py         # FastAPI REST API
├── cli/
│   ├── __init__.py
│   └── main.py           # Click CLI
├── demo/
│   ├── run_demo.py       # End-to-end demo with 10 mock leads
│   └── output/           # Demo exports land here
├── exports/              # CLI/API exports land here
├── requirements.txt
├── .env.example
└── README.md
```

---

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `ANTHROPIC_API_KEY` | **Yes** | — | Your Anthropic API key |
| `CLAUDE_MODEL` | No | `claude-sonnet-4-20250514` | Claude model to use |
| `GOOGLE_SHEETS_KEY_FILE` | No | — | Path to service account JSON |
| `DATABASE_URL` | No | `leads.db` | SQLite database path |
| `ENRICHMENT_CONCURRENCY` | No | `3` | Parallel enrichment workers |
| `SCRAPE_DELAY_MIN` | No | `2` | Min seconds between Google requests |
| `SCRAPE_DELAY_MAX` | No | `5` | Max seconds between Google requests |
| `API_PORT` | No | `3000` | FastAPI server port |

---

## Scraping Notes

- **Google rate limiting:** Random 2-5s delays between requests. If Google blocks you (CAPTCHA), wait 10-15 minutes or switch IPs.
- **Scrape cache:** All website scrapes are cached in SQLite. Re-running the same job won't re-scrape already-visited URLs.
- **User-agent rotation:** 5 different real browser user-agents are rotated on every request.
- **Graceful degradation:** If a website is unreachable, the lead is still scored with whatever data exists — it never crashes the whole run.

---

## Cost Estimation

With `claude-sonnet-4-20250514`:

| Step | Tokens/lead | Cost/lead |
|---|---|---|
| Enrichment | ~800 in / ~200 out | ~$0.0012 |
| Scoring | ~600 in / ~150 out | ~$0.0009 |
| Outreach (Hot/Warm) | ~700 in / ~200 out | ~$0.0011 |
| **Total (hot lead)** | ~2100 in / ~550 out | **~$0.003** |

**30 leads ≈ $0.09 | 1,000 leads ≈ $3.00**

---

## SaaS Pricing Suggestions

If you want to productise this agent:

### Tier 1 — Starter ($49/month)
- 100 leads/month
- CSV + JSON export
- Email scoring + outreach

### Tier 2 — Growth ($149/month)
- 500 leads/month
- Google Sheets sync
- REST API access
- Priority support

### Tier 3 — Scale ($399/month)
- 2,000 leads/month
- Custom ICP profiles
- CRM webhooks (HubSpot, Salesforce)
- White-label option

### Usage-based Add-on
- $0.05 per lead above quota

**Unit economics at $149/month plan:**
- API cost: ~$0.003 × 500 = $1.50
- Hosting (Railway/Render): ~$5/month
- Gross margin: ~96%

---

## Troubleshooting

**`ModuleNotFoundError: No module named 'googlesearch'`**
```bash
pip install googlesearch-python
```

**`ModuleNotFoundError: No module named 'dns'`**
```bash
pip install dnspython
```

**Google returns no results / CAPTCHA**
- Increase `SCRAPE_DELAY_MIN` and `SCRAPE_DELAY_MAX` in `.env`
- Run with `--limit 10` to reduce query volume
- Try a different IP / VPN

**Claude returns invalid JSON**
- This is handled automatically with defaults — the lead will get score=50, tier=Warm
- Check logs for the raw Claude response

**SMTP verification always returns False**
- Many mail servers block SMTP probing — this is expected
- The agent falls back to pattern-guessed (unverified) emails automatically

---

## License

MIT — use freely, build commercially.
