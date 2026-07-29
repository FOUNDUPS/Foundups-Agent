"""Bounded readiness loop for one owned HoloIndex query process."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Protocol


class OwnerProcess(Protocol):
    def poll(self) -> int | None: ...


class HealthProof(Protocol):
    ready: bool
    rejection: str
    binding: tuple[str, str, str, str]


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

    @classmethod
    def from_binding(
        cls,
        *,
        host: str,
        port: int,
        token: str,
        timeouts: tuple[float, float, float, float],
        binding: tuple[str, str, str, str],
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
        )


@dataclass(frozen=True)
class OwnerStartupResult:
    binding: tuple[str, str, str, str] = ("", "", "", "")
    error: str = ""


def await_owner_startup(
    *,
    process: OwnerProcess,
    settings: OwnerStartupSettings,
    health_exchange: Callable[..., HealthProof],
    clock: Callable[[], float],
    sleeper: Callable[[float], Any],
) -> OwnerStartupResult:
    """Wait for one authenticated ready proof within the total deadline."""
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
            expected_repo_head_sha=settings.expected_repo_head_sha,
            expected_repo_root_digest=settings.expected_repo_root_digest,
            expected_generation_id=settings.expected_generation_id,
            expected_receipt_digest=settings.expected_receipt_digest,
        )
        if proof.ready:
            if process.poll() is not None:
                return OwnerStartupResult(
                    error="HOLOINDEX_QUERY_SERVICE_EXITED_DURING_STARTUP"
                )
            return OwnerStartupResult(binding=proof.binding)
        if proof.rejection:
            return OwnerStartupResult(error=proof.rejection)
        sleeper(min(settings.probe_interval_seconds, remaining))


__all__ = [
    "OwnerStartupResult",
    "OwnerStartupSettings",
    "await_owner_startup",
]
