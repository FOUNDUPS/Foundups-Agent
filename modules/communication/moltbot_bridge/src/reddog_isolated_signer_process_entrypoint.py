"""One-shot isolated RedDog signer process entrypoint composition.

Slice: REDDOG_ISOLATED_SIGNER_PROCESS_ENTRYPOINT_PHASE1

This module composes the signer key-provider dry-run, kernel peer-credential
attestor, and one-request signer socket service. It does not parse environment
variables, spawn a process, bind sockets directly, read files, mutate the
repository, enqueue OpenClaw, dispatch Hermes, or re-index HoloIndex.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Optional, Protocol

from modules.communication.moltbot_bridge.src.reddog_isolated_signer_socket_service import (
    DEFAULT_SIGNER_SOCKET_SERVICE_MAX_RESPONSE_BYTES,
    DEFAULT_SIGNER_SOCKET_SERVICE_TIMEOUT_S,
    SIGNER_SOCKET_SERVICE_SERVED,
    IsolatedSignerSocketServiceResult,
    serve_reddog_isolated_signer_socket_once,
)
from modules.communication.moltbot_bridge.src.reddog_signer_key_provider_dryrun import (
    PROVIDER_MODE_TEST_ONLY_DRYRUN,
    SignerKeyProviderProfile,
    SignerKeyResolver,
    build_signer_backend_from_provider,
)
from modules.communication.moltbot_bridge.src.reddog_signer_socket_peer_credential_attestor import (
    KernelPeerCredentialAttestor,
    PeerCredentialPolicy,
)


SIGNER_PROCESS_ENTRYPOINT_SERVED = "SIGNER_PROCESS_ENTRYPOINT_SERVED"
SIGNER_PROCESS_ENTRYPOINT_REJECT = "SIGNER_PROCESS_ENTRYPOINT_REJECT"

FAIL_SIGNER_PROCESS_CONFIG_INVALID = "FAIL_SIGNER_PROCESS_CONFIG_INVALID"
FAIL_SIGNER_PROCESS_PEER_POLICY_INVALID = "FAIL_SIGNER_PROCESS_PEER_POLICY_INVALID"
FAIL_SIGNER_PROCESS_KEY_PROVIDER_REJECTED = "FAIL_SIGNER_PROCESS_KEY_PROVIDER_REJECTED"
FAIL_SIGNER_PROCESS_SERVICE_REJECTED = "FAIL_SIGNER_PROCESS_SERVICE_REJECTED"
FAIL_SIGNER_PROCESS_SERVICE_INVALID = "FAIL_SIGNER_PROCESS_SERVICE_INVALID"


class ServeSignerSocketOnce(Protocol):
    """Injected signer socket service callable."""

    def __call__(
        self,
        *,
        repo_root: Path | str,
        socket_path: Path | str | None,
        backend: Any,
        peer_attestor: Any,
        timeout_s: float,
        max_request_bytes: int,
        max_response_bytes: int,
        ready_callback: Optional[Callable[[], None]] = None,
    ) -> IsolatedSignerSocketServiceResult:
        """Serve one signer request."""


@dataclass(frozen=True)
class IsolatedSignerProcessEntryPointConfig:
    """Configuration supplied by the future isolated signer process owner."""

    repo_root: Path | str
    socket_path: Path | str | None
    key_provider_profile: SignerKeyProviderProfile
    peer_policy: PeerCredentialPolicy
    provider_mode: str = PROVIDER_MODE_TEST_ONLY_DRYRUN
    allow_test_only_key_material: bool = False
    permission_snapshot_fresh: bool = False
    timeout_s: float = DEFAULT_SIGNER_SOCKET_SERVICE_TIMEOUT_S
    max_request_bytes: int = 16384
    max_response_bytes: int = DEFAULT_SIGNER_SOCKET_SERVICE_MAX_RESPONSE_BYTES


@dataclass(frozen=True)
class IsolatedSignerProcessEntryPointResult:
    """Audit-safe entrypoint result."""

    accepted: bool
    status: str
    rejection_reasons: tuple[str, ...]
    key_provider_receipt: dict[str, Any]
    service_result: Optional[dict[str, Any]]
    no_env_parsed: bool = True
    no_process_spawned: bool = True
    no_socket_bound_directly: bool = True
    no_file_secret_loaded: bool = True
    no_repo_mutation_performed: bool = True
    no_openclaw_enqueue_performed: bool = True
    no_hermes_dispatch_performed: bool = True
    no_wre_queue_write_performed: bool = True
    no_holoindex_reindex_performed: bool = True
    no_secret_values_returned: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def run_reddog_isolated_signer_process_once(
    config: IsolatedSignerProcessEntryPointConfig,
    resolver: SignerKeyResolver,
    *,
    serve_once: ServeSignerSocketOnce = serve_reddog_isolated_signer_socket_once,
    ready_callback: Optional[Callable[[], None]] = None,
) -> IsolatedSignerProcessEntryPointResult:
    """Compose the one-shot signer service with injected dry-run dependencies."""

    if not isinstance(config, IsolatedSignerProcessEntryPointConfig):
        return _reject(FAIL_SIGNER_PROCESS_CONFIG_INVALID)
    if not _peer_policy_valid(config.peer_policy):
        return _reject(FAIL_SIGNER_PROCESS_PEER_POLICY_INVALID)

    key_result = build_signer_backend_from_provider(
        config.key_provider_profile,
        resolver,
        provider_mode=config.provider_mode,
        allow_test_only_key_material=config.allow_test_only_key_material,
        permission_snapshot_fresh=config.permission_snapshot_fresh,
    )
    key_receipt = key_result.to_receipt()
    if not key_result.ok or key_result.backend is None:
        return _reject(FAIL_SIGNER_PROCESS_KEY_PROVIDER_REJECTED, key_provider_receipt=key_receipt)

    try:
        service_result = serve_once(
            repo_root=config.repo_root,
            socket_path=config.socket_path,
            backend=key_result.backend,
            peer_attestor=KernelPeerCredentialAttestor(config.peer_policy),
            timeout_s=config.timeout_s,
            max_request_bytes=config.max_request_bytes,
            max_response_bytes=config.max_response_bytes,
            ready_callback=ready_callback,
        )
    except Exception:
        return _reject(FAIL_SIGNER_PROCESS_SERVICE_REJECTED, key_provider_receipt=key_receipt)
    if not isinstance(service_result, IsolatedSignerSocketServiceResult):
        return _reject(FAIL_SIGNER_PROCESS_SERVICE_INVALID, key_provider_receipt=key_receipt)
    service_receipt = service_result.to_dict()
    if service_result.accepted is not True or service_result.status != SIGNER_SOCKET_SERVICE_SERVED:
        return _reject(
            FAIL_SIGNER_PROCESS_SERVICE_REJECTED,
            key_provider_receipt=key_receipt,
            service_result=service_receipt,
        )

    return IsolatedSignerProcessEntryPointResult(
        accepted=True,
        status=SIGNER_PROCESS_ENTRYPOINT_SERVED,
        rejection_reasons=(),
        key_provider_receipt=key_receipt,
        service_result=service_receipt,
    )


def _reject(
    *reasons: str,
    key_provider_receipt: Optional[dict[str, Any]] = None,
    service_result: Optional[dict[str, Any]] = None,
) -> IsolatedSignerProcessEntryPointResult:
    return IsolatedSignerProcessEntryPointResult(
        accepted=False,
        status=SIGNER_PROCESS_ENTRYPOINT_REJECT,
        rejection_reasons=tuple(str(reason) for reason in reasons if reason),
        key_provider_receipt=key_provider_receipt or {},
        service_result=service_result,
    )


def _peer_policy_valid(policy: PeerCredentialPolicy) -> bool:
    if not isinstance(policy, PeerCredentialPolicy) or not policy.uid_to_principal:
        return False
    for uid, principal in policy.uid_to_principal.items():
        if not isinstance(uid, int) or uid < 0:
            return False
        if not isinstance(principal, str) or not principal or not _is_ascii(principal):
            return False
    return all(isinstance(gid, int) and gid >= 0 for gid in policy.allowed_gids)


def _is_ascii(value: str) -> bool:
    return all(ord(char) < 128 for char in value)


__all__ = [
    "FAIL_SIGNER_PROCESS_CONFIG_INVALID",
    "FAIL_SIGNER_PROCESS_KEY_PROVIDER_REJECTED",
    "FAIL_SIGNER_PROCESS_PEER_POLICY_INVALID",
    "FAIL_SIGNER_PROCESS_SERVICE_INVALID",
    "FAIL_SIGNER_PROCESS_SERVICE_REJECTED",
    "IsolatedSignerProcessEntryPointConfig",
    "IsolatedSignerProcessEntryPointResult",
    "SIGNER_PROCESS_ENTRYPOINT_REJECT",
    "SIGNER_PROCESS_ENTRYPOINT_SERVED",
    "ServeSignerSocketOnce",
    "run_reddog_isolated_signer_process_once",
]
