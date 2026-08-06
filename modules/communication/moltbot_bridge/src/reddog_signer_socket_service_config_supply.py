"""Signer socket service config supplier for resident RedDog runtime.

Slice: REDDOG_SIGNER_SERVICE_CONFIG_SUPPLY_PHASE1

This module materializes the outside-repo JSON config consumed by the
signer-owned CLI. It binds the existing promoted authority profile to explicit
WSP71 op:// references and a signer-owned peer policy. It does not resolve
secrets, start the signer service, bind sockets, parse environment variables,
spawn processes, mutate the repository, enqueue OpenClaw, dispatch Hermes,
publish PRs, settle rewards, or re-index HoloIndex.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any, Mapping, Sequence

from modules.communication.moltbot_bridge.src.reddog_architect_fix_promotion_publication import (
    architect_fix_committed_publication_reasons,
)
from modules.communication.moltbot_bridge.src.reddog_architect_fix_promotion_records import (
    canonical_digest,
)
from modules.communication.moltbot_bridge.src.reddog_runtime_json_read import (
    read_reddog_runtime_json_mapping,
)
from modules.communication.moltbot_bridge.src.reddog_authority_runtime_store import (
    atomic_replace_confined_mapping,
)
from modules.communication.moltbot_bridge.src.reddog_architect_proposal_authenticity import (
    ArchitectProposalPolicyAuthorization,
    ArchitectProposalSignerPolicy,
    DEFAULT_PROPOSAL_AUTHENTICITY_MAX_TTL_SECONDS,
    architect_proposal_replay_store_binding_digest,
    architect_proposal_signer_instance_id,
    verify_architect_proposal_policy_authorization,
)
from modules.communication.moltbot_bridge.src.reddog_isolated_signer_socket_resident_service import (
    validate_resident_signer_socket_limits,
)
from modules.communication.moltbot_bridge.src.reddog_signer_delegated_authority_runtime import (
    public_key_fingerprint,
)
from modules.communication.moltbot_bridge.src.reddog_signer_key_provider_dryrun import (
    PROVIDER_MODE_WSP71_PERMISSIONED,
)
from modules.communication.moltbot_bridge.src.reddog_signer_socket_service_runtime_wiring import (
    REDDOG_WORK_AUTHORITY_SIGNER_AGENT_ID,
    SignerSocketServiceRuntimeWiringConfig,
    architect_proposal_security_context_digest,
    validate_signer_socket_service_runtime_config,
)
from modules.communication.moltbot_bridge.src.reddog_work_order_signature_verifier import (
    FailClosedPrincipalKeyResolver,
    PrincipalKeyResolver,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_scope_signing import (
    ConversationScopeSignerPolicy,
)
from modules.infrastructure.secrets_mcp.src.vault_resolver import parse_op_reference
from modules.infrastructure.shared_utilities.runtime_artifact_safety import (
    runtime_operation_lock,
    validate_runtime_artifact_path,
    validate_runtime_root_path,
)


SIGNER_SERVICE_CONFIG_SUPPLY_ACCEPT = "SIGNER_SERVICE_CONFIG_SUPPLY_ACCEPT"
SIGNER_SERVICE_CONFIG_SUPPLY_REJECT = "SIGNER_SERVICE_CONFIG_SUPPLY_REJECT"
SIGNER_SERVICE_CONFIG_SCHEMA_VERSION = "reddog_signer_service_config.v3"

FAIL_SIGNER_CONFIG_AUTHORITY_PROFILE_INVALID = "signer_config_authority_profile_invalid"
FAIL_SIGNER_CONFIG_ARCHITECT_PUBLICATION_INVALID = (
    "signer_config_architect_publication_invalid"
)
FAIL_SIGNER_CONFIG_OUTPUT_PATH_INVALID = "signer_config_output_path_invalid"
FAIL_SIGNER_CONFIG_SOCKET_PATH_INVALID = "signer_config_socket_path_invalid"
FAIL_SIGNER_CONFIG_CONTROL_ANCHOR_PATH_INVALID = (
    "signer_config_control_anchor_path_invalid"
)
FAIL_SIGNER_CONFIG_OP_REF_INVALID = "signer_config_op_ref_invalid"
FAIL_SIGNER_CONFIG_OP_REF_REUSED = "signer_config_op_ref_reused"
FAIL_SIGNER_CONFIG_PEER_POLICY_INVALID = "signer_config_peer_policy_invalid"
FAIL_SIGNER_CONFIG_LIMITS_INVALID = "signer_config_limits_invalid"
FAIL_SIGNER_CONFIG_PROPOSAL_POLICY_INVALID = (
    "signer_config_proposal_policy_invalid"
)
FAIL_SIGNER_CONFIG_PROPOSAL_POLICY_AUTHORIZATION_INVALID = (
    "signer_config_proposal_policy_authorization_invalid"
)
FAIL_SIGNER_CONFIG_PROPOSAL_NONCE_PATH_INVALID = (
    "signer_config_proposal_nonce_path_invalid"
)
FAIL_SIGNER_CONFIG_WRITE_FAILED = "signer_config_write_failed"

_REQUIRED_AUTHORITY_FIELDS = (
    "principal_id",
    "principal_provider",
    "principal_public_key",
    "reddog_id",
    "reddog_public_key",
    "permission_snapshot_digest",
    "key_epoch",
    "consensus_receipt_digest",
    "authority_profile_source_receipt_id",
)


@dataclass(frozen=True)
class SignerServiceConfigSupplyResult:
    """Audit-safe result for signer service config materialization."""

    accepted: bool
    status: str
    config_supply_receipt_id: str | None
    config_path: str | None
    config_digest: str | None
    socket_path: str | None
    principal_id: str | None
    reddog_id: str | None
    profile_count: int
    rejection_reasons: tuple[str, ...]
    proposal_policy_configured: bool = False
    proposal_attestation_id: str | None = None
    proposal_nonce_store_path: str | None = None
    no_secret_values_written: bool = True
    no_secret_values_resolved: bool = True
    no_signer_started: bool = True
    no_socket_bound: bool = True
    no_process_spawned: bool = True
    no_shell_command_executed: bool = True
    no_repo_mutation_performed: bool = True
    no_openclaw_enqueue_performed: bool = True
    no_hermes_dispatch_performed: bool = True
    no_pr_created: bool = True
    no_reward_settlement_performed: bool = True
    no_holoindex_reindex_performed: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def run_reddog_signer_socket_service_config_supply(
    *,
    repo_root: Path | str,
    runtime_root: Path | str,
    signer_runtime_root: Path | str,
    authority_profile: Mapping[str, Any] | None,
    authoritative_work_state_path: Path | str | None,
    output_path: Path | str | None,
    socket_path: Path | str | None,
    principal_signing_key_ref: str,
    principal_audit_mac_key_ref: str,
    reddog_signing_key_ref: str,
    reddog_audit_mac_key_ref: str,
    peer_uid_to_principal: Mapping[int | str, str],
    allowed_gids: Sequence[int | str] = (),
    max_requests: int = 16,
    timeout_s: float = 5.0,
    max_request_bytes: int = 163840,
    max_response_bytes: int = 16384,
    principal_signer_agent_id: str = "signer:principal",
    reddog_signer_agent_id: str = "signer:reddog",
    control_loop_anchor_path: Path | str | None = None,
    proposal_authority_policy: ArchitectProposalSignerPolicy | None = None,
    proposal_policy_authorization: (
        ArchitectProposalPolicyAuthorization | Mapping[str, Any] | None
    ) = None,
    proposal_nonce_store_path: Path | str | None = None,
    proposal_replay_high_water_store_id: str | None = None,
    proposal_replay_high_water_durability_receipt_id: str | None = None,
    now_epoch: int | None = None,
    principal_key_resolver: PrincipalKeyResolver | None = None,
    authoritative_work_state: Mapping[str, Any] | None = None,
) -> SignerServiceConfigSupplyResult:
    """Write one signer CLI config from existing authority artifacts."""

    root = Path(repo_root).resolve()
    profile = _mapping(authority_profile)
    reasons: list[str] = []
    reasons.extend(
        _authority_profile_reasons(
            profile,
            require_principal_provider=(
                proposal_authority_policy is not None
            ),
        )
    )
    runtime, signer_runtime, out, sock, anchor, path_reasons = _runtime_artifact_paths(
        root,
        runtime_root,
        signer_runtime_root,
        output_path,
        socket_path,
        control_loop_anchor_path,
    )
    reasons.extend(path_reasons)
    reasons.extend(
        _architect_publication_reasons(
            profile,
            authoritative_work_state,
            runtime,
            authoritative_work_state_path,
        )
    )
    op_refs = (
        (reddog_signing_key_ref, reddog_audit_mac_key_ref)
        if proposal_authority_policy is not None
        else (
            principal_signing_key_ref,
            principal_audit_mac_key_ref,
            reddog_signing_key_ref,
            reddog_audit_mac_key_ref,
        )
    )
    reasons.extend(_op_ref_reasons(op_refs))
    peer_policy, peer_reasons = _peer_policy(peer_uid_to_principal, allowed_gids)
    reasons.extend(peer_reasons)
    reasons.extend(_limit_reasons(max_requests, timeout_s, max_request_bytes, max_response_bytes))
    (
        proposal_nonce_path,
        proposal_replay_high_water_store_id,
        proposal_reasons,
    ) = _proposal_runtime_inputs(
        root,
        signer_runtime,
        profile,
        proposal_authority_policy,
        proposal_nonce_store_path,
        proposal_replay_high_water_store_id,
        proposal_replay_high_water_durability_receipt_id,
        reddog_signer_agent_id,
    )
    reasons.extend(proposal_reasons)

    deduped = _dedupe(reasons)
    if deduped:
        return _reject(deduped)

    assert out is not None
    assert sock is not None
    assert anchor is not None
    assert runtime is not None
    assert signer_runtime is not None
    assert peer_policy is not None
    conversation_policy = (
        None
        if proposal_authority_policy is not None
        else _conversation_scope_policy(profile)
    )
    conversation_anchor = (
        signer_runtime / "conversation_scope_anchor.json"
        if conversation_policy is not None
        else None
    )
    unsigned_config = _config(
        authority_profile=profile,
        runtime_root=runtime,
        signer_runtime_root=signer_runtime,
        socket_path=sock,
        principal_signing_key_ref=principal_signing_key_ref,
        principal_audit_mac_key_ref=principal_audit_mac_key_ref,
        reddog_signing_key_ref=reddog_signing_key_ref,
        reddog_audit_mac_key_ref=reddog_audit_mac_key_ref,
        peer_policy=peer_policy,
        max_requests=max_requests,
        timeout_s=timeout_s,
        max_request_bytes=max_request_bytes,
        max_response_bytes=max_response_bytes,
        principal_signer_agent_id=principal_signer_agent_id,
        reddog_signer_agent_id=reddog_signer_agent_id,
        control_loop_anchor_path=anchor,
        conversation_scope_anchor_path=conversation_anchor,
        conversation_scope_signer_policy=conversation_policy,
        proposal_authority_policy=proposal_authority_policy,
        proposal_policy_authorization=None,
        proposal_nonce_store_path=proposal_nonce_path,
        proposal_replay_high_water_store_id=(
            proposal_replay_high_water_store_id
        ),
        proposal_replay_high_water_durability_receipt_id=(
            proposal_replay_high_water_durability_receipt_id
        ),
    )
    provisional_runtime_config = SignerSocketServiceRuntimeWiringConfig(
        repo_root=root,
        runtime_root=runtime,
        signer_runtime_root=signer_runtime,
        socket_path=sock,
        peer_policy=unsigned_config["peer_policy"],
        provider_mode=str(unsigned_config["provider_mode"]),
        allow_test_only_key_material=False,
        permission_snapshot_fresh=True,
        max_requests=unsigned_config["max_requests"],
        timeout_s=unsigned_config["timeout_s"],
        max_request_bytes=unsigned_config["max_request_bytes"],
        max_response_bytes=unsigned_config["max_response_bytes"],
        key_provider_profiles=tuple(
            unsigned_config["key_provider_profiles"]
        ),
        control_loop_anchor_path=anchor,
        control_loop_authority_policy=unsigned_config.get(
            "control_loop_authority_policy"
        ),
        conversation_scope_anchor_path=unsigned_config.get(
            "conversation_scope_anchor_path"
        ),
        conversation_scope_signer_policy=unsigned_config.get(
            "conversation_scope_signer_policy"
        ),
        verified_outcome_signer_policy=unsigned_config.get(
            "verified_outcome_signer_policy"
        ),
        proposal_authority_policy=unsigned_config.get(
            "proposal_authority_policy"
        ),
        proposal_nonce_store_path=proposal_nonce_path,
        proposal_replay_high_water_store_id=(
            proposal_replay_high_water_store_id
        ),
        proposal_replay_high_water_durability_receipt_id=(
            proposal_replay_high_water_durability_receipt_id
        ),
    )
    try:
        security_context_digest = (
            architect_proposal_security_context_digest(
                provisional_runtime_config
            )
            if proposal_authority_policy is not None
            else ""
        )
    except (OSError, TypeError, ValueError):
        return _reject(
            (FAIL_SIGNER_CONFIG_PROPOSAL_POLICY_AUTHORIZATION_INVALID,)
        )
    if proposal_authority_policy is not None:
        signer_instance_id = architect_proposal_signer_instance_id(
            signer_runtime,
            str(profile.get("reddog_public_key") or ""),
            str(profile.get("key_epoch") or ""),
        )
        replay_store_binding_digest = (
            architect_proposal_replay_store_binding_digest(
                signer_instance_id,
                proposal_nonce_path,
                proposal_replay_high_water_store_id,
            )
        )
    else:
        signer_instance_id = ""
        replay_store_binding_digest = ""
    try:
        authorization_now = int(
            now_epoch if now_epoch is not None else time.time()
        )
    except (TypeError, ValueError):
        authorization_now = 0
    verified_proposal_authorization, authorization_reasons = (
        _proposal_policy_authorization(
            profile,
            proposal_authority_policy,
            proposal_policy_authorization,
            principal_key_resolver=(
                principal_key_resolver
                or FailClosedPrincipalKeyResolver()
            ),
            expected_signer_instance_id=signer_instance_id,
            expected_replay_store_binding_digest=(
                replay_store_binding_digest
            ),
            expected_security_context_digest=security_context_digest,
            now_epoch=authorization_now,
        )
    )
    if authorization_reasons:
        return _reject(authorization_reasons)
    config = dict(unsigned_config)
    if verified_proposal_authorization is not None:
        config["proposal_policy_authorization"] = (
            verified_proposal_authorization.to_dict()
        )
    profile_count = len(tuple(config["key_provider_profiles"]))
    runtime_config_reasons = validate_signer_socket_service_runtime_config(
        replace(
            provisional_runtime_config,
            proposal_policy_authorization=config.get(
                "proposal_policy_authorization"
            ),
            proposal_security_context_digest=(
                security_context_digest
                if proposal_authority_policy is not None
                else None
            ),
        )
    )
    if runtime_config_reasons:
        return _reject((FAIL_SIGNER_CONFIG_AUTHORITY_PROFILE_INVALID + ":runtime_config",))
    config_digest = _digest(config)
    receipt = {
        "schema_version": SIGNER_SERVICE_CONFIG_SCHEMA_VERSION,
        "config_digest": config_digest,
        "config_path": str(out),
        "socket_path": str(sock),
        "control_loop_anchor_path": str(anchor),
        "principal_id": str(profile["principal_id"]),
        "reddog_id": str(profile["reddog_id"]),
        "profile_count": profile_count,
        "proposal_policy_configured": proposal_authority_policy is not None,
        "proposal_attestation_id": (
            proposal_authority_policy.expected_payload.attestation_id
            if proposal_authority_policy is not None
            else None
        ),
        "proposal_nonce_store_path": (
            str(proposal_nonce_path) if proposal_nonce_path is not None else None
        ),
        "no_secret_values_written": True,
        "no_secret_values_resolved": True,
        "no_signer_started": True,
        "no_socket_bound": True,
    }
    receipt["config_supply_receipt_id"] = _digest(receipt)
    try:
        with runtime_operation_lock(str(out) + ".operation"):
            atomic_replace_confined_mapping(
                out, config, repo_root=root, allowed_root=runtime
            )
    except Exception:
        return _reject((FAIL_SIGNER_CONFIG_WRITE_FAILED,))
    return SignerServiceConfigSupplyResult(
        accepted=True,
        status=SIGNER_SERVICE_CONFIG_SUPPLY_ACCEPT,
        config_supply_receipt_id=str(receipt["config_supply_receipt_id"]),
        config_path=str(out),
        config_digest=config_digest,
        socket_path=str(sock),
        principal_id=str(profile["principal_id"]),
        reddog_id=str(profile["reddog_id"]),
        profile_count=profile_count,
        rejection_reasons=(),
        proposal_policy_configured=proposal_authority_policy is not None,
        proposal_attestation_id=(
            proposal_authority_policy.expected_payload.attestation_id
            if proposal_authority_policy is not None
            else None
        ),
        proposal_nonce_store_path=(
            str(proposal_nonce_path) if proposal_nonce_path is not None else None
        ),
    )


def _runtime_artifact_paths(
    repo_root: Path,
    runtime_root: Path | str,
    signer_runtime_root: Path | str,
    output_path: Path | str | None,
    socket_path: Path | str | None,
    anchor_path: Path | str | None,
) -> tuple[Path | None, Path | None, Path | None, Path | None, Path | None, list[str]]:
    reasons: list[str] = []

    def resolve(
        value: Path | str | None,
        root: Path | None,
        reason: str,
    ) -> Path | None:
        if not value or root is None:
            reasons.append(reason)
            return None
        try:
            return validate_runtime_artifact_path(
                value,
                repo_root=repo_root,
                allowed_root=root,
            )
        except ValueError:
            reasons.append(reason)
            return None

    try:
        runtime = validate_runtime_root_path(runtime_root, repo_root=repo_root)
    except ValueError:
        runtime = None
        reasons.append(FAIL_SIGNER_CONFIG_OUTPUT_PATH_INVALID)
    try:
        signer_runtime = validate_runtime_root_path(
            signer_runtime_root,
            repo_root=repo_root,
        )
    except ValueError:
        signer_runtime = None
        reasons.append(FAIL_SIGNER_CONFIG_CONTROL_ANCHOR_PATH_INVALID)
    if (
        runtime is not None
        and signer_runtime is not None
        and (
            signer_runtime == runtime
            or runtime in signer_runtime.parents
            or signer_runtime in runtime.parents
        )
    ):
        reasons.append(FAIL_SIGNER_CONFIG_CONTROL_ANCHOR_PATH_INVALID)
    out = resolve(output_path, runtime, FAIL_SIGNER_CONFIG_OUTPUT_PATH_INVALID)
    sock = resolve(socket_path, runtime, FAIL_SIGNER_CONFIG_SOCKET_PATH_INVALID)
    if out is not None and (
        out.parent != runtime
        or (out.exists() and not out.is_file())
    ):
        reasons.append(FAIL_SIGNER_CONFIG_OUTPUT_PATH_INVALID)
        out = None
    if sock is not None and (
        sock.parent != runtime
        or sock.exists()
    ):
        reasons.append(FAIL_SIGNER_CONFIG_SOCKET_PATH_INVALID)
        sock = None
    if anchor_path is None and signer_runtime is not None:
        anchor_path = signer_runtime / "signer_control_loop_anchor.json"
    anchor = resolve(
        anchor_path,
        signer_runtime,
        FAIL_SIGNER_CONFIG_CONTROL_ANCHOR_PATH_INVALID,
    )
    if anchor is not None and anchor.parent != signer_runtime:
        reasons.append(FAIL_SIGNER_CONFIG_CONTROL_ANCHOR_PATH_INVALID)
        anchor = None
    return runtime, signer_runtime, out, sock, anchor, reasons


def _proposal_runtime_inputs(
    repo_root: Path,
    signer_runtime_root: Path | None,
    authority_profile: Mapping[str, Any],
    policy: ArchitectProposalSignerPolicy | None,
    nonce_store_path: Path | str | None,
    high_water_store_id: str | None,
    high_water_durability_receipt_id: str | None,
    reddog_signer_agent_id: str,
) -> tuple[Path | None, str | None, list[str]]:
    if policy is None:
        return (
            None,
            None,
            (
                []
                if (
                    nonce_store_path is None
                    and high_water_store_id is None
                    and high_water_durability_receipt_id is None
                )
                else [FAIL_SIGNER_CONFIG_PROPOSAL_POLICY_INVALID]
            ),
        )
    if (
        not isinstance(policy, ArchitectProposalSignerPolicy)
        or signer_runtime_root is None
        or not _ascii_string(high_water_store_id)
        or not _is_sha256_digest(high_water_durability_receipt_id)
        or reddog_signer_agent_id
        != REDDOG_WORK_AUTHORITY_SIGNER_AGENT_ID
    ):
        return None, None, [FAIL_SIGNER_CONFIG_PROPOSAL_POLICY_INVALID]
    payload = policy.expected_payload
    identity_matches = (
        payload.requester_principal_id
        == str(authority_profile.get("principal_id") or "")
        and payload.reddog_id
        == str(authority_profile.get("reddog_id") or "")
        and payload.signer_public_key
        == str(authority_profile.get("reddog_public_key") or "")
        and payload.key_epoch
        == str(authority_profile.get("key_epoch") or "")
        and payload.consensus_receipt_digest
        == str(authority_profile.get("consensus_receipt_digest") or "")
        and payload.authority_profile_source_receipt_id
        == str(
            authority_profile.get("authority_profile_source_receipt_id")
            or ""
        )
    )
    ttl = int(payload.expires_at) - int(payload.issued_at)
    if (
        not identity_matches
        or policy.max_ttl_seconds <= 0
        or policy.max_ttl_seconds
        > DEFAULT_PROPOSAL_AUTHENTICITY_MAX_TTL_SECONDS
        or ttl <= 0
        or ttl > int(policy.max_ttl_seconds)
    ):
        return None, None, [FAIL_SIGNER_CONFIG_PROPOSAL_POLICY_INVALID]
    canonical_target = (
        signer_runtime_root / "architect_proposal_nonce_store.json"
    )
    target_value = nonce_store_path or canonical_target
    try:
        target = validate_runtime_artifact_path(
            target_value,
            repo_root=repo_root,
            allowed_root=signer_runtime_root,
        )
    except (OSError, TypeError, ValueError):
        return None, None, [
            FAIL_SIGNER_CONFIG_PROPOSAL_NONCE_PATH_INVALID
        ]
    if target.parent != signer_runtime_root or (
        target.exists() and not target.is_file()
    ) or target != canonical_target.resolve():
        return None, None, [
            FAIL_SIGNER_CONFIG_PROPOSAL_NONCE_PATH_INVALID
        ]
    return target, str(high_water_store_id).strip(), []


def _proposal_policy_authorization(
    authority_profile: Mapping[str, Any],
    policy: ArchitectProposalSignerPolicy | None,
    value: ArchitectProposalPolicyAuthorization | Mapping[str, Any] | None,
    *,
    principal_key_resolver: PrincipalKeyResolver,
    expected_signer_instance_id: str,
    expected_replay_store_binding_digest: str,
    expected_security_context_digest: str,
    now_epoch: int,
) -> tuple[ArchitectProposalPolicyAuthorization | None, list[str]]:
    if policy is None:
        return (
            None,
            []
            if value is None
            else [FAIL_SIGNER_CONFIG_PROPOSAL_POLICY_AUTHORIZATION_INVALID],
        )
    raw = value.to_dict() if hasattr(value, "to_dict") else value
    if not isinstance(raw, Mapping):
        return None, [FAIL_SIGNER_CONFIG_PROPOSAL_POLICY_AUTHORIZATION_INVALID]
    try:
        trusted_principal_key = principal_key_resolver.resolve(
            str(authority_profile.get("principal_id") or ""),
            str(authority_profile.get("principal_provider") or ""),
        )
        verified = verify_architect_proposal_policy_authorization(
            raw,
            policy=policy,
            authority_profile=authority_profile,
            trusted_principal_public_key=str(
                trusted_principal_key or ""
            ),
            expected_signer_instance_id=(
                expected_signer_instance_id
            ),
            expected_replay_store_binding_digest=(
                expected_replay_store_binding_digest
            ),
            expected_security_context_digest=(
                expected_security_context_digest
            ),
            now_epoch=now_epoch,
        )
    except Exception:
        return None, [FAIL_SIGNER_CONFIG_PROPOSAL_POLICY_AUTHORIZATION_INVALID]
    return verified, []


def _config(
    *,
    authority_profile: Mapping[str, Any],
    runtime_root: Path,
    signer_runtime_root: Path,
    socket_path: Path,
    principal_signing_key_ref: str,
    principal_audit_mac_key_ref: str,
    reddog_signing_key_ref: str,
    reddog_audit_mac_key_ref: str,
    peer_policy: Mapping[str, Any],
    max_requests: int,
    timeout_s: float,
    max_request_bytes: int,
    max_response_bytes: int,
    principal_signer_agent_id: str,
    reddog_signer_agent_id: str,
    control_loop_anchor_path: Path,
    conversation_scope_anchor_path: Path | None,
    conversation_scope_signer_policy: ConversationScopeSignerPolicy | None,
    proposal_authority_policy: ArchitectProposalSignerPolicy | None,
    proposal_policy_authorization: ArchitectProposalPolicyAuthorization | None,
    proposal_nonce_store_path: Path | None,
    proposal_replay_high_water_store_id: str | None,
    proposal_replay_high_water_durability_receipt_id: str | None,
) -> dict[str, Any]:
    principal_public = str(authority_profile["principal_public_key"])
    reddog_public = str(authority_profile["reddog_public_key"])
    permission_digest = str(authority_profile["permission_snapshot_digest"])
    key_epoch = str(authority_profile["key_epoch"])
    config = {
        "schema_version": SIGNER_SERVICE_CONFIG_SCHEMA_VERSION,
        "runtime_root": str(runtime_root),
        "signer_runtime_root": str(signer_runtime_root),
        "socket_path": str(socket_path),
        "control_loop_anchor_path": str(control_loop_anchor_path),
        "provider_mode": PROVIDER_MODE_WSP71_PERMISSIONED,
        "allow_test_only_key_material": False,
        "permission_snapshot_fresh": True,
        "control_loop_authority_policy": {
            "issuer_principal_id": str(authority_profile["principal_id"]),
            "signer_public_key": reddog_public,
            "key_epoch": key_epoch,
            "consensus_receipt_digest": str(
                authority_profile["consensus_receipt_digest"]
            ),
            "authority_profile_digest": _digest(authority_profile),
            "authority_profile_source_receipt_id": str(
                authority_profile["authority_profile_source_receipt_id"]
            ),
        },
        "verified_outcome_signer_policy": {
            "issuer_principal_id": str(authority_profile["principal_id"]),
            "reddog_id": str(authority_profile["reddog_id"]),
            "signer_public_key": reddog_public,
            "key_epoch": key_epoch,
            "authority_tier": "HIGH",
            "consensus_receipt_digest": str(
                authority_profile["consensus_receipt_digest"]
            ),
            "max_future_skew_seconds": 60,
        },
        "max_requests": int(max_requests),
        "timeout_s": float(timeout_s),
        "max_request_bytes": int(max_request_bytes),
        "max_response_bytes": int(max_response_bytes),
        "key_provider_profiles": [
            {
                "signer_profile_id": "principal-identity",
                "signer_agent_id": str(principal_signer_agent_id),
                "signing_key_ref": str(principal_signing_key_ref),
                "audit_mac_key_ref": str(principal_audit_mac_key_ref),
                "expected_public_key": principal_public,
                "expected_key_fingerprint": public_key_fingerprint(principal_public),
                "expected_key_epoch": key_epoch,
                "permission_snapshot_digest": permission_digest,
                "ttl_seconds": int(authority_profile.get("identity_ttl_seconds") or 300),
            },
            {
                "signer_profile_id": "reddog-work-authority",
                "signer_agent_id": str(reddog_signer_agent_id),
                "signing_key_ref": str(reddog_signing_key_ref),
                "audit_mac_key_ref": str(reddog_audit_mac_key_ref),
                "expected_public_key": reddog_public,
                "expected_key_fingerprint": public_key_fingerprint(reddog_public),
                "expected_key_epoch": key_epoch,
                "permission_snapshot_digest": permission_digest,
                "ttl_seconds": int(authority_profile.get("work_authority_ttl_seconds") or 300),
            },
        ],
        "peer_policy": dict(peer_policy),
    }
    if conversation_scope_signer_policy is not None:
        assert conversation_scope_anchor_path is not None
        config["conversation_scope_anchor_path"] = str(
            conversation_scope_anchor_path
        )
        config["conversation_scope_signer_policy"] = asdict(
            conversation_scope_signer_policy
        )
    if proposal_authority_policy is not None:
        assert proposal_nonce_store_path is not None
        assert proposal_replay_high_water_store_id is not None
        assert (
            proposal_replay_high_water_durability_receipt_id is not None
        )
        config["key_provider_profiles"] = [
            config["key_provider_profiles"][1]
        ]
        config.pop("control_loop_authority_policy", None)
        config["proposal_authority_policy"] = {
            "expected_payload": (
                proposal_authority_policy.expected_payload.to_dict()
            ),
            "max_ttl_seconds": int(
                proposal_authority_policy.max_ttl_seconds
            ),
        }
        config["proposal_nonce_store_path"] = str(
            proposal_nonce_store_path
        )
        config["proposal_replay_high_water_store_id"] = (
            proposal_replay_high_water_store_id
        )
        config[
            "proposal_replay_high_water_durability_receipt_id"
        ] = proposal_replay_high_water_durability_receipt_id
        if proposal_policy_authorization is not None:
            config["proposal_policy_authorization"] = (
                proposal_policy_authorization.to_dict()
            )
    return config


def _conversation_scope_policy(
    authority_profile: Mapping[str, Any],
) -> ConversationScopeSignerPolicy | None:
    values = (
        str(authority_profile.get("principal_id") or "").strip(),
        str(authority_profile.get("principal_provider") or "").strip(),
        str(authority_profile.get("repo_full_name") or "").strip(),
        str(authority_profile.get("reddog_public_key") or "").strip(),
        str(authority_profile.get("key_epoch") or "").strip(),
    )
    if (
        any(not value or not value.isascii() for value in values)
        or "/" not in values[2]
    ):
        return None
    ttl = int(authority_profile.get("identity_ttl_seconds") or 300)
    if ttl <= 0 or ttl > 86400:
        return None
    return ConversationScopeSignerPolicy(
        issuer_principal_id=values[0],
        issuer_principal_provider=values[1],
        repo_full_name=values[2],
        signer_public_key=values[3],
        key_epoch=values[4],
        max_scope_ttl_seconds=ttl,
    )


def _authority_profile_reasons(
    profile: Mapping[str, Any],
    *,
    require_principal_provider: bool,
) -> list[str]:
    if not profile or not _ascii_deep(profile):
        return [FAIL_SIGNER_CONFIG_AUTHORITY_PROFILE_INVALID]
    required_fields = tuple(
        field
        for field in _REQUIRED_AUTHORITY_FIELDS
        if require_principal_provider or field != "principal_provider"
    )
    missing = [
        field
        for field in required_fields
        if not str(profile.get(field) or "")
    ]
    if missing:
        return [FAIL_SIGNER_CONFIG_AUTHORITY_PROFILE_INVALID + ":" + field for field in missing]
    if str(profile.get("principal_public_key")) == str(profile.get("reddog_public_key")):
        return [FAIL_SIGNER_CONFIG_AUTHORITY_PROFILE_INVALID + ":key_reuse"]
    for field in (
        "permission_snapshot_digest",
        "consensus_receipt_digest",
        "authority_profile_source_receipt_id",
    ):
        if not _is_sha256_digest(profile.get(field)):
            return [FAIL_SIGNER_CONFIG_AUTHORITY_PROFILE_INVALID + ":" + field]
    return []


def _architect_publication_reasons(
    profile: Mapping[str, Any],
    work_state: Mapping[str, Any] | None,
    runtime_root: Path | None,
    work_state_path: Path | str | None,
) -> list[str]:
    durable_state = _read_current_authoritative_work_state(
        runtime_root,
        work_state_path,
    )
    if durable_state is None:
        return [FAIL_SIGNER_CONFIG_ARCHITECT_PUBLICATION_INVALID]
    if (
        isinstance(work_state, Mapping)
        and canonical_digest(work_state) != canonical_digest(durable_state)
    ):
        return [FAIL_SIGNER_CONFIG_ARCHITECT_PUBLICATION_INVALID]
    binding = profile.get("operational_context_binding")
    if not isinstance(binding, Mapping):
        binding = {}
    reasons = architect_fix_committed_publication_reasons(
        durable_state,
        profile,
        queue_item_id=str(binding.get("queue_item_id") or ""),
        claim_id=str(binding.get("claim_id") or ""),
    )
    return (
        []
        if not reasons
        else [FAIL_SIGNER_CONFIG_ARCHITECT_PUBLICATION_INVALID]
    )


def _read_current_authoritative_work_state(
    runtime_root: Path | None,
    work_state_path: Path | str | None,
) -> Mapping[str, Any] | None:
    if runtime_root is None or not work_state_path:
        return None
    try:
        return read_reddog_runtime_json_mapping(
            work_state_path,
            allowed_root=runtime_root,
        )
    except Exception:
        return None


def _is_sha256_digest(value: object) -> bool:
    text = str(value or "")
    return len(text) == 71 and text.startswith("sha256:") and all(
        char in "0123456789abcdef" for char in text[7:]
    )


def _op_ref_reasons(values: Sequence[str]) -> list[str]:
    refs = tuple(str(value or "").strip() for value in values)
    reasons: list[str] = []
    for ref in refs:
        if not parse_op_reference(ref):
            reasons.append(FAIL_SIGNER_CONFIG_OP_REF_INVALID)
    if len(set(refs)) != len(refs):
        reasons.append(FAIL_SIGNER_CONFIG_OP_REF_REUSED)
    return reasons


def _peer_policy(
    uid_to_principal: Mapping[int | str, str],
    allowed_gids: Sequence[int | str],
) -> tuple[dict[str, Any] | None, list[str]]:
    try:
        uid_map = {int(uid): str(principal) for uid, principal in uid_to_principal.items()}
        gids = tuple(int(gid) for gid in allowed_gids)
    except Exception:
        return None, [FAIL_SIGNER_CONFIG_PEER_POLICY_INVALID]
    if not uid_map:
        return None, [FAIL_SIGNER_CONFIG_PEER_POLICY_INVALID]
    if any(uid < 0 for uid in uid_map) or any(gid < 0 for gid in gids):
        return None, [FAIL_SIGNER_CONFIG_PEER_POLICY_INVALID]
    if any(not principal or not _ascii_string(principal) for principal in uid_map.values()):
        return None, [FAIL_SIGNER_CONFIG_PEER_POLICY_INVALID]
    return {
        "uid_to_principal": {str(uid): principal for uid, principal in sorted(uid_map.items())},
        "allowed_gids": list(gids),
        "transport": "unix_socket",
        "credential_source_prefix": "kernel_peer_credential",
    }, []


def _limit_reasons(
    max_requests: int,
    timeout_s: float,
    max_request_bytes: int,
    max_response_bytes: int,
) -> list[str]:
    if validate_resident_signer_socket_limits(
        max_requests=max_requests,
        timeout_s=timeout_s,
        max_request_bytes=max_request_bytes,
        max_response_bytes=max_response_bytes,
    ) or type(max_requests) is not int or max_requests < 2:
        return [FAIL_SIGNER_CONFIG_LIMITS_INVALID]
    return []


def _mapping(value: Mapping[str, Any] | None) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _reject(reasons: Sequence[str]) -> SignerServiceConfigSupplyResult:
    return SignerServiceConfigSupplyResult(
        accepted=False,
        status=SIGNER_SERVICE_CONFIG_SUPPLY_REJECT,
        config_supply_receipt_id=None,
        config_path=None,
        config_digest=None,
        socket_path=None,
        principal_id=None,
        reddog_id=None,
        profile_count=0,
        rejection_reasons=_dedupe(reasons),
    )


def _digest(payload: Mapping[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _dedupe(values: Sequence[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(str(value) for value in values if str(value)))


def _ascii_string(value: object) -> bool:
    return isinstance(value, str) and all(ord(char) < 128 for char in value)


def _ascii_deep(value: object) -> bool:
    if isinstance(value, str):
        return _ascii_string(value)
    if isinstance(value, Mapping):
        return all(_ascii_string(key) and _ascii_deep(item) for key, item in value.items())
    if isinstance(value, (list, tuple)):
        return all(_ascii_deep(item) for item in value)
    if value is None or isinstance(value, (bool, int, float)):
        return True
    return False


__all__ = [
    "FAIL_SIGNER_CONFIG_AUTHORITY_PROFILE_INVALID",
    "FAIL_SIGNER_CONFIG_LIMITS_INVALID",
    "FAIL_SIGNER_CONFIG_OP_REF_INVALID",
    "FAIL_SIGNER_CONFIG_OP_REF_REUSED",
    "FAIL_SIGNER_CONFIG_OUTPUT_PATH_INVALID",
    "FAIL_SIGNER_CONFIG_CONTROL_ANCHOR_PATH_INVALID",
    "FAIL_SIGNER_CONFIG_PEER_POLICY_INVALID",
    "FAIL_SIGNER_CONFIG_PROPOSAL_NONCE_PATH_INVALID",
    "FAIL_SIGNER_CONFIG_PROPOSAL_POLICY_AUTHORIZATION_INVALID",
    "FAIL_SIGNER_CONFIG_PROPOSAL_POLICY_INVALID",
    "FAIL_SIGNER_CONFIG_SOCKET_PATH_INVALID",
    "FAIL_SIGNER_CONFIG_WRITE_FAILED",
    "SIGNER_SERVICE_CONFIG_SCHEMA_VERSION",
    "SIGNER_SERVICE_CONFIG_SUPPLY_ACCEPT",
    "SIGNER_SERVICE_CONFIG_SUPPLY_REJECT",
    "SignerServiceConfigSupplyResult",
    "run_reddog_signer_socket_service_config_supply",
]
