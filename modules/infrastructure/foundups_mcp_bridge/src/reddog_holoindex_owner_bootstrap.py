"""Process-lifetime HoloIndex owner bootstrap for RedDog operational work."""

from __future__ import annotations

import os
import threading
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from holo_index.repository_state import repository_root_digest
from holo_index.storage_contract import resolve_holoindex_ssd_path

from .holo_query_service_supervisor import (
    DEFAULT_OWNER_PROBE_TIMEOUT_SECONDS,
    SERVICE_TOKEN_ENV,
    SERVICE_URL_ENV,
    HoloQueryServiceSupervisor,
    HoloQueryServiceSupervisorError,
    _authenticated_health_probe,
)


OWNER_NOT_REQUESTED = "NOT_REQUESTED"
OWNER_CONFIGURED = "CONFIGURED"
OWNER_AUTO_START_DISABLED = "AUTO_START_DISABLED"
OWNER_STARTED = "STARTED"
OWNER_REUSED = "REUSED"
OWNER_FAILED = "FAILED"

AUTO_START_ENV = "REDDOG_HOLOINDEX_OWNER_AUTO_START"
AUTO_START_DISABLED_ERROR = "HOLOINDEX_QUERY_SERVICE_AUTO_START_DISABLED"
BOOTSTRAP_FAILED_ERROR = "HOLOINDEX_QUERY_SERVICE_BOOTSTRAP_FAILED"
CONFIGURED_INVALID_ERROR = "HOLOINDEX_QUERY_SERVICE_CONFIGURED_INVALID"
CONFIGURED_UNREADY_ERROR = "HOLOINDEX_QUERY_SERVICE_CONFIGURED_UNREADY"
# The owner health contract runs a semantic canary. Keep the exact-binding
# proof aligned with the supervisor rather than imposing a shorter timeout
# than the query service itself permits.
CONFIGURED_HEALTH_TIMEOUT_SECONDS = DEFAULT_OWNER_PROBE_TIMEOUT_SECONDS
MIN_CONFIGURED_TOKEN_CHARS = 32
QUERY_PATH = "/holoindex/v1/query"
PHASE1_BIND_HOST = "127.0.0.1"

_OWNER_LOCK = threading.RLock()
_OWNER_SUPERVISOR: HoloQueryServiceSupervisor | None = None
_OWNER_HANDOFF: tuple[str, str] | None = None
_OWNER_EXPECTED_BINDING: tuple[str, str, str, str] = ("", "", "", "")


@dataclass(frozen=True)
class RedDogHoloIndexOwnerBootstrapResult:
    """Secret-free owner bootstrap status suitable for console reporting."""

    ready: bool
    status: str
    error: str = ""


def _configured_owner_health_ready(
    *,
    service_url: str,
    token: str,
    expected_repo_head_sha: str = "",
    expected_repo_root_digest: str = "",
    expected_generation_id: str = "",
    expected_receipt_digest: str = "",
) -> bool:
    """Prove the configured endpoint serves the exact semantic health contract."""
    try:
        parsed = urlparse(service_url)
        host = str(parsed.hostname or "")
        port = parsed.port or 80
    except ValueError:
        return False
    probe_kwargs = {
        "host": host,
        "port": port,
        "token": token,
        "timeout_seconds": CONFIGURED_HEALTH_TIMEOUT_SECONDS,
    }
    if expected_repo_head_sha:
        probe_kwargs["expected_repo_head_sha"] = expected_repo_head_sha
    if expected_repo_root_digest:
        probe_kwargs["expected_repo_root_digest"] = expected_repo_root_digest
    if expected_generation_id:
        probe_kwargs["expected_generation_id"] = expected_generation_id
    if expected_receipt_digest:
        probe_kwargs["expected_receipt_digest"] = expected_receipt_digest
    return _authenticated_health_probe(
        **probe_kwargs,
    )


def _service_endpoint_is_valid(service_url: str) -> bool:
    """Accept only the owner's bounded loopback query endpoint."""
    try:
        parsed = urlparse(service_url)
        port = parsed.port
    except ValueError:
        return False
    return bool(
        parsed.scheme == "http"
        and parsed.hostname == PHASE1_BIND_HOST
        and parsed.username is None
        and parsed.password is None
        and (port is None or 1 <= port <= 65_535)
        and parsed.path in {"", "/", QUERY_PATH, f"{QUERY_PATH}/"}
        and not parsed.query
        and not parsed.fragment
    )


def _configured_service_result(
    *,
    expected_repo_head_sha: str = "",
    expected_repo_root_digest: str = "",
    expected_generation_id: str = "",
    expected_receipt_digest: str = "",
) -> RedDogHoloIndexOwnerBootstrapResult | None:
    url = str(os.environ.get(SERVICE_URL_ENV) or "").strip()
    token = str(os.environ.get(SERVICE_TOKEN_ENV) or "").strip()
    if not url and not token:
        return None
    if not url or len(token) < MIN_CONFIGURED_TOKEN_CHARS:
        return RedDogHoloIndexOwnerBootstrapResult(
            ready=False,
            status=OWNER_FAILED,
            error=CONFIGURED_INVALID_ERROR,
        )
    if not _service_endpoint_is_valid(url):
        return RedDogHoloIndexOwnerBootstrapResult(
            ready=False,
            status=OWNER_FAILED,
            error=CONFIGURED_INVALID_ERROR,
        )
    if not _configured_owner_health_ready(
        service_url=url,
        token=token,
        expected_repo_head_sha=expected_repo_head_sha,
        expected_repo_root_digest=expected_repo_root_digest,
        expected_generation_id=expected_generation_id,
        expected_receipt_digest=expected_receipt_digest,
    ):
        return RedDogHoloIndexOwnerBootstrapResult(
            ready=False,
            status=OWNER_FAILED,
            error=CONFIGURED_UNREADY_ERROR,
        )
    return RedDogHoloIndexOwnerBootstrapResult(
        ready=True,
        status=OWNER_CONFIGURED,
    )


def _validated_owner_handoff(
    supervisor: HoloQueryServiceSupervisor,
    *,
    expected_repo_head_sha: str = "",
    expected_repo_root_digest: str = "",
    expected_generation_id: str = "",
    expected_receipt_digest: str = "",
) -> tuple[str, str]:
    """Read a handoff whose exact binding was proven during supervisor startup."""
    handoff = supervisor.environment_for_child({})
    service_url = str(handoff.get(SERVICE_URL_ENV) or "").strip()
    token = str(handoff.get(SERVICE_TOKEN_ENV) or "").strip()
    if (
        not _service_endpoint_is_valid(service_url)
        or len(token) < MIN_CONFIGURED_TOKEN_CHARS
    ):
        raise HoloQueryServiceSupervisorError(CONFIGURED_INVALID_ERROR)
    expected_binding = (
        expected_repo_head_sha,
        expected_repo_root_digest,
        expected_generation_id,
        expected_receipt_digest,
    )
    verified_binding = supervisor.verified_binding
    if not supervisor.is_ready or any(
        expected and expected != verified
        for expected, verified in zip(expected_binding, verified_binding)
    ):
        raise HoloQueryServiceSupervisorError(CONFIGURED_UNREADY_ERROR)
    return service_url, token


def resolve_reddog_holoindex_owner_handoff() -> tuple[str, str] | None:
    """Return a live private handoff without contending with active queries."""
    with _OWNER_LOCK:
        supervisor = _OWNER_SUPERVISOR
        if supervisor is None or _OWNER_HANDOFF is None:
            return None
        if supervisor.is_ready:
            return _OWNER_HANDOFF
        failed_handoff = _OWNER_HANDOFF
    return restart_reddog_holoindex_owner(failed_handoff=failed_handoff)


def verify_reddog_holoindex_owner_binding(
    *,
    repo_root: Path | str,
    expected_repo_head_sha: str,
    expected_generation_id: str,
    expected_receipt_digest: str,
) -> bool:
    """Verify that the active query owner serves one exact generation."""

    expected_binding = _requested_binding(
        repo_root,
        expected_repo_head_sha,
        expected_generation_id,
        expected_receipt_digest,
    )
    with _OWNER_LOCK:
        supervisor = _OWNER_SUPERVISOR
        if (
            supervisor is not None
            and _OWNER_HANDOFF is not None
            and supervisor.is_ready
        ):
            return supervisor.verified_binding == expected_binding

        service_url = os.environ.get(SERVICE_URL_ENV, "").strip()
        token = os.environ.get(SERVICE_TOKEN_ENV, "").strip()
        if not service_url or not token:
            return False
        return _configured_owner_health_ready(
            service_url=service_url,
            token=token,
            expected_repo_head_sha=expected_binding[0],
            expected_repo_root_digest=expected_binding[1],
            expected_generation_id=expected_binding[2],
            expected_receipt_digest=expected_binding[3],
        )


def restart_reddog_holoindex_owner(
    *,
    failed_handoff: tuple[str, str],
) -> tuple[str, str] | None:
    """Replace only the owned handoff that produced a poison/death signal."""
    global _OWNER_EXPECTED_BINDING, _OWNER_HANDOFF, _OWNER_SUPERVISOR
    with _OWNER_LOCK:
        supervisor = _OWNER_SUPERVISOR
        if supervisor is None or _OWNER_HANDOFF is None:
            return None
        if _OWNER_HANDOFF != failed_handoff:
            return _OWNER_HANDOFF if supervisor.is_ready else None
        repo_root = supervisor.repo_root
        expected = _OWNER_EXPECTED_BINDING
        supervisor.stop()
        _OWNER_SUPERVISOR = None
        _OWNER_HANDOFF = None
        _OWNER_EXPECTED_BINDING = ("", "", "", "")
        restarted = ensure_reddog_holoindex_owner(
            repo_root=repo_root,
            requested=True,
            expected_repo_head_sha=expected[0],
            expected_generation_id=expected[2],
            expected_receipt_digest=expected[3],
        )
        return _OWNER_HANDOFF if restarted.ready else None


def _requested_binding(
    repo_root: Path | str,
    repo_head_sha: str,
    generation_id: str,
    receipt_digest: str,
) -> tuple[str, str, str, str]:
    return (
        repo_head_sha,
        repository_root_digest(Path(repo_root)),
        generation_id,
        receipt_digest,
    )


def _stop_owned_owner() -> None:
    """Stop and erase only the supervisor owned by this host process."""
    global _OWNER_EXPECTED_BINDING, _OWNER_HANDOFF, _OWNER_SUPERVISOR
    supervisor = _OWNER_SUPERVISOR
    if supervisor is not None:
        supervisor.stop()
    _OWNER_SUPERVISOR = None
    _OWNER_HANDOFF = None
    _OWNER_EXPECTED_BINDING = ("", "", "", "")


def _reuse_owned_owner(
    *,
    expected_binding: tuple[str, str, str, str],
) -> RedDogHoloIndexOwnerBootstrapResult | None:
    """Return REUSED only after the live owner matches and reproves binding."""
    global _OWNER_HANDOFF
    supervisor = _OWNER_SUPERVISOR
    if supervisor is None:
        return None
    matches = all(
        not requested_value or requested_value == stored_value
        for requested_value, stored_value in zip(
            expected_binding,
            _OWNER_EXPECTED_BINDING,
        )
    )
    if not supervisor.is_ready or not matches or _OWNER_HANDOFF is None:
        _stop_owned_owner()
        return None
    try:
        _OWNER_HANDOFF = _validated_owner_handoff(
            supervisor,
            expected_repo_head_sha=expected_binding[0],
            expected_repo_root_digest=expected_binding[1],
            expected_generation_id=expected_binding[2],
            expected_receipt_digest=expected_binding[3],
        )
    except Exception:
        _stop_owned_owner()
        return None
    return RedDogHoloIndexOwnerBootstrapResult(ready=True, status=OWNER_REUSED)


def _start_owned_owner(
    *,
    repo_root: Path | str,
    expected_binding: tuple[str, str, str, str],
) -> RedDogHoloIndexOwnerBootstrapResult:
    """Start, authenticate, and retain one process-private owner."""
    global _OWNER_EXPECTED_BINDING, _OWNER_HANDOFF, _OWNER_SUPERVISOR
    supervisor: HoloQueryServiceSupervisor | None = None
    try:
        ssd_path = resolve_holoindex_ssd_path(environ=os.environ)
        supervisor = HoloQueryServiceSupervisor(
            repo_root=repo_root,
            ssd_path=ssd_path,
        )
        supervisor.start(
            expected_repo_head_sha=expected_binding[0],
            expected_repo_root_digest=expected_binding[1],
            expected_generation_id=expected_binding[2],
            expected_receipt_digest=expected_binding[3],
        )
        handoff = _validated_owner_handoff(
            supervisor,
            expected_repo_head_sha=expected_binding[0],
            expected_repo_root_digest=expected_binding[1],
            expected_generation_id=expected_binding[2],
            expected_receipt_digest=expected_binding[3],
        )
    except HoloQueryServiceSupervisorError as exc:
        if supervisor is not None:
            supervisor.stop()
        return RedDogHoloIndexOwnerBootstrapResult(
            ready=False,
            status=OWNER_FAILED,
            error=exc.code,
        )
    except Exception:
        if supervisor is not None:
            supervisor.stop()
        return RedDogHoloIndexOwnerBootstrapResult(
            ready=False,
            status=OWNER_FAILED,
            error=BOOTSTRAP_FAILED_ERROR,
        )
    _OWNER_SUPERVISOR = supervisor
    _OWNER_HANDOFF = handoff
    _OWNER_EXPECTED_BINDING = expected_binding
    return RedDogHoloIndexOwnerBootstrapResult(ready=True, status=OWNER_STARTED)


def ensure_reddog_holoindex_owner(
    *,
    repo_root: Path | str,
    requested: bool,
    expected_repo_head_sha: str = "",
    expected_generation_id: str = "",
    expected_receipt_digest: str = "",
) -> RedDogHoloIndexOwnerBootstrapResult:
    """Ensure one host owner exists only for Holo-dependent RedDog work."""
    if not requested:
        return RedDogHoloIndexOwnerBootstrapResult(
            ready=False,
            status=OWNER_NOT_REQUESTED,
        )
    expected_binding = _requested_binding(
        repo_root,
        expected_repo_head_sha,
        expected_generation_id,
        expected_receipt_digest,
    )
    with _OWNER_LOCK:
        reused = _reuse_owned_owner(expected_binding=expected_binding)
        if reused is not None:
            return reused
        configured_result = _configured_service_result(
            expected_repo_head_sha=expected_repo_head_sha,
            expected_repo_root_digest=expected_binding[1],
            expected_generation_id=expected_generation_id,
            expected_receipt_digest=expected_receipt_digest,
        )
        if configured_result is not None:
            return configured_result
        if os.environ.get(AUTO_START_ENV, "1") == "0":
            return RedDogHoloIndexOwnerBootstrapResult(
                ready=False,
                status=OWNER_AUTO_START_DISABLED,
                error=AUTO_START_DISABLED_ERROR,
            )
        return _start_owned_owner(
            repo_root=repo_root,
            expected_binding=expected_binding,
        )


def cleanup_reddog_holoindex_owner(*, restore_environment: bool = True) -> None:
    """Stop the owned process and erase its process-private handoff."""
    del restore_environment  # Retained for compatibility; auto-start never edits env.
    global _OWNER_EXPECTED_BINDING, _OWNER_HANDOFF, _OWNER_SUPERVISOR
    with _OWNER_LOCK:
        supervisor, _OWNER_SUPERVISOR = _OWNER_SUPERVISOR, None
        _OWNER_HANDOFF = None
        _OWNER_EXPECTED_BINDING = ("", "", "", "")
        if supervisor is not None:
            supervisor.stop()


__all__ = [
    "AUTO_START_ENV",
    "OWNER_AUTO_START_DISABLED",
    "OWNER_CONFIGURED",
    "OWNER_FAILED",
    "OWNER_NOT_REQUESTED",
    "OWNER_REUSED",
    "OWNER_STARTED",
    "RedDogHoloIndexOwnerBootstrapResult",
    "cleanup_reddog_holoindex_owner",
    "ensure_reddog_holoindex_owner",
    "restart_reddog_holoindex_owner",
    "resolve_reddog_holoindex_owner_handoff",
    "verify_reddog_holoindex_owner_binding",
]
