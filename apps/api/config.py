"""Central settings, loaded from env vars (see .env.example for the full annotated list)."""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

Backend = Literal["vertex", "local"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    google_cloud_project: str = "prudently-hackathon"
    google_cloud_location: str = "us-central1"
    memory_bank_location: str = "us"

    google_genai_use_vertexai: bool = False
    model_reasoning: str = "gemini-3.5-flash"
    model_fast: str = "gemini-3.5-flash"
    gemini_api_key_secret: str = "prudently-gemini-api-key"

    registry_backend: Backend = "local"
    identity_backend: Backend = "local"
    gateway_backend: Backend = "local"
    armor_backend: Backend = "vertex"
    observability_backend: Backend = "local"

    sim_seed: int = 42
    sim_speedup: int = 1440
    dry_run: bool = True

    firestore_emulator_host: str | None = None
    pubsub_emulator_host: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
