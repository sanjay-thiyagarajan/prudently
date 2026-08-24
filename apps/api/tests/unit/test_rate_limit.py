"""The bug this guards against: slowapi's default key_func (request.client.host) does not stay
constant across requests from the same real client behind Cloud Run's load balancer, so a
25-request burst against a live, deployed, rate-limited route never triggered a single 429 —
found by testing live, not assumed. _real_client_ip reads X-Forwarded-For instead."""

from __future__ import annotations

from unittest.mock import MagicMock

from services.platform.rate_limit import _real_client_ip


def _request(forwarded: str | None, client_host: str | None = "10.0.0.1") -> MagicMock:
    request = MagicMock()
    request.headers = {"x-forwarded-for": forwarded} if forwarded else {}
    request.client = MagicMock(host=client_host) if client_host else None
    return request


def test_uses_first_hop_of_x_forwarded_for():
    # Cloud Run's own load balancer appends its hops after the real client's — the real client
    # is always the first entry.
    request = _request("203.0.113.7, 10.0.0.1, 10.0.0.2")
    assert _real_client_ip(request) == "203.0.113.7"


def test_strips_whitespace_around_the_first_hop():
    request = _request(" 203.0.113.7 , 10.0.0.1")
    assert _real_client_ip(request) == "203.0.113.7"


def test_falls_back_to_client_host_when_header_absent():
    # Local dev (no proxy in front) never sets X-Forwarded-For.
    request = _request(None, client_host="127.0.0.1")
    assert _real_client_ip(request) == "127.0.0.1"


def test_falls_back_to_unknown_when_nothing_is_available():
    request = _request(None, client_host=None)
    assert _real_client_ip(request) == "unknown"
