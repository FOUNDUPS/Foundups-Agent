"""Verifier-only reader for the active external-signer generation."""

from __future__ import annotations

from pathlib import Path
from dataclasses import dataclass
from typing import Protocol

from modules.communication.moltbot_bridge.src.reddog_read_only_runtime_json_store import (
    ReadOnlyRuntimeJsonStore,
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
from modules.communication.moltbot_bridge.src.reddog_signer_runtime_generation_verifier_authority import (
    SignerRuntimeGenerationVerifierAuthorityBoundary,
    require_signer_runtime_generation_verifier_authority,
)
from modules.infrastructure.shared_utilities.runtime_artifact_safety import (
    confined_runtime_operation_lock,
    validate_runtime_root_path,
)


class SignerRuntimeGenerationReader(Protocol):
    def load(self) -> SignerRuntimeGenerationActivation | None: ...


class SignerRuntimeGenerationHighWaterReader(Protocol):
    @property
    def store_id(self) -> str: ...

    @property
    def durability_receipt_id(self) -> str: ...

    @property
    def rollback_domain_root(self) -> Path: ...

    def load(self, anchor_id: str) -> SignerRuntimeGenerationHighWater | None: ...

    def pending(
        self, anchor_id: str
    ) -> SignerRuntimeGenerationPendingAdvance | None: ...


@dataclass(frozen=True)
class VerifiedSignerRuntimeGenerationHighWaterReader:
    reader: SignerRuntimeGenerationHighWaterReader
    store_id: str
    durability_receipt_id: str


class SignerRuntimeGenerationHighWaterReaderAuthorityBoundary(Protocol):
    def require(
        self, value: object
    ) -> VerifiedSignerRuntimeGenerationHighWaterReader: ...


class SignerRuntimeGenerationReaderAuthorityBoundary(Protocol):
    def require(self, value: object) -> SignerRuntimeGenerationReader: ...


class _ReaderAuthorityBoundary:
    __slots__ = ("_authority", "_reader")

    def __init__(
        self,
        authority: object,
        reader: DurableSignerRuntimeGenerationReader,
    ) -> None:
        self._authority = authority
        self._reader = reader

    def require(self, value: object) -> SignerRuntimeGenerationReader:
        if value is not self._authority:
            raise ValueError("generation_reader_authority_unverified")
        return self._reader


class DurableSignerRuntimeGenerationReader:
    """Read one authenticated generation without retaining signing capability."""

    def __init__(
        self,
        path: Path | str,
        *,
        allowed_root: Path | str,
        repo_root: Path | str,
        anchor_id: str,
        verifier_authority: object,
        verifier_authority_boundary: (
            SignerRuntimeGenerationVerifierAuthorityBoundary
        ),
        high_water_authority: object,
        high_water_authority_boundary: (
            SignerRuntimeGenerationHighWaterReaderAuthorityBoundary
        ),
    ) -> None:
        self._anchor_id = _text(anchor_id, "anchor_id")
        self._verifier = _verifier(
            require_signer_runtime_generation_verifier_authority(
                verifier_authority,
                verifier_authority_boundary,
            )
        )
        self._store = ReadOnlyRuntimeJsonStore(
            path,
            allowed_root=allowed_root,
            repo_root=repo_root,
        )
        verified = high_water_authority_boundary.require(high_water_authority)
        _read_only_high_water_reader(verified.reader)
        if (
            verified.store_id != verified.reader.store_id
            or verified.durability_receipt_id
            != verified.reader.durability_receipt_id
        ):
            raise ValueError("generation_reader_high_water_authority_mismatch")
        rollback_root = validate_runtime_root_path(
            verified.reader.rollback_domain_root,
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


def create_signer_runtime_generation_reader_authority(
    reader: DurableSignerRuntimeGenerationReader,
) -> tuple[object, SignerRuntimeGenerationReaderAuthorityBoundary]:
    if not isinstance(reader, DurableSignerRuntimeGenerationReader):
        raise ValueError("generation_reader_authority_reader_invalid")
    authority = object()
    return authority, _ReaderAuthorityBoundary(authority, reader)


def _verifier(value: object) -> SignerRuntimeGenerationVerifier:
    if not callable(getattr(value, "verify", None)) or callable(
        getattr(value, "authenticate", None)
    ):
        raise ValueError("generation_reader_verifier_invalid")
    _text(getattr(value, "authenticator_id", None), "authenticator_id")
    return value  # type: ignore[return-value]


def _read_only_high_water_reader(value: object) -> None:
    forbidden = ("abort_prepared", "advance", "commit_prepared", "prepare")
    if any(callable(getattr(value, name, None)) for name in forbidden):
        raise ValueError("generation_reader_high_water_write_capability")
    if not callable(getattr(value, "load", None)) or not callable(
        getattr(value, "pending", None)
    ):
        raise ValueError("generation_reader_high_water_invalid")


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
    "create_signer_runtime_generation_reader_authority",
    "SignerRuntimeGenerationHighWaterReader",
    "SignerRuntimeGenerationHighWaterReaderAuthorityBoundary",
    "SignerRuntimeGenerationReader",
    "SignerRuntimeGenerationReaderAuthorityBoundary",
    "VerifiedSignerRuntimeGenerationHighWaterReader",
]
