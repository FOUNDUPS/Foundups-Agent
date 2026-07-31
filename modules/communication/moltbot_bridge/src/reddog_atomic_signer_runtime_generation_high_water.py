"""Authenticated durable high-water authority for signer generations."""

from __future__ import annotations

import hashlib
import json
import secrets
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping
from weakref import WeakKeyDictionary

from modules.communication.moltbot_bridge.src.reddog_authority_runtime_store import (
    AtomicJsonAuthorityRuntimeStore,
)
from modules.communication.moltbot_bridge.src.reddog_read_only_runtime_json_store import (
    ReadOnlyRuntimeJsonStore,
)
from modules.communication.moltbot_bridge.src.reddog_signer_runtime_generation_anchor import (
    SignerRuntimeGenerationHighWater,
    SignerRuntimeGenerationPendingAdvance,
    SignerRuntimeGenerationSigner,
    SignerRuntimeGenerationVerifier,
)
from modules.communication.moltbot_bridge.src.reddog_signer_runtime_generation_verifier_authority import (
    SignerRuntimeGenerationVerifierAuthorityBoundary,
    require_signer_runtime_generation_verifier_authority,
)
from modules.infrastructure.shared_utilities.runtime_artifact_safety import (
    confined_runtime_operation_lock,
)


SCHEMA_VERSION = "reddog_signer_runtime_generation_high_water.v1"
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
    ) -> None:
        self._store_id = _ascii(store_id, "store_id")
        self._durability_receipt_id = _sha256(
            durability_receipt_id, "durability_receipt_id"
        )
        self._signer = _signer(signer)
        self._verifier = _verifier(verifier)
        if self._signer.authenticator_id != self._verifier.authenticator_id:
            raise ValueError("generation_high_water_signer_verifier_mismatch")
        self._store = AtomicJsonAuthorityRuntimeStore(
            path,
            allowed_root=allowed_root,
            repo_root=repo_root,
        )
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

    def load(
        self, anchor_id: str
    ) -> SignerRuntimeGenerationHighWater | None:
        with self._lock():
            entry = _entry(self._load(), _anchor_id(anchor_id))
            return _high_water(entry.get("current"))

    def pending(
        self, anchor_id: str
    ) -> SignerRuntimeGenerationPendingAdvance | None:
        with self._lock():
            entry = _entry(self._load(), _anchor_id(anchor_id))
            return _pending(entry.get("pending"))

    def prepare(
        self,
        anchor_id: str,
        *,
        expected: SignerRuntimeGenerationHighWater | None,
        next_value: SignerRuntimeGenerationHighWater,
    ) -> SignerRuntimeGenerationPendingAdvance:
        anchor = _anchor_id(anchor_id)
        _optional_high_water(expected)
        _next_high_water(expected, next_value)
        transaction_id = _random_transaction_id()
        with self._lock():
            state = self._load()
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
            )
            self._commit(
                _updated_entry(
                    state, anchor, current=expected, pending=pending
                ),
                state,
            )
            return pending

    def commit_prepared(self, anchor_id: str, transaction_id: str) -> None:
        anchor = _anchor_id(anchor_id)
        transaction = _sha256(transaction_id, "transaction_id")
        with self._lock():
            state = self._load()
            entry = _entry(state, anchor)
            pending = _required_pending(entry, transaction)
            if _high_water(entry.get("current")) != pending.expected:
                raise RuntimeError("generation_high_water_commit_conflict")
            self._commit(
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
        with self._lock():
            state = self._load()
            entry = _entry(state, anchor)
            pending = _required_pending(entry, transaction)
            if _high_water(entry.get("current")) != pending.expected:
                raise RuntimeError("generation_high_water_abort_conflict")
            self._commit(
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
            anchor_id, expected=expected, next_value=next_value
        )
        self.commit_prepared(anchor_id, pending.transaction_id)
        if self.load(anchor_id) != next_value:
            raise RuntimeError("generation_high_water_commit_unverified")

    def _load(self) -> dict[str, Any]:
        state = self._store.load()
        return _verified_state(
            state,
            store_id=self._store_id,
            durability_receipt_id=self._durability_receipt_id,
            rollback_domain_digest=_root_digest(self.rollback_domain_root),
            verifier=self._verifier,
        )

    def _commit(
        self, state: Mapping[str, Any], previous: Mapping[str, Any]
    ) -> None:
        sealed = _sealed_state(
            state,
            store_id=self._store_id,
            durability_receipt_id=self._durability_receipt_id,
            rollback_domain_digest=_root_digest(self.rollback_domain_root),
            signer=self._signer,
            verifier=self._verifier,
        )
        self._store.commit(
            sealed,
            expected_revision=previous.get("revision"),
        )

    def _lock(self):
        return confined_runtime_operation_lock(
            self._lock_path,
            repo_root=self._store.repo_root,
            allowed_root=self._store.allowed_root,
        )


class AtomicSignerRuntimeGenerationHighWaterReader:
    """Verifier-only view of authenticated high-water state."""

    __slots__ = ("__weakref__",)

    def __init__(
        self,
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
    ) -> None:
        resolved_store_id = _ascii(store_id, "store_id")
        resolved_receipt_id = _sha256(
            durability_receipt_id, "durability_receipt_id"
        )
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
        _HIGH_WATER_READER_STATES[self] = _HighWaterReaderState(
            store_id=resolved_store_id,
            durability_receipt_id=resolved_receipt_id,
            verifier=verifier,
            store=store,
            lock_path=store.path.with_name(
                store.path.name + ".high-water-transaction.lock"
            ),
        )

    @property
    def store_id(self) -> str:
        return _HIGH_WATER_READER_STATES[self].store_id

    @property
    def durability_receipt_id(self) -> str:
        return _HIGH_WATER_READER_STATES[self].durability_receipt_id

    @property
    def rollback_domain_root(self) -> Path:
        return _HIGH_WATER_READER_STATES[self].store.allowed_root

    def load(
        self, anchor_id: str
    ) -> SignerRuntimeGenerationHighWater | None:
        return _high_water(self._entry(anchor_id).get("current"))

    def pending(
        self, anchor_id: str
    ) -> SignerRuntimeGenerationPendingAdvance | None:
        return _pending(self._entry(anchor_id).get("pending"))

    def _entry(self, anchor_id: str) -> dict[str, Any]:
        reader = _HIGH_WATER_READER_STATES[self]
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
                verifier=reader.verifier,
            )
            return _entry(state, _anchor_id(anchor_id))


@dataclass(frozen=True)
class _HighWaterReaderState:
    store_id: str
    durability_receipt_id: str
    verifier: SignerRuntimeGenerationVerifier
    store: ReadOnlyRuntimeJsonStore
    lock_path: Path


_HIGH_WATER_READER_STATES: WeakKeyDictionary[
    AtomicSignerRuntimeGenerationHighWaterReader, _HighWaterReaderState
] = WeakKeyDictionary()


def _verified_state(
    state: Mapping[str, Any],
    *,
    store_id: str,
    durability_receipt_id: str,
    rollback_domain_digest: str,
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


def _pending(
    value: Any,
) -> SignerRuntimeGenerationPendingAdvance | None:
    if value is None:
        return None
    if not isinstance(value, Mapping) or set(value) != {
        "transaction_id",
        "expected",
        "next_value",
    }:
        raise ValueError("generation_high_water_pending_invalid")
    pending = SignerRuntimeGenerationPendingAdvance(
        transaction_id=_sha256(value.get("transaction_id"), "transaction_id"),
        expected=_high_water(value.get("expected")),
        next_value=_required_high_water(value.get("next_value")),
    )
    _validate_pending_value(pending)
    return pending


def _required_pending(
    entry: Mapping[str, Any], transaction_id: str
) -> SignerRuntimeGenerationPendingAdvance:
    pending = _pending(entry.get("pending"))
    if pending is None or pending.transaction_id != transaction_id:
        raise RuntimeError("generation_high_water_transaction_conflict")
    return pending


def _validate_pending_value(
    value: SignerRuntimeGenerationPendingAdvance,
) -> None:
    if not isinstance(value, SignerRuntimeGenerationPendingAdvance):
        raise ValueError("generation_high_water_pending_invalid")
    _sha256(value.transaction_id, "transaction_id")
    _next_high_water(value.expected, value.next_value)


def _pending_dict(
    value: SignerRuntimeGenerationPendingAdvance,
) -> dict[str, Any]:
    return {
        "transaction_id": value.transaction_id,
        "expected": (
            None if value.expected is None else asdict(value.expected)
        ),
        "next_value": asdict(value.next_value),
    }


def _random_transaction_id() -> str:
    return "sha256:" + hashlib.sha256(secrets.token_bytes(32)).hexdigest()


def _high_water(
    value: Any,
) -> SignerRuntimeGenerationHighWater | None:
    if value is None:
        return None
    return _required_high_water(value)


def _required_high_water(value: Any) -> SignerRuntimeGenerationHighWater:
    if not isinstance(value, Mapping) or set(value) != {
        "generation",
        "revision",
    }:
        raise ValueError("generation_high_water_value_invalid")
    result = SignerRuntimeGenerationHighWater(
        generation=value.get("generation"),
        revision=value.get("revision"),
    )
    _optional_high_water(result)
    return result


def _next_high_water(
    expected: SignerRuntimeGenerationHighWater | None,
    value: SignerRuntimeGenerationHighWater | None,
) -> None:
    _optional_high_water(expected)
    _optional_high_water(value)
    if value is None or value.generation != (
        1 if expected is None else expected.generation + 1
    ):
        raise ValueError("generation_high_water_not_monotonic")


def _optional_high_water(
    value: SignerRuntimeGenerationHighWater | None,
) -> None:
    if value is None:
        return
    if (
        not isinstance(value, SignerRuntimeGenerationHighWater)
        or type(value.generation) is not int
        or value.generation < 1
        or not _revision_value(value.revision)
    ):
        raise ValueError("generation_high_water_value_invalid")


def _revision_value(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and value != "0" * 64
        and all(char in "0123456789abcdef" for char in value)
    )


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
