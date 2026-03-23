#!/usr/bin/env python3
"""
Grant task executor for autonomous pipeline.

Handles grant_watchlist_review and grant_watchlist_stabilize tasks
with structured, machine-verifiable outputs suitable for supervisor verification.

Human-only gates (KYC, identity, final submit) remain intact per SKILL.md.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[4]
GRANT_WATCHLIST_STATUS_PATH = (
    REPO_ROOT
    / "modules"
    / "communication"
    / "moltbot_bridge"
    / "workspace"
    / "reports"
    / "web3_grants_0102_watchlist_status.json"
)
WSP97_RESCORED_PATH = (
    REPO_ROOT
    / "modules"
    / "communication"
    / "moltbot_bridge"
    / "workspace"
    / "reports"
    / "web3_grants_0102_wsp97_rescored_20260322.json"
)


def execute_grant_review(changed_items: List[str]) -> Dict[str, Any]:
    """
    Execute grant watchlist review for changed items.

    Returns structured evidence for supervisor verification:
    - items_reviewed: count of items processed
    - findings: per-item analysis with repo-fit assessment
    - recommendations: prioritized next steps
    - memory_update: summary for workspace memory

    Does NOT submit applications (human-only gate).
    """
    result = {
        "task_type": "grant_watchlist_review",
        "executed_at": datetime.now(UTC).isoformat(),
        "items_reviewed": 0,
        "findings": [],
        "recommendations": [],
        "memory_update": None,
        "success": False,
        "detail": "",
    }

    if not changed_items:
        result["detail"] = "no_changed_items_provided"
        return result

    # Load current watchlist status for context
    watchlist_status = _load_watchlist_status()
    if not watchlist_status:
        result["detail"] = "watchlist_status_unavailable"
        return result

    # Load WSP 97 rescored sheet if available
    rescored = _load_rescored_sheet()

    findings = []
    for item_name in changed_items[:10]:  # Cap at 10 to avoid runaway
        item_data = _find_item_in_watchlist(item_name, watchlist_status)
        finding = {
            "name": item_name,
            "ecosystem": item_data.get("ecosystem") if item_data else "unknown",
            "last_refresh_result": item_data.get("last_refresh_result") if item_data else "not_found",
            "repo_fit_assessment": _assess_repo_fit(item_name, rescored),
            "sources_ok": all(
                s.get("ok", False) for s in (item_data.get("sources", []) if item_data else [])
            ),
        }
        findings.append(finding)

    result["items_reviewed"] = len(findings)
    result["findings"] = findings

    # Generate recommendations based on findings
    high_fit_items = [f for f in findings if f["repo_fit_assessment"].get("fit_score", 0) >= 0.7]
    result["recommendations"] = [
        f"Review {f['name']} ({f['ecosystem']}) - high repo fit"
        for f in high_fit_items[:3]
    ]

    # Prepare memory update
    result["memory_update"] = {
        "type": "grant_review_outcome",
        "timestamp": result["executed_at"],
        "changed_count": len(changed_items),
        "reviewed_count": result["items_reviewed"],
        "high_fit_count": len(high_fit_items),
        "summary": f"Reviewed {result['items_reviewed']} changed grant pages; {len(high_fit_items)} show high repo fit",
    }

    result["success"] = True
    result["detail"] = f"reviewed_{result['items_reviewed']}_items"
    return result


def execute_grant_stabilize(error_items: List[str]) -> Dict[str, Any]:
    """
    Execute grant watchlist stabilization for error items.

    Returns structured remediation detail for degraded grant-watchlist refresh:
    - items_analyzed: count of error items processed
    - diagnostics: per-item error analysis
    - remediation_steps: actionable fixes
    - memory_update: summary for workspace memory

    Does NOT modify external systems (diagnostic only).
    """
    result = {
        "task_type": "grant_watchlist_stabilize",
        "executed_at": datetime.now(UTC).isoformat(),
        "items_analyzed": 0,
        "diagnostics": [],
        "remediation_steps": [],
        "memory_update": None,
        "success": False,
        "detail": "",
    }

    if not error_items:
        result["detail"] = "no_error_items_provided"
        return result

    # Load current watchlist status for error context
    watchlist_status = _load_watchlist_status()
    if not watchlist_status:
        result["detail"] = "watchlist_status_unavailable"
        return result

    diagnostics = []
    remediation_steps = []

    for item_name in error_items[:10]:  # Cap at 10
        item_data = _find_item_in_watchlist(item_name, watchlist_status)
        if not item_data:
            diagnostics.append({
                "name": item_name,
                "error_type": "not_found_in_watchlist",
                "http_status": None,
                "recommendation": "verify_watchlist_entry_exists",
            })
            continue

        sources = item_data.get("sources", [])
        for source in sources:
            if not source.get("ok", True):
                error_type = _categorize_error(source.get("error", ""), source.get("http_status"))
                diag = {
                    "name": item_name,
                    "url": source.get("url"),
                    "error_type": error_type,
                    "http_status": source.get("http_status"),
                    "raw_error": source.get("error"),
                }
                diagnostics.append(diag)

                # Generate remediation based on error type
                if error_type == "rate_limit":
                    remediation_steps.append(
                        f"{item_name}: Add delay between requests or use rotating proxies"
                    )
                elif error_type == "url_not_found":
                    remediation_steps.append(
                        f"{item_name}: Verify URL is still valid; grant page may have moved"
                    )
                elif error_type == "cloudflare_block":
                    remediation_steps.append(
                        f"{item_name}: Use browser automation or manual check"
                    )
                else:
                    remediation_steps.append(
                        f"{item_name}: Investigate {error_type} error manually"
                    )

    result["items_analyzed"] = len(error_items)
    result["diagnostics"] = diagnostics
    result["remediation_steps"] = list(set(remediation_steps))  # Dedupe

    # Prepare memory update
    result["memory_update"] = {
        "type": "grant_stabilize_outcome",
        "timestamp": result["executed_at"],
        "error_count": len(error_items),
        "analyzed_count": len(diagnostics),
        "remediation_count": len(result["remediation_steps"]),
        "summary": f"Analyzed {len(diagnostics)} grant fetch errors; {len(result['remediation_steps'])} remediation steps identified",
    }

    result["success"] = True
    result["detail"] = f"analyzed_{len(diagnostics)}_errors"
    return result


def _load_watchlist_status() -> Optional[Dict[str, Any]]:
    """Load the grant watchlist status snapshot."""
    if not GRANT_WATCHLIST_STATUS_PATH.exists():
        return None
    try:
        return json.loads(GRANT_WATCHLIST_STATUS_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.debug("Failed to load watchlist status: %s", exc)
        return None


def _load_rescored_sheet() -> Optional[Dict[str, Any]]:
    """Load the WSP 97 rescored grant sheet if available."""
    if not WSP97_RESCORED_PATH.exists():
        return None
    try:
        return json.loads(WSP97_RESCORED_PATH.read_text(encoding="utf-8"))
    except Exception:
        return None


def _find_item_in_watchlist(item_name: str, watchlist: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Find a specific item in the watchlist by name."""
    items = watchlist.get("items", [])
    for item in items:
        if item.get("name") == item_name:
            return item
    return None


def _assess_repo_fit(item_name: str, rescored: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Assess repo fit for a grant based on WSP 97 rescored data."""
    if not rescored:
        return {"fit_score": 0.5, "notes": "rescored_sheet_unavailable"}

    # Search priority groups for the item
    for group_name, items in rescored.get("priority_groups", {}).items():
        for item in items:
            if item.get("name") == item_name:
                return {
                    "fit_score": _priority_to_fit_score(group_name),
                    "group": group_name,
                    "blockchain_fit": item.get("repo_blockchain_fit"),
                    "notes": item.get("notes", ""),
                }

    return {"fit_score": 0.3, "notes": "not_in_rescored_sheet"}


def _priority_to_fit_score(group_name: str) -> float:
    """Convert priority group name to a fit score.

    Maps actual priority groups from web3_grants_0102_wsp97_rescored_20260322.json:
    - p0_apply_now: Best repo fit, apply immediately
    - p1_after_one_concrete_adapter: Good fit, needs one more adapter
    - p2_deprioritized_until_new_chain_surface: Low priority until new chain support
    """
    mapping = {
        "p0_apply_now": 0.95,
        "p1_after_one_concrete_adapter": 0.70,
        "p2_deprioritized_until_new_chain_surface": 0.35,
    }
    return mapping.get(group_name.lower(), 0.5)


def _categorize_error(error_str: Optional[str], http_status: Optional[int]) -> str:
    """Categorize error type for remediation guidance."""
    if http_status == 429:
        return "rate_limit"
    if http_status == 404:
        return "url_not_found"
    if http_status == 403:
        return "access_denied"
    if http_status and http_status >= 500:
        return "server_error"

    error_lower = (error_str or "").lower()
    if "cloudflare" in error_lower or "captcha" in error_lower:
        return "cloudflare_block"
    if "timeout" in error_lower:
        return "timeout"
    if "ssl" in error_lower or "certificate" in error_lower:
        return "ssl_error"

    return "unknown"
