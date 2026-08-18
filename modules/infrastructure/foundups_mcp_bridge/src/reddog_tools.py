"""
RedDog & Fusion Perception Tools for FoundUps MCP Bridge.
=========================================================

Provides read-only access to RedDog external state, worker lane assignments,
research threads, and grounded Fusion analysis packets for 0102.

WSP References:
- WSP 97: Truthful Verification (curated state boundaries)
- WSP 50: Pre-Action Verification (HoloIndex grounding)
- WSP 48: Recursive Self-Improvement (pattern memory)
"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional

from .response_schema import error_response, ok_response

logger = logging.getLogger(__name__)


def _get_git_head_info(repo_root: Path) -> Dict[str, str]:
    """Retrieve current Git HEAD commit and branch."""
    info = {"commit": "unknown", "branch": "unknown"}
    try:
        commit_proc = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=5,
        )
        if commit_proc.returncode == 0:
            info["commit"] = commit_proc.stdout.strip()

        branch_proc = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=5,
        )
        if branch_proc.returncode == 0:
            info["branch"] = branch_proc.stdout.strip()
    except Exception as exc:
        logger.debug(f"[REDDOG] Git info lookup error: {exc}")
    return info


def get_reddog_state(repo_root: Path) -> Dict[str, Any]:
    """
    Get current RedDog external state snapshot.

    Reads curated session continuity state, active worker lanes, open research
    threads, and recent slice lineage from WSP_knowledge/red_dog_external_state.

    Args:
        repo_root: Repository root path

    Returns:
        MCPResponse with current RedDog state snapshot.
    """
    try:
        state_dir = repo_root / "WSP_knowledge" / "red_dog_external_state"
        git_info = _get_git_head_info(repo_root)

        current_context_file = state_dir / "CURRENT_CONTEXT.md"
        active_threads_file = state_dir / "ACTIVE_RESEARCH_THREADS.md"
        lineage_file = state_dir / "WORK_TO_WORK_LINEAGE.md"

        context_text = current_context_file.read_text(encoding="utf-8", errors="replace") if current_context_file.exists() else ""
        threads_text = active_threads_file.read_text(encoding="utf-8", errors="replace") if active_threads_file.exists() else ""
        lineage_text = lineage_file.read_text(encoding="utf-8", errors="replace") if lineage_file.exists() else ""

        data = {
            "git": git_info,
            "state_dir_exists": state_dir.exists(),
            "active_context_summary": context_text[:1500],
            "active_research_threads": threads_text[:1500],
            "work_to_work_lineage": lineage_text[:1500],
        }

        return ok_response(data, source="reddog")
    except Exception as exc:
        logger.error(f"[REDDOG] get_reddog_state error: {exc}")
        return error_response(str(exc))


def reddog_analyze(
    repo_root: Path,
    prompt: str,
    target_module: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Run grounded RedDog Fusion analysis for a problem statement.

    Combines live Git state, active worker lane state, target module documentation,
    and overseer posture into a structured Fusion packet for 0102 reasoning.

    Args:
        repo_root: Repository root path
        prompt: Task or problem statement to analyze
        target_module: Optional module name to scope the analysis

    Returns:
        MCPResponse with grounded Fusion analysis packet.
    """
    if not prompt or not prompt.strip():
        return error_response("Prompt cannot be empty")

    try:
        from . import overseer_tools, doc_tools

        git_info = _get_git_head_info(repo_root)
        overseer_res = overseer_tools.get_overseer_status(repo_root).get("data", {})

        state_dir = repo_root / "WSP_knowledge" / "red_dog_external_state"
        current_context_file = state_dir / "CURRENT_CONTEXT.md"
        context_snippet = current_context_file.read_text(encoding="utf-8", errors="replace")[:1000] if current_context_file.exists() else ""

        module_doc = None
        if target_module:
            doc_res = doc_tools.get_module_docs(repo_root, module_name=target_module)
            if doc_res.get("status") == "ok":
                module_doc = doc_res.get("data", {}).get("readme", "")[:1000]

        fusion_packet = {
            "prompt": prompt.strip(),
            "target_module": target_module,
            "git_state": git_info,
            "system_posture": "normal" if overseer_res.get("available") else "degraded",
            "active_context": context_snippet,
            "module_doc_snippet": module_doc,
        }

        return ok_response(fusion_packet, source="reddog_fusion", prompt=prompt)
    except Exception as exc:
        logger.error(f"[REDDOG] reddog_analyze error: {exc}")
        return error_response(str(exc))
