"""Prompt schema and shape validation for backend architect proposals."""

from __future__ import annotations

import json
from typing import Any, Mapping, Sequence

from modules.communication.moltbot_bridge.src.reddog_architect_proposal_admission_contract import (
    ArchitectProposalAdmissionPolicy,
    proposal_admission_prompt_policy,
)
from modules.communication.moltbot_bridge.src.reddog_operational_context_snapshot import (
    OperationalContextSnapshot,
)


VALIDATION_INVALID_OUTPUT = "invalid_model_output"
VALIDATION_WSP15_MISMATCH = "wsp15_receipt_mismatch"


def build_architect_proposal_prompt(
    *,
    snapshot: OperationalContextSnapshot,
    report_bundle_id: str | None,
    report_views: Sequence[Mapping[str, Any]],
    wsp15_allocation_receipt: Mapping[str, Any],
    proposal_admission_policy: ArchitectProposalAdmissionPolicy,
    max_chars: int,
) -> str:
    payload = {
        "task": "Return one backend RedDog architect determination as strict JSON only.",
        "required_fields": [
            "action", "next_slice_name", "summary", "decision_reasons",
            "evidence_refs", "wsp15_allocation_receipt_id", "reuse_decision",
            "requested_operation", "target_runtime", "target_effect_plane",
            "allowed_paths", "denied_paths", "required_tests",
            "required_policy_gates", "required_capabilities",
            "produced_capabilities", "expected_evidence", "stop_conditions",
        ],
        "rules": _PROMPT_RULES,
        "snapshot_receipt_id": snapshot.snapshot_receipt_id,
        "snapshot_content_digest": snapshot.snapshot_content_digest,
        "work_state_revision": snapshot.work_state.get("revision"),
        "repo_head_sha": snapshot.repo_state.get("head_sha"),
        "audit_report_collection": {
            "accepted": True,
            "report_count": len(report_views),
            "bundle_id": report_bundle_id,
        },
        "wsp15_allocation_receipt_id": wsp15_allocation_receipt.get("receipt_id"),
        "wsp15_execution_binding": {
            "requested_operation": wsp15_allocation_receipt.get("requested_operation"),
            "changed_paths": list(wsp15_allocation_receipt.get("changed_paths") or ()),
            "allowed_read_targets": list(
                wsp15_allocation_receipt.get("allowed_read_targets") or ()
            ),
            "prompt_digest": wsp15_allocation_receipt.get("prompt_digest"),
        },
        "proposal_admission_policy": proposal_admission_prompt_policy(
            snapshot=snapshot,
            policy=proposal_admission_policy,
        ),
        "reports": list(report_views),
    }
    return _budgeted_json(payload, max_chars=max_chars)


def validate_architect_proposal_output(
    output: Mapping[str, Any],
    *,
    reports: Sequence[Mapping[str, Any]],
    wsp15_allocation_receipt_id: str | None,
) -> tuple[str, ...]:
    if not output:
        return (VALIDATION_INVALID_OUTPUT,)
    reasons: list[str] = []
    action = _text(output.get("action")).upper()
    next_slice = _text(output.get("next_slice_name"))
    evidence_refs = _texts(output.get("evidence_refs"))
    if not _base_shape_valid(output, action=action, next_slice=next_slice):
        reasons.append(VALIDATION_INVALID_OUTPUT)
    report_refs = _report_evidence_refs(reports)
    if not evidence_refs or not set(evidence_refs).issubset(report_refs):
        reasons.append(VALIDATION_INVALID_OUTPUT)
    if _text(output.get("wsp15_allocation_receipt_id")) != _text(
        wsp15_allocation_receipt_id
    ):
        reasons.append(VALIDATION_WSP15_MISMATCH)
    return tuple(dict.fromkeys(reasons))


_PROMPT_RULES = [
    "Use FIX only for one audit-supported proposal; code derives whether it is executable now.",
    "Use RESEARCH_MORE when evidence is insufficient.",
    "Use REVISE when a valid direction has implementation, configuration, platform, or policy blockers.",
    "Use STOP when no next work should be queued.",
    "Use only evidence_refs present in the supplied audit reports.",
    "Configuration cannot satisfy a missing implementation trust anchor.",
    "An INDEX_GAP or unconfirmed defect must not produce FIX.",
    "Current draft-PR capability is not merge authority.",
    "Declare every capability required to execute the slice and every capability the slice produces.",
    "Produced capabilities are outputs, never current authority.",
    "Specify exact paths, tests, evidence, and stop conditions for effectful work.",
    "Echo the supplied WSP15 allocation receipt id exactly.",
]


def _base_shape_valid(
    output: Mapping[str, Any],
    *,
    action: str,
    next_slice: str,
) -> bool:
    sequence_fields = (
        "evidence_refs", "decision_reasons", "allowed_paths", "denied_paths",
        "required_tests", "required_policy_gates", "required_capabilities",
        "produced_capabilities", "expected_evidence", "stop_conditions",
    )
    actions = {"FIX", "RESEARCH_MORE", "REVISE", "STOP"}
    return (
        action in actions
        and (
            _valid_slice_name(next_slice)
            if action in {"FIX", "RESEARCH_MORE", "REVISE"}
            else not next_slice
        )
        and bool(_text(output.get("summary")))
        and bool(_text(output.get("reuse_decision")))
        and bool(_text(output.get("requested_operation")))
        and bool(_text(output.get("target_runtime")))
        and bool(_text(output.get("target_effect_plane")))
        and all(_is_sequence(output.get(field)) for field in sequence_fields)
    )


def _report_evidence_refs(reports: Sequence[Mapping[str, Any]]) -> set[str]:
    refs: set[str] = set()
    for report in reports:
        refs.update(_texts(report.get("evidence_refs")))
        findings = report.get("findings")
        if not _is_sequence(findings):
            continue
        for finding in findings:
            if isinstance(finding, Mapping):
                refs.update(_texts(finding.get("evidence_refs")))
    return refs


def _budgeted_json(value: Mapping[str, Any], *, max_chars: int) -> str:
    text = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )
    if len(text) > max_chars:
        raise ValueError("architect_prompt_budget_exceeded")
    return text


def _texts(value: Any) -> tuple[str, ...]:
    if not _is_sequence(value):
        return ()
    return tuple(dict.fromkeys(_text(item) for item in value if _text(item)))


def _is_sequence(value: Any) -> bool:
    return not isinstance(value, (str, bytes)) and isinstance(value, Sequence)


def _valid_slice_name(value: str) -> bool:
    return (
        value.endswith("_PHASE1")
        and value.replace("_", "").isalnum()
        and value.upper() == value
    )


def _text(value: Any) -> str:
    return str(value or "").strip()


__all__ = [
    "VALIDATION_INVALID_OUTPUT",
    "VALIDATION_WSP15_MISMATCH",
    "build_architect_proposal_prompt",
    "validate_architect_proposal_output",
]
