"""Grounded record helpers for RedDog authenticated conversation scope."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from modules.communication.moltbot_bridge.src.reddog_conversation_scope_contract import (
    REVISION_RECEIPT_SCHEMA,
    SHA256_RE,
    canonical_digest,
    sanitized_text,
    string_list,
    typed_items,
)
from modules.communication.moltbot_bridge.src.reddog_grounded_target_assignment_continuity import (
    validate_grounded_target_receipt,
)
from modules.communication.moltbot_bridge.src.reddog_registered_foundup_target_verifier import (
    verify_registered_foundup_target,
)


@dataclass(frozen=True)
class AuthenticatedConversationScopeResult:
    accepted: bool
    status: str
    conversation_id: str = ""
    conversation_revision: int = -1
    revision_receipt_id: str = ""
    projection: Mapping[str, Any] | None = None
    rejection_reasons: tuple[str, ...] = ()
    no_work_authority_granted: bool = True
    no_worker_dispatch_performed: bool = True
    no_repo_mutation_performed: bool = True
    no_holoindex_reindex_performed: bool = True


def verified_grounding(
    repo_root: Any, work_focus: str, receipt: Mapping[str, Any]
) -> tuple[Mapping[str, Any], str]:
    result = validate_grounded_target_receipt(
        receipt, work_focus=work_focus, expected_source_surface="editor_thin_client"
    )
    if not result.accepted or result.verified is None:
        return {}, (result.rejection_reasons or ("conversation_scope_grounding_invalid",))[0]
    value = result.verified.to_dict()
    target = value.get("registered_foundup_target")
    selection = {
        "foundup_id": value.get("foundup_id"),
        "registered_foundup_target_receipt_id": value.get("registered_foundup_target_receipt_id"),
    }
    reasons = verify_registered_foundup_target(
        repo_root, target, selection_receipt=selection
    )
    if reasons or not str(value.get("foundup_id") or ""):
        return {}, reasons[0] if reasons else "conversation_scope_foundup_missing"
    return value, ""


def state_values(**values: Any) -> dict[str, Any]:
    turn_id = sanitized_text(values["turn_id"], limit=160)
    parent_turn_id = sanitized_text(values["parent_turn_id"], limit=160)
    if not SHA256_RE.fullmatch(turn_id) or (
        parent_turn_id and not SHA256_RE.fullmatch(parent_turn_id)
    ):
        raise ValueError("conversation_scope_turn_lineage_invalid")
    state = {
        "turn_id": turn_id,
        "parent_turn_id": parent_turn_id,
        "discussion_foundup_ids": string_list(values["discussions"], maximum=16),
        "active_topic": sanitized_text(values["active_topic"]),
        "current_objective": sanitized_text(values["current_objective"]),
        "accepted_decisions": typed_items(values["accepted_decisions"]),
        "rejected_options": typed_items(values["rejected_options"]),
        "open_questions": typed_items(values["open_questions"]),
        "repository_evidence_refs": string_list(
            values["repository_evidence_refs"], maximum=64
        ),
    }
    if not _evidence_is_grounded(state, values["allowed_evidence_refs"]):
        raise ValueError("conversation_scope_evidence_not_grounded")
    return state


def grounding_evidence_refs(grounded: Mapping[str, Any]) -> tuple[str, ...]:
    refs: list[str] = []
    for item in grounded.get("semantic_target_coverage", ()):
        if isinstance(item, Mapping):
            refs.extend(str(ref) for ref in item.get("evidence_refs", ()))
    refs.extend(str(path) for path in grounded.get("direct_read_paths", ()))
    target = grounded.get("registered_foundup_target")
    if isinstance(target, Mapping):
        refs.extend(
            str(item.get("path") or "")
            for item in target.get("evidence_digests", ())
            if isinstance(item, Mapping)
        )
    return tuple(dict.fromkeys(ref for ref in refs if ref))


def _evidence_is_grounded(state: Mapping[str, Any], allowed: Any) -> bool:
    approved = set(str(item) for item in allowed)
    supplied = set(str(item) for item in state["repository_evidence_refs"])
    for field in ("accepted_decisions", "rejected_options", "open_questions"):
        for item in state[field]:
            supplied.update(str(ref) for ref in item["evidence_refs"])
    return all(ref in approved or _evidence_anchor(ref) in approved for ref in supplied)


def _evidence_anchor(reference: str) -> str:
    base, separator, suffix = reference.rpartition(":")
    return base if separator and suffix.isdigit() else reference


def revision_receipt(
    record: Mapping[str, Any], *, previous: str, revision: int
) -> dict[str, Any]:
    state = {
        key: value
        for key, value in record.items()
        if key not in {"revision_receipts", "record_auth_mac", "record_digest"}
    }
    payload = {
        "schema_version": REVISION_RECEIPT_SCHEMA,
        "conversation_id": record["conversation_id"],
        "revision": revision,
        "previous_receipt_id": previous,
        "state_digest": canonical_digest(state),
        "authority": "authenticated_scope_integrity_not_work_authority",
    }
    return {**payload, "receipt_id": canonical_digest(payload)}


def authority_matches(
    record: Mapping[str, Any], authority: Mapping[str, Any]
) -> bool:
    return all(
        record.get(field) == authority.get(field)
        for field in (
            "principal_id", "principal_provider", "verified_subject_digest",
            "principal_record_digest", "principal_key_fingerprint", "transport",
            "session_binding_digest",
        )
    )


def stored_result(result: Mapping[str, Any]) -> AuthenticatedConversationScopeResult:
    record = result.get("record")
    if not result.get("ok") or not isinstance(record, Mapping):
        return rejected(str(result.get("reason") or "conversation_scope_store_rejected"))
    return accepted(record)


def accepted(record: Mapping[str, Any]) -> AuthenticatedConversationScopeResult:
    receipt = record["revision_receipts"][-1]
    projection = {
        key: record[key]
        for key in (
            "conversation_id", "conversation_revision", "turn_id", "parent_turn_id",
            "authorized_foundup_id", "discussion_foundup_ids", "active_topic",
            "current_objective", "accepted_decisions", "rejected_options", "open_questions",
            "repository_evidence_refs", "last_grounded_head_sha", "holoindex_generation_id",
            "holoindex_freshness_receipt_id", "grounding_receipt_id",
            "source_snapshot_id", "source_snapshot_digest",
            "pending_work_proposal_id", "pending_work_proposal_digest", "updated_at",
            "expires_at", "record_digest",
        )
    }
    projection.update(
        {
            "schema_version": "reddog_authenticated_conversation_projection.v1",
            "authority_effect": "none",
            "revision_receipt_id": receipt["receipt_id"],
        }
    )
    return AuthenticatedConversationScopeResult(
        True,
        "CONVERSATION_SCOPE_ACCEPT",
        str(record["conversation_id"]),
        int(record["conversation_revision"]),
        str(receipt["receipt_id"]),
        projection,
        (),
    )


def rejected(reason: str) -> AuthenticatedConversationScopeResult:
    return AuthenticatedConversationScopeResult(
        False, "CONVERSATION_SCOPE_REJECT", rejection_reasons=(reason,)
    )


__all__ = [
    "AuthenticatedConversationScopeResult", "accepted", "authority_matches", "rejected",
    "grounding_evidence_refs", "revision_receipt", "state_values", "stored_result",
    "verified_grounding",
]
