"""Pure record construction for an admitted RedDog architect FIX promotion."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Mapping


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
    }


def _evidence_receipt_ids(
    inputs: ArchitectFixPromotionRecordInputs,
) -> dict[str, str]:
    return {
        "model_selection_receipt_id": str(inputs.model_selection["receipt_id"]),
        "model_runtime_binding_receipt_id": str(
            inputs.model_runtime_binding.get("receipt_id", "")
        ),
        "memex_supply_receipt_id": str(inputs.memex_supply["receipt_id"]),
        "proposal_admission_receipt_id": inputs.proposal_admission_receipt_id,
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
    }


def _evidence_refs(
    inputs: ArchitectFixPromotionRecordInputs,
    claim_id: str,
) -> tuple[str, ...]:
    runtime_refs = (
        [f"model_runtime_binding:{inputs.model_runtime_binding['receipt_id']}"]
        if inputs.model_runtime_binding
        else []
    )
    refs = [
        f"claim:{claim_id}",
        f"freshness:{inputs.freshness_receipt_id}",
        f"wsp15_allocation:{inputs.allocation['receipt_id']}",
        f"architect_determination:{inputs.determination_id}",
        f"proposal_admission:{inputs.proposal_admission_receipt_id}",
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
        "model_catalog_snapshot_id": inputs.model_selection["catalog_snapshot_id"],
        "model_selection_receipt_id": inputs.model_selection["receipt_id"],
        "model_selection_digest": inputs.model_selection_digest,
        "model_runtime_binding_receipt_id": inputs.model_runtime_binding.get(
            "receipt_id", ""
        ),
        "model_runtime_binding_digest": inputs.model_runtime_binding_digest,
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
    "ArchitectFixPromotionRecordInputs",
    "ArchitectFixPromotionRecords",
    "build_architect_fix_promotion_records",
    "canonical_digest",
]
