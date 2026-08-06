"""Authenticated create, resume, and CAS-update operations for RedDog scope."""

from __future__ import annotations

from typing import Any, Mapping

from modules.communication.moltbot_bridge.src.reddog_conversation_scope_capability import (
    AuthenticatedConversationScopeCapability,
    consume_conversation_scope_capability,
    conversation_scope_authority_view,
    verify_record_with_scope_authority,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_scope_advance import (
    advance_authenticated_conversation_scope,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_scope_contract import (
    SCHEMA_VERSION,
    canonical_digest,
    sanitized_text,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_scope_record import (
    AuthenticatedConversationScopeResult,
    accepted,
    authority_matches,
    grounding_evidence_refs,
    rejected,
    revision_receipt,
    state_values,
    stored_result,
    verified_grounding,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_scope_store import (
    AgentDbConversationScopeStore,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_scope_persistence import (
    persist_authenticated_conversation_record,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_scope_request import (
    ConversationScopeCreateRequest,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_scope_kind import (
    SCOPE_KIND_FOUNDUP,
    SCOPE_KINDS,
)


MAX_SCOPE_TTL_SECONDS = 86400


def create_authenticated_conversation_scope(
    *,
    store: AgentDbConversationScopeStore,
    capability: AuthenticatedConversationScopeCapability,
    repo_root: Any,
    request: ConversationScopeCreateRequest,
    now_epoch: int,
) -> AuthenticatedConversationScopeResult:
    scope_kind = str(request.scope_kind or "").strip()
    if scope_kind not in SCOPE_KINDS:
        return rejected("conversation_scope_kind_invalid")
    if scope_kind == SCOPE_KIND_FOUNDUP:
        grounded, reason = verified_grounding(
            repo_root, request.work_focus, request.grounding_receipt
        )
        if reason:
            return rejected(reason)
    else:
        grounded = {}
        if _nonfoundup_grounding_present(request):
            return rejected("conversation_scope_nonfoundup_grounding_forbidden")
    foundup_id = str(grounded.get("foundup_id") or "")
    raw_discussions = request.discussion_foundup_ids
    if any(type(item) is not str or not item for item in raw_discussions):
        return rejected("conversation_scope_discussion_set_invalid")
    discussions = tuple(dict.fromkeys(raw_discussions))
    if len(discussions) != len(raw_discussions):
        return rejected("conversation_scope_discussion_set_invalid")
    authority = consume_conversation_scope_capability(
        capability,
        active_foundup_id=foundup_id,
        discussion_foundup_ids=discussions,
        now_epoch=now_epoch,
        scope_kind=scope_kind,
    )
    authority_view = conversation_scope_authority_view(authority)
    if authority is None or authority_view is None:
        return rejected("conversation_scope_access_denied")
    try:
        record = _new_scope_record(
            request, grounded, authority_view, discussions, now_epoch,
            scope_kind=scope_kind,
        )
    except (TypeError, ValueError):
        return rejected("conversation_scope_input_invalid")
    record["record_auth_nonce"] = _record_auth_nonce(record)
    record["revision_receipts"] = [revision_receipt(record, previous="", revision=0)]
    return stored_result(
        persist_authenticated_conversation_record(
            store=store, authority=authority, record=record, expected_revision=-1
        )
    )


def _new_scope_record(
    request: ConversationScopeCreateRequest, grounded: Mapping[str, Any], authority_view: Mapping[str, Any],
    discussions: tuple[str, ...], now_epoch: int, *, scope_kind: str,
) -> dict[str, Any]:
    state = state_values(
        turn_id=request.turn_id, parent_turn_id="", discussions=discussions,
        active_topic=request.active_topic, current_objective=request.current_objective,
        accepted_decisions=request.accepted_decisions,
        rejected_options=request.rejected_options, open_questions=request.open_questions,
        repository_evidence_refs=request.repository_evidence_refs,
        allowed_evidence_refs=(
            grounding_evidence_refs(grounded)
            if scope_kind == SCOPE_KIND_FOUNDUP
            else ()
        ),
    )
    ttl = int(request.ttl_seconds)
    nonce = sanitized_text(request.conversation_nonce, limit=160)
    if ttl <= 0 or ttl > MAX_SCOPE_TTL_SECONDS or not nonce:
        raise ValueError("conversation_scope_ttl_or_nonce_invalid")
    foundup_id = str(grounded.get("foundup_id") or "")
    conversation_id = _conversation_id(
        authority_view, scope_kind, foundup_id, discussions, nonce
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "conversation_id": conversation_id,
        "scope_kind": scope_kind,
        **{key: authority_view[key] for key in (
            "principal_id", "principal_provider", "verified_subject_digest",
            "principal_record_digest", "principal_key_fingerprint", "transport",
            "session_binding_digest",
        )},
        "credential_id": str(authority_view.get("credential_id") or ""),
        "session_id": str(authority_view.get("session_id") or ""),
        "repo_full_name": str(authority_view.get("repo_full_name") or ""),
        "authorized_foundup_id": foundup_id,
        "conversation_revision": 0,
        **state,
        "source_snapshot_id": str(request.source_snapshot_id or ""),
        "source_snapshot_digest": str(request.source_snapshot_digest or ""),
        "last_grounded_head_sha": str(grounded.get("holoindex_repo_head_sha") or ""),
        "holoindex_generation_id": str(grounded.get("holoindex_generation_id") or ""),
        "holoindex_freshness_receipt_id": str(grounded.get("holoindex_freshness_receipt_digest") or ""),
        "grounding_receipt_id": str(grounded.get("receipt_id") or ""),
        "pending_work_proposal_id": "", "pending_work_proposal_digest": "",
        "created_at": int(now_epoch), "updated_at": int(now_epoch),
        "expires_at": int(now_epoch) + ttl,
        "revision_receipts": [],
        "record_auth_scheme": str(authority_view["record_auth_scheme"]),
        "record_auth_signature": "",
        "record_auth_signer_public_key": "",
        "record_auth_key_fingerprint": "",
        "record_auth_key_epoch": "",
        "record_auth_nonce": "",
        "record_auth_audit_mac": "",
        "record_auth_audit_attestation_signature": "",
        "previous_record_auth_signature_digest": "",
        "record_digest": "",
    }


def _conversation_id(
    authority: Mapping[str, Any], scope_kind: str, foundup_id: str,
    discussions: tuple[str, ...], nonce: str,
) -> str:
    return canonical_digest(
        {
            "principal_id": authority["principal_id"],
            "scope_kind": scope_kind,
            "foundup_id": foundup_id,
            "discussion_foundup_ids": list(discussions),
            "session_binding_digest": authority["session_binding_digest"],
            "conversation_nonce": nonce,
        }
    )


def _nonfoundup_grounding_present(request: ConversationScopeCreateRequest) -> bool:
    return bool(
        request.grounding_receipt
        or request.repository_evidence_refs
        or request.source_snapshot_id
        or request.source_snapshot_digest
    )


def _record_auth_nonce(record: Mapping[str, Any]) -> str:
    return canonical_digest(
        {
            "conversation_id": record["conversation_id"],
            "conversation_revision": record["conversation_revision"],
            "turn_id": record["turn_id"],
            "updated_at": record["updated_at"],
            "previous_record_auth_signature_digest": record[
                "previous_record_auth_signature_digest"
            ],
        }
    )


def resume_authenticated_conversation_scope(
    *,
    store: AgentDbConversationScopeStore,
    capability: AuthenticatedConversationScopeCapability,
    conversation_id: str,
    expected_head_sha: str,
    expected_holoindex_generation_id: str,
    expected_source_snapshot_id: str,
    expected_source_snapshot_digest: str,
    now_epoch: int,
) -> AuthenticatedConversationScopeResult:
    loaded = store.load(conversation_id)
    record = loaded.get("record") if loaded.get("ok") else None
    if not isinstance(record, Mapping):
        return rejected("conversation_scope_access_denied")
    authority = consume_conversation_scope_capability(
        capability,
        active_foundup_id=str(record["authorized_foundup_id"]),
        discussion_foundup_ids=tuple(str(item) for item in record["discussion_foundup_ids"]),
        now_epoch=now_epoch,
        scope_kind=str(record.get("scope_kind") or ""),
    )
    authority_view = conversation_scope_authority_view(authority)
    if (
        authority is None
        or authority_view is None
        or not authority_matches(record, authority_view)
        or not verify_record_with_scope_authority(authority, record)
    ):
        return rejected("conversation_scope_access_denied")
    if int(now_epoch) >= int(record["expires_at"]):
        return rejected("conversation_scope_expired")
    if not _resume_bindings_match(
        record,
        expected_head_sha=expected_head_sha,
        expected_holoindex_generation_id=expected_holoindex_generation_id,
        expected_source_snapshot_id=expected_source_snapshot_id,
        expected_source_snapshot_digest=expected_source_snapshot_digest,
    ):
        return rejected("conversation_scope_regrounding_required")
    return accepted(record)


def _resume_bindings_match(
    record: Mapping[str, Any],
    *,
    expected_head_sha: str,
    expected_holoindex_generation_id: str,
    expected_source_snapshot_id: str,
    expected_source_snapshot_digest: str,
) -> bool:
    expected = (
        str(expected_head_sha),
        str(expected_holoindex_generation_id),
        str(expected_source_snapshot_id),
        str(expected_source_snapshot_digest),
    )
    actual = (
        str(record["last_grounded_head_sha"]),
        str(record["holoindex_generation_id"]),
        str(record["source_snapshot_id"]),
        str(record["source_snapshot_digest"]),
    )
    if record.get("scope_kind") == SCOPE_KIND_FOUNDUP:
        return actual == expected
    return actual == ("", "", "", "") and expected == ("", "", "", "")


__all__ = [
    "AuthenticatedConversationScopeResult", "advance_authenticated_conversation_scope",
    "create_authenticated_conversation_scope", "resume_authenticated_conversation_scope",
]
