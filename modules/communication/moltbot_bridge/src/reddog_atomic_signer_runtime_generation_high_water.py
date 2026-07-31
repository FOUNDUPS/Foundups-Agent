"""Authenticated durable high-water authority for signer generations."""

from __future__ import annotations

import hashlib
import json
import secrets
from dataclasses import asdict
from pathlib import Path
from typing import Any, Mapping

from modules.communication.moltbot_bridge.src.reddog_authority_runtime_store import (
    AtomicJsonAuthorityRuntimeStore,
)
from modules.communication.moltbot_bridge.src.reddog_atomic_signer_runtime_generation_high_water_reader import (
    AtomicSignerRuntimeGenerationHighWaterReader,
)
from modules.communication.moltbot_bridge.src.reddog_proposal_authenticity_nonce_store import (
    ProposalReplayHighWater,
    ProposalReplayHighWaterStore,
)
from modules.communication.moltbot_bridge.src.reddog_signer_runtime_generation_anchor import (
    SignerRuntimeGenerationHighWater,
    SignerRuntimeGenerationPendingAdvance,
    SignerRuntimeGenerationSigner,
    SignerRuntimeGenerationVerifier,
)
from modules.communication.moltbot_bridge.src.reddog_signer_runtime_generation_pending_codec import (
    decode_high_water as _high_water,
    decode_pending as _pending,
    pending_dict as _pending_dict,
    require_pending as _required_pending,
    validate_next_high_water as _next_high_water,
    validate_optional_high_water as _optional_high_water,
    validate_pending as _validate_pending_value,
    validate_previous_anchor_state_json as _previous_anchor_state_json,
)
from modules.communication.moltbot_bridge.src.reddog_signer_runtime_generation_witness_binding import (
    SignerRuntimeGenerationWitnessBinding,
    require_generation_witness_binding,
)
from modules.infrastructure.shared_utilities.runtime_artifact_safety import (
    confined_runtime_operation_lock,
)


SCHEMA_VERSION = "reddog_signer_runtime_generation_high_water.v2"
_MAX_ANCHORS = 128
_MAX_AUTHENTICATION_TAG_LENGTH = 4096


class AtomicSignerRuntimeGenerationHighWaterStore:
    """Signer-owned authenticated CAS outside the anchor rollback domain."""

    def __init__(
        self,
        path: Path | str,
        *,
        allowed_root: Path | str,
        repo_root: Path | str,
        store_id: str,
        durability_receipt_id: str,
        signer: SignerRuntimeGenerationSigner,
        verifier: SignerRuntimeGenerationVerifier,
        generation_witness_store: ProposalReplayHighWaterStore,
        generation_witness_binding: SignerRuntimeGenerationWitnessBinding,
    ) -> None:
        self._store_id = _ascii(store_id, "store_id")
        self._durability_receipt_id = _sha256(
            durability_receipt_id, "durability_receipt_id"
        )
        self._signer = _signer(signer)
        self._verifier = _verifier(verifier)
        if self._signer.authenticator_id != self._verifier.authenticator_id:
            raise ValueError("generation_high_water_signer_verifier_mismatch")
        self._witness = _witness(generation_witness_store)
        self._witness_binding = require_generation_witness_binding(
            generation_witness_binding,
            authenticator_id=self._verifier.authenticator_id,
            high_water_store_id=self._store_id,
            high_water_durability_receipt_id=self._durability_receipt_id,
            witness_store_id=self._witness.store_id,
            witness_durability_receipt_id=(
                self._witness.durability_receipt_id
            ),
        )
        self._store = AtomicJsonAuthorityRuntimeStore(
            path,
            allowed_root=allowed_root,
            repo_root=repo_root,
        )
        if _paths_overlap(
            self._witness.rollback_domain_root,
            self._store.allowed_root,
        ):
            raise ValueError("generation_high_water_witness_domain_overlap")
        self._lock_path = self._store.path.with_name(
            self._store.path.name + ".high-water-transaction.lock"
        )

    @property
    def store_id(self) -> str:
        return self._store_id

    @property
    def durable(self) -> bool:
        return True
    @property
    def durability_receipt_id(self) -> str:
        return self._durability_receipt_id

    @property
    def rollback_domain_root(self) -> Path:
        return self._store.allowed_root

    @property
    def witness_rollback_domain_root(self) -> Path:
        return self._witness.rollback_domain_root
    def witness_load(
        self, anchor_id: str
    ) -> SignerRuntimeGenerationHighWater | None:
        return _witness_high_water(
            self._witness.load(self._witness_digest(anchor_id))
        )

    def witness_advance(
        self,
        anchor_id: str,
        *,
        expected: SignerRuntimeGenerationHighWater | None,
        next_value: SignerRuntimeGenerationHighWater,
    ) -> None:
        self._witness.advance(
            self._witness_digest(anchor_id),
            expected=_proposal_high_water(expected),
            next_value=_required_proposal_high_water(next_value),
        )

    def load(
        self, anchor_id: str
    ) -> SignerRuntimeGenerationHighWater | None:
        with _writer_lock(self):
            entry = _entry(_load_store_state(self), _anchor_id(anchor_id))
            return _high_water(entry.get("current"))

    def pending(
        self, anchor_id: str
    ) -> SignerRuntimeGenerationPendingAdvance | None:
        with _writer_lock(self):
            entry = _entry(_load_store_state(self), _anchor_id(anchor_id))
            return _pending(entry.get("pending"))

    def prepare(
        self,
        anchor_id: str,
        *,
        expected: SignerRuntimeGenerationHighWater | None,
        next_value: SignerRuntimeGenerationHighWater,
        previous_anchor_state_json: str = "{}",
    ) -> SignerRuntimeGenerationPendingAdvance:
        anchor = _anchor_id(anchor_id)
        _optional_high_water(expected)
        _next_high_water(expected, next_value)
        previous_state = _previous_anchor_state_json(
            previous_anchor_state_json
        )
        transaction_id = _random_transaction_id()
        with _writer_lock(self):
            state = _load_store_state(self)
            entry = _entry(state, anchor)
            if (
                _high_water(entry.get("current")) != expected
                or entry.get("pending") is not None
            ):
                raise RuntimeError("generation_high_water_prepare_conflict")
            pending = SignerRuntimeGenerationPendingAdvance(
                transaction_id=transaction_id,
                expected=expected,
                next_value=next_value,
                previous_anchor_state_json=previous_state,
            )
            _commit_store_state(
                self,
                _updated_entry(
                    state, anchor, current=expected, pending=pending
                ),
                state,
            )
            return pending

    def commit_prepared(self, anchor_id: str, transaction_id: str) -> None:
        anchor = _anchor_id(anchor_id)
        transaction = _sha256(transaction_id, "transaction_id")
        with _writer_lock(self):
            state = _load_store_state(self)
            entry = _entry(state, anchor)
            pending = _required_pending(entry, transaction)
            if _high_water(entry.get("current")) != pending.expected:
                raise RuntimeError("generation_high_water_commit_conflict")
            _commit_store_state(
                self,
                _updated_entry(
                    state,
                    anchor,
                    current=pending.next_value,
                    pending=None,
                ),
                state,
            )

    def abort_prepared(self, anchor_id: str, transaction_id: str) -> None:
        anchor = _anchor_id(anchor_id)
        transaction = _sha256(transaction_id, "transaction_id")
        with _writer_lock(self):
            state = _load_store_state(self)
            entry = _entry(state, anchor)
            pending = _required_pending(entry, transaction)
            if _high_water(entry.get("current")) != pending.expected:
                raise RuntimeError("generation_high_water_abort_conflict")
            _commit_store_state(
                self,
                _updated_entry(
                    state,
                    anchor,
                    current=pending.expected,
                    pending=None,
                ),
                state,
            )

    def advance(
        self,
        anchor_id: str,
        *,
        expected: SignerRuntimeGenerationHighWater | None,
        next_value: SignerRuntimeGenerationHighWater,
    ) -> None:
        pending = self.prepare(
            anchor_id,
            expected=expected,
            next_value=next_value,
            previous_anchor_state_json="{}",
        )
        self.commit_prepared(anchor_id, pending.transaction_id)
        if self.load(anchor_id) != next_value:
            raise RuntimeError("generation_high_water_commit_unverified")

    def _witness_digest(self, anchor_id: str) -> str:
        return self._witness_binding.anchor_binding_digest(
            _anchor_id(anchor_id)
        )


def _load_store_state(
    writer: AtomicSignerRuntimeGenerationHighWaterStore,
) -> dict[str, Any]:
    return _verified_state(
        writer._store.load(),
        store_id=writer._store_id,
        durability_receipt_id=writer._durability_receipt_id,
        rollback_domain_digest=_root_digest(writer.rollback_domain_root),
        witness_store_id=writer._witness.store_id,
        witness_durability_receipt_id=(
            writer._witness.durability_receipt_id
        ),
        witness_binding_context_digest=(
            writer._witness_binding.context_digest()
        ),
        verifier=writer._verifier,
    )


def _commit_store_state(
    writer: AtomicSignerRuntimeGenerationHighWaterStore,
    state: Mapping[str, Any],
    previous: Mapping[str, Any],
) -> None:
    sealed = _sealed_state(
        state,
        store_id=writer._store_id,
        durability_receipt_id=writer._durability_receipt_id,
        rollback_domain_digest=_root_digest(writer.rollback_domain_root),
        witness_store_id=writer._witness.store_id,
        witness_durability_receipt_id=(
            writer._witness.durability_receipt_id
        ),
        witness_binding_context_digest=(
            writer._witness_binding.context_digest()
        ),
        signer=writer._signer,
        verifier=writer._verifier,
    )
    writer._store.commit(
        sealed,
        expected_revision=previous.get("revision"),
    )


def _writer_lock(writer: AtomicSignerRuntimeGenerationHighWaterStore):
    return confined_runtime_operation_lock(
        writer._lock_path,
        repo_root=writer._store.repo_root,
        allowed_root=writer._store.allowed_root,
    )


def _verified_state(
    state: Mapping[str, Any],
    *,
    store_id: str,
    durability_receipt_id: str,
    rollback_domain_digest: str,
    witness_store_id: str,
    witness_durability_receipt_id: str,
    witness_binding_context_digest: str,
    verifier: SignerRuntimeGenerationVerifier,
) -> dict[str, Any]:
    if not state:
        return {}
    required = {
        "schema_version",
        "store_id",
        "durability_receipt_id",
        "rollback_domain_digest",
        "authenticator_id",
        "witness_store_id",
        "witness_durability_receipt_id",
        "witness_binding_context_digest",
        "entries",
        "authentication_tag",
        "revision",
    }
    if (
        set(state) != required
        or state.get("schema_version") != SCHEMA_VERSION
        or state.get("store_id") != store_id
        or state.get("durability_receipt_id") != durability_receipt_id
        or state.get("rollback_domain_digest") != rollback_domain_digest
        or state.get("authenticator_id") != verifier.authenticator_id
        or state.get("witness_store_id") != witness_store_id
        or state.get("witness_durability_receipt_id")
        != witness_durability_receipt_id
        or state.get("witness_binding_context_digest")
        != witness_binding_context_digest
        or not isinstance(state.get("entries"), Mapping)
        or len(state["entries"]) > _MAX_ANCHORS
        or state.get("revision") != _revision(state)
    ):
        raise ValueError("generation_high_water_state_invalid")
    unsigned = dict(state)
    tag = unsigned.pop("authentication_tag")
    unsigned.pop("revision")
    if (
        not _authentication_tag(tag)
        or not verifier.verify(_canonical(unsigned), str(tag))
    ):
        raise ValueError("generation_high_water_authentication_invalid")
    for anchor_id in state["entries"]:
        _entry(state, _anchor_id(anchor_id))
    return dict(state)


def _sealed_state(
    state: Mapping[str, Any],
    *,
    store_id: str,
    durability_receipt_id: str,
    rollback_domain_digest: str,
    witness_store_id: str,
    witness_durability_receipt_id: str,
    witness_binding_context_digest: str,
    signer: SignerRuntimeGenerationSigner,
    verifier: SignerRuntimeGenerationVerifier,
) -> dict[str, Any]:
    entries = dict(state.get("entries") or {})
    unsigned = {
        "schema_version": SCHEMA_VERSION,
        "store_id": store_id,
        "durability_receipt_id": durability_receipt_id,
        "rollback_domain_digest": rollback_domain_digest,
        "authenticator_id": verifier.authenticator_id,
        "witness_store_id": witness_store_id,
        "witness_durability_receipt_id": witness_durability_receipt_id,
        "witness_binding_context_digest": witness_binding_context_digest,
        "entries": entries,
    }
    tag = signer.authenticate(_canonical(unsigned))
    if (
        not _authentication_tag(tag)
        or not verifier.verify(_canonical(unsigned), tag)
    ):
        raise ValueError("generation_high_water_authentication_rejected")
    return {**unsigned, "authentication_tag": tag}


def _entry(
    state: Mapping[str, Any], anchor_id: str
) -> dict[str, Any]:
    value = (state.get("entries") or {}).get(anchor_id)
    if value is None:
        return {"current": None, "pending": None}
    if not isinstance(value, Mapping) or set(value) != {"current", "pending"}:
        raise ValueError("generation_high_water_entry_invalid")
    current = _high_water(value.get("current"))
    pending = _pending(value.get("pending"))
    if pending is not None and pending.expected != current:
        raise ValueError("generation_high_water_pending_expected_mismatch")
    return {
        "current": None if current is None else asdict(current),
        "pending": None if pending is None else _pending_dict(pending),
    }


def _updated_entry(
    state: Mapping[str, Any],
    anchor_id: str,
    *,
    current: SignerRuntimeGenerationHighWater | None,
    pending: SignerRuntimeGenerationPendingAdvance | None,
) -> dict[str, Any]:
    _optional_high_water(current)
    if pending is not None:
        _validate_pending_value(pending)
        if pending.expected != current:
            raise ValueError("generation_high_water_pending_expected_mismatch")
    entries = dict(state.get("entries") or {})
    if current is None and pending is None:
        entries.pop(anchor_id, None)
    else:
        entries[anchor_id] = {
            "current": None if current is None else asdict(current),
            "pending": None if pending is None else _pending_dict(pending),
        }
    return {"entries": entries}


def _random_transaction_id() -> str:
    return "sha256:" + hashlib.sha256(secrets.token_bytes(32)).hexdigest()


def _signer(
    value: Any,
) -> SignerRuntimeGenerationSigner:
    if not callable(getattr(value, "authenticate", None)):
        raise ValueError("generation_high_water_signer_invalid")
    _ascii(getattr(value, "authenticator_id", None), "authenticator_id")
    return value


def _verifier(
    value: Any,
) -> SignerRuntimeGenerationVerifier:
    if not callable(getattr(value, "verify", None)) or callable(
        getattr(value, "authenticate", None)
    ):
        raise ValueError("generation_high_water_verifier_invalid")
    _ascii(getattr(value, "authenticator_id", None), "authenticator_id")
    return value


def _witness(value: Any) -> ProposalReplayHighWaterStore:
    if (
        not isinstance(value, ProposalReplayHighWaterStore)
        or value.durable is not True
        or not isinstance(value.store_id, str)
        or not value.store_id.strip()
        or not value.store_id.isascii()
        or not isinstance(
            getattr(value, "rollback_domain_root", None), Path
        )
        or not _sha256(
            value.durability_receipt_id,
            "witness_durability_receipt_id",
        )
    ):
        raise ValueError("generation_high_water_witness_invalid")
    return value


def _proposal_high_water(
    value: SignerRuntimeGenerationHighWater | None,
) -> ProposalReplayHighWater | None:
    if value is None:
        return None
    return _required_proposal_high_water(value)


def _required_proposal_high_water(
    value: SignerRuntimeGenerationHighWater,
) -> ProposalReplayHighWater:
    _optional_high_water(value)
    return ProposalReplayHighWater(
        sequence=value.generation,
        state_revision=value.revision,
    )


def _witness_high_water(
    value: ProposalReplayHighWater | None,
) -> SignerRuntimeGenerationHighWater | None:
    if value is None:
        return None
    result = SignerRuntimeGenerationHighWater(
        generation=value.sequence,
        revision=value.state_revision,
    )
    _optional_high_water(result)
    return result


def _authentication_tag(value: Any) -> bool:
    return (
        isinstance(value, str)
        and bool(value)
        and value.isascii()
        and len(value) <= _MAX_AUTHENTICATION_TAG_LENGTH
    )


def _anchor_id(value: Any) -> str:
    return _ascii(value, "anchor_id")


def _ascii(value: Any, name: str) -> str:
    if (
        not isinstance(value, str)
        or not value.strip()
        or not value.isascii()
        or len(value) > 1024
    ):
        raise ValueError(f"generation_high_water_{name}_invalid")
    return value.strip()


def _sha256(value: Any, name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 71
        or not value.startswith("sha256:")
        or value[7:] == "0" * 64
        or any(char not in "0123456789abcdef" for char in value[7:])
    ):
        raise ValueError(f"generation_high_water_{name}_invalid")
    return value


def _revision(state: Mapping[str, Any]) -> str:
    unsigned = dict(state)
    unsigned.pop("revision", None)
    return hashlib.sha256(_canonical(unsigned)).hexdigest()


def _root_digest(value: Path) -> str:
    return "sha256:" + hashlib.sha256(
        str(value.resolve()).encode("utf-8")
    ).hexdigest()


def _paths_overlap(first: Path, second: Path) -> bool:
    return first == second or first in second.parents or second in first.parents


def _canonical(value: Mapping[str, Any]) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


__all__ = [
    "AtomicSignerRuntimeGenerationHighWaterReader",
    "AtomicSignerRuntimeGenerationHighWaterStore",
    "SCHEMA_VERSION",
]
