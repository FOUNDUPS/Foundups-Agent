"""Authenticated single-model AutoResearch promotion-to-runtime composition.

This adapter composes existing gates without becoming a signer or authority.
It accepts only the process-local authenticated campaign-promotion result,
derives a non-authoritative deterministic production-selection preview, asks an
external boundary for independent benchmark and promotion signatures bound to
that preview, verifies the complete evidence chain, proves the verified
selection reproduces the preview ID, and finally invokes the existing runtime-
binding artifact supplier.  Panel candidates remain shadow-only.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping

from modules.communication.moltbot_bridge.src.reddog_work_order_signature_verifier import (
    SignatureVerifier,
)

from .model_autoresearch_authenticated_promotion_authority import (
    AuthenticatedCampaignPromotionSupplyResult,
    CampaignPromotionAuthorityRequest,
    VerifiedCampaignPromotionAuthority,
    rehydrate_signed_campaign_promotion_authority_receipt,
)
from .model_autoresearch_campaign_promotion_gate_supply import (
    rehydrate_model_autoresearch_campaign_promotion_gate_supply_receipt,
)
from .model_autoresearch_configured_gateway_evidence import digest_payload
from .model_autoresearch_production_authority_use import (
    CampaignPromotionAuthorityUseContext,
    trusted_campaign_authority_time,
    validate_campaign_promotion_authority_use,
)
from .model_autoresearch_production_binding_preflight import (
    preflight_preview_evidence,
    preflight_promotion_policy_digest,
    preflight_runtime_policy,
    preflight_trusted_keys,
    preflight_verification_dependencies,
)
from .model_autoresearch_production_binding_runner import (
    run_production_binding_transaction,
)
from .model_autoresearch_production_binding_transaction import (
    production_publication_identity,
)
from .model_intelligence_catalog import PromotionState
from .model_intelligence_outcomes import (
    ModelBenchmarkEvidenceReceipt,
    ModelOutcomeMetrics,
)
from .model_intelligence_selection import (
    ModelTaskRequirements,
    SelectionDecision,
    SelectionMode,
    SelectionPurpose,
    select_models_for_task,
)
from .model_promotion_gate import ModelPromotionGateDecision
from .model_runtime_binding import ModelRuntimeBindingPolicy
from .model_runtime_binding_artifact_supply import (
    ModelRuntimeBindingArtifactSupplyResult,
)
from .model_selection_artifact_supply import (
    ModelSelectionArtifactSupplyResult,
)
from .model_signed_evidence import (
    ModelEvidenceKeyResolver,
    rehydrate_model_catalog_snapshot,
)


MAX_GATE_ARTIFACT_BYTES = 1_048_576


@dataclass(frozen=True)
class SingleModelProductionSelectionPreview:
    """Non-authoritative subject presented to independent external signers."""

    selection_receipt_id: str
    catalog_snapshot_id: str
    candidate_model_id: str
    promotion_gate_receipt_id: str
    promotion_evidence_receipt_id: str
    promotion_policy_digest: str


@dataclass(frozen=True)
class SingleModelProductionBindingResult:
    """Successful selection and runtime-binding artifact composition."""

    preview: SingleModelProductionSelectionPreview
    selection: ModelSelectionArtifactSupplyResult
    runtime_binding: ModelRuntimeBindingArtifactSupplyResult


def build_authenticated_single_model_production_selection_preview(
    *,
    repo_root: Path | str,
    authenticated_promotion: AuthenticatedCampaignPromotionSupplyResult,
    catalog_snapshot: Mapping[str, Any],
    requirements: ModelTaskRequirements,
    authority_use: CampaignPromotionAuthorityUseContext,
) -> SingleModelProductionSelectionPreview:
    """Derive the exact selection ID that external evidence must sign.

    The temporary evidence object is confined to this function.  It is never
    returned, serialized, persisted, or accepted by the runtime-binding gate.
    The final adapter invocation must reproduce the same selection ID using
    independently verified signed evidence.
    """

    root = Path(repo_root).resolve()
    now = trusted_campaign_authority_time(authority_use)
    gate = _authenticated_single_gate(
        authenticated_promotion,
        root,
        authority_use=authority_use,
        now=now,
    )
    return _selection_preview_for_gate(
        authenticated_promotion, catalog_snapshot, requirements, gate
    )


def _selection_preview_for_gate(
    authenticated_promotion: AuthenticatedCampaignPromotionSupplyResult,
    catalog_snapshot: Mapping[str, Any],
    requirements: ModelTaskRequirements,
    gate: Any,
) -> SingleModelProductionSelectionPreview:
    normalized = _single_production_requirements(requirements, gate.task_family)
    snapshot = rehydrate_model_catalog_snapshot(catalog_snapshot)
    promotion = gate.promotion_evidence_receipt
    assert promotion is not None
    cards = [
        card for card in snapshot.cards if card.canonical_model_id == gate.candidate_id
    ]
    if len(cards) != 1 or cards[0].promotion_state != PromotionState.CHAMPION:
        raise ValueError("single_model_production_catalog_champion_required")

    provisional = preflight_preview_evidence(gate, _benchmark_for_gate(gate), promotion)
    selection = select_models_for_task(
        snapshot,
        normalized,
        production_evidence=provisional,
    )
    if (
        selection.decision != SelectionDecision.SELECTED
        or selection.selected_model_ids != (gate.candidate_id,)
    ):
        raise ValueError("single_model_production_preview_rejected")
    policy_digest = preflight_promotion_policy_digest(authenticated_promotion, gate)
    return SingleModelProductionSelectionPreview(
        selection_receipt_id=selection.receipt_id,
        catalog_snapshot_id=snapshot.snapshot_id,
        candidate_model_id=gate.candidate_id,
        promotion_gate_receipt_id=gate.receipt_id,
        promotion_evidence_receipt_id=promotion.receipt_id,
        promotion_policy_digest=policy_digest,
    )


def bind_authenticated_single_model_promotion_to_runtime(
    *,
    repo_root: Path | str,
    authenticated_promotion: AuthenticatedCampaignPromotionSupplyResult,
    catalog_snapshot: Mapping[str, Any],
    requirements: ModelTaskRequirements,
    authority_use: CampaignPromotionAuthorityUseContext,
    signed_evidence_provider: Callable[
        [SingleModelProductionSelectionPreview], Mapping[str, Any]
    ],
    evidence_key_resolver: ModelEvidenceKeyResolver,
    evidence_signature_verifier: SignatureVerifier,
    trusted_keys_payload: Mapping[str, Any],
    runtime_policy: Mapping[str, Any] | ModelRuntimeBindingPolicy,
    selection_output_path: Path | str,
    runtime_binding_output_path: Path | str,
) -> SingleModelProductionBindingResult:
    """Verify external evidence and produce one existing runtime-binding artifact."""
    inputs = _prepare_binding_inputs(
        repo_root=repo_root,
        authenticated_promotion=authenticated_promotion,
        catalog_snapshot=catalog_snapshot,
        requirements=requirements,
        authority_use=authority_use,
        signed_evidence_provider=signed_evidence_provider,
        evidence_key_resolver=evidence_key_resolver,
        evidence_signature_verifier=evidence_signature_verifier,
        trusted_keys_payload=trusted_keys_payload,
        runtime_policy=runtime_policy,
        selection_output_path=selection_output_path,
        runtime_binding_output_path=runtime_binding_output_path,
    )
    selection, runtime = run_production_binding_transaction(
        inputs, signed_evidence_provider
    )
    return SingleModelProductionBindingResult(inputs["preview"], selection, runtime)


def _prepare_binding_inputs(**values: Any) -> dict[str, Any]:
    root = Path(values["repo_root"]).resolve()
    selection_output = _outside_repo_output(values["selection_output_path"], root)
    runtime_output = _outside_repo_output(values["runtime_binding_output_path"], root)
    if selection_output == runtime_output:
        raise ValueError("single_model_production_output_paths_must_differ")
    provider = values["signed_evidence_provider"]
    if not callable(provider):
        raise ValueError("single_model_production_evidence_provider_invalid")
    preflight_verification_dependencies(
        evidence_key_resolver=values["evidence_key_resolver"],
        evidence_signature_verifier=values["evidence_signature_verifier"],
    )
    now = trusted_campaign_authority_time(values["authority_use"])
    preview = build_authenticated_single_model_production_selection_preview(
        repo_root=root,
        authenticated_promotion=values["authenticated_promotion"],
        catalog_snapshot=values["catalog_snapshot"],
        requirements=values["requirements"],
        authority_use=values["authority_use"],
    )
    gate = _authenticated_single_gate(
        values["authenticated_promotion"],
        root,
        authority_use=values["authority_use"],
        now=now,
    )
    return _normalized_binding_inputs(
        values, root, selection_output, runtime_output, now, preview, gate
    )


def _normalized_binding_inputs(
    values: Mapping[str, Any],
    root: Path,
    selection_output: Path,
    runtime_output: Path,
    now: int,
    preview: SingleModelProductionSelectionPreview,
    gate: Any,
) -> dict[str, Any]:
    authenticated = values["authenticated_promotion"]
    runtime_policy = preflight_runtime_policy(
        values["runtime_policy"],
        gate=gate,
        authority_receipt_id=authenticated.authority.receipt.receipt_id,
    )
    trusted_keys = preflight_trusted_keys(
        values["trusted_keys_payload"],
        key_resolver=values["evidence_key_resolver"],
    )
    inputs = {
        **dict(values),
        "root": root,
        "selection_output": selection_output,
        "runtime_output": runtime_output,
        "now": now,
        "preview": preview,
        "gate": gate,
        "snapshot": rehydrate_model_catalog_snapshot(values["catalog_snapshot"]),
        "requirements": _single_production_requirements(
            values["requirements"], gate.task_family
        ),
        "runtime_policy": runtime_policy,
        "trusted_keys": trusted_keys,
        "key_resolver": values["evidence_key_resolver"],
        "signature_verifier": values["evidence_signature_verifier"],
    }
    inputs["publication_identity"] = production_publication_identity(
        authenticated_promotion=authenticated,
        preview=preview,
        runtime_policy=runtime_policy,
        trusted_keys=trusted_keys,
        selection_output=selection_output,
        runtime_output=runtime_output,
    )
    return inputs


def _authenticated_single_gate(
    value: AuthenticatedCampaignPromotionSupplyResult,
    repo_root: Path,
    *,
    authority_use: CampaignPromotionAuthorityUseContext,
    now: int,
):
    if type(value) is not AuthenticatedCampaignPromotionSupplyResult:
        raise ValueError("authenticated_campaign_promotion_result_required")
    authority = value.authority
    if (
        type(authority) is not VerifiedCampaignPromotionAuthority
        or type(authority.request) is not CampaignPromotionAuthorityRequest
    ):
        raise ValueError("authenticated_campaign_promotion_authority_invalid")
    validate_campaign_promotion_authority_use(authority, authority_use, now=now)
    rehydrated_authority_receipt = (
        rehydrate_signed_campaign_promotion_authority_receipt(
            authority.receipt.to_dict()
        )
    )
    if (
        authority.authenticated is not True
        or authority.nonce_consumed is not True
        or authority.durable_store_receipt_id != authority.receipt.receipt_id
        or authority.receipt.request_id != authority.request.request_id
        or authority.receipt.request_digest
        != digest_payload(authority.request.to_dict())
        or rehydrated_authority_receipt != authority.receipt
    ):
        raise ValueError("authenticated_campaign_promotion_authority_invalid")
    if len(authority.request.candidate_ids) != 1:
        raise ValueError("panel_promotion_is_shadow_only")
    return _authenticated_gate_artifact(value, authority, repo_root)


def _authenticated_gate_artifact(
    value: AuthenticatedCampaignPromotionSupplyResult,
    authority: VerifiedCampaignPromotionAuthority,
    repo_root: Path,
):
    supply = value.supply
    if not supply.accepted or len(supply.promotion_gate_receipt_ids) != 1:
        raise ValueError("authenticated_campaign_promotion_supply_invalid")
    if (
        supply.source_execution_receipt_id
        != authority.request.source_execution_receipt_id
    ):
        raise ValueError("authenticated_campaign_promotion_execution_mismatch")
    path = _outside_repo_existing_artifact(supply.output_path, repo_root)
    payload = _read_bounded_json(path)
    receipt = rehydrate_model_autoresearch_campaign_promotion_gate_supply_receipt(
        payload
    )
    if (
        receipt.receipt_id != supply.supply_receipt_id
        or receipt.source_execution_receipt_id != supply.source_execution_receipt_id
        or tuple(item.receipt_id for item in receipt.promotion_gate_receipts)
        != supply.promotion_gate_receipt_ids
        or len(receipt.promotion_gate_receipts) != 1
    ):
        raise ValueError("authenticated_campaign_promotion_supply_mismatch")
    gate = receipt.promotion_gate_receipts[0]
    promotion = gate.promotion_evidence_receipt
    if (
        gate.decision != ModelPromotionGateDecision.PROMOTE_CHAMPION
        or gate.candidate_id != authority.request.candidate_ids[0]
        or gate.candidate_id.startswith("model_panel_candidate:")
        or promotion is None
        or promotion.promotion_authority_receipt_id != authority.request.request_id
        or promotion.signed_promotion_receipt_id != authority.receipt.receipt_id
    ):
        raise ValueError("authenticated_single_model_promotion_gate_required")
    return gate


def _benchmark_for_gate(gate):
    # The authenticated authority request binds the exact execution receipt;
    # the gate binds the benchmark receipt ID.  Rehydrate the already-verified
    # gate artifact and use the exact benchmark record supplied later as the
    # final authority.  For preview, only fields used by deterministic ranking
    # are needed; promotion evidence owns the pass-rate and benchmark lineage.
    promotion = gate.promotion_evidence_receipt
    assert promotion is not None
    return ModelBenchmarkEvidenceReceipt(
        receipt_id=promotion.benchmark_evidence_receipt_id,
        model_id=gate.candidate_id,
        task_family=gate.task_family,
        task_set_digest=gate.policy.required_task_set_digest,
        held_out_split_digest=gate.policy.required_held_out_split_digest,
        prompt_topology_digest="selection-preview-only",
        verifier_digest=gate.policy.required_verifier_digest,
        verifier_receipt_id="selection-preview-only",
        sample_count=gate.policy.min_sample_count,
        accepted_count=gate.policy.min_sample_count,
        verifier_pass_rate=max(gate.policy.min_verifier_pass_rate, 1.0),
        metrics=ModelOutcomeMetrics(),
    )


def _single_production_requirements(
    value: ModelTaskRequirements,
    task_family: str,
) -> ModelTaskRequirements:
    if type(value) is not ModelTaskRequirements:
        raise ValueError("single_model_production_requirements_required")
    normalized = value.normalized()
    if (
        normalized.selection_mode != SelectionMode.SINGLE
        or normalized.purpose != SelectionPurpose.PRODUCTION
        or normalized.max_candidates != 1
    ):
        raise ValueError("panel_promotion_is_shadow_only")
    if normalized.task_family != task_family:
        raise ValueError("single_model_production_task_family_mismatch")
    return normalized


def _outside_repo_output(value: Path | str, repo_root: Path) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = repo_root.parent / path
    resolved = path.resolve()
    if resolved == repo_root or resolved.is_relative_to(repo_root):
        raise ValueError("single_model_production_output_inside_repo")
    return resolved


def _outside_repo_existing_artifact(value: Any, repo_root: Path) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("authenticated_campaign_promotion_artifact_missing")
    path = _outside_repo_output(value, repo_root)
    if path.is_symlink() or not path.is_file():
        raise ValueError("authenticated_campaign_promotion_artifact_invalid")
    return path


def _read_bounded_json(path: Path) -> Mapping[str, Any]:
    if path.stat().st_size > MAX_GATE_ARTIFACT_BYTES:
        raise ValueError("authenticated_campaign_promotion_artifact_too_large")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError("authenticated_campaign_promotion_artifact_invalid")
    return payload


__all__ = [
    "CampaignPromotionAuthorityUseContext",
    "SingleModelProductionBindingResult",
    "SingleModelProductionSelectionPreview",
    "bind_authenticated_single_model_promotion_to_runtime",
    "build_authenticated_single_model_production_selection_preview",
]
