"""Durable one-owner state machine for canonical idle schedule windows."""

from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable

from modules.infrastructure.idle_automation.src.schedule_claim_codec import (
    MAX_ATTEMPTS,
    MAX_EXECUTION_RECORDS,
    MAX_LEASE_RECOVERIES,
    ScheduleClaimOps,
    ScheduleStateError,
    build_execution_id,
    iso_time,
    load_claim_state,
    normalized_utc,
    parse_time,
    save_claim_state,
)
from modules.infrastructure.shared_utilities.runtime_artifact_safety import (
    runtime_operation_lock,
    validate_runtime_artifact_path,
    validate_runtime_root_path,
)

LEASE_SECONDS = 3900
RETRY_BACKOFF_SECONDS = (60, 300)
TERMINAL_RETENTION_DAYS = 35
KNOWN_OUTCOMES = frozenset(
    {"success", "routine_failed", "dispatch_error", "finalize_error"}
)


@dataclass(frozen=True)
class ScheduleWindow:
    """Immutable canonical identity of one schedule cadence window."""

    schedule_id: str
    routine: str
    cadence: str
    window_start: str
    window_end: str
    execution_id: str


@dataclass(frozen=True)
class ScheduleClaim:
    """A durable one-owner lease returned only after publication."""

    schedule_id: str
    routine: str
    cadence: str
    window_start: str
    window_end: str
    execution_id: str
    token: str
    claimant_id: str
    lease_expires_at: str
    attempt: int


class ScheduleClaimStore:
    """Serialize one-window claims and exact-token finalization under one lock."""

    def __init__(
        self,
        *,
        repo_root: Path | str,
        runtime_root: Path | str,
        ops: ScheduleClaimOps | None = None,
        token_factory: Callable[[], str] | None = None,
        claimant_id: str | None = None,
    ) -> None:
        self.repo_root = Path(repo_root).resolve()
        root = validate_runtime_root_path(runtime_root, repo_root=self.repo_root)
        root.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.runtime_root = validate_runtime_root_path(
            root, repo_root=self.repo_root
        )
        self.state_path = validate_runtime_artifact_path(
            self.runtime_root / "schedule_claim_state.json",
            repo_root=self.repo_root,
            allowed_root=self.runtime_root,
        )
        self.ops = ops or ScheduleClaimOps()
        self.token_factory = token_factory or (lambda: secrets.token_urlsafe(24))
        self.claimant_id = claimant_id or f"worker-{secrets.token_hex(12)}"
        if not _valid_opaque(self.claimant_id):
            raise ScheduleStateError("schedule_claim_claimant_invalid")

    def claim_window(
        self, window: ScheduleWindow, *, now: datetime
    ) -> ScheduleClaim | None:
        """Durably claim one canonical window immediately before dispatch."""
        _validate_window(window)
        current = normalized_utc(now)
        if not parse_time(window.window_start) <= current < parse_time(
            window.window_end
        ):
            return None
        with runtime_operation_lock(self.state_path):
            state = self._load_state()
            changed = _prune_terminal_records(state, current)
            claim, record_changed = self._claim_window(state, window, current)
            if changed or record_changed:
                self._save_state(state, current)
            return claim

    def finalize(
        self,
        token: str,
        *,
        success: bool,
        outcome_code: str,
        now: datetime,
    ) -> bool:
        """Finalize the current exact token, including expired-unreclaimed."""
        if not _valid_opaque(token) or type(success) is not bool:
            return False
        current = normalized_utc(now)
        with runtime_operation_lock(self.state_path):
            state = self._load_state()
            record = _record_for_token(state, token)
            if record is None:
                return False
            _apply_finalization(record, success, outcome_code, current)
            self._save_state(state, current)
            return True

    def _claim_window(
        self,
        state: dict,
        window: ScheduleWindow,
        now: datetime,
    ) -> tuple[ScheduleClaim | None, bool]:
        records = state["executions"]
        record = records.get(window.execution_id)
        if record is None:
            if len(records) >= MAX_EXECUTION_RECORDS:
                raise ScheduleStateError(
                    "schedule_claim_state_capacity_exhausted"
                )
            record = _new_record(window)
            records[window.execution_id] = record
        else:
            _validate_record_matches_window(record, window)
            eligible, changed = _prepare_existing_record(record, now)
            if not eligible:
                return None, changed
        token = self.token_factory()
        if not _valid_opaque(token):
            raise ScheduleStateError("schedule_claim_token_invalid")
        if _record_for_token(state, token) is not None:
            raise ScheduleStateError("schedule_claim_token_collision")
        _apply_claim(record, token, self.claimant_id, now)
        return _claim_from_record(record), True

    def _load_state(self) -> dict:
        return load_claim_state(
            self.state_path,
            repo_root=self.repo_root,
            runtime_root=self.runtime_root,
        )

    def _save_state(self, state: dict, now: datetime) -> None:
        save_claim_state(
            state,
            now,
            path=self.state_path,
            runtime_root=self.runtime_root,
            ops=self.ops,
        )


def _new_record(window: ScheduleWindow) -> dict:
    return {
        "execution_id": window.execution_id,
        "schedule_id": window.schedule_id,
        "routine": window.routine,
        "cadence": window.cadence,
        "window_start": window.window_start,
        "window_end": window.window_end,
        "status": "new",
        "attempt": 0,
        "lease_recoveries": 0,
        "token": None,
        "claimant_id": None,
        "claimed_at": None,
        "lease_expires_at": None,
        "next_attempt_at": None,
        "completed_at": None,
        "terminal_at": None,
        "last_outcome": None,
    }


def _apply_claim(
    record: dict, token: str, claimant_id: str, now: datetime
) -> None:
    record["attempt"] += 1
    record["status"] = "claimed"
    record["token"] = token
    record["claimant_id"] = claimant_id
    record["claimed_at"] = iso_time(now)
    record["lease_expires_at"] = iso_time(
        now + timedelta(seconds=LEASE_SECONDS)
    )
    record["next_attempt_at"] = None


def _prepare_existing_record(record: dict, now: datetime) -> tuple[bool, bool]:
    status = record["status"]
    if status in {"completed", "exhausted"}:
        return False, False
    if status == "claimed":
        if parse_time(record["lease_expires_at"]) > now:
            return False, False
        if (
            record["lease_recoveries"] >= MAX_LEASE_RECOVERIES
            or record["attempt"] >= MAX_ATTEMPTS
        ):
            _mark_exhausted(record, now)
            return False, True
        record["lease_recoveries"] += 1
        return True, False
    if status == "retry_wait":
        if parse_time(record["next_attempt_at"]) > now:
            return False, False
        if record["attempt"] >= MAX_ATTEMPTS:
            _mark_exhausted(record, now)
            return False, True
        return True, False
    raise ScheduleStateError("schedule_claim_state_status_invalid")


def _apply_finalization(
    record: dict, success: bool, outcome_code: str, now: datetime
) -> None:
    _clear_owner(record)
    record["last_outcome"] = _safe_outcome(outcome_code)
    if success:
        record["status"] = "completed"
        record["completed_at"] = iso_time(now)
        record["terminal_at"] = iso_time(now)
        record["next_attempt_at"] = None
    elif record["attempt"] >= MAX_ATTEMPTS:
        _mark_exhausted(record, now)
    else:
        delay = RETRY_BACKOFF_SECONDS[record["attempt"] - 1]
        record["status"] = "retry_wait"
        record["next_attempt_at"] = iso_time(
            now + timedelta(seconds=delay)
        )


def _mark_exhausted(record: dict, now: datetime) -> None:
    record["status"] = "exhausted"
    _clear_owner(record)
    record["next_attempt_at"] = None
    record["terminal_at"] = iso_time(now)


def _clear_owner(record: dict) -> None:
    for key in ("token", "claimant_id", "lease_expires_at"):
        record[key] = None


def _claim_from_record(record: dict) -> ScheduleClaim:
    return ScheduleClaim(
        schedule_id=record["schedule_id"],
        routine=record["routine"],
        cadence=record["cadence"],
        window_start=record["window_start"],
        window_end=record["window_end"],
        execution_id=record["execution_id"],
        token=record["token"],
        claimant_id=record["claimant_id"],
        lease_expires_at=record["lease_expires_at"],
        attempt=record["attempt"],
    )


def _record_for_token(state: dict, token: str) -> dict | None:
    matches = [
        record
        for record in state["executions"].values()
        if record["status"] == "claimed" and record["token"] == token
    ]
    if len(matches) > 1:
        raise ScheduleStateError("schedule_claim_token_not_unique")
    return matches[0] if matches else None


def _validate_window(window: ScheduleWindow) -> None:
    if not isinstance(window, ScheduleWindow):
        raise ScheduleStateError("schedule_claim_window_type_invalid")
    start, end = parse_time(window.window_start), parse_time(window.window_end)
    if start >= end:
        raise ScheduleStateError("schedule_claim_window_range_invalid")
    expected = build_execution_id(
        window.schedule_id,
        window.routine,
        window.cadence,
        window.window_start,
        window.window_end,
    )
    if not secrets.compare_digest(window.execution_id, expected):
        raise ScheduleStateError("schedule_claim_window_id_invalid")


def _validate_record_matches_window(
    record: dict, window: ScheduleWindow
) -> None:
    fields = (
        "execution_id",
        "schedule_id",
        "routine",
        "cadence",
        "window_start",
        "window_end",
    )
    if any(record[field] != getattr(window, field) for field in fields):
        raise ScheduleStateError("schedule_claim_window_record_mismatch")


def _prune_terminal_records(state: dict, now: datetime) -> bool:
    cutoff = now - timedelta(days=TERMINAL_RETENTION_DAYS)
    expired = [
        execution_id
        for execution_id, record in state["executions"].items()
        if (
            record["terminal_at"] is not None
            and parse_time(record["terminal_at"]) < cutoff
        )
        or (
            record["terminal_at"] is None
            and parse_time(record["window_end"]) < cutoff
        )
    ]
    for execution_id in expired:
        del state["executions"][execution_id]
    return bool(expired)


def _safe_outcome(value: object) -> str:
    if isinstance(value, str) and value in KNOWN_OUTCOMES:
        return value
    digest = hashlib.sha256(str(value).encode("utf-8")).hexdigest()[:24]
    return f"digest:{digest}"


def _valid_opaque(value: object) -> bool:
    return isinstance(value, str) and 0 < len(value) <= 256


__all__ = [
    "LEASE_SECONDS",
    "MAX_ATTEMPTS",
    "RETRY_BACKOFF_SECONDS",
    "ScheduleClaim",
    "ScheduleClaimOps",
    "ScheduleClaimStore",
    "ScheduleStateError",
    "ScheduleWindow",
    "build_execution_id",
]
