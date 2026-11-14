"""
Schedule DBA (PatternMemory) integration for youtube_shorts_scheduler.

Purpose (0102-first):
- Record scheduling events into the existing SQLite "DBA" (PatternMemory) so 0102 can
  recall what was scheduled without scanning YouTube Studio.

This is NOT video indexing. It is scheduling telemetry/state.
Indexing is layered after scheduling is stable.
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def record_schedule_outcome(
    *,
    channel_id: str,
    video_id: str,
    date_str: str,
    time_str: str,
    mode: str,
    success: bool,
    agent: str = "selenium",
    details: Optional[Dict[str, Any]] = None,
    db_path: Optional[Path] = None,
) -> bool:
    """
    Record a scheduling event into PatternMemory (SQLite).

    Args:
        channel_id: YouTube channel ID
        video_id: YouTube video ID
        date_str: Studio date string (e.g., "Jan 19, 2026")
        time_str: Studio time string (e.g., "5:30 PM")
        mode: Caller mode, e.g. "schedule" or "test"
        success: Whether scheduling succeeded
        agent: Agent identifier ("selenium", "ui-tars", etc.)
        details: Extra diagnostic fields (selector path, readback values, errors, jitter)
        db_path: Optional override for tests (otherwise default wre_core/data/pattern_memory.db)

    Returns:
        True if stored, False if PatternMemory unavailable or store failed.
    """
    start = time.time()

    try:
        from modules.infrastructure.wre_core.src.pattern_memory import PatternMemory, SkillOutcome
    except Exception as exc:
        logger.debug("[SCHEDULE-DBA] PatternMemory unavailable: %s", exc)
        return False

    input_context = {
        "channel_id": channel_id,
        "video_id": video_id,
        "date_str": date_str,
        "time_str": time_str,
        "mode": mode,
    }
    # A click acknowledgement must not train the positive-success pattern.
    details = details if isinstance(details, dict) else {}
    readback = details.get("readback")
    verified = bool(success) and isinstance(readback, dict) and all((
        readback.get("independent") is True,
        readback.get("channel_id") == channel_id,
        readback.get("video_id") == video_id,
        readback.get("date_str") == date_str,
        readback.get("time_str") == time_str,
        isinstance(details.get("requested_timezone"), str) and bool(details.get("requested_timezone").strip()),
        readback.get("timezone") == details.get("requested_timezone"),
        readback.get("visibility") == "scheduled",
    ))
    output_result = {
        "success": verified, "reported_success": bool(success),
        "verification_status": "verified" if verified else ("independent_readback_required" if success else "failed"),
        "performance_measured": False, "details": details,
    }
    fidelity = 1.0 if verified else 0.0
    quality = 1.0 if verified else 0.0

    try:
        memory = PatternMemory(db_path=db_path) if db_path is not None else PatternMemory()
        outcome = SkillOutcome(
            execution_id=str(uuid.uuid4()),
            skill_name="youtube_shorts_scheduler_schedule",
            agent=agent,
            timestamp=datetime.now().isoformat(),
            input_context=json.dumps(input_context, ensure_ascii=False),
            output_result=json.dumps(output_result, ensure_ascii=False),
            success=verified,
            pattern_fidelity=float(fidelity),
            outcome_quality=float(quality),
            execution_time_ms=int((time.time() - start) * 1000),
            step_count=5,
            failed_at_step=None if verified else (5 if success else 3),
            notes="Saved-state fidelity only; audience performance is unmeasured.",
        )
        memory.store_outcome(outcome)
        return True
    except Exception as exc:
        logger.warning("[SCHEDULE-DBA] Failed to store outcome: %s", exc)
        return False

