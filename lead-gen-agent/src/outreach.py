"""
Outreach Email Generation Module
──────────────────────────────────
Generates personalised cold emails for Hot and Warm leads using Claude.

Quality gate: Every generated email MUST contain at least one
company-specific sentence derived from enrichment data. If it doesn't,
the module regenerates (up to MAX_RETRIES times) with a stricter prompt.

Email format:
  Subject line (punchy, < 60 chars)
  Para 1 — Hook (reference company-specific detail)
  Para 2 — Value proposition
  Para 3 — CTA (simple, low commitment)
"""

import json
import logging
import os
import re
from typing import Optional

import anthropic

logger = logging.getLogger(__name__)

MAX_RETRIES = 2
MIN_COMPANY_DETAIL_SIGNALS = 1  # at least 1 company-specific phrase must appear


def _get_client() -> anthropic.Anthropic:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable not set")
    return anthropic.Anthropic(api_key=api_key)


# ---------------------------------------------------------------------------
# Quality gate
# ---------------------------------------------------------------------------

def _contains_company_detail(email_body: str, lead: dict) -> bool:
    """
    Check that the email references at least one company-specific detail.
    Looks for: company name, pain points phrases, tech signals, or summary keywords.
    """
    body_lower = email_body.lower()

    # Company name mention (excluding generic words)
    company = lead.get("company", "")
    if company and len(company) > 3 and company.lower() in body_lower:
        return True

    # Pain point phrases
    for pain in lead.get("pain_points", []):
        if len(pain) > 10:
            key_phrase = pain.lower().split()[:3]
            if all(w in body_lower for w in key_phrase):
                return True

    # Tech signals
    for signal in lead.get("tech_signals", []):
        if len(signal) > 5 and signal.lower()[:8] in body_lower:
            return True

    # Company summary keywords (first few meaningful words)
    summary = lead.get("company_summary", "")
    if summary:
        words = [w for w in summary.lower().split() if len(w) > 5][:5]
        matching = sum(1 for w in words if w in body_lower)
        if matching >= 2:
            return True

    return False


# ---------------------------------------------------------------------------
# Email generation
# ---------------------------------------------------------------------------

def generate_outreach_email(lead: dict, sender_name: str = "Alex", sender_company: str = "YourCo") -> dict:
    """
    Generate a personalised cold email for a lead.

    Returns the lead dict with email_subject and email_body populated.
    Skips Cold leads (tier = 'Cold').
    """
    from datetime import datetime, timezone

    tier = lead.get("tier", "Cold")
    if tier == "Cold":
        logger.debug("Skipping outreach for Cold lead: %s", lead.get("name"))
        return lead

    model = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514")
    client = _get_client()

    for attempt in range(1, MAX_RETRIES + 2):  # +2 so we try MAX_RETRIES+1 times total
        strict = attempt > 1
        prompt = _build_email_prompt(lead, sender_name, sender_company, strict=strict)

        try:
            response = client.messages.create(
                model=model,
                max_tokens=800,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = response.content[0].text.strip()
            raw = re.sub(r"^```(?:json)?\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw)

            data = json.loads(raw)
            subject = data.get("subject", "").strip()
            body = data.get("body", "").strip()

            if not subject or not body:
                logger.warning("Empty email generated for %s (attempt %d)", lead.get("name"), attempt)
                continue

            # Quality gate
            if _contains_company_detail(body, lead):
                lead["email_subject"] = subject
                lead["email_body"] = body
                lead["outreach_at"] = datetime.now(timezone.utc).isoformat()
                logger.info(
                    "Generated outreach email for %s @ %s (attempt %d, tier=%s)",
                    lead.get("name"), lead.get("company"), attempt, tier
                )
                return lead
            else:
                logger.warning(
                    "Email for %s lacks company-specific detail (attempt %d/%d) — regenerating",
                    lead.get("name"), attempt, MAX_RETRIES + 1
                )

        except (json.JSONDecodeError, KeyError) as exc:
            logger.error("Email parse error for %s (attempt %d): %s", lead.get("name"), attempt, exc)
        except anthropic.APIError as exc:
            logger.error("Claude API error for %s: %s", lead.get("name"), exc)
            break

    # Last resort: store what we have even without company detail
    logger.warning("Max retries hit for %s — storing last generated email", lead.get("name"))
    lead.setdefault("email_subject", f"Quick question for {lead.get('company', 'your team')}")
    lead.setdefault("email_body", f"Hi {lead.get('name', 'there')},\n\n[Email generation failed quality check — review manually]\n")
    lead["outreach_at"] = datetime.now(timezone.utc).isoformat()
    return lead


def _build_email_prompt(
    lead: dict,
    sender_name: str,
    sender_company: str,
    strict: bool = False,
) -> str:
    name = lead.get("name") or "there"
    first_name = name.split()[0] if name != "there" else "there"
    title = lead.get("title") or "leader"
    company = lead.get("company") or "your company"
    company_summary = lead.get("company_summary") or "a growing company"
    pain_points = lead.get("pain_points") or []
    tech_signals = lead.get("tech_signals") or []
    tier = lead.get("tier", "Warm")
    score_reasoning = lead.get("score_reasoning") or ""

    pain_str = "\n".join(f"  - {p}" for p in pain_points[:3]) if pain_points else "  - None specified"
    tech_str = "\n".join(f"  - {t}" for t in tech_signals[:3]) if tech_signals else "  - None specified"

    strict_instruction = """
CRITICAL REQUIREMENT: The email body MUST contain at least one sentence that references
a specific, concrete detail about this company — not generic phrases like "your team" or
"your business". Reference the company summary, a pain point, or a tech signal directly.
For example: "I noticed {company} is focused on [specific thing from summary]..." or
"Given that you're dealing with [specific pain point]..."
""" if strict else ""

    return f"""You are a world-class B2B cold email copywriter. Write a short, highly personalised cold email.

RECIPIENT:
- Name: {name}
- First name: {first_name}
- Title: {title}
- Company: {company}
- Tier: {tier}
- Score reasoning: {score_reasoning}

COMPANY CONTEXT:
{company_summary}

Pain points:
{pain_str}

Tech signals:
{tech_str}

SENDER:
- Name: {sender_name}
- Company: {sender_company}

REQUIREMENTS:
- Subject line: punchy, under 60 characters, do NOT use clickbait or ALL CAPS
- Paragraph 1 (hook): Open with a specific observation about {company} — reference their product, mission, or a pain point. 2-3 sentences.
- Paragraph 2 (value): Explain what {sender_company} does and why it's relevant to them. 2-3 sentences.
- Paragraph 3 (CTA): One low-commitment ask (e.g., "Worth a 15-min call?"). 1-2 sentences.
- Total email: under 150 words
- Tone: Direct, human, not salesy. No buzzwords.
- Do NOT use "I hope this email finds you well" or similar openers.
{strict_instruction}

Respond with ONLY a valid JSON object (no markdown, no explanation):
{{
  "subject": "<subject line>",
  "body": "<full email body with paragraph breaks using \\n\\n>"
}}"""
