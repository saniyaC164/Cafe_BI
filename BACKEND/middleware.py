"""
middleware.py
==============
All middleware for the Cafe BI backend:

  1. RequestLoggingMiddleware  — logs method, path, status, duration
  2. RateLimitMiddleware       — simple in-memory rate limiter per IP
  3. CacheMiddleware           — in-memory response cache for slow endpoints
  4. ErrorHandlerMiddleware    — catches unhandled exceptions, returns clean JSON

Usage: imported and registered in main.py
"""

import time
import json
import hashlib
from collections import defaultdict
from typing import Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware


# ─────────────────────────────────────────────
# 1. REQUEST LOGGING
# Logs every request: method, path, status code, duration
# ─────────────────────────────────────────────
class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start  = time.perf_counter()
        method = request.method
        path   = request.url.path

        try:
            response = await call_next(request)
            duration = (time.perf_counter() - start) * 1000
            print(
                f"  {method:6s} {path:45s} "
                f"-> {response.status_code}  ({duration:.1f}ms)"
            )
            return response
        except Exception as exc:
            duration = (time.perf_counter() - start) * 1000
            print(f"  {method:6s} {path:45s} -> 500  ({duration:.1f}ms)  ERROR: {exc}")
            raise


# ─────────────────────────────────────────────
# 2. RATE LIMITING
# Max N requests per IP per minute.
# Exempt: /docs, /openapi.json, /health
# ─────────────────────────────────────────────
RATE_LIMIT_REQUESTS = 60        # requests allowed
RATE_LIMIT_WINDOW   = 60        # per N seconds

EXEMPT_PATHS = {"/", "/health", "/docs", "/openapi.json", "/redoc"}


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_requests: int = RATE_LIMIT_REQUESTS,
                 window_seconds: int = RATE_LIMIT_WINDOW):
        super().__init__(app)
        self.max_requests  = max_requests
        self.window        = window_seconds
        # {ip: [(timestamp, count)]}
        self._buckets: dict[str, list] = defaultdict(list)

    def _get_ip(self, request: Request) -> str:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def _is_allowed(self, ip: str) -> tuple[bool, int]:
        now    = time.time()
        window = self._buckets[ip]

        # Drop entries outside the current window
        self._buckets[ip] = [(t, c) for t, c in window if now - t < self.window]

        total = sum(c for _, c in self._buckets[ip])
        if total >= self.max_requests:
            return False, 0

        self._buckets[ip].append((now, 1))
        return True, self.max_requests - total - 1

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if request.url.path in EXEMPT_PATHS:
            return await call_next(request)

        ip              = self._get_ip(request)
        allowed, remaining = self._is_allowed(ip)

        if not allowed:
            return JSONResponse(
                status_code=429,
                content={
                    "error":   "rate_limit_exceeded",
                    "message": f"Too many requests. Max {self.max_requests} per {self.window}s.",
                    "retry_after_seconds": self.window,
                },
                headers={"Retry-After": str(self.window)},
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"]     = str(self.max_requests)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response


# ─────────────────────────────────────────────
# 3. RESPONSE CACHE
# Caches GET responses in memory for slow endpoints.
# MBA and Forecasting take 3–5s — cache saves repeated calls.
#
# Cache TTL by path prefix:
#   /api/mba/*        → 10 minutes  (Apriori is expensive)
#   /api/forecast/*   → 15 minutes  (Prophet training)
#   /api/kpi/*        → 2 minutes
#   /api/sentiment/*  → 5 minutes
#   /api/inventory/*  → 2 minutes
# ─────────────────────────────────────────────
CACHE_TTL: dict[str, int] = {
    "/api/mba":        600,    # 10 min
    "/api/forecast":   900,    # 15 min
    "/api/kpi":        120,    # 2 min
    "/api/sentiment":  300,    # 5 min
    "/api/inventory":  120,    # 2 min
}


class CacheMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        # {cache_key: (timestamp, body_bytes, status_code, headers)}
        self._store: dict[str, tuple] = {}

    def _get_ttl(self, path: str) -> int | None:
        for prefix, ttl in CACHE_TTL.items():
            if path.startswith(prefix):
                return ttl
        return None

    def _make_key(self, request: Request) -> str:
        raw = f"{request.method}:{request.url.path}:{str(request.query_params)}"
        return hashlib.md5(raw.encode()).hexdigest()

    def _is_fresh(self, key: str, ttl: int) -> bool:
        if key not in self._store:
            return False
        cached_at = self._store[key][0]
        return (time.time() - cached_at) < ttl

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Only cache GET requests
        if request.method != "GET":
            return await call_next(request)

        ttl = self._get_ttl(request.url.path)
        if ttl is None:
            return await call_next(request)

        key = self._make_key(request)

        if self._is_fresh(key, ttl):
            _, body, status_code, headers = self._store[key]
            response = Response(
                content    = body,
                status_code= status_code,
                media_type = "application/json",
            )
            response.headers["X-Cache"] = "HIT"
            # Restore original headers except content-length (auto-set)
            for k, v in headers.items():
                if k.lower() not in ("content-length", "content-type"):
                    response.headers[k] = v
            return response

        # Cache miss — call the actual endpoint
        response = await call_next(request)

        if response.status_code == 200:
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            self._store[key] = (time.time(), body, response.status_code, dict(response.headers))
            response = Response(
                content    = body,
                status_code= response.status_code,
                media_type = "application/json",
            )
            response.headers["X-Cache"] = "MISS"

        return response

    def invalidate(self, path_prefix: str):
        """Call this to clear cache entries for a given prefix (e.g. after retraining)."""
        keys_to_delete = [
            k for k in self._store
            if path_prefix in k
        ]
        for k in keys_to_delete:
            del self._store[k]


# ─────────────────────────────────────────────
# 4. GLOBAL ERROR HANDLER
# Catches any unhandled exception and returns
# a clean JSON error instead of a raw 500 traceback.
# ─────────────────────────────────────────────
class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            return await call_next(request)
        except Exception as exc:
            return JSONResponse(
                status_code=500,
                content={
                    "error":   "internal_server_error",
                    "message": "An unexpected error occurred. Please try again.",
                    "detail":  str(exc),       # remove this line in production
                },
            )