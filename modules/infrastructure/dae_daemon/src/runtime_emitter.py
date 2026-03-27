"""Lightweight structured runtime event emitter.

Emits compact structured events for troubleshooting and tuning of
active OpenClaw runtime paths.  Follows the ``record_advisor_event()``
pattern (telemetry.py): best-effort JSONL append, no daemon dependency,
no SQLite, no background threads.

Design separation:
    - **Breadcrumbs** = lineage / continuity / provenance  (agent_db)
    - **Runtime events** = duration / status / failure analysis  (this module)

WSP Compliance:
    WSP 91: DAEMON Observability Protocol
    WSP 72: No cross-module deps (stdlib + pathlib only)
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Default emitter output directory
_DEFAULT_EVENTS_DIR = Path(__file__).resolve().parents[2] / "reports"

# Module-level singleton path (overridable for tests)
_events_dir: Path = _DEFAULT_EVENTS_DIR
_events_filename: str = "runtime_events.jsonl"


def _utc_iso() -> str:
    return datetime.now(UTC).isoformat()


@dataclass
class RuntimeEvent:
    """Compact structured event for runtime troubleshooting.

    Fields:
        surface:              Which runtime surface emitted (e.g. "training_adapter",
                              "run_task", "wsp_orchestrator", "idle_handoff").
        event_type:           What happened (e.g. "training_batch", "worker_dispatch",
                              "startup_task", "idle_trigger").
        status:               "started", "success", or "failure".
        duration_ms:          Wall-clock milliseconds (0 for "started" events).
        continuity_id:        From ContinuityContext if available, else None.
        parent_continuity_id: Parent lineage if available.
        task_id:              AgentDB task_id or execution_id if relevant.
        error:                Error message on failure, else None.
        details:              Small dict with surface-specific context (keep compact).
        timestamp:            ISO-8601 UTC, auto-filled.
    """

    surface: str
    event_type: str
    status: str  # "started" | "success" | "failure"
    duration_ms: int = 0
    continuity_id: Optional[str] = None
    parent_continuity_id: Optional[str] = None
    task_id: Optional[str] = None
    error: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=_utc_iso)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        # Strip None values for compact JSONL
        return {k: v for k, v in d.items() if v is not None}


def emit(event: RuntimeEvent) -> None:
    """Append a RuntimeEvent to the JSONL file (best-effort, never raises)."""
    try:
        target_dir = _events_dir
        target_dir.mkdir(parents=True, exist_ok=True)
        path = target_dir / _events_filename
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event.to_dict(), ensure_ascii=False, default=str) + "\n")
    except Exception as exc:
        logger.debug("[RUNTIME-EMITTER] Failed to write event: %s", exc)


def emit_start(
    surface: str,
    event_type: str,
    *,
    continuity_id: Optional[str] = None,
    parent_continuity_id: Optional[str] = None,
    task_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
) -> float:
    """Emit a 'started' event and return the monotonic start time for duration tracking."""
    emit(RuntimeEvent(
        surface=surface,
        event_type=event_type,
        status="started",
        continuity_id=continuity_id,
        parent_continuity_id=parent_continuity_id,
        task_id=task_id,
        details=details or {},
    ))
    return time.monotonic()


def emit_success(
    surface: str,
    event_type: str,
    start_time: float,
    *,
    continuity_id: Optional[str] = None,
    parent_continuity_id: Optional[str] = None,
    task_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
) -> None:
    """Emit a 'success' event with computed duration."""
    duration_ms = int((time.monotonic() - start_time) * 1000)
    emit(RuntimeEvent(
        surface=surface,
        event_type=event_type,
        status="success",
        duration_ms=duration_ms,
        continuity_id=continuity_id,
        parent_continuity_id=parent_continuity_id,
        task_id=task_id,
        details=details or {},
    ))


def emit_failure(
    surface: str,
    event_type: str,
    start_time: float,
    error: str,
    *,
    continuity_id: Optional[str] = None,
    parent_continuity_id: Optional[str] = None,
    task_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
) -> None:
    """Emit a 'failure' event with computed duration and error message."""
    duration_ms = int((time.monotonic() - start_time) * 1000)
    emit(RuntimeEvent(
        surface=surface,
        event_type=event_type,
        status="failure",
        duration_ms=duration_ms,
        continuity_id=continuity_id,
        parent_continuity_id=parent_continuity_id,
        task_id=task_id,
        error=error[:500] if error else None,
        details=details or {},
    ))


def set_events_dir(path: Path) -> None:
    """Override the events directory (for testing)."""
    global _events_dir
    _events_dir = path


def reset_events_dir() -> None:
    """Reset to default events directory."""
    global _events_dir
    _events_dir = _DEFAULT_EVENTS_DIR
