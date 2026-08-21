"""No-op Observability adapter for offline dev — spans are context managers that do nothing
and never touch the network, so call sites work identically regardless of backend."""

from __future__ import annotations

from contextlib import contextmanager


class _NoopSpan:  # pylint: disable=too-few-public-methods
    trace_id: str | None = None

    def set_attribute(self, key: str, value: object) -> None:
        pass


class LocalObservabilityService:  # pylint: disable=too-few-public-methods
    @contextmanager
    def span(
        self, name: str, attributes: dict[str, object] | None = None
    ):  # pylint: disable=unused-argument
        yield _NoopSpan()
