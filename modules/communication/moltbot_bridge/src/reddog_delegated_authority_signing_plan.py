"""Canonical signing plan for delegated RedDog authority issuance."""

from __future__ import annotations

from typing import Any

from modules.communication.moltbot_bridge.src.reddog_signer_delegated_authority_runtime import (
    DelegatedAuthorityRuntimeRequest,
    PrincipalAuthorityRecord,
    SigningRequest,
    public_key_fingerprint,
)
from modules.communication.moltbot_bridge.src.reddog_signer_optional_authority_bindings import (
    attach_optional_authority_bindings,
)
from modules.communication.moltbot_bridge.src.reddog_work_order_signature_verifier import (
    PREFIX_IDENTITY,
    PREFIX_WORKAUTH,
    canonical_signing_input,
)


def build_delegated_authority_signing_requests(
    request: DelegatedAuthorityRuntimeRequest,
    principal: PrincipalAuthorityRecord,
    *,
    authority_tier: str,
    has_runtime_binding: bool,
) -> tuple[dict[str, Any], dict[str, Any], SigningRequest, SigningRequest]:
    """Build the two exact signer requests approved by elevated consensus."""

    identity, identity_request = _identity_signing_material(
        request, principal, authority_tier
    )
    work_authority, workauth_request = _workauth_signing_material(
        request, authority_tier, has_runtime_binding
    )
    return identity, work_authority, identity_request, workauth_request


def _identity_signing_material(
    request: DelegatedAuthorityRuntimeRequest,
    principal: PrincipalAuthorityRecord,
    authority_tier: str,
) -> tuple[dict[str, Any], SigningRequest]:
    identity = {
        "principal_id": request.principal_id,
        "principal_provider": request.principal_provider,
        "principal_public_key": request.principal_public_key,
        "principal_key_fingerprint": public_key_fingerprint(request.principal_public_key),
        "principal_wallet": principal.principal_wallet,
        "reddog_id": request.reddog_id,
        "reddog_public_key": request.reddog_public_key,
        "reddog_key_fingerprint": public_key_fingerprint(request.reddog_public_key),
        "repo_scope": list(principal.repo_scope),
        "foundup_scope": list(principal.foundup_scope),
        "reward_account": principal.reward_account,
        "owner_dae": principal.owner_dae,
        "revocation_policy": {
            "ttl_seconds": max(0, request.identity_expires_at - request.issued_at),
            "allowlist_bound": True,
            "kill_switch_ref": f"reddog_revocation:{request.reddog_id}",
        },
        "identity_nonce": request.identity_nonce,
        "issued_at": request.issued_at,
        "expires_at": request.identity_expires_at,
    }
    return identity, _signing_request(
        request,
        payload=identity,
        prefix=PREFIX_IDENTITY,
        signer_role="principal",
        signer_public_key=request.principal_public_key,
        nonce=request.identity_nonce,
        operation="delegate_reddog_identity",
        authority_tier=authority_tier,
    )


def _workauth_signing_material(
    request: DelegatedAuthorityRuntimeRequest,
    authority_tier: str,
    has_runtime_binding: bool,
) -> tuple[dict[str, Any], SigningRequest]:
    work_authority = _workauth_payload(request, authority_tier)
    if has_runtime_binding:
        work_authority["model_runtime_binding_receipt_id"] = str(
            request.model_runtime_binding_receipt_id
        )
        work_authority["model_runtime_binding_digest"] = str(
            request.model_runtime_binding_digest
        )
    attach_optional_authority_bindings(work_authority, request)
    return work_authority, _signing_request(
        request,
        payload=work_authority,
        prefix=PREFIX_WORKAUTH,
        signer_role="reddog",
        signer_public_key=request.reddog_public_key,
        nonce=request.work_authority_nonce,
        operation=request.requested_operation,
        authority_tier=authority_tier,
    )


def _signing_request(
    request: DelegatedAuthorityRuntimeRequest,
    *,
    payload: dict[str, Any],
    prefix: str,
    signer_role: str,
    signer_public_key: str,
    nonce: str,
    operation: str,
    authority_tier: str,
) -> SigningRequest:
    from modules.communication.moltbot_bridge.src.reddog_elevated_authority_consensus_contract import (
        canonical_json_digest,
    )

    signing_input = canonical_signing_input(payload, prefix)
    return SigningRequest(
        signing_input=signing_input,
        payload_digest=canonical_json_digest({"signing_input": signing_input}),
        signer_role=signer_role,
        signer_public_key=signer_public_key,
        requester_principal_id=request.principal_id,
        nonce=nonce,
        key_epoch=request.key_epoch,
        requested_operation=operation,
        authority_tier=authority_tier,
        consensus_receipt_digest=request.consensus_receipt_digest,
    )


def _workauth_payload(
    request: DelegatedAuthorityRuntimeRequest, authority_tier: str
) -> dict[str, Any]:
    return {
        "work_order_id": request.work_order_id,
        "work_order_digest": request.work_order_digest,
        "base_ref": request.base_ref,
        "principal_id": request.principal_id,
        "reddog_id": request.reddog_id,
        "repo_full_name": request.repo_full_name,
        "foundup_id": request.foundup_id,
        "allowed_paths": list(request.allowed_paths),
        "denied_paths": list(request.denied_paths),
        "requested_operation": request.requested_operation,
        "permission_snapshot_digest": request.permission_snapshot_digest,
        "queue_consumer_receipt_digest": request.queue_consumer_receipt_digest,
        "selected_slice": str(request.queue_consumer_receipt["slice_id"]),
        "wsp15_allocation_receipt": dict(request.wsp15_allocation_receipt),
        "wsp15_allocation_receipt_id": request.wsp15_allocation_receipt_id,
        "wsp15_allocation_digest": request.wsp15_allocation_digest,
        "wsp15_priority": request.wsp15_priority,
        "wsp15_mps_total": request.wsp15_mps_total,
        "wsp15_reasoning_tier": request.wsp15_reasoning_tier,
        "progressive_policy_stage_receipt_id": request.progressive_policy_stage_receipt_id,
        "progressive_policy_stage_digest": request.progressive_policy_stage_digest,
        "progressive_policy_stage_receipt": dict(request.progressive_policy_stage_receipt),
        "nonce": request.work_authority_nonce,
        "issued_at": request.issued_at,
        "expires_at": request.work_authority_expires_at,
        "valve_state_required": request.valve_state_required,
        "key_epoch": request.key_epoch,
        "signer_public_key": request.reddog_public_key,
        "authority_tier": authority_tier,
        "consensus_receipt_digest": request.consensus_receipt_digest,
        "sovereign_authorization_digest": request.sovereign_authorization_digest,
        "receipt_chain": [],
    }


__all__ = ["build_delegated_authority_signing_requests"]
