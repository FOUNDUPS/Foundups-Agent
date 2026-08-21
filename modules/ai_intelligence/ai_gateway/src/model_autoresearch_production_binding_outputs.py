"""Durable staged-output claims with identity-owned cleanup."""

from __future__ import annotations

import json
import secrets
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .model_autoresearch_configured_gateway_atomic_create import atomic_create_bytes
from .model_autoresearch_production_binding_artifact_durability import (
    HeldProductionArtifact,
    ProductionArtifactProof,
    cleanup_owned_artifact,
    publish_held_artifact,
    seal_staged_artifact,
    verify_held_artifact,
)
from .model_autoresearch_production_binding_output_cleanup import (
    cleanup_output_transaction,
)
from .model_autoresearch_production_binding_claims import (
    ProductionBindingClaimReceipt,
    load_or_create_claim,
)


@dataclass(frozen=True)
class ProductionOutputTransaction:
    selection_output: Path
    runtime_output: Path
    selection_stage: Path
    runtime_stage: Path
    selection_claim: ProductionArtifactProof | None
    runtime_claim: ProductionArtifactProof | None
    selection_supply: Path | None
    runtime_supply: Path | None


def claim_output_transaction(inputs: Mapping[str, Any]) -> ProductionOutputTransaction:
    selection, runtime = inputs["selection_output"], inputs["runtime_output"]
    if _occupied(selection) or _occupied(runtime):
        raise ValueError("single_model_production_output_claim_failed")
    claim = load_or_create_claim(inputs)
    paths = (Path(claim.selection_stage), Path(claim.runtime_stage))
    proofs: list[ProductionArtifactProof] = []
    try:
        proofs.append(_claim_stage(paths[0], claim, "selection"))
        proofs.append(_claim_stage(paths[1], claim, "runtime"))
    except Exception:
        for path, proof in zip(paths, proofs):
            _cleanup_one(path, proof)
        raise
    return ProductionOutputTransaction(
        selection,
        runtime,
        *paths,
        proofs[0],
        proofs[1],
        _supply_path(selection, "selection"),
        _supply_path(runtime, "runtime"),
    )


def transaction_for_claim(
    inputs: Mapping[str, Any], claim: ProductionBindingClaimReceipt
) -> ProductionOutputTransaction:
    paths = (Path(claim.selection_stage), Path(claim.runtime_stage))
    return ProductionOutputTransaction(
        inputs["selection_output"],
        inputs["runtime_output"],
        *paths,
        None,
        None,
        None,
        None,
    )


def close_sealed_artifacts(values: tuple[HeldProductionArtifact, ...]) -> None:
    for value in values:
        value.close()


def publish_staged_outputs(
    transaction: ProductionOutputTransaction,
    sealed: tuple[HeldProductionArtifact, HeldProductionArtifact],
) -> None:
    publish_held_artifact(sealed[0], transaction.selection_output)
    publish_held_artifact(sealed[1], transaction.runtime_output)
    cleanup_claim_markers(transaction)


def cleanup_claim_markers(transaction: ProductionOutputTransaction) -> None:
    for path, proof in (
        (transaction.selection_stage, transaction.selection_claim),
        (transaction.runtime_stage, transaction.runtime_claim),
    ):
        if proof is not None:
            cleanup_owned_artifact(path, proof)


def _claim_stage(
    path: Path, claim: ProductionBindingClaimReceipt, role: str
) -> ProductionArtifactProof:
    marker = stage_claim_bytes(claim, role)
    try:
        atomic_create_bytes(path, marker, root=path.parent)
    except Exception:
        raise ValueError("single_model_production_output_claim_failed") from None
    return _proof_existing_claim(path, claim, role)


def _proof_existing_claim(
    path: Path, claim: ProductionBindingClaimReceipt, role: str
) -> ProductionArtifactProof:
    try:
        held = seal_staged_artifact(path)
        try:
            payload = verify_held_artifact(held)
            if payload != stage_claim_bytes(claim, role):
                raise ValueError("single_model_production_output_ownership_conflict")
            return held.proof
        finally:
            held.close()
    except ValueError:
        raise
    except Exception:
        raise ValueError("single_model_production_output_ownership_conflict") from None


def stage_claim_bytes(claim: ProductionBindingClaimReceipt, role: str) -> bytes:
    payload = {
        "schema_version": "single_model_production_stage_claim.v1",
        "claim_receipt_id": claim.receipt_id,
        "binding_digest": claim.binding_digest,
        "token": claim.token,
        "role": role,
    }
    return (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode()


def _occupied(path: Path) -> bool:
    return path.exists() or path.is_symlink()


def _cleanup_one(path: Path, proof: ProductionArtifactProof) -> None:
    try:
        cleanup_owned_artifact(path, proof)
    except Exception:
        pass


def _supply_path(output: Path, role: str) -> Path:
    token = secrets.token_hex(16)
    return output.with_name(f".{output.name}.{role}.{token}.supply")


__all__ = [
    "ProductionOutputTransaction",
    "claim_output_transaction",
    "cleanup_claim_markers",
    "cleanup_output_transaction",
    "close_sealed_artifacts",
    "publish_staged_outputs",
    "stage_claim_bytes",
    "transaction_for_claim",
]
