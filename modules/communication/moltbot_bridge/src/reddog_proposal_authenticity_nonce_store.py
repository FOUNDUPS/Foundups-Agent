"""Durable signer-owned replay store for architect proposal attestations."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from pathlib import Path
from typing import Any, Callable, Mapping

from modules.communication.moltbot_bridge.src.reddog_authority_runtime_store import (
    AtomicJsonAuthorityRuntimeStore,
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


class AtomicProposalAuthenticityNonceStore:
    """Persist proposal nonce reservations under a confined signer runtime root."""

    def __init__(
        self,
        path: Path | str,
        *,
        allowed_root: Path | str,
        repo_root: Path | str,
        integrity_key: bytes,
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
        self._integrity_key = integrity_key
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
            state = self._store.load()
            updated, result = mutation(state)
            if updated is state:
                return result
            try:
                self._store.commit(
                    _seal_state(updated, self._integrity_key),
                    expected_revision=state.get("revision"),
                )
                return result
            except RuntimeError as exc:
                if str(exc) != "revision_conflict":
                    raise
        raise RuntimeError("proposal_authenticity_nonce_store_conflict")


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
    if not isinstance(raw_consumed, Mapping) or not isinstance(
        raw_reserved, Mapping
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
        "consumed",
        "reservations",
        "revision",
        "state_mac",
    }
    if state and not set(state).issubset(allowed):
        raise ValueError("proposal_authenticity_nonce_store_state_invalid")
    return {"schema_version": PROPOSAL_NONCE_STORE_SCHEMA_VERSION}


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


__all__ = [
    "AtomicProposalAuthenticityNonceStore",
    "DEFAULT_PROPOSAL_NONCE_CLOCK_SKEW_SECONDS",
    "DEFAULT_PROPOSAL_NONCE_MAX_ENTRIES",
    "DEFAULT_PROPOSAL_NONCE_RETENTION_SECONDS",
    "PROPOSAL_NONCE_STORE_SCHEMA_VERSION",
]
