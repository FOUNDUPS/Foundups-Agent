"""Canonical identity for one authenticated RedDog conversation scope."""

from __future__ import annotations

from typing import Sequence

from modules.communication.moltbot_bridge.src.reddog_conversation_scope_digest import (
    canonical_digest,
)


def conversation_scope_id(
    *, principal_id: str, scope_kind: str, foundup_id: str,
    discussion_foundup_ids: Sequence[str], session_identity: str,
    conversation_nonce: str,
) -> str:
    """Derive the scope ID from authenticated identity and client nonce."""

    return canonical_digest(
        {
            "principal_id": principal_id,
            "scope_kind": scope_kind,
            "foundup_id": foundup_id,
            "discussion_foundup_ids": list(discussion_foundup_ids),
            "session_binding_digest": session_identity,
            "conversation_nonce": conversation_nonce,
        }
    )


__all__ = ["conversation_scope_id"]
