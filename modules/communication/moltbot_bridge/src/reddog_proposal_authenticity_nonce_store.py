"""Durable signer-owned replay store for architect proposal attestations."""

from __future__ import annotations

import hashlib
import hmac
import json
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Protocol, runtime_checkable

from modules.communication.moltbot_bridge.src.reddog_authority_runtime_store import (
    AtomicJsonAuthorityRuntimeStore,
)
from modules.infrastructure.shared_utilities.runtime_artifact_safety import (
    confined_runtime_operation_lock,
)

PROPOSAL_NONCE_STORE_SCHEMA_VERSION = (
    "reddog_architect_proposal_nonce_store.v1"
)
_MAX_COMMIT_RETRIES = 4
DEFAULT_PROPOSAL_NONCE_CLOCK_SKEW_SECONDS = 60
DEFAULT_PROPOSAL_NONCE_RETENTION_SECONDS = 300
DEFAULT_PROPOSAL_NONCE_MAX_ENTRIES = 2048
_MIN_INTEGRITY_KEY_BYTES = 16
_STATE_MAC_PREFIX = "proposal-nonce-state-mac-v1:"


@dataclass(frozen=True)
class ProposalReplayHighWater:
    sequence: int
    state_revision: str


@runtime_checkable
class ProposalReplayHighWaterStore(Protocol):
    """Independent monotonic authority outside the nonce-state rollback domain."""

    @property
    def store_id(self) -> str: ...

    @property
    def durable(self) -> bool: ...

    @property
    def durability_receipt_id(self) -> str | None: ...

    def load(
        self,
        replay_store_binding_digest: str,
    ) -> ProposalReplayHighWater | None: ...

    def advance(
        self,
        replay_store_binding_digest: str,
        *,
        expected: ProposalReplayHighWater | None,
        next_value: ProposalReplayHighWater,
    ) -> None: ...


class InMemoryProposalReplayHighWaterStore:
    """Thread-safe independent high-water authority for deterministic tests."""

    def __init__(self, store_id: str = "in-memory:test-only") -> None:
        if not _text(store_id) or not store_id.isascii():
            raise ValueError("proposal_replay_high_water_store_id_invalid")
        self._store_id = store_id
        self._values: dict[str, ProposalReplayHighWater] = {}
        self._lock = threading.Lock()

    @property
    def store_id(self) -> str:
        return self._store_id

    @property
    def durable(self) -> bool:
        return False

    @property
    def durability_receipt_id(self) -> None:
        return None

    def load(
        self,
        replay_store_binding_digest: str,
    ) -> ProposalReplayHighWater | None:
        with self._lock:
            return self._values.get(replay_store_binding_digest)

    def advance(
        self,
        replay_store_binding_digest: str,
        *,
        expected: ProposalReplayHighWater | None,
        next_value: ProposalReplayHighWater,
    ) -> None:
        with self._lock:
            current = self._values.get(replay_store_binding_digest)
            if current != expected:
                raise RuntimeError(
                    "proposal_replay_high_water_conflict"
                )
            if (
                next_value.sequence
                != (current.sequence + 1 if current is not None else 1)
                or not _text(next_value.state_revision)
            ):
                raise ValueError(
                    "proposal_replay_high_water_invalid"
                )
            self._values[replay_store_binding_digest] = next_value


class AtomicProposalAuthenticityNonceStore:
    """Persist proposal nonce reservations under a confined signer runtime root."""

    def __init__(
        self,
        path: Path | str,
        *,
        allowed_root: Path | str,
        repo_root: Path | str,
        integrity_key: bytes,
        replay_store_binding_digest: str,
        high_water_store: ProposalReplayHighWaterStore,
        clock: Callable[[], float] = time.time,
        clock_skew_seconds: int = (
            DEFAULT_PROPOSAL_NONCE_CLOCK_SKEW_SECONDS
        ),
        retention_seconds: int = DEFAULT_PROPOSAL_NONCE_RETENTION_SECONDS,
        max_entries: int = DEFAULT_PROPOSAL_NONCE_MAX_ENTRIES,
    ) -> None:
        if (
            not isinstance(integrity_key, bytes)
            or len(integrity_key) < _MIN_INTEGRITY_KEY_BYTES
        ):
            raise ValueError(
                "proposal_authenticity_nonce_integrity_key_invalid"
            )
        if (
            not callable(clock)
            or type(clock_skew_seconds) is not int
            or clock_skew_seconds < 0
            or type(retention_seconds) is not int
            or retention_seconds < clock_skew_seconds
            or type(max_entries) is not int
            or max_entries < 1
            or max_entries > DEFAULT_PROPOSAL_NONCE_MAX_ENTRIES
        ):
            raise ValueError("proposal_authenticity_nonce_policy_invalid")
        self._store = AtomicJsonAuthorityRuntimeStore(
            path,
            allowed_root=allowed_root,
            repo_root=repo_root,
        )
        self._repo_root = Path(repo_root).resolve()
        self._allowed_root = Path(allowed_root).resolve()
        if not _sha256(replay_store_binding_digest):
            raise ValueError(
                "proposal_authenticity_nonce_replay_binding_invalid"
            )
        self._integrity_key = integrity_key
        self._replay_store_binding_digest = (
            replay_store_binding_digest
        )
        if not isinstance(
            high_water_store,
            ProposalReplayHighWaterStore,
        ):
            raise ValueError(
                "proposal_authenticity_high_water_store_invalid"
            )
        self._high_water_store = high_water_store
        # This transaction lock must differ from AtomicJsonAuthorityRuntimeStore's
        # own ".operation" lock because one mutation calls that store while held.
        self._transaction_lock_path = Path(
            str(self._store.path) + ".proposal-transaction.lock"
        )
        self._clock = clock
        self._clock_skew_seconds = clock_skew_seconds
        self._retention_seconds = retention_seconds
        self._max_entries = max_entries

    @property
    def path(self) -> Path:
        return self._store.path

    def reserve(self, nonce: str, *, expires_at: int, subject: str) -> str | None:
        clean_nonce = _text(nonce)
        clean_subject = _text(subject)
        expiry = int(expires_at)
        if not clean_nonce or not clean_subject or expiry <= 0:
            return None
        reservation = _digest(
            {
                "expires_at": expiry,
                "nonce": clean_nonce,
                "subject": clean_subject,
            }
        )

        def mutate(state: dict[str, Any]) -> tuple[dict[str, Any], str | None]:
            now_epoch = int(self._clock())
            if expiry <= now_epoch:
                return state, None
            consumed, reserved = _validated_entries(
                state,
                integrity_key=self._integrity_key,
            )
            consumed, reserved = _pruned_entries(
                consumed,
                reserved,
                now_epoch=now_epoch,
                clock_skew_seconds=self._clock_skew_seconds,
                retention_seconds=self._retention_seconds,
            )
            key = _nonce_key(clean_subject, clean_nonce)
            if key in consumed or any(
                _nonce_key(
                    _text(value.get("subject")),
                    _text(value.get("nonce")),
                )
                == key
                for value in reserved.values()
            ):
                return state, None
            if len(consumed) + len(reserved) >= self._max_entries:
                return state, None
            updated = _base_state(state)
            updated["consumed"] = consumed
            updated["reservations"] = {
                **reserved,
                reservation: {
                    "expires_at": expiry,
                    "nonce": clean_nonce,
                    "subject": clean_subject,
                },
            }
            return updated, reservation

        return self._mutate(mutate)

    def commit(self, reservation: str) -> None:
        token = _text(reservation)
        if not token:
            raise ValueError("proposal_authenticity_nonce_reservation_invalid")

        def mutate(state: dict[str, Any]) -> tuple[dict[str, Any], bool]:
            consumed, reserved = _validated_entries(
                state,
                integrity_key=self._integrity_key,
            )
            entry = reserved.pop(token, None)
            if entry is None:
                raise ValueError(
                    "proposal_authenticity_nonce_reservation_invalid"
                )
            if int(entry["expires_at"]) <= int(self._clock()):
                raise ValueError(
                    "proposal_authenticity_nonce_reservation_expired"
                )
            key = _nonce_key(
                _text(entry.get("subject")),
                _text(entry.get("nonce")),
            )
            if key in consumed:
                raise ValueError("proposal_authenticity_nonce_replay")
            updated = _base_state(state)
            updated["consumed"] = {
                **consumed,
                key: {
                    "expires_at": int(entry["expires_at"]),
                    "nonce_digest": _digest(_text(entry["nonce"])),
                    "subject_digest": _digest(_text(entry["subject"])),
                },
            }
            updated["reservations"] = reserved
            return updated, True

        if self._mutate(mutate) is not True:
            raise ValueError("proposal_authenticity_nonce_commit_failed")

    def rollback(self, reservation: str) -> None:
        token = _text(reservation)
        if not token:
            return

        def mutate(state: dict[str, Any]) -> tuple[dict[str, Any], bool]:
            consumed, reserved = _validated_entries(
                state,
                integrity_key=self._integrity_key,
            )
            if token not in reserved:
                return state, True
            reserved.pop(token)
            updated = _base_state(state)
            updated["consumed"] = consumed
            updated["reservations"] = reserved
            return updated, True

        self._mutate(mutate)

    def _mutate(
        self,
        mutation: Callable[
            [dict[str, Any]],
            tuple[dict[str, Any], Any],
        ],
    ) -> Any:
        for _ in range(_MAX_COMMIT_RETRIES):
            with confined_runtime_operation_lock(
                self._transaction_lock_path,
                repo_root=self._repo_root,
                allowed_root=self._allowed_root,
            ):
                state, high_water = self._load_state()
                updated, result = mutation(state)
                if updated is state:
                    return result
                try:
                    state_revision = self._store.commit(
                        _seal_state(updated, self._integrity_key),
                        expected_revision=state.get("revision"),
                    )
                    next_value = ProposalReplayHighWater(
                        sequence=int(updated["sequence"]),
                        state_revision=state_revision,
                    )
                    self._high_water_store.advance(
                        self._replay_store_binding_digest,
                        expected=high_water,
                        next_value=next_value,
                    )
                    return result
                except RuntimeError as exc:
                    if str(exc) not in {
                        "revision_conflict",
                        "proposal_replay_high_water_conflict",
                    }:
                        raise
        raise RuntimeError("proposal_authenticity_nonce_store_conflict")

    def _load_state(
        self,
    ) -> tuple[dict[str, Any], ProposalReplayHighWater | None]:
        state = self._store.load()
        high_water = self._high_water_store.load(
            self._replay_store_binding_digest
        )
        if not state:
            if high_water is None:
                return {}, None
            raise ValueError(
                "proposal_authenticity_nonce_store_rollback_detected"
            )
        _validate_state_integrity(state, self._integrity_key)
        state_value = ProposalReplayHighWater(
            sequence=int(state.get("sequence") or 0),
            state_revision=str(state.get("revision") or ""),
        )
        if high_water == state_value:
            return state, high_water
        expected_sequence = (
            high_water.sequence + 1
            if high_water is not None
            else 1
        )
        if state_value.sequence != expected_sequence:
            raise ValueError(
                "proposal_authenticity_nonce_store_rollback_detected"
            )
        self._high_water_store.advance(
            self._replay_store_binding_digest,
            expected=high_water,
            next_value=state_value,
        )
        return state, state_value


def _validated_entries(
    state: Mapping[str, Any],
    *,
    integrity_key: bytes,
) -> tuple[dict[str, Mapping[str, Any]], dict[str, Mapping[str, Any]]]:
    if not state:
        return {}, {}
    _validate_state_integrity(state, integrity_key)
    if state.get("schema_version") != PROPOSAL_NONCE_STORE_SCHEMA_VERSION:
        raise ValueError("proposal_authenticity_nonce_store_schema_invalid")
    raw_consumed = state.get("consumed")
    raw_reserved = state.get("reservations")
    if (
        type(state.get("sequence")) is not int
        or int(state["sequence"]) < 1
        or not isinstance(raw_consumed, Mapping)
        or not isinstance(raw_reserved, Mapping)
    ):
        raise ValueError("proposal_authenticity_nonce_store_state_invalid")
    consumed = _entry_mapping(raw_consumed, consumed=True)
    reserved = _entry_mapping(raw_reserved, consumed=False)
    return consumed, reserved


def _entry_mapping(
    values: Mapping[str, Any],
    *,
    consumed: bool,
) -> dict[str, Mapping[str, Any]]:
    result: dict[str, Mapping[str, Any]] = {}
    required = (
        {"expires_at", "nonce_digest", "subject_digest"}
        if consumed
        else {"expires_at", "nonce", "subject"}
    )
    for key, value in values.items():
        if (
            not isinstance(key, str)
            or not key
            or not isinstance(value, Mapping)
            or set(value) != required
            or not isinstance(value.get("expires_at"), int)
            or int(value["expires_at"]) <= 0
            or any(not _text(value.get(field)) for field in required - {"expires_at"})
        ):
            raise ValueError("proposal_authenticity_nonce_store_state_invalid")
        result[key] = dict(value)
    return result


def _base_state(state: Mapping[str, Any]) -> dict[str, Any]:
    allowed = {
        "schema_version",
        "sequence",
        "consumed",
        "reservations",
        "revision",
        "state_mac",
    }
    if state and not set(state).issubset(allowed):
        raise ValueError("proposal_authenticity_nonce_store_state_invalid")
    return {
        "schema_version": PROPOSAL_NONCE_STORE_SCHEMA_VERSION,
        "sequence": int(state.get("sequence") or 0) + 1,
    }


def _nonce_key(subject: str, nonce: str) -> str:
    return _digest({"nonce": nonce, "subject": subject})


def _pruned_entries(
    consumed: Mapping[str, Mapping[str, Any]],
    reserved: Mapping[str, Mapping[str, Any]],
    *,
    now_epoch: int,
    clock_skew_seconds: int,
    retention_seconds: int,
) -> tuple[dict[str, Mapping[str, Any]], dict[str, Mapping[str, Any]]]:
    live_consumed = {
        key: dict(value)
        for key, value in consumed.items()
        if int(value["expires_at"]) + retention_seconds > now_epoch
    }
    live_reserved = {
        key: dict(value)
        for key, value in reserved.items()
        if int(value["expires_at"]) + clock_skew_seconds > now_epoch
    }
    return live_consumed, live_reserved


def _validate_state_integrity(
    state: Mapping[str, Any],
    integrity_key: bytes,
) -> None:
    supplied_mac = state.get("state_mac")
    supplied_revision = state.get("revision")
    if (
        not isinstance(supplied_mac, str)
        or not supplied_mac.startswith(_STATE_MAC_PREFIX)
        or not isinstance(supplied_revision, str)
        or not supplied_revision
    ):
        raise ValueError("proposal_authenticity_nonce_store_integrity_invalid")
    expected_mac = _state_mac(state, integrity_key)
    if not hmac.compare_digest(supplied_mac, expected_mac):
        raise ValueError("proposal_authenticity_nonce_store_integrity_invalid")
    unsigned = dict(state)
    unsigned.pop("revision", None)
    expected_revision = hashlib.sha256(
        json.dumps(
            unsigned,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()
    if not hmac.compare_digest(supplied_revision, expected_revision):
        raise ValueError("proposal_authenticity_nonce_store_integrity_invalid")


def _seal_state(state: Mapping[str, Any], integrity_key: bytes) -> dict[str, Any]:
    sealed = dict(state)
    sealed.pop("revision", None)
    sealed.pop("state_mac", None)
    sealed["state_mac"] = _state_mac(sealed, integrity_key)
    return sealed


def _state_mac(state: Mapping[str, Any], integrity_key: bytes) -> str:
    unsigned = dict(state)
    unsigned.pop("revision", None)
    unsigned.pop("state_mac", None)
    raw = json.dumps(
        unsigned,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")
    return _STATE_MAC_PREFIX + hmac.new(
        integrity_key,
        raw,
        hashlib.sha256,
    ).hexdigest()


def _digest(value: Any) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _sha256(value: Any) -> bool:
    text = _text(value)
    return len(text) == 71 and text.startswith("sha256:") and all(
        char in "0123456789abcdef" for char in text[7:]
    )


__all__ = [
    "AtomicProposalAuthenticityNonceStore",
    "DEFAULT_PROPOSAL_NONCE_CLOCK_SKEW_SECONDS",
    "DEFAULT_PROPOSAL_NONCE_MAX_ENTRIES",
    "DEFAULT_PROPOSAL_NONCE_RETENTION_SECONDS",
    "InMemoryProposalReplayHighWaterStore",
    "ProposalReplayHighWater",
    "ProposalReplayHighWaterStore",
    "PROPOSAL_NONCE_STORE_SCHEMA_VERSION",
]
