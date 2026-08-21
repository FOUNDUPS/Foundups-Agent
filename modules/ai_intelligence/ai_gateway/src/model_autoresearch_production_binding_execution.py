"""Verified execution phase for authenticated single-model production binding."""

from __future__ import annotations

from dataclasses import replace
from typing import Any, Mapping

from . import (
    model_autoresearch_production_binding_artifact_durability as artifact_durability,
)
from .model_autoresearch_production_binding_finalization import (
    complete_production_publication,
    verify_current_production_time,
)
from .model_autoresearch_production_binding_outputs import publish_staged_outputs
from .model_autoresearch_production_binding_json import (
    canonical_json_mapping,
    read_production_json,
)
from .model_autoresearch_production_binding_recovery import persist_terminal_receipt
from .model_autoresearch_production_binding_transaction import (
    advance_publication,
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
    inputs: dict[str, Any],
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
    transaction = inputs["output_transaction"]
    artifact_durability.seal_staged_artifacts(
        transaction.selection_stage, transaction.runtime_stage
    )
    verify_current_production_time(
        inputs, bundle, transaction.runtime_stage, _verify_binding_inputs
    )
    persist_terminal_receipt(inputs, bundle, transaction)
    complete_production_publication(inputs, bundle, publication, _verify_binding_inputs)
    publish_staged_outputs(transaction)
    selection = replace(selection, output_path=str(inputs["selection_output"]))
    runtime = replace(runtime, output_path=str(inputs["runtime_output"]))
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
    if (
        selection.receipt_id != preview.selection_receipt_id
        or selection.selected_model_ids != (preview.candidate_model_id,)
    ):
        raise ValueError("single_model_production_preview_not_reproduced")
    artifact = verify_model_runtime_binding_artifact(
        catalog_snapshot=inputs["catalog_snapshot"],
        model_selection_receipt=canonical_json_mapping(
            selection.to_dict(), "single_model_production_selection_payload_invalid"
        ),
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
    identity = inputs["publication_identity"]
    nonce, binding = identity.nonce, identity.binding_digest
    if (
        advance_publication(
            context.publication_store,
            nonce=nonce,
            binding_digest=binding,
            target_status="RESERVED",
        )
        == "APPLIED"
    ):
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
        output_path=inputs["output_transaction"].selection_stage,
    )
    if (
        not selection.accepted
        or selection.selection_receipt_id != preview.selection_receipt_id
    ):
        raise ValueError("single_model_production_selection_supply_rejected")
    runtime = run_reddog_model_runtime_binding_artifact_supply(
        repo_root=inputs["root"],
        catalog_snapshot=inputs["catalog_snapshot"],
        model_selection_receipt=read_production_json(
            inputs["output_transaction"].selection_stage,
            "single_model_production_selection_artifact_invalid",
        ),
        benchmark_evidence_receipts=(benchmark.to_dict(),),
        promotion_evidence_receipts=(promotion.to_dict(),),
        verified_evidence_bundle=bundle,
        trusted_keys_payload=inputs["trusted_keys"],
        runtime_policy=inputs["runtime_policy"],
        output_path=inputs["output_transaction"].runtime_stage,
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


__all__ = ["execute_production_binding"]
