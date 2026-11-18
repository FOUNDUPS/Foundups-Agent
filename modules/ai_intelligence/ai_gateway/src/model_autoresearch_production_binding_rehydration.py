"""Use-time verification and result rehydration for terminal recovery."""

from __future__ import annotations

from typing import Any, Mapping

from .model_autoresearch_production_terminal_receipt import (
    ProductionBindingTerminalReceipt,
)
from .model_runtime_binding_artifact_supply import (
    MODEL_RUNTIME_BINDING_ARTIFACT_SUPPLY_ACCEPT,
    ModelRuntimeBindingArtifactSupplyResult,
)
from .model_runtime_binding_evidence_verifier import (
    discard_verified_runtime_binding_capability,
)
from .model_runtime_binding_use_time_verifier import ModelRuntimeBindingUseTimeVerifier
from .model_selection_artifact_supply import (
    MODEL_SELECTION_ARTIFACT_SUPPLY_ACCEPT,
    ModelSelectionArtifactSupplyResult,
)
from .model_signed_evidence import (
    rehydrate_model_runtime_binding_receipt,
    rehydrate_model_selection_receipt,
)


def verify_recovered_runtime(
    inputs: Mapping[str, Any],
    receipt: ProductionBindingTerminalReceipt,
    selection: Mapping[str, Any],
    runtime: Mapping[str, Any],
    values: tuple[Any, Any, Any, Any, Any],
    now: int,
) -> None:
    _evidence, benchmark, promotion, _benchmark_sig, _promotion_sig = values
    verifier = ModelRuntimeBindingUseTimeVerifier(
        catalog_snapshot=inputs["catalog_snapshot"],
        benchmark_evidence_receipts=(benchmark.to_dict(),),
        promotion_evidence_receipts=(promotion.to_dict(),),
        verified_evidence_bundle=receipt.verified_evidence_bundle,
        runtime_policy=inputs["runtime_policy"],
        trusted_keys_payload=inputs["trusted_keys"],
        key_resolver=inputs["key_resolver"],
        signature_verifier=inputs["signature_verifier"],
        trusted_now_epoch=lambda: now,
    )
    capability = verifier.verify(binding=runtime, selection=selection)
    discard_verified_runtime_binding_capability(capability)


def rehydrate_production_supply_results(
    inputs: Mapping[str, Any],
    selection_payload: Mapping[str, Any],
    runtime_payload: Mapping[str, Any],
) -> tuple[Any, Any]:
    selection = rehydrate_model_selection_receipt(selection_payload)
    runtime = rehydrate_model_runtime_binding_receipt(runtime_payload)
    preview = inputs["preview"]
    if selection.receipt_id != preview.selection_receipt_id:
        raise ValueError("single_model_production_recovery_selection_mismatch")
    if runtime.selection_receipt_id != preview.selection_receipt_id:
        raise ValueError("single_model_production_recovery_runtime_mismatch")
    return (
        ModelSelectionArtifactSupplyResult(
            True,
            MODEL_SELECTION_ARTIFACT_SUPPLY_ACCEPT,
            selection.receipt_id,
            selection.catalog_snapshot_id,
            selection.selected_model_ids,
            str(inputs["selection_output"]),
            (),
        ),
        ModelRuntimeBindingArtifactSupplyResult(
            True,
            MODEL_RUNTIME_BINDING_ARTIFACT_SUPPLY_ACCEPT,
            runtime.receipt_id,
            runtime.catalog_snapshot_id,
            runtime.selection_receipt_id,
            runtime.runtime_surface,
            runtime.principal_model,
            runtime.panel_models,
            str(inputs["runtime_output"]),
            (),
        ),
    )


__all__ = ["rehydrate_production_supply_results", "verify_recovered_runtime"]
