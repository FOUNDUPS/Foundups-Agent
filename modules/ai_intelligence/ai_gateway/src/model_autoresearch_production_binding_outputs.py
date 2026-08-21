"""Staged output ownership and explicit quarantine for production binding."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from . import (
    model_autoresearch_production_binding_artifact_durability as artifact_durability,
)
from .model_autoresearch_production_binding_transaction import (
    ProductionPublicationIdentity,
)


@dataclass(frozen=True)
class ProductionOutputTransaction:
    selection_output: Path
    runtime_output: Path
    selection_stage: Path
    runtime_stage: Path

    @property
    def owned_paths(self) -> tuple[Path, ...]:
        return (
            self.selection_output,
            self.runtime_output,
            self.selection_stage,
            self.runtime_stage,
        )


def claim_output_transaction(
    selection_output: Path,
    runtime_output: Path,
    identity: ProductionPublicationIdentity,
) -> ProductionOutputTransaction:
    transaction = output_transaction_for(selection_output, runtime_output, identity)
    claimed: list[Path] = []
    try:
        for path in transaction.owned_paths:
            path.parent.mkdir(parents=True, exist_ok=True)
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            os.close(fd)
            claimed.append(path)
    except Exception:
        try:
            cleanup_output_paths(tuple(claimed))
        except ValueError:
            raise ValueError(
                "single_model_production_output_claim_cleanup_failed"
            ) from None
        raise ValueError("single_model_production_output_claim_failed") from None
    return transaction


def output_transaction_for(
    selection_output: Path,
    runtime_output: Path,
    identity: ProductionPublicationIdentity,
) -> ProductionOutputTransaction:
    suffix = identity.binding_digest.removeprefix("sha256:")[:16]
    return ProductionOutputTransaction(
        selection_output=selection_output,
        runtime_output=runtime_output,
        selection_stage=_stage_path(selection_output, suffix),
        runtime_stage=_stage_path(runtime_output, suffix),
    )


def publish_staged_outputs(transaction: ProductionOutputTransaction) -> None:
    try:
        os.replace(transaction.selection_stage, transaction.selection_output)
        artifact_durability.fsync_published_parent(transaction.selection_output)
        os.replace(transaction.runtime_stage, transaction.runtime_output)
        artifact_durability.fsync_published_parent(transaction.runtime_output)
    except OSError:
        raise ValueError("single_model_production_output_publication_failed") from None


def cleanup_output_transaction(transaction: ProductionOutputTransaction) -> None:
    cleanup_output_paths(transaction.owned_paths)


def cleanup_output_paths(paths: tuple[Path, ...]) -> None:
    quarantined: list[Path] = []
    failures: list[Path] = []
    for path in paths:
        if not path.exists():
            continue
        try:
            path.unlink()
        except OSError:
            try:
                quarantine = _available_quarantine_path(path)
                os.replace(path, quarantine)
                quarantined.append(quarantine)
            except OSError:
                failures.append(path)
    if failures:
        raise ValueError("single_model_production_cleanup_failed")
    if quarantined:
        raise ValueError("single_model_production_cleanup_quarantined")


def _stage_path(path: Path, suffix: str) -> Path:
    return path.with_name("." + path.name + "." + suffix + ".staging")


def _available_quarantine_path(path: Path) -> Path:
    for index in range(100):
        candidate = path.with_name(path.name + f".invalid.{index:02d}")
        if not candidate.exists():
            return candidate
    raise OSError("single_model_production_quarantine_exhausted")


__all__ = [
    "ProductionOutputTransaction",
    "claim_output_transaction",
    "cleanup_output_paths",
    "cleanup_output_transaction",
    "output_transaction_for",
    "publish_staged_outputs",
]
