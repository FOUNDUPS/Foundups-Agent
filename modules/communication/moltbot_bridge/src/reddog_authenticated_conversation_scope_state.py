"""Authenticated create, resume, and CAS-update operations for RedDog scope."""

from __future__ import annotations

from dataclasses import replace
from typing import Any, Mapping

from modules.communication.moltbot_bridge.src.reddog_conversation_scope_capability import (
    AuthenticatedConversationScopeCapability,
    VerifiedConversationScopeAuthority,
    consume_conversation_scope_capability,
    consume_verified_scope_authority_for_scope_creation,
    conversation_scope_authority_view,
    discard_conversation_scope_capability,
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
from modules.communication.moltbot_bridge.src.reddog_conversation_scope_signing import (
    unsigned_conversation_scope_record,
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
    grounded, discussions, scope_kind, reason = _scope_creation_inputs(
        repo_root, request
    )
    if reason:
        return rejected(reason)
    foundup_id = str(grounded.get("foundup_id") or "")
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
        result, _record = _persist_new_scope(
            store, authority, request, grounded, authority_view, discussions,
            now_epoch, scope_kind,
        )
        return result
    finally:
        discard_conversation_scope_capability(authority)


def create_authenticated_conversation_scope_from_verified_authority(
    *, store: AgentDbConversationScopeStore,
    authority: VerifiedConversationScopeAuthority, repo_root: Any,
    request: ConversationScopeCreateRequest, now_epoch: int,
    record_epoch: int, minimum_expires_at: int,
) -> AuthenticatedConversationScopeResult:
    """Consume one exact resident authority to create or recover one scope."""
    if (
        type(record_epoch) is not int or record_epoch < 0
        or type(minimum_expires_at) is not int
        or minimum_expires_at <= record_epoch
    ):
        discard_conversation_scope_capability(authority)
        return rejected("conversation_scope_input_invalid")
    grounded, discussions, scope_kind, reason = _scope_creation_inputs(
        repo_root, request
    )
    if reason:
        discard_conversation_scope_capability(authority)
        return rejected(reason)
    foundup_id = str(grounded.get("foundup_id") or "")
    claimed = consume_verified_scope_authority_for_scope_creation(
        authority, active_foundup_id=foundup_id,
        discussion_foundup_ids=discussions, scope_kind=scope_kind,
        now_epoch=now_epoch,
    )
    view = conversation_scope_authority_view(claimed)
    if claimed is None or view is None:
        return rejected("conversation_scope_access_denied")
    if int(view["expires_at"]) < minimum_expires_at:
        discard_conversation_scope_capability(claimed)
        return rejected("conversation_scope_expired")
    bounded_request = _authority_bound_scope_request(request, view, record_epoch)
    if (
        bounded_request is None
        or record_epoch + int(bounded_request.ttl_seconds) < minimum_expires_at
    ):
        discard_conversation_scope_capability(claimed)
        return rejected("conversation_scope_expired")
    session_identity = str(view.get("session_id") or "")
    try:
        result, expected = _persist_new_scope(
            store, claimed, bounded_request, grounded, view, discussions,
            record_epoch, scope_kind, conversation_session_identity=session_identity,
        )
        if result.accepted or not _creation_conflict(result):
            return result
        return _recover_exact_new_scope(store, claimed, view, expected, now_epoch)
    finally:
        discard_conversation_scope_capability(claimed)


def _authority_bound_scope_request(
    request: ConversationScopeCreateRequest, authority: Mapping[str, Any],
    record_epoch: int,
) -> ConversationScopeCreateRequest | None:
    try:
        ttl = min(int(request.ttl_seconds), int(authority["expires_at"]) - record_epoch)
        return replace(request, ttl_seconds=ttl) if ttl > 0 else None
    except Exception:
        return None


def _scope_creation_inputs(
    repo_root: Any, request: ConversationScopeCreateRequest,
) -> tuple[Mapping[str, Any], tuple[str, ...], str, str]:
    try:
        if type(request) is not ConversationScopeCreateRequest:
            return {}, (), "", "conversation_scope_input_invalid"
        scope_kind = str(request.scope_kind or "").strip()
        if scope_kind not in SCOPE_KINDS:
            return {}, (), "", "conversation_scope_kind_invalid"
        grounded: Mapping[str, Any] = {}
        if scope_kind == SCOPE_KIND_FOUNDUP:
            grounded, reason = verified_grounding(
                repo_root, request.work_focus, request.grounding_receipt
            )
            if reason:
                return {}, (), "", reason
        elif _nonfoundup_grounding_present(request):
            return {}, (), "", "conversation_scope_nonfoundup_grounding_forbidden"
        raw = request.discussion_foundup_ids
        if any(type(item) is not str or not item for item in raw):
            return {}, (), "", "conversation_scope_discussion_set_invalid"
        discussions = tuple(dict.fromkeys(raw))
        if len(discussions) != len(raw):
            return {}, (), "", "conversation_scope_discussion_set_invalid"
        return grounded, discussions, scope_kind, ""
    except Exception:
        return {}, (), "", "conversation_scope_input_invalid"


def _persist_new_scope(
    store: AgentDbConversationScopeStore, authority: Any,
    request: ConversationScopeCreateRequest, grounded: Mapping[str, Any],
    authority_view: Mapping[str, Any], discussions: tuple[str, ...],
    now_epoch: int, scope_kind: str, *, conversation_session_identity: str = "",
) -> tuple[AuthenticatedConversationScopeResult, Mapping[str, Any]]:
    try:
        record = _new_scope_record(
            request, grounded, authority_view, discussions, now_epoch,
            scope_kind=scope_kind,
            conversation_session_identity=conversation_session_identity,
        )
        record["record_auth_nonce"] = _record_auth_nonce(record)
        record["revision_receipts"] = [
            revision_receipt(record, previous="", revision=0)
        ]
    except (TypeError, ValueError):
        return rejected("conversation_scope_input_invalid"), {}
    stored = persist_authenticated_conversation_record(
        store=store, authority=authority, record=record, expected_revision=-1
    )
    return stored_result(stored), record


def _creation_conflict(result: AuthenticatedConversationScopeResult) -> bool:
    return bool(
        result.rejection_reasons
        and result.rejection_reasons[0]
        in {"conversation_scope_exists", "conversation_scope_revision_conflict"}
    )


def _recover_exact_new_scope(
    store: AgentDbConversationScopeStore, authority: Any,
    authority_view: Mapping[str, Any], expected: Mapping[str, Any], now_epoch: int,
) -> AuthenticatedConversationScopeResult:
    try:
        loaded = store.load(str(expected["conversation_id"]))
        record = loaded.get("record") if loaded.get("ok") else None
        valid = bool(
            isinstance(record, Mapping)
            and int(now_epoch) < int(record["expires_at"])
            and unsigned_conversation_scope_record(record)
            == unsigned_conversation_scope_record(expected)
            and authority_matches(record, authority_view)
            and verify_record_with_scope_authority(authority, record)
        )
    except Exception:
        valid, record = False, None
    return accepted(record) if valid and isinstance(record, Mapping) else rejected(
        "conversation_scope_creation_conflict"
    )


def _new_scope_record(
    request: ConversationScopeCreateRequest, grounded: Mapping[str, Any], authority_view: Mapping[str, Any],
    discussions: tuple[str, ...], now_epoch: int, *, scope_kind: str, conversation_session_identity: str = "",
) -> dict[str, Any]:
    state = _initial_scope_state(request, grounded, discussions, scope_kind)
    ttl = int(request.ttl_seconds)
    nonce = sanitized_text(request.conversation_nonce, limit=160)
    if ttl <= 0 or ttl > MAX_SCOPE_TTL_SECONDS or not nonce:
        raise ValueError("conversation_scope_ttl_or_nonce_invalid")
    foundup_id = str(grounded.get("foundup_id") or "")
    conversation_id = _conversation_id(
        authority_view, scope_kind, foundup_id, discussions, nonce,
        conversation_session_identity=conversation_session_identity,
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


def _initial_scope_state(
    request: ConversationScopeCreateRequest, grounded: Mapping[str, Any],
    discussions: tuple[str, ...], scope_kind: str,
) -> dict[str, Any]:
    return state_values(
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


def _conversation_id(
    authority: Mapping[str, Any], scope_kind: str, foundup_id: str,
    discussions: tuple[str, ...], nonce: str, *, conversation_session_identity: str,
) -> str:
    return canonical_digest(
        {
            "principal_id": authority["principal_id"],
            "scope_kind": scope_kind,
            "foundup_id": foundup_id,
            "discussion_foundup_ids": list(discussions),
            "session_binding_digest": (
                conversation_session_identity or authority["session_binding_digest"]
            ),
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
    "create_authenticated_conversation_scope",
    "create_authenticated_conversation_scope_from_verified_authority",
    "resume_authenticated_conversation_scope",
]
