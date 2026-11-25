"""Security dependencies for Scan2RAG API."""

import os
import secrets

from fastapi import Header, HTTPException, status


def verify_api_key(
    x_api_key: str | None = Header(default=None),
    authorization: str | None = Header(default=None),
) -> None:
    """Verify API key when SCAN2RAG_API_KEY is configured in environment."""
    expected_key = os.getenv("SCAN2RAG_API_KEY", "").strip()
    if not expected_key:
        # Dev/test mode when no API key is configured
        return

    provided_key = x_api_key
    if not provided_key and authorization and authorization.lower().startswith("bearer "):
        provided_key = authorization[7:].strip()

    if not provided_key or not secrets.compare_digest(provided_key, expected_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key.",
        )
