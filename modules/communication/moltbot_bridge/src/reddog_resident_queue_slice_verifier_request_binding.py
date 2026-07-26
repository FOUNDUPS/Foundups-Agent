"""Resident queue slice-verifier request binding.

Slice: REDDOG_RESIDENT_QUEUE_SLICE_VERIFIER_REQUEST_BINDING_PHASE1

This module derives the independent evidence-producer request for the resident
queue slice-verifier stage from an explicit `slice_verifier_plan` on the bound
work order plus already-recorded authority, verification, worktree, and bounded
pilot chain results. It emits request data only; it does not run commands,
create or update PRs, merge, write PatternMemory, settle rewards, enqueue
OpenClaw, dispatch Hermes, or re-index HoloIndex.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Mapping


SLICE_VERIFIER_REQUEST_BINDING_ACCEPT = "SLICE_VERIFIER_REQUEST_BINDING_ACCEPT"
SLICE_VERIFIER_REQUEST_BINDING_REJECT = "SLICE_VERIFIER_REQUEST_BINDING_REJECT"

FAIL_SLICE_VERIFIER_PLAN_MISSING = "FAIL_SLICE_VERIFIER_PLAN_MISSING"
FAIL_SLICE_VERIFIER_PLAN_INVALID = "FAIL_SLICE_VERIFIER_PLAN_INVALID"
FAIL_AUTHORITY_RUNTIME_MISSING = "FAIL_AUTHORITY_RUNTIME_MISSING"
FAIL_AUTHORITY_VERIFICATION_MISSING = "FAIL_AUTHORITY_VERIFICATION_MISSING"
FAIL_SIGNED_AUTHORITY_MISSING = "FAIL_SIGNED_AUTHORITY_MISSING"
FAIL_WORKTREE_CREATE_MISSING = "FAIL_WORKTREE_CREATE_MISSING"
FAIL_BOUNDED_WORKER_PILOT_MISSING = "FAIL_BOUNDED_WORKER_PILOT_MISSING"
FAIL_BOUNDED_WORKER_PILOT_REJECTED = "FAIL_BOUNDED_WORKER_PILOT_REJECTED"
FAIL_SIGNED_RECEIPT_CHAIN_MISSING = "FAIL_SIGNED_RECEIPT_CHAIN_MISSING"
FAIL_ASSURANCE_RESERVATION_MISSING = "FAIL_ASSURANCE_RESERVATION_MISSING"
FAIL_ASSURANCE_RESERVATION_MISMATCH = "FAIL_ASSURANCE_RESERVATION_MISMATCH"


@dataclass(frozen=True)
class ResidentQueueSliceVerifierRequestBindingResult:
    decision: str
    accepted: bool
    evidence_producer_request: Dict[str, Any] = field(default_factory=dict)
    rejection_reasons: list[str] = field(default_factory=list)
    no_command_execution_performed: bool = True
    no_github_call_performed: bool = True
    no_pr_publish_performed: bool = True
    no_merge_performed: bool = True
    no_pattern_memory_write_performed: bool = True
    no_reward_settlement_performed: bool = True
    no_openclaw_enqueue_performed: bool = True
    no_hermes_dispatch_performed: bool = True
    no_holoindex_reindex_performed: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def build_resident_queue_slice_verifier_request(
    *,
    work_order: Mapping[str, Any],
    stage_results: Mapping[str, Mapping[str, Any]],
    repo_root: Path,
    holoindex_evidence: Mapping[str, Any] | None = None,
    assurance_reservation_store: Any = None,
) -> ResidentQueueSliceVerifierRequestBindingResult:
    """Build an evidence-producer request from resident queue chain state."""

    plan = _mapping(work_order.get("slice_verifier_plan"))
    reasons: list[str] = []
    if not plan:
        reasons.append(FAIL_SLICE_VERIFIER_PLAN_MISSING)

    authority_runtime = _mapping(stage_results.get("authority_runtime"))
    authority_result = _mapping(authority_runtime.get("authority_result"))
    work_authority = _mapping(authority_result.get("work_authority"))
    authority_receipt = _mapping(authority_result.get("receipt"))
    if not authority_runtime or authority_result.get("accepted") is not True:
        reasons.append(FAIL_AUTHORITY_RUNTIME_MISSING)
    if not work_authority:
        reasons.append(FAIL_SIGNED_AUTHORITY_MISSING)

    authority_verification = _mapping(stage_results.get("authority_verification"))
    verification = _mapping(authority_verification.get("verification_result"))
    if not authority_verification or verification.get("accepted") is not True:
        reasons.append(FAIL_AUTHORITY_VERIFICATION_MISSING)

    worktree_create_stage = _mapping(stage_results.get("worktree_create"))
    worktree_create = _mapping(worktree_create_stage.get("worktree_create_result"))
    worktree_path = str(worktree_create.get("worktree_path") or "")
    if not worktree_create_stage or not worktree_create or not worktree_path:
        reasons.append(FAIL_WORKTREE_CREATE_MISSING)

    bounded_stage = _mapping(stage_results.get("bounded_worker_pilot"))
    pilot_result = _mapping(bounded_stage.get("pilot_result"))
    pilot_receipt = _mapping(pilot_result.get("receipt"))
    if not bounded_stage or not pilot_result or not pilot_receipt:
        reasons.append(FAIL_BOUNDED_WORKER_PILOT_MISSING)
    elif bounded_stage.get("decision") != "QUEUE_AUTHORIZED_BOUNDED_WORKER_PILOT_INVOKE_ACCEPT":
        reasons.append(FAIL_BOUNDED_WORKER_PILOT_REJECTED)
    elif pilot_result.get("accepted") is not True:
        reasons.append(FAIL_BOUNDED_WORKER_PILOT_REJECTED)

    signed_receipt_chain = _mapping(plan.get("signed_receipt_chain")) or _mapping(
        _mapping(work_order.get("bounded_worker_plan")).get("signed_receipt_chain")
    )
    if not signed_receipt_chain:
        reasons.append(FAIL_SIGNED_RECEIPT_CHAIN_MISSING)

    admission = _mapping(stage_results.get("assurance_capacity_admission"))
    recorded_reservation = _mapping(admission.get("reservation"))
    reservation_id = str(recorded_reservation.get("reservation_id") or "")
    durable_reservation = {}
    if (
        admission.get("decision") != "ASSURANCE_CAPACITY_ADMISSION_ACCEPT"
        or not reservation_id
        or assurance_reservation_store is None
    ):
        reasons.append(FAIL_ASSURANCE_RESERVATION_MISSING)
    else:
        durable_reservation = _mapping(
            assurance_reservation_store.get_independent_assurance_reservation(
                reservation_id
            )
        )
        if _mapping(durable_reservation.get("reservation")):
            durable_reservation = _mapping(
                durable_reservation.get("reservation")
            )
        durable_admission_digest = str(
            durable_reservation.get("admission_reservation_digest")
            or durable_reservation.get("reservation_digest")
            or ""
        )
        if (
            not durable_reservation
            or str(durable_reservation.get("status") or "").upper()
            != "RESERVED"
            or durable_admission_digest
            != str(recorded_reservation.get("reservation_digest") or "")
            or str(durable_reservation.get("work_order_id") or "")
            != str(work_order.get("work_order_id") or "")
        ):
            reasons.append(FAIL_ASSURANCE_RESERVATION_MISMATCH)

    for field_name in (
        "slice_name",
        "base_sha",
        "head_sha",
        "required_checks",
    ):
        if field_name not in plan or plan.get(field_name) in (None, "", (), [], {}):
            reasons.append(f"{FAIL_SLICE_VERIFIER_PLAN_INVALID}:{field_name}")

    if reasons:
        return _reject(reasons)

    signed_authority = {
        **dict(work_authority),
        "accepted": True,
        "signature_gate_digest": str(
            authority_receipt.get("work_authority_digest")
            or authority_receipt.get("receipt_id")
            or ""
        ),
    }
    evidence = _mapping(holoindex_evidence) or _mapping(work_order.get("holoindex_evidence"))
    expected_paths = _string_list(plan.get("expected_changed_paths")) or _string_list(
        pilot_receipt.get("written_artifacts")
    )
    request = {
        "explicit_evidence_production_requested": True,
        "work_order_id": str(work_order.get("work_order_id") or ""),
        "slice_name": str(plan.get("slice_name") or ""),
        "worker_id": str(durable_reservation.get("author_principal_id") or ""),
        "verifier_id": str(
            durable_reservation.get("verifier_principal_id") or ""
        ),
        "assurance_reservation_id": str(
            durable_reservation.get("reservation_id") or ""
        ),
        "assurance_reservation_digest": str(
            durable_reservation.get("admission_reservation_digest")
            or durable_reservation.get("reservation_digest")
            or ""
        ),
        "verifier_task_id": str(
            durable_reservation.get("verifier_task_id") or ""
        ),
        "base_sha": str(plan.get("base_sha") or ""),
        "head_sha": str(plan.get("head_sha") or ""),
        "repo_root": str(repo_root),
        "worktree_path": worktree_path,
        "operation_cwd": str(plan.get("operation_cwd") or worktree_path),
        "allowed_path_patterns": _string_list(plan.get("allowed_path_patterns"))
        or _string_list(work_order.get("allowed_paths")),
        "expected_changed_paths": expected_paths,
        "forbidden_path_patterns": _string_list(plan.get("forbidden_path_patterns"))
        or _string_list(work_order.get("denied_paths")),
        "required_checks": _list(plan.get("required_checks")),
        "signed_authority": signed_authority,
        "signed_receipt_chain": dict(signed_receipt_chain),
        "worktree_receipt": dict(pilot_receipt),
        "bounded_worker_pilot_receipt": dict(pilot_receipt),
        "holoindex_evidence": dict(evidence),
        "pattern_memory_write_performed": False,
        "draft_pr_published": False,
        "merge_performed": False,
    }
    for optional in ("protected_surface_authorization_digest", "consensus_receipt_digest"):
        if plan.get(optional):
            request[optional] = plan[optional]

    return ResidentQueueSliceVerifierRequestBindingResult(
        decision=SLICE_VERIFIER_REQUEST_BINDING_ACCEPT,
        accepted=True,
        evidence_producer_request=request,
        rejection_reasons=[],
    )


def _reject(reasons: list[str]) -> ResidentQueueSliceVerifierRequestBindingResult:
    return ResidentQueueSliceVerifierRequestBindingResult(
        decision=SLICE_VERIFIER_REQUEST_BINDING_REJECT,
        accepted=False,
        rejection_reasons=_dedupe(reasons),
    )


def _mapping(value: Any) -> Mapping[str, Any]:
    if hasattr(value, "to_dict"):
        candidate = value.to_dict()
        return candidate if isinstance(candidate, Mapping) else {}
    return value if isinstance(value, Mapping) else {}


def _list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return []


def _string_list(value: Any) -> list[str]:
    return [str(item) for item in _list(value) if str(item)]


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if text and text not in seen:
            seen.add(text)
            ordered.append(text)
    return ordered


__all__ = [
    "FAIL_AUTHORITY_RUNTIME_MISSING",
    "FAIL_ASSURANCE_RESERVATION_MISMATCH",
    "FAIL_ASSURANCE_RESERVATION_MISSING",
    "FAIL_AUTHORITY_VERIFICATION_MISSING",
    "FAIL_BOUNDED_WORKER_PILOT_MISSING",
    "FAIL_BOUNDED_WORKER_PILOT_REJECTED",
    "FAIL_SIGNED_AUTHORITY_MISSING",
    "FAIL_SIGNED_RECEIPT_CHAIN_MISSING",
    "FAIL_SLICE_VERIFIER_PLAN_INVALID",
    "FAIL_SLICE_VERIFIER_PLAN_MISSING",
    "FAIL_WORKTREE_CREATE_MISSING",
    "ResidentQueueSliceVerifierRequestBindingResult",
    "SLICE_VERIFIER_REQUEST_BINDING_ACCEPT",
    "SLICE_VERIFIER_REQUEST_BINDING_REJECT",
    "build_resident_queue_slice_verifier_request",
]
