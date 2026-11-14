"""Strict codec and atomic publication for idle schedule claim state."""

from __future__ import annotations

import hashlib
import json
import os
import secrets
import stat
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import BinaryIO, Callable

from modules.infrastructure.shared_utilities.runtime_artifact_safety import (
    validate_runtime_artifact_path,
)

STATE_SCHEMA = "idle_automation_schedule_claim_state.v1"
MAX_STATE_BYTES = 2 * 1024 * 1024
MAX_EXECUTION_RECORDS = 4096
MAX_ATTEMPTS = 3
MAX_LEASE_RECOVERIES = 1


class ScheduleStateError(ValueError):
    """The durable claim state could not be trusted."""


def _write_all(stream: BinaryIO, payload: bytes) -> None:
    if stream.write(payload) != len(payload):
        raise OSError("schedule_claim_state_write_incomplete")


@dataclass(frozen=True)
class ScheduleClaimOps:
    """Trusted low-level seams for deterministic offline durability tests."""

    writer: Callable[[BinaryIO, bytes], None] = _write_all
    fsync: Callable[[int], None] = os.fsync
    replacer: Callable[[Path, Path], None] = os.replace


def build_execution_id(
    schedule_id: str,
    routine: str,
    cadence: str,
    window_start: str,
    window_end: str,
) -> str:
    """Return the canonical digest for one immutable schedule window."""
    fields = [schedule_id, routine, cadence, window_start, window_end]
    if any(not isinstance(item, str) or not item for item in fields):
        raise ScheduleStateError("schedule_claim_window_text_invalid")
    canonical = json.dumps(
        fields, ensure_ascii=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def normalized_utc(value: datetime) -> datetime:
    """Normalize an aware or legacy-naive timestamp to UTC."""
    if not isinstance(value, datetime):
        raise ScheduleStateError("schedule_claim_time_invalid")
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def parse_time(value: object) -> datetime:
    """Parse a required ISO timestamp or fail closed."""
    if not isinstance(value, str) or not value:
        raise ScheduleStateError("schedule_claim_timestamp_invalid")
    try:
        return normalized_utc(datetime.fromisoformat(value.replace("Z", "+00:00")))
    except ValueError as error:
        raise ScheduleStateError("schedule_claim_timestamp_invalid") from error


def iso_time(value: datetime) -> str:
    """Serialize a normalized UTC timestamp."""
    return normalized_utc(value).isoformat()


def empty_state() -> dict:
    """Return a canonical empty state document."""
    return {
        "schema_version": STATE_SCHEMA,
        "updated_at": iso_time(datetime(1970, 1, 1, tzinfo=UTC)),
        "executions": {},
    }


def load_claim_state(
    path: Path, *, repo_root: Path, runtime_root: Path
) -> dict:
    """Read and validate state from the trusted fixed artifact path."""
    target = validate_runtime_artifact_path(
        path,
        repo_root=repo_root,
        allowed_root=runtime_root,
    )
    if not target.exists():
        return empty_state()
    metadata = os.lstat(target)
    if (
        not stat.S_ISREG(metadata.st_mode)
        or metadata.st_nlink != 1
        or metadata.st_size > MAX_STATE_BYTES
    ):
        raise ScheduleStateError("schedule_claim_state_file_invalid")
    try:
        state = json.loads(
            target.read_text(encoding="utf-8"),
            object_pairs_hook=_unique_object,
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ScheduleStateError("schedule_claim_state_malformed") from error
    validate_state(state)
    return state


def save_claim_state(
    state: dict,
    now: datetime,
    *,
    path: Path,
    runtime_root: Path,
    ops: ScheduleClaimOps,
) -> None:
    """Atomically publish validated state or restore exact prior bytes."""
    state["updated_at"] = iso_time(now)
    validate_state(state)
    payload = (
        json.dumps(state, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("utf-8")
    if len(payload) > MAX_STATE_BYTES:
        raise ScheduleStateError("schedule_claim_state_capacity_exhausted")
    prior = path.read_bytes() if path.exists() else None
    descriptor, raw_path = tempfile.mkstemp(
        prefix=".schedule-claims.", suffix=".tmp", dir=runtime_root
    )
    temporary: Path | None = Path(raw_path)
    try:
        owned_descriptor = descriptor
        descriptor = -1
        _write_temporary(owned_descriptor, payload, ops)
        try:
            ops.replacer(temporary, path)
            temporary = None
            if path.read_bytes() != payload:
                raise OSError("schedule_claim_state_post_replace_mismatch")
        except Exception:
            _restore_lkg(runtime_root, path, prior)
            raise
        _fsync_parent(runtime_root)
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _write_temporary(
    descriptor: int,
    payload: bytes,
    ops: ScheduleClaimOps,
) -> None:
    owned_descriptor = descriptor
    try:
        if hasattr(os, "fchmod"):
            os.fchmod(owned_descriptor, 0o600)
        with os.fdopen(owned_descriptor, "w+b", closefd=True) as stream:
            owned_descriptor = -1
            ops.writer(stream, payload)
            stream.flush()
            if os.fstat(stream.fileno()).st_size != len(payload):
                raise OSError("schedule_claim_state_size_mismatch")
            ops.fsync(stream.fileno())
            stream.seek(0)
            if stream.read(len(payload) + 1) != payload:
                raise OSError("schedule_claim_state_content_mismatch")
    finally:
        if owned_descriptor >= 0:
            os.close(owned_descriptor)


def validate_state(state: object) -> None:
    """Validate exact top-level and record schemas."""
    if not isinstance(state, dict) or set(state) != {
        "schema_version",
        "updated_at",
        "executions",
    }:
        raise ScheduleStateError("schedule_claim_state_shape_invalid")
    if state["schema_version"] != STATE_SCHEMA:
        raise ScheduleStateError("schedule_claim_state_schema_invalid")
    parse_time(state["updated_at"])
    records = state["executions"]
    if not isinstance(records, dict) or len(records) > MAX_EXECUTION_RECORDS:
        raise ScheduleStateError("schedule_claim_state_records_invalid")
    for execution_id, record in records.items():
        _validate_record(execution_id, record)


def _validate_record(execution_id: str, record: object) -> None:
    required = _record_keys()
    if not isinstance(record, dict) or set(record) != required:
        raise ScheduleStateError("schedule_claim_record_shape_invalid")
    text_fields = (
        "execution_id",
        "schedule_id",
        "routine",
        "cadence",
        "window_start",
        "window_end",
        "status",
    )
    if any(
        not isinstance(record[field], str) or not record[field]
        for field in text_fields
    ):
        raise ScheduleStateError("schedule_claim_record_text_invalid")
    _validate_record_identity(execution_id, record)
    if record["status"] not in {
        "claimed",
        "retry_wait",
        "completed",
        "exhausted",
    }:
        raise ScheduleStateError("schedule_claim_record_status_invalid")
    if type(record["attempt"]) is not int or not 1 <= record["attempt"] <= MAX_ATTEMPTS:
        raise ScheduleStateError("schedule_claim_record_attempt_invalid")
    if (
        type(record["lease_recoveries"]) is not int
        or not 0 <= record["lease_recoveries"] <= MAX_LEASE_RECOVERIES
    ):
        raise ScheduleStateError("schedule_claim_record_recovery_invalid")
    _validate_status_fields(record)


def _validate_record_identity(execution_id: str, record: dict) -> None:
    if record["execution_id"] != execution_id:
        raise ScheduleStateError("schedule_claim_record_id_invalid")
    expected = build_execution_id(
        record["schedule_id"],
        record["routine"],
        record["cadence"],
        record["window_start"],
        record["window_end"],
    )
    if not secrets.compare_digest(execution_id, expected):
        raise ScheduleStateError("schedule_claim_record_id_invalid")
    if parse_time(record["window_start"]) >= parse_time(record["window_end"]):
        raise ScheduleStateError("schedule_claim_record_window_invalid")
    claimed_at = record["claimed_at"]
    if claimed_at is not None and not (
        parse_time(record["window_start"])
        <= parse_time(claimed_at)
        < parse_time(record["window_end"])
    ):
        raise ScheduleStateError("schedule_claim_record_claim_time_invalid")


def _validate_status_fields(record: dict) -> None:
    nullable = (
        "token",
        "claimant_id",
        "claimed_at",
        "lease_expires_at",
        "next_attempt_at",
        "completed_at",
        "terminal_at",
        "last_outcome",
    )
    values = (record[key] for key in nullable)
    if any(value is not None and not isinstance(value, str) for value in values):
        raise ScheduleStateError("schedule_claim_record_optional_invalid")
    status = record["status"]
    if status == "claimed":
        _validate_claimed(record)
    elif status == "retry_wait":
        _validate_retry(record)
    elif status == "completed":
        _validate_completed(record)
    else:
        _validate_exhausted(record)


def _validate_claimed(record: dict) -> None:
    owner_fields = ("token", "claimant_id", "claimed_at", "lease_expires_at")
    if not all(record[key] for key in owner_fields):
        raise ScheduleStateError("schedule_claim_record_lease_invalid")
    if not _valid_opaque(record["token"]) or not _valid_opaque(record["claimant_id"]):
        raise ScheduleStateError("schedule_claim_record_owner_invalid")
    claimed_at = parse_time(record["claimed_at"])
    if parse_time(record["lease_expires_at"]) <= claimed_at:
        raise ScheduleStateError("schedule_claim_record_lease_order_invalid")


def _validate_retry(record: dict) -> None:
    if (
        _has_owner(record)
        or not record["claimed_at"]
        or not record["next_attempt_at"]
    ):
        raise ScheduleStateError("schedule_claim_record_retry_invalid")
    if parse_time(record["next_attempt_at"]) <= parse_time(record["claimed_at"]):
        raise ScheduleStateError("schedule_claim_record_retry_order_invalid")


def _validate_completed(record: dict) -> None:
    if (
        not record["completed_at"]
        or not record["terminal_at"]
        or not record["claimed_at"]
        or _has_owner(record)
        or record["next_attempt_at"] is not None
    ):
        raise ScheduleStateError("schedule_claim_record_completion_invalid")
    claimed_at = parse_time(record["claimed_at"])
    if parse_time(record["completed_at"]) < claimed_at:
        raise ScheduleStateError("schedule_claim_record_completion_order_invalid")
    if parse_time(record["terminal_at"]) < claimed_at:
        raise ScheduleStateError("schedule_claim_record_terminal_order_invalid")


def _validate_exhausted(record: dict) -> None:
    if (
        _has_owner(record)
        or record["next_attempt_at"] is not None
        or not record["claimed_at"]
        or not record["terminal_at"]
    ):
        raise ScheduleStateError("schedule_claim_record_exhausted_invalid")
    if parse_time(record["terminal_at"]) < parse_time(record["claimed_at"]):
        raise ScheduleStateError("schedule_claim_record_terminal_order_invalid")


def _record_keys() -> set[str]:
    return {
        "execution_id",
        "schedule_id",
        "routine",
        "cadence",
        "window_start",
        "window_end",
        "status",
        "attempt",
        "lease_recoveries",
        "token",
        "claimant_id",
        "claimed_at",
        "lease_expires_at",
        "next_attempt_at",
        "completed_at",
        "terminal_at",
        "last_outcome",
    }


def _valid_opaque(value: object) -> bool:
    return isinstance(value, str) and 0 < len(value) <= 256


def _has_owner(record: dict) -> bool:
    return any(
        record[key] is not None
        for key in ("token", "claimant_id", "lease_expires_at")
    )


def _unique_object(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ScheduleStateError("schedule_claim_state_duplicate_key")
        result[key] = value
    return result


def _restore_lkg(root: Path, target: Path, prior: bytes | None) -> None:
    if prior is None:
        target.unlink(missing_ok=True)
        _fsync_parent(root)
        return
    descriptor, raw_path = tempfile.mkstemp(
        prefix=".schedule-claims.restore.", suffix=".tmp", dir=root
    )
    temporary = Path(raw_path)
    try:
        with os.fdopen(descriptor, "w+b", closefd=True) as stream:
            descriptor = -1
            _write_all(stream, prior)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, target)
        _fsync_parent(root)
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        temporary.unlink(missing_ok=True)


def _fsync_parent(parent: Path) -> None:
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    try:
        descriptor = os.open(parent, flags)
    except (OSError, NotImplementedError):
        return
    try:
        os.fsync(descriptor)
    except (OSError, NotImplementedError):
        pass
    finally:
        os.close(descriptor)


__all__ = [
    "MAX_ATTEMPTS",
    "MAX_EXECUTION_RECORDS",
    "MAX_LEASE_RECOVERIES",
    "ScheduleClaimOps",
    "ScheduleStateError",
    "build_execution_id",
    "empty_state",
    "iso_time",
    "load_claim_state",
    "normalized_utc",
    "parse_time",
    "save_claim_state",
]
