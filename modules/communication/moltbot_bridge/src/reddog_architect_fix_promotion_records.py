"""Pure record construction for an admitted RedDog architect FIX promotion."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any, Mapping, Optional


class ArchitectFixPromotionReason:
    WORK_STATE_SCHEMA = "REJECT_ARCHITECT_FIX_PROMOTION_WORK_STATE_SCHEMA"
    WORK_STATE_FRESHNESS = "REJECT_ARCHITECT_FIX_PROMOTION_WORK_STATE_FRESHNESS"
    DETERMINATION_MISSING = "REJECT_ARCHITECT_FIX_PROMOTION_DETERMINATION_MISSING"
    DETERMINATION_NOT_ACCEPTED = "REJECT_ARCHITECT_FIX_PROMOTION_DETERMINATION_NOT_ACCEPTED"
    DETERMINATION_NOT_FIX = "REJECT_ARCHITECT_FIX_PROMOTION_DETERMINATION_NOT_FIX"
    QUEUE_CANDIDATE_MISSING = "REJECT_ARCHITECT_FIX_PROMOTION_QUEUE_CANDIDATE_MISSING"
    QUEUE_CANDIDATE_MALFORMED = "REJECT_ARCHITECT_FIX_PROMOTION_QUEUE_CANDIDATE_MALFORMED"
    WSP15_ALLOCATION_INVALID = "REJECT_ARCHITECT_FIX_PROMOTION_WSP15_ALLOCATION_INVALID"
    WSP15_ALLOCATION_MISMATCH = "REJECT_ARCHITECT_FIX_PROMOTION_WSP15_ALLOCATION_MISMATCH"
    MODEL_SELECTION_MISSING = "REJECT_ARCHITECT_FIX_PROMOTION_MODEL_SELECTION_MISSING"
    MODEL_SELECTION_INVALID = "REJECT_ARCHITECT_FIX_PROMOTION_MODEL_SELECTION_INVALID"
    MODEL_SELECTION_NOT_PRODUCTION = "REJECT_ARCHITECT_FIX_PROMOTION_MODEL_SELECTION_NOT_PRODUCTION"
    MODEL_RUNTIME_BINDING_INVALID = "REJECT_ARCHITECT_FIX_PROMOTION_MODEL_RUNTIME_BINDING_INVALID"
    MODEL_RUNTIME_BINDING_NOT_BOUND = "REJECT_ARCHITECT_FIX_PROMOTION_MODEL_RUNTIME_BINDING_NOT_BOUND"
    MODEL_RUNTIME_BINDING_MISMATCH = "REJECT_ARCHITECT_FIX_PROMOTION_MODEL_RUNTIME_BINDING_MISMATCH"
    MEMEX_SUPPLY_MISSING = "REJECT_ARCHITECT_FIX_PROMOTION_MEMEX_SUPPLY_MISSING"
    MEMEX_SUPPLY_INVALID = "REJECT_ARCHITECT_FIX_PROMOTION_MEMEX_SUPPLY_INVALID"
    AUTHORITY_PROFILE_MISSING = "REJECT_ARCHITECT_FIX_PROMOTION_AUTHORITY_PROFILE_MISSING"
    AUTHORITY_PROFILE_INCOMPLETE = "REJECT_ARCHITECT_FIX_PROMOTION_AUTHORITY_PROFILE_INCOMPLETE"
    AUTHORITY_PROFILE_SECRET_FIELD = (
        "REJECT_ARCHITECT_FIX_PROMOTION_AUTHORITY_PROFILE_SECRET_FIELD"
    )
    HOLOINDEX_EVIDENCE_MISSING = "REJECT_ARCHITECT_FIX_PROMOTION_HOLOINDEX_EVIDENCE_MISSING"
    PROPOSAL_ADMISSION_INVALID = (
        "REJECT_ARCHITECT_FIX_PROMOTION_PROPOSAL_ADMISSION_INVALID"
    )
    PROPOSAL_AUTHENTICITY_INVALID = (
        "REJECT_ARCHITECT_FIX_PROMOTION_PROPOSAL_AUTHENTICITY_INVALID"
    )
    HOLOINDEX_BINDING_MISMATCH = (
        "REJECT_ARCHITECT_FIX_PROMOTION_HOLOINDEX_BINDING_MISMATCH"
    )
    REPO_HEAD_MISMATCH = "REJECT_ARCHITECT_FIX_PROMOTION_REPO_HEAD_MISMATCH"
    AUTHORITY_PROFILE_PRECOMMIT_WRITE_FAILED = (
        "REJECT_ARCHITECT_FIX_PROMOTION_AUTHORITY_PROFILE_PRECOMMIT_WRITE_FAILED"
    )
    PUBLICATION_COORDINATOR_MISSING = (
        "REJECT_ARCHITECT_FIX_PROMOTION_PUBLICATION_COORDINATOR_MISSING"
    )
    DUPLICATE_QUEUE_ITEM = "REJECT_ARCHITECT_FIX_PROMOTION_DUPLICATE_QUEUE_ITEM"
    STORE_REJECTED = "REJECT_ARCHITECT_FIX_PROMOTION_STORE_REJECTED"
    FIX_PROMOTION_CLAIM_FENCE_INVALID = (
        "REJECT_ARCHITECT_FIX_PROMOTION_CLAIM_FENCE_INVALID"
    )


@dataclass(frozen=True)
class ArchitectFixPromotionReceipt:
    schema_version: str
    promotion_receipt_id: str
    status: str
    architect_determination_receipt_id: str
    source_queue_candidate_id: str
    queue_item_id: str
    claim_id: str
    selected_slice: str
    worker_id: str
    freshness_receipt_id: str
    wsp15_allocation_receipt_id: str
    wsp15_allocation_digest: str
    proposal_admission_receipt_id: str
    proposal_admission_digest: str
    proposal_authenticity_attestation_id: str
    proposal_authenticity_attestation_digest: str
    proposal_policy_authorization_id: str
    proposal_policy_authorization_digest: str
    proposal_signer_runtime_context_digest: str
    model_catalog_snapshot_id: str
    model_selection_receipt_id: str
    model_selection_digest: str
    memex_supply_receipt_id: str
    memex_supply_digest: str
    publication_id: str
    authority_profile_digest: str
    committed_revision: Optional[str]
    model_runtime_binding_receipt_id: Optional[str] = None
    model_runtime_binding_digest: Optional[str] = None
    model_runtime_binding_verification_receipt_id: Optional[str] = None
    model_runtime_binding_verification_digest: Optional[str] = None
    agentdb_fix_promotion_claim_id: Optional[str] = None
    agentdb_fix_promotion_claim_revision: Optional[int] = None
    agentdb_fix_promotion_claim_fence_digest: Optional[str] = None
    no_signing_performed: bool = True
    no_worker_spawn_performed: bool = True
    no_worktree_created: bool = True
    no_shell_command_executed: bool = True
    no_openclaw_enqueue_performed: bool = True
    no_hermes_dispatch_performed: bool = True
    no_repo_mutation_performed: bool = True
    authoritative_work_state_mutation_performed: bool = True
    no_holoindex_reindex_performed: bool = True
    no_pr_created: bool = True
    no_pattern_memory_write_performed: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ArchitectFixPromotionResult:
    accepted: bool
    status: str
    receipt: Optional[ArchitectFixPromotionReceipt]
    rejection_reasons: tuple[str, ...]
    authority_profile: Optional[Mapping[str, Any]] = None
    work_state_snapshot: Optional[Mapping[str, Any]] = None
    no_signing_performed: bool = True
    no_worker_spawn_performed: bool = True
    no_worktree_created: bool = True
    no_shell_command_executed: bool = True
    no_openclaw_enqueue_performed: bool = True
    no_hermes_dispatch_performed: bool = True
    no_holoindex_reindex_performed: bool = True
    no_pr_created: bool = True
    no_pattern_memory_write_performed: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "accepted": self.accepted,
            "status": self.status,
            "receipt": self.receipt.to_dict() if self.receipt else None,
            "rejection_reasons": list(self.rejection_reasons),
            "authority_profile": dict(self.authority_profile or {}),
            "work_state_snapshot": dict(self.work_state_snapshot or {}),
            "no_signing_performed": self.no_signing_performed,
            "no_worker_spawn_performed": self.no_worker_spawn_performed,
            "no_worktree_created": self.no_worktree_created,
            "no_shell_command_executed": self.no_shell_command_executed,
            "no_openclaw_enqueue_performed": self.no_openclaw_enqueue_performed,
            "no_hermes_dispatch_performed": self.no_hermes_dispatch_performed,
            "no_holoindex_reindex_performed": self.no_holoindex_reindex_performed,
            "no_pr_created": self.no_pr_created,
            "no_pattern_memory_write_performed": self.no_pattern_memory_write_performed,
        }


@dataclass(frozen=True)
class ArchitectFixPromotionRecordInputs:
    selected_slice: str
    determination_id: str
    worker_id: str
    now_iso: str
    expires_at: str
    freshness_receipt_id: str
    reconciliation_report_id: str
    proposal_admission_receipt_id: str
    proposal_admission_digest: str
    proposal_authenticity_attestation_id: str
    proposal_authenticity_attestation_digest: str
    proposal_policy_authorization_id: str
    proposal_policy_authorization_digest: str
    proposal_signer_runtime_context_digest: str
    authorized_base_sha: str
    model_selection_digest: str
    model_runtime_binding_digest: str
    memex_supply_digest: str
    candidate: Mapping[str, Any]
    allocation: Mapping[str, Any]
    model_selection: Mapping[str, Any]
    model_runtime_binding: Mapping[str, Any]
    memex_supply: Mapping[str, Any]


@dataclass(frozen=True)
class ArchitectFixPromotionRecords:
    claim_id: str
    queue_item_id: str
    claim: Mapping[str, Any]
    queue_item: Mapping[str, Any]
    sync_receipt: Mapping[str, Any]
    evidence_refs: tuple[str, ...]


def canonical_digest(payload: Any) -> str:
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


def build_architect_fix_promotion_records(
    inputs: ArchitectFixPromotionRecordInputs,
) -> ArchitectFixPromotionRecords:
    claim_id = canonical_digest(_claim_seed(inputs))
    queue_item_id = canonical_digest(_queue_seed(inputs, claim_id))
    evidence_refs = _evidence_refs(inputs, claim_id)
    return ArchitectFixPromotionRecords(
        claim_id=claim_id,
        queue_item_id=queue_item_id,
        claim=_claim(inputs, claim_id),
        queue_item=_queue_item(inputs, claim_id, queue_item_id, evidence_refs),
        sync_receipt=_sync_receipt(inputs, claim_id, queue_item_id),
        evidence_refs=evidence_refs,
    )


def _claim_seed(inputs: ArchitectFixPromotionRecordInputs) -> dict[str, Any]:
    return {
        "selected_slice": inputs.selected_slice,
        "determination_receipt_id": inputs.determination_id,
        **_evidence_receipt_ids(inputs),
        "worker_id": inputs.worker_id,
        "claimed_at": inputs.now_iso,
        "freshness_receipt_id": inputs.freshness_receipt_id,
        "authorized_base_sha": inputs.authorized_base_sha,
        **_proposal_authority_binding(inputs),
    }


def _queue_seed(
    inputs: ArchitectFixPromotionRecordInputs,
    claim_id: str,
) -> dict[str, Any]:
    return {
        "slice_id": inputs.selected_slice,
        "claim_id": claim_id,
        "worker_id": inputs.worker_id,
        "enqueued_at": inputs.now_iso,
        "determination_receipt_id": inputs.determination_id,
        "authorized_base_sha": inputs.authorized_base_sha,
        "wsp15_allocation_receipt_id": inputs.allocation["receipt_id"],
        **_evidence_receipt_ids(inputs),
        **_proposal_authority_binding(inputs),
    }


def _evidence_receipt_ids(
    inputs: ArchitectFixPromotionRecordInputs,
) -> dict[str, str]:
    return {
        "model_selection_receipt_id": str(inputs.model_selection["receipt_id"]),
        "model_runtime_binding_receipt_id": str(
            inputs.model_runtime_binding.get("receipt_id", "")
        ),
        "model_runtime_binding_verification_receipt_id": str(
            inputs.model_runtime_binding.get("verification_receipt_id", "")
        ),
        "memex_supply_receipt_id": str(inputs.memex_supply["receipt_id"]),
        "proposal_admission_receipt_id": inputs.proposal_admission_receipt_id,
    }


def _proposal_authority_binding(
    inputs: ArchitectFixPromotionRecordInputs,
) -> dict[str, str]:
    return {
        "proposal_authenticity_attestation_id": (
            inputs.proposal_authenticity_attestation_id
        ),
        "proposal_authenticity_attestation_digest": (
            inputs.proposal_authenticity_attestation_digest
        ),
        "proposal_policy_authorization_id": (
            inputs.proposal_policy_authorization_id
        ),
        "proposal_policy_authorization_digest": (
            inputs.proposal_policy_authorization_digest
        ),
        "proposal_signer_runtime_context_digest": (
            inputs.proposal_signer_runtime_context_digest
        ),
    }


def _claim(
    inputs: ArchitectFixPromotionRecordInputs,
    claim_id: str,
) -> dict[str, Any]:
    return {
        "claim_id": claim_id,
        "slice_id": inputs.selected_slice,
        "worker_id": inputs.worker_id,
        "lane_id": "reddog_operational",
        "claimed_at": inputs.now_iso,
        "expires_at": inputs.expires_at,
        "reconciliation_report_id": inputs.reconciliation_report_id,
        "freshness_receipt_id": inputs.freshness_receipt_id,
        "status": "ACTIVE",
        "source_determination_receipt_id": inputs.determination_id,
        "authorized_base_sha": inputs.authorized_base_sha,
        **_evidence_receipt_ids(inputs),
        **_proposal_authority_binding(inputs),
    }


def _evidence_refs(
    inputs: ArchitectFixPromotionRecordInputs,
    claim_id: str,
) -> tuple[str, ...]:
    runtime_refs = (
        [
            f"model_runtime_binding:{inputs.model_runtime_binding['receipt_id']}",
            (
                "model_runtime_binding_verification:"
                f"{inputs.model_runtime_binding['verification_receipt_id']}"
            ),
        ]
        if inputs.model_runtime_binding
        else []
    )
    refs = [
        f"claim:{claim_id}",
        f"freshness:{inputs.freshness_receipt_id}",
        f"wsp15_allocation:{inputs.allocation['receipt_id']}",
        f"architect_determination:{inputs.determination_id}",
        f"proposal_admission:{inputs.proposal_admission_receipt_id}",
        (
            "proposal_authenticity_attestation:"
            f"{inputs.proposal_authenticity_attestation_id}"
        ),
        (
            "proposal_policy_authorization:"
            f"{inputs.proposal_policy_authorization_id}"
        ),
        f"model_selection:{inputs.model_selection['receipt_id']}",
        *runtime_refs,
        f"memex_supply:{inputs.memex_supply['receipt_id']}",
        *[str(ref) for ref in inputs.candidate.get("evidence_refs") or ()],
    ]
    return tuple(dict.fromkeys(refs))


def _queue_item(
    inputs: ArchitectFixPromotionRecordInputs,
    claim_id: str,
    queue_item_id: str,
    evidence_refs: tuple[str, ...],
) -> dict[str, Any]:
    return {
        "queue_item_id": queue_item_id,
        "slice_id": inputs.selected_slice,
        "claim_id": claim_id,
        "worker_id": inputs.worker_id,
        "status": "QUEUED",
        "enqueued_at": inputs.now_iso,
        "evidence_refs": list(evidence_refs),
        "wsp15_allocation_receipt": dict(inputs.allocation),
        "source_determination_receipt_id": inputs.determination_id,
        "source_queue_candidate_id": str(
            inputs.candidate.get("queue_candidate_id") or ""
        ),
        "authorized_base_sha": inputs.authorized_base_sha,
        "proposal_admission_receipt_id": inputs.proposal_admission_receipt_id,
        "proposal_admission_digest": inputs.proposal_admission_digest,
        **_proposal_authority_binding(inputs),
        "model_catalog_snapshot_id": inputs.model_selection["catalog_snapshot_id"],
        "model_selection_receipt_id": inputs.model_selection["receipt_id"],
        "model_selection_digest": inputs.model_selection_digest,
        "model_runtime_binding_receipt_id": inputs.model_runtime_binding.get(
            "receipt_id", ""
        ),
        "model_runtime_binding_digest": inputs.model_runtime_binding_digest,
        "model_runtime_binding_verification_receipt_id": (
            inputs.model_runtime_binding.get("verification_receipt_id", "")
        ),
        "model_runtime_binding_verification_digest": (
            inputs.model_runtime_binding.get("verification_receipt_digest", "")
        ),
        "memex_supply_receipt_id": inputs.memex_supply["receipt_id"],
        "memex_supply_digest": inputs.memex_supply_digest,
        "no_execution_performed": True,
    }


def _sync_receipt(
    inputs: ArchitectFixPromotionRecordInputs,
    claim_id: str,
    queue_item_id: str,
) -> dict[str, Any]:
    return {
        "sync_id": canonical_digest(
            {"queue_item_id": queue_item_id, "claim_id": claim_id}
        ),
        "status": "WRE_QUEUE_SYNCED",
        "queue_item_ids": [queue_item_id],
        "selected_slice": inputs.selected_slice,
        "rejection_reasons": [],
        "source": "reddog_architect_fix_wsp15_work_order_promotion.v1",
        "no_execution_performed": True,
    }


__all__ = [
    "ArchitectFixPromotionReason",
    "ArchitectFixPromotionReceipt",
    "ArchitectFixPromotionResult",
    "ArchitectFixPromotionRecordInputs",
    "ArchitectFixPromotionRecords",
    "build_architect_fix_promotion_records",
    "canonical_digest",
]
