"""Security dependencies for Scan2RAG API (fail-closed by default)."""

import os
import secrets

from fastapi import Header, HTTPException, Query, status

DEV_FLAGS = {"1", "true", "yes", "on"}


def _unauthenticated_dev_allowed() -> bool:
    environment = os.getenv("ENVIRONMENT", "development").strip().lower()
    allow_dev = os.getenv("ALLOW_UNAUTHENTICATED_DEV", "").strip().lower() in DEV_FLAGS
    return environment == "development" and allow_dev


def _verify_provided_key(provided_key: str | None) -> None:
    if _unauthenticated_dev_allowed():
        return
    expected_key = os.getenv("SCAN2RAG_API_KEY", "").strip()
    if not expected_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key is not configured or invalid.",
        )
    if not provided_key or not secrets.compare_digest(provided_key, expected_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key.",
        )


def verify_api_key(
    x_api_key: str | None = Header(default=None),
    authorization: str | None = Header(default=None),
) -> None:
    """Verify API key from X-API-Key or Bearer header."""
    provided_key = x_api_key
    if not provided_key and authorization and authorization.lower().startswith("bearer "):
        provided_key = authorization[7:].strip()
    _verify_provided_key(provided_key)


def verify_api_key_query(api_key: str | None = Query(default=None)) -> None:
    """Verify API key from query string (PDF iframe fallback)."""
    _verify_provided_key(api_key)
