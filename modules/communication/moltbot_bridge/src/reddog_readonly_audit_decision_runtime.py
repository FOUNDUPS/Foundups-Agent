"""Deterministic decision gate for collected RedDog read-only audit reports.

Slice: REDDOG_READONLY_AUDIT_DECISION_RUNTIME_PHASE1

This module consumes an already validated read-only audit report collection and
emits the next-action decision receipt RedDog can display at startup. It does
not call models, execute commands, mutate repositories, enqueue OpenClaw work,
dispatch Hermes/WRE, create worktrees, or mutate/re-index HoloIndex.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any, Mapping, Optional, Sequence

from modules.communication.moltbot_bridge.src.reddog_readonly_audit_report_collection import (
    ReadOnlyAuditReportCollectionResult,
)


READONLY_AUDIT_DECISION_ACCEPT = "READONLY_AUDIT_DECISION_ACCEPT"
READONLY_AUDIT_DECISION_REJECT = "READONLY_AUDIT_DECISION_REJECT"

ACTION_FIX = "FIX"
ACTION_RESEARCH_MORE = "RESEARCH_MORE"
ACTION_REVISE = "REVISE"
ACTION_STOP = "STOP"
ACTION_WAIT_FOR_REPORTS = "WAIT_FOR_REPORTS"

DEFAULT_SEMANTIC_FINDINGS_SLICE = "REDDOG_READONLY_AUDIT_SEMANTIC_FINDINGS_PHASE1"

ALLOWED_ACTIONS = (ACTION_FIX, ACTION_RESEARCH_MORE, ACTION_REVISE, ACTION_STOP)
ALLOWED_WSP97_LABELS = ("OBSERVED", "INFERRED", "SPECIFIED_NOT_IMPLEMENTED", "NEEDS_VERIFICATION")
ALLOWED_PRIORITIES = ("P0", "P1", "P2", "P3", "P4")
ALLOWED_SEVERITIES = ("BLOCKER", "MAJOR", "MINOR", "INFO")

_ACTION_RANK = {ACTION_FIX: 0, ACTION_REVISE: 1, ACTION_RESEARCH_MORE: 2, ACTION_STOP: 3}
_PRIORITY_RANK = {priority: index for index, priority in enumerate(ALLOWED_PRIORITIES)}
_SEVERITY_RANK = {severity: index for index, severity in enumerate(ALLOWED_SEVERITIES)}


@dataclass(frozen=True)
class ReadOnlyAuditSemanticFinding:
    """Validated semantic finding extracted from one read-only audit report."""

    finding_id: str
    lane_id: str
    claim: str
    wsp97_label: str
    recommended_action: str
    wsp15_priority: str
    severity: str
    evidence_refs: tuple[str, ...]
    next_slice_name: Optional[str]
    finding_digest: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ReadOnlyAuditDecisionReceipt:
    """Next-action decision emitted after read-only audit report collection."""

    decision_id: str
    accepted: bool
    status: str
    action: str
    swarm_id: str
    report_bundle_id: Optional[str]
    report_count: int
    finding_count: int
    selected_finding_digest: Optional[str]
    next_slice_name: Optional[str]
    wsp15_priority: Optional[str]
    decision_reasons: tuple[str, ...]
    rejection_reasons: tuple[str, ...]
    finding_digests: tuple[str, ...]
    no_model_call_performed: bool = True
    no_shell_command_executed: bool = True
    no_repo_mutation_performed: bool = True
    no_holoindex_reindex_performed: bool = True
    no_openclaw_enqueue_performed: bool = True
    no_hermes_dispatch_performed: bool = True
    no_worktree_operation_performed: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def decide_reddog_readonly_audit_next_action(
    *,
    collection_result: ReadOnlyAuditReportCollectionResult,
    reports: Sequence[Mapping[str, Any]],
) -> ReadOnlyAuditDecisionReceipt:
    """Emit a deterministic next-action receipt from collected read-only reports."""

    bundle = collection_result.validation.bundle if collection_result.validation else None
    bundle_id = bundle.bundle_id if bundle else None
    reasons: list[str] = []
    decision_reasons: list[str] = []

    if not collection_result.accepted:
        reasons.extend(collection_result.rejection_reasons or ("collection_not_accepted",))
        return _receipt(
            accepted=False,
            action=ACTION_WAIT_FOR_REPORTS,
            swarm_id=collection_result.swarm_id,
            report_bundle_id=bundle_id,
            report_count=collection_result.report_count,
            findings=(),
            selected=None,
            next_slice_name=None,
            wsp15_priority=None,
            decision_reasons=("report_collection_not_accepted",),
            rejection_reasons=_dedupe(reasons),
        )

    if collection_result.report_count != len(reports):
        reasons.append("report_count_mismatch")

    findings: list[ReadOnlyAuditSemanticFinding] = []
    for report_index, report in enumerate(reports):
        if not isinstance(report, Mapping):
            reasons.append(f"report_not_mapping:{report_index}")
            continue
        findings.extend(_extract_report_findings(report=report, report_index=report_index, reasons=reasons))

    reasons = list(_dedupe(reasons))
    if reasons:
        return _receipt(
            accepted=False,
            action=ACTION_WAIT_FOR_REPORTS,
            swarm_id=collection_result.swarm_id,
            report_bundle_id=bundle_id,
            report_count=collection_result.report_count,
            findings=tuple(findings),
            selected=None,
            next_slice_name=None,
            wsp15_priority=None,
            decision_reasons=("semantic_finding_validation_failed",),
            rejection_reasons=tuple(reasons),
        )

    if not findings:
        return _receipt(
            accepted=True,
            action=ACTION_RESEARCH_MORE,
            swarm_id=collection_result.swarm_id,
            report_bundle_id=bundle_id,
            report_count=collection_result.report_count,
            findings=(),
            selected=None,
            next_slice_name=DEFAULT_SEMANTIC_FINDINGS_SLICE,
            wsp15_priority="P1",
            decision_reasons=("semantic_findings_missing",),
            rejection_reasons=(),
        )

    selected = sorted(findings, key=_finding_sort_key)[0]
    return _receipt(
        accepted=True,
        action=selected.recommended_action,
        swarm_id=collection_result.swarm_id,
        report_bundle_id=bundle_id,
        report_count=collection_result.report_count,
        findings=tuple(findings),
        selected=selected,
        next_slice_name=selected.next_slice_name,
        wsp15_priority=selected.wsp15_priority,
        decision_reasons=(f"selected:{selected.finding_id}",),
        rejection_reasons=(),
    )


def _extract_report_findings(
    *,
    report: Mapping[str, Any],
    report_index: int,
    reasons: list[str],
) -> tuple[ReadOnlyAuditSemanticFinding, ...]:
    lane_id = str(report.get("lane_id") or "").strip()
    report_refs = _normalize_refs(report.get("evidence_refs"))
    raw_findings = report.get("findings") or ()
    if isinstance(raw_findings, (str, bytes)) or not isinstance(raw_findings, Sequence):
        reasons.append(f"findings_not_sequence:{lane_id or report_index}")
        return ()

    findings: list[ReadOnlyAuditSemanticFinding] = []
    for finding_index, raw in enumerate(raw_findings):
        if not isinstance(raw, Mapping):
            reasons.append(f"finding_not_mapping:{lane_id or report_index}:{finding_index}")
            continue
        finding = _coerce_finding(raw, lane_id=lane_id, report_refs=report_refs, reasons=reasons)
        if finding is not None:
            findings.append(finding)
    return tuple(findings)


def _coerce_finding(
    raw: Mapping[str, Any],
    *,
    lane_id: str,
    report_refs: tuple[str, ...],
    reasons: list[str],
) -> Optional[ReadOnlyAuditSemanticFinding]:
    finding_id = str(raw.get("finding_id") or "").strip()
    claim = str(raw.get("claim") or "").strip()
    wsp97_label = str(raw.get("wsp97_label") or "").strip().upper()
    action = str(raw.get("recommended_action") or "").strip().upper()
    priority = str(raw.get("wsp15_priority") or "").strip().upper()
    severity = str(raw.get("severity") or "INFO").strip().upper()
    next_slice = str(raw.get("next_slice_name") or "").strip() or None
    evidence_refs = _normalize_refs(raw.get("evidence_refs"))
    scope = finding_id or f"{lane_id}:unknown"
    local_reasons: list[str] = []

    if not finding_id:
        local_reasons.append(f"finding_missing_id:{lane_id}")
    if not lane_id:
        local_reasons.append(f"finding_missing_lane:{scope}")
    if not claim:
        local_reasons.append(f"finding_missing_claim:{scope}")
    if wsp97_label not in ALLOWED_WSP97_LABELS:
        local_reasons.append(f"finding_bad_wsp97_label:{scope}")
    if action not in ALLOWED_ACTIONS:
        local_reasons.append(f"finding_bad_action:{scope}")
    if priority not in ALLOWED_PRIORITIES:
        local_reasons.append(f"finding_bad_wsp15_priority:{scope}")
    if severity not in ALLOWED_SEVERITIES:
        local_reasons.append(f"finding_bad_severity:{scope}")
    if action in {ACTION_FIX, ACTION_RESEARCH_MORE, ACTION_REVISE} and not next_slice:
        local_reasons.append(f"finding_missing_next_slice:{scope}")
    if not evidence_refs and wsp97_label != "NEEDS_VERIFICATION":
        local_reasons.append(f"finding_missing_evidence:{scope}")
    if wsp97_label == "NEEDS_VERIFICATION" and action != ACTION_RESEARCH_MORE:
        local_reasons.append(f"finding_needs_verification_not_research_more:{scope}")
    if evidence_refs and not set(evidence_refs).issubset(set(report_refs)):
        local_reasons.append(f"finding_evidence_not_in_report:{scope}")

    if local_reasons:
        reasons.extend(local_reasons)
        return None

    payload = {
        "finding_id": finding_id,
        "lane_id": lane_id,
        "claim": claim,
        "wsp97_label": wsp97_label,
        "recommended_action": action,
        "wsp15_priority": priority,
        "severity": severity,
        "evidence_refs": evidence_refs,
        "next_slice_name": next_slice,
    }
    return ReadOnlyAuditSemanticFinding(
        finding_id=finding_id,
        lane_id=lane_id,
        claim=claim,
        wsp97_label=wsp97_label,
        recommended_action=action,
        wsp15_priority=priority,
        severity=severity,
        evidence_refs=evidence_refs,
        next_slice_name=next_slice,
        finding_digest=_digest(payload),
    )


def _receipt(
    *,
    accepted: bool,
    action: str,
    swarm_id: str,
    report_bundle_id: Optional[str],
    report_count: int,
    findings: Sequence[ReadOnlyAuditSemanticFinding],
    selected: Optional[ReadOnlyAuditSemanticFinding],
    next_slice_name: Optional[str],
    wsp15_priority: Optional[str],
    decision_reasons: Sequence[str],
    rejection_reasons: Sequence[str],
) -> ReadOnlyAuditDecisionReceipt:
    finding_digests = tuple(sorted(finding.finding_digest for finding in findings))
    payload = {
        "accepted": accepted,
        "action": action,
        "swarm_id": swarm_id,
        "report_bundle_id": report_bundle_id,
        "report_count": report_count,
        "finding_digests": finding_digests,
        "selected_finding_digest": selected.finding_digest if selected else None,
        "next_slice_name": next_slice_name,
        "wsp15_priority": wsp15_priority,
        "decision_reasons": list(decision_reasons),
        "rejection_reasons": list(rejection_reasons),
    }
    return ReadOnlyAuditDecisionReceipt(
        decision_id=_digest(payload),
        accepted=accepted,
        status=READONLY_AUDIT_DECISION_ACCEPT if accepted else READONLY_AUDIT_DECISION_REJECT,
        action=action,
        swarm_id=swarm_id,
        report_bundle_id=report_bundle_id,
        report_count=report_count,
        finding_count=len(findings),
        selected_finding_digest=selected.finding_digest if selected else None,
        next_slice_name=next_slice_name,
        wsp15_priority=wsp15_priority,
        decision_reasons=tuple(decision_reasons),
        rejection_reasons=tuple(rejection_reasons),
        finding_digests=finding_digests,
    )


def _finding_sort_key(finding: ReadOnlyAuditSemanticFinding) -> tuple[int, int, int, str]:
    return (
        _ACTION_RANK.get(finding.recommended_action, 99),
        _PRIORITY_RANK.get(finding.wsp15_priority, 99),
        _SEVERITY_RANK.get(finding.severity, 99),
        finding.finding_id,
    )


def _normalize_refs(value: Any) -> tuple[str, ...]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        return ()
    return tuple(dict.fromkeys(str(item).strip() for item in value if str(item).strip()))


def _dedupe(values: Sequence[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(str(value) for value in values if str(value).strip()))


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)


def _digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


__all__ = [
    "ACTION_FIX",
    "ACTION_RESEARCH_MORE",
    "ACTION_REVISE",
    "ACTION_STOP",
    "ACTION_WAIT_FOR_REPORTS",
    "DEFAULT_SEMANTIC_FINDINGS_SLICE",
    "READONLY_AUDIT_DECISION_ACCEPT",
    "READONLY_AUDIT_DECISION_REJECT",
    "ReadOnlyAuditDecisionReceipt",
    "ReadOnlyAuditSemanticFinding",
    "decide_reddog_readonly_audit_next_action",
]
