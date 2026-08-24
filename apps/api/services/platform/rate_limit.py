"""Shared slowapi Limiter instance — docs/threat-model.md findings 1/4: no rate limiting
existed anywhere in this stack (confirmed absent from pyproject.toml, app.py, and Cloud Run
config; the 3-instance scaling cap is a cost ceiling, not a throttle). One shared instance
because slowapi's per-route `@limiter.limit(...)` decorator and the app-level exception handler
registered in app.py must reference the identical object.

Two real bugs found live (not assumed) getting this working, both the "looked done, wasn't"
shape this project's own history is full of:

1. Keyed by the real client IP, not slowapi's default `get_remote_address`. Cloud Run
   terminates TLS and proxies every request through its own load balancer, so
   `request.client.host` (what `get_remote_address` reads) is the load balancer's own
   connection peer, not guaranteed constant across requests from the same external client — a
   25-request burst against a live, deployed, decorated route never triggered a single 429.
   Cloud Run forwards the real client IP as the first entry of `X-Forwarded-For`, which
   `_real_client_ip` reads instead.
2. `Limiter(key_style=...)` defaults to `"url"` — slowapi's own bucket key includes the
   *literal* request path, `{token}` segment and all, not the route template. A burst against
   `/approvals/{token}/approve` with a different candidate `token` on every request (exactly
   the brute-force/scanning shape this limit exists to blunt) landed in a fresh bucket every
   time and never accumulated — caught by testing with a *varying* path locally, after a
   same-path burst had already shown the decorator itself worked. `key_style="endpoint"` scopes
   the bucket to the route's view function instead, so the limit is genuinely "N attempts per
   client against this endpoint," independent of which token is in the URL.
"""

from __future__ import annotations

from fastapi import Request
from slowapi import Limiter


def _real_client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


limiter = Limiter(key_func=_real_client_ip, key_style="endpoint")
