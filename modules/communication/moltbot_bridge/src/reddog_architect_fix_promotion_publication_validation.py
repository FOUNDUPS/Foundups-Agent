"""Validation and state projection for architect FIX publication."""

from __future__ import annotations

import json
from typing import Any, Mapping

from modules.communication.moltbot_bridge.src.reddog_architect_fix_promotion_records import (
    canonical_digest,
)

PUBLICATION_SCHEMA_VERSION = "reddog_architect_fix_promotion_publication.v1"
STAGED_PROFILE_SCHEMA_VERSION = "reddog_architect_fix_staged_profile.v1"
PUBLICATION_INTENT_PREPARED = "INTENT_PREPARED"
PUBLICATION_STATE_PREPARED = "STATE_PREPARED"
PUBLICATION_PROFILE_PUBLISHED = "PROFILE_PUBLISHED"
PUBLICATION_COMMITTED = "COMMITTED"
_JOURNAL_PHASES = {
    PUBLICATION_INTENT_PREPARED,
    PUBLICATION_STATE_PREPARED,
    PUBLICATION_PROFILE_PUBLISHED,
    PUBLICATION_COMMITTED,
}
_PUBLICATION_RECORD_FIELDS = {
    "schema_version",
    "publication_id",
    "state",
    "proposal_authenticity_attestation_id",
    "authority_profile_digest",
    "active_work_state_digest",
    "base_work_state_digest",
}
_STAGE_FIELDS = {
    "schema_version",
    "publication_id",
    "proposal_authenticity_attestation_id",
    "authority_profile_digest",
    "active_work_state_digest",
    "expected_work_state_revision",
    "authority_profile",
    "active_work_state",
    "receipt_id",
}
_JOURNAL_FIELDS = {
    "schema_version",
    "publication_id",
    "phase",
    "proposal_authenticity_attestation_id",
    "authority_profile_digest",
    "active_work_state_digest",
    "expected_work_state_revision",
    "prepared_revision",
    "committed_revision",
    "receipt_id",
}


def publication_binding(
    stage: Mapping[str, Any],
    *,
    state: str,
    base_work_state_digest: str | None,
) -> dict[str, Any]:
    return {
        "schema_version": PUBLICATION_SCHEMA_VERSION,
        "publication_id": stage["publication_id"],
        "state": state,
        "proposal_authenticity_attestation_id": stage[
            "proposal_authenticity_attestation_id"
        ],
        "authority_profile_digest": stage["authority_profile_digest"],
        "active_work_state_digest": stage["active_work_state_digest"],
        "base_work_state_digest": base_work_state_digest,
    }


def validate_prepared_snapshot(
    current: Mapping[str, Any],
    record: Mapping[str, Any],
    stage: Mapping[str, Any],
) -> None:
    without_publication = without_revision(current)
    without_publication["architect_fix_publications"] = [
        dict(item)
        for item in without_publication.get("architect_fix_publications") or ()
        if isinstance(item, Mapping)
        and item.get("publication_id") != stage["publication_id"]
    ]
    if not without_publication["architect_fix_publications"]:
        without_publication.pop("architect_fix_publications", None)
    if canonical_digest(without_publication) != record.get(
        "base_work_state_digest"
    ):
        raise RuntimeError("architect_fix_publication_prepared_state_changed")


def validate_publication_record(
    record: Mapping[str, Any],
    stage: Mapping[str, Any],
) -> None:
    state = record.get("state")
    if (
        set(record) != _PUBLICATION_RECORD_FIELDS
        or record.get("schema_version") != PUBLICATION_SCHEMA_VERSION
        or not is_sha256(record.get("publication_id"))
        or not is_attestation_id(
            record.get("proposal_authenticity_attestation_id")
        )
        or not is_sha256(record.get("authority_profile_digest"))
        or not is_sha256(record.get("active_work_state_digest"))
        or record.get("publication_id") != stage.get("publication_id")
        or record.get("proposal_authenticity_attestation_id")
        != stage.get("proposal_authenticity_attestation_id")
        or record.get("authority_profile_digest")
        != stage.get("authority_profile_digest")
        or record.get("active_work_state_digest")
        != stage.get("active_work_state_digest")
        or state not in {PUBLICATION_STATE_PREPARED, PUBLICATION_COMMITTED}
        or (
            state == PUBLICATION_STATE_PREPARED
            and not is_sha256(record.get("base_work_state_digest"))
        )
        or (
            state == PUBLICATION_COMMITTED
            and record.get("base_work_state_digest") is not None
        )
    ):
        raise RuntimeError("architect_fix_publication_state_binding_invalid")


def validate_journal(journal: Mapping[str, Any]) -> None:
    unsigned = dict(journal)
    receipt_id = str(unsigned.pop("receipt_id", ""))
    phase = journal.get("phase")
    if (
        set(journal) != _JOURNAL_FIELDS
        or journal.get("schema_version") != PUBLICATION_SCHEMA_VERSION
        or phase not in _JOURNAL_PHASES
        or not is_sha256(journal.get("publication_id"))
        or not is_attestation_id(
            journal.get("proposal_authenticity_attestation_id")
        )
        or not is_sha256(journal.get("authority_profile_digest"))
        or not is_sha256(journal.get("active_work_state_digest"))
        or not is_optional_revision(journal.get("expected_work_state_revision"))
        or not journal_revisions_match_phase(journal, phase=phase)
        or not is_sha256(receipt_id)
        or receipt_id != canonical_digest(unsigned)
    ):
        raise RuntimeError("architect_fix_publication_journal_invalid")


def validate_stage(stage: Mapping[str, Any]) -> None:
    unsigned = dict(stage)
    receipt_id = str(unsigned.pop("receipt_id", ""))
    profile = stage.get("authority_profile")
    active = stage.get("active_work_state")
    if (
        set(stage) != _STAGE_FIELDS
        or stage.get("schema_version") != STAGED_PROFILE_SCHEMA_VERSION
        or receipt_id != canonical_digest(unsigned)
        or not is_sha256(stage.get("publication_id"))
        or not is_attestation_id(
            stage.get("proposal_authenticity_attestation_id")
        )
        or not is_sha256(stage.get("authority_profile_digest"))
        or not is_sha256(stage.get("active_work_state_digest"))
        or not is_optional_revision(stage.get("expected_work_state_revision"))
        or not is_sha256(receipt_id)
        or not isinstance(profile, Mapping)
        or not isinstance(active, Mapping)
        or canonical_digest(profile) != stage.get("authority_profile_digest")
        or canonical_digest(
            architect_fix_publication_state_projection(
                active,
                publication_id=str(stage.get("publication_id") or ""),
            )
        )
        != stage.get("active_work_state_digest")
    ):
        raise RuntimeError("architect_fix_publication_stage_invalid")


def validate_stage_journal_binding(
    stage: Mapping[str, Any],
    journal: Mapping[str, Any],
) -> None:
    for key in (
        "publication_id",
        "proposal_authenticity_attestation_id",
        "authority_profile_digest",
        "active_work_state_digest",
        "expected_work_state_revision",
    ):
        if stage.get(key) != journal.get(key):
            raise RuntimeError(
                "architect_fix_publication_journal_binding_invalid"
            )


def validate_journal_record_binding(
    journal: Mapping[str, Any],
    record: Mapping[str, Any],
) -> None:
    for key in (
        "publication_id",
        "proposal_authenticity_attestation_id",
        "authority_profile_digest",
        "active_work_state_digest",
    ):
        if journal.get(key) != record.get(key):
            raise RuntimeError(
                "architect_fix_publication_journal_binding_invalid"
            )


def validate_committed_snapshot(
    snapshot: Mapping[str, Any],
    record: Mapping[str, Any],
) -> None:
    try:
        projection = architect_fix_publication_state_projection(
            snapshot,
            publication_id=str(record.get("publication_id") or ""),
        )
    except ValueError as exc:
        raise RuntimeError(
            "architect_fix_publication_committed_state_invalid"
        ) from exc
    if canonical_digest(projection) != record.get("active_work_state_digest"):
        raise RuntimeError("architect_fix_publication_committed_state_changed")


def publication_record(
    snapshot: Mapping[str, Any],
    *,
    publication_id: str,
) -> Mapping[str, Any] | None:
    matches = [
        item
        for item in snapshot.get("architect_fix_publications") or ()
        if isinstance(item, Mapping)
        and str(item.get("publication_id") or "") == publication_id
    ]
    if len(matches) > 1:
        raise RuntimeError("architect_fix_publication_record_ambiguous")
    return matches[0] if matches else None


def _promotion_record(
    snapshot: Mapping[str, Any],
    *,
    publication_id: str,
) -> Mapping[str, Any] | None:
    matches = [
        item
        for item in snapshot.get("architect_fix_promotions") or ()
        if isinstance(item, Mapping)
        and str(item.get("publication_id") or "") == publication_id
    ]
    if len(matches) > 1:
        raise RuntimeError("architect_fix_promotion_record_ambiguous")
    return matches[0] if matches else None


def architect_fix_publication_state_projection(
    snapshot: Mapping[str, Any],
    *,
    publication_id: str,
) -> dict[str, Any]:
    """Return the immutable promotion lineage bound by one publication."""

    promotion = _promotion_record(
        snapshot,
        publication_id=publication_id,
    )
    if promotion is None:
        raise ValueError("architect_fix_publication_record_missing")
    queue_item_id = str(promotion.get("queue_item_id") or "")
    claim_id = str(promotion.get("claim_id") or "")
    promotions = _exact_records(
        snapshot.get("architect_fix_promotions"),
        "publication_id",
        publication_id,
    )
    queue_items = _exact_records(
        snapshot.get("wre_queue_items"),
        "queue_item_id",
        queue_item_id,
    )
    claims = _exact_records(
        snapshot.get("worker_claims"),
        "claim_id",
        claim_id,
    )
    if (
        not is_sha256(publication_id)
        or not is_sha256(queue_item_id)
        or not is_sha256(claim_id)
        or len(promotions) != 1
        or len(queue_items) != 1
        or len(claims) != 1
        or str(queue_items[0].get("claim_id") or "") != claim_id
        or str(claims[0].get("claim_id") or "") != claim_id
    ):
        raise ValueError("architect_fix_publication_lineage_invalid")
    return {
        "schema_version": str(snapshot.get("schema_version") or ""),
        "publication_id": publication_id,
        "promotion": dict(promotions[0]),
        "queue_item": dict(queue_items[0]),
        "worker_claim": dict(claims[0]),
    }


def architect_fix_committed_publication_reasons(
    snapshot: Mapping[str, Any],
    authority_profile: Mapping[str, Any],
    *,
    queue_item_id: str,
    claim_id: str,
) -> tuple[str, ...]:
    """Reject architect-FIX effects unless current publication is COMMITTED."""

    marker = str(authority_profile.get("promotion_publication_id") or "")
    all_promotions, promotions = _matching_promotions(
        snapshot,
        marker=marker,
        queue_item_id=queue_item_id,
        claim_id=claim_id,
    )
    if not marker and not promotions:
        return (
            ("architect_fix_profile_origin_ambiguous",)
            if all_promotions
            else ()
        )
    if len(promotions) != 1 or marker != promotions[0].get("publication_id"):
        return ("architect_fix_promotion_binding_invalid",)
    publications = _exact_records(
        snapshot.get("architect_fix_publications"),
        "publication_id",
        marker,
    )
    profile_digest = canonical_digest(authority_profile)
    if (
        len(publications) != 1
        or not _committed_publication_binding_matches(
            publications[0],
            promotions[0],
            authority_profile,
            profile_digest,
        )
    ):
        return ("architect_fix_publication_not_committed",)
    try:
        validate_committed_snapshot(snapshot, publications[0])
    except RuntimeError:
        return ("architect_fix_publication_state_mismatch",)
    return ()


def _matching_promotions(
    snapshot: Mapping[str, Any],
    *,
    marker: str,
    queue_item_id: str,
    claim_id: str,
) -> tuple[list[Mapping[str, Any]], list[Mapping[str, Any]]]:
    all_promotions = [
        item
        for item in snapshot.get("architect_fix_promotions") or ()
        if isinstance(item, Mapping)
    ]
    matching = [
        item
        for item in all_promotions
        if str(item.get("publication_id") or "") == marker
        or (
            str(item.get("queue_item_id") or "") == queue_item_id
            and str(item.get("claim_id") or "") == claim_id
        )
    ]
    return all_promotions, matching


def _committed_publication_binding_matches(
    publication: Mapping[str, Any],
    promotion: Mapping[str, Any],
    profile: Mapping[str, Any],
    profile_digest: str,
) -> bool:
    attestation_id = profile.get("proposal_authenticity_attestation_id")
    return (
        set(publication) == _PUBLICATION_RECORD_FIELDS
        and publication.get("schema_version") == PUBLICATION_SCHEMA_VERSION
        and publication.get("state") == PUBLICATION_COMMITTED
        and publication.get("base_work_state_digest") is None
        and is_sha256(publication.get("publication_id"))
        and is_sha256(publication.get("active_work_state_digest"))
        and publication.get("authority_profile_digest") == profile_digest
        and promotion.get("authority_profile_digest") == profile_digest
        and publication.get("proposal_authenticity_attestation_id")
        == attestation_id
        and promotion.get("proposal_authenticity_attestation_id")
        == attestation_id
    )


def _exact_records(
    values: Any,
    field: str,
    expected: str,
) -> list[Mapping[str, Any]]:
    return [
        item
        for item in values or ()
        if isinstance(item, Mapping)
        and str(item.get(field) or "") == expected
    ]


def is_sha256(value: Any) -> bool:
    text = str(value or "")
    return len(text) == 71 and text.startswith("sha256:") and all(
        char in "0123456789abcdef" for char in text[7:]
    )


def is_revision(value: Any) -> bool:
    text = str(value or "")
    return len(text) == 64 and all(
        char in "0123456789abcdef" for char in text
    )


def is_optional_revision(value: Any) -> bool:
    return value is None or is_revision(value)


def journal_revisions_match_phase(
    journal: Mapping[str, Any],
    *,
    phase: Any,
) -> bool:
    prepared = journal.get("prepared_revision")
    committed = journal.get("committed_revision")
    if phase == PUBLICATION_INTENT_PREPARED:
        return prepared is None and committed is None
    if phase in {PUBLICATION_STATE_PREPARED, PUBLICATION_PROFILE_PUBLISHED}:
        return is_revision(prepared) and committed is None
    if phase == PUBLICATION_COMMITTED:
        return is_revision(prepared) and is_revision(committed)
    return False


def is_attestation_id(value: Any) -> bool:
    text = str(value or "")
    prefix = "reddog_architect_proposal_attestation_"
    suffix = text.removeprefix(prefix)
    return (
        text.startswith(prefix)
        and len(suffix) == 32
        and all(char in "0123456789abcdef" for char in suffix)
    )


def without_revision(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    payload = json.loads(json.dumps(snapshot, sort_keys=True))
    payload.pop("revision", None)
    return payload


__all__ = [
    "architect_fix_committed_publication_reasons",
    "architect_fix_publication_state_projection",
    "is_attestation_id",
    "is_optional_revision",
    "is_sha256",
    "publication_binding",
    "publication_record",
    "PUBLICATION_COMMITTED",
    "PUBLICATION_INTENT_PREPARED",
    "PUBLICATION_PROFILE_PUBLISHED",
    "PUBLICATION_SCHEMA_VERSION",
    "PUBLICATION_STATE_PREPARED",
    "STAGED_PROFILE_SCHEMA_VERSION",
    "validate_committed_snapshot",
    "validate_journal",
    "validate_journal_record_binding",
    "validate_prepared_snapshot",
    "validate_publication_record",
    "validate_stage",
    "validate_stage_journal_binding",
    "without_revision",
]
