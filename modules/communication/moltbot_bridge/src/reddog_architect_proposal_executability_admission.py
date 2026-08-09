"""Deterministic validity and readiness admission for architect proposals."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from modules.communication.moltbot_bridge.src.reddog_architect_proposal_admission_contract import (
    ArchitectProposalAdmissionPolicy,
    ArchitectProposalExecutabilityReceipt,
    CREATE_NEW,
    EFFECT_CONFIGURATION_ONLY,
    EFFECT_DRAFT_PR_PUBLISH,
    EFFECT_EXTERNAL,
    EFFECT_LIVE_WORKTREE_CANARY,
    EFFECT_MERGE,
    EFFECT_NONE,
    EFFECT_READ_ONLY_AUDIT,
    EFFECT_REPOSITORY_CODE_CHANGE,
    EXECUTION_READINESS_STATES,
    EXTEND_EXISTING,
    LIVE_EXECUTION_CAPABILITIES,
    PROPOSAL_ADMISSION_SCHEMA_VERSION,
    PROPOSAL_VALIDITIES,
    READINESS_CONFIGURATION_BLOCKED,
    READINESS_EVIDENCE_BLOCKED,
    READINESS_IMPLEMENTATION_BLOCKED,
    READINESS_PLATFORM_BLOCKED,
    READINESS_POLICY_BLOCKED,
    READINESS_READY,
    REUSE_DECISIONS,
    REUSE_EXISTING,
    TARGET_EFFECT_PLANES,
    VALIDITY_INVALID,
    VALIDITY_NEEDS_RESEARCH,
    VALIDITY_VALID,
    current_architect_proposal_admission_policy,
    proposal_admission_prompt_policy,
    reevaluate_architect_proposal_execution_readiness,
    reevaluate_architect_proposal_promotion_preconditions,
    required_capabilities_for_effect,
    validate_architect_proposal_executability_receipt,
)
from modules.communication.moltbot_bridge.src.reddog_operational_context_snapshot import (
    OperationalContextSnapshot,
)
from modules.communication.moltbot_bridge.src.reddog_progressive_execution_stage_policy import (
    DECISION_BOUNDED_EXECUTION_ADMITTED,
    ProgressiveExecutionStageReceipt,
    evaluate_proposal_stage,
)


@dataclass(frozen=True)
class _Proposal:
    action: str
    slice_id: str | None
    summary: str
    reuse_decision: str
    requested_operation: str
    target_runtime: str
    effect_plane: str
    allowed_paths: tuple[str, ...]
    denied_paths: tuple[str, ...]
    required_tests: tuple[str, ...]
    policy_gates: tuple[str, ...]
    required_capabilities: tuple[str, ...]
    produced_capabilities: tuple[str, ...]
    expected_evidence: tuple[str, ...]
    stop_conditions: tuple[str, ...]
    declared_reasons: tuple[str, ...]
    invalid_path_tokens: bool


@dataclass(frozen=True)
class _Support:
    finding_ids: tuple[str, ...]
    conflicts: tuple[str, ...]
    direct_read_grounded: bool
    direct_read_paths: tuple[str, ...]


@dataclass(frozen=True)
class _Decision:
    validity: str
    readiness: str
    admissible: bool
    validity_reasons: tuple[str, ...]
    missing_preconditions: tuple[str, ...]


def evaluate_architect_proposal_executability(
    *,
    model_output: Mapping[str, Any],
    snapshot: OperationalContextSnapshot,
    reports: Sequence[Mapping[str, Any]],
    report_bundle_id: str | None,
    wsp15_allocation_receipt: Mapping[str, Any],
    policy: ArchitectProposalAdmissionPolicy | None = None,
    conversation_binding: Mapping[str, Any] | None = None,
) -> ArchitectProposalExecutabilityReceipt:
    """Validate proposal structure and derive current execution readiness."""

    current_policy = policy or current_architect_proposal_admission_policy()
    proposal = _proposal(model_output)
    support = _proposal_support(reports=reports, slice_id=proposal.slice_id)
    decision = _decision(
        proposal=proposal,
        snapshot=snapshot,
        support=support,
        policy=current_policy,
    )
    return _receipt(
        proposal=proposal,
        snapshot=snapshot,
        support=support,
        decision=decision,
        report_bundle_id=report_bundle_id,
        wsp15_allocation_receipt=wsp15_allocation_receipt,
        policy=current_policy,
        conversation_binding=conversation_binding,
    )


def _proposal(value: Mapping[str, Any]) -> _Proposal:
    return _Proposal(
        action=_text(value.get("action")).upper(),
        slice_id=_text(value.get("next_slice_name")) or None,
        summary=_text(value.get("summary")),
        reuse_decision=_text(value.get("reuse_decision")).upper(),
        requested_operation=_text(value.get("requested_operation")).lower(),
        target_runtime=_text(value.get("target_runtime")).lower(),
        effect_plane=_text(value.get("target_effect_plane")).upper(),
        allowed_paths=_normalize_paths(value.get("allowed_paths")),
        denied_paths=_normalize_paths(value.get("denied_paths")),
        required_tests=_normalize_texts(value.get("required_tests")),
        policy_gates=_normalize_texts(value.get("required_policy_gates")),
        required_capabilities=_normalize_texts(value.get("required_capabilities")),
        produced_capabilities=_normalize_texts(value.get("produced_capabilities")),
        expected_evidence=_normalize_texts(value.get("expected_evidence")),
        stop_conditions=_normalize_texts(value.get("stop_conditions")),
        declared_reasons=_normalize_texts(value.get("decision_reasons")),
        invalid_path_tokens=(
            _has_invalid_paths(value.get("allowed_paths"))
            or _has_invalid_paths(value.get("denied_paths"))
        ),
    )


def _decision(
    *,
    proposal: _Proposal,
    snapshot: OperationalContextSnapshot,
    support: _Support,
    policy: ArchitectProposalAdmissionPolicy,
) -> _Decision:
    reasons = _validity_reasons(proposal, snapshot=snapshot, support=support)
    validity = _validity(reasons)
    blockers = _readiness_blockers(
        proposal=proposal,
        snapshot=snapshot,
        support=support,
        policy=policy,
    )
    readiness, missing = _readiness(validity=validity, blockers=blockers)
    return _Decision(
        validity=validity,
        readiness=readiness,
        admissible=(
            proposal.action == "FIX"
            and validity == VALIDITY_VALID
            and readiness == READINESS_READY
        ),
        validity_reasons=reasons,
        missing_preconditions=missing,
    )


def _validity_reasons(
    proposal: _Proposal,
    *,
    snapshot: OperationalContextSnapshot,
    support: _Support,
) -> tuple[str, ...]:
    reasons = [*_shape_reasons(proposal), *_snapshot_reasons(snapshot)]
    if proposal.action == "FIX" and not support.finding_ids:
        reasons.append("proposal_not_supported_by_observed_fix_finding")
    if proposal.action == "FIX" and support.conflicts:
        reasons.append("conflicting_audit_finding")
    required = required_capabilities_for_effect(proposal.effect_plane)
    if not required.issubset(proposal.required_capabilities):
        reasons.append("effect_capability_requirements_underdeclared")
    return _dedupe(reasons)


def _shape_reasons(proposal: _Proposal) -> tuple[str, ...]:
    reasons: list[str] = []
    if proposal.action == "FIX" and (
        not proposal.slice_id or not _valid_slice_name(proposal.slice_id)
    ):
        reasons.append("slice_id_invalid")
    if proposal.reuse_decision not in REUSE_DECISIONS:
        reasons.append("reuse_decision_invalid")
    if proposal.effect_plane not in TARGET_EFFECT_PLANES:
        reasons.append("target_effect_plane_invalid")
    if proposal.action == "STOP" and proposal.effect_plane != EFFECT_NONE:
        reasons.append("stop_effect_plane_must_be_none")
    if proposal.action != "STOP" and proposal.effect_plane == EFFECT_NONE:
        reasons.append("non_stop_effect_plane_missing")
    if _effectful_contract_incomplete(proposal):
        reasons.append("effectful_proposal_contract_incomplete")
    if set(proposal.allowed_paths).intersection(proposal.denied_paths):
        reasons.append("allowed_denied_path_overlap")
    if proposal.invalid_path_tokens:
        reasons.append("repository_path_token_invalid")
    if (
        proposal.reuse_decision == CREATE_NEW
        and proposal.effect_plane != EFFECT_READ_ONLY_AUDIT
    ):
        reasons.append("create_new_requires_separate_architecture_gate")
    return tuple(reasons)


def _effectful_contract_incomplete(proposal: _Proposal) -> bool:
    if proposal.action != "FIX" or proposal.effect_plane == EFFECT_READ_ONLY_AUDIT:
        return False
    required = (
        proposal.requested_operation,
        proposal.target_runtime,
        proposal.allowed_paths,
        proposal.denied_paths,
        proposal.required_tests,
        proposal.policy_gates,
        proposal.expected_evidence,
        proposal.stop_conditions,
    )
    return any(not item for item in required)


def _snapshot_reasons(snapshot: OperationalContextSnapshot) -> tuple[str, ...]:
    reasons: list[str] = []
    if not snapshot.snapshot_receipt_id or not snapshot.snapshot_content_digest:
        reasons.append("operational_snapshot_binding_missing")
    repo_head = _text(snapshot.repo_state.get("head_sha"))
    if not repo_head or repo_head.lower() == "unknown":
        reasons.append("repository_head_unknown")
    if not _text(snapshot.work_state.get("revision")):
        reasons.append("work_state_revision_missing")
    return tuple(reasons)


def _readiness_blockers(
    *,
    proposal: _Proposal,
    snapshot: OperationalContextSnapshot,
    support: _Support,
    policy: ArchitectProposalAdmissionPolicy,
) -> Mapping[str, tuple[str, ...]]:
    index_gap = snapshot.holoindex_state.get("freshness_ok") is not True
    holo_exception = _is_holo_maintenance_proposal(proposal, support)
    missing = required_capabilities_for_effect(proposal.effect_plane).union(
        proposal.required_capabilities
    ).difference(
        policy.available_capabilities
    )
    return {
        READINESS_EVIDENCE_BLOCKED: (
            ("holoindex_index_gap",) if index_gap and not holo_exception else ()
        ),
        READINESS_PLATFORM_BLOCKED: _platform_blockers(proposal, policy),
        READINESS_POLICY_BLOCKED: _policy_blockers(proposal, policy),
        READINESS_CONFIGURATION_BLOCKED: (),
        READINESS_IMPLEMENTATION_BLOCKED: tuple(
            policy.missing_capability_reasons.get(
                capability, f"required_capability_unavailable:{capability}"
            )
            for capability in sorted(missing)
        ),
    }


def _platform_blockers(
    proposal: _Proposal,
    policy: ArchitectProposalAdmissionPolicy,
) -> tuple[str, ...]:
    if (
        proposal.effect_plane == EFFECT_LIVE_WORKTREE_CANARY
        and policy.platform not in policy.live_canary_platforms
    ):
        return (f"live_canary_platform_unsupported:{policy.platform}",)
    return ()


def _policy_blockers(
    proposal: _Proposal,
    policy: ArchitectProposalAdmissionPolicy,
) -> tuple[str, ...]:
    reasons: list[str] = []
    if proposal.effect_plane == EFFECT_MERGE and not policy.merge_authority_available:
        reasons.append("merge_authority_unavailable")
    if (
        proposal.effect_plane == EFFECT_EXTERNAL
        and not policy.external_effect_authority_available
    ):
        reasons.append("external_effect_authority_unavailable")
    return tuple(reasons)


def _validity(reasons: Sequence[str]) -> str:
    research_reasons = {
        "proposal_not_supported_by_observed_fix_finding",
        "conflicting_audit_finding",
    }
    if reasons and all(reason in research_reasons for reason in reasons):
        return VALIDITY_NEEDS_RESEARCH
    return VALIDITY_INVALID if reasons else VALIDITY_VALID


def _readiness(
    *,
    validity: str,
    blockers: Mapping[str, tuple[str, ...]],
) -> tuple[str, tuple[str, ...]]:
    if validity != VALIDITY_VALID:
        return READINESS_EVIDENCE_BLOCKED, (
            f"proposal_validity_not_ready:{validity}",
        )
    for status in (
        READINESS_EVIDENCE_BLOCKED,
        READINESS_PLATFORM_BLOCKED,
        READINESS_POLICY_BLOCKED,
        READINESS_CONFIGURATION_BLOCKED,
        READINESS_IMPLEMENTATION_BLOCKED,
    ):
        if blockers[status]:
            return status, _dedupe(blockers[status])
    return READINESS_READY, ()


def _receipt(
    *,
    proposal: _Proposal,
    snapshot: OperationalContextSnapshot,
    support: _Support,
    decision: _Decision,
    report_bundle_id: str | None,
    wsp15_allocation_receipt: Mapping[str, Any],
    policy: ArchitectProposalAdmissionPolicy,
    conversation_binding: Mapping[str, Any] | None,
) -> ArchitectProposalExecutabilityReceipt:
    stage = evaluate_proposal_stage(
        action=proposal.action,
        reuse_decision=proposal.reuse_decision,
        effect_plane=proposal.effect_plane,
        allocation=wsp15_allocation_receipt,
        selected_slice=proposal.slice_id or "",
        requested_operation=proposal.requested_operation,
        changed_paths=proposal.allowed_paths,
        would_block_reasons=decision.missing_preconditions,
    )
    payload = {
        **_receipt_contract(proposal),
        **_receipt_decision(proposal, decision, stage),
        **_receipt_bindings(
            proposal=proposal,
            support=support,
            snapshot=snapshot,
            report_bundle_id=report_bundle_id,
            wsp15_allocation_receipt=wsp15_allocation_receipt,
            policy=policy,
            conversation_binding=conversation_binding,
        ),
        "supporting_finding_ids": list(support.finding_ids),
        "supporting_direct_read_paths": list(support.direct_read_paths),
        **_stage_fields(stage),
        "rejection_reasons": (
            [] if decision.validity == VALIDITY_VALID else list(decision.validity_reasons)
        ),
        "no_queue_mutation_performed": True,
        "no_execution_performed": True,
        "no_repo_mutation_performed": True,
        "no_holoindex_reindex_performed": True,
    }
    return _typed_receipt(payload)


def _receipt_contract(proposal: _Proposal) -> dict[str, Any]:
    return {
        "schema_version": PROPOSAL_ADMISSION_SCHEMA_VERSION,
        "action": proposal.action,
        "slice_id": proposal.slice_id,
        "task_summary_digest": _digest(proposal.summary),
        "reuse_decision": proposal.reuse_decision,
        "requested_operation": proposal.requested_operation,
        "target_runtime": proposal.target_runtime,
        "target_effect_plane": proposal.effect_plane,
        "allowed_paths": list(proposal.allowed_paths),
        "denied_paths": list(proposal.denied_paths),
        "required_tests": list(proposal.required_tests),
        "required_policy_gates": list(proposal.policy_gates),
        "required_capabilities": list(proposal.required_capabilities),
        "produced_capabilities": list(proposal.produced_capabilities),
        "expected_evidence": list(proposal.expected_evidence),
        "stop_conditions": list(proposal.stop_conditions),
    }


def _receipt_decision(
    proposal: _Proposal,
    decision: _Decision,
    stage: ProgressiveExecutionStageReceipt,
) -> dict[str, Any]:
    produced_warnings = (
        "produced_capability_is_output_not_current_authority:" + capability
        for capability in proposal.produced_capabilities
        if decision.readiness == READINESS_IMPLEMENTATION_BLOCKED
        and capability in proposal.required_capabilities
    )
    return {
        "accepted": decision.validity == VALIDITY_VALID,
        "proposal_validity": decision.validity,
        "execution_readiness": decision.readiness,
        "admissible_to_authoritative_queue": (
            decision.admissible
            and stage.decision == DECISION_BOUNDED_EXECUTION_ADMITTED
        ),
        "missing_preconditions": list(decision.missing_preconditions),
        "decision_reasons": list(
            _dedupe(
                (
                    *proposal.declared_reasons,
                    *decision.validity_reasons,
                    *decision.missing_preconditions,
                    *produced_warnings,
                )
            )
        ),
    }


def _receipt_bindings(
    *,
    proposal: _Proposal,
    support: _Support,
    snapshot: OperationalContextSnapshot,
    report_bundle_id: str | None,
    wsp15_allocation_receipt: Mapping[str, Any],
    policy: ArchitectProposalAdmissionPolicy,
    conversation_binding: Mapping[str, Any] | None,
) -> dict[str, Any]:
    return {
        "snapshot_receipt_id": snapshot.snapshot_receipt_id,
        "snapshot_content_digest": snapshot.snapshot_content_digest,
        "repo_head_sha": _text(snapshot.repo_state.get("head_sha")),
        "work_state_revision": _text(snapshot.work_state.get("revision")),
        "holoindex_generation_id": _text(
            snapshot.holoindex_state.get("generation_id")
        ),
        "holoindex_freshness_receipt_digest": _text(
            snapshot.holoindex_state.get("receipt_digest")
        ),
        "index_gap_detected": snapshot.holoindex_state.get("freshness_ok") is not True,
        "direct_read_grounded": support.direct_read_grounded,
        "holoindex_maintenance_exception_applied": (
            snapshot.holoindex_state.get("freshness_ok") is not True
            and _is_holo_maintenance_proposal(proposal, support)
        ),
        "report_bundle_id": _text(report_bundle_id),
        "wsp15_allocation_receipt_id": _text(
            wsp15_allocation_receipt.get("receipt_id")
        ),
        "wsp15_allocation_digest": _digest(wsp15_allocation_receipt),
        "wsp15_complexity": wsp15_allocation_receipt.get("complexity"),
        "policy_digest": _digest(policy.to_dict()),
        **_conversation_bindings(conversation_binding),
    }


def _stage_fields(
    stage: ProgressiveExecutionStageReceipt,
) -> dict[str, Any]:
    return {
        "progressive_policy_stage": stage.stage,
        "progressive_policy_decision": stage.decision,
        "progressive_policy_stage_receipt_id": stage.receipt_id,
        "progressive_policy_stage_receipt": stage.to_dict(),
        "progressive_policy_would_block_reasons": list(
            stage.would_block_reasons
        ),
        "independent_verifier_required": (
            stage.independent_verifier_required
        ),
    }


def _conversation_bindings(
    value: Mapping[str, Any] | None,
) -> dict[str, Any]:
    fields = (
        "conversation_binding_digest",
        "conversation_id",
        "conversation_revision",
        "conversation_revision_receipt_id",
        "conversation_scope_record_digest",
        "authorized_foundup_id",
        "resident_intent_id",
        "resident_intent_digest",
        "conversation_grounding_receipt_id",
    )
    if not isinstance(value, Mapping):
        return {
            "conversation_binding_present": False,
            **{field: (-1 if field == "conversation_revision" else "") for field in fields},
        }
    return {
        "conversation_binding_present": True,
        **{field: value.get(field) for field in fields},
    }


def _typed_receipt(payload: Mapping[str, Any]) -> ArchitectProposalExecutabilityReceipt:
    values = dict(payload)
    tuple_fields = (
        "allowed_paths", "denied_paths", "required_tests", "required_policy_gates",
        "required_capabilities", "produced_capabilities", "expected_evidence",
        "stop_conditions", "missing_preconditions", "decision_reasons",
        "supporting_finding_ids", "rejection_reasons",
        "supporting_direct_read_paths",
        "progressive_policy_would_block_reasons",
    )
    for field in tuple_fields:
        values[field] = tuple(values[field])
    receipt = ArchitectProposalExecutabilityReceipt(
        receipt_id=_digest(payload),
        **values,
    )
    return validate_architect_proposal_executability_receipt(receipt.to_dict())


def _proposal_support(
    *,
    reports: Sequence[Mapping[str, Any]],
    slice_id: str | None,
) -> _Support:
    support: list[str] = []
    conflicts: list[str] = []
    direct_read_paths: list[str] = []
    for report in reports:
        report_refs = set(_normalize_texts(report.get("evidence_refs")))
        for finding in _findings(report):
            if _text(finding.get("next_slice_name")) != _text(slice_id):
                continue
            finding_id = _text(finding.get("finding_id"))
            finding_refs = set(_normalize_texts(finding.get("evidence_refs")))
            action = _text(finding.get("recommended_action")).upper()
            observed = _text(finding.get("wsp97_label")).upper() == "OBSERVED"
            if action == "FIX" and observed and finding_refs and finding_refs.issubset(report_refs):
                support.append(finding_id)
                direct_read_paths.extend(
                    path
                    for path in (
                        _repo_path_from_file_evidence(ref)
                        for ref in finding_refs
                    )
                    if path.startswith("holo_index/")
                )
            elif action in {"REVISE", "RESEARCH_MORE", "STOP"} and finding_id:
                conflicts.append(finding_id)
    paths = _dedupe(direct_read_paths)
    return _Support(_dedupe(support), _dedupe(conflicts), bool(paths), paths)


def _findings(report: Mapping[str, Any]) -> tuple[Mapping[str, Any], ...]:
    values = report.get("findings")
    if isinstance(values, (str, bytes)) or not isinstance(values, Sequence):
        return ()
    return tuple(value for value in values if isinstance(value, Mapping))


def _is_holo_maintenance_proposal(
    proposal: _Proposal,
    support: _Support | None = None,
) -> bool:
    evidence_paths = set(support.direct_read_paths) if support else set()
    return (
        "HOLOINDEX" in _text(proposal.slice_id).upper()
        and proposal.requested_operation
        in {"holoindex_maintenance", "index_maintenance"}
        and bool(proposal.allowed_paths)
        and all(path.startswith("holo_index/") for path in proposal.allowed_paths)
        and all(
            not any(token in path for token in ("*", "?", "["))
            for path in proposal.allowed_paths
        )
        and (support is None or set(proposal.allowed_paths) == evidence_paths)
    )


def _repo_path_from_file_evidence(value: str) -> str:
    text = _text(value)
    if not text.startswith("file:"):
        return ""
    body = text.removeprefix("file:")
    for marker in (":sha256:", ":lines:", "#L"):
        if marker in body:
            body = body.split(marker, 1)[0]
    return body.replace("\\", "/")


def _normalize_paths(value: Any) -> tuple[str, ...]:
    return _dedupe(
        item.replace("\\", "/")
        for item in _normalize_texts(value)
        if _valid_repo_path(item.replace("\\", "/"))
    )


def _has_invalid_paths(value: Any) -> bool:
    paths = _normalize_texts(value)
    return any(
        not _valid_repo_path(path.replace("\\", "/")) for path in paths
    )


def _valid_repo_path(path: str) -> bool:
    parts = path.split("/")
    return (
        bool(path)
        and not path.startswith(("/", "../"))
        and "\x00" not in path
        and ":" not in parts[0]
        and all(part not in {"", ".", ".."} for part in parts)
    )


def _normalize_texts(value: Any) -> tuple[str, ...]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        return ()
    return _dedupe(_text(item) for item in value if _text(item))


def _dedupe(values: Sequence[str] | Any) -> tuple[str, ...]:
    return tuple(dict.fromkeys(_text(item) for item in values if _text(item)))


def _valid_slice_name(value: str) -> bool:
    text = _text(value)
    return (
        text.endswith("_PHASE1")
        and text.replace("_", "").isalnum()
        and text.upper() == text
    )


def _text(value: Any) -> str:
    return str(value or "").strip()


def _digest(value: Any) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


__all__ = [
    "ArchitectProposalAdmissionPolicy",
    "ArchitectProposalExecutabilityReceipt",
    "CREATE_NEW",
    "EFFECT_CONFIGURATION_ONLY",
    "EFFECT_DRAFT_PR_PUBLISH",
    "EFFECT_EXTERNAL",
    "EFFECT_LIVE_WORKTREE_CANARY",
    "EFFECT_MERGE",
    "EFFECT_NONE",
    "EFFECT_READ_ONLY_AUDIT",
    "EFFECT_REPOSITORY_CODE_CHANGE",
    "EXECUTION_READINESS_STATES",
    "EXTEND_EXISTING",
    "LIVE_EXECUTION_CAPABILITIES",
    "PROPOSAL_ADMISSION_SCHEMA_VERSION",
    "PROPOSAL_VALIDITIES",
    "READINESS_EVIDENCE_BLOCKED",
    "READINESS_IMPLEMENTATION_BLOCKED",
    "READINESS_PLATFORM_BLOCKED",
    "READINESS_READY",
    "REUSE_DECISIONS",
    "REUSE_EXISTING",
    "TARGET_EFFECT_PLANES",
    "VALIDITY_NEEDS_RESEARCH",
    "VALIDITY_VALID",
    "current_architect_proposal_admission_policy",
    "evaluate_architect_proposal_executability",
    "proposal_admission_prompt_policy",
    "reevaluate_architect_proposal_execution_readiness",
    "reevaluate_architect_proposal_promotion_preconditions",
    "validate_architect_proposal_executability_receipt",
]
