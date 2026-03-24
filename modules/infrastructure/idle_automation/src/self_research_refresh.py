#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OpenClaw self-research refresh loop.

Uses existing repo surfaces to keep 0102's understanding current:
- AgentDB index freshness tracking
- HoloIndex index refresh
- WSP compliance scanning
- Daemon self-audit recurrence signals
- External opportunity and ecosystem watchlists

Outputs:
- consolidated report JSON
- autonomous task queue entries
- optional PatternMemory outcome
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import subprocess
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from holo_index.qwen_advisor.issue_mps_evaluator import IssueMPSEvaluator

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_REPORT_PATH = (
    REPO_ROOT
    / "modules"
    / "communication"
    / "moltbot_bridge"
    / "workspace"
    / "reports"
    / "openclaw_self_research_status.json"
)
GRANT_WATCHLIST_STATUS_PATH = (
    REPO_ROOT
    / "modules"
    / "communication"
    / "moltbot_bridge"
    / "workspace"
    / "reports"
    / "web3_grants_0102_watchlist_status.json"
)
PQN_RESEARCH_WATCHLIST_STATUS_PATH = (
    REPO_ROOT
    / "modules"
    / "communication"
    / "moltbot_bridge"
    / "workspace"
    / "reports"
    / "pqn_external_research_watchlist_status.json"
)
OPENCLAW_ECOSYSTEM_WATCHLIST_STATUS_PATH = (
    REPO_ROOT
    / "modules"
    / "communication"
    / "moltbot_bridge"
    / "workspace"
    / "reports"
    / "openclaw_external_ecosystem_watchlist_status.json"
)
SEVERITY_WEIGHT = {"critical": 4, "high": 3, "medium": 2, "low": 1}


def utc_now_iso() -> str:
    """Return current UTC timestamp in ISO format."""
    return datetime.now(UTC).isoformat()


def tail_text(text: str, max_chars: int = 1600) -> str:
    """Return bounded tail of subprocess output."""
    clean = (text or "").strip()
    if len(clean) <= max_chars:
        return clean
    return clean[-max_chars:]


def slugify(value: str, max_len: int = 64) -> str:
    """Create stable task ids from arbitrary text."""
    compact = "".join(ch.lower() if ch.isalnum() else "_" for ch in value)
    while "__" in compact:
        compact = compact.replace("__", "_")
    compact = compact.strip("_")
    if not compact:
        compact = "item"
    return compact[:max_len]


def priority_label(total_mps: int) -> str:
    """Map WSP 15 total score to a priority label."""
    if total_mps >= 16:
        return "P0"
    if total_mps >= 13:
        return "P1"
    if total_mps >= 10:
        return "P2"
    if total_mps >= 7:
        return "P3"
    return "P4"


def action_for_priority(priority: str) -> str:
    """Return default action guidance for a priority band."""
    if priority == "P0":
        return "Fix immediately"
    if priority == "P1":
        return "Batch within current session"
    if priority == "P2":
        return "Schedule next"
    if priority == "P3":
        return "Backlog"
    return "Reconsider later"


def manual_mps(
    complexity: int,
    importance: int,
    deferability: int,
    impact: int,
    reasoning: str,
) -> Dict[str, Any]:
    """Create a WSP 15 score bundle when IssueMPSEvaluator does not fit."""
    total = complexity + importance + deferability + impact
    priority = priority_label(total)
    return {
        "complexity": complexity,
        "importance": importance,
        "deferability": deferability,
        "impact": impact,
        "total_mps": total,
        "priority": priority,
        "action": action_for_priority(priority),
        "reasoning": reasoning,
    }


def map_violation_type_to_issue_type(violation_type: str) -> str:
    """Map WSP compliance categories onto existing issue evaluator types."""
    key = (violation_type or "").upper()
    mapping = {
        "WSP 57 - NAMING COHERENCE": "WSP_VIOLATION",
        "WSP 62 - FILE SIZE LIMIT": "SIZE_VIOLATION",
        "WSP 63 - COMPONENT COUNT": "ARCHITECTURE",
        "WSP 65 - SINGLE ORCHESTRATION": "ARCHITECTURE",
        "WSP 3 - ARCHITECTURE ORGANIZATION": "ARCHITECTURE",
        "WSP 22 - MODLOG DOCUMENTATION": "WSP_VIOLATION",
        "WSP 6 - TEST COVERAGE": "MISSING_TESTS",
        "WSP 12 - DEPENDENCY MANAGEMENT": "DEPENDENCY",
    }
    return mapping.get(key, "WSP_VIOLATION")


def group_wsp_violations(violations: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Aggregate WSP violations by type so the queue stays actionable."""
    grouped: Dict[str, Dict[str, Any]] = {}
    for violation in violations:
        violation_type = str(violation.get("violation_type", "unknown"))
        entry = grouped.setdefault(
            violation_type,
            {
                "violation_type": violation_type,
                "issue_type": map_violation_type_to_issue_type(violation_type),
                "severity": "low",
                "wsp_protocol": violation.get("wsp_protocol"),
                "count": 0,
                "descriptions": [],
                "affected_files": [],
            },
        )
        entry["count"] += 1
        entry["descriptions"].append(str(violation.get("description", "")))
        severity = str(violation.get("severity", "low")).lower()
        if SEVERITY_WEIGHT.get(severity, 0) > SEVERITY_WEIGHT.get(entry["severity"], 0):
            entry["severity"] = severity
        for file_path in violation.get("affected_files", []) or []:
            if file_path not in entry["affected_files"]:
                entry["affected_files"].append(file_path)

    groups = list(grouped.values())
    groups.sort(
        key=lambda item: (
            SEVERITY_WEIGHT.get(str(item.get("severity", "low")).lower(), 0),
            int(item.get("count", 0)),
        ),
        reverse=True,
    )
    return groups


class SelfResearchRefresher:
    """Refresh internal/external system intelligence and rank follow-up work."""

    def __init__(
        self,
        repo_root: Path | None = None,
        report_path: Path | None = None,
        origin_continuity_id: str | None = None,
    ):
        self.repo_root = Path(repo_root or REPO_ROOT).resolve()
        self.report_path = Path(report_path or DEFAULT_REPORT_PATH)
        self.evaluator = IssueMPSEvaluator()
        self.index_max_age_hours = int(os.getenv("OPENCLAW_SELF_RESEARCH_INDEX_MAX_AGE_HOURS", "6"))
        # Gateway Continuity Layer: Store origin continuity for tasks created during refresh
        self.origin_continuity_id = origin_continuity_id
        self.compliance_max_age_hours = int(
            os.getenv("OPENCLAW_SELF_RESEARCH_COMPLIANCE_MAX_AGE_HOURS", "24")
        )
        self.holo_timeout_sec = int(os.getenv("OPENCLAW_SELF_RESEARCH_HOLO_TIMEOUT_SEC", "900"))
        self.watchlist_timeout_sec = int(
            os.getenv("OPENCLAW_SELF_RESEARCH_WATCHLIST_TIMEOUT_SEC", "300")
        )
        self.max_candidates = int(os.getenv("OPENCLAW_SELF_RESEARCH_MAX_CANDIDATES", "8"))

    def load_existing_report(self) -> Dict[str, Any]:
        """Load previous self-research report if present."""
        if not self.report_path.exists():
            return {}
        try:
            return json.loads(self.report_path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    @staticmethod
    def _section_is_fresh(section: Dict[str, Any], max_age_hours: int) -> bool:
        """Return True when a report section is recent enough to reuse."""
        checked_on = section.get("checked_on") or section.get("generated_on")
        if not checked_on:
            return False
        try:
            checked = datetime.fromisoformat(str(checked_on).replace("Z", "+00:00"))
        except ValueError:
            return False
        if checked.tzinfo is None:
            checked = checked.replace(tzinfo=UTC)
        age_hours = (datetime.now(UTC) - checked).total_seconds() / 3600
        return age_hours <= max_age_hours

    def refresh_holo_index(self) -> Dict[str, Any]:
        """Refresh HoloIndex if the tracked code/WSP indexes are stale."""
        from modules.infrastructure.database.src.agent_db import AgentDB

        db = AgentDB()
        code_stale = db.should_refresh_index("code", max_age_hours=self.index_max_age_hours)
        wsp_stale = db.should_refresh_index("wsp", max_age_hours=self.index_max_age_hours)
        result: Dict[str, Any] = {
            "checked_on": utc_now_iso(),
            "index_max_age_hours": self.index_max_age_hours,
            "code_stale": code_stale,
            "wsp_stale": wsp_stale,
            "refresh_attempted": False,
            "refresh_success": False,
            "returncode": None,
            "stdout_tail": "",
            "stderr_tail": "",
        }
        if not code_stale and not wsp_stale:
            return result

        command = [sys.executable, str(self.repo_root / "holo_index.py"), "--index-all"]
        result["refresh_attempted"] = True
        try:
            completed = subprocess.run(
                command,
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                timeout=self.holo_timeout_sec,
                check=False,
            )
            result["returncode"] = completed.returncode
            result["stdout_tail"] = tail_text(completed.stdout)
            result["stderr_tail"] = tail_text(completed.stderr)
            result["refresh_success"] = completed.returncode == 0
        except Exception as exc:
            result["stderr_tail"] = f"{type(exc).__name__}: {exc}"
            result["refresh_success"] = False
        return result

    def scan_wsp_compliance(self) -> Dict[str, Any]:
        """Run the repo-wide WSP compliance scan and summarize it."""
        from modules.infrastructure.wsp_core.src.wsp_compliance_checker import (
            WSPComplianceChecker,
        )

        checker = WSPComplianceChecker(project_root=self.repo_root)
        violations = asyncio.run(checker.scan())
        violation_rows: List[Dict[str, Any]] = []
        for violation in violations:
            violation_rows.append(
                {
                    "violation_type": violation.violation_type.value,
                    "description": violation.description,
                    "severity": violation.severity,
                    "wsp_protocol": violation.wsp_protocol,
                    "affected_files": violation.affected_files,
                    "auto_fixable": violation.auto_fixable,
                }
            )

        groups = group_wsp_violations(violation_rows)
        return {
            "checked_on": utc_now_iso(),
            "violation_count": len(violation_rows),
            "top_violation_groups": groups[:5],
            "violations": violation_rows[:25],
        }

    def scan_self_audit(self) -> Dict[str, Any]:
        """Sample the daemon self-audit loop and summarize recurring signatures."""
        from modules.infrastructure.wre_core.src.daemon_self_audit_loop import (
            DaemonSelfAuditLoop,
        )

        audit = DaemonSelfAuditLoop(self.repo_root)
        opened = audit.scan_once()
        state_path = audit.state_path
        state: Dict[str, Any] = {}
        if state_path.exists():
            try:
                state = json.loads(state_path.read_text(encoding="utf-8"))
            except Exception:
                state = {}

        signature_stats = state.get("signature_stats", {}) or {}
        top_signatures = []
        for signature, raw in signature_stats.items():
            top_signatures.append(
                {
                    "signature": signature,
                    "count": int(raw.get("count", 0)),
                    "recommended_fix": raw.get("recommended_fix", ""),
                    "last_fix_result": raw.get("last_fix_result", ""),
                    "last_seen": raw.get("last_seen"),
                }
            )
        top_signatures.sort(key=lambda item: item["count"], reverse=True)
        return {
            "checked_on": utc_now_iso(),
            "events_opened": opened,
            "signature_count": len(signature_stats),
            "top_signatures": top_signatures[:5],
        }

    def refresh_grant_watchlist(self) -> Dict[str, Any]:
        """Refresh the existing grant watchlist script and load its status snapshot."""
        return self._refresh_watchlist(
            script_name="refresh_grant_watchlist.py",
            status_path=GRANT_WATCHLIST_STATUS_PATH,
        )

    def refresh_pqn_research_watchlist(self) -> Dict[str, Any]:
        """Refresh the PQN external research watchlist and load its status snapshot."""
        return self._refresh_watchlist(
            script_name="refresh_pqn_research_watchlist.py",
            status_path=PQN_RESEARCH_WATCHLIST_STATUS_PATH,
        )

    def refresh_openclaw_ecosystem_watchlist(self) -> Dict[str, Any]:
        """Refresh the OpenClaw external ecosystem watchlist and load its status snapshot."""
        return self._refresh_watchlist(
            script_name="refresh_openclaw_ecosystem_watchlist.py",
            status_path=OPENCLAW_ECOSYSTEM_WATCHLIST_STATUS_PATH,
        )

    def _refresh_watchlist(self, *, script_name: str, status_path: Path) -> Dict[str, Any]:
        """Run a watchlist refresh script and load its status snapshot."""
        command = [sys.executable, str(self.repo_root / "scripts" / script_name)]
        result: Dict[str, Any] = {
            "checked_on": utc_now_iso(),
            "refresh_attempted": True,
            "refresh_success": False,
            "returncode": None,
            "stdout_tail": "",
            "stderr_tail": "",
            "status": {},
        }
        try:
            completed = subprocess.run(
                command,
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                timeout=self.watchlist_timeout_sec,
                check=False,
            )
            result["returncode"] = completed.returncode
            result["stdout_tail"] = tail_text(completed.stdout)
            result["stderr_tail"] = tail_text(completed.stderr)
            result["refresh_success"] = completed.returncode == 0
        except Exception as exc:
            result["stderr_tail"] = f"{type(exc).__name__}: {exc}"

        if status_path.exists():
            try:
                result["status"] = json.loads(status_path.read_text(encoding="utf-8"))
            except Exception as exc:
                result["status"] = {"error": f"status_read_failed: {exc}"}
        return result

    def _build_issue_candidate(
        self,
        *,
        source: str,
        title: str,
        description: str,
        issue_type: str,
        confidence: float,
        required_skills: List[str],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        evaluation = self.evaluator.evaluate_issue(issue_type, description, confidence=confidence)
        return {
            "task_id": f"self_research_{source}_{slugify(title)}",
            "source": source,
            "title": title,
            "description": description,
            "required_skills": required_skills,
            "context": context,
            "mps": {
                "complexity": evaluation.complexity_score,
                "importance": evaluation.importance_score,
                "deferability": evaluation.deferability_score,
                "impact": evaluation.impact_score,
                "total_mps": evaluation.total_mps,
                "priority": evaluation.priority.value,
                "action": evaluation.action,
                "reasoning": evaluation.reasoning,
            },
            "priority_score": float(evaluation.total_mps),
        }

    def _build_manual_candidate(
        self,
        *,
        source: str,
        title: str,
        description: str,
        required_skills: List[str],
        context: Dict[str, Any],
        complexity: int,
        importance: int,
        deferability: int,
        impact: int,
        reasoning: str,
        stable_task_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        score = manual_mps(complexity, importance, deferability, impact, reasoning)
        task_id = stable_task_id or f"self_research_{source}_{slugify(title)}"
        return {
            "task_id": task_id,
            "source": source,
            "title": title,
            "description": description,
            "required_skills": required_skills,
            "context": context,
            "mps": score,
            "priority_score": float(score["total_mps"]),
        }

    @staticmethod
    def _issue_type_for_self_audit(signature: str, recommended_fix: str) -> str:
        fix = (recommended_fix or "").strip().lower()
        signature_lower = (signature or "").strip().lower()
        if fix == "verify_dae_event_store" or "unique constraint failed" in signature_lower:
            return "ARCHITECTURE"
        if fix in {"start_ironclaw_gateway", "diagnose_microphone_device"}:
            return "DEPENDENCY"
        return "DEPENDENCY"

    def build_update_candidates(
        self,
        *,
        holo_index: Dict[str, Any],
        compliance: Dict[str, Any],
        self_audit: Dict[str, Any],
        grant_watchlist: Dict[str, Any],
        pqn_research_watchlist: Optional[Dict[str, Any]] = None,
        openclaw_ecosystem_watchlist: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Convert raw refresh signals into a ranked WSP 15 task queue."""
        candidates: List[Dict[str, Any]] = []

        if holo_index.get("refresh_attempted") and not holo_index.get("refresh_success"):
            candidates.append(
                self._build_issue_candidate(
                    source="holo_index",
                    title="restore HoloIndex refresh path",
                    description="HoloIndex index refresh failed; repo memory may be stale.",
                    issue_type="DEPENDENCY",
                    confidence=0.98,
                    required_skills=["holo-search", "openclaw-monitor"],
                    context={"holo_index": holo_index},
                )
            )

        for group in compliance.get("top_violation_groups", [])[:3]:
            files = group.get("affected_files", [])[:5]
            candidates.append(
                self._build_issue_candidate(
                    source="wsp_compliance",
                    title=f"reduce {group['violation_type']} ({group['count']} finding(s))",
                    description=group["descriptions"][0] if group.get("descriptions") else group["violation_type"],
                    issue_type=str(group.get("issue_type", "WSP_VIOLATION")),
                    confidence=0.95 if group.get("severity") in {"critical", "high"} else 0.85,
                    required_skills=["holo-search", "openclaw-monitor"],
                    context={
                        "violation_type": group.get("violation_type"),
                        "severity": group.get("severity"),
                        "count": group.get("count"),
                        "affected_files": files,
                    },
                )
            )

        for item in self_audit.get("top_signatures", [])[:3]:
            if int(item.get("count", 0)) <= 0:
                continue
            signature = str(item.get("signature", ""))
            recommended_fix = str(item.get("recommended_fix", ""))
            candidates.append(
                self._build_issue_candidate(
                    source="self_audit",
                    title=f"resolve recurring daemon error ({recommended_fix or 'inspect'})",
                    description=signature,
                    issue_type=self._issue_type_for_self_audit(signature, recommended_fix),
                    confidence=0.90,
                    required_skills=["openclaw-monitor"],
                    context=item,
                )
            )

        watchlist_status = grant_watchlist.get("status", {}) or {}
        changed_count = int(watchlist_status.get("changed_count", 0) or 0)
        error_count = int(watchlist_status.get("error_count", 0) or 0)
        if changed_count > 0:
            candidates.append(
                self._build_manual_candidate(
                    source="external_watchlist",
                    title=f"review {changed_count} changed grant opportunity page(s)",
                    description="External funding sources changed and need repo-fit review before 0102 applies next.",
                    required_skills=["openclaw-grants", "openclaw-monitor"],
                    context={
                        "changed_count": changed_count,
                        "changed_items": watchlist_status.get("changed_items", []),
                    },
                    complexity=2,
                    importance=4,
                    deferability=4,
                    impact=4,
                    reasoning="External opportunities changed; quick review yields near-term funding leverage.",
                    stable_task_id="grant_watchlist_review",
                )
            )

        if error_count > 0:
            candidates.append(
                self._build_manual_candidate(
                    source="external_watchlist",
                    title=f"stabilize {error_count} watchlist refresh error(s)",
                    description="Official-source opportunity refresh is degraded and may miss new grant windows.",
                    required_skills=["openclaw-grants", "openclaw-monitor"],
                    context={
                        "error_count": error_count,
                        "error_items": watchlist_status.get("error_items", []),
                    },
                    complexity=2,
                    importance=3,
                    deferability=3,
                    impact=3,
                    reasoning="Watchlist fetch failures reduce external awareness but are usually quick to harden.",
                    stable_task_id="grant_watchlist_stabilize",
                )
            )

        pqn_watchlist_status = (pqn_research_watchlist or {}).get("status", {}) or {}
        pqn_changed_count = int(pqn_watchlist_status.get("changed_count", 0) or 0)
        pqn_error_count = int(pqn_watchlist_status.get("error_count", 0) or 0)
        if pqn_changed_count > 0:
            candidates.append(
                self._build_manual_candidate(
                    source="pqn_external_watchlist",
                    title=f"review {pqn_changed_count} changed PQN external research page(s)",
                    description=(
                        "External PQN-adjacent research systems changed and need WSP 97 "
                        "repo-fit review before adoption guidance changes."
                    ),
                    required_skills=["pqn-research", "openclaw-monitor"],
                    context={
                        "changed_count": pqn_changed_count,
                        "changed_items": pqn_watchlist_status.get("changed_items", []),
                    },
                    complexity=2,
                    importance=3,
                    deferability=3,
                    impact=4,
                    reasoning=(
                        "External research tooling drift can change adoption guidance and "
                        "benchmark positioning for PQN work."
                    ),
                    stable_task_id="pqn_watchlist_review",
                )
            )

        if pqn_error_count > 0:
            candidates.append(
                self._build_manual_candidate(
                    source="pqn_external_watchlist",
                    title=f"stabilize {pqn_error_count} PQN external watchlist refresh error(s)",
                    description=(
                        "PQN external research monitoring is degraded and may miss changes in "
                        "benchmark repos such as Get Physics Done."
                    ),
                    required_skills=["pqn-research", "openclaw-monitor"],
                    context={
                        "error_count": pqn_error_count,
                        "error_items": pqn_watchlist_status.get("error_items", []),
                    },
                    complexity=2,
                    importance=2,
                    deferability=3,
                    impact=3,
                    reasoning=(
                        "External benchmark monitoring should stay healthy but is less urgent "
                        "than direct system or funding path failures."
                    ),
                    stable_task_id="pqn_watchlist_stabilize",
                )
            )

        ecosystem_watchlist_status = (openclaw_ecosystem_watchlist or {}).get("status", {}) or {}
        ecosystem_changed_count = int(ecosystem_watchlist_status.get("changed_count", 0) or 0)
        ecosystem_error_count = int(ecosystem_watchlist_status.get("error_count", 0) or 0)
        if ecosystem_changed_count > 0:
            candidates.append(
                self._build_manual_candidate(
                    source="openclaw_ecosystem_watchlist",
                    title=f"review {ecosystem_changed_count} changed OpenClaw ecosystem signal(s)",
                    description=(
                        "External agent-infrastructure systems changed and need WSP 97 repo-fit "
                        "review before OpenClaw memory, context, or orchestration guidance changes."
                    ),
                    required_skills=["openclaw-monitor", "holo-search"],
                    context={
                        "changed_count": ecosystem_changed_count,
                        "changed_items": ecosystem_watchlist_status.get("changed_items", []),
                    },
                    complexity=2,
                    importance=4,
                    deferability=3,
                    impact=4,
                    reasoning=(
                        "Context and memory infrastructure shifts can materially change the "
                        "OpenClaw roadmap, but should still be gated through WSP 97 review."
                    ),
                    stable_task_id="openclaw_ecosystem_watchlist_review",
                )
            )

        if ecosystem_error_count > 0:
            candidates.append(
                self._build_manual_candidate(
                    source="openclaw_ecosystem_watchlist",
                    title=f"stabilize {ecosystem_error_count} OpenClaw ecosystem watchlist error(s)",
                    description=(
                        "OpenClaw external ecosystem monitoring is degraded and may miss "
                        "important infrastructure changes such as OpenViking updates."
                    ),
                    required_skills=["openclaw-monitor"],
                    context={
                        "error_count": ecosystem_error_count,
                        "error_items": ecosystem_watchlist_status.get("error_items", []),
                    },
                    complexity=2,
                    importance=3,
                    deferability=3,
                    impact=3,
                    reasoning=(
                        "Ecosystem drift monitoring should stay healthy so architecture "
                        "decisions are based on current upstream reality."
                    ),
                    stable_task_id="openclaw_ecosystem_watchlist_stabilize",
                )
            )

        candidates.sort(
            key=lambda item: (
                int(item["mps"]["total_mps"]),
                1 if item["source"] == "self_audit" else 0,
            ),
            reverse=True,
        )
        return candidates[: self.max_candidates]

    def publish_autonomous_tasks(self, candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Write ranked candidates into the existing AgentDB autonomous queue.

        Grant tasks use stable task_ids (grant_watchlist_review, grant_watchlist_stabilize)
        to prevent duplicate accumulation and enable deterministic dispatch.

        Completed stable grant tasks are NOT reopened unless context materially changed.
        """
        from modules.infrastructure.database.src.agent_db import AgentDB

        db = AgentDB()

        # Clean up stale slugified GRANT tasks only (not PQN/ecosystem watchlist tasks)
        # Precision filter:
        #   1. task_id LIKE 'self_research_external_watchlist_%' (old slugified pattern)
        #   2. required_skills contains 'openclaw-grants' (grant-specific skill)
        #   3. task_id NOT IN stable IDs (preserve new stable tasks)
        stable_grant_task_ids = {"grant_watchlist_review", "grant_watchlist_stabilize"}
        candidate_task_ids = {c["task_id"] for c in candidates}
        if candidate_task_ids & stable_grant_task_ids:
            try:
                db.db.execute_write(
                    """
                    DELETE FROM agents_autonomous_tasks
                    WHERE status IN ('pending', 'failed', NULL, '')
                      AND task_id LIKE 'self_research_external_watchlist_%'
                      AND required_skills LIKE '%openclaw-grants%'
                      AND task_id NOT IN (?, ?)
                    """,
                    ("grant_watchlist_review", "grant_watchlist_stabilize"),
                )
            except Exception as exc:
                logger.debug("Stale grant task cleanup skipped: %s", exc)

        # Check which stable grant tasks are already completed
        completed_stable_grants = set()
        for task_id in stable_grant_task_ids:
            try:
                rows = db.db.execute_query(
                    "SELECT status, context FROM agents_autonomous_tasks WHERE task_id = ?",
                    (task_id,),
                )
                if rows and rows[0].get("status") == "completed":
                    completed_stable_grants.add(task_id)
            except Exception:
                pass  # Table may not exist yet

        published: List[Dict[str, Any]] = []
        for candidate in candidates:
            task_id = candidate["task_id"]

            # Skip republishing completed stable grant tasks unless context changed
            if task_id in completed_stable_grants:
                # Check if context materially changed (different items)
                try:
                    rows = db.db.execute_query(
                        "SELECT context FROM agents_autonomous_tasks WHERE task_id = ?",
                        (task_id,),
                    )
                    if rows:
                        import json as _json
                        old_ctx = rows[0].get("context")
                        if isinstance(old_ctx, str):
                            old_ctx = _json.loads(old_ctx)
                        old_items = set((old_ctx or {}).get("context", {}).get("changed_items", []) +
                                        (old_ctx or {}).get("context", {}).get("error_items", []))
                        new_items = set(candidate.get("context", {}).get("changed_items", []) +
                                        candidate.get("context", {}).get("error_items", []))
                        if old_items == new_items:
                            # Same context, don't reopen
                            published.append({
                                "task_id": task_id,
                                "title": candidate["title"],
                                "created": False,
                                "priority": candidate["mps"]["priority"],
                                "skipped_reason": "completed_same_context",
                            })
                            continue
                except Exception:
                    pass  # If we can't compare, proceed with republish

            created = db.create_autonomous_task(
                task_id=task_id,
                description=candidate["description"],
                required_skills=candidate["required_skills"],
                estimated_complexity=float(candidate["mps"]["complexity"]),
                priority_score=float(candidate["priority_score"]),
                context={
                    "source": candidate["source"],
                    "title": candidate["title"],
                    "mps": candidate["mps"],
                    "context": candidate["context"],
                },
                origin_continuity_id=self.origin_continuity_id,
            )
            # Ensure status is set to 'pending' only for new tasks (don't reset completed)
            if created and task_id not in completed_stable_grants:
                try:
                    db.db.execute_write(
                        "UPDATE agents_autonomous_tasks SET status = 'pending' WHERE task_id = ? AND status IS NULL",
                        (task_id,),
                    )
                except Exception:
                    pass  # Status column may already be set or have a default

            published.append(
                {
                    "task_id": task_id,
                    "title": candidate["title"],
                    "created": bool(created),
                    "priority": candidate["mps"]["priority"],
                }
            )
        return published

    def remember_outcome(self, report: Dict[str, Any], duration_ms: int) -> None:
        """Persist one summary outcome into PatternMemory for recall."""
        try:
            from modules.infrastructure.wre_core.src.pattern_memory import (
                PatternMemory,
                SkillOutcome,
            )

            outcome = SkillOutcome(
                execution_id=f"self_research_{uuid.uuid4().hex[:12]}",
                skill_name="self_research_refresh",
                agent="openclaw_self_research",
                timestamp=utc_now_iso(),
                input_context=json.dumps(
                    {
                        "index_max_age_hours": self.index_max_age_hours,
                        "max_candidates": self.max_candidates,
                    },
                    ensure_ascii=True,
                ),
                output_result=json.dumps(
                    {
                        "candidate_count": len(report.get("update_candidates", [])),
                        "task_count": len(report.get("autonomous_tasks", [])),
                        "top_priorities": [
                            item["mps"]["priority"] for item in report.get("update_candidates", [])[:3]
                        ],
                    },
                    ensure_ascii=True,
                ),
                success=True,
                pattern_fidelity=1.0,
                outcome_quality=1.0,
                execution_time_ms=duration_ms,
                step_count=4,
                notes=f"report={self.report_path}",
            )
            PatternMemory().store_outcome(outcome)
        except Exception as exc:
            logger.debug("PatternMemory outcome store skipped: %s", exc)

    def run(
        self,
        *,
        run_holo_refresh: bool = True,
        run_compliance: bool = True,
        run_self_audit: bool = True,
        run_watchlists: bool = True,
        write_tasks: bool = True,
        remember_outcome: bool = True,
        emit_nudges: bool = True,
        force_compliance: bool = False,
    ) -> Dict[str, Any]:
        """Execute a full self-research cycle and write the consolidated report."""
        start = datetime.now(UTC)
        previous_report = self.load_existing_report()
        holo_index = {"skipped": True}
        compliance = {"skipped": True}
        self_audit = {"skipped": True}
        grant_watchlist = {"skipped": True}
        pqn_research_watchlist = {"skipped": True}
        openclaw_ecosystem_watchlist = {"skipped": True}

        if run_holo_refresh:
            holo_index = self.refresh_holo_index()
        if run_compliance:
            cached_compliance = previous_report.get("wsp_compliance", {}) or {}
            if (
                not force_compliance
                and cached_compliance
                and self._section_is_fresh(cached_compliance, self.compliance_max_age_hours)
            ):
                compliance = dict(cached_compliance)
                compliance["cached"] = True
            else:
                compliance = self.scan_wsp_compliance()
                compliance["cached"] = False
        if run_self_audit:
            self_audit = self.scan_self_audit()
        if run_watchlists:
            grant_watchlist = self.refresh_grant_watchlist()
            pqn_research_watchlist = self.refresh_pqn_research_watchlist()
            openclaw_ecosystem_watchlist = self.refresh_openclaw_ecosystem_watchlist()

        candidates = self.build_update_candidates(
            holo_index=holo_index,
            compliance=compliance,
            self_audit=self_audit,
            grant_watchlist=grant_watchlist,
            pqn_research_watchlist=pqn_research_watchlist,
            openclaw_ecosystem_watchlist=openclaw_ecosystem_watchlist,
        )
        published = self.publish_autonomous_tasks(candidates) if write_tasks else []

        report = {
            "generated_on": utc_now_iso(),
            "repo_root": str(self.repo_root),
            "holo_index": holo_index,
            "wsp_compliance": compliance,
            "self_audit": self_audit,
            "grant_watchlist": grant_watchlist,
            "pqn_research_watchlist": pqn_research_watchlist,
            "openclaw_ecosystem_watchlist": openclaw_ecosystem_watchlist,
            "update_candidates": candidates,
            "autonomous_tasks": published,
            "next_actions": [item["title"] for item in candidates[:3]],
        }

        self.report_path.parent.mkdir(parents=True, exist_ok=True)
        self.report_path.write_text(
            json.dumps(report, indent=2, ensure_ascii=True) + "\n",
            encoding="utf-8",
        )

        duration_ms = int((datetime.now(UTC) - start).total_seconds() * 1000)
        report["duration_ms"] = duration_ms
        self.report_path.write_text(
            json.dumps(report, indent=2, ensure_ascii=True) + "\n",
            encoding="utf-8",
        )

        # Emit memory nudges for high-value events detected in fresh reports
        nudge_paths: List[Path] = []
        if emit_nudges:
            nudge_paths = self._emit_memory_nudges()
            report["memory_nudges_emitted"] = len(nudge_paths)
            # Re-write report with nudge count included
            self.report_path.write_text(
                json.dumps(report, indent=2, ensure_ascii=True) + "\n",
                encoding="utf-8",
            )

        if remember_outcome:
            self.remember_outcome(report, duration_ms)
        return report

    def _emit_memory_nudges(self) -> List[Path]:
        """Emit memory nudges and record breadcrumbs."""
        try:
            from modules.communication.moltbot_bridge.src.memory_nudge_engine import (
                emit_memory_nudges,
            )

            nudge_paths = emit_memory_nudges(
                repo_root=self.repo_root,
                record_breadcrumbs=True,
            )
            if nudge_paths:
                logger.info(
                    "[SELF-RESEARCH] Emitted %d memory nudge(s): %s",
                    len(nudge_paths),
                    [p.name for p in nudge_paths],
                )
            return nudge_paths
        except ImportError as exc:
            logger.debug("Memory nudge engine not available: %s", exc)
            return []
        except Exception as exc:
            logger.warning("Failed to emit memory nudges: %s", exc)
            return []


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entry point for the self-research refresh loop."""
    parser = argparse.ArgumentParser(description="Refresh OpenClaw self-research status.")
    parser.add_argument("--report-out", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--no-holo-refresh", action="store_true")
    parser.add_argument("--no-compliance", action="store_true")
    parser.add_argument("--no-self-audit", action="store_true")
    parser.add_argument("--no-watchlists", action="store_true")
    parser.add_argument("--no-tasks", action="store_true")
    parser.add_argument("--no-memory", action="store_true")
    parser.add_argument("--no-nudges", action="store_true", help="Skip memory nudge emission")
    parser.add_argument("--force-compliance", action="store_true")
    args = parser.parse_args(argv)

    refresher = SelfResearchRefresher(report_path=args.report_out)
    report = refresher.run(
        run_holo_refresh=not args.no_holo_refresh,
        run_compliance=not args.no_compliance,
        run_self_audit=not args.no_self_audit,
        run_watchlists=not args.no_watchlists,
        write_tasks=not args.no_tasks,
        remember_outcome=not args.no_memory,
        emit_nudges=not args.no_nudges,
        force_compliance=args.force_compliance,
    )

    print(f"[OK] Self-research report written to {args.report_out}")
    print(f"[OK] Update candidates: {len(report.get('update_candidates', []))}")
    print(f"[OK] Autonomous tasks published: {len(report.get('autonomous_tasks', []))}")
    print(f"[OK] Memory nudges emitted: {report.get('memory_nudges_emitted', 0)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
