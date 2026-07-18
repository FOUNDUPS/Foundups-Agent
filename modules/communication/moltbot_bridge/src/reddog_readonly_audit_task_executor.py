"""Deterministic executor for RedDog read-only audit tasks.

Slice: REDDOG_READONLY_AUDIT_TASK_REPORT_EXECUTOR_PHASE1

This module consumes one AgentDB task context produced by
`reddog_openclaw_readonly_audit_swarm_enqueue` and emits a read-only audit
report shape accepted by `validate_reddog_openclaw_readonly_audit_reports`.

It reads only allowlisted repository files, computes evidence digests, and
returns a structured report. It does not call models, execute shell commands,
dispatch Hermes/WRE, create worktrees, mutate repository files, mutate
HoloIndex, enqueue OpenClaw work, or write reports to disk.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

from modules.communication.moltbot_bridge.src.reddog_lane_state_reconciler import (
    reconcile_active_and_json_ledgers,
)
from modules.communication.moltbot_bridge.src.reddog_openclaw_readonly_audit_swarm_enqueue import (
    READONLY_AUDIT_TASK_SOURCE,
)


READONLY_AUDIT_TASK_REPORT_ACCEPT = "READONLY_AUDIT_TASK_REPORT_ACCEPT"
READONLY_AUDIT_TASK_REPORT_REJECT = "READONLY_AUDIT_TASK_REPORT_REJECT"
READONLY_AUDIT_LANE_ANALYZER_SLICE = "REDDOG_READONLY_AUDIT_LANE_ANALYZER_PHASE1"
AUTHORITATIVE_WORK_STATE_REFRESH_SLICE = "REDDOG_AUTHORITATIVE_WORK_STATE_REFRESH_RUNTIME_PHASE1"

MAX_READ_TARGETS = 32
MAX_READ_BYTES_PER_TARGET = 12_000
DENIED_BASENAMES = frozenset({".env", ".env.local", ".env.production", "id_rsa", "id_dsa"})
DENIED_SEGMENTS = frozenset({".git", ".ssh", ".aws", ".azure", ".gcp", "__pycache__"})
ACTIVE_SLICE_LEDGER_TARGET = "docs/0102_session_briefings/ACTIVE_SLICE_LEDGER.md"
WORK_LEDGER_TARGET = "docs/0102_session_briefings/work_ledger.schema.json"
LANE_RECONCILER_AUDIT_LANES = frozenset({"repo_code_audit", "runtime_freshness_audit"})


class ReadOnlyAuditTaskRejectReason:
    INVALID_CONTEXT = "REJECT_INVALID_CONTEXT"
    WRONG_SOURCE = "REJECT_WRONG_SOURCE"
    MISSING_ASSIGNMENT = "REJECT_MISSING_ASSIGNMENT"
    TOO_MANY_TARGETS = "REJECT_TOO_MANY_TARGETS"
    UNSAFE_TARGET = "REJECT_UNSAFE_TARGET"
    TARGET_READ_FAILED = "REJECT_TARGET_READ_FAILED"
    MISSING_WSP15_ALLOCATION = "REJECT_MISSING_WSP15_ALLOCATION"
    MALFORMED_WSP15_ALLOCATION = "REJECT_MALFORMED_WSP15_ALLOCATION"
    WSP15_BINDING_MISMATCH = "REJECT_WSP15_BINDING_MISMATCH"
    WSP15_FUSION_REQUIRED = "REJECT_WSP15_FUSION_REQUIRED"
    INDEX_QUERY_FAILED = "REJECT_INDEX_QUERY_FAILED"
    INDEX_QUERY_STALE = "REJECT_INDEX_QUERY_STALE"
    INDEX_QUERY_NO_CANDIDATES = "REJECT_INDEX_QUERY_NO_CANDIDATES"
    REPOSITORY_STATE_CHANGED = "REJECT_REPOSITORY_STATE_CHANGED"
    MODEL_FAILURE = "REJECT_MODEL_FAILURE"
    MODEL_TIMEOUT = "REJECT_MODEL_TIMEOUT"
    MODEL_SELECTION_RECEIPT = "REJECT_MODEL_SELECTION_RECEIPT"
    MODEL_RUNTIME_BINDING_RECEIPT = "REJECT_MODEL_RUNTIME_BINDING_RECEIPT"
    MODEL_SCHEMA_FAILURE = "REJECT_MODEL_SCHEMA_FAILURE"
    UNKNOWN_EVIDENCE_REF = "REJECT_UNKNOWN_EVIDENCE_REF"
    REPORT_MISSING_EVIDENCE = "REJECT_REPORT_MISSING_EVIDENCE"
    PROMPT_BUDGET_EXCEEDED = "REJECT_PROMPT_BUDGET_EXCEEDED"


@dataclass(frozen=True)
class ReadOnlyTargetEvidence:
    path: str
    digest: str
    bytes_read: int
    line_count: int
    truncated: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class _ReadOnlyTargetSnapshot:
    evidence: ReadOnlyTargetEvidence
    text: str


@dataclass(frozen=True)
class ReadOnlyAuditTaskExecutionResult:
    accepted: bool
    decision: str
    report: Optional[Mapping[str, Any]]
    evidence: tuple[ReadOnlyTargetEvidence, ...]
    rejection_reasons: tuple[str, ...]
    no_model_call_performed: bool = True
    no_shell_command_executed: bool = True
    no_repo_mutation_performed: bool = True
    no_holoindex_reindex_performed: bool = True
    no_openclaw_enqueue_performed: bool = True
    no_hermes_dispatch_performed: bool = True
    no_worktree_operation_performed: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "accepted": self.accepted,
            "decision": self.decision,
            "report": dict(self.report) if self.report else None,
            "evidence": [item.to_dict() for item in self.evidence],
            "rejection_reasons": list(self.rejection_reasons),
            "no_model_call_performed": self.no_model_call_performed,
            "no_shell_command_executed": self.no_shell_command_executed,
            "no_repo_mutation_performed": self.no_repo_mutation_performed,
            "no_holoindex_reindex_performed": self.no_holoindex_reindex_performed,
            "no_openclaw_enqueue_performed": self.no_openclaw_enqueue_performed,
            "no_hermes_dispatch_performed": self.no_hermes_dispatch_performed,
            "no_worktree_operation_performed": self.no_worktree_operation_performed,
        }


def execute_reddog_readonly_audit_task(
    *,
    task_context: Mapping[str, Any],
    repo_root: str | Path,
    task_id: str | None = None,
    model_runner: Any | None = None,
    holoindex_adapter: Any | None = None,
    codeindex_adapter: Any | None = None,
    external_research_retriever: Any | None = None,
    timeout_seconds: int = 60,
) -> ReadOnlyAuditTaskExecutionResult:
    """Execute a RedDog read-only audit task.

    The default path remains deterministic for existing task contexts. Tasks
    explicitly marked ``model_backed_0102`` and assigned to ``repo_code_audit``
    use the model-backed worker path and fail closed on retrieval/model/schema
    errors.
    """

    if not isinstance(task_context, Mapping):
        return _reject([ReadOnlyAuditTaskRejectReason.INVALID_CONTEXT])
    if task_context.get("source") != READONLY_AUDIT_TASK_SOURCE:
        return _reject([ReadOnlyAuditTaskRejectReason.WRONG_SOURCE])
    assignment = task_context.get("assignment")
    if not isinstance(assignment, Mapping):
        return _reject([ReadOnlyAuditTaskRejectReason.MISSING_ASSIGNMENT])

    targets = tuple(str(value) for value in assignment.get("allowed_read_targets", ()) if str(value).strip())
    if not targets:
        return _reject([ReadOnlyAuditTaskRejectReason.MISSING_ASSIGNMENT])
    if len(targets) > MAX_READ_TARGETS:
        return _reject([ReadOnlyAuditTaskRejectReason.TOO_MANY_TARGETS])

    root = Path(repo_root).resolve()
    lane_id = str(assignment.get("lane_id") or "")
    if task_context.get("worker_mode") == "model_backed_0102":
        from modules.communication.moltbot_bridge.src.reddog_readonly_0102_audit_worker_runtime import (
            execute_model_backed_repo_code_audit,
        )

        return execute_model_backed_repo_code_audit(
            task_context=task_context,
            assignment=assignment,
            seed_targets=targets,
            task_id=task_id,
            repo_root=root,
            model_runner=model_runner,
            holoindex_adapter=holoindex_adapter,
            codeindex_adapter=codeindex_adapter,
            external_research_retriever=external_research_retriever,
            timeout_seconds=timeout_seconds,
        )

    snapshots: list[_ReadOnlyTargetSnapshot] = []
    for target in targets:
        safe_path = _resolve_safe_target(root, target)
        if safe_path is None:
            return _reject([ReadOnlyAuditTaskRejectReason.UNSAFE_TARGET])
        try:
            snapshots.append(_read_target_snapshot(root, safe_path))
        except Exception:
            return _reject([ReadOnlyAuditTaskRejectReason.TARGET_READ_FAILED])

    evidence = tuple(item.evidence for item in snapshots)
    report = _build_report(assignment=assignment, snapshots=snapshots)
    return ReadOnlyAuditTaskExecutionResult(
        accepted=True,
        decision=READONLY_AUDIT_TASK_REPORT_ACCEPT,
        report=report,
        evidence=evidence,
        rejection_reasons=(),
    )


def _resolve_safe_target(root: Path, target: str) -> Optional[Path]:
    normalized = str(target).replace("\\", "/").strip()
    while normalized.startswith("./"):
        normalized = normalized[2:]
    if not normalized or normalized.startswith("/") or normalized.startswith("../") or "/../" in normalized:
        return None
    if ":" in normalized or "\x00" in normalized:
        return None
    segments = tuple(segment for segment in normalized.split("/") if segment)
    if any(segment in DENIED_SEGMENTS for segment in segments):
        return None
    if not segments or segments[-1] in DENIED_BASENAMES:
        return None
    candidate = (root / normalized).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return None
    if not candidate.is_file() or candidate.is_symlink():
        return None
    return candidate


def _read_target_snapshot(root: Path, path: Path) -> _ReadOnlyTargetSnapshot:
    raw = path.read_bytes()
    truncated = len(raw) > MAX_READ_BYTES_PER_TARGET
    payload = raw[:MAX_READ_BYTES_PER_TARGET]
    digest = "sha256:" + hashlib.sha256(payload).hexdigest()
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError:
        text = payload.decode("utf-8", errors="replace")
    relative = path.relative_to(root).as_posix()
    return _ReadOnlyTargetSnapshot(
        evidence=ReadOnlyTargetEvidence(
            path=relative,
            digest=digest,
            bytes_read=len(payload),
            line_count=text.count("\n") + (1 if text else 0),
            truncated=truncated,
        ),
        text=text,
    )


def _build_report(
    *,
    assignment: Mapping[str, Any],
    snapshots: Sequence[_ReadOnlyTargetSnapshot],
) -> Mapping[str, Any]:
    lane_id = str(assignment.get("lane_id") or "")
    assignment_id = str(assignment.get("assignment_id") or "")
    evidence = tuple(item.evidence for item in snapshots)
    evidence_refs = tuple(
        f"file:{item.path}:{item.digest}:lines:{item.line_count}"
        for item in evidence
    )
    findings = _build_semantic_findings(lane_id=lane_id, snapshots=snapshots)
    return {
        "assignment_id": assignment_id,
        "lane_id": lane_id,
        "snapshot_receipt_id": str(assignment.get("snapshot_receipt_id") or ""),
        "summary": (
            f"{lane_id} read-only audit evidence collected from {len(evidence)} target(s); "
            "no mutation, shell, model, enqueue, or re-index performed."
        ),
        "evidence_refs": list(evidence_refs),
        "repo_mutation_performed": False,
        "execution_performed": False,
        "openclaw_enqueue_performed": False,
        "readonly_audit_performed": True,
        "target_evidence": [item.to_dict() for item in evidence],
        "findings": findings,
        "report_digest": "sha256:" + _digest(
            {
                "assignment_id": assignment_id,
                "lane_id": lane_id,
                "evidence_refs": evidence_refs,
                "findings": findings,
            }
        ),
    }


def _build_semantic_findings(
    *,
    lane_id: str,
    snapshots: Sequence[_ReadOnlyTargetSnapshot],
) -> list[Mapping[str, Any]]:
    evidence_refs = tuple(_evidence_ref(item.evidence) for item in snapshots)
    if not lane_id or not evidence_refs:
        return []
    reconciler_finding = _build_lane_reconciler_finding(lane_id=lane_id, snapshots=snapshots)
    if reconciler_finding is not None:
        return [reconciler_finding]
    return [
        {
            "finding_id": f"{lane_id}:lane_analyzer_missing",
            "claim": (
                f"{lane_id} collected read-only evidence, but the lane-specific "
                "semantic analyzer is not implemented in the deterministic executor."
            ),
            "wsp97_label": "SPECIFIED_NOT_IMPLEMENTED",
            "recommended_action": "FIX",
            "wsp15_priority": "P1",
            "severity": "MAJOR",
            "evidence_refs": list(evidence_refs),
            "next_slice_name": READONLY_AUDIT_LANE_ANALYZER_SLICE,
        }
    ]


def _build_lane_reconciler_finding(
    *,
    lane_id: str,
    snapshots: Sequence[_ReadOnlyTargetSnapshot],
) -> Optional[Mapping[str, Any]]:
    if lane_id not in LANE_RECONCILER_AUDIT_LANES:
        return None
    by_path = {item.evidence.path: item for item in snapshots}
    active = by_path.get(ACTIVE_SLICE_LEDGER_TARGET)
    ledger = by_path.get(WORK_LEDGER_TARGET)
    if active is None or ledger is None:
        return None

    report = reconcile_active_and_json_ledgers(
        active.text,
        ledger.text,
        now_iso="2026-07-14T00:00:00+00:00",
        stale_after_days=30,
    )
    evidence_refs = [_evidence_ref(active.evidence), _evidence_ref(ledger.evidence)]
    selected = report.prework_packet.chosen_slice
    if report.recommended_action == "NO_OPEN_WORK":
        action = "STOP"
        priority = "P4"
        severity = "INFO"
        next_slice = None
        claim = "Lane-state reconciliation found no open work in the provided ledgers."
    elif report.recommended_action == "CLAIM_NEXT_SLICE" and selected:
        action = "FIX"
        priority = "P1"
        severity = "MAJOR"
        next_slice = selected
        claim = f"Lane-state reconciliation selected next slice {selected}."
    elif report.recommended_action == "RECONCILE_LEDGER_BEFORE_WORK":
        action = "REVISE"
        priority = "P0"
        severity = "BLOCKER"
        next_slice = AUTHORITATIVE_WORK_STATE_REFRESH_SLICE
        claim = "Lane-state reconciliation found ledger conflicts that block worker assignment."
    else:
        action = "REVISE"
        priority = "P1"
        severity = "MAJOR"
        next_slice = AUTHORITATIVE_WORK_STATE_REFRESH_SLICE
        claim = f"Lane-state reconciliation returned {report.recommended_action} before work can continue."

    return {
        "finding_id": f"{lane_id}:lane_state_reconciliation:{report.recommended_action.lower()}",
        "claim": claim,
        "wsp97_label": "OBSERVED",
        "recommended_action": action,
        "wsp15_priority": priority,
        "severity": severity,
        "evidence_refs": evidence_refs,
        "next_slice_name": next_slice,
        "reconciliation_report_id": report.report_id,
        "next_wsp15_queue": list(report.next_wsp15_queue),
        "stale_sources": list(report.stale_sources),
        "conflict_count": len(report.conflicts),
    }


def _evidence_ref(item: ReadOnlyTargetEvidence) -> str:
    return f"file:{item.path}:{item.digest}:lines:{item.line_count}"


def _reject(reasons: Sequence[str]) -> ReadOnlyAuditTaskExecutionResult:
    return ReadOnlyAuditTaskExecutionResult(
        accepted=False,
        decision=READONLY_AUDIT_TASK_REPORT_REJECT,
        report=None,
        evidence=(),
        rejection_reasons=tuple(dict.fromkeys(str(reason) for reason in reasons)),
    )


def _digest(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


__all__ = [
    "READONLY_AUDIT_TASK_REPORT_ACCEPT",
    "READONLY_AUDIT_TASK_REPORT_REJECT",
    "READONLY_AUDIT_LANE_ANALYZER_SLICE",
    "AUTHORITATIVE_WORK_STATE_REFRESH_SLICE",
    "ReadOnlyAuditTaskExecutionResult",
    "ReadOnlyAuditTaskRejectReason",
    "ReadOnlyTargetEvidence",
    "execute_reddog_readonly_audit_task",
]
