#!/usr/bin/env python3
"""
Startup Maintenance Gate - Compute-conserving startup maintenance detection.

At startup, detects stale generated documentation / model policy / training readiness /
index freshness, then queues maintenance work for later execution instead of doing
heavy work inline.

Does NOT:
- Run model training
- Run full HoloIndex indexing
- Rewrite narrative docs
- Block startup with heavy compute

DOES:
- Inspect timestamps/hashes cheaply
- Queue maintenance tasks to AgentDB
- Return quickly without blocking
"""

from __future__ import annotations

import json
import logging
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from modules.infrastructure.shared_utilities.corpus_resolver import resolve_corpus_path

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[4]
REPORTS_DIR = (
    REPO_ROOT
    / "modules"
    / "communication"
    / "moltbot_bridge"
    / "workspace"
    / "reports"
)


def utc_now() -> datetime:
    """Return current UTC datetime."""
    return datetime.now(UTC)


def utc_now_iso() -> str:
    """Return current UTC timestamp in ISO format."""
    return utc_now().isoformat()


def _load_json_safe(path: Path) -> Optional[Dict[str, Any]]:
    """Load JSON file safely, returning None on error."""
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _artifact_age_hours(artifact: Optional[Dict[str, Any]], key: str = "generated_on") -> Optional[float]:
    """Return age in hours of a generated artifact, or None if unavailable."""
    if not artifact:
        return None
    ts = artifact.get(key) or artifact.get("checked_on")
    if not ts:
        return None
    try:
        checked = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        if checked.tzinfo is None:
            checked = checked.replace(tzinfo=UTC)
        return (utc_now() - checked).total_seconds() / 3600
    except Exception:
        return None


class StartupMaintenanceGate:
    """Lightweight startup maintenance detector and task queuer."""

    def __init__(
        self,
        repo_root: Optional[Path] = None,
        max_self_research_age_hours: float = 6.0,
        max_holo_index_age_hours: float = 12.0,
        max_training_status_age_hours: float = 24.0,
        max_model_status_age_hours: float = 24.0,
    ):
        self.repo_root = Path(repo_root or REPO_ROOT).resolve()
        self.reports_dir = REPORTS_DIR
        self.max_self_research_age_hours = max_self_research_age_hours
        self.max_holo_index_age_hours = max_holo_index_age_hours
        self.max_training_status_age_hours = max_training_status_age_hours
        self.max_model_status_age_hours = max_model_status_age_hours

    def check_self_research_status(self) -> Dict[str, Any]:
        """Check if self-research status is stale."""
        path = self.reports_dir / "openclaw_self_research_status.json"
        status = _load_json_safe(path)
        age = _artifact_age_hours(status)

        return {
            "artifact": "self_research_status",
            "path": str(path),
            "exists": status is not None,
            "age_hours": age,
            "max_age_hours": self.max_self_research_age_hours,
            "stale": age is None or age > self.max_self_research_age_hours,
        }

    def check_holo_index_freshness(self) -> Dict[str, Any]:
        """Check if HoloIndex is stale using AgentDB."""
        try:
            from modules.infrastructure.database.src.agent_db import AgentDB

            db = AgentDB()
            code_stale = db.should_refresh_index("code", max_age_hours=self.max_holo_index_age_hours)
            wsp_stale = db.should_refresh_index("wsp", max_age_hours=self.max_holo_index_age_hours)
            stale = code_stale or wsp_stale
        except Exception as exc:
            logger.debug("HoloIndex freshness check failed: %s", exc)
            code_stale = None
            wsp_stale = None
            stale = True  # Assume stale if we can't check

        return {
            "artifact": "holo_index",
            "code_stale": code_stale,
            "wsp_stale": wsp_stale,
            "max_age_hours": self.max_holo_index_age_hours,
            "stale": stale,
        }

    def check_training_readiness(self) -> Dict[str, Any]:
        """Check training readiness without running training."""
        path = self.reports_dir / "training_readiness_status.json"
        status = _load_json_safe(path)
        age = _artifact_age_hours(status)

        # Check PatternMemory stats and corpus size for consistent due/progress
        training_due = False
        checkpoint_line = None
        corpus_lines = None
        progress_pct = 0.0
        try:
            from holo_index.qwen_advisor.pattern_memory import PatternMemory

            mem = PatternMemory()
            stats = mem.get_stats()
            if stats:
                checkpoint_line = stats.get("checkpoint_line", 0)

            # Get actual corpus size for percentage-based completion
            corpus_path = resolve_corpus_path(self.repo_root)
            if corpus_path is not None and corpus_path.exists():
                with open(corpus_path, "r", encoding="utf-8", errors="ignore") as f:
                    corpus_lines = sum(1 for _ in f)

            # Training is due if less than 95% complete (consistent policy)
            if corpus_lines and checkpoint_line is not None:
                progress_pct = (checkpoint_line / corpus_lines) * 100
                training_due = progress_pct < 95.0
            elif checkpoint_line is None:
                # No checkpoint means training never started
                training_due = True
        except Exception:
            pass

        return {
            "artifact": "training_readiness",
            "path": str(path),
            "exists": status is not None,
            "age_hours": age,
            "max_age_hours": self.max_training_status_age_hours,
            "stale": age is None or age > self.max_training_status_age_hours,
            "checkpoint_line": checkpoint_line,
            "corpus_lines": corpus_lines,
            "progress_pct": progress_pct,
            "training_due": training_due,
        }

    def check_model_routing_status(self) -> Dict[str, Any]:
        """Check local model routing status freshness."""
        path = self.reports_dir / "local_model_status.json"
        status = _load_json_safe(path)
        age = _artifact_age_hours(status)

        return {
            "artifact": "model_routing_status",
            "path": str(path),
            "exists": status is not None,
            "age_hours": age,
            "max_age_hours": self.max_model_status_age_hours,
            "stale": age is None or age > self.max_model_status_age_hours,
        }

    def detect_maintenance_needs(self) -> Dict[str, Any]:
        """Detect all maintenance needs without running heavy work."""
        checks = {
            "self_research": self.check_self_research_status(),
            "holo_index": self.check_holo_index_freshness(),
            "training": self.check_training_readiness(),
            "model_routing": self.check_model_routing_status(),
        }

        stale_count = sum(1 for c in checks.values() if c.get("stale"))
        training_due = checks["training"].get("training_due", False)

        return {
            "checked_at": utc_now_iso(),
            "checks": checks,
            "stale_count": stale_count,
            "training_due": training_due,
            "maintenance_needed": stale_count > 0 or training_due,
        }

    def queue_maintenance_tasks(self, detection: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Queue maintenance tasks to AgentDB for later execution.

        Does NOT execute tasks - only queues them for idle automation / supervisor.
        """
        try:
            from modules.infrastructure.database.src.agent_db import AgentDB
        except ImportError:
            logger.warning("[STARTUP_MAINT] AgentDB unavailable - cannot queue tasks")
            return []

        db = AgentDB()
        queued = []
        checks = detection.get("checks", {})

        # Queue self-research refresh if stale
        if checks.get("self_research", {}).get("stale"):
            task_id = "startup_refresh_self_research"
            created = db.create_autonomous_task(
                task_id=task_id,
                description="Refresh self-research status (startup maintenance gate detected staleness)",
                required_skills=["openclaw-monitor"],
                estimated_complexity=2.0,
                priority_score=12.0,
                context={
                    "source": "startup_maintenance_gate",
                    "trigger": "stale_self_research",
                    "age_hours": checks["self_research"].get("age_hours"),
                },
            )
            if created:
                try:
                    db.db.execute_write(
                        "UPDATE agents_autonomous_tasks SET status = 'pending' WHERE task_id = ? AND status IS NULL",
                        (task_id,),
                    )
                except Exception:
                    pass
            queued.append({"task_id": task_id, "created": created, "type": "self_research_refresh"})

        # Queue HoloIndex refresh if stale
        if checks.get("holo_index", {}).get("stale"):
            task_id = "startup_refresh_holo_index"
            created = db.create_autonomous_task(
                task_id=task_id,
                description="Refresh HoloIndex (startup maintenance gate detected staleness)",
                required_skills=["holo-search"],
                estimated_complexity=3.0,
                priority_score=11.0,
                context={
                    "source": "startup_maintenance_gate",
                    "trigger": "stale_holo_index",
                    "code_stale": checks["holo_index"].get("code_stale"),
                    "wsp_stale": checks["holo_index"].get("wsp_stale"),
                },
            )
            if created:
                try:
                    db.db.execute_write(
                        "UPDATE agents_autonomous_tasks SET status = 'pending' WHERE task_id = ? AND status IS NULL",
                        (task_id,),
                    )
                except Exception:
                    pass
            queued.append({"task_id": task_id, "created": created, "type": "holo_index_refresh"})

        # Queue training batch only if explicitly due AND status is stale
        training = checks.get("training", {})
        if training.get("training_due") and training.get("stale"):
            task_id = "startup_training_batch"
            created = db.create_autonomous_task(
                task_id=task_id,
                description="Run training batch (startup detected training is due)",
                required_skills=["training-system"],
                estimated_complexity=4.0,
                priority_score=10.0,
                context={
                    "source": "startup_maintenance_gate",
                    "trigger": "training_due",
                    "checkpoint_line": training.get("checkpoint_line"),
                },
            )
            if created:
                try:
                    db.db.execute_write(
                        "UPDATE agents_autonomous_tasks SET status = 'pending' WHERE task_id = ? AND status IS NULL",
                        (task_id,),
                    )
                except Exception:
                    pass
            queued.append({"task_id": task_id, "created": created, "type": "training_batch"})

        # Queue model status refresh if stale
        if checks.get("model_routing", {}).get("stale"):
            task_id = "startup_refresh_model_status"
            created = db.create_autonomous_task(
                task_id=task_id,
                description="Refresh local model routing status",
                required_skills=["openclaw-monitor"],
                estimated_complexity=1.0,
                priority_score=8.0,
                context={
                    "source": "startup_maintenance_gate",
                    "trigger": "stale_model_status",
                    "age_hours": checks["model_routing"].get("age_hours"),
                },
            )
            if created:
                try:
                    db.db.execute_write(
                        "UPDATE agents_autonomous_tasks SET status = 'pending' WHERE task_id = ? AND status IS NULL",
                        (task_id,),
                    )
                except Exception:
                    pass
            queued.append({"task_id": task_id, "created": created, "type": "model_status_refresh"})

        return queued

    def run(self, queue_tasks: bool = True) -> Dict[str, Any]:
        """Run startup maintenance detection and optionally queue tasks.

        Returns quickly - does NOT run heavy work.
        """
        detection = self.detect_maintenance_needs()
        queued = []

        if queue_tasks and detection.get("maintenance_needed"):
            queued = self.queue_maintenance_tasks(detection)

        return {
            "detection": detection,
            "queued_tasks": queued,
            "queue_enabled": queue_tasks,
        }


def run_startup_maintenance_gate(repo_root: Optional[Path] = None, queue_tasks: bool = True) -> bool:
    """Run the startup maintenance gate.

    This is the entry point called from main.py.
    Returns True always (non-blocking) but logs maintenance needs.
    """
    try:
        gate = StartupMaintenanceGate(repo_root=repo_root)
        result = gate.run(queue_tasks=queue_tasks)

        detection = result.get("detection", {})
        stale_count = detection.get("stale_count", 0)
        training_due = detection.get("training_due", False)
        queued = result.get("queued_tasks", [])

        if stale_count > 0 or training_due:
            parts = []
            if stale_count > 0:
                parts.append(f"stale={stale_count}")
            if training_due:
                parts.append("training_due=yes")
            if queued:
                parts.append(f"queued={len(queued)}")

            print(f"[STARTUP-MAINT] preflight=PASS {' '.join(parts)}")
        else:
            print("[STARTUP-MAINT] preflight=PASS fresh")

        return True  # Never blocks startup

    except Exception as exc:
        logger.debug("[STARTUP-MAINT] Detection failed: %s", exc)
        print(f"[STARTUP-MAINT] preflight=WARN error={type(exc).__name__}")
        return True  # Non-blocking even on error


if __name__ == "__main__":
    import sys

    queue = "--no-queue" not in sys.argv
    run_startup_maintenance_gate(queue_tasks=queue)
