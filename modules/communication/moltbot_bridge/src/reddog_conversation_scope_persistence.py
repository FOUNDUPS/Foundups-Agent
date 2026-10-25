"""Scheme-aware persistence for authenticated conversation records."""

from __future__ import annotations

from typing import Any, Mapping

from modules.communication.moltbot_bridge.src.reddog_conversation_scope_capability import (
    conversation_scope_authority_view,
    sign_record_with_scope_authority,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_scope_signing import (
    CONVERSATION_SCOPE_AUTH_SCHEME,
    unsigned_conversation_scope_record,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_scope_store import (
    AgentDbConversationScopeStore,
)


LEGACY_HMAC_AUTH_SCHEME = "hmac-sha256-v1"


def persist_authenticated_conversation_record(
    *,
    store: AgentDbConversationScopeStore,
    authority: Any,
    record: Mapping[str, Any],
    expected_revision: int,
) -> Mapping[str, Any]:
    """Persist HMAC atomically or E0 through its durable signer anchor."""

    view = conversation_scope_authority_view(authority)
    scheme = str(view.get("record_auth_scheme") or "") if view else ""
    if scheme == LEGACY_HMAC_AUTH_SCHEME:
        return _persist_hmac(store, authority, record, expected_revision)
    if scheme == CONVERSATION_SCOPE_AUTH_SCHEME:
        return _persist_e0(store, authority, record, expected_revision)
    return _failure("conversation_scope_record_authentication_unavailable")


def _persist_hmac(
    store: AgentDbConversationScopeStore,
    authority: Any,
    record: Mapping[str, Any],
    expected_revision: int,
) -> Mapping[str, Any]:
    envelope = sign_record_with_scope_authority(authority, record)
    if not isinstance(envelope, Mapping):
        return _failure("conversation_scope_record_authentication_unavailable")
    signed = {**record, **envelope}
    if expected_revision == -1:
        return store.create(signed)
    return store.compare_and_swap(
        str(signed["conversation_id"]),
        expected_revision=expected_revision,
        next_record=signed,
    )


def _persist_e0(
    store: AgentDbConversationScopeStore,
    authority: Any,
    record: Mapping[str, Any],
    expected_revision: int,
) -> Mapping[str, Any]:
    transactions = store.pending_transactions()
    staged = transactions.stage(
        unsigned_conversation_scope_record(record),
        expected_revision=expected_revision,
    )
    if not staged.get("ok") or not isinstance(staged.get("record"), Mapping):
        return _failure(
            str(staged.get("reason") or "conversation_scope_pending_rejected")
        )
    signed = dict(staged["record"])
    envelope = sign_record_with_scope_authority(
        authority, signed, require_replay=bool(staged.get("recovery_only"))
    )
    if not isinstance(envelope, Mapping):
        return _failure("conversation_scope_record_authentication_unavailable")
    signed.update(envelope)
    return transactions.finalize(signed, expected_revision=expected_revision)


def _failure(reason: str) -> Mapping[str, Any]:
    return {"ok": False, "reason": reason, "record": None}


__all__ = ["LEGACY_HMAC_AUTH_SCHEME", "persist_authenticated_conversation_record"]
