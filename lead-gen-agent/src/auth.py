"""
API Authentication
───────────────────
Simple API key auth for the FastAPI server.

Set API_KEY in .env to enable authentication.
If API_KEY is not set, auth is disabled (useful for local development).

Clients send the key in the X-API-Key header:
    curl -H "X-API-Key: your-key-here" http://localhost:3000/api/runs

Or as a Bearer token:
    curl -H "Authorization: Bearer your-key-here" http://localhost:3000/api/runs
"""

import os
from fastapi import HTTPException, Security, status
from fastapi.security.api_key import APIKeyHeader
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
_bearer_scheme = HTTPBearer(auto_error=False)


async def require_api_key(
    api_key_header: str = Security(_api_key_header),
    bearer: HTTPAuthorizationCredentials = Security(_bearer_scheme),
) -> str | None:
    """
    FastAPI dependency — validates the API key.

    Accepts the key via:
      - X-API-Key header
      - Authorization: Bearer <key>

    If API_KEY env var is not set, all requests are allowed (dev mode).
    Returns the validated key, or None if auth is disabled.
    """
    expected = os.getenv("API_KEY", "").strip()

    if not expected:
        # Auth disabled — development / self-hosted with no external access
        return None

    # Extract token from either source
    token = api_key_header or (bearer.credentials if bearer else None)

    if not token or token != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key. Pass X-API-Key header or Authorization: Bearer <key>.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    return token
