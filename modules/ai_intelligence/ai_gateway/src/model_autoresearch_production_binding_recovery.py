"""Durable terminal receipt and verified recovery for production binding."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from .model_autoresearch_configured_gateway_evidence import digest_payload
from .model_autoresearch_production_authority_use import (
    trusted_campaign_authority_time,
    validate_campaign_promotion_authority_use,
)
from .model_autoresearch_production_binding_outputs import (
    ProductionOutputTransaction,
    cleanup_claim_markers,
)
from . import (
    model_autoresearch_production_binding_artifact_durability as artifact_durability,
)
from .model_autoresearch_production_binding_rehydration import (
    rehydrate_production_supply_results,
    verify_recovered_runtime,
)
from .model_autoresearch_production_binding_temporal import pure_recheck_production_time
from .model_autoresearch_single_model_evidence_preflight import (
    verify_external_single_model_evidence_bundle,
)
from .model_autoresearch_production_terminal_receipt import (
    ProductionBindingTerminalReceipt,
    rehydrate_production_terminal_receipt,
)


def persist_terminal_receipt(
    inputs: Mapping[str, Any],
    bundle: Mapping[str, Any],
    transaction: ProductionOutputTransaction,
    sealed: tuple[Any, Any],
) -> ProductionBindingTerminalReceipt:
    identity = inputs["publication_identity"]
    receipt = ProductionBindingTerminalReceipt(
        receipt_id=identity.terminal_receipt_id,
        nonce=identity.nonce,
        binding_digest=identity.binding_digest,
        selection_digest=digest_payload(
            artifact_durability.read_held_json(
                sealed[0], "single_model_production_terminal_artifact_invalid"
            )
        ),
        runtime_digest=digest_payload(
            artifact_durability.read_held_json(
                sealed[1], "single_model_production_terminal_artifact_invalid"
            )
        ),
        selection_proof=sealed[0].proof.to_dict(),
        runtime_proof=sealed[1].proof.to_dict(),
        selection_source=str(sealed[0].path),
        runtime_source=str(sealed[1].path),
        verified_evidence_bundle=dict(bundle),
    )
    operation = getattr(inputs["authority_use"].receipt_store, "append", None)
    if not callable(operation):
        raise ValueError("single_model_production_terminal_store_invalid")
    try:
        stored_id = operation(receipt)
    except Exception:
        raise ValueError(
            "single_model_production_terminal_persistence_failed"
        ) from None
    if stored_id != receipt.receipt_id:
        raise ValueError("single_model_production_terminal_persistence_failed")
    return receipt


def recover_terminal_binding(
    inputs: Mapping[str, Any],
    transaction: ProductionOutputTransaction,
    *,
    required: bool,
) -> tuple[Any, Any, Path, Path, ProductionBindingTerminalReceipt] | None:
    identity = inputs["publication_identity"]
    payload = _load_terminal_payload(inputs, identity.terminal_receipt_id, required)
    if payload is None:
        return None
    receipt = rehydrate_production_terminal_receipt(payload, identity)
    return _recover_verified_terminal(inputs, transaction, receipt)


def _load_terminal_payload(inputs, receipt_id, required):
    try:
        return inputs["authority_use"].receipt_store.load(receipt_id)
    except Exception:
        if not required:
            return None
        raise ValueError("single_model_production_terminal_receipt_missing") from None


def _recover_verified_terminal(inputs, transaction, receipt):
    selection_payload, selection_source = _load_artifact(
        transaction.selection_output,
        _receipt_source(receipt.selection_source, transaction.selection_stage),
        receipt.selection_digest,
        artifact_durability.proof_from_dict(receipt.selection_proof),
    )
    runtime_payload, runtime_source = _load_artifact(
        transaction.runtime_output,
        _receipt_source(receipt.runtime_source, transaction.runtime_stage),
        receipt.runtime_digest,
        artifact_durability.proof_from_dict(receipt.runtime_proof),
    )
    now = trusted_campaign_authority_time(inputs["authority_use"])
    validate_campaign_promotion_authority_use(
        inputs["authenticated_promotion"].authority,
        inputs["authority_use"],
        now=now,
    )
    values = verify_external_single_model_evidence_bundle(
        bundle=receipt.verified_evidence_bundle,
        preview=inputs["preview"],
        gate=inputs["gate"],
        key_resolver=inputs["key_resolver"],
        signature_verifier=inputs["signature_verifier"],
        revoked_key_epochs=inputs["trusted_keys"]["revoked_key_epochs"],
        now=now,
    )
    verify_recovered_runtime(
        inputs, receipt, selection_payload, runtime_payload, values, now
    )
    pure_recheck_production_time(inputs, values, runtime_payload)
    selection, runtime = rehydrate_production_supply_results(
        inputs, selection_payload, runtime_payload
    )
    return selection, runtime, selection_source, runtime_source, receipt


def publish_recovered_binding(recovered, transaction) -> tuple[Any, Any]:
    selection, runtime, selection_source, runtime_source, receipt = recovered
    artifact_durability.publish_held_artifact(
        selection_source, transaction.selection_output
    )
    artifact_durability.publish_held_artifact(
        runtime_source, transaction.runtime_output
    )
    cleanup_claim_markers(transaction)
    return selection, runtime


def _load_artifact(
    final: Path,
    stage: Path,
    expected_digest: str,
    proof: artifact_durability.ProductionArtifactProof,
) -> tuple[Mapping[str, Any], artifact_durability.HeldProductionArtifact]:
    held = None
    try:
        held = artifact_durability.open_interrupted_posix_publication(
            stage, final, proof
        )
    except (OSError, ValueError):
        held = None
    if held is not None:
        try:
            payload = _read_matching_artifact(held, expected_digest)
        except (OSError, ValueError):
            held.close()
        else:
            if payload is not None:
                return payload, held
            held.close()
    for candidate in (final, stage):
        held = None
        try:
            held = artifact_durability.open_verified_artifact(candidate, proof)
            payload = _read_matching_artifact(held, expected_digest)
        except (OSError, ValueError):
            if held is not None:
                held.close()
            continue
        if payload is not None:
            return payload, held
        held.close()
    raise ValueError("single_model_production_terminal_artifact_missing")


def _read_matching_artifact(held, expected_digest):
    payload = artifact_durability.read_held_json(
        held, "single_model_production_terminal_artifact_invalid"
    )
    return payload if digest_payload(payload) == expected_digest else None


def _receipt_source(value: str | None, legacy: Path) -> Path:
    return Path(value) if value else legacy


__all__ = [
    "persist_terminal_receipt",
    "publish_recovered_binding",
    "recover_terminal_binding",
]
