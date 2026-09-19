"""Authority-profile projection for an admitted architect FIX promotion."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Mapping

from modules.communication.moltbot_bridge.src.reddog_authority_profile_rehydration import (
    rehydrate_authority_profile_runtime,
    rehydrate_authority_profile_source,
    snapshot_authority_profile_m2m,
    worker_plan_matches_execution_scope,
)
from modules.communication.moltbot_bridge.src.reddog_authority_profile_safety import (
    authority_profile_runtime_unknown_field_paths,
    authority_profile_malformed_digest_paths,
    authority_profile_secret_field_paths,
    authority_profile_unknown_field_paths,
)

from modules.communication.moltbot_bridge.src.reddog_architect_fix_candidate_gate import (
    snapshot_architect_fix_plan_lineage,
)
from modules.communication.moltbot_bridge.src.reddog_architect_fix_promotion_records import (
    ArchitectFixPromotionReason,
)


_AUTHORITY_PROFILE_REQUIRED = (
    "principal_id",
    "principal_provider",
    "principal_public_key",
    "reddog_id",
    "reddog_public_key",
    "repo_full_name",
    "foundup_id",
    "allowed_paths",
    "denied_paths",
    "requested_operation",
    "permission_snapshot_digest",
    "identity_nonce",
    "work_authority_nonce",
    "issued_at",
    "identity_expires_at",
    "work_authority_expires_at",
    "valve_state_required",
    "key_epoch",
    "consensus_receipt_digest",
    "authority_profile_source_receipt_id",
    "required_tests",
    "required_policy_gates",
)



@dataclass(frozen=True)
class ArchitectFixPromotionProfileInputs:
    authority_profile: Mapping[str, Any]
    verified_authority_identity: Mapping[str, Any]
    determination: Mapping[str, Any]
    allocation: Mapping[str, Any]
    model_selection_receipt: Mapping[str, Any]
    model_selection: Mapping[str, Any]
    model_selection_digest: str
    model_runtime_binding_receipt: Mapping[str, Any] | None
    model_runtime_binding: Mapping[str, Any]
    model_runtime_binding_digest: str | None
    memex_supply: Mapping[str, Any]
    memex_supply_digest: str
    proposal_admission: Mapping[str, Any]
    proposal_admission_digest: str
    proposal_authenticity_attestation_id: str
    proposal_authenticity_attestation_digest: str
    proposal_policy_authorization_id: str
    proposal_policy_authorization_digest: str
    proposal_signer_runtime_context_digest: str
    work_order_id: str
    queue_item_id: str
    claim_id: str
    holoindex_evidence: Mapping[str, Any]


def prepare_architect_fix_promotion_inputs(
    determination: Mapping[str, Any], profile: Mapping[str, Any],
) -> tuple[Mapping[str, Any], Mapping[str, Any], tuple[str, ...]]:
    """Freeze one raw/wrapped determination and source profile before effects.

    A declared proposal plan must match the explicit profile plan and scope.
    This is consistency validation, not signing or current execution authority.
    The outer receipt shape is preserved so repeated preflight selects once.
    """
    reasons = []
    try:
        if (type(profile) is dict and "bounded_worker_plan" in profile
                and type(profile["bounded_worker_plan"]) is not dict):
            raise ValueError("bounded_worker_plan_not_plain_mapping")
        profile = snapshot_authority_profile_m2m(profile)
        reasons.extend(_validate_authority_profile(profile))
        profile = rehydrate_authority_profile_source(profile)
    except (TypeError, ValueError, RecursionError, OverflowError):
        reasons.append(ArchitectFixPromotionReason.AUTHORITY_PROFILE_INCOMPLETE
                       + ":typed_rehydration")
    if reasons:
        return {}, {}, tuple(dict.fromkeys(reasons))
    try:
        determination = _snapshot_promotion_determination(determination, profile)
    except (TypeError, ValueError, RecursionError, OverflowError):
        return {}, {}, (ArchitectFixPromotionReason.AUTHORITY_PROFILE_INCOMPLETE
                        + ":proposal_plan_binding",)
    return determination, profile, ()


def _snapshot_promotion_determination(value, profile):
    if type(value) is not dict:
        raise ValueError("determination_not_plain_mapping")
    receipt = value.get("receipt")
    if receipt is not None and type(receipt) is not dict:
        raise ValueError("determination_receipt_not_plain_mapping")
    determination, bound = snapshot_architect_fix_plan_lineage(
        receipt if receipt else value, profile.get("bounded_worker_plan"),
    )
    if bound and not worker_plan_matches_execution_scope(
        profile["bounded_worker_plan"], profile,
    ):
        raise ValueError("profile_proposal_plan_scope_mismatch")
    # Freeze absence too: a later callback cannot add a previously absent plan.
    detached = json.loads(json.dumps(determination, allow_nan=False))
    return {"receipt": detached} if receipt else detached


def _validate_authority_profile(profile: Mapping[str, Any]) -> list[str]:
    if type(profile) is not dict or not profile:
        return [ArchitectFixPromotionReason.AUTHORITY_PROFILE_MISSING]
    missing = [
        field
        for field in _AUTHORITY_PROFILE_REQUIRED
        if field not in profile or profile.get(field) in (None, "", (), [], {})
    ]
    reasons = [
        ArchitectFixPromotionReason.AUTHORITY_PROFILE_INCOMPLETE + ":" + field
        for field in missing
    ]
    reasons.extend(
        ArchitectFixPromotionReason.AUTHORITY_PROFILE_SECRET_FIELD + ":" + path
        for path in authority_profile_secret_field_paths(profile)
    )
    reasons.extend(
        ArchitectFixPromotionReason.AUTHORITY_PROFILE_INCOMPLETE
        + ":unknown_field:"
        + path
        for path in authority_profile_unknown_field_paths(profile, seed=False)
    )
    reasons.extend(
        ArchitectFixPromotionReason.AUTHORITY_PROFILE_INCOMPLETE
        + ":digest_format:"
        + path
        for path in authority_profile_malformed_digest_paths(profile)
    )
    return reasons



def promoted_authority_profile(
    inputs: ArchitectFixPromotionProfileInputs,
) -> Mapping[str, Any]:
    profile = {
        **inputs.authority_profile,
        **inputs.verified_authority_identity,
    }
    binding = _operational_binding(inputs)
    profile.update(_profile_updates(inputs, binding))
    if inputs.model_runtime_binding:
        profile.update(_runtime_binding_fields(
            inputs.model_runtime_binding_receipt,
            inputs.model_runtime_binding,
        ))
    unknown = authority_profile_runtime_unknown_field_paths(profile)
    if unknown:
        raise ValueError(f"architect_fix_authority_profile_invalid:{unknown[0]}")
    return rehydrate_authority_profile_runtime(profile)


def _operational_binding(
    inputs: ArchitectFixPromotionProfileInputs,
) -> dict[str, Any]:
    determination = inputs.determination
    selection = inputs.model_selection
    runtime = inputs.model_runtime_binding
    memex = inputs.memex_supply
    determination_id = str(determination["determination_receipt_id"])
    binding = {
        "work_order_id": inputs.work_order_id,
        "snapshot_receipt_id": str(determination.get("snapshot_receipt_id") or ""),
        "context_view_id": str(determination.get("context_view_id") or ""),
        "evidence_bundle_id": str(determination.get("evidence_bundle_id") or ""),
        "determination_id": determination_id,
        "readonly_audit_decision_id": determination_id,
        "architect_determination_receipt_id": determination_id,
        "queue_item_id": inputs.queue_item_id,
        "claim_id": inputs.claim_id,
        "authorized_base_sha": inputs.proposal_admission["repo_head_sha"],
        "wsp15_allocation_receipt": dict(inputs.allocation),
        "model_catalog_snapshot_id": selection["catalog_snapshot_id"],
        "model_selection_receipt_id": selection["receipt_id"],
        "model_selection_digest": inputs.model_selection_digest,
        "model_selection_receipt": dict(inputs.model_selection_receipt),
        "model_runtime_binding_receipt_id": runtime.get("receipt_id", ""),
        "model_runtime_binding_digest": inputs.model_runtime_binding_digest or "",
        "memex_supply_receipt_id": memex["receipt_id"],
        "memex_supply_digest": inputs.memex_supply_digest,
        "proposal_admission_receipt_id": inputs.proposal_admission["receipt_id"],
        "proposal_admission_digest": inputs.proposal_admission_digest,
        "proposal_admission": dict(inputs.proposal_admission),
        **_proposal_authority_binding(inputs),
        "holoindex_evidence": dict(inputs.holoindex_evidence),
    }
    if runtime:
        binding.update(
            _runtime_binding_fields(inputs.model_runtime_binding_receipt, runtime)
        )
    return binding


def _profile_updates(
    inputs: ArchitectFixPromotionProfileInputs,
    binding: Mapping[str, Any],
) -> dict[str, Any]:
    determination = inputs.determination
    selection = inputs.model_selection
    runtime = inputs.model_runtime_binding
    memex = inputs.memex_supply
    determination_id = str(determination["determination_receipt_id"])
    return {
        "work_order_id": inputs.work_order_id,
        "base_ref": inputs.proposal_admission["repo_head_sha"],
        "authorized_base_sha": inputs.proposal_admission["repo_head_sha"],
        "task_summary": str(
            inputs.authority_profile.get("task_summary")
            or f"RedDog architect FIX promotion for {determination.get('next_slice_name')}."
        ),
        "wsp15_allocation_receipt": dict(inputs.allocation),
        "snapshot_receipt_id": binding["snapshot_receipt_id"],
        "context_view_id": binding["context_view_id"],
        "evidence_bundle_id": binding["evidence_bundle_id"],
        "readonly_audit_decision_id": determination_id,
        "determination_id": determination_id,
        "model_catalog_snapshot_id": selection["catalog_snapshot_id"],
        "model_selection_receipt_id": selection["receipt_id"],
        "model_selection_digest": inputs.model_selection_digest,
        "model_selection_receipt": dict(inputs.model_selection_receipt),
        "model_runtime_binding_receipt_id": runtime.get("receipt_id", ""),
        "model_runtime_binding_digest": inputs.model_runtime_binding_digest or "",
        "memex_supply_receipt_id": memex["receipt_id"],
        "memex_supply_digest": inputs.memex_supply_digest,
        "proposal_admission_receipt_id": inputs.proposal_admission["receipt_id"],
        "proposal_admission_digest": inputs.proposal_admission_digest,
        "proposal_admission": dict(inputs.proposal_admission),
        **_proposal_authority_binding(inputs),
        "operational_context_binding": binding,
        "holoindex_evidence": dict(inputs.holoindex_evidence),
    }


def _proposal_authority_binding(
    inputs: ArchitectFixPromotionProfileInputs,
) -> dict[str, str]:
    return {
        "proposal_authenticity_attestation_id": (
            inputs.proposal_authenticity_attestation_id
        ),
        "proposal_authenticity_attestation_digest": (
            inputs.proposal_authenticity_attestation_digest
        ),
        "proposal_policy_authorization_id": (
            inputs.proposal_policy_authorization_id
        ),
        "proposal_policy_authorization_digest": (
            inputs.proposal_policy_authorization_digest
        ),
        "proposal_signer_runtime_context_digest": (
            inputs.proposal_signer_runtime_context_digest
        ),
    }


def _runtime_binding_fields(
    receipt: Mapping[str, Any] | None,
    runtime: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "model_runtime_binding_receipt": dict(receipt or {}),
        "model_runtime_binding_verification_receipt": dict(
            runtime.get("verification_receipt") or {}
        ),
        "model_runtime_binding_verification_receipt_id": str(
            runtime.get("verification_receipt_id") or ""
        ),
        "model_runtime_binding_verification_digest": str(
            runtime.get("verification_receipt_digest") or ""
        ),
        "model_runtime_binding_runtime_surface": runtime["runtime_surface"],
        "model_runtime_binding_principal_model": runtime["principal_model"],
        "model_runtime_binding_panel_models": list(runtime["panel_models"]),
        "model_runtime_binding_role_bindings": list(runtime["role_bindings"]),
    }


__all__ = [
    "ArchitectFixPromotionProfileInputs",
    "promoted_authority_profile",
    "prepare_architect_fix_promotion_inputs",
]
