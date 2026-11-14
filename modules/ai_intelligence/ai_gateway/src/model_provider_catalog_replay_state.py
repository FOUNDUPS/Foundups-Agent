"""Strict durable replay state for scheduled provider catalog discovery."""

from __future__ import annotations

import json
import os
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from modules.ai_intelligence.ai_gateway.src.model_provider_catalog_artifact_store import (
    ProviderCatalogArtifactStore,
)
from modules.ai_intelligence.ai_gateway.src.model_provider_catalog_snapshot import (
    MAX_RESPONSE_BYTES,
    DiscoveryInvocation,
    DiscoveryReceipt,
    ProviderCatalogCandidateSnapshot,
    rehydrate_candidate_snapshot,
    rehydrate_discovery_invocation,
    rehydrate_discovery_receipt,
)
from modules.infrastructure.shared_utilities.runtime_artifact_safety import (
    secure_read_confined_bytes,
    validate_runtime_artifact_path,
    validate_runtime_root_path,
)

LEDGER_SCHEMA = "model_provider_catalog_scheduled_replay_ledger.v1"
MAX_LEDGER_ENTRIES = 64
MAX_LEDGER_BYTES = 512 * 1024
MAX_RECEIPT_BYTES = 64 * 1024
# Direct discovery admits up to 8 MiB of JSON. Four times that bound covers
# sanitized structure/JSON escaping, with one receipt allowance for envelope
# metadata. This remains a fixed read cap rather than an unbounded file read.
MAX_CANDIDATE_BYTES = (4 * MAX_RESPONSE_BYTES) + MAX_RECEIPT_BYTES
_STATUSES = frozenset(
    {"ARMED", "BLOCKED_PRECALL", "INDETERMINATE", "COMPLETED", "FAILED"}
)
_LEDGER_KEYS = frozenset({"schema_version", "updated_at_ms", "entries"})
_ENTRY_KEYS = frozenset(
    {"invocation", "status", "receipt", "window_expires_at_ms"}
)


class ReplayStateError(ValueError):
    """Scheduled replay evidence is absent from the trusted state model."""


@dataclass(frozen=True)
class ScheduledDiscoveryPaths:
    """Fixed trusted runtime identities for scheduled discovery."""

    runtime_root: Path
    attempt_path: Path
    candidate_path: Path
    ledger_path: Path
    guard_identity: Path


def derive_scheduled_discovery_paths(
    *, repo_root: Path | str, runtime_root: Path | str
) -> ScheduledDiscoveryPaths:
    """Derive all fixed identities below one validated outside-repo root."""

    root = validate_runtime_root_path(runtime_root, repo_root=repo_root)
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    root = validate_runtime_root_path(root, repo_root=repo_root)
    names = (
        "openrouter_scheduled_discovery_attempt.json",
        "openrouter_scheduled_discovery_candidate.json",
        "openrouter_scheduled_discovery_ledger.json",
        "openrouter_scheduled_discovery_operation.guard",
    )
    targets = tuple(
        validate_runtime_artifact_path(
            root / name,
            repo_root=repo_root,
            allowed_root=root,
        )
        for name in names
    )
    if len(set(targets)) != len(targets):
        raise ReplayStateError("scheduled_discovery_paths_not_distinct")
    return ScheduledDiscoveryPaths(root, *targets)


def empty_replay_ledger() -> dict[str, Any]:
    """Return a canonical empty replay ledger."""

    return {
        "schema_version": LEDGER_SCHEMA,
        "updated_at_ms": 0,
        "entries": {},
    }


def load_replay_ledger(
    paths: ScheduledDiscoveryPaths, *, now_ms: int
) -> dict[str, Any]:
    """Load a strict bounded ledger; absence is the only empty-state signal."""

    raw = _read_optional_json(
        paths.ledger_path,
        paths.runtime_root,
        MAX_LEDGER_BYTES,
        "scheduled_replay_ledger_invalid",
    )
    state = empty_replay_ledger() if raw is None else raw
    validate_replay_ledger(state, now_ms=now_ms)
    return state


def save_replay_ledger(
    paths: ScheduledDiscoveryPaths,
    state: dict[str, Any],
    *,
    now_ms: int,
    store: ProviderCatalogArtifactStore,
) -> None:
    """Validate and atomically publish the bounded ledger."""

    state["updated_at_ms"] = now_ms
    validate_replay_ledger(state, now_ms=now_ms)
    encoded = json.dumps(
        state, sort_keys=True, separators=(",", ":")
    ) + "\n"
    if len(encoded.encode("utf-8")) > MAX_LEDGER_BYTES:
        raise ReplayStateError("scheduled_replay_ledger_capacity_exhausted")
    store.replace_text(paths.ledger_path, encoded)


def validate_replay_ledger(state: object, *, now_ms: int) -> None:
    """Validate exact schemas and invocation/receipt binding."""

    if not isinstance(state, dict) or set(state) != _LEDGER_KEYS:
        raise ReplayStateError("scheduled_replay_ledger_invalid")
    if state["schema_version"] != LEDGER_SCHEMA or not _uint(
        state["updated_at_ms"]
    ):
        raise ReplayStateError("scheduled_replay_ledger_invalid")
    if not _uint(now_ms) or now_ms < state["updated_at_ms"]:
        raise ReplayStateError("scheduled_replay_ledger_invalid")
    entries = state["entries"]
    if not isinstance(entries, dict) or len(entries) > MAX_LEDGER_ENTRIES:
        raise ReplayStateError("scheduled_replay_ledger_capacity_exhausted")
    for invocation_id, entry in entries.items():
        _validate_entry(invocation_id, entry)


def armed_entry(invocation: DiscoveryInvocation) -> dict[str, Any]:
    """Create an ARMED record with no claimed terminal evidence."""

    item = rehydrate_discovery_invocation(invocation.to_dict())
    if item.mode != "scheduled":
        raise ReplayStateError("scheduled_invocation_required")
    return {
        "invocation": item.to_dict(),
        "status": "ARMED",
        "receipt": None,
        "window_expires_at_ms": item.expires_at_ms,
    }


def receipt_entry(receipt: DiscoveryReceipt) -> dict[str, Any]:
    """Create a terminal/retryable record from one strict receipt."""

    item = rehydrate_discovery_receipt(receipt.to_dict())
    if item.invocation.mode != "scheduled":
        raise ReplayStateError("scheduled_invocation_required")
    entry = {
        "invocation": item.invocation.to_dict(),
        "status": item.outcome,
        "receipt": item.to_dict(),
        "window_expires_at_ms": item.invocation.expires_at_ms,
    }
    _validate_entry(item.invocation.invocation_id, entry)
    return entry


def prune_expired_entries(state: dict[str, Any], *, now_ms: int) -> bool:
    """Prune only entries whose canonical scheduled window has expired."""

    expired = [
        invocation_id
        for invocation_id, entry in state["entries"].items()
        if now_ms > entry["window_expires_at_ms"]
    ]
    for invocation_id in expired:
        del state["entries"][invocation_id]
    return bool(expired)


def read_attempt_receipt(
    paths: ScheduledDiscoveryPaths,
) -> DiscoveryReceipt | None:
    """Read the fixed latest-attempt receipt through the strict boundary."""

    raw = _read_optional_json(
        paths.attempt_path,
        paths.runtime_root,
        MAX_RECEIPT_BYTES,
        "scheduled_discovery_attempt_invalid",
    )
    if raw is None:
        return None
    try:
        return rehydrate_discovery_receipt(raw)
    except (TypeError, ValueError) as error:
        raise ReplayStateError("scheduled_discovery_attempt_invalid") from error


def read_candidate_snapshot(
    paths: ScheduledDiscoveryPaths,
    *,
    now_ms: int,
    require_fresh: bool = True,
) -> ProviderCatalogCandidateSnapshot | None:
    """Read the fixed current candidate through the strict boundary."""

    raw = _read_optional_json(
        paths.candidate_path,
        paths.runtime_root,
        MAX_CANDIDATE_BYTES,
        "scheduled_discovery_candidate_invalid",
    )
    if raw is None:
        return None
    try:
        validation_now = now_ms
        if not require_fresh and type(raw.get("fresh_until_ms")) is int:
            validation_now = min(now_ms, raw["fresh_until_ms"])
        return rehydrate_candidate_snapshot(raw, now_ms=validation_now)
    except (TypeError, ValueError) as error:
        raise ReplayStateError("scheduled_discovery_candidate_invalid") from error


def _validate_entry(invocation_id: object, entry: object) -> None:
    if (
        not isinstance(invocation_id, str)
        or not isinstance(entry, dict)
        or set(entry) != _ENTRY_KEYS
        or entry["status"] not in _STATUSES
    ):
        raise ReplayStateError("scheduled_replay_entry_invalid")
    try:
        invocation = rehydrate_discovery_invocation(entry["invocation"])
    except (TypeError, ValueError) as error:
        raise ReplayStateError("scheduled_replay_entry_invalid") from error
    if (
        invocation.mode != "scheduled"
        or invocation.invocation_id != invocation_id
        or entry["window_expires_at_ms"] != invocation.expires_at_ms
    ):
        raise ReplayStateError("scheduled_replay_entry_invalid")
    _validate_entry_receipt(invocation, entry)


def _validate_entry_receipt(
    invocation: DiscoveryInvocation, entry: Mapping[str, Any]
) -> None:
    if entry["status"] == "ARMED":
        if entry["receipt"] is not None:
            raise ReplayStateError("scheduled_replay_entry_invalid")
        return
    try:
        receipt = rehydrate_discovery_receipt(entry["receipt"])
    except (TypeError, ValueError) as error:
        raise ReplayStateError("scheduled_replay_entry_invalid") from error
    if (
        receipt.invocation != invocation
        or receipt.outcome != entry["status"]
        or (receipt.outcome == "BLOCKED_PRECALL" and receipt.attempted)
        or (receipt.outcome != "BLOCKED_PRECALL" and not receipt.attempted)
    ):
        raise ReplayStateError("scheduled_replay_entry_invalid")


def _read_optional_json(
    path: Path, root: Path, limit: int, reason: str
) -> dict[str, Any] | None:
    if not os.path.lexists(path):
        return None
    try:
        before = os.lstat(path)
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_nlink != 1
            or before.st_size > limit
        ):
            raise ReplayStateError(reason)
        payload, cursor = _secure_read_exact(
            path, root, before, limit, reason
        )
        after = os.lstat(path)
        if (
            cursor != before.st_size
            or (before.st_dev, before.st_ino, before.st_size)
            != (after.st_dev, after.st_ino, after.st_size)
            or after.st_nlink != 1
        ):
            raise ReplayStateError(reason)
        value = json.loads(
            payload.decode("utf-8", errors="strict"),
            object_pairs_hook=_unique_object,
        )
    except (
        OSError,
        UnicodeError,
        json.JSONDecodeError,
        RecursionError,
        ValueError,
    ) as error:
        if isinstance(error, ReplayStateError):
            raise
        raise ReplayStateError(reason) from error
    if not isinstance(value, dict):
        raise ReplayStateError(reason)
    return value


def _secure_read_exact(
    path: Path,
    root: Path,
    expected: os.stat_result,
    limit: int,
    reason: str,
) -> tuple[bytes, int]:
    """Compose bounded descriptor-confined chunks from one stable identity."""

    chunks: list[bytes] = []
    cursor = 0
    while cursor < expected.st_size:
        chunk, next_cursor = secure_read_confined_bytes(
            path,
            allowed_root=root,
            offset=cursor,
            max_bytes=min(1024 * 1024, limit - cursor),
        )
        current = os.lstat(path)
        if (
            not chunk
            or next_cursor != cursor + len(chunk)
            or (current.st_dev, current.st_ino, current.st_size)
            != (expected.st_dev, expected.st_ino, expected.st_size)
            or current.st_nlink != 1
        ):
            raise ReplayStateError(reason)
        chunks.append(chunk)
        cursor = next_cursor
    return b"".join(chunks), cursor


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ReplayStateError("scheduled_discovery_duplicate_key")
        result[key] = value
    return result


def _uint(value: object) -> bool:
    return type(value) is int and value >= 0


__all__ = [
    "MAX_CANDIDATE_BYTES",
    "MAX_LEDGER_ENTRIES",
    "ReplayStateError",
    "ScheduledDiscoveryPaths",
    "armed_entry",
    "derive_scheduled_discovery_paths",
    "empty_replay_ledger",
    "load_replay_ledger",
    "prune_expired_entries",
    "read_attempt_receipt",
    "read_candidate_snapshot",
    "receipt_entry",
    "save_replay_ledger",
]
