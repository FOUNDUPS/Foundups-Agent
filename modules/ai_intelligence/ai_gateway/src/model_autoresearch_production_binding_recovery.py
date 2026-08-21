"""Durable terminal receipt and verified recovery for production binding."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Mapping

from .model_autoresearch_configured_gateway_evidence import digest_payload
from .model_autoresearch_production_authority_use import (
    trusted_campaign_authority_time,
    validate_campaign_promotion_authority_use,
)
from .model_autoresearch_production_binding_outputs import ProductionOutputTransaction
from . import (
    model_autoresearch_production_binding_artifact_durability as artifact_durability,
)
from .model_autoresearch_production_binding_rehydration import (
    rehydrate_production_supply_results,
    verify_recovered_runtime,
)
from .model_autoresearch_production_binding_temporal import (
    pure_recheck_production_time,
)
from .model_autoresearch_production_binding_json import read_production_json
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
) -> ProductionBindingTerminalReceipt:
    identity = inputs["publication_identity"]
    receipt = ProductionBindingTerminalReceipt(
        receipt_id=identity.terminal_receipt_id,
        nonce=identity.nonce,
        binding_digest=identity.binding_digest,
        selection_digest=digest_payload(_read_json(transaction.selection_stage)),
        runtime_digest=digest_payload(_read_json(transaction.runtime_stage)),
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
    try:
        payload = inputs["authority_use"].receipt_store.load(
            identity.terminal_receipt_id
        )
    except Exception:
        if not required:
            return None
        raise ValueError("single_model_production_terminal_receipt_missing") from None
    receipt = rehydrate_production_terminal_receipt(payload, identity)
    selection_payload, selection_source = _load_artifact(
        transaction.selection_output,
        transaction.selection_stage,
        receipt.selection_digest,
    )
    runtime_payload, runtime_source = _load_artifact(
        transaction.runtime_output,
        transaction.runtime_stage,
        receipt.runtime_digest,
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
    _publish_verified(
        selection_source, transaction.selection_output, receipt.selection_digest
    )
    _publish_verified(
        runtime_source, transaction.runtime_output, receipt.runtime_digest
    )
    return selection, runtime


def _load_artifact(
    final: Path, stage: Path, expected_digest: str
) -> tuple[Mapping[str, Any], Path]:
    for candidate in (final, stage):
        try:
            payload = _read_json(candidate)
        except ValueError:
            continue
        if digest_payload(payload) == expected_digest:
            return payload, candidate
    raise ValueError("single_model_production_terminal_artifact_missing")


def _publish_verified(source: Path, final: Path, expected_digest: str) -> None:
    if digest_payload(_read_json(source)) != expected_digest:
        raise ValueError("single_model_production_terminal_artifact_changed")
    if source != final:
        try:
            os.replace(source, final)
        except OSError:
            raise ValueError(
                "single_model_production_output_publication_failed"
            ) from None
    artifact_durability.fsync_published_parent(final)


def _read_json(path: Path) -> Mapping[str, Any]:
    return read_production_json(
        path, "single_model_production_terminal_artifact_invalid"
    )


__all__ = [
    "persist_terminal_receipt",
    "publish_recovered_binding",
    "recover_terminal_binding",
]
