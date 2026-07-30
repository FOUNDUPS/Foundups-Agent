"""Rehydrate and verify serialized aggregate PANEL model evidence."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from modules.communication.moltbot_bridge.src.reddog_work_order_signature_verifier import (
    SignatureVerifier,
)

from .model_intelligence_catalog import ModelCatalogSnapshot
from .model_intelligence_selection import ModelSelectionReceipt
from .model_panel_signed_evidence import (
    PanelMemberEvidenceInput,
    VerifiedModelPanelEvidence,
    build_verified_model_panel_evidence,
)
from .model_runtime_binding import ModelRuntimeBindingPolicy
from .model_signed_evidence import ModelEvidenceKeyResolver


PANEL_EVIDENCE_BUNDLE_SCHEMA_VERSION = "model_panel_signed_evidence_bundle.v1"


def rehydrate_verified_panel_evidence_bundle(
    bundle: Mapping[str, Any],
    *,
    catalog_snapshot: ModelCatalogSnapshot,
    selection_receipt: ModelSelectionReceipt,
    runtime_policy: ModelRuntimeBindingPolicy,
    context_receipt_ids: Mapping[str, Any],
    key_resolver: ModelEvidenceKeyResolver,
    signature_verifier: SignatureVerifier,
    now: int,
    consume_nonce: bool = False,
    revoked_member_key_epochs: Sequence[str] = (),
    revoked_panel_key_epochs: Sequence[str] = (),
) -> VerifiedModelPanelEvidence:
    entries = _member_inputs(bundle)
    aggregate = _mapping(bundle.get("aggregate_receipt"), "aggregate_receipt")
    _validate_bundle_context(bundle, aggregate, catalog_snapshot, selection_receipt)
    return build_verified_model_panel_evidence(
        catalog_snapshot=catalog_snapshot,
        selection_receipt=selection_receipt,
        member_inputs=entries,
        aggregate_receipt=aggregate,
        runtime_policy=runtime_policy,
        task_receipt_id=_required(context_receipt_ids, "task_receipt_id"),
        topology_receipt_id=_required(context_receipt_ids, "topology_receipt_id"),
        policy_receipt_id=_required(context_receipt_ids, "policy_receipt_id"),
        runtime_surface_receipt_id=_required(
            context_receipt_ids, "runtime_surface_receipt_id"
        ),
        member_key_resolver=key_resolver,
        member_signature_verifier=signature_verifier,
        panel_key_resolver=key_resolver,
        panel_signature_verifier=signature_verifier,
        now=now,
        consume_nonce=consume_nonce,
        revoked_member_key_epochs=revoked_member_key_epochs,
        revoked_panel_key_epochs=revoked_panel_key_epochs,
    )


def _validate_bundle_context(
    bundle: Mapping[str, Any],
    aggregate: Mapping[str, Any],
    snapshot: ModelCatalogSnapshot,
    selection: ModelSelectionReceipt,
) -> None:
    if bundle.get("schema_version") != PANEL_EVIDENCE_BUNDLE_SCHEMA_VERSION:
        raise ValueError("invalid_panel_evidence_bundle_schema")
    expected = (
        snapshot.snapshot_id,
        selection.receipt_id,
        _required(aggregate, "benchmark_run_receipt_id"),
    )
    actual = (
        _required(bundle, "catalog_snapshot_id"),
        _required(bundle, "selection_receipt_id"),
        _required(bundle, "benchmark_run_receipt_id"),
    )
    if actual != expected:
        raise ValueError("panel_evidence_bundle_context_mismatch")


def _member_inputs(bundle: Mapping[str, Any]) -> tuple[PanelMemberEvidenceInput, ...]:
    entries = bundle.get("entries")
    if not isinstance(entries, list) or not entries:
        raise ValueError("missing_panel_evidence_entries")
    return tuple(_member_input(entry) for entry in entries)


def _member_input(value: Any) -> PanelMemberEvidenceInput:
    entry = _mapping(value, "panel_evidence_entry")
    return PanelMemberEvidenceInput(
        role=_required(entry, "role"),
        model_id=_required(entry, "model_id"),
        provider=_required(entry, "provider"),
        benchmark_receipt=_mapping(
            entry.get("benchmark_receipt"), "benchmark_receipt"
        ),
        promotion_receipt=_mapping(
            entry.get("promotion_receipt"), "promotion_receipt"
        ),
        benchmark_signature_receipt=_mapping(
            entry.get("benchmark_signature_receipt"),
            "benchmark_signature_receipt",
        ),
        promotion_signature_receipt=_mapping(
            entry.get("promotion_signature_receipt"),
            "promotion_signature_receipt",
        ),
    )


def _mapping(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{name}_missing")
    return value


def _required(value: Mapping[str, Any], name: str) -> str:
    result = str(value.get(name) or "").strip()
    if not result:
        raise ValueError(f"{name}_missing")
    return result


__all__ = [
    "PANEL_EVIDENCE_BUNDLE_SCHEMA_VERSION",
    "rehydrate_verified_panel_evidence_bundle",
]
