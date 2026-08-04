"""PatternMemory sink adapter for verified RedDog resident-queue outcomes.

Slice: REDDOG_MAIN_RESIDENT_QUEUE_PATTERN_MEMORY_SINK_BRIDGE_PHASE1

This adapter stages records outside normal recall, then requires a one-use,
process-local activation capability derived from exact ACTIVE signed authority.
The legacy direct-store method fails closed.

The sink requires an explicit SQLite database path outside the repository
checkout. It never creates a default PatternMemory client, executes commands,
enqueues OpenClaw, dispatches Hermes, settles rewards, merges PRs, or re-indexes
HoloIndex.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

from modules.communication.moltbot_bridge.src.foundup_memex_pattern_memory_activation import (
    consume_pattern_memory_activation,
)
from modules.infrastructure.wre_core.src.pattern_memory import PatternMemory, SkillOutcome


REDDOG_VERIFIED_PATTERN_MEMORY_SINK_READY = "REDDOG_VERIFIED_PATTERN_MEMORY_SINK_READY"

SECRET_MARKERS = (
    "authorization:",
    "bearer ",
    "api_key",
    "apikey",
    "private_key",
    "begin private key",
    "secret=",
    "token=",
    "password=",
)


class PatternMemorySinkConfigurationError(ValueError):
    """Raised when the sink cannot be constructed safely."""


def _is_inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)


def _digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _contains_secret(value: Any) -> bool:
    text = _canonical_json(value).lower()
    return any(marker in text for marker in SECRET_MARKERS)


def _record_id(record: Mapping[str, Any]) -> str:
    return "reddog_verified_outcome_" + _digest(record).removeprefix("sha256:")[:16]


def reddog_verified_pattern_memory_record_id(record: Mapping[str, Any]) -> str:
    """Return the canonical record identifier used by the PatternMemory row."""

    return _record_id(record)


def reddog_verified_pattern_memory_record_digest(record: Mapping[str, Any]) -> str:
    """Return the canonical digest used by admission receipts."""

    return _digest(record)


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _validated_record(record: Mapping[str, Any]) -> Dict[str, Any]:
    payload = dict(record)
    if payload.get("record_type") != "reddog_verified_recursive_improvement_outcome":
        raise ValueError("unsupported_verified_outcome_record_type")
    if _contains_secret(payload):
        raise ValueError("secret_in_verified_outcome_record")
    return payload


def _ensure_staging_table(memory: PatternMemory) -> None:
    memory.conn.execute(
        "CREATE TABLE IF NOT EXISTS reddog_verified_outcome_staging ("
        "record_id TEXT PRIMARY KEY, payload TEXT NOT NULL, agent TEXT NOT NULL, "
        "staged_at TEXT NOT NULL)"
    )
    memory.conn.commit()


def _stored_payload(row: Any) -> Optional[Dict[str, Any]]:
    if row is None:
        return None
    try:
        payload = json.loads(row["output_result"])
    except (json.JSONDecodeError, TypeError):
        return None
    return payload if isinstance(payload, dict) else None


@dataclass(frozen=True)
class RedDogVerifiedPatternMemorySink:
    """Store verified RedDog outcomes in an explicit PatternMemory database."""

    db_path: Path
    agent: str = "reddog"

    @property
    def status(self) -> str:
        return REDDOG_VERIFIED_PATTERN_MEMORY_SINK_READY

    def store_verified_outcome(self, record: Mapping[str, Any]) -> str:
        """Reject direct activation; signed authority capability is mandatory."""

        _validated_record(record)
        raise ValueError("verified_outcome_activation_capability_required")

    def stage_verified_outcome(self, record: Mapping[str, Any]) -> str:
        """Persist an outcome outside normal recall until authority is active."""

        payload = _validated_record(record)
        execution_id = _record_id(payload)
        memory = PatternMemory(db_path=self.db_path)
        try:
            _ensure_staging_table(memory)
            active = memory.conn.execute(
                "SELECT output_result, agent, success FROM skill_outcomes "
                "WHERE execution_id = ? LIMIT 1",
                (execution_id,),
            ).fetchone()
            if active is not None:
                if (
                    active["agent"] != self.agent
                    or active["success"] != 1
                    or _stored_payload(active) != payload
                ):
                    raise ValueError("verified_outcome_existing_record_conflict")
                return execution_id
            staged = memory.conn.execute(
                "SELECT payload, agent FROM reddog_verified_outcome_staging "
                "WHERE record_id = ? LIMIT 1",
                (execution_id,),
            ).fetchone()
            canonical = _canonical_json(payload)
            if staged is not None:
                if staged["payload"] != canonical or staged["agent"] != self.agent:
                    raise ValueError("verified_outcome_staged_record_conflict")
                return execution_id
            memory.conn.execute(
                "INSERT INTO reddog_verified_outcome_staging "
                "(record_id, payload, agent, staged_at) VALUES (?, ?, ?, ?)",
                (execution_id, canonical, self.agent, _utc_now()),
            )
            memory.conn.commit()
            return execution_id
        finally:
            memory.close()

    def activate_verified_outcome(
        self,
        record_id: str,
        activation_capability: Any,
        record: Mapping[str, Any],
    ) -> str:
        """Atomically make one exact staged outcome visible to PatternMemory."""

        candidate = str(record_id or "").strip()
        if not candidate:
            raise ValueError("verified_outcome_record_id_missing")
        payload = _validated_record(record)
        if _record_id(payload) != candidate or not consume_pattern_memory_activation(
            activation_capability,
            record_id=candidate,
            record=payload,
        ):
            raise ValueError("verified_outcome_activation_capability_invalid")
        memory = PatternMemory(db_path=self.db_path)
        try:
            _ensure_staging_table(memory)
            return self._activate(memory, candidate)
        finally:
            memory.close()

    def _activate(self, memory: PatternMemory, record_id: str) -> str:
        memory.conn.execute("BEGIN IMMEDIATE")
        try:
            staged = memory.conn.execute(
                "SELECT payload, agent, staged_at FROM reddog_verified_outcome_staging "
                "WHERE record_id = ? LIMIT 1",
                (record_id,),
            ).fetchone()
            active = memory.conn.execute(
                "SELECT output_result, agent, success FROM skill_outcomes "
                "WHERE execution_id = ? LIMIT 1",
                (record_id,),
            ).fetchone()
            if staged is None:
                active_payload = _stored_payload(active)
                if (
                    active is None
                    or active["agent"] != self.agent
                    or active["success"] != 1
                    or active_payload is None
                    or _record_id(active_payload) != record_id
                ):
                    raise ValueError("verified_outcome_stage_missing")
                memory.conn.commit()
                return record_id
            payload = _validated_record(json.loads(staged["payload"]))
            if _record_id(payload) != record_id or staged["agent"] != self.agent:
                raise ValueError("verified_outcome_staged_record_invalid")
            if active is not None:
                if (
                    active["agent"] != self.agent
                    or active["success"] != 1
                    or _stored_payload(active) != payload
                ):
                    raise ValueError("verified_outcome_existing_record_conflict")
            else:
                self._insert_active(memory, record_id, payload, staged["staged_at"])
            memory.conn.execute(
                "DELETE FROM reddog_verified_outcome_staging WHERE record_id = ?",
                (record_id,),
            )
            memory.conn.commit()
            return record_id
        except Exception:
            memory.conn.rollback()
            raise

    def _insert_active(
        self, memory: PatternMemory, record_id: str, payload: Mapping[str, Any], timestamp: str
    ) -> None:
        outcome = SkillOutcome(
            execution_id=record_id,
            skill_name=str(payload.get("slice_name") or "reddog_verified_outcome"),
            agent=self.agent,
            timestamp=timestamp,
            input_context=_canonical_json({
                key: payload.get(key)
                for key in (
                    "work_order_id",
                    "gate_id",
                    "ratchet_id",
                    "verifier_receipt_id",
                )
            }),
            output_result=_canonical_json(payload),
            success=True,
            pattern_fidelity=1.0,
            outcome_quality=1.0,
            execution_time_ms=0,
            step_count=0,
            notes="RedDog verified recursive improvement outcome admitted after held-out gate.",
        )
        memory.conn.execute(
            "INSERT INTO skill_outcomes (execution_id, skill_name, agent, timestamp, "
            "input_context, output_result, success, pattern_fidelity, outcome_quality, "
            "execution_time_ms, step_count, failed_at_step, notes) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                outcome.execution_id, outcome.skill_name, outcome.agent, outcome.timestamp,
                outcome.input_context, outcome.output_result, 1, outcome.pattern_fidelity,
                outcome.outcome_quality, outcome.execution_time_ms, outcome.step_count,
                outcome.failed_at_step, outcome.notes,
            ),
        )

    def load_verified_outcome(self, record_id: str) -> Optional[Dict[str, Any]]:
        """Read back one canonical RedDog outcome through PatternMemory schema."""

        if not self.db_path.is_file() or not str(record_id or "").strip():
            return None
        memory = PatternMemory(db_path=self.db_path)
        try:
            cursor = memory.conn.cursor()
            cursor.execute(
                "SELECT execution_id, agent, success, output_result "
                "FROM skill_outcomes WHERE execution_id = ? LIMIT 1",
                (record_id,),
            )
            row = cursor.fetchone()
        finally:
            memory.close()
        if row is None or row["agent"] != self.agent or row["success"] != 1:
            return None
        try:
            payload = json.loads(row["output_result"])
        except (json.JSONDecodeError, TypeError):
            return None
        if not isinstance(payload, dict) or _record_id(payload) != record_id:
            return None
        if payload.get("record_type") != "reddog_verified_recursive_improvement_outcome":
            return None
        return payload


def build_reddog_verified_pattern_memory_sink(
    *,
    repo_root: Path | str,
    db_path: Path | str | None,
    agent: str = "reddog",
) -> Optional[RedDogVerifiedPatternMemorySink]:
    """Build an explicit outside-repo PatternMemory sink, or None if disabled."""

    if not db_path:
        return None
    root = Path(repo_root).resolve()
    path = Path(db_path)
    if not path.is_absolute():
        path = (root / path).resolve()
    else:
        path = path.resolve()
    if _is_inside(path, root):
        raise PatternMemorySinkConfigurationError("pattern_memory_db_path_inside_repo")
    return RedDogVerifiedPatternMemorySink(db_path=path, agent=agent)


__all__ = [
    "PatternMemorySinkConfigurationError",
    "REDDOG_VERIFIED_PATTERN_MEMORY_SINK_READY",
    "RedDogVerifiedPatternMemorySink",
    "build_reddog_verified_pattern_memory_sink",
    "reddog_verified_pattern_memory_record_digest",
    "reddog_verified_pattern_memory_record_id",
]
