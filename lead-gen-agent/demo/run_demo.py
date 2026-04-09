#!/usr/bin/env python3
"""
End-to-End Demo
────────────────
Demonstrates the full pipeline with 10 pre-built mock leads so you can
see real AI scoring + outreach without spending API budget on scraping.

Run:
  cd lead-gen-agent
  python demo/run_demo.py

What it does:
  1. Seeds 10 realistic mock leads (no Google scraping needed)
  2. Runs enrichment stubs (simulated website data)
  3. Calls Claude for scoring and outreach generation (real API calls)
  4. Prints a rich table + sample emails
  5. Exports to demo/output/demo_leads.csv and demo/output/demo_leads.json
"""

import json
import logging
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.rule import Rule
from rich import print as rprint

console = Console()
logging.basicConfig(level=logging.WARNING)  # quiet during demo

# ---------------------------------------------------------------------------
# 10 mock leads (realistic B2B SaaS UK scenario)
# ---------------------------------------------------------------------------

MOCK_LEADS = [
    {
        "name": "Sarah Chen",
        "title": "VP of Sales",
        "company": "Growthly",
        "website": "https://growthly.io",
        "location": "London, UK",
        "linkedin_url": "https://linkedin.com/in/sarah-chen-growthly",
        "source": "google_linkedin",
        "company_summary": (
            "Growthly is a B2B SaaS platform that helps mid-market revenue teams "
            "automate pipeline management and forecast accuracy. They serve 200+ "
            "customers in the UK and Europe, primarily targeting Series B+ companies."
        ),
        "pain_points": [
            "Manual CRM data entry consuming 30% of rep time",
            "Pipeline forecast accuracy below 60%",
            "Lack of real-time deal risk signals",
        ],
        "tech_signals": [
            "Salesforce CRM integration mentioned on pricing page",
            "Hiring 3 Sales Engineers (LinkedIn job posts)",
            "Published blog post on RevOps automation",
        ],
    },
    {
        "name": "James Okafor",
        "title": "Head of Revenue",
        "company": "Stackify",
        "website": "https://stackify.com",
        "location": "Manchester, UK",
        "linkedin_url": "https://linkedin.com/in/james-okafor-stackify",
        "source": "google_linkedin",
        "company_summary": (
            "Stackify provides developer-focused APM and log management tools "
            "for SaaS companies. Founded in 2012, they serve 7,000+ customers "
            "globally with a focus on SMB engineering teams."
        ),
        "pain_points": [
            "High customer churn due to onboarding complexity",
            "PLG motion needs sales assist at key conversion points",
            "No structured SDR process for enterprise upsell",
        ],
        "tech_signals": [
            "Product-led growth model (free tier on homepage)",
            "Recent Series A announcement ($12M)",
            "HubSpot forms on contact page",
        ],
    },
    {
        "name": "Priya Sharma",
        "title": "Chief Revenue Officer",
        "company": "FinFlowAI",
        "website": "https://finflowai.com",
        "location": "London, UK",
        "linkedin_url": "https://linkedin.com/in/priya-sharma-finflowai",
        "source": "google_linkedin",
        "company_summary": (
            "FinFlowAI uses machine learning to automate accounts payable and "
            "receivable workflows for UK fintechs and mid-market finance teams. "
            "Backed by Balderton Capital, Series A."
        ),
        "pain_points": [
            "Scaling sales from founder-led to repeatable motion",
            "No outbound playbook for enterprise accounts",
            "CFO buying committee requires multi-stakeholder nurture",
        ],
        "tech_signals": [
            "Intercom chat widget on site",
            "4 open BDR roles on LinkedIn",
            "Case study mentions Revolut and Monzo as customers",
        ],
    },
    {
        "name": "Tom Whitfield",
        "title": "Director of Sales",
        "company": "Claritask",
        "website": "https://claritask.co",
        "location": "Bristol, UK",
        "linkedin_url": "https://linkedin.com/in/tom-whitfield-claritask",
        "source": "google_linkedin",
        "company_summary": (
            "Claritask is a project management SaaS for professional services firms, "
            "competing with Asana and Monday.com in the UK market. "
            "~150 employees, bootstrapped."
        ),
        "pain_points": [
            "Difficulty competing against well-funded incumbents on brand",
            "Long sales cycles due to committee buying in PSF segment",
            "No sales automation beyond basic email sequences",
        ],
        "tech_signals": [
            "Zapier and Make.com integrations listed",
            "Blog posts on Asana vs Claritask comparisons",
            "Active G2 review acquisition programme",
        ],
    },
    {
        "name": "Elena Volkov",
        "title": "VP Sales EMEA",
        "company": "DataLoom",
        "website": "https://dataloom.io",
        "location": "London, UK",
        "linkedin_url": "https://linkedin.com/in/elena-volkov-dataloom",
        "source": "google_linkedin",
        "company_summary": (
            "DataLoom is a no-code data pipeline platform targeting data teams at "
            "growth-stage SaaS companies. Series B ($45M), 300 employees. "
            "Strong product-market fit in the UK and DACH markets."
        ),
        "pain_points": [
            "Expanding into enterprise requiring new sales methodology",
            "Lack of sales engineering capacity for complex PoCs",
            "Territory management is manual in Google Sheets",
        ],
        "tech_signals": [
            "Snowflake and dbt partner page",
            "Hiring VP Enterprise Sales on LinkedIn",
            "Gong.io mentioned in a job description",
        ],
    },
    {
        "name": "Marcus Lee",
        "title": "Head of Partnerships",
        "company": "Syntra Health",
        "website": "https://syntrahealth.com",
        "location": "Edinburgh, UK",
        "linkedin_url": "https://linkedin.com/in/marcus-lee-syntra",
        "source": "google_company",
        "company_summary": (
            "Syntra Health builds clinical workflow software for NHS trusts and "
            "private healthcare providers in the UK. Heavily regulated space, "
            "long procurement cycles. Series A, 80 employees."
        ),
        "pain_points": [
            "NHS procurement cycles take 18-24 months",
            "Partnerships channel underutilised for faster GTM",
            "No CRM tracking for partner-sourced pipeline",
        ],
        "tech_signals": [
            "Partnership page lists 3 NHS pilot sites",
            "Blog posts about NHS digital transformation",
            "Hiring Head of Sales on Indeed",
        ],
    },
    {
        "name": "Yuki Tanaka",
        "title": "Founder & CEO",
        "company": "Refyne",
        "website": "https://refyne.ai",
        "location": "London, UK",
        "linkedin_url": "https://linkedin.com/in/yuki-tanaka-refyne",
        "source": "google_linkedin",
        "company_summary": (
            "Refyne is an AI-powered code review tool for engineering teams, "
            "positioned as a GitHub Copilot companion. Pre-Series A, 12 employees, "
            "strong developer community traction."
        ),
        "pain_points": [
            "Transitioning from bottoms-up dev adoption to enterprise sales",
            "No structured sales function — founder doing all sales",
            "Pricing and packaging not aligned for enterprise buyers",
        ],
        "tech_signals": [
            "GitHub and GitLab integrations on website",
            "Y Combinator W24 badge on homepage",
            "Active Product Hunt launch page",
        ],
    },
    {
        "name": "Charlotte Davies",
        "title": "Sales Director",
        "company": "Payloop",
        "website": "https://payloop.co.uk",
        "location": "London, UK",
        "linkedin_url": "https://linkedin.com/in/charlotte-davies-payloop",
        "source": "google_linkedin",
        "company_summary": (
            "Payloop is a UK-based payroll automation SaaS for SMBs, competing with "
            "Sage and Xero. 500+ customers, 40 employees, profitable and growing. "
            "Recently launched an API for embedded payroll."
        ),
        "pain_points": [
            "Limited outbound capability — mostly inbound and referral",
            "Embedded payroll API needs different sales motion (partner/developer)",
            "No sales forecasting or pipeline visibility",
        ],
        "tech_signals": [
            "Xero marketplace listing",
            "API docs with Stripe-style UX",
            "Mentions Making Tax Digital compliance",
        ],
    },
    {
        "name": "Ahmed Hassan",
        "title": "Head of Sales",
        "company": "Logiqo",
        "website": "https://logiqo.com",
        "location": "Leeds, UK",
        "linkedin_url": "https://linkedin.com/in/ahmed-hassan-logiqo",
        "source": "google_linkedin",
        "company_summary": (
            "Logiqo builds supply chain optimisation software for mid-market "
            "UK manufacturers and 3PL providers. Bootstrapped, 25 employees, "
            "profitable. Thinking about raising a seed round."
        ),
        "pain_points": [
            "Manual quoting and order management in Excel",
            "No structured lead qualification process",
            "Sales team of 2 reps with no sales tooling",
        ],
        "tech_signals": [
            "SAP integration mentioned on features page",
            "Case study with a UK logistics firm",
            "Job post for junior BDR on LinkedIn",
        ],
    },
    {
        "name": "Rachel Park",
        "title": "VP Marketing",
        "company": "Contentful UK",
        "website": "https://contentful.com",
        "location": "London, UK",
        "linkedin_url": "https://linkedin.com/in/rachel-park-contentful",
        "source": "google_linkedin",
        "company_summary": (
            "Contentful is a global headless CMS leader with a significant UK "
            "enterprise presence. Series E, 800+ employees. Rachel leads the EMEA "
            "demand gen and marketing ops function."
        ),
        "pain_points": [
            "Marketing → sales handoff quality and SLA compliance",
            "ABM programme needs tighter sales alignment",
            "Attribution modelling across a complex multi-touch journey",
        ],
        "tech_signals": [
            "Marketo and Salesforce logos on integration page",
            "Partner ecosystem page with 300+ technology partners",
            "Hiring a Revenue Operations Manager",
        ],
    },
]


# ---------------------------------------------------------------------------
# Demo runner
# ---------------------------------------------------------------------------

def run_demo() -> None:
    console.print(Panel.fit(
        "[bold cyan]AI Lead Generation Agent — Demo[/]\n"
        "Running full pipeline on 10 mock leads (real Claude API calls)",
        border_style="cyan",
    ))

    if not os.getenv("ANTHROPIC_API_KEY"):
        console.print(
            "[bold red]Error:[/] ANTHROPIC_API_KEY not set.\n"
            "Copy .env.example to .env and add your key, then re-run."
        )
        sys.exit(1)

    # Initialise DB
    from src.database import init_db, upsert_lead, create_run, update_run_status
    init_db()

    run_id = str(uuid.uuid4())
    run_config = {
        "industry": "B2B SaaS",
        "titles": ["VP of Sales", "Head of Sales", "CRO", "Sales Director"],
        "location": "UK",
        "keywords": ["SaaS", "fintech", "Series A"],
        "limit": 10,
        "demo": True,
    }
    create_run(run_id, run_config)

    # Seed leads with run_id
    leads = []
    for mock in MOCK_LEADS:
        lead = dict(mock)
        lead["id"] = str(uuid.uuid4())
        lead["run_id"] = run_id
        lead["created_at"] = datetime.now(timezone.utc).isoformat()
        lead["enriched_at"] = datetime.now(timezone.utc).isoformat()
        lead["email"] = f"{mock['name'].split()[0].lower()}.{mock['name'].split()[-1].lower()}@{mock['website'].replace('https://', '').replace('http://', '').split('/')[0]}"
        lead["email_verified"] = 0
        lead["email_source"] = "pattern_guess_unverified"
        leads.append(lead)

    console.print(f"\n[bold]Step 1/3:[/] Loaded {len(leads)} mock leads\n")

    # ---- Scoring ----
    console.print(Rule("[bold yellow]Step 2/3: Scoring leads with Claude[/]"))
    from src.scoring import score_lead

    for i, lead in enumerate(leads, 1):
        console.print(f"  Scoring [{i}/{len(leads)}]: [cyan]{lead['name']}[/] @ [cyan]{lead['company']}[/]...")
        lead = score_lead(lead, run_config=run_config)
        leads[i - 1] = lead
        upsert_lead(lead)
        tier_col = {"Hot": "red", "Warm": "yellow", "Cold": "blue"}.get(lead["tier"], "white")
        console.print(
            f"    → Score: [bold]{lead['score']}[/] | "
            f"Tier: [{tier_col}]{lead['tier']}[/{tier_col}] | "
            f"{lead['score_reasoning'][:80]}..."
        )

    # ---- Outreach ----
    console.print(f"\n")
    console.print(Rule("[bold yellow]Step 3/3: Generating outreach emails (Hot + Warm only)[/]"))
    from src.outreach import generate_outreach_email

    hot_warm = [l for l in leads if l.get("tier") in ("Hot", "Warm")]
    for i, lead in enumerate(hot_warm, 1):
        console.print(f"  Writing email [{i}/{len(hot_warm)}]: [cyan]{lead['name']}[/] @ [cyan]{lead['company']}[/]...")
        lead = generate_outreach_email(lead, sender_name="Alex", sender_company="SalesForge")
        # Update in main list
        for j, l in enumerate(leads):
            if l["id"] == lead["id"]:
                leads[j] = lead
        upsert_lead(lead)

    # ---- Results table ----
    console.print(f"\n")
    console.print(Rule("[bold cyan]Results[/]"))

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("#", width=3)
    table.add_column("Name", width=18)
    table.add_column("Title", width=22)
    table.add_column("Company", width=16)
    table.add_column("Score", justify="center", width=7)
    table.add_column("Tier", width=7)
    table.add_column("Email", width=30)

    tier_col_map = {"Hot": "red", "Warm": "yellow", "Cold": "blue"}
    sorted_leads = sorted(leads, key=lambda x: x.get("score") or 0, reverse=True)

    for i, lead in enumerate(sorted_leads, 1):
        tier = lead.get("tier") or "—"
        tc = tier_col_map.get(tier, "white")
        table.add_row(
            str(i),
            lead.get("name") or "—",
            (lead.get("title") or "—")[:22],
            (lead.get("company") or "—")[:16],
            str(lead.get("score") or "—"),
            f"[{tc}]{tier}[/{tc}]",
            lead.get("email") or "—",
        )

    console.print(table)

    # ---- Sample emails ----
    hot_leads_with_email = [l for l in sorted_leads if l.get("tier") == "Hot" and l.get("email_subject")]
    if hot_leads_with_email:
        console.print(f"\n")
        console.print(Rule("[bold red]Sample Hot Lead Email[/]"))
        sample = hot_leads_with_email[0]
        console.print(Panel(
            f"[bold]To:[/] {sample.get('name')} <{sample.get('email', 'unknown')}>\n"
            f"[bold]Subject:[/] {sample.get('email_subject', '')}\n\n"
            f"{sample.get('email_body', '')}",
            title=f"Email for {sample.get('company')}",
            border_style="red",
        ))

    warm_leads_with_email = [l for l in sorted_leads if l.get("tier") == "Warm" and l.get("email_subject")]
    if warm_leads_with_email:
        console.print(f"\n")
        console.print(Rule("[bold yellow]Sample Warm Lead Email[/]"))
        sample = warm_leads_with_email[0]
        console.print(Panel(
            f"[bold]To:[/] {sample.get('name')} <{sample.get('email', 'unknown')}>\n"
            f"[bold]Subject:[/] {sample.get('email_subject', '')}\n\n"
            f"{sample.get('email_body', '')}",
            title=f"Email for {sample.get('company')}",
            border_style="yellow",
        ))

    # ---- Export ----
    console.print(f"\n")
    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)

    from src.export import export_csv, export_json
    csv_path = export_csv(leads, str(output_dir / "demo_leads.csv"))
    json_path = export_json(leads, str(output_dir / "demo_leads.json"))

    # ---- Summary ----
    hot = sum(1 for l in leads if l.get("tier") == "Hot")
    warm = sum(1 for l in leads if l.get("tier") == "Warm")
    cold = sum(1 for l in leads if l.get("tier") == "Cold")
    with_outreach = sum(1 for l in leads if l.get("email_subject"))

    update_run_status(run_id, "done", {
        "total_leads": len(leads),
        "hot": hot, "warm": warm, "cold": cold,
        "with_outreach": with_outreach,
    })

    console.print(Panel(
        f"[bold green]Demo complete![/]\n\n"
        f"Leads processed:  [bold]{len(leads)}[/]\n"
        f"[red]Hot leads:[/]        [bold]{hot}[/]\n"
        f"[yellow]Warm leads:[/]       [bold]{warm}[/]\n"
        f"[blue]Cold leads:[/]       [bold]{cold}[/]\n"
        f"Outreach emails:  [bold]{with_outreach}[/]\n\n"
        f"Exports:\n"
        f"  CSV:  {csv_path}\n"
        f"  JSON: {json_path}\n\n"
        f"Run ID: {run_id}",
        title="Summary",
        border_style="green",
    ))


if __name__ == "__main__":
    run_demo()
