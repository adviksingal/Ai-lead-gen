"""
Tests for src/export.py — CSV, JSON export correctness.
"""

import csv
import json
import uuid
from pathlib import Path
from datetime import datetime, timezone


def _sample_leads(n: int = 3) -> list[dict]:
    leads = []
    tiers = ["Hot", "Warm", "Cold"]
    for i in range(n):
        leads.append({
            "id": str(uuid.uuid4()),
            "run_id": str(uuid.uuid4()),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "name": f"Person {i}",
            "title": "VP Sales",
            "company": f"Company {i}",
            "website": f"https://company{i}.com",
            "email": f"person{i}@company{i}.com",
            "email_verified": 0,
            "email_source": "pattern_guess_unverified",
            "linkedin_url": f"https://linkedin.com/in/person-{i}",
            "location": "London, UK",
            "score": 80 - (i * 20),
            "tier": tiers[i % 3],
            "company_summary": f"Company {i} is a SaaS company.",
            "pain_points": ["Problem A", "Problem B"],
            "tech_signals": ["Salesforce"],
            "score_reasoning": "Good match.",
            "email_subject": f"Subject {i}",
            "email_body": f"Body {i}",
            "source": "google_linkedin",
            "enriched_at": datetime.now(timezone.utc).isoformat(),
            "scored_at": datetime.now(timezone.utc).isoformat(),
            "outreach_at": datetime.now(timezone.utc).isoformat(),
            "_raw_emails_from_site": ["info@company.com"],  # should be stripped
        })
    return leads


def test_csv_export_creates_file(tmp_path):
    from src.export import export_csv
    leads = _sample_leads(2)
    path = export_csv(leads, str(tmp_path / "test.csv"))
    assert Path(path).exists()


def test_csv_export_correct_row_count(tmp_path):
    from src.export import export_csv
    leads = _sample_leads(5)
    path = export_csv(leads, str(tmp_path / "test.csv"))
    with open(path) as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 5


def test_csv_export_strips_internal_fields(tmp_path):
    from src.export import export_csv
    leads = _sample_leads(1)
    path = export_csv(leads, str(tmp_path / "test.csv"))
    with open(path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            assert "_raw_emails_from_site" not in row


def test_csv_export_flattens_lists(tmp_path):
    from src.export import export_csv
    leads = _sample_leads(1)
    path = export_csv(leads, str(tmp_path / "test.csv"))
    with open(path) as f:
        row = next(csv.DictReader(f))
    # pain_points should be a semicolon-joined string
    assert ";" in row["pain_points"] or row["pain_points"].count("Problem") == 2


def test_csv_export_all_required_columns(tmp_path):
    from src.export import export_csv, CSV_COLUMNS
    leads = _sample_leads(1)
    path = export_csv(leads, str(tmp_path / "test.csv"))
    with open(path) as f:
        header = next(csv.reader(f))
    for col in ["name", "company", "score", "tier", "email"]:
        assert col in header


def test_json_export_creates_file(tmp_path):
    from src.export import export_json
    leads = _sample_leads(2)
    path = export_json(leads, str(tmp_path / "test.json"))
    assert Path(path).exists()


def test_json_export_valid_json(tmp_path):
    from src.export import export_json
    leads = _sample_leads(3)
    path = export_json(leads, str(tmp_path / "test.json"))
    with open(path) as f:
        data = json.load(f)
    assert isinstance(data, list)
    assert len(data) == 3


def test_json_export_strips_internal_fields(tmp_path):
    from src.export import export_json
    leads = _sample_leads(1)
    path = export_json(leads, str(tmp_path / "test.json"))
    with open(path) as f:
        data = json.load(f)
    assert "_raw_emails_from_site" not in data[0]


def test_json_export_preserves_lists(tmp_path):
    from src.export import export_json
    leads = _sample_leads(1)
    path = export_json(leads, str(tmp_path / "test.json"))
    with open(path) as f:
        data = json.load(f)
    assert isinstance(data[0]["pain_points"], list)


def test_export_leads_dispatcher_csv(tmp_path):
    from src.export import export_leads
    leads = _sample_leads(2)
    path = export_leads(leads, fmt="csv", output_path=str(tmp_path / "out.csv"))
    assert path.endswith(".csv")
    assert Path(path).exists()


def test_export_leads_dispatcher_json(tmp_path):
    from src.export import export_leads
    leads = _sample_leads(2)
    path = export_leads(leads, fmt="json", output_path=str(tmp_path / "out.json"))
    assert path.endswith(".json")


def test_export_leads_unknown_format():
    from src.export import export_leads
    import pytest
    with pytest.raises(ValueError, match="Unknown export format"):
        export_leads([], fmt="xml")


def test_csv_export_empty_leads(tmp_path):
    from src.export import export_csv
    path = export_csv([], str(tmp_path / "empty.csv"))
    with open(path) as f:
        rows = list(csv.DictReader(f))
    assert rows == []
