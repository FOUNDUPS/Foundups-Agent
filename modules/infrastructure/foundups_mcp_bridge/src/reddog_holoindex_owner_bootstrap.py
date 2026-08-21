"""Process-lifetime HoloIndex owner bootstrap for RedDog operational work."""

from __future__ import annotations

import hmac
import os
import threading
from dataclasses import dataclass
from pathlib import Path

from holo_index.repository_state import repository_root_digest
from .holo_query_binding import parse_exact_binding
from .holo_query_service_supervisor import (
    BINDING_MISMATCH_ERROR,
    DEFAULT_OWNER_PROBE_TIMEOUT_SECONDS,
    SERVICE_TOKEN_ENV,
    SERVICE_URL_ENV,
    HoloQueryServiceSupervisor,
    HoloQueryServiceSupervisorError,
    _authenticated_health_probe,
)
from .holo_query_replica_binding import (
    parse_replica_binding,
)
from .reddog_holoindex_owner_replica_route import (
    QUERY_REPLICA_REQUIRED_ERROR,
    QueryReplicaOwnerRoute,
    owner_start_binding_kwargs,
    owner_supervisor_configuration,
    replica_route_is_current,
)
from .reddog_holoindex_owner_configured import (
    configured_owner_health_ready,
    requested_owner_binding,
    service_endpoint_is_valid,
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
QUERY_REPLICA_INVALID_ERROR = "QUERY_REPLICA_INVALID"
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
_OWNER_REPLICA_ROUTE: QueryReplicaOwnerRoute | None = None


@dataclass(frozen=True)
class RedDogHoloIndexOwnerBootstrapResult:
    """Secret-free owner bootstrap status suitable for console reporting."""

    ready: bool
    status: str
    error: str = ""


def _owner_failed(error: str) -> RedDogHoloIndexOwnerBootstrapResult:
    return RedDogHoloIndexOwnerBootstrapResult(
        ready=False, status=OWNER_FAILED, error=error,
    )


def _configured_owner_health_ready(
    *,
    service_url: str,
    token: str,
    expected_repo_head_sha: str = "",
    expected_repo_root_digest: str = "",
    expected_generation_id: str = "",
    expected_receipt_digest: str = "",
    expected_replica_binding: tuple[str, str, str, str] = ("", "", "", ""),
) -> bool:
    return configured_owner_health_ready(
        service_url=service_url, token=token,
        timeout_seconds=CONFIGURED_HEALTH_TIMEOUT_SECONDS,
        health_probe=_authenticated_health_probe,
        expected_repo_head_sha=expected_repo_head_sha,
        expected_repo_root_digest=expected_repo_root_digest,
        expected_generation_id=expected_generation_id,
        expected_receipt_digest=expected_receipt_digest,
        expected_replica_binding=expected_replica_binding,
    )


def _service_endpoint_is_valid(service_url: str) -> bool:
    """Accept only the owner's bounded loopback query endpoint."""
    return service_endpoint_is_valid(
        service_url, host=PHASE1_BIND_HOST, query_path=QUERY_PATH,
    )


def _configured_service_result(
    *,
    expected_repo_head_sha: str = "",
    expected_repo_root_digest: str = "",
    expected_generation_id: str = "",
    expected_receipt_digest: str = "",
    expected_replica_binding: tuple[str, str, str, str] = ("", "", "", ""),
) -> RedDogHoloIndexOwnerBootstrapResult | None:
    canonical_binding = parse_exact_binding((
        expected_repo_head_sha, expected_repo_root_digest,
        expected_generation_id, expected_receipt_digest,
    ), allow_empty_fields=True)
    if canonical_binding is None:
        return _owner_failed(BINDING_MISMATCH_ERROR)
    replica_binding = parse_replica_binding(expected_replica_binding)
    if replica_binding is None:
        return _owner_failed(QUERY_REPLICA_REQUIRED_ERROR)
    url = str(os.environ.get(SERVICE_URL_ENV) or "").strip()
    token = str(os.environ.get(SERVICE_TOKEN_ENV) or "").strip()
    if not url and not token:
        return None
    if not url or len(token) < MIN_CONFIGURED_TOKEN_CHARS:
        return _owner_failed(CONFIGURED_INVALID_ERROR)
    if not _service_endpoint_is_valid(url):
        return _owner_failed(CONFIGURED_INVALID_ERROR)
    health_kwargs = {
        "service_url": url, "token": token,
        "expected_repo_head_sha": canonical_binding[0],
        "expected_repo_root_digest": canonical_binding[1],
        "expected_generation_id": canonical_binding[2],
        "expected_receipt_digest": canonical_binding[3],
    }
    health_kwargs["expected_replica_binding"] = replica_binding
    if not _configured_owner_health_ready(**health_kwargs):
        return _owner_failed(CONFIGURED_UNREADY_ERROR)
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
    expected_replica_binding: tuple[str, str, str, str] = ("", "", "", ""),
) -> tuple[str, str]:
    """Read a handoff whose exact binding was proven during supervisor startup."""
    expected_binding = parse_exact_binding((
        expected_repo_head_sha, expected_repo_root_digest,
        expected_generation_id, expected_receipt_digest,
    ), allow_empty_fields=True)
    if expected_binding is None:
        raise HoloQueryServiceSupervisorError(BINDING_MISMATCH_ERROR)
    replica_binding = parse_replica_binding(expected_replica_binding)
    if replica_binding is None:
        raise HoloQueryServiceSupervisorError(QUERY_REPLICA_REQUIRED_ERROR)
    verified_binding = parse_exact_binding(supervisor.verified_binding)
    verified_replica = parse_replica_binding(getattr(
        supervisor, "verified_replica_binding", ("", "", "", "")
    ))
    if verified_binding is None or not supervisor.is_ready or any(
        expected and expected != verified
        for expected, verified in zip(expected_binding, verified_binding)
    ) or verified_replica != replica_binding:
        raise HoloQueryServiceSupervisorError(CONFIGURED_UNREADY_ERROR)
    handoff = supervisor.environment_for_child({})
    service_url = str(handoff.get(SERVICE_URL_ENV) or "").strip()
    token = str(handoff.get(SERVICE_TOKEN_ENV) or "").strip()
    if (
        not _service_endpoint_is_valid(service_url)
        or len(token) < MIN_CONFIGURED_TOKEN_CHARS
    ):
        raise HoloQueryServiceSupervisorError(CONFIGURED_INVALID_ERROR)
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


def _owner_binding_is_ready(
    expected_binding: tuple[str, str, str, str],
    route: QueryReplicaOwnerRoute,
) -> bool:
    supervisor = _OWNER_SUPERVISOR
    if (
        supervisor is not None
        and _OWNER_HANDOFF is not None
        and supervisor.is_ready
    ):
        verified = parse_exact_binding(supervisor.verified_binding)
        verified_replica = parse_replica_binding(getattr(
            supervisor, "verified_replica_binding", ("", "", "", ""),
        ))
        return (
            verified == expected_binding
            and verified_replica == route.expected_replica_binding
        )

    service_url = os.environ.get(SERVICE_URL_ENV, "").strip()
    token = os.environ.get(SERVICE_TOKEN_ENV, "").strip()
    if not service_url or not token:
        return False
    health_kwargs = dict(
        service_url=service_url,
        token=token,
        expected_repo_head_sha=expected_binding[0],
        expected_repo_root_digest=expected_binding[1],
        expected_generation_id=expected_binding[2],
        expected_receipt_digest=expected_binding[3],
    )
    health_kwargs["expected_replica_binding"] = route.expected_replica_binding
    return _configured_owner_health_ready(**health_kwargs)


def verify_reddog_holoindex_owner_binding(
    *,
    repo_root: Path | str,
    expected_repo_head_sha: str,
    expected_generation_id: str,
    expected_receipt_digest: str,
    query_replica_route: QueryReplicaOwnerRoute | None = None,
) -> bool:
    """Verify that the active query owner serves one exact generation."""
    try:
        route, expected_binding = _required_owner_request(
            repo_root=repo_root,
            expected_repo_head_sha=expected_repo_head_sha,
            expected_generation_id=expected_generation_id,
            expected_receipt_digest=expected_receipt_digest,
            query_replica_route=query_replica_route,
        )
    except HoloQueryServiceSupervisorError:
        return False
    with _OWNER_LOCK:
        return _owner_binding_is_ready(expected_binding, route)


def restart_reddog_holoindex_owner(
    *,
    failed_handoff: tuple[str, str],
) -> tuple[str, str] | None:
    """Replace only the owned handoff that produced a poison/death signal."""
    global _OWNER_EXPECTED_BINDING, _OWNER_HANDOFF, _OWNER_REPLICA_ROUTE, _OWNER_SUPERVISOR
    with _OWNER_LOCK:
        supervisor = _OWNER_SUPERVISOR
        if supervisor is None or _OWNER_HANDOFF is None:
            return None
        if _OWNER_HANDOFF != failed_handoff:
            return _OWNER_HANDOFF if supervisor.is_ready else None
        repo_root = supervisor.repo_root
        runtime_root = getattr(supervisor, "runtime_root", None)
        expected = _OWNER_EXPECTED_BINDING
        replica_route = _OWNER_REPLICA_ROUTE
        supervisor.stop()
        _OWNER_SUPERVISOR = None
        _OWNER_HANDOFF = None
        _OWNER_EXPECTED_BINDING = ("", "", "", "")
        restarted = ensure_reddog_holoindex_owner(
            repo_root=repo_root,
            runtime_root=runtime_root,
            requested=True,
            expected_repo_head_sha=expected[0],
            expected_generation_id=expected[2],
            expected_receipt_digest=expected[3],
            query_replica_route=replica_route,
        )
        return _OWNER_HANDOFF if restarted.ready else None


_requested_binding = requested_owner_binding


def _stop_owned_owner() -> None:
    """Stop and erase only the supervisor owned by this host process."""
    global _OWNER_EXPECTED_BINDING, _OWNER_HANDOFF, _OWNER_REPLICA_ROUTE, _OWNER_SUPERVISOR
    supervisor = _OWNER_SUPERVISOR
    if supervisor is not None:
        supervisor.stop()
    _OWNER_SUPERVISOR = None
    _OWNER_HANDOFF = None
    _OWNER_EXPECTED_BINDING = ("", "", "", "")
    _OWNER_REPLICA_ROUTE = None


def _reuse_owned_owner(
    *,
    expected_binding: tuple[str, str, str, str],
    expected_runtime_root: Path,
    query_replica_route: QueryReplicaOwnerRoute | None,
) -> RedDogHoloIndexOwnerBootstrapResult | None:
    """Return REUSED only after the live owner matches and reproves binding."""
    global _OWNER_HANDOFF
    supervisor = _OWNER_SUPERVISOR
    if supervisor is None:
        return None
    if not replica_route_is_current(query_replica_route):
        _stop_owned_owner()
        return None
    runtime_matches = Path(
        getattr(supervisor, "runtime_root", supervisor.repo_root)
    ).resolve(strict=False) == expected_runtime_root
    matches = all(
        not requested_value or requested_value == stored_value
        for requested_value, stored_value in zip(
            expected_binding,
            _OWNER_EXPECTED_BINDING,
        )
    )
    replica_matches = query_replica_route == _OWNER_REPLICA_ROUTE
    if (
        not supervisor.is_ready
        or not runtime_matches
        or not matches
        or not replica_matches
        or _OWNER_HANDOFF is None
    ):
        _stop_owned_owner()
        return None
    try:
        query_replica_route.revalidate()
        _OWNER_HANDOFF = _validated_owner_handoff(
            supervisor,
            expected_repo_head_sha=expected_binding[0],
            expected_repo_root_digest=expected_binding[1],
            expected_generation_id=expected_binding[2],
            expected_receipt_digest=expected_binding[3],
            expected_replica_binding=query_replica_route.expected_replica_binding,
        )
    except Exception:
        _stop_owned_owner()
        return None
    return RedDogHoloIndexOwnerBootstrapResult(ready=True, status=OWNER_REUSED)


def _required_current_route(
    route: QueryReplicaOwnerRoute | None,
) -> QueryReplicaOwnerRoute:
    if route is None:
        raise HoloQueryServiceSupervisorError(QUERY_REPLICA_REQUIRED_ERROR)
    if not replica_route_is_current(route):
        raise HoloQueryServiceSupervisorError(QUERY_REPLICA_INVALID_ERROR)
    return route


def _start_owned_owner(
    *, repo_root: Path | str,
    runtime_root: Path | str | None,
    expected_binding: tuple[str, str, str, str],
    query_replica_route: QueryReplicaOwnerRoute | None,
) -> RedDogHoloIndexOwnerBootstrapResult:
    """Start, authenticate, and retain one process-private owner."""
    global _OWNER_EXPECTED_BINDING, _OWNER_HANDOFF, _OWNER_REPLICA_ROUTE, _OWNER_SUPERVISOR
    supervisor: HoloQueryServiceSupervisor | None = None
    try:
        route = _required_current_route(query_replica_route)
        ssd_path = route.canonical_ssd_path
        supervisor_args, replica_binding = owner_supervisor_configuration(
            repo_root=repo_root, runtime_root=runtime_root,
            canonical_ssd_path=ssd_path, route=route,
        )
        supervisor = HoloQueryServiceSupervisor(**supervisor_args)
        supervisor.start(**owner_start_binding_kwargs(expected_binding, replica_binding))
        handoff = _validated_owner_handoff(
            supervisor,
            expected_repo_head_sha=expected_binding[0],
            expected_repo_root_digest=expected_binding[1],
            expected_generation_id=expected_binding[2],
            expected_receipt_digest=expected_binding[3],
            expected_replica_binding=replica_binding,
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
    _OWNER_REPLICA_ROUTE = route
    return RedDogHoloIndexOwnerBootstrapResult(ready=True, status=OWNER_STARTED)


def _required_owner_request(
    *, repo_root: Path | str, expected_repo_head_sha: object,
    expected_generation_id: object, expected_receipt_digest: object,
    query_replica_route: QueryReplicaOwnerRoute | None,
) -> tuple[QueryReplicaOwnerRoute, tuple[str, str, str, str]]:
    requested = parse_exact_binding((
        expected_repo_head_sha, "", expected_generation_id,
        expected_receipt_digest,
    ), allow_empty_fields=True)
    if requested is None:
        raise HoloQueryServiceSupervisorError(BINDING_MISMATCH_ERROR)
    route = _required_current_route(query_replica_route)
    try:
        observed = _requested_binding(
            repo_root, requested[0], requested[2], requested[3],
        )
    except (TypeError, ValueError):
        raise HoloQueryServiceSupervisorError(BINDING_MISMATCH_ERROR) from None
    binding = parse_exact_binding(observed, allow_empty_fields=True)
    if binding is None:
        raise HoloQueryServiceSupervisorError(BINDING_MISMATCH_ERROR)
    return route, binding


def ensure_reddog_holoindex_owner(
    *, repo_root: Path | str,
    runtime_root: Path | str | None = None, requested: bool,
    expected_repo_head_sha: str = "", expected_generation_id: str = "",
    expected_receipt_digest: str = "", query_replica_route: QueryReplicaOwnerRoute | None = None,
) -> RedDogHoloIndexOwnerBootstrapResult:
    """Ensure one host owner exists only for Holo-dependent RedDog work."""
    if not requested:
        return RedDogHoloIndexOwnerBootstrapResult(False, OWNER_NOT_REQUESTED)
    try:
        route, expected_binding = _required_owner_request(
            repo_root=repo_root,
            expected_repo_head_sha=expected_repo_head_sha,
            expected_generation_id=expected_generation_id,
            expected_receipt_digest=expected_receipt_digest,
            query_replica_route=query_replica_route,
        )
    except HoloQueryServiceSupervisorError as exc:
        return _owner_failed(exc.code)
    expected_runtime_root = Path(runtime_root or repo_root).resolve(strict=False)
    with _OWNER_LOCK:
        reused = _reuse_owned_owner(
            expected_binding=expected_binding,
            expected_runtime_root=expected_runtime_root,
            query_replica_route=route,
        )
        if reused is not None:
            return reused
        configured_result = _configured_service_result(
            expected_repo_head_sha=expected_binding[0],
            expected_repo_root_digest=expected_binding[1],
            expected_generation_id=expected_binding[2],
            expected_receipt_digest=expected_binding[3],
            expected_replica_binding=route.expected_replica_binding,
        )
        if configured_result is not None:
            return configured_result
        if os.environ.get(AUTO_START_ENV, "1") == "0":
            return RedDogHoloIndexOwnerBootstrapResult(
                False, OWNER_AUTO_START_DISABLED, AUTO_START_DISABLED_ERROR,
            )
        return _start_owned_owner(
            repo_root=repo_root,
            runtime_root=runtime_root,
            expected_binding=expected_binding,
            query_replica_route=route,
        )


def cleanup_reddog_holoindex_owner(
    *,
    restore_environment: bool = True,
    expected_handoff: tuple[str, str] | None = None,
) -> bool:
    """Stop only the owner matching an optional process-private handoff."""
    del restore_environment  # Retained for compatibility; auto-start never edits env.
    global _OWNER_EXPECTED_BINDING, _OWNER_HANDOFF, _OWNER_REPLICA_ROUTE, _OWNER_SUPERVISOR
    with _OWNER_LOCK:
        if expected_handoff is not None and (
            _OWNER_HANDOFF is None
            or _OWNER_HANDOFF[0] != expected_handoff[0]
            or not hmac.compare_digest(_OWNER_HANDOFF[1], expected_handoff[1])
        ):
            return False
        supervisor, _OWNER_SUPERVISOR = _OWNER_SUPERVISOR, None
        _OWNER_HANDOFF = None
        _OWNER_EXPECTED_BINDING = ("", "", "", "")
        _OWNER_REPLICA_ROUTE = None
        if supervisor is not None:
            supervisor.stop()
        return True


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
