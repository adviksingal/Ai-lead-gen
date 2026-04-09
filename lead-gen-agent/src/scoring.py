"""
Lead Scoring Module
────────────────────
Uses Claude to score each lead 1-100 and classify as Hot / Warm / Cold.
Claude receives the full lead profile + enrichment data and returns:
  - score (int 1-100)
  - tier ("Hot" | "Warm" | "Cold")
  - reasoning (2-3 sentence explanation)

Tier thresholds:
  Hot  ≥ 70
  Warm 40-69
  Cold < 40
"""

import json
import logging
import os
import re
from typing import Optional

import anthropic

logger = logging.getLogger(__name__)

HOT_THRESHOLD = 70
WARM_THRESHOLD = 40


def _get_client() -> anthropic.Anthropic:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable not set")
    return anthropic.Anthropic(api_key=api_key)


def _tier_from_score(score: int) -> str:
    if score >= HOT_THRESHOLD:
        return "Hot"
    elif score >= WARM_THRESHOLD:
        return "Warm"
    return "Cold"


def score_lead(lead: dict, run_config: Optional[dict] = None) -> dict:
    """
    Score a single lead using Claude.

    Args:
        lead: Enriched lead dict
        run_config: Original run config (industry, titles, etc.) for context

    Returns:
        Lead dict with score, tier, score_reasoning, scored_at populated.
    """
    from datetime import datetime, timezone

    model = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514")

    # Build the scoring prompt
    prompt = _build_scoring_prompt(lead, run_config or {})

    client = _get_client()
    try:
        response = client.messages.create(
            model=model,
            max_tokens=400,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip()
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)

        data = json.loads(raw)
        score = int(data.get("score", 50))
        score = max(1, min(100, score))  # clamp 1-100
        tier = data.get("tier", _tier_from_score(score))
        # Validate tier value
        if tier not in ("Hot", "Warm", "Cold"):
            tier = _tier_from_score(score)
        reasoning = data.get("reasoning", "")

        lead["score"] = score
        lead["tier"] = tier
        lead["score_reasoning"] = reasoning
        lead["scored_at"] = datetime.now(timezone.utc).isoformat()

        logger.info(
            "Scored %s @ %s → %d (%s): %s",
            lead.get("name"), lead.get("company"), score, tier, reasoning[:80]
        )

    except (json.JSONDecodeError, KeyError, ValueError) as exc:
        logger.error("Score parsing failed for %s: %s", lead.get("company"), exc)
        # Assign a default mid-score rather than failing the whole pipeline
        lead["score"] = 50
        lead["tier"] = "Warm"
        lead["score_reasoning"] = "Scoring failed — default assigned."
        lead["scored_at"] = datetime.now(timezone.utc).isoformat()
    except anthropic.APIError as exc:
        logger.error("Claude API error scoring %s: %s", lead.get("company"), exc)
        lead["score"] = 50
        lead["tier"] = "Warm"
        lead["score_reasoning"] = "API error — default assigned."
        lead["scored_at"] = datetime.now(timezone.utc).isoformat()

    return lead


def _build_scoring_prompt(lead: dict, run_config: dict) -> str:
    """Build the Claude scoring prompt from lead data."""

    # Summarise lead data
    name = lead.get("name") or "Unknown"
    title = lead.get("title") or "Unknown"
    company = lead.get("company") or "Unknown"
    location = lead.get("location") or "Unknown"
    website = lead.get("website") or "Unknown"
    company_summary = lead.get("company_summary") or "No summary available"
    pain_points = lead.get("pain_points") or []
    tech_signals = lead.get("tech_signals") or []
    has_email = bool(lead.get("email"))
    email_verified = bool(lead.get("email_verified"))
    has_linkedin = bool(lead.get("linkedin_url"))

    # Summarise run config
    target_industry = run_config.get("industry", "")
    target_titles = run_config.get("titles", [])
    target_location = run_config.get("location", "")
    target_keywords = run_config.get("keywords", [])

    pain_points_str = "\n".join(f"  - {p}" for p in pain_points) if pain_points else "  - None identified"
    tech_signals_str = "\n".join(f"  - {t}" for t in tech_signals) if tech_signals else "  - None identified"
    target_titles_str = ", ".join(target_titles) if target_titles else "any"

    return f"""You are a B2B sales qualification expert. Score this lead for sales outreach potential.

TARGET PROFILE (ideal customer):
- Industry: {target_industry or "any"}
- Job titles: {target_titles_str}
- Location: {target_location or "any"}
- Keywords: {", ".join(target_keywords) if target_keywords else "any"}

LEAD PROFILE:
- Name: {name}
- Title: {title}
- Company: {company}
- Location: {location}
- Website: {website}
- Has verified email: {email_verified}
- Has LinkedIn profile: {has_linkedin}

COMPANY ENRICHMENT:
{company_summary}

Pain points identified:
{pain_points_str}

Tech signals:
{tech_signals_str}

SCORING CRITERIA:
- Title match (does it match target titles?): worth 30 points
- Company fit (relevant industry, size signals, pain points): worth 30 points
- Contact quality (verified email + LinkedIn): worth 20 points
- Location match: worth 10 points
- Enrichment depth (strong signals, clear pain points): worth 10 points

Respond with ONLY a valid JSON object (no markdown, no explanation):
{{
  "score": <integer 1-100>,
  "tier": "<Hot|Warm|Cold>",
  "reasoning": "<2-3 sentences explaining the score>"
}}

Hot = 70-100 (strong fit, ready to reach out)
Warm = 40-69 (moderate fit, worth nurturing)
Cold = 1-39 (poor fit or insufficient data)"""
