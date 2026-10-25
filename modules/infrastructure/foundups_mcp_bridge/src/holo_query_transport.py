"""Exact transport scalar admission for private Holo owner health."""

from __future__ import annotations

import math
from dataclasses import dataclass

OWNER_HOST = "127.0.0.1"
MIN_BEARER_TOKEN_CHARS = 32
MAX_HEALTH_TIMEOUT_SECONDS = 300.0


@dataclass(frozen=True)
class ExactHealthTransport:
    host: str
    port: int
    token: str
    timeout_seconds: float


def exact_bearer_token(value: object) -> str | None:
    if type(value) is not str or len(value) < MIN_BEARER_TOKEN_CHARS:
        return None
    if value != value.strip() or not value.isprintable():
        return None
    return value


def normalize_health_transport(
    *, host: object, port: object, token: object, timeout_seconds: object,
) -> ExactHealthTransport | None:
    bearer = exact_bearer_token(token)
    if type(host) is not str or host != OWNER_HOST or bearer is None:
        return None
    if type(port) is not int or not 1 <= port <= 65_535:
        return None
    if type(timeout_seconds) not in {int, float}:
        return None
    if type(timeout_seconds) is float and not math.isfinite(timeout_seconds):
        return None
    if not 0 < timeout_seconds <= MAX_HEALTH_TIMEOUT_SECONDS:
        return None
    return ExactHealthTransport(host, port, bearer, float(timeout_seconds))
