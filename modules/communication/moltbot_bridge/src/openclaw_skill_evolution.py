"""Deterministic OpenClaw skill evolution report helpers.

Phase 1 is read-only: surface review candidates from PatternMemory without
mutating WRE skills or scheduling promotions.

Phase 2 adds a bounded mutation surface that:
- Surfaces A/B test status and promotion readiness per skill
- Gates all mutation operations behind explicit env vars (fail-closed)
- Reuses existing WRE primitives (PatternMemory, WRESkillsRegistryV2)
- Does NOT introduce duplicate A/B or promotion engines

WSP Compliance: WSP 48 (Recursive Self-Improvement), WSP 77 (Agent Coordination)
"""

from __future__ import annotations

import json
import logging
import os
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

# Phase 2: Mutation Surface Constants
MUTATION_SURFACE_FILENAME = "openclaw_mutation_surface_report.json"

# Phase 2: Environment Gates (fail-closed by default)
# These must be explicitly set to "1" to enable mutation features
def _is_mutation_surface_enabled() -> bool:
    return os.getenv("OPENCLAW_MUTATION_SURFACE_ENABLED", "0") == "1"

def _is_ab_scheduling_enabled() -> bool:
    return os.getenv("OPENCLAW_AB_SCHEDULING_ENABLED", "0") == "1"

def _is_promotion_enabled() -> bool:
    return os.getenv("OPENCLAW_PROMOTION_ENABLED", "0") == "1"


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


# =============================================================================
# Phase 2: Mutation Surface (bounded, gated, reuses WRE primitives only)
# =============================================================================


def get_mutation_surface_report_path(repo_root: Path) -> Path:
    """Return the canonical mutation surface report path."""
    root = Path(repo_root).resolve()
    return (
        root
        / "modules"
        / "communication"
        / "moltbot_bridge"
        / "workspace"
        / "reports"
        / MUTATION_SURFACE_FILENAME
    )


def mutation_surface_report_due(repo_root: Path, max_age_sec: float = DEFAULT_REPORT_MAX_AGE_SEC) -> bool:
    """Return True when mutation surface report is missing or older than max_age_sec."""
    if not _is_mutation_surface_enabled():
        return False  # Gate closed - never due
    report_path = get_mutation_surface_report_path(repo_root)
    if not report_path.exists():
        return True
    try:
        age_sec = max(0.0, time.time() - report_path.stat().st_mtime)
    except OSError:
        return True
    return age_sec >= max(60.0, float(max_age_sec))


def get_active_ab_test_status(pattern_memory: Any, skill_name: str) -> Optional[Dict[str, Any]]:
    """Query PatternMemory for active A/B test on skill.

    Reuses PatternMemory.get_active_ab_test() - does NOT create duplicate storage.
    """
    if not hasattr(pattern_memory, "get_active_ab_test"):
        return None
    try:
        ab_test = pattern_memory.get_active_ab_test(skill_name)
        if ab_test is None:
            return None
        return {
            "test_id": ab_test.get("test_id"),
            "control_version": ab_test.get("control_version"),
            "treatment_version": ab_test.get("treatment_version"),
            "status": ab_test.get("status"),
            "start_time": ab_test.get("start_time"),
            "control_trials": ab_test.get("control_trials", 0),
            "treatment_trials": ab_test.get("treatment_trials", 0),
            "sample_size_target": ab_test.get("sample_size_target", 20),
        }
    except Exception as exc:
        logger.debug(
            "[MUTATION-SURFACE] get_active_ab_test failed; error_type=%s",
            type(exc).__name__,
        )
        return None


def check_ab_promotion_status(pattern_memory: Any, skill_name: str) -> Dict[str, Any]:
    """Read the statistical A/B winner without granting promotion authority.

    The function name and ``promotion_decision`` key are compatibility surfaces.
    A treatment result is candidate-nomination evidence only.
    """
    result: Dict[str, Any] = {
        "has_active_test": False,
        "promotion_decision": None,
        "blocked_reason": None,
    }

    ab_test = get_active_ab_test_status(pattern_memory, skill_name)
    if ab_test is None:
        result["blocked_reason"] = "no_active_ab_test"
        return result

    result["has_active_test"] = True
    test_id = ab_test.get("test_id")

    if not hasattr(pattern_memory, "check_ab_promotion"):
        result["blocked_reason"] = "check_ab_promotion_not_available"
        return result

    try:
        decision = pattern_memory.check_ab_promotion(test_id)
        result["promotion_decision"] = decision  # 'treatment', 'control', or None
        if decision is None:
            result["blocked_reason"] = "insufficient_samples_or_inconclusive"
    except Exception as exc:
        logger.debug(
            "[MUTATION-SURFACE] check_ab_promotion failed; error_type=%s",
            type(exc).__name__,
        )
        result["blocked_reason"] = "check_failed"

    return result


def check_promotion_readiness(
    _pattern_memory: Any,  # unused - WRESkillsRegistryV2 owns promotion readiness
    skill_name: str,
    from_state: str = "prototype",
    to_state: str = "staged",
) -> Dict[str, Any]:
    """Check promotion readiness using WRESkillsRegistryV2.

    Reuses WRESkillsRegistryV2.check_promotion_readiness() - does NOT duplicate logic.
    Note: _pattern_memory param exists for API consistency but is unused.
    """
    result: Dict[str, Any] = {
        "ready": False,
        "from_state": from_state,
        "to_state": to_state,
        "blocked_reason": None,
        "checks": {},
    }

    try:
        from modules.infrastructure.wre_core.skillz.skills_registry_v2 import WRESkillsRegistryV2
        registry = WRESkillsRegistryV2()
        readiness = registry.check_promotion_readiness(skill_name, from_state, to_state)
        registry.close()

        result["ready"] = readiness.get("ready", False)
        result["checks"] = readiness
        if not result["ready"]:
            result["blocked_reason"] = readiness.get("reason") or readiness.get("error")
    except ImportError:
        result["blocked_reason"] = "WRESkillsRegistryV2_not_available"
    except Exception as exc:
        logger.debug(
            "[MUTATION-SURFACE] promotion readiness failed; error_type=%s",
            type(exc).__name__,
        )
        result["blocked_reason"] = "check_failed"

    return result


def build_mutation_surface_entry(
    pattern_memory: Any,
    skill_name: str,
    metrics: Dict[str, Any],
    *,
    min_executions: int = DEFAULT_MIN_EXECUTIONS,
    fidelity_threshold: float = DEFAULT_FIDELITY_THRESHOLD,
) -> Dict[str, Any]:
    """Build mutation surface entry for a single skill.

    Reports raw facts only - does NOT make mutation decisions.
    """
    execution_count = int(metrics.get("execution_count", 0) or 0)
    avg_fidelity = float(metrics.get("avg_fidelity", 0.0) or 0.0)

    # Base classification from Phase 1
    status, recommendation = classify_skill_metrics(
        metrics,
        min_executions=min_executions,
        fidelity_threshold=fidelity_threshold,
    )

    # Active A/B test status (query only)
    active_ab_test = get_active_ab_test_status(pattern_memory, skill_name)

    # A/B statistical winner (query only; no promotion authority)
    ab_promotion = check_ab_promotion_status(pattern_memory, skill_name)

    # WRE promotion readiness (query only)
    promotion_readiness = check_promotion_readiness(pattern_memory, skill_name)

    # Determine mutation status
    mutation_status = "blocked"
    requires_approval = True
    blocked_reason = None
    recommended_action = recommendation

    if status == "insufficient_data":
        mutation_status = "blocked"
        blocked_reason = "insufficient_execution_data"
        recommended_action = "gather_more_data"
    elif status == "healthy":
        mutation_status = "stable"
        blocked_reason = None
        recommended_action = "no_action"
        requires_approval = False
    elif active_ab_test is not None:
        mutation_status = "ab_test_active"
        blocked_reason = None
        if ab_promotion["promotion_decision"] == "treatment":
            recommended_action = "nominate_treatment_candidate"
        elif ab_promotion["promotion_decision"] == "control":
            recommended_action = "archive_treatment"
        else:
            recommended_action = "await_ab_completion"
    elif status == "candidate_for_review":
        mutation_status = "eligible_for_ab"
        blocked_reason = None
        recommended_action = "schedule_ab_test"

    # Gate status
    gates = {
        "mutation_surface_enabled": _is_mutation_surface_enabled(),
        "ab_scheduling_enabled": _is_ab_scheduling_enabled(),
        "promotion_enabled": _is_promotion_enabled(),
    }

    return {
        "skill_name": skill_name,
        "execution_count": execution_count,
        "avg_fidelity": avg_fidelity,
        "success_rate": float(metrics.get("success_rate", 0.0) or 0.0),
        "avg_time_ms": int(metrics.get("avg_time_ms", 0) or 0),
        "latest_evolution_event": _latest_evolution_event(pattern_memory, skill_name),
        "status": status,
        "mutation_status": mutation_status,
        "recommended_action": recommended_action,
        "requires_approval": requires_approval,
        "blocked_reason": blocked_reason,
        "active_ab_test": active_ab_test,
        "ab_promotion_status": ab_promotion,
        "promotion_readiness": promotion_readiness,
        "gates": gates,
    }


def build_mutation_surface_report(
    pattern_memory: Any,
    *,
    days: int = DEFAULT_PERIOD_DAYS,
    min_executions: int = DEFAULT_MIN_EXECUTIONS,
    fidelity_threshold: float = DEFAULT_FIDELITY_THRESHOLD,
) -> Dict[str, Any]:
    """Build a deterministic mutation surface report from PatternMemory data.

    This is a READ-ONLY surface that queries existing WRE primitives.
    It surfaces mutation eligibility and readiness but does NOT mutate.
    """
    if not _is_mutation_surface_enabled():
        return {
            "generated_on": datetime.now(timezone.utc).isoformat(),
            "enabled": False,
            "blocked_reason": "OPENCLAW_MUTATION_SURFACE_ENABLED not set",
            "skills_evaluated": 0,
            "candidates": [],
        }

    skill_names = discover_openclaw_skills(pattern_memory, days=days)
    candidates: List[Dict[str, Any]] = []

    for skill_name in skill_names:
        metrics = pattern_memory.get_skill_metrics(skill_name, days=days)
        entry = build_mutation_surface_entry(
            pattern_memory,
            skill_name,
            metrics,
            min_executions=min_executions,
            fidelity_threshold=fidelity_threshold,
        )
        candidates.append(entry)

    # Summary counts
    stable_count = sum(1 for c in candidates if c["mutation_status"] == "stable")
    ab_active_count = sum(1 for c in candidates if c["mutation_status"] == "ab_test_active")
    eligible_count = sum(1 for c in candidates if c["mutation_status"] == "eligible_for_ab")
    blocked_count = sum(1 for c in candidates if c["mutation_status"] == "blocked")

    return {
        "generated_on": datetime.now(timezone.utc).isoformat(),
        "enabled": True,
        "period_days": int(days),
        "min_executions": int(min_executions),
        "fidelity_threshold": float(fidelity_threshold),
        "skills_evaluated": len(skill_names),
        "summary": {
            "stable": stable_count,
            "ab_test_active": ab_active_count,
            "eligible_for_ab": eligible_count,
            "blocked": blocked_count,
        },
        "gates": {
            "mutation_surface_enabled": _is_mutation_surface_enabled(),
            "ab_scheduling_enabled": _is_ab_scheduling_enabled(),
            "promotion_enabled": _is_promotion_enabled(),
        },
        "candidates": candidates,
    }


def write_mutation_surface_report(repo_root: Path, report: Dict[str, Any]) -> Path:
    """Write the canonical mutation surface report artifact."""
    report_path = get_mutation_surface_report_path(repo_root)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    logger.info("[MUTATION-SURFACE] Report written: %s", report_path.name)
    return report_path
