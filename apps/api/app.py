"""Prudently API entrypoint. Day 2: hello-world + health only; agents land Day 3+."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from google.adk.a2a.utils.agent_to_a2a import to_a2a

from agents.medrep.agent import root_agent as medrep_agent
from config import get_settings
from routes.approvals import router as approvals_router
from routes.dashboard import router as dashboard_router
from routes.policy import router as policy_router
from routes.sim import router as sim_router

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
    # auto-forward the outer app's lifespan to a mounted sub-app — confirmed Day 5: without
    # this, the mounted routes 404 even though app.mount() itself succeeds silently. Entering
    # the sub-app's lifespan_context here is the documented fix for nested ASGI apps.
    async with medrep_a2a_app.router.lifespan_context(medrep_a2a_app):
        yield


app = FastAPI(title="Prudently API", lifespan=lifespan)

# /dashboard/overview and /approvals/* stay unauthenticated on purpose (see routes/policy.py's
# docstring for the write-surface that isn't): judges need the hosted URL reachable without
# the user present, and the approval links must be clickable straight from an email with no
# dashboard login. The overview's approvals list is projected down to task_type/status/
# recipient_label/subject/requested_by/timestamp in routes/dashboard.py specifically so this
# public feed never exposes the manager's real email address or full request/email bodies.
# /policy/* is real Firebase-Auth-gated manager config, which is why allow_methods now needs
# POST/PUT, not just GET.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "PUT"],
    allow_headers=["*"],
)

app.include_router(sim_router)
app.include_router(dashboard_router)
app.include_router(approvals_router)
app.include_router(policy_router)


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
    return {"service": "prudently-api", "status": "day-2-scaffold"}


# Registered last, after every FastAPI-native route above: Starlette matches routes in
# registration order, and Mount("/") matches any path, so it must come after the routes it
# should never shadow.
app.mount("/", medrep_a2a_app)
