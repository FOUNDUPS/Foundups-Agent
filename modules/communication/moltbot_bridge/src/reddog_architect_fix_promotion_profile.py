"""Authority-profile projection for an admitted architect FIX promotion."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


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
    return profile


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
        "model_runtime_binding_runtime_surface": runtime["runtime_surface"],
        "model_runtime_binding_principal_model": runtime["principal_model"],
        "model_runtime_binding_panel_models": list(runtime["panel_models"]),
        "model_runtime_binding_role_bindings": list(runtime["role_bindings"]),
    }


__all__ = [
    "ArchitectFixPromotionProfileInputs",
    "promoted_authority_profile",
]
