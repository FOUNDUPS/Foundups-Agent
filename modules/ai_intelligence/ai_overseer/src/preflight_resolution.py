#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Preflight Resolution Dispatch Contract.

DJ - AI_RESOLUTION_HOOK_CONTRACT_PHASE1

Provides on_preflight_fail() as the single structured hook for preflight
failures that today only log-and-continue. Writes a durable event artifact
under alerts/preflight/ and attempts best-effort proposal routing via
PatternMemory / Qwen / Gemma when those are available. Never auto-applies
fixes.

WSP 97 state distinction:
    detected     - emitter observed a preflight failure
    dispatched   - structured event recorded on disk
    proposed     - AI proposed a remediation (not applied)
    escalated    - event requires 012 review (severity/confidence)
    skipped      - LLM unavailable; deterministic event only

Hard constraints (Phase 1):
    - No auto-remediation
    - No fix application
    - No process mutation
    - LLM-unavailable path returns a valid dispatched event
"""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

logger = logging.getLogger(__name__)


PreflightResolutionState = Literal[
    "detected",
    "dispatched",
    "proposed",
    "escalated",
    "skipped",
]


Severity = Literal["critical", "high", "medium", "low", "info"]


_SEVERITY_ESCALATE = {"critical", "high"}

_SAFE_COMPONENT = re.compile(r"[^A-Za-z0-9_.-]+")


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_component(component: str) -> str:
    cleaned = _SAFE_COMPONENT.sub("_", component.strip()) or "unknown"
    return cleaned[:64]


@dataclass
class PreflightFailureEvent:
    """Structured preflight-failure event routed to ai_overseer."""

    component: str
    severity: Severity
    payload: Dict[str, Any]
    source: str = ""
    detected_at: str = ""
    state: PreflightResolutionState = "detected"
    requires_012: bool = False
    automation_candidate: bool = False
    pattern_recall: Optional[Dict[str, Any]] = None
    proposal: Optional[Dict[str, Any]] = None
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _default_alerts_root(repo_root: Optional[Path] = None) -> Path:
    root = repo_root or Path(os.getenv("FOUNDUPS_REPO_ROOT", ".")).resolve()
    return root / "alerts" / "preflight"


def _try_pattern_recall(event: PreflightFailureEvent) -> Optional[Dict[str, Any]]:
    try:
        from modules.infrastructure.wre_core.src.pattern_memory import (
            SQLitePatternMemory,
        )

        memory = SQLitePatternMemory()
        patterns = memory.recall_successful_patterns(
            skill_name=f"preflight_{event.component}",
            min_fidelity=0.70,
        )
        if not patterns:
            return None
        first = patterns[0]
        return {
            "pattern_id": getattr(first, "pattern_id", None),
            "fidelity": getattr(first, "fidelity", None),
            "skill_name": getattr(first, "skill_name", None),
        }
    except Exception as exc:
        logger.debug(f"[PREFLIGHT-DISPATCH] PatternMemory unavailable: {exc}")
        return None


def _try_ai_proposal(event: PreflightFailureEvent) -> Optional[Dict[str, Any]]:
    try:
        from holo_index.qwen_advisor.orchestration.autonomous_refactoring import (
            AutonomousRefactoringOrchestrator,
        )

        orchestrator = AutonomousRefactoringOrchestrator(Path("."))
        if not hasattr(orchestrator, "propose_preflight_fix"):
            return {
                "engine": "qwen",
                "available": False,
                "reason": "propose_preflight_fix method not implemented",
            }
        return orchestrator.propose_preflight_fix(event.to_dict())
    except Exception as exc:
        logger.debug(f"[PREFLIGHT-DISPATCH] AI proposal unavailable: {exc}")
        return None


def _write_event_artifact(
    event: PreflightFailureEvent,
    alerts_root: Optional[Path] = None,
) -> Path:
    root = alerts_root or _default_alerts_root()
    root.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = root / f"{_safe_component(event.component)}_{timestamp}.json"
    path.write_text(json.dumps(event.to_dict(), indent=2), encoding="utf-8")
    return path


def on_preflight_fail(
    component: str,
    severity: Severity,
    payload: Dict[str, Any],
    source: str = "",
    *,
    alerts_root: Optional[Path] = None,
    skip_ai: bool = False,
) -> Dict[str, Any]:
    """
    Single structured entry point for preflight failures.

    Args:
        component: Short identifier (e.g. "dep_security", "wsp_framework").
        severity: One of critical / high / medium / low / info.
        payload: Free-form dict of emitter-provided context.
        source: Emitter identifier (module:function or file:line).
        alerts_root: Override artifact directory (test hook).
        skip_ai: Skip AI proposal path (test hook).

    Returns:
        Dict describing the event and its resolution state. Never raises.
    """
    try:
        event = PreflightFailureEvent(
            component=component or "unknown",
            severity=severity if severity in {"critical", "high", "medium", "low", "info"} else "medium",
            payload=payload or {},
            source=source or "",
            detected_at=_utc_iso(),
            state="detected",
        )

        event.requires_012 = bool(payload.get("requires_012")) or (
            event.severity in _SEVERITY_ESCALATE
        )
        event.automation_candidate = bool(payload.get("automation_candidate", False))

        event.pattern_recall = _try_pattern_recall(event)
        if event.pattern_recall:
            event.notes.append(f"pattern_recall_hit={event.pattern_recall.get('pattern_id')}")

        if skip_ai:
            event.state = "skipped"
            event.notes.append("ai_proposal_skipped_by_caller")
        else:
            proposal = _try_ai_proposal(event)
            if proposal and proposal.get("available", True):
                event.proposal = proposal
                event.state = "proposed"
            else:
                event.state = "skipped"
                event.notes.append(
                    "ai_proposal_unavailable"
                    if proposal is None
                    else f"ai_proposal_not_implemented:{proposal.get('reason', '')}"
                )

        if event.requires_012:
            event.state = "escalated"

        artifact_path = _write_event_artifact(event, alerts_root=alerts_root)
        if event.state == "detected":
            event.state = "dispatched"

        logger.info(
            f"[PREFLIGHT-DISPATCH] component={event.component} severity={event.severity} "
            f"state={event.state} artifact={artifact_path}"
        )

        result = event.to_dict()
        result["artifact_path"] = str(artifact_path)
        return result

    except Exception as exc:
        logger.error(f"[PREFLIGHT-DISPATCH] dispatch failed: {exc}")
        return {
            "component": component,
            "severity": severity,
            "state": "detected",
            "error": str(exc),
            "notes": ["dispatch_internal_error"],
        }
