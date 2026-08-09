"""RedDog WRE queue consumer dry-run.

Slice: REDDOG_WRE_QUEUE_CONSUMER_DRYRUN_PHASE1

This module consumes the authoritative work-state WRE queue as evidence only.
It validates that one queued item is bound to a fresh durable worker claim and
emits the next required gate for runtime execution. It does not spawn workers,
create worktrees, execute shell commands, invoke OpenClaw or Hermes, mutate the
queue, edit repository files, publish PRs, settle rewards, or re-index HoloIndex.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Mapping, Optional

from modules.communication.moltbot_bridge.src.reddog_wre_queue_consumer_receipt import (
    WREQueueConsumerDryRunReceipt,
    build_queue_consumer_receipt,
)
from modules.communication.moltbot_bridge.src.reddog_queue_model_runtime_authority import (
    model_runtime_authority_fields,
)
from modules.communication.moltbot_bridge.src.reddog_progressive_execution_stage_policy import validate_queue_bounded_stage_binding
WRE_QUEUE_CONSUMER_DRYRUN_READY = "WRE_QUEUE_CONSUMER_DRYRUN_READY"
WRE_QUEUE_CONSUMER_DRYRUN_REJECT = "WRE_QUEUE_CONSUMER_DRYRUN_REJECT"

NEXT_GATE_SIGNED_AUTHORITY_REQUIRED = "SIGNED_AUTHORITY_REQUIRED"

FAIL_SCHEMA_VERSION = "FAIL_SCHEMA_VERSION"
FAIL_NO_QUEUE_ITEM = "FAIL_NO_QUEUE_ITEM"
FAIL_QUEUE_ITEM_STATUS = "FAIL_QUEUE_ITEM_STATUS"
FAIL_QUEUE_ALREADY_EXECUTED = "FAIL_QUEUE_ALREADY_EXECUTED"
FAIL_QUEUE_CLAIM_MISMATCH = "FAIL_QUEUE_CLAIM_MISMATCH"
FAIL_CLAIM_MISSING = "FAIL_CLAIM_MISSING"
FAIL_CLAIM_STATUS = "FAIL_CLAIM_STATUS"
FAIL_CLAIM_EXPIRED = "FAIL_CLAIM_EXPIRED"
FAIL_FRESHNESS_RECEIPT = "FAIL_FRESHNESS_RECEIPT"
FAIL_QUEUE_EVIDENCE_REFS = "FAIL_QUEUE_EVIDENCE_REFS"
FAIL_WSP15_ALLOCATION_RECEIPT = "FAIL_WSP15_ALLOCATION_RECEIPT"
FAIL_PROGRESSIVE_POLICY_STAGE = "FAIL_PROGRESSIVE_POLICY_STAGE"
FAIL_REQUESTED_QUEUE_NOT_FOUND = "FAIL_REQUESTED_QUEUE_NOT_FOUND"
FAIL_QUEUE_GOVERNED_LINEAGE = "FAIL_QUEUE_GOVERNED_LINEAGE"

WORK_STATE_SCHEMA_VERSION = "reddog_authoritative_work_state.v1"


@dataclass(frozen=True)
class WREQueueConsumerDryRunResult:
    """Result emitted by the WRE queue consumer dry-run."""

    accepted: bool
    status: str
    rejection_reasons: List[str]
    receipt: Optional[WREQueueConsumerDryRunReceipt]
    selected_queue_item_id: Optional[str]
    selected_slice: Optional[str]
    next_required_gate: Optional[str]
    execution_ready: bool = False
    no_queue_mutation_performed: bool = True
    no_worker_spawn_performed: bool = True
    no_worktree_created: bool = True
    no_shell_command_executed: bool = True
    no_openclaw_enqueue_performed: bool = True
    no_hermes_dispatch_performed: bool = True
    no_repo_mutation_performed: bool = True
    no_holoindex_reindex_performed: bool = True
    no_pr_created: bool = True
    no_reward_settlement_performed: bool = True

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["receipt"] = self.receipt.to_dict() if self.receipt else None
        return payload


def _digest(payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _dedupe(values: Iterable[str]) -> List[str]:
    seen: set[str] = set()
    ordered: List[str] = []
    for value in values:
        text = str(value or "").strip()
        if text and text not in seen:
            seen.add(text)
            ordered.append(text)
    return ordered


def _mapping(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    return {}


def _list_of_mappings(value: Any) -> List[Mapping[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, Mapping)]


def _parse_iso(value: Any) -> Optional[datetime]:
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _now(now_iso: Optional[str]) -> datetime:
    parsed = _parse_iso(now_iso)
    return parsed if parsed is not None else datetime.now(timezone.utc)


def _select_queue_item(
    queue_items: List[Mapping[str, Any]],
    requested_queue_item_id: Optional[str],
) -> tuple[Optional[Mapping[str, Any]], List[str]]:
    if requested_queue_item_id:
        for item in queue_items:
            if str(item.get("queue_item_id") or "") == requested_queue_item_id:
                return item, []
        return None, [FAIL_REQUESTED_QUEUE_NOT_FOUND]
    for item in queue_items:
        if str(item.get("status") or "").upper() == "QUEUED":
            return item, []
    return None, [FAIL_NO_QUEUE_ITEM]


def _find_by_id(items: List[Mapping[str, Any]], key: str, expected: str) -> Optional[Mapping[str, Any]]:
    for item in items:
        if str(item.get(key) or "") == expected:
            return item
    return None


def _reject(reasons: Iterable[str]) -> WREQueueConsumerDryRunResult:
    return WREQueueConsumerDryRunResult(
        accepted=False,
        status=WRE_QUEUE_CONSUMER_DRYRUN_REJECT,
        rejection_reasons=_dedupe(reasons),
        receipt=None,
        selected_queue_item_id=None,
        selected_slice=None,
        next_required_gate=None,
    )


def plan_reddog_wre_queue_consumer_dry_run(
    work_state_snapshot: Mapping[str, Any],
    *,
    now_iso: Optional[str] = None,
    requested_queue_item_id: Optional[str] = None,
    require_governed_lineage: bool = False,
) -> WREQueueConsumerDryRunResult:
    """Validate one authoritative WRE queue item without executing it."""

    snapshot = _mapping(work_state_snapshot)
    reasons: List[str] = []
    if snapshot.get("schema_version") != WORK_STATE_SCHEMA_VERSION:
        reasons.append(FAIL_SCHEMA_VERSION)

    queue_items = _list_of_mappings(snapshot.get("wre_queue_items"))
    claims = _list_of_mappings(snapshot.get("worker_claims"))
    freshness_receipts = _list_of_mappings(snapshot.get("freshness_receipts"))
    selected, select_reasons = _select_queue_item(queue_items, requested_queue_item_id)
    reasons.extend(select_reasons)
    if selected is None:
        return _reject(reasons)

    queue_item_id = str(selected.get("queue_item_id") or "")
    slice_id = str(selected.get("slice_id") or "")
    claim_id = str(selected.get("claim_id") or "")
    worker_id = str(selected.get("worker_id") or "")
    status = str(selected.get("status") or "").upper()
    evidence_refs = [str(ref) for ref in selected.get("evidence_refs") or []]

    if status != "QUEUED":
        reasons.append(FAIL_QUEUE_ITEM_STATUS)
    if selected.get("no_execution_performed") is not True:
        reasons.append(FAIL_QUEUE_ALREADY_EXECUTED)

    claim = _find_by_id(claims, "claim_id", claim_id)
    if claim is None:
        reasons.append(FAIL_CLAIM_MISSING)
        claim = {}
    if claim and str(claim.get("status") or "").upper() != "ACTIVE":
        reasons.append(FAIL_CLAIM_STATUS)
    if claim and (
        str(claim.get("slice_id") or "") != slice_id
        or str(claim.get("worker_id") or "") != worker_id
    ):
        reasons.append(FAIL_QUEUE_CLAIM_MISMATCH)

    expires_at = _parse_iso(claim.get("expires_at")) if claim else None
    if expires_at is None or expires_at <= _now(now_iso):
        reasons.append(FAIL_CLAIM_EXPIRED)

    freshness_receipt_id = str(claim.get("freshness_receipt_id") or "") if claim else ""
    freshness = _find_by_id(freshness_receipts, "receipt_id", freshness_receipt_id)
    if not freshness or freshness.get("fresh") is not True:
        reasons.append(FAIL_FRESHNESS_RECEIPT)

    wsp15_allocation = _mapping(selected.get("wsp15_allocation_receipt"))
    allocation_receipt_id = str(wsp15_allocation.get("receipt_id") or "")
    allocation_priority = str(wsp15_allocation.get("priority") or "")
    allocation_tier = str(wsp15_allocation.get("reasoning_tier") or "")
    allocation_total = wsp15_allocation.get("mps_total")
    allocation_worker_plan = _mapping(wsp15_allocation.get("worker_plan"))
    allocation_digest = _digest(wsp15_allocation) if wsp15_allocation else ""
    if (
        not allocation_receipt_id.startswith("sha256:")
        or not allocation_digest.startswith("sha256:")
        or not allocation_priority
        or not allocation_tier
        or not isinstance(allocation_total, int)
        or not allocation_worker_plan
    ):
        reasons.append(FAIL_WSP15_ALLOCATION_RECEIPT)
    stage_receipt = _mapping(selected.get("progressive_policy_stage_receipt"))
    stage_receipt_id = str(selected.get("progressive_policy_stage_receipt_id") or "")
    stage_digest = str(selected.get("progressive_policy_stage_digest") or "")
    if not validate_queue_bounded_stage_binding(selected, wsp15_allocation):
        reasons.append(FAIL_PROGRESSIVE_POLICY_STAGE)

    expected_refs = {
        f"claim:{claim_id}",
        f"freshness:{freshness_receipt_id}",
        f"wsp15_allocation:{allocation_receipt_id}",
    }
    if require_governed_lineage:
        governed_reasons, governed_refs = _governed_lineage_reasons(selected, claim)
        reasons.extend(governed_reasons)
        expected_refs.update(governed_refs)
    if not expected_refs.issubset(set(evidence_refs)):
        reasons.append(FAIL_QUEUE_EVIDENCE_REFS)

    deduped = _dedupe(reasons)
    if deduped:
        return WREQueueConsumerDryRunResult(
            accepted=False,
            status=WRE_QUEUE_CONSUMER_DRYRUN_REJECT,
            rejection_reasons=deduped,
            receipt=None,
            selected_queue_item_id=queue_item_id or None,
            selected_slice=slice_id or None,
            next_required_gate=None,
        )

    receipt_seed = {
        "queue_item_id": queue_item_id,
        "slice_id": slice_id,
        "claim_id": claim_id,
        "worker_id": worker_id,
        "freshness_receipt_id": freshness_receipt_id,
        "operational_snapshot_id": str(
            snapshot.get("snapshot_id")
            or snapshot.get("operational_snapshot_id")
            or _digest(snapshot)
        ),
        "wsp15_allocation_receipt_id": allocation_receipt_id,
        "wsp15_allocation_digest": allocation_digest,
        "wsp15_priority": allocation_priority,
        "wsp15_mps_total": allocation_total,
        "reasoning_tier": allocation_tier,
        "progressive_policy_stage_receipt_id": stage_receipt_id, "progressive_policy_stage_digest": stage_digest,
        "model_selection_receipt_id": str(selected.get("model_selection_receipt_id") or ""),
        "model_selection_digest": str(selected.get("model_selection_digest") or ""),
        **model_runtime_authority_fields(selected),
        "memex_supply_receipt_id": str(selected.get("memex_supply_receipt_id") or ""),
        "memex_supply_digest": str(selected.get("memex_supply_digest") or ""),
        "next_required_gate": NEXT_GATE_SIGNED_AUTHORITY_REQUIRED,
    }
    receipt = build_queue_consumer_receipt(receipt_seed)
    return WREQueueConsumerDryRunResult(
        accepted=True,
        status=WRE_QUEUE_CONSUMER_DRYRUN_READY,
        rejection_reasons=[],
        receipt=receipt,
        selected_queue_item_id=queue_item_id,
        selected_slice=slice_id,
        next_required_gate=NEXT_GATE_SIGNED_AUTHORITY_REQUIRED,
        execution_ready=False,
    )


def _governed_lineage_reasons(
    queue: Mapping[str, Any], claim: Mapping[str, Any]
) -> tuple[list[str], set[str]]:
    reasons: list[str] = []
    refs: set[str] = set()
    if str(claim.get("lane_id") or "") != "reddog_operational":
        reasons.append(f"{FAIL_QUEUE_GOVERNED_LINEAGE}:lane_id")
    if not str(claim.get("reconciliation_report_id") or ""):
        reasons.append(f"{FAIL_QUEUE_GOVERNED_LINEAGE}:reconciliation_report_id")
    governed_ids = {
        "source_determination_receipt_id": "architect_determination",
        "model_selection_receipt_id": "model_selection",
        "memex_supply_receipt_id": "memex_supply",
    }
    for field, evidence_kind in governed_ids.items():
        queue_value = str(queue.get(field) or "")
        if not queue_value or queue_value != str(claim.get(field) or ""):
            reasons.append(f"{FAIL_QUEUE_GOVERNED_LINEAGE}:{field}")
        refs.add(f"{evidence_kind}:{queue_value}")
    runtime_reasons, runtime_refs = _runtime_lineage_reasons(queue, claim)
    reasons.extend(runtime_reasons)
    refs.update(runtime_refs)
    for field in ("model_selection_digest", "memex_supply_digest"):
        if not str(queue.get(field) or "").startswith("sha256:"):
            reasons.append(f"{FAIL_QUEUE_GOVERNED_LINEAGE}:{field}")
    return reasons, refs


def _runtime_lineage_reasons(
    queue: Mapping[str, Any], claim: Mapping[str, Any]
) -> tuple[list[str], set[str]]:
    reasons: list[str] = []
    refs: set[str] = set()
    runtime_id = str(queue.get("model_runtime_binding_receipt_id") or "")
    runtime_digest = str(queue.get("model_runtime_binding_digest") or "")
    verification_id = str(
        queue.get("model_runtime_binding_verification_receipt_id") or ""
    )
    verification_digest = str(
        queue.get("model_runtime_binding_verification_digest") or ""
    )
    binding_presence = tuple(
        bool(value)
        for value in (
            runtime_id,
            runtime_digest,
            verification_id,
            verification_digest,
        )
    )
    if any(binding_presence) and not all(binding_presence):
        reasons.append(f"{FAIL_QUEUE_GOVERNED_LINEAGE}:model_runtime_binding_pair")
    if runtime_id:
        if runtime_id != str(claim.get("model_runtime_binding_receipt_id") or ""):
            reasons.append(f"{FAIL_QUEUE_GOVERNED_LINEAGE}:model_runtime_binding_receipt_id")
        if verification_id != str(
            claim.get("model_runtime_binding_verification_receipt_id") or ""
        ):
            reasons.append(
                f"{FAIL_QUEUE_GOVERNED_LINEAGE}:"
                "model_runtime_binding_verification_receipt_id"
            )
        if not verification_digest.startswith("sha256:"):
            reasons.append(
                f"{FAIL_QUEUE_GOVERNED_LINEAGE}:"
                "model_runtime_binding_verification_digest"
            )
        refs.add(f"model_runtime_binding:{runtime_id}")
        refs.add(f"model_runtime_binding_verification:{verification_id}")
    return reasons, refs


__all__ = [
    "FAIL_CLAIM_EXPIRED",
    "FAIL_CLAIM_MISSING",
    "FAIL_CLAIM_STATUS",
    "FAIL_FRESHNESS_RECEIPT",
    "FAIL_NO_QUEUE_ITEM",
    "FAIL_QUEUE_ALREADY_EXECUTED",
    "FAIL_QUEUE_CLAIM_MISMATCH",
    "FAIL_QUEUE_EVIDENCE_REFS",
    "FAIL_QUEUE_ITEM_STATUS",
    "FAIL_REQUESTED_QUEUE_NOT_FOUND",
    "FAIL_QUEUE_GOVERNED_LINEAGE",
    "FAIL_SCHEMA_VERSION",
    "NEXT_GATE_SIGNED_AUTHORITY_REQUIRED",
    "WREQueueConsumerDryRunReceipt",
    "WREQueueConsumerDryRunResult",
    "WRE_QUEUE_CONSUMER_DRYRUN_READY",
    "WRE_QUEUE_CONSUMER_DRYRUN_REJECT",
    "plan_reddog_wre_queue_consumer_dry_run",
]
