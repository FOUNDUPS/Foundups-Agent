"""Validation for an explicitly configured loopback Holo query owner."""

from __future__ import annotations

from typing import Callable
from urllib.parse import urlparse
from pathlib import Path

from holo_index.repository_state import repository_root_digest
from .holo_query_binding import parse_exact_binding
from .holo_query_owner_health import BINDING_MISMATCH_ERROR
from .holo_query_replica_binding import parse_replica_binding


def configured_owner_health_ready(
    *, service_url: str, token: str, timeout_seconds: float,
    health_probe: Callable[..., bool], expected_repo_head_sha: str = "",
    expected_repo_root_digest: str = "", expected_generation_id: str = "",
    expected_receipt_digest: str = "",
    expected_replica_binding: tuple[str, str, str, str] = ("", "", "", ""),
) -> bool:
    """Prove the configured endpoint serves the exact semantic contract."""

    canonical_binding = parse_exact_binding((
        expected_repo_head_sha, expected_repo_root_digest,
        expected_generation_id, expected_receipt_digest,
    ), allow_empty_fields=True)
    replica_binding = parse_replica_binding(expected_replica_binding)
    if canonical_binding is None or replica_binding is None:
        return False

    try:
        parsed = urlparse(service_url)
        host, port = str(parsed.hostname or ""), parsed.port or 80
    except ValueError:
        return False
    kwargs = {
        "host": host, "port": port, "token": token,
        "timeout_seconds": timeout_seconds,
    }
    expected = {
        "expected_repo_head_sha": canonical_binding[0],
        "expected_repo_root_digest": canonical_binding[1],
        "expected_generation_id": canonical_binding[2],
        "expected_receipt_digest": canonical_binding[3],
    }
    kwargs.update({key: value for key, value in expected.items() if value})
    kwargs["expected_replica_binding"] = replica_binding
    return health_probe(**kwargs)


def service_endpoint_is_valid(
    service_url: str, *, host: str, query_path: str,
) -> bool:
    """Accept only the bounded literal-loopback query endpoint."""

    try:
        parsed, port = urlparse(service_url), urlparse(service_url).port
    except ValueError:
        return False
    return bool(
        parsed.scheme == "http" and parsed.hostname == host
        and parsed.username is None and parsed.password is None
        and (port is None or 1 <= port <= 65_535)
        and parsed.path in {"", "/", query_path, f"{query_path}/"}
        and not parsed.query and not parsed.fragment
    )


def requested_owner_binding(
    repo_root: Path | str, repo_head_sha: str,
    generation_id: str, receipt_digest: str,
) -> tuple[str, str, str, str]:
    requested = parse_exact_binding(
        (repo_head_sha, "", generation_id, receipt_digest),
        allow_empty_fields=True,
    )
    if requested is None:
        raise ValueError(BINDING_MISMATCH_ERROR)
    binding = parse_exact_binding((
        requested[0], repository_root_digest(Path(repo_root)),
        requested[2], requested[3],
    ), allow_empty_fields=True)
    if binding is None:
        raise ValueError(BINDING_MISMATCH_ERROR)
    return binding


__all__ = [
    "configured_owner_health_ready", "requested_owner_binding",
    "service_endpoint_is_valid",
]
