"""Bounded materialization workflow for signer socket service config."""

from __future__ import annotations

import time
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Mapping

from modules.communication.moltbot_bridge.src.reddog_architect_proposal_runtime_authorization import (
    verify_architect_proposal_runtime_authorization,
)
from modules.communication.moltbot_bridge.src.reddog_authority_runtime_store import (
    atomic_replace_confined_mapping,
)
from modules.communication.moltbot_bridge.src.reddog_signer_socket_service_config_composition import (
    ConfigInputs,
    RuntimeArtifactPaths,
    architect_publication_reasons,
    authority_profile_reasons,
    build_config,
    conversation_scope_policy,
    limit_reasons,
    op_ref_reasons,
    peer_policy,
    proposal_runtime_inputs,
    runtime_artifact_paths,
)
from modules.communication.moltbot_bridge.src.reddog_signer_socket_service_config_supply_contract import (
    CONVERSATION_SCOPE_MIN_REQUEST_BYTES,
    FAIL_SIGNER_CONFIG_AUTHORITY_PROFILE_INVALID,
    FAIL_SIGNER_CONFIG_OUTPUT_PATH_INVALID,
    FAIL_SIGNER_CONFIG_PROPOSAL_POLICY_AUTHORIZATION_INVALID,
    FAIL_SIGNER_CONFIG_WRITE_FAILED,
    SIGNER_SERVICE_CONFIG_SCHEMA_VERSION,
    SIGNER_SERVICE_CONFIG_SUPPLY_ACCEPT,
    SignerServiceConfigSupplyRequest,
    SignerServiceConfigSupplyResult,
    canonical_config_digest,
    dedupe_reasons,
    reject_supply,
)
from modules.communication.moltbot_bridge.src.reddog_signer_socket_service_runtime_wiring import (
    SignerSocketServiceRuntimeWiringConfig,
    architect_proposal_security_context_digest,
    validate_signer_socket_service_runtime_config,
)
from modules.communication.moltbot_bridge.src.reddog_work_order_signature_verifier import (
    FailClosedPrincipalKeyResolver,
)
from modules.infrastructure.shared_utilities.runtime_artifact_safety import (
    runtime_operation_lock,
)


@dataclass(frozen=True)
class PreparedConfigSupply:
    request: SignerServiceConfigSupplyRequest
    repo_root: Path
    profile: Mapping[str, Any]
    paths: RuntimeArtifactPaths
    peer_policy: Mapping[str, Any]
    proposal_nonce_path: Path | None
    proposal_store_id: str | None


@dataclass(frozen=True)
class ProvisionalConfig:
    prepared: PreparedConfigSupply
    mapping: dict[str, Any]
    runtime: SignerSocketServiceRuntimeWiringConfig


def materialize_signer_service_config(
    request: SignerServiceConfigSupplyRequest,
) -> SignerServiceConfigSupplyResult:
    prepared, reasons = _prepare(request)
    if prepared is None:
        return reject_supply(reasons)
    provisional = _provisional(prepared)
    if provisional is None:
        return reject_supply((FAIL_SIGNER_CONFIG_AUTHORITY_PROFILE_INVALID,))
    authorized, reasons = _authorize(provisional)
    if authorized is None:
        return reject_supply(reasons)
    return _validate_write_and_accept(authorized)


def _prepare(
    request: SignerServiceConfigSupplyRequest,
) -> tuple[PreparedConfigSupply | None, tuple[str, ...]]:
    repo = Path(request.repo_root).resolve()
    profile = request.authority_profile
    profile = profile if isinstance(profile, Mapping) else {}
    paths = runtime_artifact_paths(
        repo, request.runtime_root, request.signer_runtime_root,
        request.output_path, request.socket_path, request.control_loop_anchor_path,
    )
    peer, peer_reasons = peer_policy(
        request.peer_uid_to_principal, request.allowed_gids
    )
    nonce, store_id, proposal_reasons = proposal_runtime_inputs(
        repo, paths.signer_runtime, profile, request.proposal_authority_policy,
        request.proposal_nonce_store_path,
        request.proposal_replay_high_water_store_id,
        request.proposal_replay_high_water_durability_receipt_id,
        request.reddog_signer_agent_id,
    )
    reasons = _preparation_reasons(
        request, profile, paths, peer_reasons, proposal_reasons
    )
    if reasons or peer is None:
        return None, reasons
    return PreparedConfigSupply(
        request, repo, profile, paths, peer, nonce, store_id
    ), ()


def _preparation_reasons(
    request: SignerServiceConfigSupplyRequest,
    profile: Mapping[str, Any],
    paths: RuntimeArtifactPaths,
    peer_reasons: tuple[str, ...],
    proposal_reasons: tuple[str, ...],
) -> tuple[str, ...]:
    refs = _operation_references(request)
    reasons = list(authority_profile_reasons(
        profile,
        require_principal_provider=request.proposal_authority_policy is not None,
    ))
    reasons.extend(paths.reasons)
    if paths.output is not None and request.authoritative_work_state_path:
        try:
            state_path = Path(request.authoritative_work_state_path).resolve()
        except (OSError, TypeError, ValueError):
            state_path = None
        if state_path is not None and state_path == paths.output:
            reasons.append(FAIL_SIGNER_CONFIG_OUTPUT_PATH_INVALID)
    reasons.extend(architect_publication_reasons(
        profile, request.authoritative_work_state, paths.runtime,
        request.authoritative_work_state_path,
    ))
    reasons.extend(op_ref_reasons(refs))
    reasons.extend(peer_reasons)
    reasons.extend(limit_reasons(
        request.max_requests, request.timeout_s,
        request.max_request_bytes, request.max_response_bytes,
    ))
    reasons.extend(proposal_reasons)
    return dedupe_reasons(reasons)


def _operation_references(
    request: SignerServiceConfigSupplyRequest,
) -> tuple[str, ...]:
    if request.proposal_authority_policy is not None:
        return request.reddog_signing_key_ref, request.reddog_audit_mac_key_ref
    return (
        request.principal_signing_key_ref,
        request.principal_audit_mac_key_ref,
        request.reddog_signing_key_ref,
        request.reddog_audit_mac_key_ref,
    )


def _provisional(prepared: PreparedConfigSupply) -> ProvisionalConfig | None:
    request = prepared.request
    paths = prepared.paths
    if not all((paths.runtime, paths.signer_runtime, paths.output, paths.socket, paths.anchor)):
        return None
    conversation_policy = None
    if (
        request.proposal_authority_policy is None
        and int(request.max_request_bytes)
        >= CONVERSATION_SCOPE_MIN_REQUEST_BYTES
    ):
        conversation_policy = conversation_scope_policy(prepared.profile)
    conversation_anchor = (
        paths.signer_runtime / "conversation_scope_anchor.json"
        if conversation_policy is not None else None
    )
    try:
        mapping = build_config(_config_inputs(
            prepared, conversation_policy, conversation_anchor
        ))
        runtime = _runtime_config(prepared, mapping, conversation_anchor)
    except (KeyError, TypeError, ValueError):
        return None
    return ProvisionalConfig(prepared, mapping, runtime)


def _config_inputs(
    prepared: PreparedConfigSupply,
    conversation_policy: Any,
    conversation_anchor: Path | None,
) -> ConfigInputs:
    request = prepared.request
    paths = prepared.paths
    return ConfigInputs(
        authority_profile=prepared.profile,
        runtime_root=paths.runtime, signer_runtime_root=paths.signer_runtime,
        socket_path=paths.socket,
        principal_signing_key_ref=request.principal_signing_key_ref,
        principal_audit_mac_key_ref=request.principal_audit_mac_key_ref,
        reddog_signing_key_ref=request.reddog_signing_key_ref,
        reddog_audit_mac_key_ref=request.reddog_audit_mac_key_ref,
        peer_policy=prepared.peer_policy,
        max_requests=request.max_requests, timeout_s=request.timeout_s,
        max_request_bytes=request.max_request_bytes,
        max_response_bytes=request.max_response_bytes,
        principal_signer_agent_id=request.principal_signer_agent_id,
        reddog_signer_agent_id=request.reddog_signer_agent_id,
        control_loop_anchor_path=paths.anchor,
        conversation_scope_anchor_path=conversation_anchor,
        conversation_scope_signer_policy=conversation_policy,
        proposal_authority_policy=request.proposal_authority_policy,
        proposal_policy_authorization=None,
        proposal_nonce_store_path=prepared.proposal_nonce_path,
        proposal_replay_high_water_store_id=prepared.proposal_store_id,
        proposal_replay_high_water_durability_receipt_id=(
            request.proposal_replay_high_water_durability_receipt_id
        ),
    )


def _runtime_config(
    prepared: PreparedConfigSupply,
    mapping: Mapping[str, Any],
    conversation_anchor: Path | None,
) -> SignerSocketServiceRuntimeWiringConfig:
    request = prepared.request
    paths = prepared.paths
    return SignerSocketServiceRuntimeWiringConfig(
        repo_root=prepared.repo_root,
        runtime_root=paths.runtime, signer_runtime_root=paths.signer_runtime,
        socket_path=paths.socket, peer_policy=mapping["peer_policy"],
        provider_mode=str(mapping["provider_mode"]),
        allow_test_only_key_material=False, permission_snapshot_fresh=True,
        max_requests=mapping["max_requests"], timeout_s=mapping["timeout_s"],
        max_request_bytes=mapping["max_request_bytes"],
        max_response_bytes=mapping["max_response_bytes"],
        key_provider_profiles=tuple(mapping["key_provider_profiles"]),
        control_loop_anchor_path=paths.anchor,
        control_loop_authority_policy=mapping.get("control_loop_authority_policy"),
        conversation_scope_anchor_path=conversation_anchor,
        conversation_scope_signer_policy=mapping.get("conversation_scope_signer_policy"),
        verified_outcome_signer_policy=mapping.get("verified_outcome_signer_policy"),
        proposal_authority_policy=mapping.get("proposal_authority_policy"),
        proposal_nonce_store_path=prepared.proposal_nonce_path,
        proposal_replay_high_water_store_id=prepared.proposal_store_id,
        proposal_replay_high_water_durability_receipt_id=(
            request.proposal_replay_high_water_durability_receipt_id
        ),
    )


def _authorize(
    provisional: ProvisionalConfig,
) -> tuple[ProvisionalConfig | None, tuple[str, ...]]:
    request = provisional.prepared.request
    policy = request.proposal_authority_policy
    try:
        context_digest = (
            architect_proposal_security_context_digest(provisional.runtime)
            if policy is not None else ""
        )
        now = int(request.now_epoch if request.now_epoch is not None else time.time())
    except (OSError, TypeError, ValueError):
        return None, (FAIL_SIGNER_CONFIG_PROPOSAL_POLICY_AUTHORIZATION_INVALID,)
    if policy is None:
        if request.proposal_policy_authorization is not None:
            return None, (FAIL_SIGNER_CONFIG_PROPOSAL_POLICY_AUTHORIZATION_INVALID,)
        return provisional, ()
    mapping = dict(provisional.mapping)
    raw = request.proposal_policy_authorization
    raw = raw.to_dict() if hasattr(raw, "to_dict") else raw
    runtime = replace(
        provisional.runtime,
        proposal_policy_authorization=raw,
        proposal_security_context_digest=context_digest,
    )
    try:
        _, verified = verify_architect_proposal_runtime_authorization(
            runtime,
            principal_key_resolver=(
                request.principal_key_resolver or FailClosedPrincipalKeyResolver()
            ),
            now_epoch=now,
        )
    except (OSError, TypeError, ValueError):
        return None, (FAIL_SIGNER_CONFIG_PROPOSAL_POLICY_AUTHORIZATION_INVALID,)
    mapping["proposal_policy_authorization"] = verified.to_dict()
    runtime = replace(
            runtime, proposal_policy_authorization=verified.to_dict(),
            proposal_security_context_digest=context_digest,
    )
    return ProvisionalConfig(provisional.prepared, mapping, runtime), ()


def _validate_write_and_accept(
    authorized: ProvisionalConfig,
) -> SignerServiceConfigSupplyResult:
    if validate_signer_socket_service_runtime_config(authorized.runtime):
        return reject_supply((
            FAIL_SIGNER_CONFIG_AUTHORITY_PROFILE_INVALID + ":runtime_config",
        ))
    prepared = authorized.prepared
    output = prepared.paths.output
    runtime_root = prepared.paths.runtime
    if output is None or runtime_root is None:
        return reject_supply((FAIL_SIGNER_CONFIG_WRITE_FAILED,))
    try:
        with runtime_operation_lock(str(output) + ".operation"):
            atomic_replace_confined_mapping(
                output, authorized.mapping,
                repo_root=prepared.repo_root, allowed_root=runtime_root,
            )
    except Exception:
        return reject_supply((FAIL_SIGNER_CONFIG_WRITE_FAILED,))
    return _accepted_result(authorized)


def _accepted_result(authorized: ProvisionalConfig) -> SignerServiceConfigSupplyResult:
    prepared = authorized.prepared
    request = prepared.request
    profile = prepared.profile
    config_digest = canonical_config_digest(authorized.mapping)
    receipt = _receipt(authorized, config_digest)
    return SignerServiceConfigSupplyResult(
        accepted=True, status=SIGNER_SERVICE_CONFIG_SUPPLY_ACCEPT,
        config_supply_receipt_id=str(receipt["config_supply_receipt_id"]),
        config_path=str(prepared.paths.output), config_digest=config_digest,
        socket_path=str(prepared.paths.socket),
        principal_id=str(profile["principal_id"]),
        reddog_id=str(profile["reddog_id"]),
        profile_count=len(tuple(authorized.mapping["key_provider_profiles"])),
        rejection_reasons=(),
        proposal_policy_configured=request.proposal_authority_policy is not None,
        proposal_attestation_id=(
            request.proposal_authority_policy.expected_payload.attestation_id
            if request.proposal_authority_policy is not None else None
        ),
        proposal_nonce_store_path=(
            str(prepared.proposal_nonce_path)
            if prepared.proposal_nonce_path is not None else None
        ),
    )


def _receipt(
    authorized: ProvisionalConfig, config_digest: str
) -> dict[str, Any]:
    prepared = authorized.prepared
    request = prepared.request
    policy = request.proposal_authority_policy
    receipt = {
        "schema_version": SIGNER_SERVICE_CONFIG_SCHEMA_VERSION,
        "config_digest": config_digest,
        "config_path": str(prepared.paths.output),
        "socket_path": str(prepared.paths.socket),
        "control_loop_anchor_path": str(prepared.paths.anchor),
        "principal_id": str(prepared.profile["principal_id"]),
        "reddog_id": str(prepared.profile["reddog_id"]),
        "profile_count": len(tuple(authorized.mapping["key_provider_profiles"])),
        "proposal_policy_configured": policy is not None,
        "proposal_attestation_id": (
            policy.expected_payload.attestation_id if policy is not None else None
        ),
        "proposal_nonce_store_path": (
            str(prepared.proposal_nonce_path)
            if prepared.proposal_nonce_path is not None else None
        ),
        "no_secret_values_written": True,
        "no_secret_values_resolved": True,
        "no_signer_started": True,
        "no_socket_bound": True,
    }
    receipt["config_supply_receipt_id"] = canonical_config_digest(receipt)
    return receipt


__all__ = ["materialize_signer_service_config"]
