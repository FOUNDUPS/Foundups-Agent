"""Deterministic candidate and proposal checks before FIX promotion."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

from holo_index.freshness_receipt import (
    HoloIndexFreshnessReceipt,
    evaluate_freshness_for_paths,
)

from modules.communication.moltbot_bridge.src.reddog_architect_proposal_executability_admission import (
    ArchitectProposalExecutabilityReceipt,
    EFFECT_REPOSITORY_CODE_CHANGE,
    reevaluate_architect_proposal_execution_readiness,
    validate_architect_proposal_executability_receipt,
)


CANDIDATE_MALFORMED = "candidate_malformed"
PROPOSAL_ADMISSION_INVALID = "proposal_admission_invalid"
REPO_HEAD_MISMATCH = "repo_head_mismatch"
HOLOINDEX_BINDING_MISMATCH = "holoindex_binding_mismatch"


def validate_architect_fix_candidate(
    candidate: Mapping[str, Any],
    determination: Mapping[str, Any],
    *,
    schema_version: str,
) -> tuple[str, ...]:
    expected_id = _digest(
        {
            "source_determination_receipt_id": str(
                candidate.get("source_determination_receipt_id") or ""
            ),
            "slice_id": str(candidate.get("slice_id") or ""),
            "snapshot_receipt_id": str(
                determination.get("snapshot_receipt_id") or ""
            ),
            "report_bundle_id": str(determination.get("report_bundle_id") or ""),
            "wsp15_allocation_receipt_id": str(
                determination.get("wsp15_allocation_receipt_id") or ""
            ),
            "proposal_admission_receipt_id": str(
                candidate.get("proposal_admission_receipt_id") or ""
            ),
        }
    )
    expected = (
        candidate
        and candidate.get("schema_version") == schema_version
        and str(candidate.get("queue_candidate_id") or "") == expected_id
        and str(candidate.get("source_determination_receipt_id") or "")
        == str(determination.get("determination_receipt_id") or "")
        and str(candidate.get("slice_id") or "")
        == str(determination.get("next_slice_name") or "")
        and str(candidate.get("status") or "").upper()
        in {"CANDIDATE", "BLOCKED_CANDIDATE"}
        and candidate.get("no_execution_performed") is True
        and isinstance(candidate.get("wsp15_allocation_receipt"), Mapping)
        and bool(candidate.get("wsp15_allocation_receipt"))
    )
    return () if expected else (CANDIDATE_MALFORMED,)


def validate_architect_fix_proposal_admission(
    *,
    determination: Mapping[str, Any],
    candidate: Mapping[str, Any],
    current_work_state: Mapping[str, Any],
    current_repo_head_sha: str | None,
    current_holoindex_receipt: Any,
) -> tuple[ArchitectProposalExecutabilityReceipt | None, tuple[str, ...]]:
    raw = determination.get("proposal_admission")
    try:
        receipt = validate_architect_proposal_executability_receipt(
            raw if isinstance(raw, Mapping) else {}
        )
    except ValueError:
        return None, (PROPOSAL_ADMISSION_INVALID,)
    reasons = _lineage_reasons(
        receipt=receipt,
        determination=determination,
        candidate=candidate,
        current_work_state=current_work_state,
        current_repo_head_sha=current_repo_head_sha,
        current_holoindex_receipt=current_holoindex_receipt,
    )
    if reevaluate_architect_proposal_execution_readiness(receipt):
        reasons.append(PROPOSAL_ADMISSION_INVALID)
    return (
        receipt if not reasons else None,
        tuple(dict.fromkeys(reasons)),
    )


def _lineage_reasons(
    *,
    receipt: ArchitectProposalExecutabilityReceipt,
    determination: Mapping[str, Any],
    candidate: Mapping[str, Any],
    current_work_state: Mapping[str, Any],
    current_repo_head_sha: str | None,
    current_holoindex_receipt: Any,
) -> list[str]:
    expected = (
        receipt.accepted is True
        and receipt.admissible_to_authoritative_queue is True
        and receipt.action == "FIX"
        and receipt.target_effect_plane == EFFECT_REPOSITORY_CODE_CHANGE
        and receipt.slice_id == determination.get("next_slice_name")
        and _valid_determination_id(determination, receipt)
        and receipt.snapshot_receipt_id
        == str(determination.get("snapshot_receipt_id") or "")
        and receipt.snapshot_content_digest
        == str(determination.get("snapshot_content_digest") or "")
        and receipt.report_bundle_id
        == str(determination.get("report_bundle_id") or "")
        and receipt.wsp15_allocation_receipt_id
        == str(determination.get("wsp15_allocation_receipt_id") or "")
        and receipt.wsp15_allocation_digest
        == str(determination.get("wsp15_allocation_digest") or "")
        and receipt.work_state_revision
        == str(current_work_state.get("revision") or "")
        and str(candidate.get("status") or "").upper() == "CANDIDATE"
        and receipt.receipt_id
        == str(candidate.get("proposal_admission_receipt_id") or "")
        and _digest(receipt.to_dict())
        == str(candidate.get("proposal_admission_digest") or "")
    )
    reasons = [] if expected else [PROPOSAL_ADMISSION_INVALID]
    if not current_repo_head_sha or receipt.repo_head_sha != current_repo_head_sha:
        reasons.append(REPO_HEAD_MISMATCH)
    if not _current_holoindex_binding_matches(
        receipt,
        current_holoindex_receipt=current_holoindex_receipt,
        current_repo_head_sha=current_repo_head_sha,
    ):
        reasons.append(HOLOINDEX_BINDING_MISMATCH)
    return reasons


def _valid_determination_id(
    determination: Mapping[str, Any],
    receipt: ArchitectProposalExecutabilityReceipt,
) -> bool:
    seed = {
        "cycle_id": determination.get("cycle_id"),
        "action": determination.get("action"),
        "next_slice_name": determination.get("next_slice_name"),
        "model_result_digest": determination.get("model_result_digest"),
        "model_selection_digest": determination.get("model_selection_digest"),
        "provider_call_id": determination.get("provider_call_id"),
        "provider_call_receipt_id": determination.get("provider_call_receipt_id"),
        "provider_call_evidence_digest": determination.get(
            "provider_call_evidence_digest"
        ),
        "proposal_admission_receipt_id": receipt.receipt_id,
    }
    return str(determination.get("determination_receipt_id") or "") == _digest(seed)


def _current_holoindex_binding_matches(
    receipt: ArchitectProposalExecutabilityReceipt,
    *,
    current_holoindex_receipt: Any,
    current_repo_head_sha: str | None,
) -> bool:
    if not isinstance(current_holoindex_receipt, HoloIndexFreshnessReceipt):
        return False
    payload = (
        current_holoindex_receipt.to_dict()
        if hasattr(current_holoindex_receipt, "to_dict")
        else current_holoindex_receipt
    )
    if not isinstance(payload, Mapping):
        return False
    generation_id = str(payload.get("generation_id") or "")
    if (
        generation_id != receipt.holoindex_generation_id
        or _digest(payload) != receipt.holoindex_freshness_receipt_digest
    ):
        return False
    check = evaluate_freshness_for_paths(
        current_holoindex_receipt,
        receipt.allowed_paths,
        expected_repo_head_sha=current_repo_head_sha,
    )
    return check.ok or receipt.holoindex_maintenance_exception_applied


def _digest(payload: Any) -> str:
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


__all__ = [
    "CANDIDATE_MALFORMED",
    "HOLOINDEX_BINDING_MISMATCH",
    "PROPOSAL_ADMISSION_INVALID",
    "REPO_HEAD_MISMATCH",
    "validate_architect_fix_candidate",
    "validate_architect_fix_proposal_admission",
]
