"""Queue-candidate projection for an admitted RedDog architect determination."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any, Mapping

from modules.communication.moltbot_bridge.src.reddog_architect_proposal_executability_admission import (
    ArchitectProposalExecutabilityReceipt,
)


ARCHITECT_QUEUE_CANDIDATE_SCHEMA_VERSION = "reddog_architect_queue_candidate.v2"


def _digest(value: object) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        default=str,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True)
class ArchitectQueueCandidate:
    """Queue candidate emitted by an admitted FIX determination."""

    schema_version: str
    queue_candidate_id: str
    source_determination_receipt_id: str
    slice_id: str
    status: str
    evidence_refs: tuple[str, ...]
    wsp15_allocation_receipt: Mapping[str, Any]
    proposal_admission_receipt_id: str
    proposal_admission_digest: str
    progressive_policy_stage_receipt_id: str
    progressive_policy_stage_digest: str
    progressive_policy_stage_receipt: Mapping[str, Any]
    independent_verifier_required: bool
    no_queue_mutation_performed: bool = True
    no_execution_performed: bool = True
    no_worker_spawn_performed: bool = True
    no_openclaw_enqueue_performed: bool = True
    no_hermes_dispatch_performed: bool = True
    no_repo_mutation_performed: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_architect_queue_candidate(
    *,
    source_determination_receipt_id: str,
    next_slice_name: str,
    snapshot_receipt_id: str,
    report_bundle_id: str | None,
    wsp15_allocation_receipt: Mapping[str, Any],
    proposal_admission: ArchitectProposalExecutabilityReceipt,
) -> ArchitectQueueCandidate:
    """Project one digest-bound candidate without mutating the queue."""
    payload = {
        "source_determination_receipt_id": source_determination_receipt_id,
        "slice_id": next_slice_name,
        "snapshot_receipt_id": snapshot_receipt_id,
        "report_bundle_id": report_bundle_id,
        "wsp15_allocation_receipt_id": wsp15_allocation_receipt.get("receipt_id"),
        "proposal_admission_receipt_id": proposal_admission.receipt_id,
    }
    return ArchitectQueueCandidate(
        schema_version=ARCHITECT_QUEUE_CANDIDATE_SCHEMA_VERSION,
        queue_candidate_id=_digest(payload),
        source_determination_receipt_id=source_determination_receipt_id,
        slice_id=next_slice_name,
        status=(
            "CANDIDATE"
            if proposal_admission.admissible_to_authoritative_queue
            else "BLOCKED_CANDIDATE"
        ),
        evidence_refs=(
            f"architect_determination:{source_determination_receipt_id}",
            f"snapshot:{snapshot_receipt_id}",
            f"report_bundle:{report_bundle_id}",
            f"wsp15_allocation:{wsp15_allocation_receipt.get('receipt_id')}",
            f"proposal_admission:{proposal_admission.receipt_id}",
        ),
        wsp15_allocation_receipt=dict(wsp15_allocation_receipt),
        proposal_admission_receipt_id=proposal_admission.receipt_id,
        proposal_admission_digest=_digest(proposal_admission.to_dict()),
        progressive_policy_stage_receipt_id=(
            proposal_admission.progressive_policy_stage_receipt_id
        ),
        progressive_policy_stage_digest=_digest(
            proposal_admission.progressive_policy_stage_receipt
        ),
        progressive_policy_stage_receipt=dict(
            proposal_admission.progressive_policy_stage_receipt
        ),
        independent_verifier_required=proposal_admission.independent_verifier_required,
    )
