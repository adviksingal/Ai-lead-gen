"""
Tests for src/outreach.py — quality gate, email generation, cold lead skip.
"""

import json
import uuid
import pytest
from datetime import datetime, timezone


def _make_lead(**kwargs) -> dict:
    base = {
        "id": str(uuid.uuid4()),
        "run_id": str(uuid.uuid4()),
        "name": "Sarah Chen",
        "title": "VP of Sales",
        "company": "Growthly",
        "website": "https://growthly.io",
        "company_summary": "Growthly automates pipeline management for B2B revenue teams.",
        "pain_points": ["Manual CRM data entry consuming rep time", "Low forecast accuracy"],
        "tech_signals": ["Salesforce integration", "Hiring Sales Engineers"],
        "score": 82,
        "tier": "Hot",
        "score_reasoning": "Strong ICP match.",
    }
    base.update(kwargs)
    return base


# ── Quality gate ──────────────────────────────────────────────────────────────

class TestQualityGate:
    def test_passes_with_company_name(self):
        from src.outreach import _contains_company_detail
        lead = _make_lead()
        body = "Hi Sarah, I noticed Growthly recently scaled its pipeline product..."
        assert _contains_company_detail(body, lead) is True

    def test_passes_with_pain_point_phrase(self):
        from src.outreach import _contains_company_detail
        lead = _make_lead()
        body = "Hi Sarah, given the manual CRM data entry challenges your reps face..."
        assert _contains_company_detail(body, lead) is True

    def test_passes_with_tech_signal(self):
        from src.outreach import _contains_company_detail
        lead = _make_lead()
        body = "Hi Sarah, I saw you're hiring Sales Engineers — a strong signal of..."
        assert _contains_company_detail(body, lead) is True

    def test_passes_with_summary_keywords(self):
        from src.outreach import _contains_company_detail
        lead = _make_lead()
        # Use multiple keywords from company_summary
        body = "Your pipeline management approach for revenue teams is interesting..."
        assert _contains_company_detail(body, lead) is True

    def test_fails_generic_body(self):
        from src.outreach import _contains_company_detail
        lead = _make_lead()
        body = "Hi there, I think your business could really benefit from our solution..."
        assert _contains_company_detail(body, lead) is False

    def test_fails_short_company_name(self):
        from src.outreach import _contains_company_detail
        lead = _make_lead(company="IBM")  # len <= 3, skipped
        body = "Hi there, I believe we could help your business grow significantly."
        assert _contains_company_detail(body, lead) is False

    def test_case_insensitive_company_match(self):
        from src.outreach import _contains_company_detail
        lead = _make_lead(company="Growthly")
        body = "Hi Sarah, I've been following growthly's work for a while..."
        assert _contains_company_detail(body, lead) is True


# ── Cold lead skip ────────────────────────────────────────────────────────────

def test_cold_lead_skipped(mocker):
    from src.outreach import generate_outreach_email
    lead = _make_lead(tier="Cold", score=25)
    result = generate_outreach_email(lead)
    # Should return unchanged — no email_subject set
    assert result.get("email_subject") is None


# ── Email generation (mocked API) ─────────────────────────────────────────────

def test_generate_email_success(mocker):
    from src.outreach import generate_outreach_email

    mock_response = mocker.MagicMock()
    mock_response.content = [mocker.MagicMock(text=json.dumps({
        "subject": "Quick question about Growthly's sales motion",
        "body": (
            "Hi Sarah,\n\n"
            "I noticed Growthly recently expanded its pipeline automation features — "
            "interesting timing given the manual CRM pain teams typically face.\n\n"
            "At SalesForge, we help Series B revenue teams build outbound playbooks.\n\n"
            "Worth a 15-min call?\n\nBest, Alex"
        ),
    }))]
    mock_client = mocker.MagicMock()
    mock_client.messages.create.return_value = mock_response
    mocker.patch("anthropic.Anthropic", return_value=mock_client)

    lead = _make_lead()
    result = generate_outreach_email(lead, sender_name="Alex", sender_company="SalesForge")

    assert result["email_subject"] == "Quick question about Growthly's sales motion"
    assert "Growthly" in result["email_body"]
    assert result.get("outreach_at") is not None


def test_generate_email_retries_on_generic(mocker):
    """If first attempt produces a generic email, it should retry."""
    from src.outreach import generate_outreach_email

    generic_body = "Hi there, I think your business would benefit from our platform."
    specific_body = "Hi Sarah, Growthly's pipeline automation is impressive — loved the blog post."

    call_count = {"n": 0}

    def side_effect(*args, **kwargs):
        call_count["n"] += 1
        text = generic_body if call_count["n"] == 1 else specific_body
        mock_response = mocker.MagicMock()
        mock_response.content = [mocker.MagicMock(text=json.dumps({
            "subject": "Test subject",
            "body": text,
        }))]
        return mock_response

    mock_client = mocker.MagicMock()
    mock_client.messages.create.side_effect = side_effect
    mocker.patch("anthropic.Anthropic", return_value=mock_client)

    lead = _make_lead()
    result = generate_outreach_email(lead)
    assert "Growthly" in result["email_body"]
    assert call_count["n"] >= 2  # retried at least once


def test_generate_email_fallback_on_all_retries_fail(mocker):
    """After all retries fail quality check, stores fallback email."""
    from src.outreach import generate_outreach_email

    mock_response = mocker.MagicMock()
    mock_response.content = [mocker.MagicMock(text=json.dumps({
        "subject": "Hello",
        "body": "Generic email with no company detail whatsoever.",
    }))]
    mock_client = mocker.MagicMock()
    mock_client.messages.create.return_value = mock_response
    mocker.patch("anthropic.Anthropic", return_value=mock_client)

    lead = _make_lead()
    result = generate_outreach_email(lead)
    # Should still have a subject/body (fallback)
    assert result.get("email_subject") is not None
    assert result.get("email_body") is not None


# ── Scoring ───────────────────────────────────────────────────────────────────

def test_score_lead_success(mocker):
    from src.scoring import score_lead

    mock_response = mocker.MagicMock()
    mock_response.content = [mocker.MagicMock(text=json.dumps({
        "score": 78,
        "tier": "Hot",
        "reasoning": "Strong ICP match, verified email, relevant pain points.",
    }))]
    mock_client = mocker.MagicMock()
    mock_client.messages.create.return_value = mock_response
    mocker.patch("anthropic.Anthropic", return_value=mock_client)

    lead = _make_lead(score=None, tier=None)
    result = score_lead(lead)
    assert result["score"] == 78
    assert result["tier"] == "Hot"
    assert result["score_reasoning"] != ""


def test_score_lead_clamps_to_range(mocker):
    from src.scoring import score_lead

    for raw_score, expected_clamped in [(150, 100), (-5, 1), (0, 1)]:
        mock_response = mocker.MagicMock()
        mock_response.content = [mocker.MagicMock(text=json.dumps({
            "score": raw_score,
            "tier": "Hot",
            "reasoning": "test",
        }))]
        mock_client = mocker.MagicMock()
        mock_client.messages.create.return_value = mock_response
        mocker.patch("anthropic.Anthropic", return_value=mock_client)

        result = score_lead(_make_lead(score=None, tier=None))
        assert 1 <= result["score"] <= 100


def test_tier_thresholds():
    from src.scoring import _tier_from_score
    assert _tier_from_score(70) == "Hot"
    assert _tier_from_score(100) == "Hot"
    assert _tier_from_score(69) == "Warm"
    assert _tier_from_score(40) == "Warm"
    assert _tier_from_score(39) == "Cold"
    assert _tier_from_score(1) == "Cold"


def test_score_lead_json_error_uses_default(mocker):
    """Malformed Claude response → fallback score=50, tier=Warm."""
    from src.scoring import score_lead

    mock_response = mocker.MagicMock()
    mock_response.content = [mocker.MagicMock(text="not valid json {{")]
    mock_client = mocker.MagicMock()
    mock_client.messages.create.return_value = mock_response
    mocker.patch("anthropic.Anthropic", return_value=mock_client)

    result = score_lead(_make_lead(score=None, tier=None))
    assert result["score"] == 50
    assert result["tier"] == "Warm"
