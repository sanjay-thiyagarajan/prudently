"""Prudently API entrypoint. Day 2: hello-world + health only; agents land Day 3+."""

from fastapi import FastAPI

from config import get_settings
from routes.sim import router as sim_router

app = FastAPI(title="Prudently API")
app.include_router(sim_router)


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
