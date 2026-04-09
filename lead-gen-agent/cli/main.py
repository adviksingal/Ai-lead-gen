#!/usr/bin/env python3
"""
AI Lead Generation Agent — CLI
────────────────────────────────
Usage:
  python cli/main.py run     --industry "B2B SaaS" --titles "Head of Sales,VP Sales" --location UK --limit 30
  python cli/main.py export  --format csv
  python cli/main.py export  --run-id <id> --format json
  python cli/main.py serve   --port 3000
  python cli/main.py leads   --tier Hot
  python cli/main.py runs
"""

import logging
import os
import sys
from pathlib import Path

import click
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich import print as rprint

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).parent.parent))
load_dotenv()

console = Console()


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    # Quiet noisy libraries
    for noisy in ("httpx", "httpcore", "urllib3", "hpack"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


# ---------------------------------------------------------------------------
# CLI group
# ---------------------------------------------------------------------------

@click.group()
@click.option("--verbose", "-v", is_flag=True, help="Enable debug logging")
@click.pass_context
def cli(ctx: click.Context, verbose: bool) -> None:
    """AI Lead Generation Agent — find, enrich, score, and email B2B leads."""
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    _setup_logging(verbose)


# ---------------------------------------------------------------------------
# run command
# ---------------------------------------------------------------------------

@cli.command()
@click.option("--industry", "-i", required=True, help='Target industry, e.g. "B2B SaaS"')
@click.option("--titles", "-t", required=True,
              help='Comma-separated job titles, e.g. "Head of Sales,VP Sales"')
@click.option("--location", "-l", default="", help='Location filter, e.g. "UK" or "London"')
@click.option("--keywords", "-k", default="",
              help='Comma-separated keywords, e.g. "Series A,fintech"')
@click.option("--company-size", default=None, help='Company size hint, e.g. "50-200"')
@click.option("--limit", "-n", default=30, show_default=True, help="Max leads to find")
@click.option("--concurrency", "-c", default=3, show_default=True,
              help="Parallel enrichment workers")
@click.option("--sender-name", default="Alex", show_default=True)
@click.option("--sender-company", default="YourCo", show_default=True)
@click.option("--skip-outreach", is_flag=True, help="Skip email generation")
@click.option("--export-csv", is_flag=True, help="Auto-export to CSV when done")
@click.option("--export-json", is_flag=True, help="Auto-export to JSON when done")
@click.pass_context
def run(
    ctx: click.Context,
    industry: str,
    titles: str,
    location: str,
    keywords: str,
    company_size: str,
    limit: int,
    concurrency: int,
    sender_name: str,
    sender_company: str,
    skip_outreach: bool,
    export_csv: bool,
    export_json: bool,
) -> None:
    """Run a full lead generation pipeline."""
    from src.agent import RunConfig, run_lead_gen
    from src.export import export_leads

    if not os.getenv("ANTHROPIC_API_KEY"):
        console.print("[bold red]Error:[/] ANTHROPIC_API_KEY not set. "
                      "Copy .env.example to .env and add your key.")
        sys.exit(1)

    title_list = [t.strip() for t in titles.split(",") if t.strip()]
    keyword_list = [k.strip() for k in keywords.split(",") if k.strip()]

    config = RunConfig(
        industry=industry,
        titles=title_list,
        location=location,
        keywords=keyword_list,
        company_size=company_size or None,
        limit=limit,
        concurrency=concurrency,
        sender_name=sender_name,
        sender_company=sender_company,
        skip_outreach=skip_outreach,
    )

    console.print(Panel.fit(
        f"[bold cyan]AI Lead Generation Agent[/]\n"
        f"Industry: [yellow]{industry}[/] | Titles: [yellow]{', '.join(title_list)}[/]\n"
        f"Location: [yellow]{location or 'Any'}[/] | Limit: [yellow]{limit}[/]",
        border_style="cyan",
    ))

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("{task.completed}/{task.total}"),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task("Running lead gen pipeline...", total=limit)

        # Monkey-patch upsert_lead to update progress
        import src.database as db_mod
        original_upsert = db_mod.upsert_lead

        def _tracked_upsert(lead: dict) -> None:
            original_upsert(lead)
            progress.advance(task)

        db_mod.upsert_lead = _tracked_upsert

        try:
            run_id, results = run_lead_gen(config)
        finally:
            db_mod.upsert_lead = original_upsert

    _print_results_table(results, run_id)

    if export_csv:
        path = export_leads(results, fmt="csv")
        console.print(f"\n[green]Exported CSV:[/] {path}")
    if export_json:
        path = export_leads(results, fmt="json")
        console.print(f"[green]Exported JSON:[/] {path}")

    console.print(f"\n[dim]Run ID: {run_id}[/]")
    console.print("[dim]Use 'python cli/main.py export --run-id <id>' to export later.[/]")


def _print_results_table(results: list[dict], run_id: str) -> None:
    """Render a Rich table of lead results."""
    table = Table(
        title=f"Lead Results (run: {run_id[:8]}...)",
        show_header=True,
        header_style="bold magenta",
    )
    table.add_column("Name", style="cyan", width=18)
    table.add_column("Title", width=20)
    table.add_column("Company", width=18)
    table.add_column("Score", justify="center", width=7)
    table.add_column("Tier", width=7)
    table.add_column("Email", width=28)
    table.add_column("Has Outreach", justify="center", width=12)

    tier_colours = {"Hot": "red", "Warm": "yellow", "Cold": "blue"}

    for lead in results:
        tier = lead.get("tier") or "—"
        colour = tier_colours.get(tier, "white")
        table.add_row(
            lead.get("name") or "—",
            (lead.get("title") or "—")[:20],
            (lead.get("company") or "—")[:18],
            str(lead.get("score") or "—"),
            f"[{colour}]{tier}[/{colour}]",
            lead.get("email") or "—",
            "✓" if lead.get("email_subject") else "—",
        )

    console.print(table)

    hot = sum(1 for r in results if r.get("tier") == "Hot")
    warm = sum(1 for r in results if r.get("tier") == "Warm")
    cold = sum(1 for r in results if r.get("tier") == "Cold")
    emails_found = sum(1 for r in results if r.get("email"))
    console.print(
        f"\n[bold]Summary:[/] {len(results)} leads | "
        f"[red]Hot: {hot}[/] | [yellow]Warm: {warm}[/] | [blue]Cold: {cold}[/] | "
        f"[green]Emails found: {emails_found}[/]"
    )


# ---------------------------------------------------------------------------
# export command
# ---------------------------------------------------------------------------

@cli.command()
@click.option("--run-id", default=None, help="Export a specific run (default: all leads)")
@click.option("--format", "fmt", default="csv", type=click.Choice(["csv", "json", "sheets"]),
              show_default=True, help="Export format")
@click.option("--tier", default=None, type=click.Choice(["Hot", "Warm", "Cold"]),
              help="Filter by tier")
@click.option("--min-score", default=None, type=int, help="Minimum score filter")
@click.option("--output", "-o", default=None, help="Output file path")
@click.option("--sheets-name", default="AI Lead Gen Leads", help="Google Sheets spreadsheet name")
@click.pass_context
def export(
    ctx: click.Context,
    run_id: str,
    fmt: str,
    tier: str,
    min_score: int,
    output: str,
    sheets_name: str,
) -> None:
    """Export leads to CSV, JSON, or Google Sheets."""
    from src.database import init_db, get_leads_for_run, list_leads
    from src.export import export_leads

    init_db()

    if run_id:
        leads = get_leads_for_run(run_id)
    else:
        leads = list_leads(tier=tier, min_score=min_score, limit=10000)

    if not leads:
        console.print("[yellow]No leads found matching criteria.[/]")
        return

    console.print(f"Exporting [bold]{len(leads)}[/] leads as [bold]{fmt.upper()}[/]...")
    try:
        result = export_leads(leads, fmt=fmt, output_path=output,
                              spreadsheet_name=sheets_name)
        console.print(f"[green]Exported to:[/] {result}")
    except Exception as exc:
        console.print(f"[red]Export failed:[/] {exc}")
        sys.exit(1)


# ---------------------------------------------------------------------------
# leads command
# ---------------------------------------------------------------------------

@cli.command()
@click.option("--tier", default=None, type=click.Choice(["Hot", "Warm", "Cold"]))
@click.option("--min-score", default=None, type=int)
@click.option("--limit", default=50)
@click.pass_context
def leads(ctx: click.Context, tier: str, min_score: int, limit: int) -> None:
    """List leads from the database."""
    from src.database import init_db, list_leads

    init_db()
    results = list_leads(tier=tier, min_score=min_score, limit=limit)

    if not results:
        console.print("[yellow]No leads found.[/]")
        return

    _print_results_table(results, "all")


# ---------------------------------------------------------------------------
# runs command
# ---------------------------------------------------------------------------

@cli.command()
@click.option("--limit", default=10, show_default=True)
@click.pass_context
def runs(ctx: click.Context, limit: int) -> None:
    """List recent lead gen runs."""
    import json
    from src.database import init_db, list_runs

    init_db()
    run_list = list_runs(limit=limit)

    if not run_list:
        console.print("[yellow]No runs found.[/]")
        return

    table = Table(title="Recent Runs", header_style="bold magenta")
    table.add_column("Run ID", width=10)
    table.add_column("Created At", width=22)
    table.add_column("Status", width=10)
    table.add_column("Summary", width=50)

    status_colours = {"done": "green", "running": "yellow", "failed": "red"}

    for r in run_list:
        status = r.get("status", "?")
        colour = status_colours.get(status, "white")
        summary_raw = r.get("summary") or "{}"
        summary = json.loads(summary_raw) if isinstance(summary_raw, str) else summary_raw
        summary_str = (
            f"Leads: {summary.get('total_leads', '?')}, "
            f"Scored: {summary.get('scored', '?')}, "
            f"Hot: {summary.get('hot', '?')}"
        ) if summary else "—"
        table.add_row(
            r["id"][:8] + "...",
            r.get("created_at", "?")[:19],
            f"[{colour}]{status}[/{colour}]",
            summary_str,
        )

    console.print(table)


# ---------------------------------------------------------------------------
# serve command
# ---------------------------------------------------------------------------

@cli.command()
@click.option("--port", "-p", default=3000, show_default=True)
@click.option("--host", default="0.0.0.0", show_default=True)
@click.option("--reload", is_flag=True, help="Enable auto-reload (dev mode)")
@click.pass_context
def serve(ctx: click.Context, port: int, host: str, reload: bool) -> None:
    """Start the FastAPI REST server."""
    import uvicorn

    console.print(Panel.fit(
        f"[bold cyan]Lead Gen API[/]\n"
        f"[green]http://{host}:{port}[/]\n"
        f"Docs: [underline]http://localhost:{port}/docs[/]",
        border_style="cyan",
    ))

    uvicorn.run(
        "api.server:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info",
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    cli()
