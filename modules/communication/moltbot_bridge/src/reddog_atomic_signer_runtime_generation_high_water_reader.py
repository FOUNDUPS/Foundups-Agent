"""Verifier-only reader for authenticated signer generation high-water state."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from modules.communication.moltbot_bridge.src.reddog_read_only_runtime_json_store import (
    ReadOnlyRuntimeJsonStore,
)
from modules.communication.moltbot_bridge.src.reddog_signer_runtime_generation_contract import (
    SignerRuntimeGenerationHighWater,
    SignerRuntimeGenerationPendingAdvance,
    SignerRuntimeGenerationVerifier,
    _build_process_local_registry,
)
from modules.communication.moltbot_bridge.src.reddog_signer_runtime_generation_verifier_authority import (
    SignerRuntimeGenerationVerifierAuthorityBoundary,
    require_signer_runtime_generation_verifier_authority,
)
from modules.communication.moltbot_bridge.src.reddog_signer_runtime_generation_witness_binding import (
    SignerRuntimeGenerationWitnessBinding,
    require_generation_witness_binding,
)
from modules.communication.moltbot_bridge.src.reddog_sqlite_monotonic_authority_store import (
    SqliteMonotonicAuthorityReader,
)
from modules.infrastructure.shared_utilities.runtime_artifact_safety import (
    confined_runtime_operation_lock,
)


_issue_state, _lookup_state = _build_process_local_registry(
    "generation_high_water_reader_state_unverified"
)
del _build_process_local_registry


@dataclass(frozen=True)
class _ReaderState:
    store: ReadOnlyRuntimeJsonStore
    lock_path: Path
    store_id: str
    durability_receipt_id: str
    verifier: SignerRuntimeGenerationVerifier
    witness: SqliteMonotonicAuthorityReader
    witness_binding: SignerRuntimeGenerationWitnessBinding


def _initialize_reader(
    self: object,
    path: Path | str,
    *,
    allowed_root: Path | str,
    repo_root: Path | str,
    store_id: str,
    durability_receipt_id: str,
    verifier_authority: object,
    verifier_authority_boundary: (
        SignerRuntimeGenerationVerifierAuthorityBoundary
    ),
    generation_witness_reader: SqliteMonotonicAuthorityReader,
    generation_witness_binding: SignerRuntimeGenerationWitnessBinding,
    issue_state: Any,
) -> None:
    from modules.communication.moltbot_bridge.src.reddog_atomic_signer_runtime_generation_high_water import (
        _ascii,
        _sha256,
        _verifier,
    )

    store = ReadOnlyRuntimeJsonStore(
        path,
        allowed_root=allowed_root,
        repo_root=repo_root,
    )
    verified = require_signer_runtime_generation_verifier_authority(
        verifier_authority,
        boundary=verifier_authority_boundary,
    )
    verifier = _verifier(verified)
    if type(generation_witness_reader) is not SqliteMonotonicAuthorityReader:
        raise ValueError("generation_high_water_witness_reader_invalid")
    witness = generation_witness_reader
    binding = require_generation_witness_binding(
        generation_witness_binding,
        authenticator_id=verifier.authenticator_id,
        high_water_store_id=store_id,
        high_water_durability_receipt_id=durability_receipt_id,
        witness_store_id=witness.store_id,
        witness_durability_receipt_id=witness.durability_receipt_id,
    )
    issue_state(
        self,
        _ReaderState(
            store=store,
            lock_path=store.path.with_name(
                store.path.name + ".high-water-transaction.lock"
            ),
            store_id=_ascii(store_id, "store_id"),
            durability_receipt_id=_sha256(
                durability_receipt_id, "durability_receipt_id"
            ),
            verifier=verifier,
            witness=witness,
            witness_binding=binding,
        ),
    )


def _reader_init(issue_state: Any):
    def initialize(
        self: object,
        path: Path | str,
        *,
        allowed_root: Path | str,
        repo_root: Path | str,
        store_id: str,
        durability_receipt_id: str,
        verifier_authority: object,
        verifier_authority_boundary: (
            SignerRuntimeGenerationVerifierAuthorityBoundary
        ),
        generation_witness_reader: SqliteMonotonicAuthorityReader,
        generation_witness_binding: SignerRuntimeGenerationWitnessBinding,
    ) -> None:
        _initialize_reader(
            self,
            path,
            allowed_root=allowed_root,
            repo_root=repo_root,
            store_id=store_id,
            durability_receipt_id=durability_receipt_id,
            verifier_authority=verifier_authority,
            verifier_authority_boundary=verifier_authority_boundary,
            generation_witness_reader=generation_witness_reader,
            generation_witness_binding=generation_witness_binding,
            issue_state=issue_state,
        )

    return initialize


def _reader_property(lookup: Any, name: str):
    def read(self: object) -> Any:
        state = lookup(self)
        if name == "rollback_domain_root":
            return state.store.allowed_root
        if name == "witness_rollback_domain_root":
            return state.witness.rollback_domain_root
        return getattr(state, name)

    return property(read)


def _reader_entry(lookup: Any):
    def entry(self: object, anchor_id: str) -> dict[str, Any]:
        from modules.communication.moltbot_bridge.src.reddog_atomic_signer_runtime_generation_high_water import (
            _anchor_id,
            _entry,
            _root_digest,
            _verified_state,
        )

        reader = lookup(self)
        with confined_runtime_operation_lock(
            reader.lock_path,
            repo_root=reader.store.repo_root,
            allowed_root=reader.store.allowed_root,
        ):
            state = _verified_state(
                reader.store.load(),
                store_id=reader.store_id,
                durability_receipt_id=reader.durability_receipt_id,
                rollback_domain_digest=_root_digest(
                    reader.store.allowed_root
                ),
                witness_store_id=reader.witness.store_id,
                witness_durability_receipt_id=(
                    reader.witness.durability_receipt_id
                ),
                witness_binding_context_digest=(
                    reader.witness_binding.context_digest()
                ),
                verifier=reader.verifier,
            )
            return _entry(state, _anchor_id(anchor_id))

    return entry


def _reader_witness_load(lookup: Any):
    def witness_load(
        self: object, anchor_id: str
    ) -> SignerRuntimeGenerationHighWater | None:
        from modules.communication.moltbot_bridge.src.reddog_atomic_signer_runtime_generation_high_water import (
            _witness_high_water,
        )

        state = lookup(self)
        return _witness_high_water(
            state.witness.load(
                state.witness_binding.anchor_binding_digest(anchor_id)
            )
        )

    return witness_load


class AtomicSignerRuntimeGenerationHighWaterReader:
    """Verifier-only view of authenticated high-water state."""

    __slots__ = ("__weakref__",)

    __init__ = _reader_init(_issue_state)
    store_id = _reader_property(_lookup_state, "store_id")
    durability_receipt_id = _reader_property(
        _lookup_state, "durability_receipt_id"
    )
    rollback_domain_root = _reader_property(
        _lookup_state, "rollback_domain_root"
    )
    witness_rollback_domain_root = _reader_property(
        _lookup_state, "witness_rollback_domain_root"
    )
    _entry = _reader_entry(_lookup_state)
    witness_load = _reader_witness_load(_lookup_state)

    def load(
        self, anchor_id: str
    ) -> SignerRuntimeGenerationHighWater | None:
        from modules.communication.moltbot_bridge.src.reddog_signer_runtime_generation_pending_codec import (
            decode_high_water,
        )

        return decode_high_water(self._entry(anchor_id).get("current"))

    def pending(
        self, anchor_id: str
    ) -> SignerRuntimeGenerationPendingAdvance | None:
        from modules.communication.moltbot_bridge.src.reddog_signer_runtime_generation_pending_codec import (
            decode_pending,
        )

        return decode_pending(self._entry(anchor_id).get("pending"))


del _issue_state, _lookup_state
del _reader_entry, _reader_init, _reader_property, _reader_witness_load


__all__ = ["AtomicSignerRuntimeGenerationHighWaterReader"]
