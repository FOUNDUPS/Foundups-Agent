#!/usr/bin/env python3
"""
MCP Bridge Signal Normalization and State Compression.

Compresses raw overseer channels into actionable state intelligence.

Tools:
- get_overseer_summary: Compressed situational awareness
- get_hot_modules: Volatility-ranked module list
- get_repeated_failures: Clustered recurring failures
- get_active_risks: Normalized risk objects
- get_recommended_focus: Prioritized next actions
- get_prompt_context_packet: Auto-assembled prompt context

WSP References:
- WSP 97: System Execution Prompting Protocol
- WSP 48: Recursive Self-Improvement (pattern memory)
- WSP 77: Agent Coordination
"""

from __future__ import annotations

import logging
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from .response_schema import ok_response, error_response

logger = logging.getLogger(__name__)

# Import existing tools for data sourcing
from . import overseer_tools
from . import diff_tools
from . import holo_tools
from . import impact_scoring
from . import dependency_tools

# Reuse critical modules from impact_scoring
CRITICAL_MODULES = impact_scoring.CRITICAL_MODULES

# Risk type taxonomy
RISK_TYPES = {
    "regression_risk": "Risk of breaking existing functionality",
    "coordination_risk": "Risk from multi-agent or cross-module coordination",
    "dependency_risk": "Risk from module dependency chains",
    "repeated_failure_risk": "Risk from recurring failure patterns",
    "drift_risk": "Risk from state or architecture drift",
    "context_gap_risk": "Risk from incomplete information",
}

# Severity levels
SEVERITY_LEVELS = ["low", "medium", "high", "critical"]


# =============================================================================
# Tool 1: Overseer Summary
# =============================================================================


def get_overseer_summary(repo_root: Path) -> Dict[str, Any]:
    """
    Get compressed overseer situational awareness.

    Args:
        repo_root: Repository root path

    Returns:
        MCPResponse with compressed summary
    """
    sources_used = []
    confidence = 0.3  # Base confidence

    summary = {
        "top_concerns": [],
        "mission_activity": {},
        "failure_clusters": [],
        "hot_modules": [],
        "system_posture": "unknown",
        "recommended_focus": [],
    }

    # Source 1: Overseer status
    status = overseer_tools.get_overseer_status(repo_root)
    if status.get("status") == "ok":
        sources_used.append("overseer_status")
        confidence += 0.1

        status_data = _get_data(status)
        summary["system_posture"] = _determine_system_posture(status_data)

        if isinstance(status_data.get("wsp_audit_status"), dict):
            audit = status_data["wsp_audit_status"]
            if isinstance(audit, dict) and audit.get("drift_count", 0) > 0:
                summary["top_concerns"].append({
                    "type": "drift_risk",
                    "summary": f"WSP drift detected: {audit['drift_count']} issues",
                    "severity": _normalize_severity(audit.get("severity", "medium")),
                })

    # Source 2: Mission history
    missions = overseer_tools.get_mission_history(repo_root, limit=20)
    if missions.get("status") == "ok":
        sources_used.append("mission_history")
        confidence += 0.1

        mission_list = _get_data(missions).get("missions", [])
        summary["mission_activity"] = _summarize_mission_activity(mission_list)

        # Check for failed missions
        failed = [m for m in mission_list if m.get("status") == "failed"]
        if failed:
            summary["top_concerns"].append({
                "type": "coordination_risk",
                "summary": f"{len(failed)} failed missions in recent history",
                "severity": "medium" if len(failed) < 3 else "high",
            })

    # Source 3: Failure patterns
    failures = overseer_tools.get_known_failure_patterns(repo_root, limit=30)
    if failures.get("status") == "ok":
        sources_used.append("failure_patterns")
        confidence += 0.1

        failure_list = _get_data(failures).get("failures", [])
        summary["failure_clusters"] = _cluster_failures(failure_list)[:5]

        if len(failure_list) > 10:
            summary["top_concerns"].append({
                "type": "repeated_failure_risk",
                "summary": f"{len(failure_list)} known failure patterns",
                "severity": "medium",
            })

    # Source 4: Hot modules (computed)
    hot_result = get_hot_modules(repo_root, limit=5)
    if hot_result.get("status") == "ok":
        sources_used.append("hot_modules")
        confidence += 0.1
        summary["hot_modules"] = _get_data(hot_result).get("modules", [])[:5]

    # Source 5: Recommended focus (computed)
    focus_result = get_recommended_focus(repo_root, limit=5)
    if focus_result.get("status") == "ok":
        sources_used.append("recommended_focus")
        confidence += 0.1
        summary["recommended_focus"] = _get_data(focus_result).get("focus_items", [])[:5]

    # Sort concerns by severity
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    summary["top_concerns"].sort(
        key=lambda x: severity_order.get(x.get("severity", "low"), 4)
    )
    summary["top_concerns"] = summary["top_concerns"][:10]

    # Cap confidence
    confidence = min(confidence, 0.9)

    return ok_response(
        summary,
        source="signal_normalization",
        tool="get_overseer_summary",
        confidence=confidence,
        sources_used=sources_used,
    )


def _get_data(response: Any) -> Dict[str, Any]:
    """Safely extract data dict from tool response envelope."""
    if isinstance(response, dict):
        data = response.get("data")
        if isinstance(data, dict):
            return data
    return {}


def _determine_system_posture(status_data: Dict) -> str:
    """Determine overall system posture from status data."""
    if not status_data.get("available"):
        return "degraded"

    audit = status_data.get("wsp_audit_status") or {}
    if audit.get("severity") == "critical":
        return "critical"
    if audit.get("drift_count", 0) > 5:
        return "drifting"
    if not status_data.get("security_monitor_active"):
        return "unmonitored"

    return "stable"


def _summarize_mission_activity(missions: List[Dict]) -> Dict:
    """Summarize mission activity."""
    if not missions:
        return {"total": 0, "recent_count": 0}

    status_counts = Counter(m.get("status", "unknown") for m in missions)
    type_counts = Counter(m.get("mission_type", "unknown") for m in missions)

    return {
        "total": len(missions),
        "by_status": dict(status_counts),
        "by_type": dict(type_counts.most_common(5)),
        "completion_rate": status_counts.get("completed", 0) / max(len(missions), 1),
    }


def _cluster_failures(failures: List[Dict]) -> List[Dict]:
    """Cluster similar failures."""
    clusters = defaultdict(list)

    for f in failures:
        # Create a signature for clustering
        sig_parts = []
        if f.get("type"):
            sig_parts.append(f["type"])
        if f.get("_category"):
            sig_parts.append(f["_category"])
        if f.get("signature"):
            sig_parts.append(f["signature"][:50])

        sig = ":".join(sig_parts) if sig_parts else "unknown"
        clusters[sig].append(f)

    # Convert to list format
    result = []
    for sig, items in clusters.items():
        result.append({
            "cluster_signature": sig,
            "count": len(items),
            "samples": items[:3],
            "severity": _infer_failure_severity(items),
        })

    # Sort by count descending
    result.sort(key=lambda x: x["count"], reverse=True)
    return result


def _normalize_severity(sev: Any) -> str:
    """Normalize arbitrary severity strings to standard taxonomy."""
    s = str(sev).lower().strip()
    if s in ("critical", "fatal"):
        return "critical"
    if s in ("high", "error"):
        return "high"
    if s in ("medium", "warning", "warn"):
        return "medium"
    return "low"


def _infer_failure_severity(failures: List[Dict]) -> str:
    """Infer severity from failure list."""
    for f in failures:
        if f.get("severity") == "critical":
            return "critical"
        if f.get("type") == "incident":
            return "high"
    if len(failures) > 5:
        return "medium"
    return "low"


# =============================================================================
# Tool 2: Hot Modules
# =============================================================================


def get_hot_modules(repo_root: Path, limit: int = 10) -> Dict[str, Any]:
    """
    Get modules ranked by recent volatility/risk.

    Args:
        repo_root: Repository root path
        limit: Maximum modules to return

    Returns:
        MCPResponse with ranked modules
    """
    sources_used = []
    confidence = 0.3
    module_scores: Dict[str, Dict] = defaultdict(lambda: {
        "score": 0.0,
        "factors": [],
        "change_count": 0,
        "failure_count": 0,
        "dependency_count": 0,
        "is_critical": False,
    })

    # Factor 1: Recent change frequency (from diff)
    diff_result = diff_tools.get_diff_summary(
        repo_root, commit_range="HEAD~20..HEAD", group_by_module=True
    )
    if diff_result.get("status") == "ok":
        sources_used.append("recent_changes")
        confidence += 0.15

        grouped = _get_data(diff_result).get("grouped_by_module", {})
        for module_key, files in grouped.items():
            module = _extract_module_name(module_key)
            if module:
                change_count = len(files) if isinstance(files, list) else 0
                module_scores[module]["change_count"] = change_count
                module_scores[module]["score"] += change_count * 0.1
                if change_count > 0:
                    module_scores[module]["factors"].append(
                        f"changed_files:{change_count}"
                    )

    # Factor 2: Critical module status
    for module in list(module_scores.keys()):
        if module in CRITICAL_MODULES:
            multiplier = CRITICAL_MODULES[module]
            module_scores[module]["is_critical"] = True
            module_scores[module]["score"] *= multiplier
            module_scores[module]["factors"].append(f"critical:{multiplier}x")

    # Factor 3: Failure association
    failures = overseer_tools.get_known_failure_patterns(repo_root, limit=50)
    if failures.get("status") == "ok":
        sources_used.append("failure_patterns")
        confidence += 0.1

        for f in _get_data(failures).get("failures", []):
            # Try to extract module from failure
            module = _extract_module_from_failure(f)
            if module:
                module_scores[module]["failure_count"] += 1
                module_scores[module]["score"] += 0.2
                if module_scores[module]["failure_count"] == 1:
                    module_scores[module]["factors"].append("has_failures")

    # Factor 4: Dependency centrality (reverse deps)
    for module in list(module_scores.keys()):
        rdeps = dependency_tools.get_reverse_dependencies(repo_root, module_name=module)
        if rdeps.get("status") == "ok":
            dep_count = _get_data(rdeps).get("dependent_count", 0)
            module_scores[module]["dependency_count"] = dep_count
            if dep_count > 3:
                module_scores[module]["score"] += dep_count * 0.05
                module_scores[module]["factors"].append(f"dependents:{dep_count}")

    if module_scores:
        sources_used.append("dependency_analysis")
        confidence += 0.1

    # Rank and format
    ranked = []
    for module, data in module_scores.items():
        if data["score"] > 0:
            ranked.append({
                "module": module,
                "heat_score": round(data["score"], 2),
                "factors": data["factors"],
                "change_count": data["change_count"],
                "failure_count": data["failure_count"],
                "dependency_count": data["dependency_count"],
                "is_critical": data["is_critical"],
            })

    ranked.sort(key=lambda x: x["heat_score"], reverse=True)

    confidence = min(confidence, 0.85)

    return ok_response(
        {
            "modules": ranked[:limit],
            "total_scored": len(ranked),
            "scoring_note": "heat_score is a heuristic combining change frequency, criticality, failures, and dependencies",
        },
        source="signal_normalization",
        tool="get_hot_modules",
        confidence=confidence,
        sources_used=sources_used,
    )


def _extract_module_name(module_key: str) -> Optional[str]:
    """Extract module name from grouped key like 'infrastructure/ai_overseer'."""
    if "/" in module_key:
        parts = module_key.split("/")
        return parts[-1] if parts else None
    return module_key if module_key not in ("root", "docs", "wsp_framework") else None


def _extract_module_from_failure(failure: Dict) -> Optional[str]:
    """Try to extract module name from failure dict."""
    # Check source_file
    if failure.get("source_file"):
        match = re.search(r"modules/[^/]+/([^/]+)", failure["source_file"])
        if match:
            return match.group(1)
    # Check signature
    if failure.get("signature"):
        match = re.search(r"modules/[^/]+/([^/]+)", failure["signature"])
        if match:
            return match.group(1)
    return None


# =============================================================================
# Tool 3: Repeated Failures
# =============================================================================


def get_repeated_failures(repo_root: Path, limit: int = 10) -> Dict[str, Any]:
    """
    Get recurring failure patterns, clustered and deduplicated.

    Args:
        repo_root: Repository root path
        limit: Maximum clusters to return

    Returns:
        MCPResponse with clustered failures
    """
    sources_used = []
    confidence = 0.4
    all_failures = []

    # Source 1: Known failure patterns
    failures = overseer_tools.get_known_failure_patterns(repo_root, limit=50)
    if failures.get("status") == "ok":
        sources_used.append("known_failures")
        confidence += 0.15
        all_failures.extend(_get_data(failures).get("failures", []))

    # Source 2: HoloIndex failure memory
    holo_failures = holo_tools.holo_failure_memory(repo_root, query="error failure", limit=30)
    if holo_failures.get("status") == "ok":
        sources_used.append("holo_failure_memory")
        confidence += 0.1
        for f in _get_data(holo_failures).get("failures", []):
            # Normalize to common shape
            all_failures.append({
                "type": f.get("source", "holo"),
                "signature": f.get("pattern", "")[:100],
                "module": f.get("module"),
                "last_seen": f.get("last_seen"),
                "frequency": f.get("frequency", 1),
            })

    # Cluster by similarity
    clusters = _cluster_failures_advanced(all_failures)

    # Filter to only repeated (count > 1 or explicit frequency)
    repeated = [c for c in clusters if c["count"] > 1 or c.get("total_frequency", 0) > 1]
    repeated.sort(key=lambda x: x["count"] + x.get("total_frequency", 0), reverse=True)

    confidence = min(confidence, 0.8)

    return ok_response(
        {
            "clusters": repeated[:limit],
            "total_clusters": len(repeated),
            "total_failures_analyzed": len(all_failures),
            "note": "Clusters with count > 1 indicate repeated patterns" if repeated else "No repeated failures detected",
        },
        source="signal_normalization",
        tool="get_repeated_failures",
        confidence=confidence,
        sources_used=sources_used,
    )


def _cluster_failures_advanced(failures: List[Dict]) -> List[Dict]:
    """Advanced failure clustering with deduplication."""
    clusters = defaultdict(lambda: {
        "items": [],
        "modules": set(),
        "total_frequency": 0,
    })

    for f in failures:
        # Create normalized signature
        sig = _normalize_failure_signature(f)
        clusters[sig]["items"].append(f)
        if f.get("module"):
            clusters[sig]["modules"].add(f["module"])
        clusters[sig]["total_frequency"] += f.get("frequency", 1)

    result = []
    for sig, data in clusters.items():
        result.append({
            "signature": sig,
            "count": len(data["items"]),
            "total_frequency": data["total_frequency"],
            "modules": list(data["modules"])[:5],
            "last_seen": _get_most_recent(data["items"]),
            "severity": _infer_failure_severity(data["items"]),
            "samples": data["items"][:2],
        })

    return result


def _normalize_failure_signature(failure: Dict) -> str:
    """Create normalized signature for clustering."""
    parts = []

    if failure.get("type"):
        parts.append(failure["type"])
    if failure.get("_category"):
        parts.append(failure["_category"])
    if failure.get("signature"):
        # Normalize: lowercase, collapse whitespace, truncate
        sig = re.sub(r"\s+", " ", failure["signature"].lower().strip())[:60]
        parts.append(sig)
    if failure.get("pattern"):
        sig = re.sub(r"\s+", " ", failure["pattern"].lower().strip())[:60]
        parts.append(sig)

    return ":".join(parts) if parts else "unknown"


def _get_most_recent(items: List[Dict]) -> Optional[str]:
    """Get most recent timestamp from items."""
    for item in items:
        if item.get("last_seen"):
            return item["last_seen"]
        if item.get("created_at"):
            return item["created_at"]
    return None


# =============================================================================
# Tool 4: Active Risks
# =============================================================================


def get_active_risks(repo_root: Path, limit: int = 10) -> Dict[str, Any]:
    """
    Get normalized active risk objects.

    Args:
        repo_root: Repository root path
        limit: Maximum risks to return

    Returns:
        MCPResponse with normalized risks
    """
    sources_used = []
    confidence = 0.4
    risks = []

    # Source 1: Impact scoring for critical modules
    for module in list(CRITICAL_MODULES.keys())[:5]:
        impact = impact_scoring.get_change_impact_score(
            repo_root, target_type="module", target=module
        )
        if impact.get("status") == "ok":
            data = _get_data(impact)
            if data.get("risk_level") in ("medium", "high", "critical"):
                risks.append({
                    "risk_type": "dependency_risk",
                    "scope": module,
                    "severity": data["risk_level"],
                    "confidence": data.get("confidence", 0.5),
                    "evidence_sources": ["impact_scoring"],
                    "why_it_matters": f"Critical module with {data.get('affected_count', 0)} affected dependencies",
                    "risk_factors": data.get("risk_factors", []),
                })

    if risks:
        sources_used.append("impact_scoring")
        confidence += 0.15

    # Source 2: Repeated failures -> repeated_failure_risk
    repeated = get_repeated_failures(repo_root, limit=10)
    if repeated.get("status") == "ok":
        sources_used.append("repeated_failures")
        confidence += 0.1

        for cluster in _get_data(repeated).get("clusters", [])[:3]:
            if cluster["count"] >= 2:
                risks.append({
                    "risk_type": "repeated_failure_risk",
                    "scope": ", ".join(cluster.get("modules", ["unknown"])[:3]),
                    "severity": _normalize_severity(cluster.get("severity", "medium")),
                    "confidence": 0.6,
                    "evidence_sources": ["failure_clustering"],
                    "why_it_matters": f"Failure pattern occurred {cluster['count']} times",
                    "signature": cluster.get("signature", "")[:100],
                })

    # Source 3: WSP audit drift
    status = overseer_tools.get_overseer_status(repo_root)
    if status.get("status") == "ok":
        sources_used.append("overseer_status")
        confidence += 0.1

        audit = _get_data(status).get("wsp_audit_status") or {}
        if isinstance(audit, dict) and audit.get("drift_count", 0) > 0:
            risks.append({
                "risk_type": "drift_risk",
                "scope": "WSP framework",
                "severity": _normalize_severity(audit.get("severity", "medium")),
                "confidence": 0.7,
                "evidence_sources": ["wsp_audit"],
                "why_it_matters": f"{audit['drift_count']} WSP compliance issues detected",
            })

    # Source 4: Coordination state issues
    coord = overseer_tools.get_coordination_state(repo_root)
    if coord.get("status") == "ok":
        sources_used.append("coordination_state")

        active_teams = _get_data(coord).get("active_teams", [])
        if len(active_teams) > 3:
            risks.append({
                "risk_type": "coordination_risk",
                "scope": "agent coordination",
                "severity": "medium",
                "confidence": 0.5,
                "evidence_sources": ["coordination_state"],
                "why_it_matters": f"{len(active_teams)} active teams may indicate coordination complexity",
            })

    # Sort by severity
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    risks.sort(key=lambda x: severity_order.get(x.get("severity", "low"), 4))

    confidence = min(confidence, 0.8)

    return ok_response(
        {
            "risks": risks[:limit],
            "total_risks": len(risks),
            "risk_taxonomy": list(RISK_TYPES.keys()),
        },
        source="signal_normalization",
        tool="get_active_risks",
        confidence=confidence,
        sources_used=sources_used,
    )


# =============================================================================
# Tool 5: Recommended Focus
# =============================================================================


def get_recommended_focus(repo_root: Path, limit: int = 10) -> Dict[str, Any]:
    """
    Get prioritized focus recommendations.

    Args:
        repo_root: Repository root path
        limit: Maximum items to return

    Returns:
        MCPResponse with focus recommendations
    """
    sources_used = []
    confidence = 0.4
    focus_items = []

    # Source 1: Active risks (highest priority)
    risks = get_active_risks(repo_root, limit=10)
    if risks.get("status") == "ok":
        sources_used.append("active_risks")
        confidence += 0.15

        for risk in _get_data(risks).get("risks", [])[:5]:
            if risk.get("severity") in ("high", "critical"):
                focus_items.append({
                    "focus": f"Address {risk['risk_type']} in {risk.get('scope', 'system')}",
                    "why_now": risk.get("why_it_matters", "High severity risk"),
                    "priority": 1 if risk["severity"] == "critical" else 2,
                    "suggested_context": [risk.get("scope")],
                    "linked_risks": [risk["risk_type"]],
                })

    # Source 2: Hot modules
    hot = get_hot_modules(repo_root, limit=5)
    if hot.get("status") == "ok":
        sources_used.append("hot_modules")
        confidence += 0.1

        for module in _get_data(hot).get("modules", [])[:3]:
            if module.get("heat_score", 0) > 1.0:
                focus_items.append({
                    "focus": f"Review changes in {module['module']}",
                    "why_now": f"High volatility (score: {module['heat_score']})",
                    "priority": 3,
                    "suggested_context": [module["module"]],
                    "factors": module.get("factors", []),
                })

    # Source 3: Repeated failures
    repeated = get_repeated_failures(repo_root, limit=5)
    if repeated.get("status") == "ok":
        sources_used.append("repeated_failures")
        confidence += 0.1

        for cluster in _get_data(repeated).get("clusters", [])[:2]:
            if cluster["count"] >= 3:
                focus_items.append({
                    "focus": f"Investigate recurring failure: {cluster.get('signature', 'unknown')[:50]}",
                    "why_now": f"Occurred {cluster['count']} times",
                    "priority": 2,
                    "suggested_context": cluster.get("modules", []),
                    "linked_failures": [cluster.get("signature", "")[:50]],
                })

    # Source 4: Test coverage gaps (from impact scoring data)
    # Check a few key modules for test gaps
    for module in ["ai_overseer", "shared_utilities", "wre_core"]:
        impact = impact_scoring.get_change_impact_score(
            repo_root, target_type="module", target=module
        )
        if impact.get("status") == "ok":
            coverage = _get_data(impact).get("test_coverage") or {}
            gaps = coverage.get("gaps") or [] if isinstance(coverage, dict) else []
            if gaps:
                sources_used.append("test_coverage")
                focus_items.append({
                    "focus": f"Add tests for {module}",
                    "why_now": f"Test coverage gap detected",
                    "priority": 4,
                    "suggested_context": [module],
                    "gaps": gaps[:3],
                })
                break  # Only add one test coverage item

    # Sort by priority
    focus_items.sort(key=lambda x: x.get("priority", 10))

    # Deduplicate by focus text
    seen = set()
    unique_items = []
    for item in focus_items:
        key = item["focus"][:50]
        if key not in seen:
            seen.add(key)
            unique_items.append(item)

    confidence = min(confidence, 0.75)

    return ok_response(
        {
            "focus_items": unique_items[:limit],
            "total_items": len(unique_items),
            "priority_note": "1=critical, 2=high, 3=medium, 4=low",
        },
        source="signal_normalization",
        tool="get_recommended_focus",
        confidence=confidence,
        sources_used=sources_used,
    )


# =============================================================================
# Tool 6: Prompt Context Packet
# =============================================================================


def get_prompt_context_packet(
    repo_root: Path,
    task_description: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Assemble compressed context for Windsurf prompt.

    Args:
        repo_root: Repository root path
        task_description: Optional task description for relevance filtering

    Returns:
        MCPResponse with prompt-ready context
    """
    sources_used = []
    confidence = 0.4

    packet = {
        "system_posture": "unknown",
        "hot_modules": [],
        "active_risks": [],
        "repeated_failures": [],
        "recommended_focus": [],
        "suggested_files": [],
        "suggested_wsp": [],
        "task_relevance": None,
    }

    # Get system posture
    summary = get_overseer_summary(repo_root)
    if summary.get("status") == "ok":
        sources_used.append("overseer_summary")
        confidence += 0.1
        packet["system_posture"] = _get_data(summary).get("system_posture", "unknown")

    # Get hot modules (compressed)
    hot = get_hot_modules(repo_root, limit=5)
    if hot.get("status") == "ok":
        sources_used.append("hot_modules")
        confidence += 0.1
        packet["hot_modules"] = [
            {"module": m["module"], "score": m["heat_score"]}
            for m in _get_data(hot).get("modules", [])[:5]
        ]

    # Get active risks (compressed)
    risks = get_active_risks(repo_root, limit=5)
    if risks.get("status") == "ok":
        sources_used.append("active_risks")
        confidence += 0.1
        packet["active_risks"] = [
            {
                "type": r["risk_type"],
                "scope": r["scope"],
                "severity": r["severity"],
            }
            for r in _get_data(risks).get("risks", [])[:5]
        ]

    # Get repeated failures (compressed)
    repeated = get_repeated_failures(repo_root, limit=3)
    if repeated.get("status") == "ok":
        sources_used.append("repeated_failures")
        confidence += 0.1
        packet["repeated_failures"] = [
            {
                "signature": c.get("signature", "")[:50],
                "count": c["count"],
            }
            for c in _get_data(repeated).get("clusters", [])[:3]
        ]

    # Get recommended focus (compressed)
    focus = get_recommended_focus(repo_root, limit=5)
    if focus.get("status") == "ok":
        sources_used.append("recommended_focus")
        confidence += 0.1
        packet["recommended_focus"] = [
            {"focus": f["focus"], "priority": f["priority"]}
            for f in _get_data(focus).get("focus_items", [])[:5]
        ]

    # If task description provided, get task-specific context
    if task_description and task_description.strip():
        task_packet = holo_tools.holo_task_packet(
            repo_root,
            task_description=task_description,
            include_patterns=True,
            include_failures=True,
        )
        if task_packet.get("status") == "ok":
            sources_used.append("holo_task_packet")
            confidence += 0.1

            task_data = _get_data(task_packet)
            packet["task_relevance"] = {
                "task": task_description,
                "relevant_modules": [
                    m.get("module") for m in task_data.get("relevant_modules", [])[:5]
                ],
                "suggested_wsp": [
                    w.get("title") for w in task_data.get("suggested_wsp", [])[:3]
                ],
            }

            # Merge suggested WSPs
            packet["suggested_wsp"] = [
                {"title": w.get("title"), "path": w.get("path")}
                for w in task_data.get("suggested_wsp", [])[:5]
            ]

            # Suggest files from relevant modules
            for mod in task_data.get("relevant_modules", [])[:3]:
                if mod.get("path"):
                    packet["suggested_files"].append(mod["path"])

    confidence = min(confidence, 0.85)

    return ok_response(
        packet,
        source="signal_normalization",
        tool="get_prompt_context_packet",
        confidence=confidence,
        sources_used=sources_used,
        note="Compressed context for Windsurf prompt building",
    )
