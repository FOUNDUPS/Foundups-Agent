"""Deterministic OpenClaw skill evolution report helpers.

Phase 1 is read-only: surface review candidates from PatternMemory without
mutating WRE skills or scheduling promotions.
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("openclaw_dae")

DEFAULT_PERIOD_DAYS = 7
DEFAULT_MIN_EXECUTIONS = 3
DEFAULT_FIDELITY_THRESHOLD = 0.90
DEFAULT_REPORT_MAX_AGE_SEC = 3600.0
REPORT_FILENAME = "openclaw_skill_evolution_report.json"


def get_skill_evolution_report_path(repo_root: Path) -> Path:
    """Return the canonical skill evolution report path."""
    root = Path(repo_root).resolve()
    return (
        root
        / "modules"
        / "communication"
        / "moltbot_bridge"
        / "workspace"
        / "reports"
        / REPORT_FILENAME
    )


def skill_evolution_report_due(repo_root: Path, max_age_sec: float = DEFAULT_REPORT_MAX_AGE_SEC) -> bool:
    """Return True when the report is missing or older than max_age_sec."""
    report_path = get_skill_evolution_report_path(repo_root)
    if not report_path.exists():
        return True
    try:
        age_sec = max(0.0, time.time() - report_path.stat().st_mtime)
    except OSError:
        return True
    return age_sec >= max(60.0, float(max_age_sec))


def discover_openclaw_skills(pattern_memory: Any, days: int = DEFAULT_PERIOD_DAYS) -> List[str]:
    """Discover distinct OpenClaw skill names from PatternMemory outcomes."""
    conn = getattr(pattern_memory, "conn", None)
    if conn is None:
        return []

    cutoff_time = (datetime.now() - timedelta(days=days)).isoformat()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT DISTINCT skill_name
        FROM skill_outcomes
        WHERE skill_name LIKE 'openclaw_%' AND timestamp >= ?
        ORDER BY skill_name
        """,
        (cutoff_time,),
    )
    return [row["skill_name"] for row in cursor.fetchall()]


def classify_skill_metrics(
    metrics: Dict[str, Any],
    *,
    min_executions: int = DEFAULT_MIN_EXECUTIONS,
    fidelity_threshold: float = DEFAULT_FIDELITY_THRESHOLD,
) -> Tuple[str, str]:
    """Classify a skill's health and recommend the next bounded action."""
    execution_count = int(metrics.get("execution_count", 0) or 0)
    avg_fidelity = float(metrics.get("avg_fidelity", 0.0) or 0.0)

    if execution_count < min_executions:
        return "insufficient_data", "gather_more_data"
    if avg_fidelity < fidelity_threshold:
        return "candidate_for_review", "review_for_evolution"
    return "healthy", "no_action"


def _latest_evolution_event(pattern_memory: Any, skill_name: str) -> Optional[Dict[str, Any]]:
    history = pattern_memory.get_evolution_history(skill_name)
    if not history:
        return None
    event = history[-1]
    return {
        "event_type": event.get("event_type"),
        "timestamp": event.get("timestamp"),
        "continuity_id": event.get("continuity_id"),
        "execution_id": event.get("execution_id"),
        "variation_id": event.get("variation_id"),
    }


def build_skill_evolution_report(
    pattern_memory: Any,
    *,
    days: int = DEFAULT_PERIOD_DAYS,
    min_executions: int = DEFAULT_MIN_EXECUTIONS,
    fidelity_threshold: float = DEFAULT_FIDELITY_THRESHOLD,
) -> Dict[str, Any]:
    """Build a deterministic review report from existing PatternMemory data."""
    skill_names = discover_openclaw_skills(pattern_memory, days=days)
    candidates: List[Dict[str, Any]] = []

    for skill_name in skill_names:
        metrics = pattern_memory.get_skill_metrics(skill_name, days=days)
        status, recommendation = classify_skill_metrics(
            metrics,
            min_executions=min_executions,
            fidelity_threshold=fidelity_threshold,
        )
        if status != "candidate_for_review":
            continue

        candidates.append(
            {
                "skill_name": skill_name,
                "execution_count": int(metrics.get("execution_count", 0) or 0),
                "avg_fidelity": float(metrics.get("avg_fidelity", 0.0) or 0.0),
                "success_rate": float(metrics.get("success_rate", 0.0) or 0.0),
                "avg_time_ms": int(metrics.get("avg_time_ms", 0) or 0),
                "latest_evolution_event": _latest_evolution_event(pattern_memory, skill_name),
                "status": status,
                "recommendation": recommendation,
            }
        )

    return {
        "generated_on": datetime.now(timezone.utc).isoformat(),
        "period_days": int(days),
        "min_executions": int(min_executions),
        "fidelity_threshold": float(fidelity_threshold),
        "skills_evaluated": len(skill_names),
        "candidate_count": len(candidates),
        "candidates": candidates,
    }


def write_skill_evolution_report(repo_root: Path, report: Dict[str, Any]) -> Path:
    """Write the canonical skill evolution report artifact."""
    report_path = get_skill_evolution_report_path(repo_root)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    logger.info("[SKILL-EVOLUTION] Report written: %s", report_path.name)
    return report_path
