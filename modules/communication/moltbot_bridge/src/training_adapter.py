"""OpenClaw training command adapter.

Exposes deterministic command/status surfaces for the existing
pattern-training system so OpenClaw can operate and report on
training natively.

Commands (must be the whole message or start with an explicit verb):
    - "training status" / "training progress" / "show training metrics"
    - "start training batch" / "run training batch"
    - "is training due"
"""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger("openclaw_dae")

# 012.txt canonical location
_012_TXT = Path("O:/Foundups-Agent/012.txt")

# ---------------------------------------------------------------------------
# Regex patterns — anchored so only explicit command forms match.
#
# Each pattern requires the training phrase to appear at the START of the
# normalised message (possibly preceded by one allowed verb).  This prevents
# generic search queries like "search training metrics" from hijacking.
# ---------------------------------------------------------------------------

_RE_STATUS = re.compile(
    r"^(?:show|get|check)\s+training\s+(status|progress|metrics)$"
    r"|^training\s+(status|progress|metrics)$"
)

_RE_DUE = re.compile(
    r"^(?:is\s+)?training\s+(due|needed|pending)$"
)

_RE_BATCH = re.compile(
    r"^(?:start|run|execute|trigger)\s+"
    r"(?:training\s+batch|pattern\s+training|batch\s+training)$"
)


async def try_training_command(raw_message: str) -> Optional[str]:
    """Match and dispatch deterministic training commands.

    Returns a formatted response string if the message matches a
    training command, or ``None`` to let normal routing continue.

    This coroutine is safe to ``await`` from any async context.
    """
    normalized = (raw_message or "").lower().strip()

    # --- status / progress / metrics ---
    if _RE_STATUS.search(normalized):
        return _training_status()

    # --- is training due ---
    if _RE_DUE.search(normalized):
        return _training_status()

    # --- start / run training batch ---
    if _RE_BATCH.search(normalized):
        return await _trigger_training_batch()

    return None


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _training_status() -> str:
    """Build a deterministic training status report."""
    parts = ["**Training Status**\n"]

    # Check if training is enabled
    training_enabled = os.getenv("AUTO_PATTERN_TRAINING", "1").strip().lower() not in {
        "0", "false", "no",
    }
    if not training_enabled:
        parts.append("- State: **DISABLED** (`AUTO_PATTERN_TRAINING=0`)")
        parts.append("- Enable with: `AUTO_PATTERN_TRAINING=1`")
        return "\n".join(parts)

    # Check PatternMemory availability
    try:
        from holo_index.qwen_advisor.pattern_memory import PatternMemory

        memory = PatternMemory()
    except Exception as exc:
        parts.append(f"- State: **UNAVAILABLE** (PatternMemory: {exc})")
        return "\n".join(parts)

    # Get stats
    try:
        stats = memory.get_stats()
    except Exception as exc:
        parts.append(f"- State: **ERROR** (get_stats failed: {exc})")
        return "\n".join(parts)

    checkpoint = stats.get("checkpoint_line", 0)
    total_patterns = stats.get("total_patterns", 0)
    verification_rate = stats.get("verification_rate", 0.0)
    verified_count = stats.get("verified_count", 0)
    sources = stats.get("sources", {})

    # Check 012.txt for due/complete calculation
    total_lines = 0
    txt_exists = _012_TXT.exists()
    if txt_exists:
        try:
            with open(_012_TXT, "r", encoding="utf-8", errors="ignore") as f:
                total_lines = sum(1 for _ in f)
        except OSError:
            total_lines = 0

    # Determine state
    if not txt_exists:
        state = "UNAVAILABLE"
        state_detail = "012.txt not found"
    elif checkpoint >= total_lines and total_lines > 0:
        state = "COMPLETE"
        state_detail = "all lines processed"
    elif total_lines > 0:
        remaining = total_lines - checkpoint
        pct = (checkpoint / total_lines) * 100
        state = "DUE"
        state_detail = f"{remaining} lines remaining ({pct:.1f}% complete)"
    else:
        state = "EMPTY"
        state_detail = "012.txt is empty"

    parts.append(f"- State: **{state}** ({state_detail})")
    parts.append(f"- Patterns stored: {total_patterns}")
    parts.append(f"- Checkpoint: line {checkpoint} / {total_lines}")
    parts.append(f"- Verification rate: {verification_rate:.1%} ({verified_count} verified)")

    if sources:
        parts.append("- Sources:")
        for source, count in sorted(sources.items(), key=lambda x: -x[1]):
            parts.append(f"  - {source}: {count}")

    if state == "DUE":
        parts.append("\nRun `start training batch` to process the next chunk.")

    return "\n".join(parts)


async def _trigger_training_batch() -> str:
    """Trigger batch pattern training and return result.

    This is a coroutine so it can be ``await``-ed from the async
    ``execute_query`` path without hitting ``asyncio.run()`` inside a
    running event loop.
    """
    # Check if training is enabled
    training_enabled = os.getenv("AUTO_PATTERN_TRAINING", "1").strip().lower() not in {
        "0", "false", "no",
    }
    if not training_enabled:
        return (
            "**Training batch not started.**\n\n"
            "Pattern training is disabled (`AUTO_PATTERN_TRAINING=0`).\n"
            "Enable with: `AUTO_PATTERN_TRAINING=1`"
        )

    try:
        from modules.infrastructure.idle_automation.src.idle_automation_dae import (
            IdleAutomationDAE,
        )

        dae = IdleAutomationDAE()
        result = await dae._execute_pattern_training()
    except Exception as exc:
        logger.error("[OPENCLAW-DAE] Training batch execution error: %s", exc)
        return f"**Training batch failed.**\n\nError: {exc}"

    success = result.get("success", False)
    patterns_stored = result.get("patterns_stored", 0)
    lines_processed = result.get("lines_processed", 0)
    error = result.get("error")

    if not success and error:
        # Distinguish "already complete" from real errors
        if "Already processed" in str(error):
            return (
                "**Training batch: already complete.**\n\n"
                f"{error}\n\n"
                "No new lines to process. Training is up to date."
            )
        return f"**Training batch did not complete.**\n\nReason: {error}"

    return (
        f"**Training batch complete.**\n\n"
        f"- Success: {success}\n"
        f"- Patterns stored: {patterns_stored}\n"
        f"- Lines processed: {lines_processed}"
    )
