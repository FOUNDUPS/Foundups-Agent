#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Memory Nudge Engine - Automatic Memory Capture for High-Value Events.

Per HERMES_INSPIRED_FOUNDUPS_NATIVE_ROADMAP_2026-03-23:
- detect high-value moments
- generate short memory candidates
- store in workspace memory
- dedupe to avoid noise

Trigger types:
- supervisor_escalation: recurring error signatures in daemon self-audit
- self_research_change: new autonomous tasks, update candidates
- worktree_pressure: queue backlog above threshold
- grant_watchlist_change: grant pages changed, need review

WSP Compliance:
- WSP 22: Update ModLog after significant changes
- WSP 60: Module Memory Architecture
- WSP 97: Autonomy boundaries
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)

# Default paths
REPO_ROOT = Path(__file__).resolve().parents[4]
WORKSPACE_MEMORY_DIR = (
    REPO_ROOT / "modules/communication/moltbot_bridge/workspace/memory"
)
REPORTS_DIR = (
    REPO_ROOT / "modules/communication/moltbot_bridge/workspace/reports"
)


@dataclass
class NudgeEvent:
    """A high-value event that warrants a memory note."""

    trigger_type: str  # supervisor_escalation, self_research_change, etc.
    title: str
    summary: str
    provenance: str  # Source artifact or event
    priority: str = "P2"
    signature: str = ""  # Dedupe key (computed if empty)
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    details: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.signature:
            # Stable signature from trigger_type + title + provenance
            raw = f"{self.trigger_type}:{self.title}:{self.provenance}"
            self.signature = hashlib.sha256(raw.encode()).hexdigest()[:16]


class MemoryNudgeEngine:
    """
    Automatic memory capture for high-value events.

    Scans existing reports and state to detect:
    - Supervisor escalations / verify failures
    - Self-research changed items / new autonomous tasks
    - Architecture decision phrases
    - Dirty worktree pressure
    - Grant watchlist changes requiring human gate

    Writes deduplicated memory notes to workspace/memory/.
    """

    def __init__(
        self,
        repo_root: Optional[Path] = None,
        memory_dir: Optional[Path] = None,
        reports_dir: Optional[Path] = None,
    ):
        self.repo_root = Path(repo_root or REPO_ROOT).resolve()
        # Derive memory_dir and reports_dir from repo_root if not explicitly provided
        if memory_dir:
            self.memory_dir = Path(memory_dir)
        else:
            self.memory_dir = self.repo_root / "modules/communication/moltbot_bridge/workspace/memory"
        if reports_dir:
            self.reports_dir = Path(reports_dir)
        else:
            self.reports_dir = self.repo_root / "modules/communication/moltbot_bridge/workspace/reports"
        self._seen_signatures: Set[str] = set()
        self._load_seen_signatures()

    def _load_seen_signatures(self) -> None:
        """Load existing nudge signatures from memory directory."""
        if not self.memory_dir.exists():
            return
        for note_path in self.memory_dir.glob("*-nudge-*.md"):
            # Extract signature from filename: YYYY-MM-DD-nudge-SIGNATURE.md
            match = re.search(r"-nudge-([a-f0-9]{16})\.md$", note_path.name)
            if match:
                self._seen_signatures.add(match.group(1))

    def scan_all(self) -> List[NudgeEvent]:
        """Scan all trigger sources and return detected high-value events."""
        events: List[NudgeEvent] = []
        events.extend(self._scan_supervisor_escalations())
        events.extend(self._scan_self_research_changes())
        events.extend(self._scan_grant_watchlist_changes())
        events.extend(self._scan_worktree_pressure())
        return events

    def emit_nudges(self, events: Optional[List[NudgeEvent]] = None) -> List[Path]:
        """
        Write memory notes for high-value events.

        Returns list of created note paths.
        Deduplicates based on event signature.
        """
        if events is None:
            events = self.scan_all()

        created: List[Path] = []
        for event in events:
            if event.signature in self._seen_signatures:
                logger.debug("Skipping duplicate nudge: %s", event.signature)
                continue

            note_path = self._write_note(event)
            if note_path:
                created.append(note_path)
                self._seen_signatures.add(event.signature)

        return created

    def _write_note(self, event: NudgeEvent) -> Optional[Path]:
        """Write a single memory note for an event."""
        self.memory_dir.mkdir(parents=True, exist_ok=True)

        date_str = datetime.now(UTC).strftime("%Y-%m-%d")
        filename = f"{date_str}-nudge-{event.signature}.md"
        note_path = self.memory_dir / filename

        content = self._format_note(event)
        try:
            note_path.write_text(content, encoding="utf-8")
            logger.info("Created memory nudge: %s", note_path.name)
            return note_path
        except Exception as exc:
            logger.error("Failed to write memory nudge: %s", exc)
            return None

    def _format_note(self, event: NudgeEvent) -> str:
        """Format event as a concise markdown memory note."""
        lines = [
            f"# [{event.priority}] {event.title}",
            "",
            f"**Trigger**: {event.trigger_type}",
            f"**Timestamp**: {event.timestamp}",
            f"**Provenance**: `{event.provenance}`",
            "",
            "## Summary",
            "",
            event.summary,
            "",
        ]

        if event.details:
            lines.append("## Details")
            lines.append("")
            lines.append("```json")
            lines.append(json.dumps(event.details, indent=2, default=str))
            lines.append("```")
            lines.append("")

        lines.append(f"---")
        lines.append(f"_Auto-generated by memory_nudge_engine | sig:{event.signature}_")
        lines.append("")

        return "\n".join(lines)

    # ------------------------------------------------------------------ #
    #  Trigger Scanners                                                   #
    # ------------------------------------------------------------------ #

    def _scan_supervisor_escalations(self) -> List[NudgeEvent]:
        """Detect recurring error signatures from daemon self-audit."""
        events: List[NudgeEvent] = []

        # Check daemon self-audit escalations
        # Live schema: {signature, event_count, recommended_fix, dispatch_result, ...}
        escalations_path = (
            self.repo_root
            / "modules/infrastructure/wre_core/reports/daemon_self_audit_escalations.jsonl"
        )
        if escalations_path.exists():
            try:
                lines = escalations_path.read_text(encoding="utf-8").strip().split("\n")
                # Only check last 10 escalations, trigger on high event_count
                for line in lines[-10:]:
                    if not line.strip():
                        continue
                    record = json.loads(line)
                    event_count = record.get("event_count", 0)
                    signature = record.get("signature", "unknown")

                    # Trigger if event_count >= 5 (recurring issue)
                    if event_count >= 5:
                        events.append(NudgeEvent(
                            trigger_type="supervisor_escalation",
                            title=f"Recurring issue: {signature[:50]}",
                            summary=f"Error signature seen {event_count} times. Recommended: {record.get('recommended_fix', 'investigate')}",
                            provenance=str(escalations_path.relative_to(self.repo_root)),
                            priority="P1" if event_count >= 10 else "P2",
                            details={
                                "event_count": event_count,
                                "recommended_fix": record.get("recommended_fix"),
                                "dispatch_result": record.get("dispatch_result"),
                            },
                        ))
            except Exception as exc:
                logger.debug("Failed to scan escalations: %s", exc)

        return events

    def _scan_self_research_changes(self) -> List[NudgeEvent]:
        """Detect new autonomous tasks or update candidates from self-research."""
        events: List[NudgeEvent] = []

        status_path = self.reports_dir / "openclaw_self_research_status.json"
        if not status_path.exists():
            return events

        try:
            data = json.loads(status_path.read_text(encoding="utf-8"))
        except Exception:
            return events

        # Check update candidates with high priority
        for candidate in data.get("update_candidates", [])[:3]:
            mps = candidate.get("mps", {})
            priority = mps.get("priority", "P3")
            if priority in ("P0", "P1"):
                events.append(NudgeEvent(
                    trigger_type="self_research_change",
                    title=f"Update candidate: {candidate.get('title', 'unknown')[:50]}",
                    summary=mps.get("reasoning", "High-priority update candidate identified.")[:200],
                    provenance=str(status_path.relative_to(self.repo_root)),
                    priority=priority,
                    details={"total_mps": mps.get("total_mps"), "action": mps.get("action")},
                ))

        # Check new autonomous tasks
        # Live schema: autonomous_tasks is a list of {task_id, title, created, priority}
        autonomous_tasks = data.get("autonomous_tasks", [])
        if isinstance(autonomous_tasks, list) and len(autonomous_tasks) > 0:
            # Count newly created tasks
            new_tasks = [t for t in autonomous_tasks if t.get("created")]
            if new_tasks:
                task_titles = [t.get("title", "unknown")[:40] for t in new_tasks[:3]]
                events.append(NudgeEvent(
                    trigger_type="self_research_change",
                    title=f"{len(new_tasks)} autonomous task(s) queued",
                    summary=f"Self-research queued: {', '.join(task_titles)}",
                    provenance=str(status_path.relative_to(self.repo_root)),
                    priority="P1",
                    details={"task_count": len(new_tasks), "tasks": task_titles},
                ))

        return events

    def _scan_grant_watchlist_changes(self) -> List[NudgeEvent]:
        """Detect grant watchlist changes requiring review."""
        events: List[NudgeEvent] = []

        watchlist_path = self.reports_dir / "web3_grants_0102_watchlist_status.json"
        if not watchlist_path.exists():
            return events

        try:
            data = json.loads(watchlist_path.read_text(encoding="utf-8"))
        except Exception:
            return events

        # Live schema: {changed_count, error_count, changed_items, error_items, items}
        changed_count = data.get("changed_count", 0)
        error_count = data.get("error_count", 0)
        changed_items = data.get("changed_items", [])
        error_items = data.get("error_items", [])

        # Trigger on changed grants (need review)
        if changed_count > 0:
            events.append(NudgeEvent(
                trigger_type="grant_watchlist_change",
                title=f"{changed_count} grant page(s) changed",
                summary=f"Changed: {', '.join(changed_items[:3])}{'...' if changed_count > 3 else ''}. Review for new opportunities.",
                provenance=str(watchlist_path.relative_to(self.repo_root)),
                priority="P1",
                details={"changed_count": changed_count, "changed_items": changed_items[:5]},
            ))

        # Trigger on refresh errors (may miss opportunities)
        if error_count > 0:
            events.append(NudgeEvent(
                trigger_type="grant_watchlist_change",
                title=f"{error_count} grant watchlist error(s)",
                summary=f"Failed to refresh: {', '.join(error_items[:3])}. May miss new opportunities.",
                provenance=str(watchlist_path.relative_to(self.repo_root)),
                priority="P2",
                details={"error_count": error_count, "error_items": error_items[:5]},
            ))

        return events

    def _scan_worktree_pressure(self) -> List[NudgeEvent]:
        """Detect repeated dirty worktree or unresolved work pressure."""
        events: List[NudgeEvent] = []

        # Check queue status for repeated unresolved items
        queue_path = self.reports_dir / "openclaw_native_execution_queue_status.json"
        if not queue_path.exists():
            return events

        try:
            data = json.loads(queue_path.read_text(encoding="utf-8"))
        except Exception:
            return events

        # If audit_required_count is high, that's pressure
        audit_count = data.get("audit_required_count", 0)
        if audit_count >= 5:
            events.append(NudgeEvent(
                trigger_type="worktree_pressure",
                title=f"Queue backlog: {audit_count} items need audit",
                summary="Native execution queue has multiple items awaiting audit review.",
                provenance=str(queue_path.relative_to(self.repo_root)),
                priority="P2",
                details={"audit_required_count": audit_count, "queue_count": data.get("queue_count", 0)},
            ))

        return events


# ------------------------------------------------------------------ #
#  Convenience API                                                    #
# ------------------------------------------------------------------ #


def emit_memory_nudges(repo_root: Optional[Path] = None) -> List[Path]:
    """
    Convenience function to scan and emit memory nudges.

    Returns list of created note paths.
    """
    engine = MemoryNudgeEngine(repo_root=repo_root)
    return engine.emit_nudges()


def scan_nudge_events(repo_root: Optional[Path] = None) -> List[NudgeEvent]:
    """
    Convenience function to scan for nudge events without emitting.

    Returns list of detected events.
    """
    engine = MemoryNudgeEngine(repo_root=repo_root)
    return engine.scan_all()
