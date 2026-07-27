"""Canonical effect binding for committed architect FIX publications."""

from __future__ import annotations

from typing import Any, Mapping

from modules.communication.moltbot_bridge.src.reddog_architect_fix_promotion_publication_validation import (
    PUBLICATION_COMMITTED,
    architect_fix_committed_publication_reasons,
    architect_fix_publication_state_projection,
    is_revision,
    is_sha256,
    validate_committed_snapshot,
)
from modules.communication.moltbot_bridge.src.reddog_architect_fix_promotion_records import (
    canonical_digest,
)

EFFECT_BINDING_SCHEMA_VERSION = (
    "reddog_architect_fix_publication_effect_binding.v1"
)
FAIL_EFFECT_BINDING_INVALID = "architect_fix_publication_effect_binding_invalid"
FAIL_EFFECT_BINDING_MISSING = "architect_fix_publication_effect_binding_missing"


def committed_publication_effect_binding(
    snapshot: Mapping[str, Any],
    authority_profile: Mapping[str, Any],
    *,
    queue_item_id: str,
    claim_id: str,
) -> dict[str, Any] | None:
    """Derive an effect binding from current durable publication authority."""

    reasons = architect_fix_committed_publication_reasons(
        snapshot,
        authority_profile,
        queue_item_id=queue_item_id,
        claim_id=claim_id,
    )
    if reasons:
        raise RuntimeError(reasons[0])
    publication_id = str(
        authority_profile.get("promotion_publication_id") or ""
    )
    if not publication_id:
        return None
    return _binding_from_state(
        snapshot,
        publication_id=publication_id,
        queue_item_id=queue_item_id,
        claim_id=claim_id,
    )


def signed_publication_effect_binding_reasons(
    snapshot: Mapping[str, Any],
    signed_payload: Mapping[str, Any],
    *,
    queue_item_id: str,
    claim_id: str,
) -> tuple[str, ...]:
    """Recompute and compare a signed publication effect binding."""

    publication_id = str(
        signed_payload.get("architect_fix_publication_receipt_id") or ""
    )
    binding_digest = str(
        signed_payload.get("architect_fix_publication_binding_digest") or ""
    )
    has_promotions = any(
        isinstance(item, Mapping)
        for item in snapshot.get("architect_fix_promotions") or ()
    )
    if not publication_id and not binding_digest:
        return (FAIL_EFFECT_BINDING_MISSING,) if has_promotions else ()
    if not is_sha256(publication_id) or not is_sha256(binding_digest):
        return (FAIL_EFFECT_BINDING_INVALID,)
    try:
        expected = _binding_from_state(
            snapshot,
            publication_id=publication_id,
            queue_item_id=queue_item_id,
            claim_id=claim_id,
        )
    except (RuntimeError, ValueError):
        return (FAIL_EFFECT_BINDING_INVALID,)
    if expected["binding_digest"] != binding_digest:
        return (FAIL_EFFECT_BINDING_INVALID,)
    return ()


def _binding_from_state(
    snapshot: Mapping[str, Any],
    *,
    publication_id: str,
    queue_item_id: str,
    claim_id: str,
) -> dict[str, Any]:
    revision = str(snapshot.get("revision") or "")
    publication = _one_record(
        snapshot.get("architect_fix_publications"),
        "publication_id",
        publication_id,
    )
    promotion = _one_record(
        snapshot.get("architect_fix_promotions"),
        "publication_id",
        publication_id,
    )
    projection = architect_fix_publication_state_projection(
        snapshot,
        publication_id=publication_id,
    )
    if not _state_binding_valid(
        publication,
        promotion,
        revision=revision,
        queue_item_id=queue_item_id,
        claim_id=claim_id,
    ):
        raise RuntimeError(FAIL_EFFECT_BINDING_INVALID)
    validate_committed_snapshot(snapshot, publication)
    if canonical_digest(projection) != publication.get(
        "active_work_state_digest"
    ):
        raise RuntimeError(FAIL_EFFECT_BINDING_INVALID)
    payload = {
        "schema_version": EFFECT_BINDING_SCHEMA_VERSION,
        "publication_id": publication_id,
        "proposal_authenticity_attestation_id": publication[
            "proposal_authenticity_attestation_id"
        ],
        "authority_profile_digest": publication["authority_profile_digest"],
        "active_work_state_digest": publication["active_work_state_digest"],
        "queue_item_id": queue_item_id,
        "claim_id": claim_id,
        "work_state_revision": revision,
    }
    return {**payload, "binding_digest": canonical_digest(payload)}


def _state_binding_valid(
    publication: Mapping[str, Any],
    promotion: Mapping[str, Any],
    *,
    revision: str,
    queue_item_id: str,
    claim_id: str,
) -> bool:
    return (
        publication.get("state") == PUBLICATION_COMMITTED
        and publication.get("base_work_state_digest") is None
        and is_revision(revision)
        and promotion.get("queue_item_id") == queue_item_id
        and promotion.get("claim_id") == claim_id
        and publication.get("authority_profile_digest")
        == promotion.get("authority_profile_digest")
        and publication.get("proposal_authenticity_attestation_id")
        == promotion.get("proposal_authenticity_attestation_id")
    )


def _one_record(
    values: Any,
    field: str,
    expected: str,
) -> Mapping[str, Any]:
    matches = [
        item
        for item in values or ()
        if isinstance(item, Mapping)
        and str(item.get(field) or "") == expected
    ]
    if len(matches) != 1:
        raise RuntimeError(FAIL_EFFECT_BINDING_INVALID)
    return matches[0]


__all__ = [
    "committed_publication_effect_binding",
    "EFFECT_BINDING_SCHEMA_VERSION",
    "FAIL_EFFECT_BINDING_INVALID",
    "FAIL_EFFECT_BINDING_MISSING",
    "signed_publication_effect_binding_reasons",
]
