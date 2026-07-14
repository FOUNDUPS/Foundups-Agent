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

from modules.communication.moltbot_bridge.src.reddog_openclaw_readonly_audit_swarm_enqueue import (
    READONLY_AUDIT_TASK_SOURCE,
)


READONLY_AUDIT_TASK_REPORT_ACCEPT = "READONLY_AUDIT_TASK_REPORT_ACCEPT"
READONLY_AUDIT_TASK_REPORT_REJECT = "READONLY_AUDIT_TASK_REPORT_REJECT"

MAX_READ_TARGETS = 32
MAX_READ_BYTES_PER_TARGET = 12_000
DENIED_BASENAMES = frozenset({".env", ".env.local", ".env.production", "id_rsa", "id_dsa"})
DENIED_SEGMENTS = frozenset({".git", ".ssh", ".aws", ".azure", ".gcp", "__pycache__"})


class ReadOnlyAuditTaskRejectReason:
    INVALID_CONTEXT = "REJECT_INVALID_CONTEXT"
    WRONG_SOURCE = "REJECT_WRONG_SOURCE"
    MISSING_ASSIGNMENT = "REJECT_MISSING_ASSIGNMENT"
    TOO_MANY_TARGETS = "REJECT_TOO_MANY_TARGETS"
    UNSAFE_TARGET = "REJECT_UNSAFE_TARGET"
    TARGET_READ_FAILED = "REJECT_TARGET_READ_FAILED"


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
) -> ReadOnlyAuditTaskExecutionResult:
    """Execute a RedDog read-only audit task using local file evidence only."""

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
    evidence: list[ReadOnlyTargetEvidence] = []
    for target in targets:
        safe_path = _resolve_safe_target(root, target)
        if safe_path is None:
            return _reject([ReadOnlyAuditTaskRejectReason.UNSAFE_TARGET])
        try:
            evidence.append(_read_target_evidence(root, safe_path))
        except Exception:
            return _reject([ReadOnlyAuditTaskRejectReason.TARGET_READ_FAILED])

    report = _build_report(assignment=assignment, evidence=evidence)
    return ReadOnlyAuditTaskExecutionResult(
        accepted=True,
        decision=READONLY_AUDIT_TASK_REPORT_ACCEPT,
        report=report,
        evidence=tuple(evidence),
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


def _read_target_evidence(root: Path, path: Path) -> ReadOnlyTargetEvidence:
    raw = path.read_bytes()
    truncated = len(raw) > MAX_READ_BYTES_PER_TARGET
    payload = raw[:MAX_READ_BYTES_PER_TARGET]
    digest = "sha256:" + hashlib.sha256(payload).hexdigest()
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError:
        text = payload.decode("utf-8", errors="replace")
    relative = path.relative_to(root).as_posix()
    return ReadOnlyTargetEvidence(
        path=relative,
        digest=digest,
        bytes_read=len(payload),
        line_count=text.count("\n") + (1 if text else 0),
        truncated=truncated,
    )


def _build_report(
    *,
    assignment: Mapping[str, Any],
    evidence: Sequence[ReadOnlyTargetEvidence],
) -> Mapping[str, Any]:
    lane_id = str(assignment.get("lane_id") or "")
    assignment_id = str(assignment.get("assignment_id") or "")
    evidence_refs = tuple(
        f"file:{item.path}:{item.digest}:lines:{item.line_count}"
        for item in evidence
    )
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
        "report_digest": "sha256:" + _digest(
            {
                "assignment_id": assignment_id,
                "lane_id": lane_id,
                "evidence_refs": evidence_refs,
            }
        ),
    }


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
    "ReadOnlyAuditTaskExecutionResult",
    "ReadOnlyAuditTaskRejectReason",
    "ReadOnlyTargetEvidence",
    "execute_reddog_readonly_audit_task",
]
