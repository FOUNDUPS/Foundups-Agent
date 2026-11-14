"""Identity-owned cleanup and quarantine for production output transactions."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .model_autoresearch_production_binding_artifact_durability import (
    HeldProductionArtifact,
    cleanup_owned_artifact,
    open_verified_artifact,
    publish_held_artifact,
)


def cleanup_output_transaction(
    transaction: Any,
    sealed: tuple[HeldProductionArtifact, ...] = (),
) -> None:
    failures, quarantined = [], []
    for path, proof in (
        (transaction.selection_stage, transaction.selection_claim),
        (transaction.runtime_stage, transaction.runtime_claim),
    ):
        if proof is not None:
            _cleanup_one(path, proof, failures, quarantined)
    supply_paths = {transaction.selection_supply, transaction.runtime_supply}
    for artifact in sealed:
        if artifact.path in supply_paths:
            _cleanup_one(artifact.path, artifact.proof, failures, quarantined)
    if failures:
        raise ValueError("single_model_production_output_ownership_conflict")
    if quarantined:
        raise ValueError("single_model_production_cleanup_quarantined")


def _cleanup_one(path, proof, failures, quarantined) -> None:
    try:
        cleanup_owned_artifact(path, proof)
        return
    except ValueError as error:
        if "ownership_conflict" in str(error):
            failures.append(path)
            return
    try:
        held = open_verified_artifact(path, proof)
        quarantine = _available_quarantine_path(path)
        try:
            publish_held_artifact(held, quarantine)
        finally:
            held.close()
        quarantined.append(quarantine)
    except Exception:
        failures.append(path)


def _available_quarantine_path(path: Path) -> Path:
    for index in range(100):
        candidate = path.with_name(path.name + f".invalid.{index:02d}")
        if not (candidate.exists() or candidate.is_symlink()):
            return candidate
    raise ValueError("single_model_production_quarantine_exhausted")


__all__ = ["cleanup_output_transaction"]
