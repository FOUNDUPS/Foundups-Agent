"""Atomic work-state transaction for a verified architect FIX promotion."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Callable, Mapping

from modules.communication.moltbot_bridge.src.reddog_architect_fix_promotion_publication import (
    ArchitectFixPromotionPublicationRequest,
)

from modules.communication.moltbot_bridge.src.reddog_architect_fix_promotion_profile import (
    ArchitectFixPromotionProfileInputs,
    promoted_authority_profile,
)
from modules.communication.moltbot_bridge.src.reddog_architect_fix_promotion_records import (
    ArchitectFixPromotionReason,
    ArchitectFixPromotionReceipt,
    ArchitectFixPromotionRecordInputs,
    ArchitectFixPromotionRecords,
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
    publication_publisher: Callable[
        [ArchitectFixPromotionPublicationRequest], str
    ]
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
    agentdb_fix_promotion_claim_fence: Mapping[str, Any]


@dataclass(frozen=True)
class _PromotionDigests:
    model_selection: str
    model_runtime_binding: str | None
    memex_supply: str
    allocation: str
    proposal_admission: str
    claim_fence: str | None


def execute_architect_fix_promotion_transaction(
    inputs: ArchitectFixPromotionTransactionInputs,
) -> ArchitectFixPromotionResult:
    """Build, persist, and return one verified promotion transaction."""

    digests = _digests(inputs)
    if _attestation_consumed(
        inputs.current, inputs.proposal_authority.attestation_id
    ):
        return _reconstruct_committed_result(inputs, digests=digests)
    records = _build_records(inputs, digests)
    profile = _build_profile(inputs, digests, records)
    publication_id = _publication_id(inputs, records)
    profile = {
        **profile,
        "promotion_publication_id": publication_id,
    }
    profile_digest = canonical_digest(profile)
    updated = _updated_state(
        inputs,
        digests,
        records,
        publication_id=publication_id,
        profile_digest=profile_digest,
    )
    try:
        revision = inputs.publication_publisher(
            ArchitectFixPromotionPublicationRequest(
                publication_id=publication_id,
                proposal_authenticity_attestation_id=(
                    inputs.proposal_authority.attestation_id
                ),
                authority_profile=profile,
                updated_work_state=updated,
                expected_work_state_revision=inputs.current.get("revision"),
            )
        )
    except Exception:
        return _reject(inputs, ArchitectFixPromotionReason.STORE_REJECTED)
    committed = inputs.store.load()
    receipt = _build_receipt(
        inputs,
        digests,
        records,
        revision,
        publication_id=publication_id,
        profile_digest=profile_digest,
    )
    return ArchitectFixPromotionResult(
        accepted=True,
        status=inputs.accept_status,
        receipt=receipt,
        rejection_reasons=(),
        authority_profile=profile,
        work_state_snapshot=committed,
    )


def _reconstruct_committed_result(
    inputs: ArchitectFixPromotionTransactionInputs,
    *,
    digests: _PromotionDigests,
) -> ArchitectFixPromotionResult:
    promotions = [
        item
        for item in inputs.current.get("architect_fix_promotions") or ()
        if isinstance(item, Mapping)
        and str(item.get("proposal_authenticity_attestation_id") or "")
        == inputs.proposal_authority.attestation_id
    ]
    if len(promotions) != 1:
        return _reject(
            inputs, ArchitectFixPromotionReason.PROPOSAL_AUTHENTICITY_INVALID
        )
    promotion = promotions[0]
    publication_id = str(promotion.get("publication_id") or "")
    records = _committed_records(inputs.current, promotion)
    if records is None:
        return _reject(
            inputs, ArchitectFixPromotionReason.PROPOSAL_AUTHENTICITY_INVALID
        )
    claim_id = records.claim_id
    queue_item_id = records.queue_item_id
    profile = _build_profile(inputs, digests, records)
    profile = {
        **profile,
        "promotion_publication_id": publication_id,
    }
    profile_digest = canonical_digest(profile)
    committed_fence_digest = str(
        promotion.get("agentdb_fix_promotion_claim_fence_digest") or ""
    )
    if not _replay_claim_fence_matches(inputs, promotion):
        return _reject(
            inputs, ArchitectFixPromotionReason.PROPOSAL_AUTHENTICITY_INVALID
        )
    expected_publication_id = _publication_id(
        inputs,
        records,
        claim_fence_digest=committed_fence_digest or None,
    )
    regenerated = _build_records(inputs, digests)
    if (
        publication_id != expected_publication_id
        or (
            regenerated.claim_id == claim_id
            and regenerated.queue_item_id == queue_item_id
            and (
                canonical_digest(regenerated.claim)
                != canonical_digest(records.claim)
                or canonical_digest(regenerated.queue_item)
                != canonical_digest(records.queue_item)
            )
        )
    ):
        return _reject(
            inputs, ArchitectFixPromotionReason.PROPOSAL_AUTHENTICITY_INVALID
        )
    publications = _matching_records(
        inputs.current,
        "architect_fix_publications",
        "publication_id",
        publication_id,
    )
    if (
        len(publications) != 1
        or publications[0].get("state")
        not in {"STATE_PREPARED", "COMMITTED"}
        or promotion.get("authority_profile_digest") != profile_digest
        or publications[0].get("authority_profile_digest") != profile_digest
        or promotion.get("proposal_authenticity_attestation_id")
        != inputs.proposal_authority.attestation_id
    ):
        return _reject(
            inputs, ArchitectFixPromotionReason.PROPOSAL_AUTHENTICITY_INVALID
        )
    replay_state = json.loads(json.dumps(inputs.current, sort_keys=True))
    replay_state.pop("revision", None)
    replay_state["architect_fix_publications"] = [
        dict(item)
        for item in replay_state.get("architect_fix_publications") or ()
        if isinstance(item, Mapping)
        and str(item.get("publication_id") or "") != publication_id
    ]
    if not replay_state["architect_fix_publications"]:
        replay_state.pop("architect_fix_publications", None)
    try:
        revision = inputs.publication_publisher(
            ArchitectFixPromotionPublicationRequest(
                publication_id=publication_id,
                proposal_authenticity_attestation_id=(
                    inputs.proposal_authority.attestation_id
                ),
                authority_profile=profile,
                updated_work_state=replay_state,
                expected_work_state_revision=inputs.current.get("revision"),
            )
        )
    except Exception:
        return _reject(inputs, ArchitectFixPromotionReason.STORE_REJECTED)
    committed = inputs.store.load()
    committed_publications = _matching_records(
        committed,
        "architect_fix_publications",
        "publication_id",
        publication_id,
    )
    if (
        len(committed_publications) != 1
        or committed_publications[0].get("state") != "COMMITTED"
    ):
        return _reject(inputs, ArchitectFixPromotionReason.STORE_REJECTED)
    return ArchitectFixPromotionResult(
        accepted=True,
        status=inputs.accept_status,
        receipt=_build_receipt(
            inputs,
            digests,
            records,
            revision,
            publication_id=publication_id,
            profile_digest=profile_digest,
            claim_fence_digest=committed_fence_digest or None,
            claim_fence_id=str(
                promotion.get("agentdb_fix_promotion_claim_id") or ""
            )
            or None,
            claim_fence_revision=promotion.get(
                "agentdb_fix_promotion_claim_revision"
            ),
        ),
        rejection_reasons=(),
        authority_profile=profile,
        work_state_snapshot=committed,
    )


def _matching_records(
    snapshot: Mapping[str, Any],
    collection: str,
    field: str,
    value: str,
) -> list[Mapping[str, Any]]:
    return [
        item
        for item in snapshot.get(collection) or ()
        if isinstance(item, Mapping) and str(item.get(field) or "") == value
    ]


def _committed_records(
    snapshot: Mapping[str, Any],
    promotion: Mapping[str, Any],
) -> ArchitectFixPromotionRecords | None:
    publication_id = str(promotion.get("publication_id") or "")
    claim_id = str(promotion.get("claim_id") or "")
    queue_item_id = str(promotion.get("queue_item_id") or "")
    collections = (
        _matching_records(
            snapshot, "architect_fix_publications", "publication_id", publication_id
        ),
        _matching_records(snapshot, "worker_claims", "claim_id", claim_id),
        _matching_records(
            snapshot, "wre_queue_items", "queue_item_id", queue_item_id
        ),
    )
    sync_receipts = [
        item
        for item in snapshot.get("queue_sync_receipts") or ()
        if isinstance(item, Mapping)
        and queue_item_id in {
            str(value) for value in item.get("queue_item_ids") or ()
        }
    ]
    publications, claims, queues = collections
    if any(len(items) != 1 for items in (*collections, sync_receipts)):
        return None
    return ArchitectFixPromotionRecords(
        claim_id=claim_id,
        queue_item_id=queue_item_id,
        claim=dict(claims[0]),
        queue_item=dict(queues[0]),
        sync_receipt=dict(sync_receipts[0]),
        evidence_refs=tuple(
            str(item) for item in queues[0].get("evidence_refs") or ()
        ),
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
        claim_fence=(
            canonical_digest(inputs.agentdb_fix_promotion_claim_fence)
            if inputs.agentdb_fix_promotion_claim_fence
            else None
        ),
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


def _updated_state(
    inputs,
    digests,
    records,
    *,
    publication_id: str,
    profile_digest: str,
):
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
        "proposal_admission_digest": digests.proposal_admission,
        "proposal_authenticity_attestation_id": authority.attestation_id,
        "proposal_authenticity_attestation_digest": authority.attestation_digest,
        "proposal_policy_authorization_id": authority.policy_authorization_id,
        "proposal_policy_authorization_digest": authority.policy_authorization_digest,
        "proposal_signer_runtime_context_digest": authority.signer_runtime_context_digest,
        "publication_id": publication_id,
        "authority_profile_digest": profile_digest,
        "created_at": inputs.now_iso,
    }
    if digests.claim_fence:
        promotion_record.update(
            {
                "agentdb_fix_promotion_claim_id": inputs.agentdb_fix_promotion_claim_fence[
                    "agentdb_claim_id"
                ],
                "agentdb_fix_promotion_claim_revision": inputs.agentdb_fix_promotion_claim_fence[
                    "claim_revision"
                ],
                "agentdb_fix_promotion_claim_fence_digest": digests.claim_fence,
            }
        )
    return _append_queue_state(
        inputs.current,
        claim=records.claim,
        queue_item=records.queue_item,
        sync_receipt=records.sync_receipt,
        promotion_record=promotion_record,
    )


def _build_receipt(
    inputs,
    digests,
    records,
    revision,
    *,
    publication_id: str,
    profile_digest: str,
    claim_fence_digest: str | None = None,
    claim_fence_id: str | None = None,
    claim_fence_revision: int | None = None,
):
    authority = inputs.proposal_authority
    seed = _receipt_seed(
        inputs,
        records,
        revision,
        publication_id=publication_id,
        profile_digest=profile_digest,
        claim_fence_digest=claim_fence_digest or digests.claim_fence,
    )
    return ArchitectFixPromotionReceipt(
        schema_version=inputs.schema_version,
        promotion_receipt_id=_promotion_receipt_id(seed),
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
        **_receipt_evidence_fields(inputs, digests),
        publication_id=publication_id,
        authority_profile_digest=profile_digest,
        committed_revision=revision,
        **_receipt_claim_fence_fields(
            inputs,
            digests,
            claim_fence_id=claim_fence_id,
            claim_fence_revision=claim_fence_revision,
            claim_fence_digest=claim_fence_digest,
        ),
    )


def _promotion_receipt_id(seed: Mapping[str, Any]) -> str:
    return (
        "architect_fix_promotion_"
        + canonical_digest(seed).removeprefix("sha256:")[:16]
    )


def _receipt_evidence_fields(inputs, digests) -> dict[str, Any]:
    return {
        "model_catalog_snapshot_id": inputs.model_selection[
            "catalog_snapshot_id"
        ],
        "model_selection_receipt_id": inputs.model_selection["receipt_id"],
        "model_selection_digest": digests.model_selection,
        "model_runtime_binding_receipt_id": (
            inputs.model_runtime_binding.get("receipt_id") or None
        ),
        "model_runtime_binding_digest": digests.model_runtime_binding,
        "memex_supply_receipt_id": inputs.memex_supply["receipt_id"],
        "memex_supply_digest": digests.memex_supply,
    }


def _receipt_claim_fence_fields(
    inputs,
    digests,
    *,
    claim_fence_id,
    claim_fence_revision,
    claim_fence_digest,
) -> dict[str, Any]:
    fence = inputs.agentdb_fix_promotion_claim_fence
    return {
        "agentdb_fix_promotion_claim_id": (
            claim_fence_id
            or (str(fence.get("agentdb_claim_id")) if fence else None)
        ),
        "agentdb_fix_promotion_claim_revision": (
            claim_fence_revision
            if claim_fence_revision is not None
            else (int(fence["claim_revision"]) if fence else None)
        ),
        "agentdb_fix_promotion_claim_fence_digest": (
            claim_fence_digest or digests.claim_fence
        ),
    }


def _receipt_seed(
    inputs,
    records,
    revision,
    *,
    publication_id: str,
    profile_digest: str,
    claim_fence_digest: str | None = None,
):
    authority = inputs.proposal_authority
    seed = {
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
        "publication_id": publication_id,
        "authority_profile_digest": profile_digest,
        "committed_revision": revision,
    }
    if claim_fence_digest:
        seed["agentdb_fix_promotion_claim_fence_digest"] = claim_fence_digest
    return seed


def _publication_id(
    inputs,
    records,
    *,
    claim_fence_digest: str | None = None,
) -> str:
    seed = {
            "proposal_authenticity_attestation_id": (
                inputs.proposal_authority.attestation_id
            ),
            "queue_item_id": records.queue_item_id,
            "claim_id": records.claim_id,
            "admitted_work_state_revision": inputs.proposal_admission.get(
                "work_state_revision"
            ),
        }
    effective_fence_digest = claim_fence_digest or _digests(inputs).claim_fence
    if effective_fence_digest:
        seed["agentdb_fix_promotion_claim_fence_digest"] = effective_fence_digest
    return canonical_digest(seed)


def _replay_claim_fence_matches(inputs, promotion) -> bool:
    fence = inputs.agentdb_fix_promotion_claim_fence
    stored_claim_id = str(promotion.get("agentdb_fix_promotion_claim_id") or "")
    stored_digest = str(
        promotion.get("agentdb_fix_promotion_claim_fence_digest") or ""
    )
    if not fence:
        return not stored_claim_id and not stored_digest
    return bool(
        stored_claim_id
        and stored_digest
        and stored_claim_id == str(fence.get("agentdb_claim_id") or "")
    )


def _append_queue_state(snapshot, *, claim, queue_item, sync_receipt, promotion_record):
    updated = json.loads(json.dumps(snapshot, sort_keys=True, default=str))
    updated.pop("revision", None)
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
