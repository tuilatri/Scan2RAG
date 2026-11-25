"""Gate: API auth matrix, explicit CORS, rate limit and fail-closed default."""

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from fastapi import HTTPException
from fastapi.routing import APIRoute

from app.core.rate_limit import RateLimitMiddleware
from app.core.security import verify_api_key, verify_api_key_query
from app.main import _allowed_origins, app


def main() -> int:
    errors: list[str] = []
    protected = []
    routes: list[APIRoute] = []
    for route in app.routes:
        if isinstance(route, APIRoute):
            routes.append(route)
        original_router = getattr(route, "original_router", None)
        if original_router is not None:
            routes.extend(r for r in original_router.routes if isinstance(r, APIRoute))

    seen: set[tuple[str, tuple[str, ...]]] = set()
    for route in routes:
        methods = tuple(sorted(route.methods or []))
        identity = (route.path, methods)
        if not route.path.startswith("/api/v1") or identity in seen:
            continue
        seen.add(identity)
        if route.path == "/api/v1/health":
            continue
        calls = {getattr(dependency, "dependency", None) for dependency in route.dependencies}
        if verify_api_key not in calls and verify_api_key_query not in calls:
            errors.append(f"unprotected:{route.path}")
        else:
            protected.append(route.path)

    if "*" in _allowed_origins:
        errors.append("cors_wildcard")

    if not any(getattr(m, "cls", None) is RateLimitMiddleware for m in app.user_middleware):
        errors.append("rate_limit_missing")

    env_backup = {key: os.environ.get(key) for key in (
        "ENVIRONMENT", "ALLOW_UNAUTHENTICATED_DEV", "SCAN2RAG_API_KEY"
    )}
    try:
        os.environ["ENVIRONMENT"] = "production"
        os.environ["ALLOW_UNAUTHENTICATED_DEV"] = "false"
        os.environ["SCAN2RAG_API_KEY"] = ""
        try:
            verify_api_key(None, None)
            errors.append("fail_open_without_key")
        except HTTPException:
            pass
    finally:
        for key, value in env_backup.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    summary = {
        "protected_routes": len(protected),
        "cors_origins": _allowed_origins,
        "rate_limit_middleware": True,
        "fail_closed": "fail_open_without_key" not in errors,
        "errors": errors,
    }
    print(json.dumps(summary, ensure_ascii=True))
    print("AUTH MATRIX PASS" if not errors else "AUTH MATRIX FAIL")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
