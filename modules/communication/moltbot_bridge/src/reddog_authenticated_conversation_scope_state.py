"""Authenticated create, resume, and CAS-update operations for RedDog scope."""

from __future__ import annotations

from typing import Any, Mapping

from modules.communication.moltbot_bridge.src.reddog_conversation_scope_capability import (
    AuthenticatedConversationScopeCapability,
    consume_conversation_scope_capability,
    conversation_scope_authority_view,
    sign_record_with_scope_authority,
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
from modules.communication.moltbot_bridge.src.reddog_conversation_scope_signing import (
    unsigned_conversation_scope_record,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_scope_request import (
    ConversationScopeCreateRequest,
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
    grounded, reason = verified_grounding(
        repo_root, request.work_focus, request.grounding_receipt
    )
    if reason:
        return rejected(reason)
    foundup_id = str(grounded.get("foundup_id") or "")
    discussions = tuple(
        dict.fromkeys(str(item) for item in request.discussion_foundup_ids if str(item))
    )
    authority = consume_conversation_scope_capability(
        capability,
        active_foundup_id=foundup_id,
        discussion_foundup_ids=discussions,
        now_epoch=now_epoch,
    )
    authority_view = conversation_scope_authority_view(authority)
    if authority is None or authority_view is None:
        return rejected("conversation_scope_access_denied")
    try:
        record = _new_scope_record(
            request, grounded, authority_view, discussions, now_epoch
        )
    except (TypeError, ValueError):
        return rejected("conversation_scope_input_invalid")
    record["record_auth_nonce"] = _record_auth_nonce(record)
    record["revision_receipts"] = [revision_receipt(record, previous="", revision=0)]
    transactions = store.pending_transactions()
    staged = transactions.stage(
        unsigned_conversation_scope_record(record), expected_revision=-1
    )
    if not staged.get("ok") or not isinstance(staged.get("record"), Mapping):
        return rejected(str(staged.get("reason") or "conversation_scope_pending_rejected"))
    record = dict(staged["record"])
    envelope = sign_record_with_scope_authority(
        authority, record, require_replay=bool(staged.get("recovery_only"))
    )
    if not isinstance(envelope, Mapping):
        return rejected("conversation_scope_record_authentication_unavailable")
    record.update(envelope)
    return stored_result(transactions.finalize(record, expected_revision=-1))


def _new_scope_record(
    request: ConversationScopeCreateRequest, grounded: Mapping[str, Any], authority_view: Mapping[str, Any],
    discussions: tuple[str, ...], now_epoch: int,
) -> dict[str, Any]:
    state = state_values(
        turn_id=request.turn_id, parent_turn_id="", discussions=discussions,
        active_topic=request.active_topic, current_objective=request.current_objective,
        accepted_decisions=request.accepted_decisions,
        rejected_options=request.rejected_options, open_questions=request.open_questions,
        repository_evidence_refs=request.repository_evidence_refs,
        allowed_evidence_refs=grounding_evidence_refs(grounded),
    )
    ttl = int(request.ttl_seconds)
    nonce = sanitized_text(request.conversation_nonce, limit=160)
    if ttl <= 0 or ttl > MAX_SCOPE_TTL_SECONDS or not nonce:
        raise ValueError("conversation_scope_ttl_or_nonce_invalid")
    foundup_id = str(grounded.get("foundup_id") or "")
    conversation_id = _conversation_id(authority_view, foundup_id, nonce)
    return {
        "schema_version": SCHEMA_VERSION,
        "conversation_id": conversation_id,
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
        "last_grounded_head_sha": str(grounded["holoindex_repo_head_sha"]),
        "holoindex_generation_id": str(grounded.get("holoindex_generation_id") or ""),
        "holoindex_freshness_receipt_id": str(grounded.get("holoindex_freshness_receipt_digest") or ""),
        "grounding_receipt_id": str(grounded["receipt_id"]),
        "pending_work_proposal_id": "",
        "pending_work_proposal_digest": "",
        "created_at": int(now_epoch),
        "updated_at": int(now_epoch),
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


def _conversation_id(authority: Mapping[str, Any], foundup_id: str, nonce: str) -> str:
    return canonical_digest(
        {
            "principal_id": authority["principal_id"],
            "foundup_id": foundup_id,
            "session_binding_digest": authority["session_binding_digest"],
            "conversation_nonce": nonce,
        }
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
    if (
        str(record["last_grounded_head_sha"]) != str(expected_head_sha)
        or str(record["holoindex_generation_id"]) != str(expected_holoindex_generation_id)
        or str(record["source_snapshot_id"]) != str(expected_source_snapshot_id)
        or str(record["source_snapshot_digest"]) != str(expected_source_snapshot_digest)
    ):
        return rejected("conversation_scope_regrounding_required")
    return accepted(record)


__all__ = [
    "AuthenticatedConversationScopeResult", "advance_authenticated_conversation_scope",
    "create_authenticated_conversation_scope", "resume_authenticated_conversation_scope",
]
