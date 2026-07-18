"""Promote a backend architect FIX determination into the signed WSP15 queue.

Slice: REDDOG_ARCHITECT_FIX_TO_SIGNED_WSP15_WORK_ORDER_PROMOTION_PHASE1

This module is the runtime bridge between the backend architect determination
receipt and the already-built resident queue signing chain. It atomically adds
one durable worker claim and one WRE queue item to the authoritative work-state
store, then returns the authority profile that the existing signer/materializer
path consumes.

It does not sign authority, spawn workers, create worktrees, run shell commands,
enqueue OpenClaw, dispatch Hermes, create PRs, admit PatternMemory, settle
rewards, or re-index HoloIndex.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping, Optional

from modules.ai_intelligence.ai_gateway.src.model_intelligence_selection import (
    SelectionDecision,
    SelectionPurpose,
)
from modules.ai_intelligence.ai_gateway.src.model_runtime_binding import (
    ModelRuntimeBindingDecision,
)
from modules.ai_intelligence.ai_gateway.src.model_signed_evidence import (
    rehydrate_model_runtime_binding_receipt,
    rehydrate_model_selection_receipt,
)
from modules.communication.moltbot_bridge.src.reddog_authoritative_work_state_refresh_runtime import (
    AuthoritativeWorkStateStore,
    WORK_STATE_SCHEMA_VERSION,
)
from modules.communication.moltbot_bridge.src.reddog_backend_architect_determination_runtime import (
    ACTION_FIX,
    ARCHITECT_DETERMINATION_ACCEPT,
    ARCHITECT_QUEUE_CANDIDATE_SCHEMA_VERSION,
)
from modules.communication.moltbot_bridge.src.reddog_wsp15_allocation_receipt import (
    canonical_reddog_wsp15_allocation_digest,
    validate_reddog_wsp15_allocation_receipt,
)


ARCHITECT_FIX_WSP15_PROMOTION_ACCEPT = "ARCHITECT_FIX_WSP15_PROMOTION_ACCEPT"
ARCHITECT_FIX_WSP15_PROMOTION_REJECT = "ARCHITECT_FIX_WSP15_PROMOTION_REJECT"
ARCHITECT_FIX_WSP15_PROMOTION_SCHEMA_VERSION = (
    "reddog_architect_fix_wsp15_work_order_promotion.v1"
)


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
    HOLOINDEX_EVIDENCE_MISSING = "REJECT_ARCHITECT_FIX_PROMOTION_HOLOINDEX_EVIDENCE_MISSING"
    DUPLICATE_QUEUE_ITEM = "REJECT_ARCHITECT_FIX_PROMOTION_DUPLICATE_QUEUE_ITEM"
    STORE_REJECTED = "REJECT_ARCHITECT_FIX_PROMOTION_STORE_REJECTED"


_AUTHORITY_PROFILE_REQUIRED = (
    "principal_id",
    "principal_provider",
    "principal_public_key",
    "reddog_id",
    "reddog_public_key",
    "repo_full_name",
    "foundup_id",
    "allowed_paths",
    "denied_paths",
    "requested_operation",
    "permission_snapshot_digest",
    "identity_nonce",
    "work_authority_nonce",
    "issued_at",
    "identity_expires_at",
    "work_authority_expires_at",
    "valve_state_required",
    "key_epoch",
    "required_tests",
    "required_policy_gates",
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
    model_catalog_snapshot_id: str
    model_selection_receipt_id: str
    model_selection_digest: str
    memex_supply_receipt_id: str
    memex_supply_digest: str
    committed_revision: Optional[str]
    model_runtime_binding_receipt_id: Optional[str] = None
    model_runtime_binding_digest: Optional[str] = None
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


def promote_reddog_architect_fix_to_signed_wsp15_work_order(
    *,
    architect_determination: Mapping[str, Any],
    work_state_store: AuthoritativeWorkStateStore,
    authority_profile: Mapping[str, Any],
    model_selection_receipt: Mapping[str, Any],
    memex_supply_receipt: Mapping[str, Any],
    model_runtime_binding_receipt: Mapping[str, Any] | None = None,
    worker_id: str,
    now_iso: str,
    claim_ttl_seconds: int = 3600,
) -> ArchitectFixPromotionResult:
    """Commit one architect FIX queue item and return its signer authority profile."""

    current = work_state_store.load()
    reasons: list[str] = []
    if current.get("schema_version") != WORK_STATE_SCHEMA_VERSION:
        reasons.append(ArchitectFixPromotionReason.WORK_STATE_SCHEMA)
    freshness_id = _freshness_receipt_id(current)
    if not freshness_id:
        reasons.append(ArchitectFixPromotionReason.WORK_STATE_FRESHNESS)

    determination = _determination_receipt(architect_determination)
    candidate = _mapping(determination.get("queue_candidate"))
    determination_id = str(determination.get("determination_receipt_id") or "")
    if not determination:
        reasons.append(ArchitectFixPromotionReason.DETERMINATION_MISSING)
    elif determination.get("accepted") is not True or determination.get("status") != ARCHITECT_DETERMINATION_ACCEPT:
        reasons.append(ArchitectFixPromotionReason.DETERMINATION_NOT_ACCEPTED)
    elif str(determination.get("action") or "").upper() != ACTION_FIX:
        reasons.append(ArchitectFixPromotionReason.DETERMINATION_NOT_FIX)
    if not candidate:
        reasons.append(ArchitectFixPromotionReason.QUEUE_CANDIDATE_MISSING)

    candidate_reasons = _validate_candidate(candidate, determination)
    reasons.extend(candidate_reasons)
    allocation = _mapping(candidate.get("wsp15_allocation_receipt"))
    allocation_validation = validate_reddog_wsp15_allocation_receipt(allocation)
    if not allocation_validation.accepted:
        reasons.append(ArchitectFixPromotionReason.WSP15_ALLOCATION_INVALID)
    elif (
        str(determination.get("wsp15_allocation_receipt_id") or "") != str(allocation.get("receipt_id") or "")
        or str(determination.get("wsp15_allocation_digest") or "")
        != canonical_reddog_wsp15_allocation_digest(allocation)
    ):
        reasons.append(ArchitectFixPromotionReason.WSP15_ALLOCATION_MISMATCH)

    selection_payload = _validate_model_selection(model_selection_receipt, reasons)
    runtime_binding_payload = _validate_model_runtime_binding(
        model_runtime_binding_receipt,
        selection_payload,
        reasons,
    )
    memex_payload = _validate_memex_supply(memex_supply_receipt, determination, reasons)
    profile_reasons = _validate_authority_profile(authority_profile)
    reasons.extend(profile_reasons)
    holoindex_evidence = _mapping(authority_profile.get("holoindex_evidence"))
    if not holoindex_evidence:
        reasons.append(ArchitectFixPromotionReason.HOLOINDEX_EVIDENCE_MISSING)

    selected_slice = str(determination.get("next_slice_name") or "")
    if selected_slice and _duplicate_queue(current, selected_slice=selected_slice, determination_id=determination_id):
        reasons.append(ArchitectFixPromotionReason.DUPLICATE_QUEUE_ITEM)

    if reasons:
        return _reject(reasons)

    assert freshness_id
    assert selection_payload
    assert memex_payload
    assert selected_slice
    now = _parse_iso(now_iso)
    expires_at = (now + timedelta(seconds=int(claim_ttl_seconds))).isoformat()
    model_selection_digest = _digest(model_selection_receipt)
    model_runtime_binding_digest = _digest(model_runtime_binding_receipt) if runtime_binding_payload else None
    memex_supply_digest = _digest(memex_supply_receipt)
    allocation_digest = canonical_reddog_wsp15_allocation_digest(allocation)

    claim_seed = {
        "selected_slice": selected_slice,
        "determination_receipt_id": determination_id,
        "model_selection_receipt_id": selection_payload["receipt_id"],
        "model_runtime_binding_receipt_id": runtime_binding_payload.get("receipt_id", ""),
        "memex_supply_receipt_id": memex_payload["receipt_id"],
        "worker_id": worker_id,
        "claimed_at": now_iso,
        "freshness_receipt_id": freshness_id,
    }
    claim_id = _digest(claim_seed)
    queue_seed = {
        "slice_id": selected_slice,
        "claim_id": claim_id,
        "worker_id": worker_id,
        "enqueued_at": now_iso,
        "determination_receipt_id": determination_id,
        "wsp15_allocation_receipt_id": allocation["receipt_id"],
        "model_selection_receipt_id": selection_payload["receipt_id"],
        "model_runtime_binding_receipt_id": runtime_binding_payload.get("receipt_id", ""),
        "memex_supply_receipt_id": memex_payload["receipt_id"],
    }
    queue_item_id = _digest(queue_seed)

    claim = {
        "claim_id": claim_id,
        "slice_id": selected_slice,
        "worker_id": worker_id,
        "lane_id": "reddog_operational",
        "claimed_at": now_iso,
        "expires_at": expires_at,
        "reconciliation_report_id": str(current.get("reconciliation_report_id") or determination_id),
        "freshness_receipt_id": freshness_id,
        "status": "ACTIVE",
        "source_determination_receipt_id": determination_id,
        "model_selection_receipt_id": selection_payload["receipt_id"],
        "model_runtime_binding_receipt_id": runtime_binding_payload.get("receipt_id", ""),
        "memex_supply_receipt_id": memex_payload["receipt_id"],
    }
    evidence_refs = tuple(
        dict.fromkeys(
            [
                f"claim:{claim_id}",
                f"freshness:{freshness_id}",
                f"wsp15_allocation:{allocation['receipt_id']}",
                f"architect_determination:{determination_id}",
                f"model_selection:{selection_payload['receipt_id']}",
                *(
                    [f"model_runtime_binding:{runtime_binding_payload['receipt_id']}"]
                    if runtime_binding_payload
                    else []
                ),
                f"memex_supply:{memex_payload['receipt_id']}",
                *[str(ref) for ref in candidate.get("evidence_refs") or ()],
            ]
        )
    )
    queue_item = {
        "queue_item_id": queue_item_id,
        "slice_id": selected_slice,
        "claim_id": claim_id,
        "worker_id": worker_id,
        "status": "QUEUED",
        "enqueued_at": now_iso,
        "evidence_refs": list(evidence_refs),
        "wsp15_allocation_receipt": dict(allocation),
        "source_determination_receipt_id": determination_id,
        "source_queue_candidate_id": str(candidate.get("queue_candidate_id") or ""),
        "model_catalog_snapshot_id": selection_payload["catalog_snapshot_id"],
        "model_selection_receipt_id": selection_payload["receipt_id"],
        "model_selection_digest": model_selection_digest,
        "model_runtime_binding_receipt_id": runtime_binding_payload.get("receipt_id", ""),
        "model_runtime_binding_digest": model_runtime_binding_digest or "",
        "memex_supply_receipt_id": memex_payload["receipt_id"],
        "memex_supply_digest": memex_supply_digest,
        "no_execution_performed": True,
    }
    sync_receipt = {
        "sync_id": _digest({"queue_item_id": queue_item_id, "claim_id": claim_id}),
        "status": "WRE_QUEUE_SYNCED",
        "queue_item_ids": [queue_item_id],
        "selected_slice": selected_slice,
        "rejection_reasons": [],
        "source": ARCHITECT_FIX_WSP15_PROMOTION_SCHEMA_VERSION,
        "no_execution_performed": True,
    }

    promoted_profile = _promoted_authority_profile(
        authority_profile=authority_profile,
        determination=determination,
        allocation=allocation,
        model_selection_receipt=model_selection_receipt,
        model_selection=selection_payload,
        model_selection_digest=model_selection_digest,
        model_runtime_binding_receipt=model_runtime_binding_receipt,
        model_runtime_binding=runtime_binding_payload,
        model_runtime_binding_digest=model_runtime_binding_digest,
        memex_supply=memex_payload,
        memex_supply_digest=memex_supply_digest,
        queue_item_id=queue_item_id,
        claim_id=claim_id,
        holoindex_evidence=holoindex_evidence,
    )
    updated = _append_queue_state(
        current,
        claim=claim,
        queue_item=queue_item,
        sync_receipt=sync_receipt,
        promotion_record={
            "schema_version": ARCHITECT_FIX_WSP15_PROMOTION_SCHEMA_VERSION,
            "architect_determination_receipt_id": determination_id,
            "queue_item_id": queue_item_id,
            "claim_id": claim_id,
            "model_selection_receipt_id": selection_payload["receipt_id"],
            "model_runtime_binding_receipt_id": runtime_binding_payload.get("receipt_id", ""),
            "memex_supply_receipt_id": memex_payload["receipt_id"],
            "created_at": now_iso,
        },
    )

    try:
        committed_revision = work_state_store.commit(updated, expected_revision=current.get("revision"))
    except Exception:
        return _reject([ArchitectFixPromotionReason.STORE_REJECTED])
    committed = work_state_store.load()

    receipt_seed = {
        "determination_receipt_id": determination_id,
        "queue_item_id": queue_item_id,
        "claim_id": claim_id,
        "model_selection_receipt_id": selection_payload["receipt_id"],
        "model_runtime_binding_receipt_id": runtime_binding_payload.get("receipt_id", ""),
        "memex_supply_receipt_id": memex_payload["receipt_id"],
        "committed_revision": committed_revision,
    }
    receipt = ArchitectFixPromotionReceipt(
        schema_version=ARCHITECT_FIX_WSP15_PROMOTION_SCHEMA_VERSION,
        promotion_receipt_id="architect_fix_promotion_" + _digest(receipt_seed).removeprefix("sha256:")[:16],
        status=ARCHITECT_FIX_WSP15_PROMOTION_ACCEPT,
        architect_determination_receipt_id=determination_id,
        source_queue_candidate_id=str(candidate.get("queue_candidate_id") or ""),
        queue_item_id=queue_item_id,
        claim_id=claim_id,
        selected_slice=selected_slice,
        worker_id=worker_id,
        freshness_receipt_id=freshness_id,
        wsp15_allocation_receipt_id=str(allocation["receipt_id"]),
        wsp15_allocation_digest=allocation_digest,
        model_catalog_snapshot_id=selection_payload["catalog_snapshot_id"],
        model_selection_receipt_id=selection_payload["receipt_id"],
        model_selection_digest=model_selection_digest,
        model_runtime_binding_receipt_id=runtime_binding_payload.get("receipt_id") or None,
        model_runtime_binding_digest=model_runtime_binding_digest,
        memex_supply_receipt_id=memex_payload["receipt_id"],
        memex_supply_digest=memex_supply_digest,
        committed_revision=committed_revision,
    )
    return ArchitectFixPromotionResult(
        accepted=True,
        status=ARCHITECT_FIX_WSP15_PROMOTION_ACCEPT,
        receipt=receipt,
        rejection_reasons=(),
        authority_profile=promoted_profile,
        work_state_snapshot=committed,
    )


def _reject(reasons: list[str]) -> ArchitectFixPromotionResult:
    return ArchitectFixPromotionResult(
        accepted=False,
        status=ARCHITECT_FIX_WSP15_PROMOTION_REJECT,
        receipt=None,
        rejection_reasons=tuple(dict.fromkeys(reasons)),
    )


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _digest(payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _parse_iso(value: str) -> datetime:
    text = str(value or "").strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _determination_receipt(value: Mapping[str, Any]) -> Mapping[str, Any]:
    mapping = _mapping(value)
    receipt = _mapping(mapping.get("receipt"))
    return receipt if receipt else mapping


def _freshness_receipt_id(snapshot: Mapping[str, Any]) -> str:
    preferred = str(snapshot.get("refresh_receipt_id") or "")
    receipts = snapshot.get("freshness_receipts")
    if not isinstance(receipts, list):
        return ""
    for receipt in receipts:
        if not isinstance(receipt, Mapping):
            continue
        receipt_id = str(receipt.get("receipt_id") or "")
        if receipt_id and receipt.get("fresh") is True and (not preferred or receipt_id == preferred):
            return receipt_id
    return ""


def _validate_candidate(candidate: Mapping[str, Any], determination: Mapping[str, Any]) -> list[str]:
    reasons: list[str] = []
    if not candidate:
        return reasons
    if candidate.get("schema_version") != ARCHITECT_QUEUE_CANDIDATE_SCHEMA_VERSION:
        reasons.append(ArchitectFixPromotionReason.QUEUE_CANDIDATE_MALFORMED)
    if str(candidate.get("source_determination_receipt_id") or "") != str(
        determination.get("determination_receipt_id") or ""
    ):
        reasons.append(ArchitectFixPromotionReason.QUEUE_CANDIDATE_MALFORMED)
    if str(candidate.get("slice_id") or "") != str(determination.get("next_slice_name") or ""):
        reasons.append(ArchitectFixPromotionReason.QUEUE_CANDIDATE_MALFORMED)
    if str(candidate.get("status") or "").upper() != "CANDIDATE":
        reasons.append(ArchitectFixPromotionReason.QUEUE_CANDIDATE_MALFORMED)
    if candidate.get("no_execution_performed") is not True:
        reasons.append(ArchitectFixPromotionReason.QUEUE_CANDIDATE_MALFORMED)
    if not _mapping(candidate.get("wsp15_allocation_receipt")):
        reasons.append(ArchitectFixPromotionReason.QUEUE_CANDIDATE_MALFORMED)
    return reasons


def _validate_model_selection(selection: Mapping[str, Any], reasons: list[str]) -> Mapping[str, Any]:
    if not isinstance(selection, Mapping) or not selection:
        reasons.append(ArchitectFixPromotionReason.MODEL_SELECTION_MISSING)
        return {}
    try:
        receipt = rehydrate_model_selection_receipt(selection)
    except Exception:
        reasons.append(ArchitectFixPromotionReason.MODEL_SELECTION_INVALID)
        return {}
    if receipt.decision != SelectionDecision.SELECTED or not receipt.selected_model_ids:
        reasons.append(ArchitectFixPromotionReason.MODEL_SELECTION_INVALID)
    if receipt.requirements.purpose != SelectionPurpose.PRODUCTION:
        reasons.append(ArchitectFixPromotionReason.MODEL_SELECTION_NOT_PRODUCTION)
    return {
        "receipt_id": receipt.receipt_id,
        "catalog_snapshot_id": receipt.catalog_snapshot_id,
        "selected_model_ids": tuple(receipt.selected_model_ids),
        "task_family": receipt.requirements.task_family,
        "panel_topology_digest": receipt.panel_topology_digest,
    }


def _validate_model_runtime_binding(
    binding: Mapping[str, Any] | None,
    model_selection: Mapping[str, Any],
    reasons: list[str],
) -> Mapping[str, Any]:
    if not binding:
        return {}
    try:
        receipt = rehydrate_model_runtime_binding_receipt(binding)
    except Exception:
        reasons.append(ArchitectFixPromotionReason.MODEL_RUNTIME_BINDING_INVALID)
        return {}
    if receipt.decision != ModelRuntimeBindingDecision.BOUND:
        reasons.append(ArchitectFixPromotionReason.MODEL_RUNTIME_BINDING_NOT_BOUND)
    if not model_selection:
        reasons.append(ArchitectFixPromotionReason.MODEL_RUNTIME_BINDING_MISMATCH)
    elif (
        receipt.selection_receipt_id != str(model_selection.get("receipt_id") or "")
        or receipt.catalog_snapshot_id != str(model_selection.get("catalog_snapshot_id") or "")
        or receipt.task_family != str(model_selection.get("task_family") or "")
    ):
        reasons.append(ArchitectFixPromotionReason.MODEL_RUNTIME_BINDING_MISMATCH)
    return {
        "receipt_id": receipt.receipt_id,
        "selection_receipt_id": receipt.selection_receipt_id,
        "catalog_snapshot_id": receipt.catalog_snapshot_id,
        "task_family": receipt.task_family,
        "runtime_surface": receipt.runtime_surface,
        "principal_model": receipt.principal_model or "",
        "panel_models": tuple(receipt.panel_models),
        "role_bindings": tuple(binding.to_dict() for binding in receipt.role_bindings),
    }


def _validate_memex_supply(
    memex_supply: Mapping[str, Any],
    determination: Mapping[str, Any],
    reasons: list[str],
) -> Mapping[str, Any]:
    if not isinstance(memex_supply, Mapping) or not memex_supply:
        reasons.append(ArchitectFixPromotionReason.MEMEX_SUPPLY_MISSING)
        return {}
    if memex_supply.get("schema_version") != "reddog_operational_memex_snapshot_supply_receipt.v1":
        reasons.append(ArchitectFixPromotionReason.MEMEX_SUPPLY_INVALID)
    receipt_id = str(memex_supply.get("receipt_id") or "")
    if not receipt_id.startswith("sha256:"):
        reasons.append(ArchitectFixPromotionReason.MEMEX_SUPPLY_INVALID)
    snapshot_receipt_id = str(memex_supply.get("snapshot_receipt_id") or "")
    if snapshot_receipt_id != str(determination.get("snapshot_receipt_id") or ""):
        reasons.append(ArchitectFixPromotionReason.MEMEX_SUPPLY_INVALID)
    if memex_supply.get("no_holoindex_reindex_performed") is not True:
        reasons.append(ArchitectFixPromotionReason.MEMEX_SUPPLY_INVALID)
    return {"receipt_id": receipt_id, "snapshot_receipt_id": snapshot_receipt_id}


def _validate_authority_profile(profile: Mapping[str, Any]) -> list[str]:
    if not isinstance(profile, Mapping) or not profile:
        return [ArchitectFixPromotionReason.AUTHORITY_PROFILE_MISSING]
    missing = [
        field
        for field in _AUTHORITY_PROFILE_REQUIRED
        if field not in profile or profile.get(field) in (None, "", (), [], {})
    ]
    return [ArchitectFixPromotionReason.AUTHORITY_PROFILE_INCOMPLETE + ":" + field for field in missing]


def _duplicate_queue(snapshot: Mapping[str, Any], *, selected_slice: str, determination_id: str) -> bool:
    for item in snapshot.get("wre_queue_items") or ():
        if not isinstance(item, Mapping):
            continue
        if str(item.get("source_determination_receipt_id") or "") == determination_id:
            return True
        if str(item.get("slice_id") or "") == selected_slice and str(item.get("status") or "").upper() == "QUEUED":
            return True
    for claim in snapshot.get("worker_claims") or ():
        if not isinstance(claim, Mapping):
            continue
        if str(claim.get("source_determination_receipt_id") or "") == determination_id:
            return True
        if str(claim.get("slice_id") or "") == selected_slice and str(claim.get("status") or "").upper() == "ACTIVE":
            return True
    return False


def _promoted_authority_profile(
    *,
    authority_profile: Mapping[str, Any],
    determination: Mapping[str, Any],
    allocation: Mapping[str, Any],
    model_selection_receipt: Mapping[str, Any],
    model_selection: Mapping[str, Any],
    model_selection_digest: str,
    model_runtime_binding_receipt: Mapping[str, Any] | None,
    model_runtime_binding: Mapping[str, Any],
    model_runtime_binding_digest: str | None,
    memex_supply: Mapping[str, Any],
    memex_supply_digest: str,
    queue_item_id: str,
    claim_id: str,
    holoindex_evidence: Mapping[str, Any],
) -> Mapping[str, Any]:
    profile = dict(authority_profile)
    determination_id = str(determination["determination_receipt_id"])
    work_order_id = _work_order_id(queue_item_id)
    binding = _promoted_operational_binding(
        determination=determination,
        allocation=allocation,
        model_selection_receipt=model_selection_receipt,
        model_selection=model_selection,
        model_selection_digest=model_selection_digest,
        model_runtime_binding_receipt=model_runtime_binding_receipt,
        model_runtime_binding=model_runtime_binding,
        model_runtime_binding_digest=model_runtime_binding_digest,
        memex_supply=memex_supply,
        memex_supply_digest=memex_supply_digest,
        work_order_id=work_order_id,
        queue_item_id=queue_item_id,
        claim_id=claim_id,
        holoindex_evidence=holoindex_evidence,
    )
    profile.update(
        _promoted_profile_updates(
            profile=profile,
            determination=determination,
            binding=binding,
            allocation=allocation,
            model_selection_receipt=model_selection_receipt,
            model_selection=model_selection,
            model_selection_digest=model_selection_digest,
            model_runtime_binding=model_runtime_binding,
            model_runtime_binding_digest=model_runtime_binding_digest,
            memex_supply=memex_supply,
            memex_supply_digest=memex_supply_digest,
            work_order_id=work_order_id,
            holoindex_evidence=holoindex_evidence,
        )
    )
    if model_runtime_binding:
        profile["model_runtime_binding_receipt"] = dict(model_runtime_binding_receipt or {})
        profile["model_runtime_binding_runtime_surface"] = model_runtime_binding["runtime_surface"]
        profile["model_runtime_binding_principal_model"] = model_runtime_binding["principal_model"]
        profile["model_runtime_binding_panel_models"] = list(model_runtime_binding["panel_models"])
        profile["model_runtime_binding_role_bindings"] = list(model_runtime_binding["role_bindings"])
    return profile


def _promoted_operational_binding(**values: Any) -> dict[str, Any]:
    determination = values["determination"]
    model_selection = values["model_selection"]
    model_runtime_binding = values["model_runtime_binding"]
    memex_supply = values["memex_supply"]
    determination_id = str(determination["determination_receipt_id"])
    binding = {
        "work_order_id": values["work_order_id"],
        "snapshot_receipt_id": str(determination.get("snapshot_receipt_id") or ""),
        "context_view_id": str(determination.get("context_view_id") or ""),
        "evidence_bundle_id": str(determination.get("evidence_bundle_id") or ""),
        "determination_id": determination_id,
        "readonly_audit_decision_id": determination_id,
        "architect_determination_receipt_id": determination_id,
        "queue_item_id": values["queue_item_id"],
        "claim_id": values["claim_id"],
        "wsp15_allocation_receipt": dict(values["allocation"]),
        "model_catalog_snapshot_id": model_selection["catalog_snapshot_id"],
        "model_selection_receipt_id": model_selection["receipt_id"],
        "model_selection_digest": values["model_selection_digest"],
        "model_selection_receipt": dict(values["model_selection_receipt"]),
        "model_runtime_binding_receipt_id": model_runtime_binding.get("receipt_id", ""),
        "model_runtime_binding_digest": values["model_runtime_binding_digest"] or "",
        "memex_supply_receipt_id": memex_supply["receipt_id"],
        "memex_supply_digest": values["memex_supply_digest"],
        "holoindex_evidence": dict(values["holoindex_evidence"]),
    }
    if model_runtime_binding:
        binding.update(
            {
                "model_runtime_binding_receipt": dict(values["model_runtime_binding_receipt"] or {}),
                "model_runtime_binding_runtime_surface": model_runtime_binding["runtime_surface"],
                "model_runtime_binding_principal_model": model_runtime_binding["principal_model"],
                "model_runtime_binding_panel_models": list(model_runtime_binding["panel_models"]),
                "model_runtime_binding_role_bindings": list(model_runtime_binding["role_bindings"]),
            }
        )
    return binding


def _promoted_profile_updates(**values: Any) -> dict[str, Any]:
    profile = values["profile"]
    determination = values["determination"]
    binding = values["binding"]
    model_selection = values["model_selection"]
    model_runtime_binding = values["model_runtime_binding"]
    memex_supply = values["memex_supply"]
    determination_id = str(determination["determination_receipt_id"])
    return {
            "work_order_id": values["work_order_id"],
            "task_summary": str(
                profile.get("task_summary")
                or f"RedDog architect FIX promotion for {determination.get('next_slice_name')}."
            ),
            "wsp15_allocation_receipt": dict(values["allocation"]),
            "snapshot_receipt_id": binding["snapshot_receipt_id"],
            "context_view_id": binding["context_view_id"],
            "evidence_bundle_id": binding["evidence_bundle_id"],
            "readonly_audit_decision_id": determination_id,
            "determination_id": determination_id,
            "model_catalog_snapshot_id": model_selection["catalog_snapshot_id"],
            "model_selection_receipt_id": model_selection["receipt_id"],
            "model_selection_digest": values["model_selection_digest"],
            "model_selection_receipt": dict(values["model_selection_receipt"]),
            "model_runtime_binding_receipt_id": model_runtime_binding.get("receipt_id", ""),
            "model_runtime_binding_digest": values["model_runtime_binding_digest"] or "",
            "memex_supply_receipt_id": memex_supply["receipt_id"],
            "memex_supply_digest": values["memex_supply_digest"],
            "operational_context_binding": binding,
            "holoindex_evidence": dict(values["holoindex_evidence"]),
    }


def _work_order_id(queue_item_id: str) -> str:
    return "wre-queue-" + hashlib.sha256(queue_item_id.encode("utf-8")).hexdigest()[:16]


def _append_queue_state(
    snapshot: Mapping[str, Any],
    *,
    claim: Mapping[str, Any],
    queue_item: Mapping[str, Any],
    sync_receipt: Mapping[str, Any],
    promotion_record: Mapping[str, Any],
) -> dict[str, Any]:
    updated = json.loads(json.dumps(snapshot, sort_keys=True, default=str))
    updated["worker_claims"] = [
        dict(item) for item in updated.get("worker_claims", []) if isinstance(item, Mapping)
    ] + [dict(claim)]
    updated["wre_queue_items"] = [
        dict(item) for item in updated.get("wre_queue_items", []) if isinstance(item, Mapping)
    ] + [dict(queue_item)]
    updated["queue_sync_receipts"] = [
        dict(item) for item in updated.get("queue_sync_receipts", []) if isinstance(item, Mapping)
    ] + [dict(sync_receipt)]
    updated["architect_fix_promotions"] = [
        dict(item) for item in updated.get("architect_fix_promotions", []) if isinstance(item, Mapping)
    ] + [dict(promotion_record)]
    updated["selected_slice"] = str(queue_item.get("slice_id") or updated.get("selected_slice") or "")
    updated["no_execution_performed"] = True
    updated["no_holoindex_mutation_performed"] = True
    return updated


__all__ = [
    "ARCHITECT_FIX_WSP15_PROMOTION_ACCEPT",
    "ARCHITECT_FIX_WSP15_PROMOTION_REJECT",
    "ARCHITECT_FIX_WSP15_PROMOTION_SCHEMA_VERSION",
    "ArchitectFixPromotionReason",
    "ArchitectFixPromotionReceipt",
    "ArchitectFixPromotionResult",
    "promote_reddog_architect_fix_to_signed_wsp15_work_order",
]
