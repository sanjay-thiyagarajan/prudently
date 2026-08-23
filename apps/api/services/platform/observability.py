"""Observability capability port: real spans exported to Cloud Trace via OTel's
`CloudTraceSpanExporter` (`observability_vertex.py`); `observability_local.py` is a true
no-op for offline dev without GCP credentials. Selected by `OBSERVABILITY_BACKEND`, matching
the adapter pattern described in AGENTS.md's "Platform adapter layer" section.

Call sites use `span(name, attributes)` as a context manager rather than a bare
fire-and-forget start call — a span needs a start *and* end to have a real duration, and the
local adapter's no-op context manager means call sites never need an `if backend == vertex`
branch."""

from __future__ import annotations

from contextlib import AbstractContextManager
from functools import lru_cache
from typing import Protocol

from config import get_settings


class SpanHandle(Protocol):  # pylint: disable=too-few-public-methods
    trace_id: str | None

    def set_attribute(self, key: str, value: object) -> None: ...  # noqa: E704


class ObservabilityService(Protocol):  # pylint: disable=too-few-public-methods
    def span(
        self, name: str, attributes: dict[str, object] | None = None
    ) -> AbstractContextManager[SpanHandle]: ...  # noqa: E704


@lru_cache
def get_observability_service() -> ObservabilityService:
    # pylint: disable=import-outside-toplevel,cyclic-import
    if get_settings().observability_backend == "vertex":
        from .observability_vertex import VertexObservabilityService

        return VertexObservabilityService()

    from .observability_local import LocalObservabilityService

    return LocalObservabilityService()
