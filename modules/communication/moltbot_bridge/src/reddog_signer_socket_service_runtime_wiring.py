"""Runtime wiring for a bounded isolated RedDog signer socket service.

Slice: REDDOG_SIGNER_SOCKET_SERVICE_RUNTIME_WIRING_PHASE1

This module composes the existing signer key-provider boundary, kernel peer
credential attestor, and bounded signer socket service. It does not parse the
environment, spawn processes, mutate repository files, dispatch OpenClaw or
Hermes, publish PRs, settle rewards, or re-index HoloIndex. Injected resolvers
and replay authorities may perform signer-runtime I/O; proposal mode also
persists the canonical signer-owned nonce state.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from dataclasses import asdict, dataclass, replace
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
    validate_resident_signer_socket_limits,
)
from modules.communication.moltbot_bridge.src.reddog_isolated_signer_socket_protocol import (
    DEFAULT_SIGNER_SOCKET_MAX_REQUEST_BYTES,
)
from modules.communication.moltbot_bridge.src.reddog_isolated_signer_socket_service import (
    DEFAULT_SIGNER_SOCKET_SERVICE_MAX_RESPONSE_BYTES,
    DEFAULT_SIGNER_SOCKET_SERVICE_TIMEOUT_S,
)
from modules.communication.moltbot_bridge.src.reddog_architect_proposal_authenticity import (
    ArchitectProposalPolicyAuthorization,
    ArchitectProposalSignerPolicy,
    ProposalAuthenticityNonceStore,
    architect_proposal_replay_store_binding_digest,
    architect_proposal_signer_instance_id,
    rehydrate_architect_proposal_signer_policy,
    verify_architect_proposal_policy_authorization,
)
from modules.communication.moltbot_bridge.src.reddog_signer_key_provider_dryrun import (
    PROVIDER_MODE_TEST_ONLY_DRYRUN,
    PROVIDER_MODE_WSP71_PERMISSIONED,
    SignerKeyProviderProfile,
    SignerKeyResolver,
    _build_proposal_signer_backend_from_verified_runtime,
    build_signer_backend_from_provider,
    validate_signer_key_provider_profile,
)
from modules.communication.moltbot_bridge.src.reddog_signer_delegated_authority_runtime import (
    RuntimeRejectCode,
    SigningRequest,
    SigningResponse,
    public_key_fingerprint,
)
from modules.communication.moltbot_bridge.src.reddog_ed25519_signer_backend import (
    ControlLoopAuthorityPolicy,
    Ed25519SignerBackend,
)
from modules.communication.moltbot_bridge.src.foundup_memex_verified_outcome_signing import (
    VerifiedOutcomeSigningAuthority,
    VerifiedOutcomeSignerPolicy,
)
from modules.communication.moltbot_bridge.src.foundup_verified_outcome_runtime_binding import (
    verified_outcome_authority_matches_runtime,
)
from modules.communication.moltbot_bridge.src.reddog_signer_mutual_peer_handshake import (
    SignerPeerInstanceBinding,
)
from modules.communication.moltbot_bridge.src.reddog_signer_control_loop_anchor import (
    ControlLoopAnchorStore,
)
from modules.communication.moltbot_bridge.src.reddog_authority_runtime_store import PrincipalAuthorityResolver
from modules.communication.moltbot_bridge.src.reddog_conversation_scope_signing import ConversationScopeSignerPolicy
from modules.communication.moltbot_bridge.src.reddog_signer_socket_service_authority_policy_runtime import (
    FAIL_CONTROL_ANCHOR,
    control_loop_anchor_store as _control_loop_anchor_store,
    control_loop_authority_policy as _control_loop_authority_policy,
    verified_outcome_signer_policy as _verified_outcome_signer_policy,
)
from modules.communication.moltbot_bridge.src.reddog_signer_socket_service_policy_runtime import (
    ConversationScopeRuntimeBinding,
    FAIL_CONVERSATION_AUTH,
    bind_conversation_scope_backend,
    build_conversation_scope_runtime_binding,
    conversation_scope_config_reasons,
    conversation_scope_security_context,
)
from modules.communication.moltbot_bridge.src.reddog_signer_socket_peer_credential_attestor import (
    KernelPeerCredentialAttestor,
    PeerCredentialPolicy,
    rehydrate_peer_credential_policy,
)
from modules.communication.moltbot_bridge.src.reddog_proposal_authenticity_nonce_store import (
    ProposalReplayHighWaterStore,
)
from modules.communication.moltbot_bridge.src.reddog_work_order_signature_verifier import (
    FailClosedPrincipalKeyResolver,
    PrincipalKeyResolver,
)
from modules.infrastructure.shared_utilities.runtime_artifact_safety import (
    validate_runtime_artifact_path,
    validate_runtime_root_path,
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
FAIL_SIGNER_RUNTIME_CONTROL_ANCHOR_INVALID = FAIL_CONTROL_ANCHOR
FAIL_SIGNER_RUNTIME_CONVERSATION_AUTH_INVALID = FAIL_CONVERSATION_AUTH
FAIL_SIGNER_RUNTIME_PROPOSAL_POLICY_INVALID = (
    "FAIL_SIGNER_RUNTIME_PROPOSAL_POLICY_INVALID"
)
FAIL_SIGNER_RUNTIME_PROPOSAL_POLICY_AUTHORIZATION_INVALID = (
    "FAIL_SIGNER_RUNTIME_PROPOSAL_POLICY_AUTHORIZATION_INVALID"
)
FAIL_SIGNER_RUNTIME_PROPOSAL_NONCE_STORE_INVALID = (
    "FAIL_SIGNER_RUNTIME_PROPOSAL_NONCE_STORE_INVALID"
)
REDDOG_WORK_AUTHORITY_SIGNER_AGENT_ID = "signer:reddog"
REDDOG_WORK_AUTHORITY_SIGNER_PROFILE_ID = "reddog-work-authority"
PRINCIPAL_IDENTITY_SIGNER_AGENT_ID = "signer:principal"
PRINCIPAL_IDENTITY_SIGNER_PROFILE_ID = "principal-identity"


ServeSignerSocketBounded = Callable[..., IsolatedSignerSocketResidentServiceResult]


@dataclass(frozen=True)
class SignerSocketServiceRuntimeWiringConfig:
    """Signer-owned runtime service wiring configuration."""

    repo_root: Path | str
    runtime_root: Path | str
    signer_runtime_root: Path | str
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
    control_loop_anchor_path: Path | str | None = None
    control_loop_authority_policy: ControlLoopAuthorityPolicy | Mapping[str, Any] | None = None
    conversation_scope_anchor_path: Path | str | None = None
    conversation_scope_signer_policy: ConversationScopeSignerPolicy | Mapping[str, Any] | None = None
    verified_outcome_signer_policy: VerifiedOutcomeSignerPolicy | Mapping[str, Any] | None = None
    proposal_authority_policy: ArchitectProposalSignerPolicy | Mapping[str, Any] | None = None
    proposal_policy_authorization: ArchitectProposalPolicyAuthorization | Mapping[str, Any] | None = None
    proposal_nonce_store_path: Path | str | None = None
    proposal_replay_high_water_store_id: str | None = None
    proposal_replay_high_water_durability_receipt_id: str | None = None
    proposal_security_context_digest: str | None = None
    signer_peer_instance_binding: SignerPeerInstanceBinding | None = None
    system_service_owner_config_id: str | None = None


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


def architect_proposal_security_context_digest(
    config: SignerSocketServiceRuntimeWiringConfig,
) -> str:
    """Digest the normalized signer configuration excluding its authorization."""

    if not isinstance(config, SignerSocketServiceRuntimeWiringConfig):
        raise ValueError("architect_proposal_security_context_invalid")
    profiles, profile_reasons = _profiles(config)
    peer_policy = _peer_policy(config.peer_policy)
    proposal_policy = _proposal_authority_policy(config.proposal_authority_policy)
    control_policy = _control_loop_authority_policy(config.control_loop_authority_policy)
    outcome_policy = _verified_outcome_signer_policy(config.verified_outcome_signer_policy)
    if (
        profile_reasons
        or peer_policy is None
        or proposal_policy is None
    ):
        raise ValueError("architect_proposal_security_context_invalid")
    repo_root = Path(config.repo_root).resolve()
    runtime_root = validate_runtime_root_path(
        config.runtime_root,
        repo_root=repo_root,
    )
    signer_root = validate_runtime_root_path(
        config.signer_runtime_root,
        repo_root=repo_root,
    )
    socket_path = validate_runtime_artifact_path(
        config.socket_path,
        repo_root=repo_root,
        allowed_root=runtime_root,
    )
    nonce_path = validate_runtime_artifact_path(
        config.proposal_nonce_store_path,
        repo_root=repo_root,
        allowed_root=signer_root,
    )
    high_water_store_id = str(
        config.proposal_replay_high_water_store_id or ""
    ).strip()
    durability_receipt_id = str(
        config.proposal_replay_high_water_durability_receipt_id or ""
    ).strip()
    if (
        not high_water_store_id
        or not _ascii(high_water_store_id)
        or not _is_sha256_digest(durability_receipt_id)
    ):
        raise ValueError("architect_proposal_security_context_invalid")
    control_anchor_path = validate_runtime_artifact_path(
        config.control_loop_anchor_path,
        repo_root=repo_root,
        allowed_root=signer_root,
    )
    conversation_context = conversation_scope_security_context(
        config, repo_root, signer_root
    )
    payload = {
        "schema_version": "reddog_architect_proposal_security_context.v1",
        "repo_root": str(repo_root),
        "runtime_root": str(runtime_root),
        "signer_runtime_root": str(signer_root),
        "socket_path": str(socket_path),
        "provider_mode": str(config.provider_mode),
        "allow_test_only_key_material": bool(
            config.allow_test_only_key_material
        ),
        "permission_snapshot_fresh": bool(
            config.permission_snapshot_fresh
        ),
        "max_requests": int(config.max_requests),
        "timeout_s": float(config.timeout_s),
        "max_request_bytes": int(config.max_request_bytes),
        "max_response_bytes": int(config.max_response_bytes),
        "peer_policy": {
            "uid_to_principal": {
                str(uid): principal
                for uid, principal in sorted(
                    peer_policy.uid_to_principal.items()
                )
            },
            "allowed_gids": sorted(peer_policy.allowed_gids),
            "transport": peer_policy.transport,
            "credential_source_prefix": (
                peer_policy.credential_source_prefix
            ),
        },
        "key_provider_profiles": [
            asdict(profile) for profile in profiles
        ],
        "control_loop_anchor_path": str(control_anchor_path),
        "control_loop_authority_policy": (
            asdict(control_policy) if control_policy is not None else None
        ),
        "conversation_scope_anchor_path": conversation_context["anchor_path"],
        "conversation_scope_signer_policy": conversation_context["policy"],
        "verified_outcome_signer_policy": (
            asdict(outcome_policy) if outcome_policy is not None else None
        ),
        "proposal_authority_policy": {
            "expected_payload": (
                proposal_policy.expected_payload.to_dict()
            ),
            "max_ttl_seconds": int(proposal_policy.max_ttl_seconds),
        },
        "proposal_nonce_store_path": str(nonce_path),
        "proposal_replay_high_water_store_id": high_water_store_id,
        "proposal_replay_high_water_durability_receipt_id": (
            durability_receipt_id
        ),
    }
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def run_reddog_signer_socket_service_runtime_wiring(
    config: SignerSocketServiceRuntimeWiringConfig,
    resolver: SignerKeyResolver,
    *,
    serve_bounded: ServeSignerSocketBounded = serve_reddog_isolated_signer_socket_bounded,
    ready_callback: Optional[Callable[[], None]] = None,
    principal_key_resolver: PrincipalKeyResolver | None = None,
    proposal_replay_high_water_store: ProposalReplayHighWaterStore | None = None,
    verified_outcome_signing_authority: VerifiedOutcomeSigningAuthority | None = None,
    conversation_scope_principal_resolver: PrincipalAuthorityResolver | None = None,
) -> SignerSocketServiceRuntimeWiringResult:
    """Build a signer backend and serve a bounded signer socket service."""

    config_reasons = validate_signer_socket_service_runtime_config(config)
    if config_reasons:
        return _reject(*config_reasons)
    profiles, profile_reasons = _profiles(config)
    if profile_reasons:
        return _reject(*profile_reasons)
    policy = _peer_policy(config.peer_policy)
    if policy is None:
        return _reject(FAIL_SIGNER_RUNTIME_PEER_POLICY_INVALID)
    anchor_store, anchor_reasons = _control_loop_anchor_store(config)
    if anchor_reasons:
        return _reject(*anchor_reasons)
    control_authority_policy = _control_loop_authority_policy(config.control_loop_authority_policy)
    outcome_policy = _verified_outcome_signer_policy(config.verified_outcome_signer_policy)
    conversation_binding, conversation_reasons = (
        build_conversation_scope_runtime_binding(config, conversation_scope_principal_resolver)
    )
    if conversation_reasons:
        return _reject(*conversation_reasons)
    if outcome_policy is not None and not verified_outcome_authority_matches_runtime(
        outcome_policy,
        verified_outcome_signing_authority,
        expected_owner_config_id=config.system_service_owner_config_id,
        signer_peer_instance_binding=config.signer_peer_instance_binding,
    ):
        return _reject(
            FAIL_SIGNER_RUNTIME_CONFIG_INVALID,
            injected_dependency_effects_unobserved=(outcome_policy is not None),
        )
    proposal_policy = _proposal_authority_policy(
        config.proposal_authority_policy
    )
    proposal_authorization = _proposal_policy_authorization(
        config,
        profiles=profiles,
        proposal_policy=proposal_policy,
        principal_key_resolver=(
            principal_key_resolver
            or FailClosedPrincipalKeyResolver()
        ),
        require_trusted_principal=True,
    )
    if proposal_policy is not None and proposal_authorization is None:
        return _reject(
            FAIL_SIGNER_RUNTIME_PROPOSAL_POLICY_AUTHORIZATION_INVALID,
            injected_dependency_effects_unobserved=True,
        )
    (
        proposal_nonce_store_path,
        proposal_replay_high_water_store_id,
        proposal_store_reasons,
    ) = _proposal_nonce_store(
        config,
        proposal_policy=proposal_policy,
    )
    if proposal_store_reasons:
        return _reject(
            *proposal_store_reasons,
            injected_dependency_effects_unobserved=(
                proposal_policy is not None
            ),
        )
    if proposal_policy is not None:
        try:
            high_water_authority_valid = bool(
                isinstance(
                    proposal_replay_high_water_store,
                    ProposalReplayHighWaterStore,
                )
                and hmac.compare_digest(
                    proposal_replay_high_water_store.store_id,
                    str(proposal_replay_high_water_store_id),
                )
                and (
                    config.provider_mode
                    != PROVIDER_MODE_WSP71_PERMISSIONED
                    or (
                        proposal_replay_high_water_store.durable is True
                        and _is_sha256_digest(
                            proposal_replay_high_water_store
                            .durability_receipt_id
                        )
                        and hmac.compare_digest(
                            str(
                                proposal_replay_high_water_store
                                .durability_receipt_id
                            ),
                            str(
                                config
                                .proposal_replay_high_water_durability_receipt_id
                            ),
                        )
                    )
                )
            )
        except Exception:
            high_water_authority_valid = False
        if not high_water_authority_valid:
            return _reject(
                FAIL_SIGNER_RUNTIME_PROPOSAL_NONCE_STORE_INVALID,
                injected_dependency_effects_unobserved=True,
            )
    backend, proposal_nonce_store, key_receipt, key_reasons = _build_backend(
        profiles,
        resolver,
        provider_mode=config.provider_mode,
        allow_test_only_key_material=config.allow_test_only_key_material,
        permission_snapshot_fresh=config.permission_snapshot_fresh,
        control_loop_anchor_store=anchor_store,
        control_loop_authority_policy=control_authority_policy,
        verified_outcome_signer_policy=outcome_policy,
        verified_outcome_signing_authority=verified_outcome_signing_authority if outcome_policy else None,
        conversation_scope_binding=conversation_binding,
        proposal_authority_policy=proposal_policy,
        proposal_policy_authorization=proposal_authorization,
        proposal_nonce_store_path=proposal_nonce_store_path,
        proposal_replay_high_water_store=(
            proposal_replay_high_water_store
        ),
        proposal_replay_high_water_store_id=(
            proposal_replay_high_water_store_id
        ),
        proposal_replay_high_water_durability_receipt_id=str(
            config.proposal_replay_high_water_durability_receipt_id or ""
        ),
        repo_root=Path(config.repo_root).resolve(),
        signer_runtime_root=validate_runtime_root_path(
            config.signer_runtime_root,
            repo_root=Path(config.repo_root).resolve(),
        ),
        signer_peer_instance_binding=config.signer_peer_instance_binding,
    )
    if key_reasons:
        return _reject(
            *key_reasons,
            key_provider_receipt=key_receipt,
            max_requests=config.max_requests,
            injected_dependency_effects_unobserved=True,
        )
    authorization_reservation = _reserve_policy_authorization(
        proposal_nonce_store,
        proposal_authorization,
    )
    if proposal_authorization is not None and not authorization_reservation:
        return _reject(
            FAIL_SIGNER_RUNTIME_PROPOSAL_POLICY_AUTHORIZATION_INVALID,
            key_provider_receipt=key_receipt,
            max_requests=config.max_requests,
            injected_dependency_effects_unobserved=True,
        )
    if not _commit_policy_authorization(
        proposal_nonce_store,
        authorization_reservation,
    ):
        return _reject(
            FAIL_SIGNER_RUNTIME_PROPOSAL_POLICY_AUTHORIZATION_INVALID,
            key_provider_receipt=key_receipt,
            max_requests=config.max_requests,
            injected_dependency_effects_unobserved=True,
        )
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
            injected_dependency_effects_unobserved=True,
        )
    if not isinstance(service, IsolatedSignerSocketResidentServiceResult):
        return _reject(
            FAIL_SIGNER_RUNTIME_SERVICE_INVALID,
            key_provider_receipt=key_receipt,
            max_requests=config.max_requests,
            injected_dependency_effects_unobserved=True,
        )
    service_receipt = service.to_dict()
    if service.accepted is not True or service.status != SIGNER_SOCKET_RESIDENT_SERVICE_SERVED:
        return _reject(
            FAIL_SIGNER_RUNTIME_SERVICE_REJECTED,
            key_provider_receipt=key_receipt,
            service_result=service_receipt,
            max_requests=config.max_requests,
            injected_dependency_effects_unobserved=True,
        )
    return SignerSocketServiceRuntimeWiringResult(
        accepted=True,
        status=SIGNER_SOCKET_RUNTIME_WIRING_SERVED,
        rejection_reasons=(),
        key_provider_receipt=key_receipt,
        service_result=service_receipt,
        max_requests=config.max_requests,
        no_env_parsed=False,
        no_file_io_performed=False,
        no_process_spawned=False,
        no_repo_mutation_performed=False,
        no_openclaw_enqueue_performed=False,
        no_hermes_dispatch_performed=False,
        no_pr_created=False,
        no_reward_settlement_performed=False,
        no_holoindex_reindex_performed=False,
    )


def validate_signer_socket_service_runtime_config(
    config: object,
) -> tuple[str, ...]:
    """Validate all non-secret signer runtime config before launch."""

    if not isinstance(config, SignerSocketServiceRuntimeWiringConfig):
        return (FAIL_SIGNER_RUNTIME_CONFIG_INVALID,)
    if not _socket_path_valid(config):
        return (FAIL_SIGNER_RUNTIME_CONFIG_INVALID,)
    profiles, profile_reasons = _profiles(config)
    if profile_reasons:
        return profile_reasons
    profile_public_keys = [profile.expected_public_key for profile in profiles]
    if len(profile_public_keys) != len(set(profile_public_keys)):
        return (FAIL_SIGNER_RUNTIME_KEY_PROVIDER_DUPLICATE,)
    policy = _peer_policy(config.peer_policy)
    if policy is None or not _peer_policy_valid(policy):
        return (FAIL_SIGNER_RUNTIME_PEER_POLICY_INVALID,)
    anchor_store, anchor_reasons = _control_loop_anchor_store(config)
    if anchor_reasons:
        return anchor_reasons
    control_authority_policy = _control_loop_authority_policy(config.control_loop_authority_policy)
    outcome_policy = _verified_outcome_signer_policy(config.verified_outcome_signer_policy)
    conversation_reasons = conversation_scope_config_reasons(
        config, set(profile_public_keys)
    )
    if conversation_reasons:
        return conversation_reasons
    if (
        config.verified_outcome_signer_policy is not None
        and outcome_policy is None
    ):
        return (FAIL_SIGNER_RUNTIME_CONFIG_INVALID,)
    if (
        config.control_loop_anchor_path is not None
        and control_authority_policy is None
        and config.proposal_authority_policy is None
    ):
        return (FAIL_SIGNER_RUNTIME_CONFIG_INVALID,)
    if (
        config.provider_mode == PROVIDER_MODE_WSP71_PERMISSIONED
        and (
            anchor_store is None
            or (
                control_authority_policy is None
                and config.proposal_authority_policy is None
            )
        )
    ):
        return (FAIL_SIGNER_RUNTIME_CONFIG_INVALID,)
    if (
        control_authority_policy is not None
        and control_authority_policy.signer_public_key
        not in set(profile_public_keys)
    ):
        return (FAIL_SIGNER_RUNTIME_CONFIG_INVALID,)
    if (
        outcome_policy is not None
        and outcome_policy.signer_public_key not in set(profile_public_keys)
    ):
        return (FAIL_SIGNER_RUNTIME_CONFIG_INVALID,)
    proposal_policy = _proposal_authority_policy(
        config.proposal_authority_policy
    )
    if (
        config.proposal_authority_policy is not None
        and proposal_policy is None
    ):
        return (FAIL_SIGNER_RUNTIME_PROPOSAL_POLICY_INVALID,)
    proposal_authorization = _proposal_policy_authorization(
        config,
        profiles=profiles,
        proposal_policy=proposal_policy,
        principal_key_resolver=None,
        require_trusted_principal=False,
    )
    if (
        (proposal_policy is None)
        != (config.proposal_policy_authorization is None)
        or (
            proposal_policy is not None
            and proposal_authorization is None
        )
    ):
        return (
            FAIL_SIGNER_RUNTIME_PROPOSAL_POLICY_AUTHORIZATION_INVALID,
        )
    _, _, proposal_store_reasons = _proposal_nonce_store(
        config,
        proposal_policy=proposal_policy,
    )
    if proposal_store_reasons:
        return proposal_store_reasons
    if proposal_policy is not None:
        try:
            expected_security_digest = (
                architect_proposal_security_context_digest(config)
            )
        except (OSError, TypeError, ValueError):
            return (
                FAIL_SIGNER_RUNTIME_PROPOSAL_POLICY_AUTHORIZATION_INVALID,
            )
        if not hmac.compare_digest(
            str(config.proposal_security_context_digest or ""),
            expected_security_digest,
        ):
            return (
                FAIL_SIGNER_RUNTIME_PROPOSAL_POLICY_AUTHORIZATION_INVALID,
            )
        if len(profiles) != 1:
            return (FAIL_SIGNER_RUNTIME_PROPOSAL_POLICY_INVALID,)
        proposal_profiles = [
            profile
            for profile in profiles
            if (
                profile.signer_profile_id
                == REDDOG_WORK_AUTHORITY_SIGNER_PROFILE_ID
                and profile.signer_agent_id
                == REDDOG_WORK_AUTHORITY_SIGNER_AGENT_ID
                and profile.expected_public_key
                == proposal_policy.expected_payload.signer_public_key
                and profile.expected_key_epoch
                == proposal_policy.expected_payload.key_epoch
            )
        ]
        if len(proposal_profiles) != 1:
            return (FAIL_SIGNER_RUNTIME_PROPOSAL_POLICY_INVALID,)
    limit_reasons = validate_resident_signer_socket_limits(
        max_requests=config.max_requests,
        timeout_s=config.timeout_s,
        max_request_bytes=config.max_request_bytes,
        max_response_bytes=config.max_response_bytes,
    )
    if limit_reasons:
        return (FAIL_SIGNER_RUNTIME_CONFIG_INVALID,)
    return ()


def _socket_path_valid(config: SignerSocketServiceRuntimeWiringConfig) -> bool:
    try:
        repo_root = Path(config.repo_root).resolve()
        runtime_root = validate_runtime_root_path(
            config.runtime_root,
            repo_root=repo_root,
        )
        socket_path = validate_runtime_artifact_path(
            config.socket_path,
            repo_root=repo_root,
            allowed_root=runtime_root,
        )
    except (OSError, TypeError, ValueError):
        return False
    return socket_path.parent == runtime_root


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
        if (
            profile is None
            or validate_signer_key_provider_profile(profile) is not None
            or public_key_fingerprint(profile.expected_public_key)
            != profile.expected_key_fingerprint
        ):
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
    control_loop_anchor_store: ControlLoopAnchorStore | None,
    control_loop_authority_policy: ControlLoopAuthorityPolicy | None,
    verified_outcome_signer_policy: VerifiedOutcomeSignerPolicy | None,
    verified_outcome_signing_authority: VerifiedOutcomeSigningAuthority | None,
    conversation_scope_binding: ConversationScopeRuntimeBinding | None,
    proposal_authority_policy: ArchitectProposalSignerPolicy | None,
    proposal_policy_authorization: ArchitectProposalPolicyAuthorization | None,
    proposal_nonce_store_path: Path | None,
    proposal_replay_high_water_store: ProposalReplayHighWaterStore | None,
    proposal_replay_high_water_store_id: str | None,
    proposal_replay_high_water_durability_receipt_id: str,
    repo_root: Path,
    signer_runtime_root: Path,
    signer_peer_instance_binding: SignerPeerInstanceBinding | None,
) -> tuple[Optional[IsolatedSignerBackend], ProposalAuthenticityNonceStore | None,
           dict[str, Any], tuple[str, ...]]:
    receipts: list[dict[str, Any]] = []
    backends: dict[str, IsolatedSignerBackend] = {}
    public_keys = [item.expected_public_key for item in profiles]
    if len(public_keys) != len(set(public_keys)):
        return None, None, _key_provider_receipt(False, receipts), (
            FAIL_SIGNER_RUNTIME_KEY_PROVIDER_DUPLICATE,
        )
    profile_ids = [item.signer_profile_id for item in profiles]
    if len(profile_ids) != len(set(profile_ids)):
        return None, None, _key_provider_receipt(False, receipts), (
            FAIL_SIGNER_RUNTIME_PROFILE_INVALID,
        )
    for profile in profiles:
        if _is_proposal_signer_profile(
            profile,
            proposal_authority_policy,
        ):
            if (
                proposal_policy_authorization is None
                or proposal_nonce_store_path is None
                or proposal_replay_high_water_store is None
                or proposal_replay_high_water_store_id is None
            ):
                return None, None, _key_provider_receipt(False, receipts), (
                    FAIL_SIGNER_RUNTIME_KEY_PROVIDER_REJECTED,
                )
            key_result = _build_proposal_signer_backend_from_verified_runtime(
                profile,
                resolver,
                provider_mode=provider_mode,
                allow_test_only_key_material=allow_test_only_key_material,
                permission_snapshot_fresh=permission_snapshot_fresh,
                proposal_authority_policy=proposal_authority_policy,
                proposal_policy_authorization=(
                    proposal_policy_authorization
                ),
                proposal_nonce_store_path=proposal_nonce_store_path,
                proposal_replay_high_water_store=(
                    proposal_replay_high_water_store
                ),
                proposal_replay_high_water_store_id=(
                    proposal_replay_high_water_store_id
                ),
                proposal_replay_high_water_durability_receipt_id=(
                    proposal_replay_high_water_durability_receipt_id
                ),
                proposal_nonce_store_allowed_root=signer_runtime_root,
                proposal_nonce_store_repo_root=repo_root,
            )
        else:
            key_result = build_signer_backend_from_provider(
                profile,
                resolver,
                provider_mode=provider_mode,
                allow_test_only_key_material=allow_test_only_key_material,
                permission_snapshot_fresh=permission_snapshot_fresh,
                control_loop_anchor_store=control_loop_anchor_store,
                control_loop_authority_policy=(
                    control_loop_authority_policy
                    if control_loop_authority_policy is not None
                    and profile.expected_public_key
                    == control_loop_authority_policy.signer_public_key
                    else None
                ),
                verified_outcome_signer_policy=(
                    verified_outcome_signer_policy
                    if verified_outcome_signer_policy is not None
                    and profile.expected_public_key
                    == verified_outcome_signer_policy.signer_public_key
                    else None
                ),
                verified_outcome_signing_authority=(
                    verified_outcome_signing_authority
                    if verified_outcome_signer_policy is not None
                    and profile.expected_public_key
                    == verified_outcome_signer_policy.signer_public_key
                    else None
                ),
            )
            key_result = bind_conversation_scope_backend(key_result, profile, conversation_scope_binding)
        receipt = key_result.to_receipt()
        receipts.append(receipt)
        if not key_result.ok or key_result.backend is None:
            return None, None, _key_provider_receipt(False, receipts), (
                FAIL_SIGNER_RUNTIME_KEY_PROVIDER_REJECTED,
            )
        public_key = str(key_result.public_key or "")
        bound_backend = _bind_peer_instance(
            key_result.backend,
            signer_peer_instance_binding,
        )
        if bound_backend is None:
            return None, None, _key_provider_receipt(False, receipts), (
                FAIL_SIGNER_RUNTIME_KEY_PROVIDER_REJECTED,
            )
        backends[public_key] = bound_backend

    if len(backends) == 1:
        backend = next(iter(backends.values()))
    else:
        backend = _RoutingSignerBackend(backends)
    nonce_store = (
        getattr(backend, "proposal_nonce_store", None)
        if proposal_policy_authorization is not None
        else None
    )
    return backend, nonce_store, _key_provider_receipt(True, receipts), ()


def _bind_peer_instance(
    backend: IsolatedSignerBackend,
    binding: SignerPeerInstanceBinding | None,
) -> IsolatedSignerBackend | None:
    if not isinstance(backend, Ed25519SignerBackend):
        return None if binding is not None else backend
    return replace(backend, signer_peer_instance_binding=binding)


def _proposal_authority_policy(
    value: ArchitectProposalSignerPolicy | Mapping[str, Any] | None,
) -> ArchitectProposalSignerPolicy | None:
    try:
        return rehydrate_architect_proposal_signer_policy(value)
    except (TypeError, ValueError):
        return None


def _proposal_policy_authorization(
    config: SignerSocketServiceRuntimeWiringConfig,
    *,
    profiles: list[SignerKeyProviderProfile],
    proposal_policy: ArchitectProposalSignerPolicy | None,
    principal_key_resolver: PrincipalKeyResolver | None,
    require_trusted_principal: bool,
) -> ArchitectProposalPolicyAuthorization | None:
    value = config.proposal_policy_authorization
    if proposal_policy is None:
        return None if value is None else None
    raw = value.to_dict() if hasattr(value, "to_dict") else value
    if not isinstance(raw, Mapping):
        return None
    proposal_profiles = [
        profile
        for profile in profiles
        if _is_proposal_signer_profile(profile, proposal_policy)
    ]
    if len(proposal_profiles) != 1:
        return None
    signer_root = Path(config.signer_runtime_root).resolve()
    nonce_path = config.proposal_nonce_store_path
    high_water_store_id = str(
        config.proposal_replay_high_water_store_id or ""
    ).strip()
    if nonce_path is None or not high_water_store_id:
        return None
    signer_instance_id = architect_proposal_signer_instance_id(
        signer_root,
        proposal_profiles[0].expected_public_key,
        proposal_profiles[0].expected_key_epoch,
    )
    replay_binding = architect_proposal_replay_store_binding_digest(
        signer_instance_id,
        nonce_path,
        high_water_store_id,
    )
    principal_id = str(raw.get("principal_id") or "")
    principal_provider = str(raw.get("principal_provider") or "")
    trusted_principal_key = str(
        raw.get("principal_public_key") or ""
    )
    if require_trusted_principal:
        if principal_key_resolver is None:
            return None
        try:
            trusted_principal_key = str(
                principal_key_resolver.resolve(
                    principal_id,
                    principal_provider,
                )
                or ""
            )
        except Exception:
            return None
    authority_profile = {
        "principal_id": proposal_policy.expected_payload.requester_principal_id,
        "principal_provider": principal_provider,
        "principal_public_key": str(
            raw.get("principal_public_key") or ""
        ),
        "reddog_id": proposal_policy.expected_payload.reddog_id,
        "reddog_public_key": proposal_profiles[0].expected_public_key,
        "key_epoch": proposal_policy.expected_payload.key_epoch,
        "authority_profile_source_receipt_id": (
            proposal_policy.expected_payload.authority_profile_source_receipt_id
        ),
    }
    try:
        return verify_architect_proposal_policy_authorization(
            raw,
            policy=proposal_policy,
            authority_profile=authority_profile,
            trusted_principal_public_key=trusted_principal_key,
            expected_signer_instance_id=signer_instance_id,
            expected_replay_store_binding_digest=replay_binding,
            expected_security_context_digest=str(
                config.proposal_security_context_digest or ""
            ),
            now_epoch=int(time.time()),
        )
    except (TypeError, ValueError):
        return None


def _proposal_nonce_store(
    config: SignerSocketServiceRuntimeWiringConfig,
    *,
    proposal_policy: ArchitectProposalSignerPolicy | None,
) -> tuple[Path | None, Path | None, tuple[str, ...]]:
    path = config.proposal_nonce_store_path
    high_water_store_id = str(
        config.proposal_replay_high_water_store_id or ""
    ).strip()
    durability_receipt_id = str(
        config.proposal_replay_high_water_durability_receipt_id or ""
    ).strip()
    security_digest = config.proposal_security_context_digest
    if (
        proposal_policy is None
        and path is None
        and not high_water_store_id
        and not durability_receipt_id
        and security_digest is None
    ):
        return None, None, ()
    if proposal_policy is None:
        return None, None, (FAIL_SIGNER_RUNTIME_PROPOSAL_POLICY_INVALID,)
    if (
        path is None
        or not high_water_store_id
        or not _ascii(high_water_store_id)
        or not _is_sha256_digest(durability_receipt_id)
        or not _is_sha256_digest(security_digest)
    ):
        return None, None, (
            FAIL_SIGNER_RUNTIME_PROPOSAL_NONCE_STORE_INVALID,
        )
    try:
        repo_root = Path(config.repo_root).resolve()
        signer_root = validate_runtime_root_path(
            config.signer_runtime_root,
            repo_root=repo_root,
        )
        target = validate_runtime_artifact_path(
            path,
            repo_root=repo_root,
            allowed_root=signer_root,
        )
    except (OSError, TypeError, ValueError):
        return None, None, (
            FAIL_SIGNER_RUNTIME_PROPOSAL_NONCE_STORE_INVALID,
        )
    if (
        target.parent != signer_root
        or target
        != (signer_root / "architect_proposal_nonce_store.json")
    ):
        return None, None, (
            FAIL_SIGNER_RUNTIME_PROPOSAL_NONCE_STORE_INVALID,
        )
    return target, high_water_store_id, ()


def _reserve_policy_authorization(
    store: ProposalAuthenticityNonceStore | None,
    authorization: ArchitectProposalPolicyAuthorization | None,
) -> str | None:
    if authorization is None:
        return None
    if store is None:
        return None
    try:
        return store.reserve(
            authorization.nonce,
            expires_at=authorization.expires_at,
            subject=(
                "proposal-policy-authorization:"
                + authorization.principal_id
            ),
        )
    except Exception:
        return None


def _commit_policy_authorization(
    store: ProposalAuthenticityNonceStore | None,
    reservation: str | None,
) -> bool:
    if store is None and reservation is None:
        return True
    if store is None or not reservation:
        return False
    try:
        store.commit(reservation)
        return True
    except Exception:
        return False


def _is_proposal_signer_profile(
    profile: SignerKeyProviderProfile,
    policy: ArchitectProposalSignerPolicy | None,
) -> bool:
    return bool(
        policy is not None
        and profile.signer_profile_id
        == REDDOG_WORK_AUTHORITY_SIGNER_PROFILE_ID
        and profile.signer_agent_id
        == REDDOG_WORK_AUTHORITY_SIGNER_AGENT_ID
        and profile.expected_public_key
        == policy.expected_payload.signer_public_key
        and profile.expected_key_epoch == policy.expected_payload.key_epoch
    )


def _is_sha256_digest(value: object) -> bool:
    text = str(value or "")
    return len(text) == 71 and text.startswith("sha256:") and all(
        char in "0123456789abcdef" for char in text[7:]
    )


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
    return rehydrate_peer_credential_policy(value)


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


def _ascii(value: object) -> bool:
    return isinstance(value, str) and all(ord(char) < 128 for char in value)


def _reject(
    *reasons: str,
    key_provider_receipt: Optional[dict[str, Any]] = None,
    service_result: Optional[dict[str, Any]] = None,
    max_requests: int = 0,
    no_file_io_performed: bool = True,
    injected_dependency_effects_unobserved: bool = False,
) -> SignerSocketServiceRuntimeWiringResult:
    no_unobserved_effect = not injected_dependency_effects_unobserved
    return SignerSocketServiceRuntimeWiringResult(
        accepted=False,
        status=SIGNER_SOCKET_RUNTIME_WIRING_REJECT,
        rejection_reasons=tuple(dict.fromkeys(reason for reason in reasons if reason)),
        key_provider_receipt=key_provider_receipt or {},
        service_result=service_result,
        max_requests=max_requests,
        no_env_parsed=no_unobserved_effect,
        no_file_io_performed=(
            no_file_io_performed and no_unobserved_effect
        ),
        no_process_spawned=no_unobserved_effect,
        no_repo_mutation_performed=no_unobserved_effect,
        no_openclaw_enqueue_performed=no_unobserved_effect,
        no_hermes_dispatch_performed=no_unobserved_effect,
        no_pr_created=no_unobserved_effect,
        no_reward_settlement_performed=no_unobserved_effect,
        no_holoindex_reindex_performed=no_unobserved_effect,
    )


__all__ = [
    "FAIL_SIGNER_RUNTIME_CONFIG_INVALID",
    "FAIL_SIGNER_RUNTIME_CONTROL_ANCHOR_INVALID",
    "FAIL_SIGNER_RUNTIME_KEY_PROVIDER_COUNT_INVALID",
    "FAIL_SIGNER_RUNTIME_KEY_PROVIDER_DUPLICATE",
    "FAIL_SIGNER_RUNTIME_KEY_PROVIDER_REJECTED",
    "FAIL_SIGNER_RUNTIME_PEER_POLICY_INVALID",
    "FAIL_SIGNER_RUNTIME_PROPOSAL_NONCE_STORE_INVALID",
    "FAIL_SIGNER_RUNTIME_PROPOSAL_POLICY_AUTHORIZATION_INVALID",
    "FAIL_SIGNER_RUNTIME_PROPOSAL_POLICY_INVALID",
    "FAIL_SIGNER_RUNTIME_PROFILE_INVALID",
    "FAIL_SIGNER_RUNTIME_SERVICE_INVALID",
    "FAIL_SIGNER_RUNTIME_SERVICE_REJECTED",
    "PRINCIPAL_IDENTITY_SIGNER_AGENT_ID",
    "PRINCIPAL_IDENTITY_SIGNER_PROFILE_ID",
    "REDDOG_WORK_AUTHORITY_SIGNER_AGENT_ID",
    "REDDOG_WORK_AUTHORITY_SIGNER_PROFILE_ID",
    "SIGNER_SOCKET_RUNTIME_WIRING_REJECT",
    "SIGNER_SOCKET_RUNTIME_WIRING_SERVED",
    "SignerSocketServiceRuntimeWiringConfig",
    "SignerSocketServiceRuntimeWiringResult",
    "architect_proposal_security_context_digest",
    "run_reddog_signer_socket_service_runtime_wiring",
    "validate_signer_socket_service_runtime_config",
]
