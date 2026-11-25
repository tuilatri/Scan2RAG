"""Lightweight per-IP rate limiting middleware (no external dependency)."""

import os
import threading
import time
from collections import defaultdict, deque

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

WINDOW_SECONDS = 60.0


def _limit(name: str, default: int) -> int:
    try:
        return max(1, int(os.getenv(name, str(default))))
    except ValueError:
        return default


class RateLimitMiddleware:
    """Sliding-window limiter keyed by (client IP, route class)."""

    def __init__(self, app: ASGIApp):
        self.app = app
        self.hits: dict[tuple[str, str], deque[float]] = defaultdict(deque)
        self.lock = threading.Lock()

    def _route_class(self, scope: Scope) -> str | None:
        path = str(scope.get("path", ""))
        method = str(scope.get("method", "GET")).upper()
        if path == "/api/v1/health":
            return None
        if path.startswith("/api/v1/ocr/") and method == "POST":
            return "rectify"
        if path.startswith("/api/v1/documents/") and path.endswith("/pdf"):
            return "pdf"
        if path.startswith("/api/v1/query"):
            return "query"
        return "other"

    def _limit_for(self, route_class: str) -> int:
        return _limit(
            {
                "rectify": "RATE_LIMIT_RECTIFY_PER_MIN",
                "pdf": "RATE_LIMIT_PDF_PER_MIN",
                "query": "RATE_LIMIT_QUERY_PER_MIN",
            }.get(route_class, "RATE_LIMIT_OTHER_PER_MIN"),
            {
                "rectify": 10,
                "pdf": 30,
                "query": 60,
                "other": 120,
            }[route_class],
        )

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        route_class = self._route_class(scope)
        if route_class is None:
            await self.app(scope, receive, send)
            return

        client = scope.get("client") or ("unknown", 0)
        client_ip = str(client[0])
        key = (client_ip, route_class)
        limit = self._limit_for(route_class)
        now = time.monotonic()

        with self.lock:
            bucket = self.hits[key]
            while bucket and now - bucket[0] > WINDOW_SECONDS:
                bucket.popleft()
            if len(bucket) >= limit:
                response = JSONResponse(
                    status_code=429,
                    content={"detail": "Rate limit exceeded."},
                    headers={"Retry-After": str(int(WINDOW_SECONDS))},
                )
            else:
                bucket.append(now)
                response = None

        if response is not None:
            await response(scope, receive, send)
            return
        await self.app(scope, receive, send)
