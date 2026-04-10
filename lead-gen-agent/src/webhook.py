"""
Webhook Notifier
─────────────────
Sends HTTP POST notifications when a lead gen run completes (or fails).

Payload shape:
    {
      "event":      "run.completed" | "run.failed",
      "run_id":     "...",
      "timestamp":  "2025-01-01T12:00:00Z",
      "summary":    { ...run summary dict... }
    }

Security:
    If WEBHOOK_SECRET env var is set, each request includes a
    X-Lead-Gen-Signature header with an HMAC-SHA256 signature of the
    JSON body, prefixed "sha256=".  Verify it on the receiving end:

        import hmac, hashlib
        sig = request.headers["X-Lead-Gen-Signature"].removeprefix("sha256=")
        expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        assert hmac.compare_digest(sig, expected)
"""

import hashlib
import hmac
import json
import logging
import os
import time
import random
from datetime import datetime, timezone
from typing import Optional

import requests

logger = logging.getLogger(__name__)

_WEBHOOK_TIMEOUT = 10
_MAX_RETRIES = 3


def _sign_payload(body: str) -> Optional[str]:
    """Return HMAC-SHA256 signature string, or None if no secret configured."""
    secret = os.getenv("WEBHOOK_SECRET", "").strip()
    if not secret:
        return None
    sig = hmac.new(
        secret.encode("utf-8"),
        body.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"sha256={sig}"


def send_webhook(url: str, event: str, payload: dict) -> bool:
    """
    POST a signed webhook to `url`.

    Args:
        url:     Target URL to POST to
        event:   Event name, e.g. "run.completed"
        payload: Arbitrary dict merged into the body

    Returns:
        True if delivered successfully, False otherwise.
    """
    if not url:
        return False

    body_dict = {
        "event": event,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **payload,
    }
    body_str = json.dumps(body_dict, ensure_ascii=False, default=str)

    headers = {
        "Content-Type": "application/json",
        "User-Agent": "LeadGenAgent/1.0",
        "X-Lead-Gen-Event": event,
    }

    sig = _sign_payload(body_str)
    if sig:
        headers["X-Lead-Gen-Signature"] = sig

    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            resp = requests.post(
                url,
                data=body_str,
                headers=headers,
                timeout=_WEBHOOK_TIMEOUT,
            )
            resp.raise_for_status()
            logger.info("Webhook delivered [event=%s, url=%s, status=%d]",
                        event, url, resp.status_code)
            return True
        except requests.RequestException as exc:
            wait = (2 ** attempt) + random.uniform(0, 1)
            if attempt < _MAX_RETRIES:
                logger.warning("Webhook attempt %d/%d failed: %s — retrying in %.1fs",
                               attempt, _MAX_RETRIES, exc, wait)
                time.sleep(wait)
            else:
                logger.error("Webhook failed after %d attempts: %s — url=%s event=%s",
                             _MAX_RETRIES, exc, url, event)

    return False
