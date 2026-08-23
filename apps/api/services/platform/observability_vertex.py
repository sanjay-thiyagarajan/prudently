"""Real Observability adapter — exports OTel spans to Cloud Trace via
`CloudTraceSpanExporter`. Both runtime identities that create spans (the Reasoning Engine's
shared service agent, and the Cloud Run `coordinator-agent-sa`) need `roles/cloudtrace.agent`
granted by hand — the same class of IAM gap as Model Armor's grant (see AGENTS.md).

Uses `SimpleSpanProcessor` rather than `BatchSpanProcessor` on purpose: this fleet's span
volume is low (a handful of Gateway decisions and Armor screens per request, not a hot loop),
and `BatchSpanProcessor` runs a background export thread that is not safe to assume works
correctly inside the Reasoning Engine's sandboxed/possibly-forking container — a silently
dropped batch on container teardown would look identical to the `armor_unavailable` bug
(clean logs, zero traces, nothing to grep for). Synchronous per-span export costs real latency
per span but guarantees the span lands before the process moves on, which matters more for a
handful of security-relevant events than for a hot path."""

from __future__ import annotations

from contextlib import contextmanager
from functools import lru_cache

from opentelemetry import trace
from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor

from config import GCP_PROJECT_ID

_TRACER_NAME = "prudently"


@lru_cache
def _tracer() -> trace.Tracer:
    provider = TracerProvider(resource=Resource.create({"service.name": "prudently-api"}))
    provider.add_span_processor(
        SimpleSpanProcessor(CloudTraceSpanExporter(project_id=GCP_PROJECT_ID))
    )
    trace.set_tracer_provider(provider)
    return trace.get_tracer(_TRACER_NAME)


class _SpanHandle:  # pylint: disable=too-few-public-methods
    def __init__(self, span: trace.Span) -> None:
        self._span = span
        ctx = span.get_span_context()
        self.trace_id = format(ctx.trace_id, "032x") if ctx.is_valid else None

    def set_attribute(self, key: str, value: object) -> None:
        self._span.set_attribute(key, value)


class VertexObservabilityService:  # pylint: disable=too-few-public-methods
    @contextmanager
    def span(self, name: str, attributes: dict[str, object] | None = None):
        with _tracer().start_as_current_span(name) as span:
            handle = _SpanHandle(span)
            if attributes:
                for key, value in attributes.items():
                    handle.set_attribute(key, value)
            yield handle
