#!/usr/bin/env python3
"""
MCP Bridge Impact Scoring Engine.

Computes change impact scores based on:
- Dependency graph (affected modules)
- Test coverage (gaps)
- Prior failure patterns
- Module criticality

WSP References:
- WSP 72: Module Independence (cross-module impact)
- WSP 97: Truthful verification (no invented data)
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .dependency_tools import get_module_dependencies, get_reverse_dependencies
from .diff_tools import get_file_diff, get_diff_summary
from .test_mapping import get_test_mapping, get_file_test_mapping
from .failure_adapter import get_prior_failures_for_modules
from .response_schema import ok_response, error_response

logger = logging.getLogger(__name__)

# Core/shared modules that increase risk when affected
CRITICAL_MODULES = {
    "shared_utilities": 1.5,
    "database": 1.4,
    "wre_core": 1.3,
    "ai_overseer": 1.2,
    "foundups_selenium": 1.2,
    "mcp_manager": 1.2,
    "wsp_orchestrator": 1.1,
}

# Risk level thresholds
RISK_THRESHOLDS = {
    "low": 0.3,
    "medium": 0.5,
    "high": 0.7,
    "critical": 0.85,
}


def get_change_impact_score(
    repo_root: Path,
    target_type: str,
    target: str,
) -> Dict[str, Any]:
    """
    Compute change impact score for a target.

    Args:
        repo_root: Repository root path
        target_type: Type of target ("module", "file", "diff", "commit_range")
        target: Target identifier (module name, file path, or commit range)

    Returns:
        MCPResponse with impact score and details
    """
    # Validate target_type
    valid_types = {"module", "file", "diff", "commit_range"}
    if target_type not in valid_types:
        return error_response(
            f"Invalid target_type: {target_type}",
            valid_types=list(valid_types),
        )

    # Resolve affected modules based on target type
    affected_modules = _resolve_affected_modules(repo_root, target_type, target)

    if affected_modules.get("error"):
        return error_response(affected_modules["error"])

    module_list = affected_modules.get("modules", [])

    if not module_list:
        return ok_response(
            {
                "target_type": target_type,
                "target": target,
                "affected_modules": [],
                "risk_level": "low",
                "test_coverage": {"covered": 0, "total": 0, "gaps": []},
                "prior_failures": [],
                "confidence": 0.5,
                "confidence_factors": ["No affected modules detected"],
                "scoring_notes": ["Target appears isolated or not in modules/ structure"],
            },
            source="impact_scoring",
            tool="get_change_impact_score",
        )

    # Compute risk weights for each module
    weighted_modules = _compute_module_risk_weights(
        repo_root, module_list, target_type, target
    )

    # Get test coverage
    test_coverage = get_test_mapping(repo_root, module_list)

    # Get prior failures
    prior_failures = get_prior_failures_for_modules(repo_root, module_list)

    # Compute overall risk level
    risk_assessment = _compute_risk_level(
        weighted_modules=weighted_modules,
        test_coverage=test_coverage,
        prior_failures=prior_failures,
        target_type=target_type,
    )

    # Compute confidence score
    confidence = _compute_confidence(
        weighted_modules=weighted_modules,
        test_coverage=test_coverage,
        prior_failures=prior_failures,
    )

    return ok_response(
        {
            "target_type": target_type,
            "target": target,
            "affected_modules": weighted_modules,
            "affected_count": len(weighted_modules),
            "risk_level": risk_assessment["level"],
            "risk_score": risk_assessment["score"],
            "risk_factors": risk_assessment["factors"],
            "test_coverage": {
                "covered": test_coverage["covered"],
                "total": test_coverage["total"],
                "gaps": test_coverage["gaps"],
                "coverage_ratio": test_coverage["covered"] / max(test_coverage["total"], 1),
            },
            "prior_failures": prior_failures["patterns"][:10],
            "failure_data_available": len(prior_failures["patterns"]) > 0,
            "confidence": confidence["score"],
            "confidence_factors": confidence["factors"],
        },
        source="impact_scoring",
        tool="get_change_impact_score",
    )


def _resolve_affected_modules(
    repo_root: Path,
    target_type: str,
    target: str,
) -> Dict[str, Any]:
    """Resolve which modules are affected by the target."""

    if target_type == "module":
        # Direct module + reverse dependencies
        modules = {target}

        # Get reverse deps (who depends on this module)
        reverse = get_reverse_dependencies(repo_root, module_name=target)
        if reverse.get("status") == "ok":
            for dep in reverse["data"].get("dependents", []):
                modules.add(dep["module"])

        return {"modules": list(modules)}

    elif target_type == "file":
        # Extract module from file path
        module = _extract_module_from_file(target)
        if not module:
            return {"error": f"Cannot determine module from file: {target}"}

        modules = {module}

        # Get reverse deps of the module
        reverse = get_reverse_dependencies(repo_root, module_name=module)
        if reverse.get("status") == "ok":
            for dep in reverse["data"].get("dependents", []):
                modules.add(dep["module"])

        return {"modules": list(modules), "primary_module": module}

    elif target_type in ("diff", "commit_range"):
        # Get diff summary to find changed files
        diff_result = get_diff_summary(repo_root, commit_range=target)
        if diff_result.get("status") != "ok":
            return {"error": f"Cannot get diff for: {target}"}

        # Extract modules from changed files
        modules = set()
        for file_info in diff_result["data"].get("changed_files", []):
            module = _extract_module_from_file(file_info["path"])
            if module:
                modules.add(module)

        # Add reverse deps for each changed module
        all_affected = set(modules)
        for module in modules:
            reverse = get_reverse_dependencies(repo_root, module_name=module)
            if reverse.get("status") == "ok":
                for dep in reverse["data"].get("dependents", []):
                    all_affected.add(dep["module"])

        return {
            "modules": list(all_affected),
            "directly_changed": list(modules),
            "diff_stats": diff_result["data"].get("overall_stats", {}),
        }

    return {"error": f"Unsupported target_type: {target_type}"}


def _extract_module_from_file(file_path: str) -> Optional[str]:
    """Extract module name from file path."""
    import re
    match = re.match(r"modules[/\\][^/\\]+[/\\]([^/\\]+)", file_path)
    if match:
        return match.group(1)
    return None


def _compute_module_risk_weights(
    repo_root: Path,
    modules: List[str],
    target_type: str,
    target: str,
) -> List[Dict[str, Any]]:
    """Compute risk weight for each affected module."""
    weighted = []

    # Determine primary module(s) if applicable
    primary_modules = set()
    if target_type == "module":
        primary_modules.add(target)
    elif target_type == "file":
        primary = _extract_module_from_file(target)
        if primary:
            primary_modules.add(primary)

    for module in modules:
        # Base weight
        base_weight = 1.0

        # Critical module multiplier
        critical_multiplier = CRITICAL_MODULES.get(module, 1.0)

        # Primary (directly changed) vs secondary (reverse dep)
        is_primary = module in primary_modules
        primary_multiplier = 1.5 if is_primary else 1.0

        # Compute final weight
        risk_weight = base_weight * critical_multiplier * primary_multiplier

        # Get dependency count for context
        deps_result = get_module_dependencies(repo_root, module_name=module)
        internal_dep_count = 0
        if deps_result.get("status") == "ok":
            internal_dep_count = deps_result["data"].get("internal_count", 0)

        weighted.append({
            "module": module,
            "risk_weight": round(risk_weight, 2),
            "is_primary": is_primary,
            "is_critical": module in CRITICAL_MODULES,
            "internal_dep_count": internal_dep_count,
        })

    # Sort by risk weight descending
    weighted.sort(key=lambda x: x["risk_weight"], reverse=True)

    return weighted


def _compute_risk_level(
    weighted_modules: List[Dict],
    test_coverage: Dict,
    prior_failures: Dict,
    target_type: str,
) -> Dict[str, Any]:
    """Compute overall risk level."""
    factors = []
    score = 0.0

    # Factor 1: Number of affected modules (0-0.3)
    module_count = len(weighted_modules)
    if module_count == 0:
        module_score = 0.0
    elif module_count == 1:
        module_score = 0.1
    elif module_count <= 3:
        module_score = 0.15
    elif module_count <= 5:
        module_score = 0.2
    elif module_count <= 10:
        module_score = 0.25
    else:
        module_score = 0.3
        factors.append(f"High module count: {module_count} affected")

    score += module_score

    # Factor 2: Critical module involvement (0-0.25)
    critical_modules = [m for m in weighted_modules if m.get("is_critical")]
    if critical_modules:
        critical_score = min(len(critical_modules) * 0.1, 0.25)
        score += critical_score
        factors.append(f"Critical modules affected: {[m['module'] for m in critical_modules]}")
    else:
        score += 0.0

    # Factor 3: Test coverage gaps (0-0.25)
    coverage_ratio = test_coverage["covered"] / max(test_coverage["total"], 1)
    if coverage_ratio == 0:
        coverage_score = 0.25
        factors.append("No test coverage for affected modules")
    elif coverage_ratio < 0.5:
        coverage_score = 0.15
        factors.append(f"Low test coverage: {coverage_ratio:.0%}")
    elif coverage_ratio < 0.8:
        coverage_score = 0.08
    else:
        coverage_score = 0.0

    score += coverage_score

    # Factor 4: Prior failure patterns (0-0.2)
    failure_count = len(prior_failures.get("patterns", []))
    if failure_count > 5:
        failure_score = 0.2
        factors.append(f"Multiple prior failures: {failure_count} patterns")
    elif failure_count > 0:
        failure_score = min(failure_count * 0.04, 0.15)
        factors.append(f"Prior failures found: {failure_count} patterns")
    else:
        failure_score = 0.0

    score += failure_score

    # Determine level from score
    if score >= RISK_THRESHOLDS["critical"]:
        level = "critical"
    elif score >= RISK_THRESHOLDS["high"]:
        level = "high"
    elif score >= RISK_THRESHOLDS["medium"]:
        level = "medium"
    else:
        level = "low"

    if not factors:
        factors.append("No significant risk factors detected")

    return {
        "level": level,
        "score": round(score, 3),
        "factors": factors,
    }


def _compute_confidence(
    weighted_modules: List[Dict],
    test_coverage: Dict,
    prior_failures: Dict,
) -> Dict[str, Any]:
    """Compute confidence score based on data completeness."""
    factors = []
    confidence = 1.0

    # Reduce confidence for missing test coverage data
    if test_coverage["total"] == 0:
        confidence -= 0.2
        factors.append("No test coverage data available")

    # Reduce confidence if no failure history
    if not prior_failures.get("patterns"):
        confidence -= 0.15
        factors.append("No prior failure data available")

    # Reduce confidence if HoloIndex not available
    if not prior_failures.get("holoindex_available"):
        confidence -= 0.1
        factors.append("HoloIndex not queried (Slice 3 integration pending)")

    # Reduce confidence for many modules (harder to assess)
    if len(weighted_modules) > 10:
        confidence -= 0.1
        factors.append("Many affected modules - assessment complexity")

    # Reduce confidence if few dependencies resolved
    deps_resolved = sum(1 for m in weighted_modules if m.get("internal_dep_count", 0) > 0)
    if deps_resolved < len(weighted_modules) / 2 and weighted_modules:
        confidence -= 0.1
        factors.append("Limited dependency resolution")

    confidence = max(0.1, confidence)  # Floor at 0.1

    if not factors:
        factors.append("Full data available")

    return {
        "score": round(confidence, 2),
        "factors": factors,
    }
