"""Verifier-only reader for the active external-signer generation."""

from __future__ import annotations

import threading
from pathlib import Path
from dataclasses import dataclass
from typing import Any, Protocol
from weakref import WeakKeyDictionary

from modules.communication.moltbot_bridge.src.reddog_atomic_signer_runtime_generation_high_water import (
    AtomicSignerRuntimeGenerationHighWaterReader,
)
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


def _build_private_registry(error: str):
    lock = threading.RLock()
    records: WeakKeyDictionary[object, Any] = WeakKeyDictionary()

    def issue(key: object, value: Any) -> None:
        with lock:
            if key in records:
                raise ValueError(f"{error}_already_issued")
            records[key] = value

    def lookup(key: object) -> Any:
        with lock:
            try:
                return records[key]
            except KeyError as exc:
                raise ValueError(error) from exc

    return issue, lookup


_issue_reader_target, _lookup_reader_target = _build_private_registry(
    "generation_reader_handle_unverified"
)
_issue_reader_authority, _lookup_reader_authority = _build_private_registry(
    "generation_reader_authority_unverified"
)
_issue_high_water_target, _lookup_high_water_target = (
    _build_private_registry("generation_high_water_handle_unverified")
)
_issue_high_water_authority, _lookup_high_water_authority = (
    _build_private_registry("generation_high_water_authority_unverified")
)
_issue_durable_reader_state, _lookup_durable_reader_state = (
    _build_private_registry("generation_reader_state_unverified")
)
del _build_private_registry


class _ReaderHandle:
    __slots__ = ("__weakref__",)

    def load(
        self, _lookup: Any = _lookup_reader_target
    ) -> SignerRuntimeGenerationActivation | None:
        return _lookup(self).load()


class _HighWaterReaderHandle:
    __slots__ = ("__weakref__",)

    @property
    def store_id(
        self, _lookup: Any = _lookup_high_water_target
    ) -> str:
        return _lookup(self).store_id

    @property
    def durability_receipt_id(
        self, _lookup: Any = _lookup_high_water_target
    ) -> str:
        return _lookup(self).durability_receipt_id

    @property
    def rollback_domain_root(
        self, _lookup: Any = _lookup_high_water_target
    ) -> Path:
        return _lookup(self).rollback_domain_root

    def load(
        self,
        anchor_id: str,
        _lookup: Any = _lookup_high_water_target,
    ) -> SignerRuntimeGenerationHighWater | None:
        return _lookup(self).load(anchor_id)

    def pending(
        self,
        anchor_id: str,
        _lookup: Any = _lookup_high_water_target,
    ) -> SignerRuntimeGenerationPendingAdvance | None:
        return _lookup(self).pending(anchor_id)


class _ReaderAuthorityBoundary:
    __slots__ = ("__weakref__",)

    def require(
        self,
        value: object,
        _lookup: Any = _lookup_reader_authority,
    ) -> SignerRuntimeGenerationReader:
        authority, reader = _lookup(self)
        if value is not authority:
            raise ValueError("generation_reader_authority_unverified")
        return reader


class _HighWaterReaderAuthorityBoundary:
    __slots__ = ("__weakref__",)

    def require(
        self,
        value: object,
        _lookup: Any = _lookup_high_water_authority,
    ) -> VerifiedSignerRuntimeGenerationHighWaterReader:
        authority, reader = _lookup(self)
        if value is not authority:
            raise ValueError("generation_high_water_reader_unverified")
        return VerifiedSignerRuntimeGenerationHighWaterReader(
            reader=reader,
            store_id=reader.store_id,
            durability_receipt_id=reader.durability_receipt_id,
        )

@dataclass(frozen=True)
class _DurableReaderState:
    anchor_id: str
    verifier: SignerRuntimeGenerationVerifier
    store: ReadOnlyRuntimeJsonStore
    high_water: SignerRuntimeGenerationHighWaterReader
    high_water_store_id: str
    durability_receipt_id: str
    lock_path: Path

class DurableSignerRuntimeGenerationReader:
    """Read one authenticated generation without retaining signing capability."""

    __slots__ = ("__weakref__",)

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
        _issue_state: Any = _issue_durable_reader_state,
    ) -> None:
        resolved_anchor_id = _text(anchor_id, "anchor_id")
        verifier = _verifier(
            require_signer_runtime_generation_verifier_authority(
                verifier_authority,
                verifier_authority_boundary,
            )
        )
        store = ReadOnlyRuntimeJsonStore(
            path,
            allowed_root=allowed_root,
            repo_root=repo_root,
        )
        verified = require_signer_runtime_generation_high_water_reader_authority(
            high_water_authority,
            high_water_authority_boundary,
        )
        _read_only_high_water_reader(verified.reader)
        if (
            verified.store_id != verified.reader.store_id
            or verified.durability_receipt_id
            != verified.reader.durability_receipt_id
        ):
            raise ValueError("generation_reader_high_water_authority_mismatch")
        rollback_root = validate_runtime_root_path(
            verified.reader.rollback_domain_root,
            repo_root=store.repo_root,
        )
        if _paths_overlap(rollback_root, store.allowed_root):
            raise ValueError("generation_reader_high_water_domain_overlap")
        if not is_sha256(verified.durability_receipt_id):
            raise ValueError("generation_reader_high_water_receipt_invalid")
        _issue_state(self, _DurableReaderState(
            anchor_id=resolved_anchor_id,
            verifier=verifier,
            store=store,
            high_water=verified.reader,
            high_water_store_id=_text(verified.store_id, "store_id"),
            durability_receipt_id=verified.durability_receipt_id,
            lock_path=store.path.with_name(
                store.path.name + ".generation-anchor.lock"
            ),
        ))

    def load(
        self, _lookup: Any = _lookup_durable_reader_state
    ) -> SignerRuntimeGenerationActivation | None:
        state = _lookup(self)
        with confined_runtime_operation_lock(
            state.lock_path,
            repo_root=state.store.repo_root,
            allowed_root=state.store.allowed_root,
        ):
            if state.high_water.pending(state.anchor_id) is not None:
                raise ValueError("generation_reader_pending_transaction")
            activation = decode_signer_runtime_generation_state(
                state.store.load(),
                anchor_id=state.anchor_id,
                verifier=state.verifier,
                high_water_store_id=state.high_water_store_id,
                high_water_durability_receipt_id=(
                    state.durability_receipt_id
                ),
            )
            current = state.high_water.load(state.anchor_id)
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
    _issue_target: Any = _issue_reader_target,
    _issue_authority: Any = _issue_reader_authority,
) -> tuple[object, SignerRuntimeGenerationReaderAuthorityBoundary]:
    if type(reader) is not DurableSignerRuntimeGenerationReader:
        raise ValueError("generation_reader_authority_reader_invalid")
    handle = _ReaderHandle()
    _issue_target(handle, reader)
    authority = object()
    boundary = _ReaderAuthorityBoundary()
    _issue_authority(boundary, (authority, handle))
    return authority, boundary


def require_signer_runtime_generation_reader_authority(
    authority: object,
    boundary: SignerRuntimeGenerationReaderAuthorityBoundary,
) -> SignerRuntimeGenerationReader:
    if type(boundary) is not _ReaderAuthorityBoundary:
        raise ValueError("generation_reader_authority_boundary_invalid")
    return boundary.require(authority)


def create_signer_runtime_generation_high_water_reader_authority(
    reader: AtomicSignerRuntimeGenerationHighWaterReader,
    _issue_target: Any = _issue_high_water_target,
    _issue_authority: Any = _issue_high_water_authority,
) -> tuple[object, SignerRuntimeGenerationHighWaterReaderAuthorityBoundary]:
    if type(reader) is not AtomicSignerRuntimeGenerationHighWaterReader:
        raise ValueError("generation_high_water_reader_invalid")
    handle = _HighWaterReaderHandle()
    _issue_target(handle, reader)
    authority = object()
    boundary = _HighWaterReaderAuthorityBoundary()
    _issue_authority(boundary, (authority, handle))
    return authority, boundary


def require_signer_runtime_generation_high_water_reader_authority(
    authority: object,
    boundary: SignerRuntimeGenerationHighWaterReaderAuthorityBoundary,
) -> VerifiedSignerRuntimeGenerationHighWaterReader:
    if type(boundary) is not _HighWaterReaderAuthorityBoundary:
        raise ValueError("generation_high_water_reader_boundary_invalid")
    return boundary.require(authority)


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


del _lookup_durable_reader_state
del _lookup_high_water_authority, _lookup_high_water_target
del _lookup_reader_authority, _lookup_reader_target
del _issue_durable_reader_state
del _issue_high_water_authority, _issue_high_water_target
del _issue_reader_authority, _issue_reader_target


__all__ = [
    "DurableSignerRuntimeGenerationReader",
    "create_signer_runtime_generation_high_water_reader_authority",
    "create_signer_runtime_generation_reader_authority",
    "require_signer_runtime_generation_high_water_reader_authority",
    "require_signer_runtime_generation_reader_authority",
    "SignerRuntimeGenerationHighWaterReader",
    "SignerRuntimeGenerationHighWaterReaderAuthorityBoundary",
    "SignerRuntimeGenerationReader",
    "SignerRuntimeGenerationReaderAuthorityBoundary",
    "VerifiedSignerRuntimeGenerationHighWaterReader",
]
