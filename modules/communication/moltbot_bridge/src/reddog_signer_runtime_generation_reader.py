"""Verifier-only reader for the active external-signer generation."""

from __future__ import annotations

from pathlib import Path
from dataclasses import dataclass
from typing import Protocol

from modules.communication.moltbot_bridge.src.reddog_authority_runtime_store import (
    AtomicJsonAuthorityRuntimeStore,
)
from modules.communication.moltbot_bridge.src.reddog_runtime_artifact_manifest_contract import (
    is_sha256,
)
from modules.communication.moltbot_bridge.src.reddog_signer_runtime_generation_anchor import (
    SignerRuntimeGenerationActivation,
    SignerRuntimeGenerationHighWater,
    SignerRuntimeGenerationPendingAdvance,
    SignerRuntimeGenerationVerifier,
    decode_signer_runtime_generation_state,
)
from modules.infrastructure.shared_utilities.runtime_artifact_safety import (
    confined_runtime_operation_lock,
    validate_runtime_root_path,
)


class SignerRuntimeGenerationReader(Protocol):
    def load(self) -> SignerRuntimeGenerationActivation | None: ...


class SignerRuntimeGenerationHighWaterReader(Protocol):
    def load(self, anchor_id: str) -> SignerRuntimeGenerationHighWater | None: ...

    def pending(
        self, anchor_id: str
    ) -> SignerRuntimeGenerationPendingAdvance | None: ...


@dataclass(frozen=True)
class VerifiedSignerRuntimeGenerationHighWaterReader:
    reader: SignerRuntimeGenerationHighWaterReader
    store_id: str
    durability_receipt_id: str
    rollback_domain_root: Path


class SignerRuntimeGenerationHighWaterReaderAuthorityBoundary(Protocol):
    def require(
        self, value: object
    ) -> VerifiedSignerRuntimeGenerationHighWaterReader: ...


class DurableSignerRuntimeGenerationReader:
    """Read one authenticated generation without retaining signing capability."""

    def __init__(
        self,
        path: Path | str,
        *,
        allowed_root: Path | str,
        repo_root: Path | str,
        anchor_id: str,
        verifier: SignerRuntimeGenerationVerifier,
        high_water_authority: object,
        high_water_authority_boundary: (
            SignerRuntimeGenerationHighWaterReaderAuthorityBoundary
        ),
    ) -> None:
        self._anchor_id = _text(anchor_id, "anchor_id")
        self._verifier = _verifier(verifier)
        self._store = AtomicJsonAuthorityRuntimeStore(
            path,
            allowed_root=allowed_root,
            repo_root=repo_root,
        )
        verified = high_water_authority_boundary.require(high_water_authority)
        rollback_root = validate_runtime_root_path(
            verified.rollback_domain_root,
            repo_root=self._store.repo_root,
        )
        if _paths_overlap(rollback_root, self._store.allowed_root):
            raise ValueError("generation_reader_high_water_domain_overlap")
        if not is_sha256(verified.durability_receipt_id):
            raise ValueError("generation_reader_high_water_receipt_invalid")
        self._high_water = verified.reader
        self._high_water_store_id = _text(verified.store_id, "store_id")
        self._durability_receipt_id = verified.durability_receipt_id
        self._lock_path = self._store.path.with_name(
            self._store.path.name + ".generation-anchor.lock"
        )

    def load(self) -> SignerRuntimeGenerationActivation | None:
        with confined_runtime_operation_lock(
            self._lock_path,
            repo_root=self._store.repo_root,
            allowed_root=self._store.allowed_root,
        ):
            if self._high_water.pending(self._anchor_id) is not None:
                raise ValueError("generation_reader_pending_transaction")
            activation = decode_signer_runtime_generation_state(
                self._store.load(),
                anchor_id=self._anchor_id,
                verifier=self._verifier,
                high_water_store_id=self._high_water_store_id,
                high_water_durability_receipt_id=(
                    self._durability_receipt_id
                ),
            )
            current = self._high_water.load(self._anchor_id)
            if activation is None:
                if current is not None:
                    raise ValueError("generation_reader_rollback_detected")
                return None
            if (
                current is None
                or current.generation != activation.generation
                or current.revision != activation.revision
            ):
                raise ValueError("generation_reader_rollback_detected")
            return activation


def _verifier(value: object) -> SignerRuntimeGenerationVerifier:
    if not callable(getattr(value, "verify", None)):
        raise ValueError("generation_reader_verifier_invalid")
    _text(getattr(value, "authenticator_id", None), "authenticator_id")
    return value  # type: ignore[return-value]


def _text(value: object, name: str) -> str:
    if (
        not isinstance(value, str)
        or not value.strip()
        or not value.isascii()
        or len(value) > 1024
    ):
        raise ValueError(f"generation_reader_{name}_invalid")
    return value.strip()


def _paths_overlap(first: Path, second: Path) -> bool:
    return first == second or first in second.parents or second in first.parents


__all__ = [
    "DurableSignerRuntimeGenerationReader",
    "SignerRuntimeGenerationHighWaterReader",
    "SignerRuntimeGenerationHighWaterReaderAuthorityBoundary",
    "SignerRuntimeGenerationReader",
    "VerifiedSignerRuntimeGenerationHighWaterReader",
]
