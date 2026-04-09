"""
Export Module
─────────────
Exports lead data to:
  1. CSV  — standard spreadsheet format
  2. JSON — full structured data
  3. Google Sheets — via gspread (optional, requires service account JSON)

All exports are timestamped and saved to an ./exports directory by default.
"""

import csv
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

EXPORT_DIR = Path("exports")

# Columns in the CSV export (in order)
CSV_COLUMNS = [
    "id", "name", "title", "company", "website", "location",
    "email", "email_verified", "email_source",
    "linkedin_url",
    "score", "tier",
    "company_summary",
    "pain_points",
    "tech_signals",
    "score_reasoning",
    "email_subject",
    "email_body",
    "source",
    "enriched_at", "scored_at", "outreach_at", "created_at",
]


def _ensure_export_dir() -> Path:
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    return EXPORT_DIR


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def _flatten_lead(lead: dict) -> dict:
    """Flatten list fields to semicolon-separated strings for CSV."""
    flat = dict(lead)
    for f in ("pain_points", "tech_signals"):
        val = flat.get(f)
        if isinstance(val, list):
            flat[f] = "; ".join(val)
        elif val is None:
            flat[f] = ""
    # Remove internal fields
    flat.pop("_raw_emails_from_site", None)
    flat.pop("raw_data", None)
    return flat


# ---------------------------------------------------------------------------
# CSV export
# ---------------------------------------------------------------------------

def export_csv(leads: list[dict], output_path: Optional[str] = None) -> str:
    """
    Export leads to a CSV file.
    Returns the path of the written file.
    """
    _ensure_export_dir()
    path = output_path or str(EXPORT_DIR / f"leads_{_timestamp()}.csv")

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        for lead in leads:
            writer.writerow(_flatten_lead(lead))

    logger.info("Exported %d leads to CSV: %s", len(leads), path)
    return path


# ---------------------------------------------------------------------------
# JSON export
# ---------------------------------------------------------------------------

def export_json(leads: list[dict], output_path: Optional[str] = None) -> str:
    """
    Export leads to a pretty-printed JSON file.
    Returns the path of the written file.
    """
    _ensure_export_dir()
    path = output_path or str(EXPORT_DIR / f"leads_{_timestamp()}.json")

    clean_leads = []
    for lead in leads:
        clean = dict(lead)
        clean.pop("_raw_emails_from_site", None)
        clean_leads.append(clean)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(clean_leads, f, indent=2, ensure_ascii=False, default=str)

    logger.info("Exported %d leads to JSON: %s", len(leads), path)
    return path


# ---------------------------------------------------------------------------
# Google Sheets export
# ---------------------------------------------------------------------------

def export_google_sheets(
    leads: list[dict],
    spreadsheet_name: str = "AI Lead Gen Leads",
    worksheet_name: Optional[str] = None,
    key_file: Optional[str] = None,
) -> str:
    """
    Export leads to a Google Sheet.

    Prerequisites:
      1. Enable Google Sheets API + Google Drive API in Google Cloud Console
      2. Create a Service Account and download the JSON key
      3. Share the target spreadsheet with the service account email
      4. Set GOOGLE_SHEETS_KEY_FILE env var (or pass key_file param)

    Returns the spreadsheet URL.
    """
    try:
        import gspread
        from google.oauth2.service_account import Credentials
    except ImportError:
        raise ImportError(
            "gspread and google-auth are required for Sheets export. "
            "Install with: pip install gspread google-auth"
        )

    key_file = key_file or os.getenv("GOOGLE_SHEETS_KEY_FILE")
    if not key_file:
        raise ValueError(
            "Google Sheets key file not specified. "
            "Set GOOGLE_SHEETS_KEY_FILE env var or pass key_file parameter."
        )

    scopes = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = Credentials.from_service_account_file(key_file, scopes=scopes)
    gc = gspread.authorize(creds)

    # Open or create spreadsheet
    try:
        sh = gc.open(spreadsheet_name)
        logger.info("Opened existing spreadsheet: %s", spreadsheet_name)
    except gspread.SpreadsheetNotFound:
        sh = gc.create(spreadsheet_name)
        logger.info("Created new spreadsheet: %s", spreadsheet_name)

    ws_title = worksheet_name or f"Run {_timestamp()}"
    try:
        ws = sh.worksheet(ws_title)
        ws.clear()
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title=ws_title, rows=len(leads) + 10, cols=len(CSV_COLUMNS))

    # Write header
    ws.append_row(CSV_COLUMNS)

    # Write data rows in batches of 50 to avoid rate limits
    rows = [
        [str(_flatten_lead(lead).get(col, "") or "") for col in CSV_COLUMNS]
        for lead in leads
    ]
    batch_size = 50
    for i in range(0, len(rows), batch_size):
        ws.append_rows(rows[i:i + batch_size])

    url = f"https://docs.google.com/spreadsheets/d/{sh.id}"
    logger.info("Exported %d leads to Google Sheets: %s", len(leads), url)
    return url


# ---------------------------------------------------------------------------
# Unified export entrypoint
# ---------------------------------------------------------------------------

def export_leads(
    leads: list[dict],
    fmt: str = "csv",
    output_path: Optional[str] = None,
    **kwargs,
) -> str:
    """
    Export leads in the specified format.

    Args:
        leads: List of lead dicts
        fmt: "csv", "json", or "sheets"
        output_path: Optional file path (csv/json only)
        **kwargs: Extra args passed to the specific exporter

    Returns:
        Path or URL of exported file/sheet.
    """
    fmt = fmt.lower().strip()
    if fmt == "csv":
        return export_csv(leads, output_path)
    elif fmt == "json":
        return export_json(leads, output_path)
    elif fmt in ("sheets", "google_sheets"):
        return export_google_sheets(leads, **kwargs)
    else:
        raise ValueError(f"Unknown export format: {fmt!r}. Use 'csv', 'json', or 'sheets'.")
