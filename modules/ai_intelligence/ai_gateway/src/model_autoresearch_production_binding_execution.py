"""Verified execution phase for authenticated single-model production binding."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from .model_autoresearch_production_binding_transaction import (
    advance_publication,
    production_publication_binding,
    reserve_evidence_publications,
)
from .model_autoresearch_single_model_evidence_preflight import (
    verify_external_single_model_evidence_bundle,
)
from .model_intelligence_selection import select_models_for_task
from .model_runtime_binding_artifact_supply import (
    run_reddog_model_runtime_binding_artifact_supply,
)
from .model_runtime_binding_evidence_verifier import (
    discard_verified_runtime_binding_capability,
    verify_model_runtime_binding_artifact,
)
from .model_selection_artifact_supply import run_reddog_model_selection_artifact_supply


def execute_production_binding(
    *,
    inputs: Mapping[str, Any],
    bundle: Mapping[str, Any],
) -> tuple[Any, Any]:
    verified = _verify_binding_inputs(inputs, bundle)
    evidence, benchmark, promotion, benchmark_signature, promotion_signature = verified
    publication = _reserve_binding_publications(
        inputs, benchmark_signature, promotion_signature
    )
    selection, runtime = _supply_binding_artifacts(
        inputs, bundle, evidence, benchmark, promotion
    )
    _complete_binding_publications(inputs, publication)
    return selection, runtime


def _verify_binding_inputs(
    inputs: Mapping[str, Any],
    bundle: Mapping[str, Any],
) -> tuple[Any, Any, Any, Any, Any]:
    values = verify_external_single_model_evidence_bundle(
        bundle=bundle,
        preview=inputs["preview"],
        gate=inputs["gate"],
        key_resolver=inputs["key_resolver"],
        signature_verifier=inputs["signature_verifier"],
        revoked_key_epochs=inputs["trusted_keys"]["revoked_key_epochs"],
        now=inputs["now"],
    )
    evidence, benchmark, promotion, _benchmark_sig, _promotion_sig = values
    selection = select_models_for_task(
        inputs["snapshot"], inputs["requirements"], production_evidence=evidence
    )
    preview = inputs["preview"]
    if selection.receipt_id != preview.selection_receipt_id or selection.selected_model_ids != (
        preview.candidate_model_id,
    ):
        raise ValueError("single_model_production_preview_not_reproduced")
    artifact = verify_model_runtime_binding_artifact(
        catalog_snapshot=inputs["catalog_snapshot"],
        model_selection_receipt=_json_mapping(selection.to_dict()),
        benchmark_evidence_receipts=(benchmark.to_dict(),),
        promotion_evidence_receipts=(promotion.to_dict(),),
        verified_evidence_bundle=bundle,
        runtime_policy=inputs["runtime_policy"],
        trusted_keys_payload=inputs["trusted_keys"],
        key_resolver=inputs["key_resolver"],
        signature_verifier=inputs["signature_verifier"],
        now=inputs["now"],
    )
    discard_verified_runtime_binding_capability(artifact.capability)
    return values


def _reserve_binding_publications(
    inputs: Mapping[str, Any],
    benchmark_signature: Any,
    promotion_signature: Any,
) -> tuple[str, str, tuple[tuple[str, str], ...]]:
    context = inputs["authority_use"]
    binding = production_publication_binding(
        authenticated_promotion=inputs["authenticated_promotion"],
        preview=inputs["preview"],
        runtime_policy=inputs["runtime_policy"],
        trusted_keys=inputs["trusted_keys"],
        selection_output=inputs["selection_output"],
        runtime_output=inputs["runtime_output"],
    )
    nonce = "single-model-production-authority-use:" + inputs[
        "authenticated_promotion"
    ].authority.receipt.receipt_id
    if advance_publication(
        context.publication_store,
        nonce=nonce,
        binding_digest=binding,
        target_status="RESERVED",
    ) == "APPLIED":
        raise ValueError("single_model_production_authority_replay")
    evidence = reserve_evidence_publications(
        context.publication_store,
        benchmark_signature,
        promotion_signature,
        use_binding_digest=binding,
    )
    advance_publication(
        context.publication_store,
        nonce=nonce,
        binding_digest=binding,
        target_status="AUTHORIZED",
    )
    return nonce, binding, evidence


def _supply_binding_artifacts(
    inputs: Mapping[str, Any],
    bundle: Mapping[str, Any],
    evidence: Any,
    benchmark: Any,
    promotion: Any,
) -> tuple[Any, Any]:
    preview = inputs["preview"]
    selection = run_reddog_model_selection_artifact_supply(
        repo_root=inputs["root"],
        catalog_snapshot=inputs["catalog_snapshot"],
        verified_evidence_bundle=evidence,
        requirements=inputs["requirements"],
        output_path=inputs["selection_output"],
    )
    if not selection.accepted or selection.selection_receipt_id != preview.selection_receipt_id:
        raise ValueError("single_model_production_selection_supply_rejected")
    runtime = run_reddog_model_runtime_binding_artifact_supply(
        repo_root=inputs["root"],
        catalog_snapshot=inputs["catalog_snapshot"],
        model_selection_receipt=_read_json(inputs["selection_output"]),
        benchmark_evidence_receipts=(benchmark.to_dict(),),
        promotion_evidence_receipts=(promotion.to_dict(),),
        verified_evidence_bundle=bundle,
        trusted_keys_payload=inputs["trusted_keys"],
        runtime_policy=inputs["runtime_policy"],
        output_path=inputs["runtime_output"],
        key_resolver=inputs["key_resolver"],
        signature_verifier=inputs["signature_verifier"],
        now=inputs["now"],
    )
    if not runtime.accepted:
        raise ValueError(
            "single_model_production_runtime_binding_rejected:"
            + ",".join(runtime.rejection_reasons)
        )
    if runtime.selection_receipt_id != preview.selection_receipt_id:
        raise ValueError("single_model_production_runtime_selection_mismatch")
    return selection, runtime


def _complete_binding_publications(
    inputs: Mapping[str, Any],
    publication: tuple[str, str, tuple[tuple[str, str], ...]],
) -> None:
    nonce, binding, _evidence = publication
    store = inputs["authority_use"].publication_store
    advance_publication(
        store, nonce=nonce, binding_digest=binding, target_status="APPLIED"
    )


def _read_json(path: Path) -> Mapping[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError("single_model_production_selection_artifact_invalid")
    return payload


def _json_mapping(value: Any) -> Mapping[str, Any]:
    payload = json.loads(json.dumps(value, sort_keys=True, separators=(",", ":")))
    if not isinstance(payload, Mapping):
        raise ValueError("single_model_production_selection_payload_invalid")
    return payload


__all__ = ["execute_production_binding"]
