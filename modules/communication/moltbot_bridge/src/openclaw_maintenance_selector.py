"""Bounded maintenance task selection for OpenClaw supervisor.

Selects safe, low-risk maintenance tasks that OpenClaw can execute
without human intervention. Uses HoloIndex execution bundle for
direction and writes structured report artifacts.

WSP Compliance:
    WSP 15: Module Prioritization (task scoring)
    WSP 77: Agent Coordination (bounded doer role)
    WSP 87: Semantic Code Discovery (HoloIndex bundle)
    WSP 97: System Execution (bounded retrieval)
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# Allowed maintenance task families (Phase 1)
# CRITICAL: These MUST map to real executors in run_task.py:
#   - source == "self_audit" → _try_self_audit_dispatch()
#   - "openclaw-grants" in required_skills → _try_grant_dispatch()
#   - source == "startup_maintenance_gate" → _try_startup_maintenance_dispatch()
#   - required_skills match WRE-registered skill → _try_wre_dispatch()
ALLOWED_TASK_FAMILIES = {
    "self_audit_fix": {
        "description": "Apply self-audit policy fixes for known safe patterns",
        "risk": "low",
        "sources": ["self_audit"],  # Maps to run_task.py dispatch path 2
        "required_skills": [],
        "executor": "self_audit_dispatch",
    },
    "grant_review": {
        "description": "Review grant watchlist items (read-only)",
        "risk": "low",
        "sources": ["grant_review", "watchlist_review"],
        "required_skills": ["openclaw-grants"],  # Maps to run_task.py dispatch path 3
        "executor": "grant_dispatch",
    },
    "startup_maintenance": {
        "description": "Startup maintenance gate tasks",
        "risk": "low",
        "sources": ["startup_maintenance_gate"],
        "required_skills": [],
        "executor": "startup_maintenance_dispatch",
    },
    "holoindex_postmerge": {
        "description": "Exact-SHA post-merge HoloIndex authority maintenance",
        "risk": "low",
        "sources": ["holoindex_postmerge_coordinator"],
        "required_skills": ["holo-search"],
        "executor": "holoindex_postmerge_dispatch",
    },
}

# Families that are explicitly NOT allowed in Phase 1
BLOCKED_TASK_FAMILIES = {
    "source_edit": "Source code modification requires explicit human approval",
    "architecture_change": "Architecture changes require 0102 review",
    "dependency_update": "Dependency updates require security review",
    "config_mutation": "Config changes require explicit approval",
    "external_api_call": "External API calls require authorization",
}


@dataclass
class MaintenanceTask:
    """A bounded maintenance task selected for execution."""

    task_id: str
    family: str
    description: str
    source: str
    risk_level: str
    bundle_confidence: float = 0.0
    execution_hints: List[str] = field(default_factory=list)
    verification_method: str = ""
    escalation_reason: Optional[str] = None

    def is_safe(self) -> bool:
        """Return True if task is safe to execute without human approval."""
        return (
            self.family in ALLOWED_TASK_FAMILIES
            and self.risk_level == "low"
            and self.escalation_reason is None
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize for reporting."""
        return {
            "task_id": self.task_id,
            "family": self.family,
            "description": self.description[:200],
            "source": self.source,
            "risk_level": self.risk_level,
            "bundle_confidence": round(self.bundle_confidence, 2),
            "is_safe": self.is_safe(),
            "escalation_reason": self.escalation_reason,
        }


@dataclass
class MaintenanceSelectionResult:
    """Result of maintenance task selection."""

    selected_task: Optional[MaintenanceTask]
    candidates_evaluated: int
    selection_reason: str
    bundle_used: bool
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "selected_task": self.selected_task.to_dict() if self.selected_task else None,
            "candidates_evaluated": self.candidates_evaluated,
            "selection_reason": self.selection_reason,
            "bundle_used": self.bundle_used,
            "timestamp": self.timestamp,
        }


def select_maintenance_task(
    pending_tasks: List[Dict[str, Any]],
    observation: Dict[str, Any],
    repo_root: Path,
) -> MaintenanceSelectionResult:
    """Select a safe bounded maintenance task from pending tasks.

    Args:
        pending_tasks: List of pending tasks from AgentDB
        observation: Current supervisor observation state
        repo_root: Repository root path

    Returns:
        MaintenanceSelectionResult with selected task or None
    """
    if not pending_tasks:
        return MaintenanceSelectionResult(
            selected_task=None,
            candidates_evaluated=0,
            selection_reason="no_pending_tasks",
            bundle_used=False,
        )

    candidates_evaluated = 0
    bundle_used = False

    for task in pending_tasks:
        candidates_evaluated += 1
        task_id = task.get("task_id", "")
        description = task.get("description", "")
        context = task.get("context", {}) if isinstance(task.get("context"), dict) else {}
        source = context.get("source", "")
        required_skills = task.get("required_skills", [])

        # Identify task family
        family = _identify_task_family(source, required_skills, description)
        if family is None:
            continue

        # Check if family is allowed
        if family not in ALLOWED_TASK_FAMILIES:
            continue

        family_config = ALLOWED_TASK_FAMILIES[family]

        # Build HoloIndex execution bundle for direction
        bundle_confidence = 0.0
        execution_hints = []
        try:
            from .openclaw_execution_bundle import build_execution_bundle

            bundle = build_execution_bundle(
                query=description,
                route=family,
                limit=3,
                include_patterns=True,
                include_docs=True,
            )
            bundle_confidence = bundle.confidence
            execution_hints = bundle.verification_hints[:3]
            bundle_used = True

            logger.debug(
                "[MAINTENANCE] Bundle for %s: conf=%.2f candidates=%d",
                task_id,
                bundle_confidence,
                len(bundle.candidate_paths),
            )
        except Exception as exc:
            logger.debug("[MAINTENANCE] Bundle build failed: %s", exc)

        # Check for blocked patterns in description
        escalation_reason = _check_blocked_patterns(description, required_skills)
        if escalation_reason:
            logger.info(
                "[MAINTENANCE] Task %s escalated: %s",
                task_id,
                escalation_reason,
            )
            # Return escalation task so supervisor can handle it
            return MaintenanceSelectionResult(
                selected_task=MaintenanceTask(
                    task_id=task_id,
                    family=family,
                    description=description,
                    source=source,
                    risk_level="high",
                    bundle_confidence=bundle_confidence,
                    execution_hints=execution_hints,
                    escalation_reason=escalation_reason,
                ),
                candidates_evaluated=candidates_evaluated,
                selection_reason="escalation_required",
                bundle_used=bundle_used,
            )

        # Select this task
        verification_method = _get_verification_method(family)
        maintenance_task = MaintenanceTask(
            task_id=task_id,
            family=family,
            description=description,
            source=source,
            risk_level=family_config["risk"],
            bundle_confidence=bundle_confidence,
            execution_hints=execution_hints,
            verification_method=verification_method,
        )

        logger.info(
            "[MAINTENANCE] Selected task %s (family=%s, risk=%s, conf=%.2f)",
            task_id,
            family,
            family_config["risk"],
            bundle_confidence,
        )

        return MaintenanceSelectionResult(
            selected_task=maintenance_task,
            candidates_evaluated=candidates_evaluated,
            selection_reason="safe_task_selected",
            bundle_used=bundle_used,
        )

    return MaintenanceSelectionResult(
        selected_task=None,
        candidates_evaluated=candidates_evaluated,
        selection_reason="no_safe_tasks_found",
        bundle_used=bundle_used,
    )


def _identify_task_family(
    source: str,
    required_skills: List[str],
    description: str,
) -> Optional[str]:
    """Identify the maintenance task family from source/skills/description.

    CRITICAL: Only returns families that have real executors in run_task.py:
    - self_audit_fix: source == "self_audit"
    - grant_review: "openclaw-grants" in required_skills
    - startup_maintenance: source == "startup_maintenance_gate"
    """
    source_lower = source.lower()

    # Check by source first (most reliable mapping to run_task.py dispatchers)
    for family, config in ALLOWED_TASK_FAMILIES.items():
        if source_lower in config["sources"]:
            return family

    # Check by required_skills (for grant_review)
    for family, config in ALLOWED_TASK_FAMILIES.items():
        if config["required_skills"] and any(
            skill in required_skills for skill in config["required_skills"]
        ):
            return family

    # No family match - task has no proven executor
    return None


def _check_blocked_patterns(
    description: str,
    required_skills: List[str],
) -> Optional[str]:
    """Check if task matches blocked patterns requiring escalation."""
    desc_lower = description.lower()

    # Source code modification signals
    if any(kw in desc_lower for kw in ["edit source", "modify code", "refactor", "rewrite"]):
        return BLOCKED_TASK_FAMILIES["source_edit"]

    # Architecture change signals
    if any(kw in desc_lower for kw in ["architecture", "redesign", "new module"]):
        return BLOCKED_TASK_FAMILIES["architecture_change"]

    # Dependency signals
    if any(kw in desc_lower for kw in ["dependency", "upgrade", "install package"]):
        return BLOCKED_TASK_FAMILIES["dependency_update"]

    # Config mutation signals
    if any(kw in desc_lower for kw in ["change config", "update env", "modify settings"]):
        return BLOCKED_TASK_FAMILIES["config_mutation"]

    return None


def _get_verification_method(family: str) -> str:
    """Get verification method for task family."""
    verification_methods = {
        "self_audit_fix": "check_audit_event_resolved",
        "grant_review": "check_task_completed_in_agentdb",
        "startup_maintenance": "check_task_completed_in_agentdb",
        "holoindex_postmerge": "check_exact_sha_completion_receipt",
    }
    return verification_methods.get(family, "check_task_completed")


def write_maintenance_report(
    result: MaintenanceSelectionResult,
    action_result: Dict[str, Any],
    verify_result: Dict[str, Any],
    repo_root: Path,
) -> Path:
    """Write structured maintenance report artifact.

    Returns:
        Path to written report file
    """
    reports_dir = (
        repo_root
        / "modules"
        / "communication"
        / "moltbot_bridge"
        / "workspace"
        / "reports"
    )
    reports_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    task_id = result.selected_task.task_id if result.selected_task else "none"
    report_name = f"maintenance_cycle_{timestamp}_{task_id[:8]}.json"
    report_path = reports_dir / report_name

    report = {
        "generated_on": datetime.now().isoformat(),
        "selection": result.to_dict(),
        "execution": {
            "ok": action_result.get("ok", False),
            "executor": action_result.get("executor", "none"),
            "execution_time_ms": action_result.get("execution_time_ms", 0),
            "detail": str(action_result.get("detail", ""))[:500],
        },
        "verification": {
            "ok": verify_result.get("ok", False),
            "fidelity": verify_result.get("fidelity", 0.0),
            "error": verify_result.get("error", ""),
        },
        "outcome": "success" if verify_result.get("ok") else "failure",
    }

    report_path.write_text(json.dumps(report, indent=2, default=str))
    logger.info("[MAINTENANCE] Report written: %s", report_path.name)

    return report_path
