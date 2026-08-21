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
from typing import Any, Callable, Mapping, cast

from modules.communication.moltbot_bridge.src.reddog_work_order_signature_verifier import (
    NonceStore,
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
    run_reddog_model_runtime_binding_artifact_supply,
)
from .model_selection_artifact_supply import (
    EVIDENCE_BUNDLE_SCHEMA_VERSION,
    ModelSelectionArtifactSupplyResult,
    run_reddog_model_selection_artifact_supply,
)
from .model_signed_evidence import (
    ModelEvidenceKeyResolver,
    ModelSignedEvidenceReceipt,
    VerifiedModelEvidenceEntry,
    VerifiedModelProductionEvidence,
    build_verified_model_production_evidence,
    rehydrate_model_benchmark_evidence_receipt,
    rehydrate_model_catalog_snapshot,
    rehydrate_model_promotion_evidence_receipt,
    rehydrate_model_signed_evidence_receipt,
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


@dataclass(frozen=True)
class _PreviewSignatureReference:
    """Non-exported non-signature marker used only to compute a preview ID."""

    receipt_id: str


def build_authenticated_single_model_production_selection_preview(
    *,
    repo_root: Path | str,
    authenticated_promotion: AuthenticatedCampaignPromotionSupplyResult,
    catalog_snapshot: Mapping[str, Any],
    requirements: ModelTaskRequirements,
) -> SingleModelProductionSelectionPreview:
    """Derive the exact selection ID that external evidence must sign.

    The temporary evidence object is confined to this function.  It is never
    returned, serialized, persisted, or accepted by the runtime-binding gate.
    The final adapter invocation must reproduce the same selection ID using
    independently verified signed evidence.
    """

    root = Path(repo_root).resolve()
    gate = _authenticated_single_gate(authenticated_promotion, root)
    normalized = _single_production_requirements(requirements, gate.task_family)
    snapshot = rehydrate_model_catalog_snapshot(catalog_snapshot)
    promotion = gate.promotion_evidence_receipt
    assert promotion is not None
    cards = [card for card in snapshot.cards if card.canonical_model_id == gate.candidate_id]
    if len(cards) != 1 or cards[0].promotion_state != PromotionState.CHAMPION:
        raise ValueError("single_model_production_catalog_champion_required")

    # Existing production selection is deterministic but requires a typed
    # evidence carrier.  These private markers satisfy only the pure preview
    # calculation; real signatures are verified before any artifact is written.
    marker = _PreviewSignatureReference(
        receipt_id="selection-preview-only:" + gate.receipt_id
    )
    provisional = VerifiedModelProductionEvidence(
        entries=(
            VerifiedModelEvidenceEntry(
                model_id=gate.candidate_id,
                benchmark_receipt=_benchmark_for_gate(gate),
                promotion_receipt=promotion,
                benchmark_signature_receipt=cast(ModelSignedEvidenceReceipt, marker),
                promotion_signature_receipt=cast(ModelSignedEvidenceReceipt, marker),
            ),
        ),
        signed_evidence_verified=False,
    )
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
    policy_digest = digest_payload([gate.policy.to_dict()])
    if policy_digest != authenticated_promotion.authority.request.promotion_policy_digest:
        raise ValueError("single_model_production_policy_authority_mismatch")
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
    signed_evidence_provider: Callable[
        [SingleModelProductionSelectionPreview], Mapping[str, Any]
    ],
    evidence_key_resolver: ModelEvidenceKeyResolver,
    evidence_signature_verifier: SignatureVerifier,
    evidence_nonce_store: NonceStore,
    trusted_keys_payload: Mapping[str, Any],
    runtime_policy: Mapping[str, Any] | ModelRuntimeBindingPolicy,
    selection_output_path: Path | str,
    runtime_binding_output_path: Path | str,
    now: int,
) -> SingleModelProductionBindingResult:
    """Verify external evidence and produce one existing runtime-binding artifact."""

    root = Path(repo_root).resolve()
    selection_output = _outside_repo_output(selection_output_path, root)
    runtime_output = _outside_repo_output(runtime_binding_output_path, root)
    if selection_output == runtime_output:
        raise ValueError("single_model_production_output_paths_must_differ")

    preview = build_authenticated_single_model_production_selection_preview(
        repo_root=root,
        authenticated_promotion=authenticated_promotion,
        catalog_snapshot=catalog_snapshot,
        requirements=requirements,
    )
    gate = _authenticated_single_gate(authenticated_promotion, root)
    bundle = signed_evidence_provider(preview)
    verified, benchmark, promotion = _verify_external_evidence_bundle(
        bundle=bundle,
        preview=preview,
        gate=gate,
        key_resolver=evidence_key_resolver,
        signature_verifier=evidence_signature_verifier,
        nonce_store=evidence_nonce_store,
        now=int(now),
    )
    snapshot = rehydrate_model_catalog_snapshot(catalog_snapshot)
    normalized = _single_production_requirements(requirements, gate.task_family)
    reproduced = select_models_for_task(
        snapshot,
        normalized,
        production_evidence=verified,
    )
    if (
        reproduced.receipt_id != preview.selection_receipt_id
        or reproduced.selected_model_ids != (preview.candidate_model_id,)
    ):
        raise ValueError("single_model_production_preview_not_reproduced")

    selection_result = run_reddog_model_selection_artifact_supply(
        repo_root=root,
        catalog_snapshot=catalog_snapshot,
        verified_evidence_bundle=verified,
        requirements=normalized,
        output_path=selection_output,
    )
    if (
        not selection_result.accepted
        or selection_result.selection_receipt_id != preview.selection_receipt_id
    ):
        raise ValueError("single_model_production_selection_supply_rejected")

    runtime_result = run_reddog_model_runtime_binding_artifact_supply(
        repo_root=root,
        catalog_snapshot=catalog_snapshot,
        # Consume the exact persisted JSON artifact, not an in-memory dataclass
        # projection whose tuple fields have not crossed the JSON boundary.
        model_selection_receipt=_read_bounded_json(selection_output),
        benchmark_evidence_receipts=(benchmark.to_dict(),),
        promotion_evidence_receipts=(promotion.to_dict(),),
        verified_evidence_bundle=bundle,
        trusted_keys_payload=trusted_keys_payload,
        runtime_policy=runtime_policy,
        output_path=runtime_output,
        key_resolver=evidence_key_resolver,
        signature_verifier=evidence_signature_verifier,
        now=int(now),
    )
    if not runtime_result.accepted:
        raise ValueError(
            "single_model_production_runtime_binding_rejected:"
            + ",".join(runtime_result.rejection_reasons)
        )
    if runtime_result.selection_receipt_id != preview.selection_receipt_id:
        raise ValueError("single_model_production_runtime_selection_mismatch")
    return SingleModelProductionBindingResult(
        preview=preview,
        selection=selection_result,
        runtime_binding=runtime_result,
    )


def _authenticated_single_gate(
    value: AuthenticatedCampaignPromotionSupplyResult,
    repo_root: Path,
):
    if type(value) is not AuthenticatedCampaignPromotionSupplyResult:
        raise ValueError("authenticated_campaign_promotion_result_required")
    authority = value.authority
    if (
        type(authority) is not VerifiedCampaignPromotionAuthority
        or type(authority.request) is not CampaignPromotionAuthorityRequest
    ):
        raise ValueError("authenticated_campaign_promotion_authority_invalid")
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
        or authority.receipt.request_digest != digest_payload(authority.request.to_dict())
        or rehydrated_authority_receipt != authority.receipt
    ):
        raise ValueError("authenticated_campaign_promotion_authority_invalid")
    if len(authority.request.candidate_ids) != 1:
        raise ValueError("panel_promotion_is_shadow_only")
    supply = value.supply
    if not supply.accepted or len(supply.promotion_gate_receipt_ids) != 1:
        raise ValueError("authenticated_campaign_promotion_supply_invalid")
    if supply.source_execution_receipt_id != authority.request.source_execution_receipt_id:
        raise ValueError("authenticated_campaign_promotion_execution_mismatch")
    path = _outside_repo_existing_artifact(supply.output_path, repo_root)
    payload = _read_bounded_json(path)
    receipt = rehydrate_model_autoresearch_campaign_promotion_gate_supply_receipt(payload)
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


def _verify_external_evidence_bundle(
    *,
    bundle: Mapping[str, Any],
    preview: SingleModelProductionSelectionPreview,
    gate: Any,
    key_resolver: ModelEvidenceKeyResolver,
    signature_verifier: SignatureVerifier,
    nonce_store: NonceStore,
    now: int,
):
    if not isinstance(bundle, Mapping) or bundle.get("schema_version") != EVIDENCE_BUNDLE_SCHEMA_VERSION:
        raise ValueError("single_model_production_evidence_bundle_invalid")
    if (
        bundle.get("catalog_snapshot_id") != preview.catalog_snapshot_id
        or bundle.get("selection_receipt_id") != preview.selection_receipt_id
    ):
        raise ValueError("single_model_production_evidence_preview_mismatch")
    entries = bundle.get("entries")
    if not isinstance(entries, list) or len(entries) != 1 or not isinstance(entries[0], Mapping):
        raise ValueError("single_model_production_evidence_entry_invalid")
    entry = entries[0]
    benchmark = rehydrate_model_benchmark_evidence_receipt(
        _mapping(entry.get("benchmark_receipt"), "benchmark_receipt")
    )
    promotion = rehydrate_model_promotion_evidence_receipt(
        _mapping(entry.get("promotion_receipt"), "promotion_receipt"),
        benchmark_receipt=benchmark,
    )
    if (
        benchmark.model_id != preview.candidate_model_id
        or benchmark.receipt_id != gate.benchmark_evidence_receipt_id
        or promotion.receipt_id != preview.promotion_evidence_receipt_id
        or promotion.to_dict() != gate.promotion_evidence_receipt.to_dict()
    ):
        raise ValueError("single_model_production_gate_evidence_mismatch")
    benchmark_signature = rehydrate_model_signed_evidence_receipt(
        _mapping(entry.get("benchmark_signature_receipt"), "benchmark_signature_receipt")
    )
    promotion_signature = rehydrate_model_signed_evidence_receipt(
        _mapping(entry.get("promotion_signature_receipt"), "promotion_signature_receipt")
    )
    if promotion_signature.promotion_policy_digest != preview.promotion_policy_digest:
        raise ValueError("single_model_production_policy_signature_mismatch")
    benchmark_run_receipt_id = _required(
        bundle.get("benchmark_run_receipt_id"), "benchmark_run_receipt_id"
    )
    verified = build_verified_model_production_evidence(
        catalog_snapshot_id=preview.catalog_snapshot_id,
        selection_receipt_id=preview.selection_receipt_id,
        benchmark_run_receipt_id=benchmark_run_receipt_id,
        benchmark_receipt=benchmark,
        promotion_receipt=promotion,
        benchmark_signature_receipt=benchmark_signature,
        promotion_signature_receipt=promotion_signature,
        key_resolver=key_resolver,
        signature_verifier=signature_verifier,
        now=now,
        nonce_store=nonce_store,
        consume_nonces=True,
    )
    return verified, benchmark, promotion


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


def _mapping(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(name + "_invalid")
    return value


def _required(value: Any, name: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(name + "_missing")
    return text


__all__ = [
    "SingleModelProductionBindingResult",
    "SingleModelProductionSelectionPreview",
    "bind_authenticated_single_model_promotion_to_runtime",
    "build_authenticated_single_model_production_selection_preview",
]
