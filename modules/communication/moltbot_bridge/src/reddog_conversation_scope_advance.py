"""CAS update operation for authenticated RedDog conversation scope."""

from __future__ import annotations

from typing import Any, Mapping

from modules.communication.moltbot_bridge.src.reddog_conversation_scope_capability import (
    AuthenticatedConversationScopeCapability,
    consume_conversation_scope_capability,
    conversation_scope_authority_view,
    sign_record_with_scope_authority,
    verify_record_with_scope_authority,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_scope_contract import (
    with_record_digest,
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
    updated["record_auth_mac"] = sign_record_with_scope_authority(authority, updated)
    return stored_result(
        store.compare_and_swap(
            request.conversation_id,
            expected_revision=int(request.expected_revision),
            next_record=with_record_digest(updated),
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
    grounded, reason = verified_grounding(
        repo_root, request.work_focus, request.grounding_receipt
    )
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
    )
    authority_view = conversation_scope_authority_view(authority)
    if (
        reason
        or str(grounded.get("foundup_id") or "") != str(current["authorized_foundup_id"])
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
        allowed_evidence_refs=grounding_evidence_refs(grounded),
    )
    updated = dict(current)
    updated.update(state)
    updated.update(
        {
            "conversation_revision": int(request.expected_revision) + 1,
            "last_grounded_head_sha": str(grounded["holoindex_repo_head_sha"]),
            "holoindex_generation_id": str(grounded.get("holoindex_generation_id") or ""),
            "holoindex_freshness_receipt_id": str(
                grounded.get("holoindex_freshness_receipt_digest") or ""
            ),
            "grounding_receipt_id": str(grounded["receipt_id"]),
            "pending_work_proposal_id": "",
            "pending_work_proposal_digest": "",
            "updated_at": int(now_epoch),
        }
    )
    previous = str(current["revision_receipts"][-1]["receipt_id"])
    updated["revision_receipts"] = [
        *current["revision_receipts"],
        revision_receipt(
            updated, previous=previous, revision=int(request.expected_revision) + 1
        ),
    ]
    return updated


__all__ = ["advance_authenticated_conversation_scope"]
