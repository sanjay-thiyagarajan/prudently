"""Prudently API entrypoint — FastAPI app wiring every route, the Medical Representative
A2A mount, and observability bootstrap."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from google.adk.a2a.utils.agent_to_a2a import to_a2a
from opentelemetry.instrumentation.asgi import OpenTelemetryMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from agents.medrep.agent import root_agent as medrep_agent
from config import a2a_shared_secret, get_settings
from routes.agents import router as agents_router
from routes.approvals import router as approvals_router
from routes.audit import router as audit_router
from routes.auth import router as auth_router
from routes.dashboard import router as dashboard_router
from routes.inventory import router as inventory_router
from routes.job_sheets import router as job_sheets_router
from routes.payroll import router as payroll_router
from routes.policy import router as policy_router
from routes.staff import router as staff_router
from routes.surgical_scheduling import router as surgical_scheduling_router
from routes.traces import router as traces_router
from routes.vendors import router as vendors_router
from routes.watch import router as watch_router
from services.platform.observability import get_observability_service
from services.platform.rate_limit import limiter
from services.watch_loop import get_watch_loop


class SharedSecretASGIMiddleware:
    """Rejects any request to the wrapped ASGI app that doesn't carry a matching
    `X-A2A-Shared-Secret` header. docs/threat-model.md finding 1: the A2A mount below has no
    auth of any kind today — Cloud Run's `allUsers` invoker grant makes the whole service
    (this mount included) publicly reachable, and Agent Engine has no per-agent mTLS to fall
    back on. Only Model Armor screens the *content* of a request; this is what access-controls
    the request itself. Not a FastAPI dependency because the A2A mount is a separately-routed
    Starlette sub-app (`to_a2a()`'s own router), entirely outside `services/auth.py`'s
    dependency-injection system.

    The secret is fetched lazily (first request), not at construction — this class is
    instantiated at module-import time (see the `app.mount(...)` call below), and a live Secret
    Manager call at import time would break the same "no GCP call before it's actually needed"
    discipline `config.py`'s `bootstrap_gemini_credentials` establishes.
    """

    def __init__(self, wrapped_app):
        self._app = wrapped_app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return
        headers = dict(scope.get("headers") or [])
        provided = headers.get(b"x-a2a-shared-secret", b"").decode()
        try:
            expected = a2a_shared_secret()
        except Exception:  # pylint: disable=broad-exception-caught
            # Secret Manager itself unreachable — fail closed, same posture as
            # services/platform/armor_vertex.py's "armor_unavailable" fail-closed handling.
            # An open A2A mount because a dependency hiccupped is worse than a false 401.
            expected = None
        if expected is None or provided != expected:
            response = JSONResponse(
                {"detail": "Missing or invalid A2A credential."}, status_code=401
            )
            await response(scope, receive, send)
            return
        await self._app(scope, receive, send)


# Medical Representative's genuine A2A endpoint (see config.py's medrep_a2a_* settings and
# AGENTS.md's A2A section for why this lives here rather than a separate Cloud Run service).
# rpc_path mounts both the JSON-RPC route and the well-known agent-card route under this
# prefix, so app.mount uses "/", not f"/{rpc_path}" — the sub-app's own routes already start
# with the prefix.
_settings = get_settings()
medrep_a2a_app = to_a2a(
    medrep_agent,
    host=_settings.medrep_a2a_host,
    protocol=_settings.medrep_a2a_protocol,
    port=443 if _settings.medrep_a2a_protocol == "https" else 80,
    rpc_path=_settings.medrep_a2a_rpc_path,
)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # to_a2a's Starlette app attaches its JSON-RPC + agent-card routes inside its OWN
    # lifespan (building the agent card is async), and Starlette's Mount does not
    # auto-forward the outer app's lifespan to a mounted sub-app — without this, the mounted
    # routes 404 even though app.mount() itself succeeds silently. Entering the sub-app's
    # lifespan_context here is the documented fix for nested ASGI apps.
    async with medrep_a2a_app.router.lifespan_context(medrep_a2a_app):
        # The fleet watch starts here, not behind a "Run" button: it must be running the
        # moment the API process is, so a judge who never touches the dashboard still sees the
        # fleet act on its own. asyncio.create_task requires a running loop, which only exists
        # once uvicorn has actually started serving — this lifespan is the earliest point that
        # is true.
        get_watch_loop().start()
        yield


app = FastAPI(title="Prudently API", lifespan=lifespan)

# docs/threat-model.md findings 1/4: registers the shared limiter (services/platform/
# rate_limit.py) app-wide. Individual routes still opt into a specific rate via
# @limiter.limit(...) (routes/approvals.py, routes/watch.py) — this just wires the machinery
# that makes those decorators work and turns a limit breach into a real 429, not a 500.
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# /dashboard/overview and /approvals/* stay unauthenticated on purpose (see routes/policy.py's
# docstring for the write-surface that isn't): judges need the hosted URL reachable without
# the user present, and the approval links must be clickable straight from an email with no
# dashboard login. The overview's approvals list is projected down to task_type/status/
# recipient_label/subject/requested_by/timestamp in routes/dashboard.py specifically so this
# public feed never exposes the manager's real email address or full request/email bodies.
# /policy/* is real Firebase-Auth-gated manager config, which is why allow_methods now needs
# POST/PUT, not just GET.
#
# allow_origins is an explicit list, not "*" (docs/threat-model.md finding 8) — wildcard CORS
# on an API that (as of Part D) carries patient-identity-adjacent responses isn't defensible
# just because bearer-token auth already rules out cookie-based CSRF; it still lets any website
# read every public GET cross-origin. PUBLIC_WEB_ORIGINS covers the deployed dashboard plus
# local dev.
_PUBLIC_WEB_ORIGINS = [
    "https://prudently-web-jnpvbtwpwa-uc.a.run.app",
    "https://prudently-web-439570031916.us-central1.run.app",
    "http://localhost:3000",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_PUBLIC_WEB_ORIGINS,
    allow_methods=["GET", "POST", "PUT"],
    allow_headers=["*"],
)

app.include_router(watch_router)
app.include_router(dashboard_router)
app.include_router(approvals_router)
app.include_router(audit_router)
app.include_router(policy_router)
app.include_router(payroll_router)
app.include_router(agents_router)
app.include_router(traces_router)
app.include_router(inventory_router)
app.include_router(staff_router)
app.include_router(vendors_router)
app.include_router(auth_router)
app.include_router(job_sheets_router)
app.include_router(surgical_scheduling_router)


@app.get("/health")
def health() -> dict:
    settings = get_settings()
    return {
        "status": "ok",
        "project": settings.google_cloud_project,
        "region": settings.google_cloud_location,
    }


@app.get("/")
def root() -> dict:
    return {"service": "prudently-api", "status": "ok"}


# Force our Cloud-Trace-exporting TracerProvider (services/platform/observability_vertex.py)
# to become the process-global OTel provider before wrapping the A2A mount in ASGI
# instrumentation — OpenTelemetryMiddleware resolves its tracer provider once, at wrap time,
# not lazily per request, so this must run first. An incoming A2A request from Supply Chain —
# whose httpx client is instrumented the same way, see agents/supply/agent.py — carries a
# real W3C traceparent header, so medrep's own spans (medrep.pre_llm_screen,
# medrep.screen_vendor_message, armor.sanitize_user_prompt) nest as children of Supply Chain's
# trace instead of starting a new root trace on every A2A hop.
with get_observability_service().span("api.bootstrap_tracing", {}):
    pass

# Registered last, after every FastAPI-native route above: Starlette matches routes in
# registration order, and Mount("/") matches any path, so it must come after the routes it
# should never shadow. Wrapped in OpenTelemetryMiddleware rather than instrumenting the outer
# `app` — the outer app's own routes (dashboard/approvals/policy/watch) don't need or want an
# incoming traceparent header trusted from arbitrary public callers; only the genuine A2A
# boundary does. SharedSecretASGIMiddleware wraps outermost so an unauthenticated request never
# reaches the tracing layer, let alone the agent, at all.
app.mount("/", SharedSecretASGIMiddleware(OpenTelemetryMiddleware(medrep_a2a_app)))
