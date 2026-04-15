import asyncio
import time
from collections import defaultdict

from fastapi import Header, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import RedirectResponse

from app.config import settings

SESSION_KEY = "authenticated"

# Paths that bypass the auth check.
_PUBLIC_PREFIXES = ("/login", "/health", "/static")

# Simple in-process brute-force counter: ip → (failure_count, last_failure_ts).
# Entries older than _TTL_S are evicted on access to bound memory usage.
_fail_counts: dict[str, tuple[int, float]] = defaultdict(lambda: (0, 0.0))
_MAX_FAILURES = 10
_LOCKOUT_DELAY_S = 2.0
_FAILURE_DELAY_S = 0.3
_TTL_S = 3600  # evict stale entries after 1 hour


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if any(request.url.path.startswith(p) for p in _PUBLIC_PREFIXES):
            return await call_next(request)
        if not request.session.get(SESSION_KEY):
            return RedirectResponse(url="/login", status_code=302)
        return await call_next(request)


async def check_login(request: Request, password: str) -> bool:
    """Verify password with brute-force protection. Returns True on success."""
    ip = request.client.host if request.client else "unknown"
    failures, last_ts = _fail_counts[ip]

    # Evict stale entry — resets counter for IPs that haven't tried recently.
    # last_ts == 0.0 means no prior failures; skip to avoid comparing against the
    # epoch (time.monotonic() - 0.0 always exceeds _TTL_S).
    if last_ts != 0.0 and time.monotonic() - last_ts > _TTL_S:
        failures = 0

    if failures >= _MAX_FAILURES:
        await asyncio.sleep(_LOCKOUT_DELAY_S)
        return False

    if password == settings.app_password:
        _fail_counts[ip] = (0, 0.0)
        return True

    _fail_counts[ip] = (failures + 1, time.monotonic())
    await asyncio.sleep(_FAILURE_DELAY_S)
    return False


async def require_htmx(hx_request: str | None = Header(None)) -> None:
    """FastAPI dependency — rejects requests that did not come from HTMX.

    HTMX always sets HX-Request: true on its own requests. Cross-origin forms
    cannot set custom headers without a CORS preflight, making this an effective
    CSRF guard without needing a token.
    """
    if hx_request != "true":
        raise HTTPException(status_code=403)
