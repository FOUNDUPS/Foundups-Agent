"""PatternMemory sink adapter for verified RedDog resident-queue outcomes.

Slice: REDDOG_MAIN_RESIDENT_QUEUE_PATTERN_MEMORY_SINK_BRIDGE_PHASE1

This adapter implements the `store_verified_outcome(record) -> record_id`
protocol required by the queue-authorized PatternMemory admission guard. It
does not decide whether an outcome is eligible. The resident queue gate chain
must already have accepted the held-out regression and PatternMemory admission
stage before this sink is called.

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
from typing import Any, Mapping, Optional

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


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass(frozen=True)
class RedDogVerifiedPatternMemorySink:
    """Store verified RedDog outcomes in an explicit PatternMemory database."""

    db_path: Path
    agent: str = "reddog"

    @property
    def status(self) -> str:
        return REDDOG_VERIFIED_PATTERN_MEMORY_SINK_READY

    def store_verified_outcome(self, record: Mapping[str, Any]) -> str:
        payload = dict(record)
        if payload.get("record_type") != "reddog_verified_recursive_improvement_outcome":
            raise ValueError("unsupported_verified_outcome_record_type")
        if _contains_secret(payload):
            raise ValueError("secret_in_verified_outcome_record")

        execution_id = _record_id(payload)
        memory = PatternMemory(db_path=self.db_path)
        try:
            cursor = memory.conn.cursor()
            cursor.execute(
                "SELECT execution_id FROM skill_outcomes WHERE execution_id = ? LIMIT 1",
                (execution_id,),
            )
            if cursor.fetchone() is not None:
                return execution_id

            outcome = SkillOutcome(
                execution_id=execution_id,
                skill_name=str(payload.get("slice_name") or "reddog_verified_outcome"),
                agent=self.agent,
                timestamp=_utc_now(),
                input_context=_canonical_json(
                    {
                        "work_order_id": payload.get("work_order_id"),
                        "gate_id": payload.get("gate_id"),
                        "ratchet_id": payload.get("ratchet_id"),
                        "verifier_receipt_id": payload.get("verifier_receipt_id"),
                    }
                ),
                output_result=_canonical_json(payload),
                success=True,
                pattern_fidelity=1.0,
                outcome_quality=1.0,
                execution_time_ms=0,
                step_count=0,
                notes="RedDog verified recursive improvement outcome admitted after held-out gate.",
            )
            memory.store_outcome(outcome)
            return execution_id
        finally:
            memory.close()


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
]
