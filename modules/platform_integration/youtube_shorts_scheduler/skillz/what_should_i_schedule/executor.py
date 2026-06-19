#!/usr/bin/env python3
"""
what_should_i_schedule - SKILLz Executor

Answers "which channel should I schedule next?" for the YouTube Shorts daemon.
Ranks the shorts-enabled channels by scheduling NEED so the daemon/Qwen works the
most-needed channel first.

This is FOR THE AGENT (WRE/daemon triggers it; --agent-command invokes it). 012 only
observes the emitted breadcrumb + PatternMemory outcome. There is NO manual-012 path.

Read-only:
    - Reads the persisted per-channel schedule tracker JSON via ScheduleTracker.
    - Never mutates a schedule, never opens a browser, never calls a live model.

WSP Compliance:
    WSP 95: SKILLz Wardrobe Protocol (micro chain-of-thought + pattern fidelity)
    WSP 77: Agent Coordination (Qwen/daemon consumes the ranking)
    WSP 91: DAEmon Observability (breadcrumb on every run)
    WSP 60/48: Pattern Memory outcome on every run (WRE self-improvement testbed)
    WSP 27: Phase 0 KNOWLEDGE (rank-before-act)

Malleable seams (intentional):
    - DATA SOURCE is injected via `count_fn` (default: ScheduleTracker.get_count).
      A future LIVE 'Has schedule' DOM verify or engagement-learning signal plugs in
      here WITHOUT touching the ranking math.
    - NEED FORMULA is injected via `deficit_fn` (default: hard-cap deficit).
      Swap the rule (e.g. weight near-term days, fold in engagement) without touching
      data loading or ranking/sort.

Usage (agent / daemon):
    from .executor import rank_channels_by_need
    ranking = rank_channels_by_need(upcoming_days=7)
    top = ranking[0]  # highest need -> schedule this channel next

Usage (--agent-command surface, via youtube_automation_adapter):
    youtube action schedule_priority upcoming_days=7
    (the adapter spawns: python -m ...skillz.what_should_i_schedule.run_skill --json)
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

# Authoritative per-day cap. Imported from the tracker so this skill tracks the
# single load-bearing knob (HARD_CAP_PER_DAY, schedule_tracker.py, landed #844).
try:
    from modules.platform_integration.youtube_shorts_scheduler.src.schedule_tracker import (
        HARD_CAP_PER_DAY,
        ScheduleTracker,
    )
except Exception:  # pragma: no cover - defensive import for isolated tests
    HARD_CAP_PER_DAY = 3
    ScheduleTracker = None  # type: ignore

DEFAULT_UPCOMING_DAYS = 7

# Source DAE label for breadcrumb attribution (WSP 91).
SOURCE_DAE = "youtube_shorts_scheduler"
SKILL_NAME = "what_should_i_schedule"


@dataclass
class ChannelNeed:
    """Scheduling-need verdict for a single channel (one row of the ranking)."""

    channel_id: str
    name: str
    upcoming_days_checked: int
    total_deficit: int
    days_empty: int
    recommend: str  # "schedule" | "sufficient"
    per_day_counts: List[int] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "channel_id": self.channel_id,
            "name": self.name,
            "upcoming_days_checked": self.upcoming_days_checked,
            "total_deficit": self.total_deficit,
            "days_empty": self.days_empty,
            "recommend": self.recommend,
            "per_day_counts": self.per_day_counts,
        }


# === Malleable seam 1: the data source ======================================

def _default_count_fn(channel_id: str, date_str: str) -> int:
    """Default data source: persisted per-channel schedule tracker JSON.

    Reads memory/schedule_<channel_id>.json via ScheduleTracker.get_count(date_str).
    Pure read; no browser, no mutation.
    """
    if ScheduleTracker is None:  # pragma: no cover - only when import failed
        return 0
    tracker = ScheduleTracker(channel_id)
    return tracker.get_count(date_str)


# === Malleable seam 2: the need formula =====================================

def _default_deficit_fn(count: int, cap: int) -> int:
    """Default need rule: a day under the hard cap contributes (cap - count)."""
    return max(0, cap - count)


def _upcoming_date_strings(upcoming_days: int, today: Optional[datetime] = None) -> List[str]:
    """Build the next-N upcoming date strings in the tracker's exact format.

    Matches ScheduleTracker date keys: f"{d.strftime('%b')} {d.day}, {d.year}"
    (Windows-safe; no %-d). Starts at tomorrow, like the allocator's default window.
    """
    base = today or datetime.now()
    dates: List[str] = []
    for offset in range(1, upcoming_days + 1):
        d = base + timedelta(days=offset)
        dates.append(f"{d.strftime('%b')} {d.day}, {d.year}")
    return dates


def compute_channel_need(
    channel_id: str,
    name: str,
    *,
    upcoming_days: int = DEFAULT_UPCOMING_DAYS,
    cap: int = HARD_CAP_PER_DAY,
    count_fn: Callable[[str, str], int] = _default_count_fn,
    deficit_fn: Callable[[int, int], int] = _default_deficit_fn,
    today: Optional[datetime] = None,
) -> ChannelNeed:
    """Compute the scheduling-need verdict for one channel (pure + configurable).

    Args:
        channel_id: YouTube channel ID (tracker key).
        name: Human-readable channel name (for the ranking row).
        upcoming_days: How many upcoming days to inspect (default 7).
        cap: Per-day hard cap (default HARD_CAP_PER_DAY=3).
        count_fn: (channel_id, date_str) -> scheduled count. Swappable data source.
        deficit_fn: (count, cap) -> per-day need contribution. Swappable formula.
        today: Injectable clock for deterministic tests.

    Returns:
        ChannelNeed with total_deficit, days_empty, and a schedule/sufficient recommend.
    """
    date_strings = _upcoming_date_strings(upcoming_days, today=today)
    per_day_counts = [int(count_fn(channel_id, ds)) for ds in date_strings]

    total_deficit = sum(deficit_fn(c, cap) for c in per_day_counts)
    days_empty = sum(1 for c in per_day_counts if c <= 0)
    recommend = "schedule" if total_deficit > 0 else "sufficient"

    return ChannelNeed(
        channel_id=channel_id,
        name=name,
        upcoming_days_checked=upcoming_days,
        total_deficit=total_deficit,
        days_empty=days_empty,
        recommend=recommend,
        per_day_counts=per_day_counts,
    )


def _default_channels() -> List[Dict[str, str]]:
    """Load shorts-enabled channels (id + name) from the channel registry."""
    from modules.infrastructure.shared_utilities.youtube_channel_registry import (
        get_channels,
    )

    channels: List[Dict[str, str]] = []
    for ch in get_channels(role="shorts"):
        cid = ch.get("id")
        if not cid:
            continue
        channels.append({"channel_id": cid, "name": ch.get("name", ch.get("key", cid))})
    return channels


def rank_channels_by_need(
    *,
    upcoming_days: int = DEFAULT_UPCOMING_DAYS,
    cap: int = HARD_CAP_PER_DAY,
    channels: Optional[List[Dict[str, str]]] = None,
    count_fn: Callable[[str, str], int] = _default_count_fn,
    deficit_fn: Callable[[int, int], int] = _default_deficit_fn,
    today: Optional[datetime] = None,
) -> List[Dict[str, Any]]:
    """Rank channels by scheduling need (highest need first).

    A channel with empty/under-target upcoming days ranks HIGH (deficit drives the
    sort). A channel full at the cap for every inspected day ranks LOWEST with
    recommend="sufficient".

    Args:
        upcoming_days: Upcoming days to inspect per channel (default 7).
        cap: Per-day hard cap (default HARD_CAP_PER_DAY=3).
        channels: Optional [{channel_id, name}, ...] override (default: registry shorts).
        count_fn: Swappable data source (default: schedule tracker).
        deficit_fn: Swappable need formula (default: hard-cap deficit).
        today: Injectable clock for deterministic tests.

    Returns:
        List of ranking rows (dicts), sorted by total_deficit desc, then days_empty
        desc, then name asc for a stable tie-break.
    """
    chan_list = channels if channels is not None else _default_channels()

    needs = [
        compute_channel_need(
            ch["channel_id"],
            ch["name"],
            upcoming_days=upcoming_days,
            cap=cap,
            count_fn=count_fn,
            deficit_fn=deficit_fn,
            today=today,
        )
        for ch in chan_list
    ]

    needs.sort(key=lambda n: (-n.total_deficit, -n.days_empty, n.name))
    return [n.to_dict() for n in needs]


# === Signal emission (WSP 91 breadcrumb + WSP 60/48 PatternMemory) ==========

def _emit_breadcrumb(ranking: List[Dict[str, Any]], upcoming_days: int, cap: int) -> bool:
    """Emit a schedule_priority breadcrumb so the WRE/overseer can learn (WSP 91)."""
    try:
        from modules.communication.livechat.src.breadcrumb_telemetry import (
            get_breadcrumb_telemetry,
        )

        top = ranking[0] if ranking else {}
        get_breadcrumb_telemetry().store_breadcrumb(
            source_dae=SOURCE_DAE,
            event_type="schedule_priority",
            message=(
                f"schedule-priority ranked {len(ranking)} channels; "
                f"top={top.get('name', 'n/a')} "
                f"deficit={top.get('total_deficit', 0)} "
                f"recommend={top.get('recommend', 'n/a')}"
            ),
            phase="WHAT_SHOULD_I_SCHEDULE",
            metadata={
                "skill": SKILL_NAME,
                "upcoming_days": upcoming_days,
                "cap": cap,
                "ranking": ranking,
            },
        )
        return True
    except Exception as exc:  # pragma: no cover - telemetry is best-effort
        logger.warning(f"[{SKILL_NAME}] breadcrumb emit failed: {exc}")
        return False


def _store_outcome(ranking: List[Dict[str, Any]], upcoming_days: int, cap: int) -> bool:
    """Store a SkillOutcome so the WRE remembers each run (WSP 60/48)."""
    try:
        import json

        from modules.infrastructure.wre_core.src.pattern_memory import (
            PatternMemory,
            SkillOutcome,
        )

        top_deficit = ranking[0]["total_deficit"] if ranking else 0
        outcome = SkillOutcome(
            execution_id=f"{SKILL_NAME}-{uuid.uuid4().hex[:12]}",
            skill_name=SKILL_NAME,
            agent="gemma",
            timestamp=datetime.now().isoformat(),
            input_context=json.dumps(
                {"upcoming_days": upcoming_days, "cap": cap, "channels": len(ranking)},
                separators=(",", ":"),
            ),
            output_result=json.dumps({"ranking": ranking}, separators=(",", ":"))[:10000],
            success=True,
            pattern_fidelity=1.0,
            outcome_quality=1.0 if top_deficit > 0 else 0.8,
            execution_time_ms=0,
            step_count=len(ranking),
            failed_at_step=None,
            notes=f"source={SKILL_NAME} read_only=true cap={cap}",
        )
        PatternMemory().store_outcome(outcome)
        return True
    except Exception as exc:  # pragma: no cover - memory is best-effort
        logger.warning(f"[{SKILL_NAME}] pattern memory store failed: {exc}")
        return False


def run_skill(
    *,
    upcoming_days: int = DEFAULT_UPCOMING_DAYS,
    cap: int = HARD_CAP_PER_DAY,
    channels: Optional[List[Dict[str, str]]] = None,
    count_fn: Callable[[str, str], int] = _default_count_fn,
    deficit_fn: Callable[[int, int], int] = _default_deficit_fn,
    today: Optional[datetime] = None,
    emit_signals: bool = True,
) -> Dict[str, Any]:
    """SKILLz entry point: rank channels and emit WRE learning signals.

    Returns a structured result (for the daemon/Qwen to consume) including the
    ranking and which signals were emitted.
    """
    ranking = rank_channels_by_need(
        upcoming_days=upcoming_days,
        cap=cap,
        channels=channels,
        count_fn=count_fn,
        deficit_fn=deficit_fn,
        today=today,
    )

    breadcrumb_emitted = False
    outcome_stored = False
    if emit_signals:
        breadcrumb_emitted = _emit_breadcrumb(ranking, upcoming_days, cap)
        outcome_stored = _store_outcome(ranking, upcoming_days, cap)

    top = ranking[0] if ranking else None
    return {
        "success": True,
        "skill": SKILL_NAME,
        "upcoming_days": upcoming_days,
        "cap": cap,
        "channel_count": len(ranking),
        "recommended_channel": top,
        "ranking": ranking,
        "breadcrumb_emitted": breadcrumb_emitted,
        "outcome_stored": outcome_stored,
    }
