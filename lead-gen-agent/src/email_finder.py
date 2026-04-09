"""
Email Finder Module
────────────────────
Two-stage approach:
  1. Try to find emails on the company website (scraped during enrichment)
  2. Generate pattern guesses and verify each with a free SMTP handshake

SMTP verification: opens a connection to the mail server, sends RCPT TO,
and reads the response — no actual email is delivered.

Pattern priority:
  first@domain > firstname.lastname@domain > f.lastname@domain >
  firstname@domain > flastname@domain > firstname.l@domain
"""

import logging
import re
import smtplib
import socket
import time
import random
from dataclasses import dataclass
from typing import Optional
import dns.resolver  # dnspython

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pattern generation
# ---------------------------------------------------------------------------

@dataclass
class EmailCandidate:
    email: str
    pattern: str
    verified: bool = False
    verification_method: str = ""


def _clean_name_part(part: str) -> str:
    """Lowercase, remove accents (basic), strip non-alpha."""
    replacements = {
        "à": "a", "á": "a", "â": "a", "ä": "a",
        "è": "e", "é": "e", "ê": "e", "ë": "e",
        "ì": "i", "í": "i", "î": "i", "ï": "i",
        "ò": "o", "ó": "o", "ô": "o", "ö": "o",
        "ù": "u", "ú": "u", "û": "u", "ü": "u",
        "ñ": "n", "ç": "c",
    }
    result = part.lower()
    for char, replacement in replacements.items():
        result = result.replace(char, replacement)
    return re.sub(r"[^a-z]", "", result)


def generate_email_patterns(name: str, domain: str) -> list[EmailCandidate]:
    """
    Generate likely email addresses for a person at a domain.
    Returns candidates ordered by frequency in the wild.
    """
    if not name or not domain:
        return []

    parts = name.strip().split()
    if len(parts) < 1:
        return []

    first = _clean_name_part(parts[0])
    last = _clean_name_part(parts[-1]) if len(parts) > 1 else ""
    f = first[0] if first else ""
    l = last[0] if last else ""  # noqa: E741

    candidates = []

    def add(pattern: str, email_str: str) -> None:
        if email_str and "@" in email_str and len(email_str) > 5:
            candidates.append(EmailCandidate(email=email_str, pattern=pattern))

    if first and last:
        add("firstname.lastname", f"{first}.{last}@{domain}")
        add("f.lastname",         f"{f}.{last}@{domain}")
        add("firstnamelastname",  f"{first}{last}@{domain}")
        add("flastname",          f"{f}{last}@{domain}")
        add("firstname.l",        f"{first}.{l}@{domain}")
        add("lastname.firstname", f"{last}.{first}@{domain}")

    if first:
        add("firstname",          f"{first}@{domain}")

    return candidates


# ---------------------------------------------------------------------------
# Domain MX lookup
# ---------------------------------------------------------------------------

def _get_mx_host(domain: str) -> Optional[str]:
    """Look up the highest-priority MX record for a domain."""
    try:
        answers = dns.resolver.resolve(domain, "MX", lifetime=5)
        mx_records = sorted(answers, key=lambda r: r.preference)
        return str(mx_records[0].exchange).rstrip(".")
    except Exception as exc:
        logger.debug("MX lookup failed for %s: %s", domain, exc)
        return None


# ---------------------------------------------------------------------------
# SMTP verification
# ---------------------------------------------------------------------------

SMTP_TIMEOUT = 10
VERIFICATION_FROM = "verify@lead-gen-agent.local"

# Responses that definitively tell us the address is invalid
HARD_REJECT_CODES = {550, 551, 552, 553, 554, 450, 421}


def verify_email_smtp(email: str) -> tuple[bool, str]:
    """
    Verify an email address exists via SMTP handshake.
    Returns (is_valid: bool, method_description: str).

    No email is actually sent — we just do:
      EHLO → MAIL FROM → RCPT TO → RSET → QUIT
    """
    domain = email.split("@")[-1]
    mx_host = _get_mx_host(domain)
    if not mx_host:
        return False, "mx_lookup_failed"

    try:
        with smtplib.SMTP(mx_host, port=25, timeout=SMTP_TIMEOUT) as smtp:
            smtp.ehlo("verify.local")
            code, msg = smtp.mail(VERIFICATION_FROM)
            if code not in (250, 200):
                return False, f"mail_from_rejected_{code}"

            code, msg = smtp.rcpt(email)
            smtp.rset()

            if code in (250, 200, 251):
                logger.debug("SMTP verified: %s (code=%d)", email, code)
                return True, "smtp_250"
            elif code in HARD_REJECT_CODES:
                logger.debug("SMTP rejected: %s (code=%d)", email, code)
                return False, f"smtp_{code}"
            else:
                # Ambiguous (e.g. greylisting) — assume unverified but not invalid
                logger.debug("SMTP ambiguous for %s (code=%d)", email, code)
                return False, f"smtp_ambiguous_{code}"

    except smtplib.SMTPConnectError:
        return False, "smtp_connect_failed"
    except smtplib.SMTPServerDisconnected:
        return False, "smtp_disconnected"
    except socket.timeout:
        return False, "smtp_timeout"
    except OSError as exc:
        logger.debug("SMTP OS error for %s: %s", email, exc)
        return False, "smtp_os_error"


# ---------------------------------------------------------------------------
# Main email finder
# ---------------------------------------------------------------------------

def find_email(lead: dict, delay_range: tuple[float, float] = (1.0, 3.0)) -> dict:
    """
    Find and verify an email for a lead.

    Steps:
      1. Check emails scraped from the company website (already stored in lead)
      2. Generate patterns + SMTP verify each candidate

    Updates lead with: email, email_verified, email_source
    Returns the updated lead dict.
    """
    # ---- Step 1: Emails found on the website ----
    site_emails = lead.get("_raw_emails_from_site", [])
    domain = _extract_domain(lead.get("website", ""))

    # Filter to company domain only (skip info@, noreply@, etc.)
    filtered_site_emails = [
        e for e in site_emails
        if domain and e.endswith(f"@{domain}")
        and not any(x in e.split("@")[0] for x in ["noreply", "no-reply", "support", "info", "hello", "contact"])
    ]

    if filtered_site_emails:
        # Prefer emails containing part of a known name
        name = lead.get("name", "")
        best = _pick_personal_email(filtered_site_emails, name)
        lead["email"] = best
        lead["email_source"] = "scraped_website"
        # Try to SMTP verify scraped emails too
        verified, method = verify_email_smtp(best)
        lead["email_verified"] = int(verified)
        logger.info("Found email on website: %s (verified=%s)", best, verified)
        return lead

    # ---- Step 2: Pattern guessing + SMTP verification ----
    name = lead.get("name", "")
    if not name or not domain:
        logger.info("Cannot guess email — missing name or domain for %s", lead.get("company"))
        return lead

    candidates = generate_email_patterns(name, domain)
    logger.info("Testing %d email patterns for %s @ %s", len(candidates), name, domain)

    for candidate in candidates:
        time.sleep(random.uniform(*delay_range))
        verified, method = verify_email_smtp(candidate.email)
        candidate.verified = verified
        candidate.verification_method = method

        if verified:
            lead["email"] = candidate.email
            lead["email_verified"] = 1
            lead["email_source"] = f"pattern:{candidate.pattern},smtp:{method}"
            logger.info("Email verified: %s (pattern=%s)", candidate.email, candidate.pattern)
            return lead

    # No verified email found — store best guess (first pattern) unverified
    if candidates:
        best_guess = candidates[0].email
        lead["email"] = best_guess
        lead["email_verified"] = 0
        lead["email_source"] = "pattern_guess_unverified"
        logger.info("Stored unverified email guess: %s", best_guess)

    return lead


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_domain(website: str) -> Optional[str]:
    if not website:
        return None
    from urllib.parse import urlparse
    parsed = urlparse(website if "://" in website else "https://" + website)
    return parsed.netloc.replace("www.", "") or None


def _pick_personal_email(emails: list[str], name: str) -> str:
    """From a list of emails, prefer one that looks personal (contains name parts)."""
    if not name:
        return emails[0]
    parts = [p.lower() for p in name.split() if len(p) > 1]
    for email in emails:
        local = email.split("@")[0].lower()
        if any(p in local for p in parts):
            return email
    return emails[0]
