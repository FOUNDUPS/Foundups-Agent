"""CAS update operation for authenticated RedDog conversation scope."""

from __future__ import annotations

from typing import Any, Mapping

from modules.communication.moltbot_bridge.src.reddog_conversation_scope_capability import (
    AuthenticatedConversationScopeCapability,
    consume_conversation_scope_capability,
    conversation_scope_authority_view,
    verify_record_with_scope_authority,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_scope_contract import (
    canonical_digest,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_scope_record import (
    AuthenticatedConversationScopeResult,
    authority_matches,
    grounding_evidence_refs,
    rejected,
    revision_receipt,
    state_values,
    stored_result,
    verified_grounding,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_scope_request import (
    ConversationScopeAdvanceRequest,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_scope_store import (
    AgentDbConversationScopeStore,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_scope_persistence import (
    persist_authenticated_conversation_record,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_scope_kind import (
    SCOPE_KIND_FOUNDUP,
)


def advance_authenticated_conversation_scope(
    *,
    store: AgentDbConversationScopeStore,
    capability: AuthenticatedConversationScopeCapability,
    repo_root: Any,
    request: ConversationScopeAdvanceRequest,
    now_epoch: int,
) -> AuthenticatedConversationScopeResult:
    current, grounded, authority, reason = _authorized_current(
        store, capability, repo_root, request, now_epoch
    )
    if reason:
        return rejected(reason)
    try:
        updated = _updated_record(current, grounded, request, now_epoch)
    except (KeyError, TypeError, ValueError):
        return rejected("conversation_scope_input_invalid")
    updated["previous_record_auth_signature_digest"] = canonical_digest(
        {"record_auth_signature": current["record_auth_signature"]}
    )
    updated["record_auth_nonce"] = _record_auth_nonce(updated)
    updated["revision_receipts"] = [
        *current["revision_receipts"],
        revision_receipt(
            updated,
            previous=str(current["revision_receipts"][-1]["receipt_id"]),
            revision=int(request.expected_revision) + 1,
        ),
    ]
    return stored_result(
        persist_authenticated_conversation_record(
            store=store,
            authority=authority,
            record=updated,
            expected_revision=int(request.expected_revision),
        )
    )


def _authorized_current(
    store: AgentDbConversationScopeStore,
    capability: AuthenticatedConversationScopeCapability,
    repo_root: Any,
    request: ConversationScopeAdvanceRequest,
    now_epoch: int,
) -> tuple[Mapping[str, Any], Mapping[str, Any], Any, str]:
    loaded = store.load(request.conversation_id)
    current = loaded.get("record") if loaded.get("ok") else None
    if not isinstance(current, Mapping):
        return {}, {}, None, "conversation_scope_access_denied"
    scope_kind = str(current.get("scope_kind") or "")
    if scope_kind == SCOPE_KIND_FOUNDUP:
        grounded, reason = verified_grounding(
            repo_root, request.work_focus, request.grounding_receipt
        )
    else:
        grounded, reason = {}, ""
        if _nonfoundup_grounding_present(request):
            reason = "conversation_scope_nonfoundup_grounding_forbidden"
    discussions = tuple(
        str(item)
        for item in request.state_patch.get(
            "discussion_foundup_ids", current["discussion_foundup_ids"]
        )
    )
    authority = consume_conversation_scope_capability(
        capability,
        active_foundup_id=str(grounded.get("foundup_id") or "") if not reason else "",
        discussion_foundup_ids=discussions,
        now_epoch=now_epoch,
        scope_kind=scope_kind,
    )
    authority_view = conversation_scope_authority_view(authority)
    if (
        reason
        or (
            scope_kind == SCOPE_KIND_FOUNDUP
            and str(grounded.get("foundup_id") or "")
            != str(current["authorized_foundup_id"])
        )
        or str(current["source_snapshot_id"]) != request.expected_source_snapshot_id
        or str(current["source_snapshot_digest"]) != request.expected_source_snapshot_digest
        or authority is None
        or authority_view is None
        or not authority_matches(current, authority_view)
        or not verify_record_with_scope_authority(authority, current)
    ):
        return {}, {}, None, reason or "conversation_scope_access_denied"
    if int(now_epoch) >= int(current["expires_at"]):
        return {}, {}, None, "conversation_scope_expired"
    if int(current["conversation_revision"]) != int(request.expected_revision):
        return {}, {}, None, "conversation_scope_revision_conflict"
    return current, grounded, authority, ""


def _updated_record(
    current: Mapping[str, Any],
    grounded: Mapping[str, Any],
    request: ConversationScopeAdvanceRequest,
    now_epoch: int,
) -> dict[str, Any]:
    if "scope_kind" in request.state_patch or "authorized_foundup_id" in request.state_patch:
        raise ValueError("conversation_scope_kind_change_forbidden")
    if str(request.state_patch["parent_turn_id"]) != str(current["turn_id"]):
        raise ValueError("conversation_scope_parent_turn_mismatch")
    state = state_values(
        turn_id=request.state_patch["turn_id"],
        parent_turn_id=request.state_patch["parent_turn_id"],
        discussions=request.state_patch.get("discussion_foundup_ids", current["discussion_foundup_ids"]),
        active_topic=request.state_patch["active_topic"],
        current_objective=request.state_patch["current_objective"],
        accepted_decisions=request.state_patch.get("accepted_decisions", ()),
        rejected_options=request.state_patch.get("rejected_options", ()),
        open_questions=request.state_patch.get("open_questions", ()),
        repository_evidence_refs=request.state_patch.get("repository_evidence_refs", ()),
        allowed_evidence_refs=(
            grounding_evidence_refs(grounded)
            if current.get("scope_kind") == SCOPE_KIND_FOUNDUP
            else ()
        ),
    )
    updated = dict(current)
    updated.update(state)
    updated.update(
        {
            "conversation_revision": int(request.expected_revision) + 1,
            "last_grounded_head_sha": str(
                grounded.get("holoindex_repo_head_sha")
                or current.get("last_grounded_head_sha")
                or ""
            ),
            "holoindex_generation_id": str(grounded.get("holoindex_generation_id") or ""),
            "holoindex_freshness_receipt_id": str(
                grounded.get("holoindex_freshness_receipt_digest") or ""
            ),
            "grounding_receipt_id": str(
                grounded.get("receipt_id") or current.get("grounding_receipt_id") or ""
            ),
            "pending_work_proposal_id": "",
            "pending_work_proposal_digest": "",
            "updated_at": int(now_epoch),
        }
    )
    return updated


def _nonfoundup_grounding_present(request: ConversationScopeAdvanceRequest) -> bool:
    patch = request.state_patch
    return bool(
        request.grounding_receipt
        or patch.get("repository_evidence_refs")
        or request.expected_source_snapshot_id
        or request.expected_source_snapshot_digest
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


__all__ = ["advance_authenticated_conversation_scope"]
