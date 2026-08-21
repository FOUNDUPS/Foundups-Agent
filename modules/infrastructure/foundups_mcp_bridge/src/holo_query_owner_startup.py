"""Bounded readiness loop for one owned HoloIndex query process."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Protocol

from .holo_query_binding import parse_exact_binding
from .holo_query_replica_binding import parse_replica_binding


class OwnerProcess(Protocol):
    def poll(self) -> int | None: ...


class HealthProof(Protocol):
    ready: bool
    rejection: str
    binding: tuple[str, str, str, str]
    replica_binding: tuple[str, str, str, str]


@dataclass(frozen=True)
class OwnerStartupSettings:
    host: str
    port: int
    token: str
    startup_timeout_seconds: float
    probe_timeout_seconds: float
    startup_probe_timeout_seconds: float
    probe_interval_seconds: float
    expected_repo_head_sha: str = ""
    expected_repo_root_digest: str = ""
    expected_generation_id: str = ""
    expected_receipt_digest: str = ""
    expected_replica_binding: tuple[str, str, str, str] = ("", "", "", "")

    @classmethod
    def from_binding(
        cls,
        *,
        host: str,
        port: int,
        token: str,
        timeouts: tuple[float, float, float, float],
        binding: tuple[str, str, str, str],
        replica_binding: tuple[str, str, str, str] = ("", "", "", ""),
    ) -> "OwnerStartupSettings":
        return cls(
            host=host,
            port=port,
            token=token,
            startup_timeout_seconds=timeouts[0],
            probe_timeout_seconds=timeouts[1],
            startup_probe_timeout_seconds=timeouts[2],
            probe_interval_seconds=timeouts[3],
            expected_repo_head_sha=binding[0],
            expected_repo_root_digest=binding[1],
            expected_generation_id=binding[2],
            expected_receipt_digest=binding[3],
            expected_replica_binding=replica_binding,
        )


@dataclass(frozen=True)
class OwnerStartupResult:
    binding: tuple[str, str, str, str] = ("", "", "", "")
    replica_binding: tuple[str, str, str, str] = ("", "", "", "")
    error: str = ""


def _ready_startup_result(
    proof: HealthProof,
    process: OwnerProcess,
    expected: tuple[str, str, str, str],
    expected_replica: tuple[str, str, str, str],
) -> OwnerStartupResult:
    if process.poll() is not None:
        return OwnerStartupResult(error="HOLOINDEX_QUERY_SERVICE_EXITED_DURING_STARTUP")
    binding = parse_exact_binding(getattr(proof, "binding", None))
    replica = parse_replica_binding(getattr(proof, "replica_binding", None))
    mismatch = binding is None or replica != expected_replica or any(
        wanted and wanted != found for wanted, found in zip(expected, binding or ())
    )
    if mismatch:
        return OwnerStartupResult(error="HOLOINDEX_QUERY_SERVICE_BINDING_MISMATCH")
    return OwnerStartupResult(binding=binding, replica_binding=replica)


def await_owner_startup(
    *,
    process: OwnerProcess,
    settings: OwnerStartupSettings,
    health_exchange: Callable[..., HealthProof],
    clock: Callable[[], float],
    sleeper: Callable[[float], Any],
) -> OwnerStartupResult:
    """Wait for one authenticated ready proof within the total deadline."""
    expected = parse_exact_binding((
        settings.expected_repo_head_sha, settings.expected_repo_root_digest,
        settings.expected_generation_id, settings.expected_receipt_digest,
    ), allow_empty_fields=True)
    if expected is None:
        return OwnerStartupResult(error="HOLOINDEX_QUERY_SERVICE_BINDING_MISMATCH")
    expected_replica = parse_replica_binding(settings.expected_replica_binding)
    if expected_replica is None:
        return OwnerStartupResult(error="HOLOINDEX_QUERY_REPLICA_REQUIRED")
    deadline = clock() + settings.startup_timeout_seconds
    while True:
        if process.poll() is not None:
            return OwnerStartupResult(error="HOLOINDEX_QUERY_SERVICE_EXITED_DURING_STARTUP")
        remaining = deadline - clock()
        if remaining <= 0:
            return OwnerStartupResult(error="HOLOINDEX_QUERY_SERVICE_STARTUP_TIMEOUT")
        proof = health_exchange(
            host=settings.host,
            port=settings.port,
            token=settings.token,
            timeout_seconds=min(
                max(
                    settings.probe_timeout_seconds,
                    settings.startup_probe_timeout_seconds,
                ),
                remaining,
            ),
            expected_repo_head_sha=expected[0],
            expected_repo_root_digest=expected[1],
            expected_generation_id=expected[2],
            expected_receipt_digest=expected[3],
            expected_replica_binding=expected_replica,
        )
        if proof.ready:
            return _ready_startup_result(
                proof, process, expected, expected_replica
            )
        if proof.rejection:
            return OwnerStartupResult(error=proof.rejection)
        sleeper(min(settings.probe_interval_seconds, remaining))


__all__ = [
    "OwnerStartupResult",
    "OwnerStartupSettings",
    "await_owner_startup",
]
