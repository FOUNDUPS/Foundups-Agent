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

from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Mapping

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
from modules.communication.moltbot_bridge.src.reddog_architect_fix_candidate_gate import (
    CANDIDATE_MALFORMED,
    HOLOINDEX_BINDING_MISMATCH,
    PROPOSAL_ADMISSION_INVALID,
    REPO_HEAD_MISMATCH,
    validate_architect_fix_candidate,
    validate_architect_fix_proposal_admission,
)
from modules.communication.moltbot_bridge.src.reddog_architect_fix_promotion_records import (
    ArchitectFixPromotionReason,
    ArchitectFixPromotionReceipt,
    ArchitectFixPromotionResult,
)
from modules.communication.moltbot_bridge.src.reddog_architect_fix_promotion_transaction import (
    ArchitectFixPromotionTransactionInputs,
    execute_architect_fix_promotion_transaction,
)
from modules.communication.moltbot_bridge.src.reddog_architect_fix_promotion_publication import (
    ArchitectFixPromotionPublicationRequest,
)
from modules.communication.moltbot_bridge.src.reddog_architect_proposal_verified_authority import (
    verify_architect_proposal_promotion_authority,
)
from modules.communication.moltbot_bridge.src.reddog_authority_profile_safety import (
    authority_profile_malformed_digest_paths,
    authority_profile_secret_field_paths,
    authority_profile_unknown_field_paths,
)
from modules.communication.moltbot_bridge.src.reddog_signer_socket_service_runtime_wiring import (
    SignerSocketServiceRuntimeWiringConfig,
)
from modules.communication.moltbot_bridge.src.reddog_work_order_signature_verifier import (
    PrincipalKeyResolver,
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
    "consensus_receipt_digest",
    "authority_profile_source_receipt_id",
    "required_tests",
    "required_policy_gates",
)


def promote_reddog_architect_fix_to_signed_wsp15_work_order(
    *,
    architect_determination: Mapping[str, Any],
    work_state_store: AuthoritativeWorkStateStore,
    authority_profile: Mapping[str, Any],
    model_selection_receipt: Mapping[str, Any],
    memex_supply_receipt: Mapping[str, Any],
    proposal_authenticity_attestation: Mapping[str, Any],
    signer_runtime_config: SignerSocketServiceRuntimeWiringConfig,
    principal_key_resolver: PrincipalKeyResolver,
    model_runtime_binding_receipt: Mapping[str, Any] | None = None,
    worker_id: str,
    now_iso: str,
    claim_ttl_seconds: int = 3600,
    current_repo_head_sha: str | None = None,
    current_holoindex_receipt: Any = None,
    authority_profile_publication_publisher: (
        Callable[[ArchitectFixPromotionPublicationRequest], str] | None
    ) = None,
    current_proposal_revoked_key_epochs: frozenset[str] = frozenset(),
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

    if CANDIDATE_MALFORMED in validate_architect_fix_candidate(
        candidate, determination,
        schema_version=ARCHITECT_QUEUE_CANDIDATE_SCHEMA_VERSION,
    ):
        reasons.append(ArchitectFixPromotionReason.QUEUE_CANDIDATE_MALFORMED)
    selected_slice = str(determination.get("next_slice_name") or "")
    duplicate_queue = bool(
        selected_slice
        and _duplicate_queue(
            current,
            selected_slice=selected_slice,
            determination_id=determination_id,
        )
    )
    retry_attestation_id = str(
        proposal_authenticity_attestation.get("attestation_id") or ""
    )
    if duplicate_queue and not any(
        isinstance(item, Mapping)
        and str(item.get("proposal_authenticity_attestation_id") or "")
        == retry_attestation_id
        for item in current.get("architect_fix_promotions") or ()
    ):
        return _reject([ArchitectFixPromotionReason.DUPLICATE_QUEUE_ITEM])
    proposal_admission, proposal_codes = validate_architect_fix_proposal_admission(
        determination=determination,
        candidate=candidate,
        current_work_state=current,
        current_repo_head_sha=current_repo_head_sha,
        current_holoindex_receipt=current_holoindex_receipt,
        committed_retry_attestation_id=retry_attestation_id,
    )
    if PROPOSAL_ADMISSION_INVALID in proposal_codes:
        reasons.append(ArchitectFixPromotionReason.PROPOSAL_ADMISSION_INVALID)
    if REPO_HEAD_MISMATCH in proposal_codes:
        reasons.append(ArchitectFixPromotionReason.REPO_HEAD_MISMATCH)
    if HOLOINDEX_BINDING_MISMATCH in proposal_codes:
        reasons.append(ArchitectFixPromotionReason.HOLOINDEX_BINDING_MISMATCH)
    if authority_profile_publication_publisher is None:
        reasons.append(
            ArchitectFixPromotionReason.PUBLICATION_COORDINATOR_MISSING
        )
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

    if reasons:
        return _reject(reasons)

    assert freshness_id
    assert selection_payload
    assert memex_payload
    assert proposal_admission is not None
    assert selected_slice
    now = _parse_iso(now_iso)
    try:
        expires_at = (
            now + timedelta(seconds=int(claim_ttl_seconds))
        ).isoformat()
    except (TypeError, ValueError, OverflowError):
        return _reject(
            [ArchitectFixPromotionReason.PROPOSAL_AUTHENTICITY_INVALID]
        )
    try:
        proposal_authority = verify_architect_proposal_promotion_authority(
            attestation=proposal_authenticity_attestation,
            proposal_admission=proposal_admission.to_dict(),
            determination=determination,
            queue_candidate=candidate,
            authority_profile=authority_profile,
            signer_runtime_config=signer_runtime_config,
            principal_key_resolver=principal_key_resolver,
            now_epoch=int(now.timestamp()),
            revoked_key_epochs=frozenset(
                current_proposal_revoked_key_epochs
            ),
        )
    except Exception:
        return _reject(
            [ArchitectFixPromotionReason.PROPOSAL_AUTHENTICITY_INVALID]
        )
    if duplicate_queue and not any(
        isinstance(item, Mapping)
        and str(item.get("proposal_authenticity_attestation_id") or "")
        == proposal_authority.attestation_id
        for item in current.get("architect_fix_promotions") or ()
    ):
        return _reject([ArchitectFixPromotionReason.DUPLICATE_QUEUE_ITEM])
    assert authority_profile_publication_publisher is not None
    return execute_architect_fix_promotion_transaction(
        ArchitectFixPromotionTransactionInputs(
            schema_version=ARCHITECT_FIX_WSP15_PROMOTION_SCHEMA_VERSION,
            accept_status=ARCHITECT_FIX_WSP15_PROMOTION_ACCEPT,
            current=current,
            store=work_state_store,
            publication_publisher=authority_profile_publication_publisher,
            authority_profile=authority_profile,
            determination=determination,
            candidate=candidate,
            allocation=allocation,
            model_selection_receipt=model_selection_receipt,
            model_selection=selection_payload,
            model_runtime_binding_receipt=model_runtime_binding_receipt,
            model_runtime_binding=runtime_binding_payload,
            memex_supply=memex_payload,
            proposal_admission=proposal_admission.to_dict(),
            proposal_authority=proposal_authority,
            selected_slice=selected_slice,
            determination_id=determination_id,
            worker_id=worker_id,
            now_iso=now_iso,
            expires_at=expires_at,
            freshness_receipt_id=freshness_id,
            holoindex_evidence=holoindex_evidence,
        )
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
    reasons = [
        ArchitectFixPromotionReason.AUTHORITY_PROFILE_INCOMPLETE + ":" + field
        for field in missing
    ]
    reasons.extend(
        ArchitectFixPromotionReason.AUTHORITY_PROFILE_SECRET_FIELD + ":" + path
        for path in authority_profile_secret_field_paths(profile)
    )
    reasons.extend(
        ArchitectFixPromotionReason.AUTHORITY_PROFILE_INCOMPLETE
        + ":unknown_field:"
        + path
        for path in authority_profile_unknown_field_paths(profile, seed=False)
    )
    reasons.extend(
        ArchitectFixPromotionReason.AUTHORITY_PROFILE_INCOMPLETE
        + ":digest_format:"
        + path
        for path in authority_profile_malformed_digest_paths(profile)
    )
    return reasons


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


__all__ = [
    "ARCHITECT_FIX_WSP15_PROMOTION_ACCEPT",
    "ARCHITECT_FIX_WSP15_PROMOTION_REJECT",
    "ARCHITECT_FIX_WSP15_PROMOTION_SCHEMA_VERSION",
    "ArchitectFixPromotionReason",
    "ArchitectFixPromotionReceipt",
    "ArchitectFixPromotionResult",
    "promote_reddog_architect_fix_to_signed_wsp15_work_order",
]
