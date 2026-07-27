"""Atomic work-state transaction for a verified architect FIX promotion."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Callable, Mapping

from modules.communication.moltbot_bridge.src.reddog_architect_fix_promotion_profile import (
    ArchitectFixPromotionProfileInputs,
    promoted_authority_profile,
)
from modules.communication.moltbot_bridge.src.reddog_architect_fix_promotion_records import (
    ArchitectFixPromotionReason,
    ArchitectFixPromotionReceipt,
    ArchitectFixPromotionRecordInputs,
    ArchitectFixPromotionResult,
    build_architect_fix_promotion_records,
    canonical_digest,
)
from modules.communication.moltbot_bridge.src.reddog_architect_proposal_verified_authority import (
    ArchitectProposalAuthorityBinding,
)
from modules.communication.moltbot_bridge.src.reddog_authoritative_work_state_refresh_runtime import (
    AuthoritativeWorkStateStore,
)
from modules.communication.moltbot_bridge.src.reddog_wsp15_allocation_receipt import (
    canonical_reddog_wsp15_allocation_digest,
)


@dataclass(frozen=True)
class ArchitectFixPromotionTransactionInputs:
    schema_version: str
    accept_status: str
    current: Mapping[str, Any]
    store: AuthoritativeWorkStateStore
    profile_writer: Callable[[Mapping[str, Any]], None]
    authority_profile: Mapping[str, Any]
    determination: Mapping[str, Any]
    candidate: Mapping[str, Any]
    allocation: Mapping[str, Any]
    model_selection_receipt: Mapping[str, Any]
    model_selection: Mapping[str, Any]
    model_runtime_binding_receipt: Mapping[str, Any] | None
    model_runtime_binding: Mapping[str, Any]
    memex_supply: Mapping[str, Any]
    proposal_admission: Mapping[str, Any]
    proposal_authority: ArchitectProposalAuthorityBinding
    selected_slice: str
    determination_id: str
    worker_id: str
    now_iso: str
    expires_at: str
    freshness_receipt_id: str
    holoindex_evidence: Mapping[str, Any]


@dataclass(frozen=True)
class _PromotionDigests:
    model_selection: str
    model_runtime_binding: str | None
    memex_supply: str
    allocation: str
    proposal_admission: str


def execute_architect_fix_promotion_transaction(
    inputs: ArchitectFixPromotionTransactionInputs,
) -> ArchitectFixPromotionResult:
    """Build, persist, and return one verified promotion transaction."""

    if _attestation_consumed(
        inputs.current, inputs.proposal_authority.attestation_id
    ):
        return _reject(
            inputs, ArchitectFixPromotionReason.PROPOSAL_AUTHENTICITY_INVALID
        )
    digests = _digests(inputs)
    records = _build_records(inputs, digests)
    profile = _build_profile(inputs, digests, records)
    updated = _updated_state(inputs, records)
    try:
        inputs.profile_writer(profile)
    except Exception:
        return _reject(
            inputs,
            ArchitectFixPromotionReason.AUTHORITY_PROFILE_PRECOMMIT_WRITE_FAILED,
        )
    try:
        revision = inputs.store.commit(
            updated, expected_revision=inputs.current.get("revision")
        )
    except Exception:
        return _reject(inputs, ArchitectFixPromotionReason.STORE_REJECTED)
    committed = inputs.store.load()
    receipt = _build_receipt(inputs, digests, records, revision)
    return ArchitectFixPromotionResult(
        accepted=True,
        status=inputs.accept_status,
        receipt=receipt,
        rejection_reasons=(),
        authority_profile=profile,
        work_state_snapshot=committed,
    )


def _digests(
    inputs: ArchitectFixPromotionTransactionInputs,
) -> _PromotionDigests:
    runtime_digest = (
        canonical_digest(inputs.model_runtime_binding_receipt)
        if inputs.model_runtime_binding
        else None
    )
    return _PromotionDigests(
        model_selection=canonical_digest(inputs.model_selection_receipt),
        model_runtime_binding=runtime_digest,
        memex_supply=canonical_digest(inputs.memex_supply),
        allocation=canonical_reddog_wsp15_allocation_digest(
            inputs.allocation
        ),
        proposal_admission=canonical_digest(inputs.proposal_admission),
    )


def _build_records(inputs, digests):
    authority = inputs.proposal_authority
    return build_architect_fix_promotion_records(
        ArchitectFixPromotionRecordInputs(
            selected_slice=inputs.selected_slice,
            determination_id=inputs.determination_id,
            worker_id=inputs.worker_id,
            now_iso=inputs.now_iso,
            expires_at=inputs.expires_at,
            freshness_receipt_id=inputs.freshness_receipt_id,
            reconciliation_report_id=str(
                inputs.current.get("reconciliation_report_id")
                or inputs.determination_id
            ),
            proposal_admission_receipt_id=inputs.proposal_admission["receipt_id"],
            proposal_admission_digest=digests.proposal_admission,
            proposal_authenticity_attestation_id=authority.attestation_id,
            proposal_authenticity_attestation_digest=authority.attestation_digest,
            proposal_policy_authorization_id=authority.policy_authorization_id,
            proposal_policy_authorization_digest=authority.policy_authorization_digest,
            proposal_signer_runtime_context_digest=authority.signer_runtime_context_digest,
            authorized_base_sha=inputs.proposal_admission["repo_head_sha"],
            model_selection_digest=digests.model_selection,
            model_runtime_binding_digest=digests.model_runtime_binding or "",
            memex_supply_digest=digests.memex_supply,
            candidate=inputs.candidate,
            allocation=inputs.allocation,
            model_selection=inputs.model_selection,
            model_runtime_binding=inputs.model_runtime_binding,
            memex_supply=inputs.memex_supply,
        )
    )


def _build_profile(inputs, digests, records):
    authority = inputs.proposal_authority
    return promoted_authority_profile(
        ArchitectFixPromotionProfileInputs(
            authority_profile=inputs.authority_profile,
            verified_authority_identity=_verified_identity(authority),
            determination=inputs.determination,
            allocation=inputs.allocation,
            model_selection_receipt=inputs.model_selection_receipt,
            model_selection=inputs.model_selection,
            model_selection_digest=digests.model_selection,
            model_runtime_binding_receipt=inputs.model_runtime_binding_receipt,
            model_runtime_binding=inputs.model_runtime_binding,
            model_runtime_binding_digest=digests.model_runtime_binding,
            memex_supply=inputs.memex_supply,
            memex_supply_digest=digests.memex_supply,
            proposal_admission=inputs.proposal_admission,
            proposal_admission_digest=digests.proposal_admission,
            proposal_authenticity_attestation_id=authority.attestation_id,
            proposal_authenticity_attestation_digest=authority.attestation_digest,
            proposal_policy_authorization_id=authority.policy_authorization_id,
            proposal_policy_authorization_digest=authority.policy_authorization_digest,
            proposal_signer_runtime_context_digest=authority.signer_runtime_context_digest,
            work_order_id=_work_order_id(records.queue_item_id),
            queue_item_id=records.queue_item_id,
            claim_id=records.claim_id,
            holoindex_evidence=inputs.holoindex_evidence,
        )
    )


def _verified_identity(
    authority: ArchitectProposalAuthorityBinding,
) -> dict[str, Any]:
    return {
        "principal_id": authority.principal_id,
        "principal_provider": authority.principal_provider,
        "principal_public_key": authority.principal_public_key,
        "reddog_id": authority.reddog_id,
        "reddog_public_key": authority.reddog_public_key,
        "key_epoch": authority.key_epoch,
        "authority_profile_source_receipt_id": (
            authority.authority_profile_source_receipt_id
        ),
    }


def _updated_state(inputs, records):
    authority = inputs.proposal_authority
    promotion_record = {
        "schema_version": inputs.schema_version,
        "architect_determination_receipt_id": inputs.determination_id,
        "queue_item_id": records.queue_item_id,
        "claim_id": records.claim_id,
        "model_selection_receipt_id": inputs.model_selection["receipt_id"],
        "model_runtime_binding_receipt_id": (
            inputs.model_runtime_binding.get("receipt_id", "")
        ),
        "memex_supply_receipt_id": inputs.memex_supply["receipt_id"],
        "proposal_admission_receipt_id": inputs.proposal_admission["receipt_id"],
        "proposal_authenticity_attestation_id": authority.attestation_id,
        "proposal_authenticity_attestation_digest": authority.attestation_digest,
        "proposal_policy_authorization_id": authority.policy_authorization_id,
        "proposal_policy_authorization_digest": authority.policy_authorization_digest,
        "proposal_signer_runtime_context_digest": authority.signer_runtime_context_digest,
        "created_at": inputs.now_iso,
    }
    return _append_queue_state(
        inputs.current,
        claim=records.claim,
        queue_item=records.queue_item,
        sync_receipt=records.sync_receipt,
        promotion_record=promotion_record,
    )


def _build_receipt(inputs, digests, records, revision):
    authority = inputs.proposal_authority
    seed = _receipt_seed(inputs, records, revision)
    return ArchitectFixPromotionReceipt(
        schema_version=inputs.schema_version,
        promotion_receipt_id=(
            "architect_fix_promotion_"
            + canonical_digest(seed).removeprefix("sha256:")[:16]
        ),
        status=inputs.accept_status,
        architect_determination_receipt_id=inputs.determination_id,
        source_queue_candidate_id=str(
            inputs.candidate.get("queue_candidate_id") or ""
        ),
        queue_item_id=records.queue_item_id,
        claim_id=records.claim_id,
        selected_slice=inputs.selected_slice,
        worker_id=inputs.worker_id,
        freshness_receipt_id=inputs.freshness_receipt_id,
        wsp15_allocation_receipt_id=str(inputs.allocation["receipt_id"]),
        wsp15_allocation_digest=digests.allocation,
        proposal_admission_receipt_id=inputs.proposal_admission["receipt_id"],
        proposal_admission_digest=digests.proposal_admission,
        proposal_authenticity_attestation_id=authority.attestation_id,
        proposal_authenticity_attestation_digest=authority.attestation_digest,
        proposal_policy_authorization_id=authority.policy_authorization_id,
        proposal_policy_authorization_digest=authority.policy_authorization_digest,
        proposal_signer_runtime_context_digest=authority.signer_runtime_context_digest,
        model_catalog_snapshot_id=inputs.model_selection["catalog_snapshot_id"],
        model_selection_receipt_id=inputs.model_selection["receipt_id"],
        model_selection_digest=digests.model_selection,
        model_runtime_binding_receipt_id=(
            inputs.model_runtime_binding.get("receipt_id") or None
        ),
        model_runtime_binding_digest=digests.model_runtime_binding,
        memex_supply_receipt_id=inputs.memex_supply["receipt_id"],
        memex_supply_digest=digests.memex_supply,
        committed_revision=revision,
    )


def _receipt_seed(inputs, records, revision):
    authority = inputs.proposal_authority
    return {
        "determination_receipt_id": inputs.determination_id,
        "queue_item_id": records.queue_item_id,
        "claim_id": records.claim_id,
        "model_selection_receipt_id": inputs.model_selection["receipt_id"],
        "model_runtime_binding_receipt_id": (
            inputs.model_runtime_binding.get("receipt_id", "")
        ),
        "memex_supply_receipt_id": inputs.memex_supply["receipt_id"],
        "proposal_admission_receipt_id": inputs.proposal_admission["receipt_id"],
        "proposal_authenticity_attestation_id": authority.attestation_id,
        "proposal_authenticity_attestation_digest": authority.attestation_digest,
        "proposal_policy_authorization_id": authority.policy_authorization_id,
        "proposal_policy_authorization_digest": authority.policy_authorization_digest,
        "proposal_signer_runtime_context_digest": authority.signer_runtime_context_digest,
        "committed_revision": revision,
    }


def _append_queue_state(snapshot, *, claim, queue_item, sync_receipt, promotion_record):
    updated = json.loads(json.dumps(snapshot, sort_keys=True, default=str))
    collections = {
        "worker_claims": claim,
        "wre_queue_items": queue_item,
        "queue_sync_receipts": sync_receipt,
        "architect_fix_promotions": promotion_record,
    }
    for key, value in collections.items():
        updated[key] = [
            dict(item)
            for item in updated.get(key, [])
            if isinstance(item, Mapping)
        ] + [dict(value)]
    updated["selected_slice"] = str(
        queue_item.get("slice_id") or updated.get("selected_slice") or ""
    )
    updated["no_execution_performed"] = True
    updated["no_holoindex_mutation_performed"] = True
    return updated


def _attestation_consumed(snapshot, attestation_id):
    return any(
        isinstance(item, Mapping)
        and str(item.get("proposal_authenticity_attestation_id") or "")
        == attestation_id
        for item in snapshot.get("architect_fix_promotions") or ()
    )


def _work_order_id(queue_item_id: str) -> str:
    digest = hashlib.sha256(queue_item_id.encode("utf-8")).hexdigest()[:16]
    return "wre-queue-" + digest


def _reject(
    inputs: ArchitectFixPromotionTransactionInputs,
    reason: str,
) -> ArchitectFixPromotionResult:
    return ArchitectFixPromotionResult(
        accepted=False,
        status=inputs.accept_status.replace("ACCEPT", "REJECT"),
        receipt=None,
        rejection_reasons=(reason,),
    )


__all__ = [
    "ArchitectFixPromotionTransactionInputs",
    "execute_architect_fix_promotion_transaction",
]
