"""Typed delegated-authority request materialization for WRE queue work."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from modules.communication.moltbot_bridge.src.reddog_signer_delegated_authority_runtime import (
    DelegatedAuthorityRuntimeRequest,
)
from modules.communication.moltbot_bridge.src.reddog_work_order_binding import (
    canonical_full_work_order_digest,
)

def materialize_delegated_authority_request(
    *,
    profile: Mapping[str, Any],
    queue_receipt: Mapping[str, Any],
    work_order_id: str,
    work_order_digest: str,
    base_ref: str,
    foundup_id: str,
    allowed_paths: Sequence[str],
    denied_paths: Sequence[str],
    operation: str,
    publication_id: str,
    publication_binding_digest: str,
) -> DelegatedAuthorityRuntimeRequest:
    """Build the canonical signer request from already-validated inputs."""

    values = _core_fields(
        profile=profile,
        work_order_id=work_order_id,
        work_order_digest=work_order_digest,
        base_ref=base_ref,
        foundup_id=foundup_id,
        allowed_paths=allowed_paths,
        denied_paths=denied_paths,
        operation=operation,
    )
    values.update(_receipt_fields(
        queue_receipt,
        publication_id=publication_id,
        publication_binding_digest=publication_binding_digest,
    ))
    values.update(_lifetime_fields(profile))
    return DelegatedAuthorityRuntimeRequest(**values)


def _core_fields(
    *,
    profile: Mapping[str, Any],
    work_order_id: str,
    work_order_digest: str,
    base_ref: str,
    foundup_id: str,
    allowed_paths: Sequence[str],
    denied_paths: Sequence[str],
    operation: str,
) -> dict[str, Any]:
    return {
        "work_order_id": work_order_id,
        "work_order_digest": work_order_digest,
        "base_ref": base_ref,
        "principal_id": str(profile["principal_id"]),
        "principal_provider": str(profile["principal_provider"]),
        "principal_public_key": str(profile["principal_public_key"]),
        "reddog_id": str(profile["reddog_id"]),
        "reddog_public_key": str(profile["reddog_public_key"]),
        "repo_full_name": str(profile["repo_full_name"]),
        "foundup_id": foundup_id,
        "allowed_paths": tuple(allowed_paths),
        "denied_paths": tuple(denied_paths),
        "requested_operation": operation,
        "permission_snapshot_digest": str(
            profile["permission_snapshot_digest"]
        ),
    }


def _receipt_fields(
    queue_receipt: Mapping[str, Any],
    *,
    publication_id: str,
    publication_binding_digest: str,
) -> dict[str, Any]:
    return {
        "queue_consumer_receipt_digest": canonical_full_work_order_digest(
            queue_receipt
        ),
        "wsp15_allocation_receipt": dict(
            queue_receipt.get("wsp15_allocation_receipt") or {}
        ),
        "wsp15_allocation_receipt_id": _text(
            queue_receipt, "wsp15_allocation_receipt_id"
        ),
        "wsp15_allocation_digest": _text(
            queue_receipt, "wsp15_allocation_digest"
        ),
        "wsp15_priority": _text(queue_receipt, "wsp15_priority"),
        "wsp15_mps_total": int(queue_receipt.get("wsp15_mps_total")),
        "wsp15_reasoning_tier": _text(queue_receipt, "reasoning_tier"),
        "progressive_policy_stage_receipt_id": _text(
            queue_receipt, "progressive_policy_stage_receipt_id"
        ),
        "progressive_policy_stage_digest": _text(
            queue_receipt, "progressive_policy_stage_digest"
        ),
        "progressive_policy_stage_receipt": dict(
            queue_receipt.get("progressive_policy_stage_receipt") or {}
        ),
        "model_selection_receipt_id": _optional(
            queue_receipt, "model_selection_receipt_id"
        ),
        "model_selection_digest": _optional(
            queue_receipt, "model_selection_digest"
        ),
        "model_runtime_binding_receipt_id": _optional(
            queue_receipt, "model_runtime_binding_receipt_id"
        ),
        "model_runtime_binding_digest": _optional(
            queue_receipt, "model_runtime_binding_digest"
        ),
        "model_runtime_binding_verification_receipt_id": _optional(
            queue_receipt, "model_runtime_binding_verification_receipt_id"
        ),
        "model_runtime_binding_verification_digest": _optional(
            queue_receipt, "model_runtime_binding_verification_digest"
        ),
        "memex_supply_receipt_id": _optional(
            queue_receipt, "memex_supply_receipt_id"
        ),
        "memex_supply_digest": _optional(
            queue_receipt, "memex_supply_digest"
        ),
        "architect_fix_publication_receipt_id": publication_id or None,
        "architect_fix_publication_binding_digest": (
            publication_binding_digest or None
        ),
    }


def _lifetime_fields(profile: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "identity_nonce": str(profile["identity_nonce"]),
        "work_authority_nonce": str(profile["work_authority_nonce"]),
        "issued_at": int(profile["issued_at"]),
        "identity_expires_at": int(profile["identity_expires_at"]),
        "work_authority_expires_at": int(
            profile["work_authority_expires_at"]
        ),
        "valve_state_required": str(profile["valve_state_required"]),
        "key_epoch": str(profile["key_epoch"]),
        "consensus_receipt_digest": _optional(
            profile, "consensus_receipt_digest"
        ),
        "sovereign_authorization_digest": _optional(
            profile, "sovereign_authorization_digest"
        ),
    }


def _optional(payload: Mapping[str, Any], field: str) -> str | None:
    value = payload.get(field)
    return str(value) if value else None


def _text(payload: Mapping[str, Any], field: str) -> str:
    return str(payload.get(field) or "")


__all__ = ["materialize_delegated_authority_request"]
