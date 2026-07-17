"""Runtime wiring for a bounded isolated RedDog signer socket service.

Slice: REDDOG_SIGNER_SOCKET_SERVICE_RUNTIME_WIRING_PHASE1

This module composes the existing signer key-provider boundary, kernel peer
credential attestor, and bounded signer socket service. It is intentionally
dependency-injected: no environment parsing, file IO, process spawning, repo
mutation, OpenClaw/Hermes dispatch, PR publication, reward settlement, or
HoloIndex re-indexing happens here.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Optional

from modules.communication.moltbot_bridge.src.reddog_isolated_signer_socket_protocol import (
    IsolatedSignerBackend,
    SignerPeerAttestation,
)
from modules.communication.moltbot_bridge.src.reddog_isolated_signer_socket_resident_service import (
    DEFAULT_SIGNER_SOCKET_RESIDENT_MAX_REQUESTS,
    SIGNER_SOCKET_RESIDENT_SERVICE_SERVED,
    IsolatedSignerSocketResidentServiceResult,
    serve_reddog_isolated_signer_socket_bounded,
)
from modules.communication.moltbot_bridge.src.reddog_isolated_signer_socket_protocol import (
    DEFAULT_SIGNER_SOCKET_MAX_REQUEST_BYTES,
)
from modules.communication.moltbot_bridge.src.reddog_isolated_signer_socket_service import (
    DEFAULT_SIGNER_SOCKET_SERVICE_MAX_RESPONSE_BYTES,
    DEFAULT_SIGNER_SOCKET_SERVICE_TIMEOUT_S,
)
from modules.communication.moltbot_bridge.src.reddog_signer_key_provider_dryrun import (
    PROVIDER_MODE_TEST_ONLY_DRYRUN,
    SignerKeyProviderProfile,
    SignerKeyResolver,
    build_signer_backend_from_provider,
)
from modules.communication.moltbot_bridge.src.reddog_signer_delegated_authority_runtime import (
    RuntimeRejectCode,
    SigningRequest,
    SigningResponse,
)
from modules.communication.moltbot_bridge.src.reddog_signer_socket_peer_credential_attestor import (
    KernelPeerCredentialAttestor,
    PeerCredentialPolicy,
)


SIGNER_SOCKET_RUNTIME_WIRING_SERVED = "SIGNER_SOCKET_RUNTIME_WIRING_SERVED"
SIGNER_SOCKET_RUNTIME_WIRING_REJECT = "SIGNER_SOCKET_RUNTIME_WIRING_REJECT"

FAIL_SIGNER_RUNTIME_CONFIG_INVALID = "FAIL_SIGNER_RUNTIME_CONFIG_INVALID"
FAIL_SIGNER_RUNTIME_PROFILE_INVALID = "FAIL_SIGNER_RUNTIME_PROFILE_INVALID"
FAIL_SIGNER_RUNTIME_PEER_POLICY_INVALID = "FAIL_SIGNER_RUNTIME_PEER_POLICY_INVALID"
FAIL_SIGNER_RUNTIME_KEY_PROVIDER_REJECTED = "FAIL_SIGNER_RUNTIME_KEY_PROVIDER_REJECTED"
FAIL_SIGNER_RUNTIME_KEY_PROVIDER_DUPLICATE = "FAIL_SIGNER_RUNTIME_KEY_PROVIDER_DUPLICATE"
FAIL_SIGNER_RUNTIME_KEY_PROVIDER_COUNT_INVALID = "FAIL_SIGNER_RUNTIME_KEY_PROVIDER_COUNT_INVALID"
FAIL_SIGNER_RUNTIME_SERVICE_REJECTED = "FAIL_SIGNER_RUNTIME_SERVICE_REJECTED"
FAIL_SIGNER_RUNTIME_SERVICE_INVALID = "FAIL_SIGNER_RUNTIME_SERVICE_INVALID"


ServeSignerSocketBounded = Callable[..., IsolatedSignerSocketResidentServiceResult]


@dataclass(frozen=True)
class SignerSocketServiceRuntimeWiringConfig:
    """Signer-owned runtime service wiring configuration."""

    repo_root: Path | str
    socket_path: Path | str | None
    peer_policy: PeerCredentialPolicy | Mapping[str, Any]
    key_provider_profile: SignerKeyProviderProfile | Mapping[str, Any] | None = None
    provider_mode: str = PROVIDER_MODE_TEST_ONLY_DRYRUN
    allow_test_only_key_material: bool = False
    permission_snapshot_fresh: bool = False
    max_requests: int = DEFAULT_SIGNER_SOCKET_RESIDENT_MAX_REQUESTS
    timeout_s: float = DEFAULT_SIGNER_SOCKET_SERVICE_TIMEOUT_S
    max_request_bytes: int = DEFAULT_SIGNER_SOCKET_MAX_REQUEST_BYTES
    max_response_bytes: int = DEFAULT_SIGNER_SOCKET_SERVICE_MAX_RESPONSE_BYTES
    key_provider_profiles: tuple[SignerKeyProviderProfile | Mapping[str, Any], ...] = ()


@dataclass(frozen=True)
class SignerSocketServiceRuntimeWiringResult:
    """Audit-safe result for signer socket service runtime wiring."""

    accepted: bool
    status: str
    rejection_reasons: tuple[str, ...]
    key_provider_receipt: dict[str, Any]
    service_result: Optional[dict[str, Any]]
    max_requests: int = 0
    no_env_parsed: bool = True
    no_file_io_performed: bool = True
    no_process_spawned: bool = True
    no_repo_mutation_performed: bool = True
    no_openclaw_enqueue_performed: bool = True
    no_hermes_dispatch_performed: bool = True
    no_pr_created: bool = True
    no_reward_settlement_performed: bool = True
    no_holoindex_reindex_performed: bool = True
    no_secret_values_returned: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def run_reddog_signer_socket_service_runtime_wiring(
    config: SignerSocketServiceRuntimeWiringConfig,
    resolver: SignerKeyResolver,
    *,
    serve_bounded: ServeSignerSocketBounded = serve_reddog_isolated_signer_socket_bounded,
    ready_callback: Optional[Callable[[], None]] = None,
) -> SignerSocketServiceRuntimeWiringResult:
    """Build a signer backend and serve a bounded signer socket service."""

    if not isinstance(config, SignerSocketServiceRuntimeWiringConfig):
        return _reject(FAIL_SIGNER_RUNTIME_CONFIG_INVALID)
    profiles, profile_reasons = _profiles(config)
    if profile_reasons:
        return _reject(*profile_reasons)
    policy = _peer_policy(config.peer_policy)
    if policy is None or not _peer_policy_valid(policy):
        return _reject(FAIL_SIGNER_RUNTIME_PEER_POLICY_INVALID)

    backend, key_receipt, key_reasons = _build_backend(
        profiles,
        resolver,
        provider_mode=config.provider_mode,
        allow_test_only_key_material=config.allow_test_only_key_material,
        permission_snapshot_fresh=config.permission_snapshot_fresh,
    )
    if key_reasons:
        return _reject(*key_reasons, key_provider_receipt=key_receipt, max_requests=config.max_requests)

    try:
        service = serve_bounded(
            repo_root=config.repo_root,
            socket_path=config.socket_path,
            backend=backend,
            peer_attestor=KernelPeerCredentialAttestor(policy),
            max_requests=config.max_requests,
            timeout_s=config.timeout_s,
            max_request_bytes=config.max_request_bytes,
            max_response_bytes=config.max_response_bytes,
            ready_callback=ready_callback,
        )
    except Exception:
        return _reject(
            FAIL_SIGNER_RUNTIME_SERVICE_REJECTED,
            key_provider_receipt=key_receipt,
            max_requests=config.max_requests,
        )
    if not isinstance(service, IsolatedSignerSocketResidentServiceResult):
        return _reject(
            FAIL_SIGNER_RUNTIME_SERVICE_INVALID,
            key_provider_receipt=key_receipt,
            max_requests=config.max_requests,
        )
    service_receipt = service.to_dict()
    if service.accepted is not True or service.status != SIGNER_SOCKET_RESIDENT_SERVICE_SERVED:
        return _reject(
            FAIL_SIGNER_RUNTIME_SERVICE_REJECTED,
            key_provider_receipt=key_receipt,
            service_result=service_receipt,
            max_requests=config.max_requests,
        )

    return SignerSocketServiceRuntimeWiringResult(
        accepted=True,
        status=SIGNER_SOCKET_RUNTIME_WIRING_SERVED,
        rejection_reasons=(),
        key_provider_receipt=key_receipt,
        service_result=service_receipt,
        max_requests=config.max_requests,
    )


@dataclass(frozen=True)
class _RoutingSignerBackend(IsolatedSignerBackend):
    backends: Mapping[str, IsolatedSignerBackend]

    def sign(self, request: SigningRequest, peer: SignerPeerAttestation) -> SigningResponse:
        backend = self.backends.get(request.signer_public_key)
        if backend is None:
            return SigningResponse(
                accepted=False,
                rejection_code=RuntimeRejectCode.SIGNER_NOT_CONFIGURED,
                no_secret_material_returned=True,
            )
        return backend.sign(request, peer)


def _profiles(
    config: SignerSocketServiceRuntimeWiringConfig,
) -> tuple[list[SignerKeyProviderProfile], tuple[str, ...]]:
    if config.key_provider_profile is not None and config.key_provider_profiles:
        return [], (FAIL_SIGNER_RUNTIME_PROFILE_INVALID,)
    raw_profiles: tuple[SignerKeyProviderProfile | Mapping[str, Any], ...]
    if config.key_provider_profiles:
        raw_profiles = tuple(config.key_provider_profiles)
    elif config.key_provider_profile is not None:
        raw_profiles = (config.key_provider_profile,)
    else:
        return [], (FAIL_SIGNER_RUNTIME_KEY_PROVIDER_COUNT_INVALID,)
    if len(raw_profiles) < 1 or len(raw_profiles) > 8:
        return [], (FAIL_SIGNER_RUNTIME_KEY_PROVIDER_COUNT_INVALID,)

    profiles: list[SignerKeyProviderProfile] = []
    for raw in raw_profiles:
        profile = _profile(raw)
        if profile is None:
            return [], (FAIL_SIGNER_RUNTIME_PROFILE_INVALID,)
        profiles.append(profile)
    return profiles, ()


def _build_backend(
    profiles: list[SignerKeyProviderProfile],
    resolver: SignerKeyResolver,
    *,
    provider_mode: str,
    allow_test_only_key_material: bool,
    permission_snapshot_fresh: bool,
) -> tuple[Optional[IsolatedSignerBackend], dict[str, Any], tuple[str, ...]]:
    receipts: list[dict[str, Any]] = []
    backends: dict[str, IsolatedSignerBackend] = {}
    for profile in profiles:
        key_result = build_signer_backend_from_provider(
            profile,
            resolver,
            provider_mode=provider_mode,
            allow_test_only_key_material=allow_test_only_key_material,
            permission_snapshot_fresh=permission_snapshot_fresh,
        )
        receipt = key_result.to_receipt()
        receipts.append(receipt)
        if not key_result.ok or key_result.backend is None:
            return None, _key_provider_receipt(False, receipts), (
                FAIL_SIGNER_RUNTIME_KEY_PROVIDER_REJECTED,
            )
        public_key = str(key_result.public_key or "")
        if public_key in backends:
            return None, _key_provider_receipt(False, receipts), (
                FAIL_SIGNER_RUNTIME_KEY_PROVIDER_DUPLICATE,
            )
        backends[public_key] = key_result.backend

    if len(backends) == 1:
        backend = next(iter(backends.values()))
    else:
        backend = _RoutingSignerBackend(backends)
    return backend, _key_provider_receipt(True, receipts), ()


def _key_provider_receipt(ok: bool, receipts: list[dict[str, Any]]) -> dict[str, Any]:
    payload: dict[str, Any] = dict(receipts[0]) if len(receipts) == 1 else {"ok": ok}
    payload["ok"] = ok
    payload["profile_count"] = len(receipts)
    payload["profile_receipts"] = receipts
    payload["public_keys"] = [
        str(receipt.get("public_key") or "")
        for receipt in receipts
        if receipt.get("public_key")
    ]
    payload["secret_values_returned"] = False
    return payload


def _profile(value: SignerKeyProviderProfile | Mapping[str, Any]) -> SignerKeyProviderProfile | None:
    if isinstance(value, SignerKeyProviderProfile):
        return value
    if not isinstance(value, Mapping):
        return None
    try:
        return SignerKeyProviderProfile(**dict(value))
    except Exception:
        return None


def _peer_policy(value: PeerCredentialPolicy | Mapping[str, Any]) -> PeerCredentialPolicy | None:
    if isinstance(value, PeerCredentialPolicy):
        return value
    if not isinstance(value, Mapping):
        return None
    try:
        uid_to_principal = {
            int(uid): str(principal)
            for uid, principal in dict(value.get("uid_to_principal") or {}).items()
        }
        allowed_gids = tuple(int(gid) for gid in tuple(value.get("allowed_gids") or ()))
        return PeerCredentialPolicy(
            uid_to_principal=uid_to_principal,
            allowed_gids=allowed_gids,
            transport=str(value.get("transport") or "unix_socket"),
            credential_source_prefix=str(
                value.get("credential_source_prefix") or "kernel_peer_credential"
            ),
        )
    except Exception:
        return None


def _peer_policy_valid(policy: PeerCredentialPolicy) -> bool:
    if not isinstance(policy, PeerCredentialPolicy) or not policy.uid_to_principal:
        return False
    for uid, principal in policy.uid_to_principal.items():
        if not isinstance(uid, int) or uid < 0:
            return False
        if not isinstance(principal, str) or not principal or not _ascii(principal):
            return False
    if not _ascii(policy.transport) or not _ascii(policy.credential_source_prefix):
        return False
    return all(isinstance(gid, int) and gid >= 0 for gid in policy.allowed_gids)


def _ascii(value: str) -> bool:
    return all(ord(char) < 128 for char in value)


def _reject(
    *reasons: str,
    key_provider_receipt: Optional[dict[str, Any]] = None,
    service_result: Optional[dict[str, Any]] = None,
    max_requests: int = 0,
) -> SignerSocketServiceRuntimeWiringResult:
    return SignerSocketServiceRuntimeWiringResult(
        accepted=False,
        status=SIGNER_SOCKET_RUNTIME_WIRING_REJECT,
        rejection_reasons=tuple(dict.fromkeys(reason for reason in reasons if reason)),
        key_provider_receipt=key_provider_receipt or {},
        service_result=service_result,
        max_requests=max_requests,
    )


__all__ = [
    "FAIL_SIGNER_RUNTIME_CONFIG_INVALID",
    "FAIL_SIGNER_RUNTIME_KEY_PROVIDER_COUNT_INVALID",
    "FAIL_SIGNER_RUNTIME_KEY_PROVIDER_DUPLICATE",
    "FAIL_SIGNER_RUNTIME_KEY_PROVIDER_REJECTED",
    "FAIL_SIGNER_RUNTIME_PEER_POLICY_INVALID",
    "FAIL_SIGNER_RUNTIME_PROFILE_INVALID",
    "FAIL_SIGNER_RUNTIME_SERVICE_INVALID",
    "FAIL_SIGNER_RUNTIME_SERVICE_REJECTED",
    "SIGNER_SOCKET_RUNTIME_WIRING_REJECT",
    "SIGNER_SOCKET_RUNTIME_WIRING_SERVED",
    "SignerSocketServiceRuntimeWiringConfig",
    "SignerSocketServiceRuntimeWiringResult",
    "run_reddog_signer_socket_service_runtime_wiring",
]
