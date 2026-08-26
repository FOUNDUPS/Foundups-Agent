"""Current-generation admission for one trusted resident conversation scope."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from modules.ai_intelligence.digital_twin.src.resident_conversation_transport_contract import (
    ResidentConversationRequest,
)
from modules.communication.moltbot_bridge.src.reddog_authenticated_conversation_scope_state import (
    AuthenticatedConversationScopeResult,
    create_authenticated_conversation_scope_from_verified_authority,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_session_authority_source import (
    ConversationSessionAuthoritySourceError,
    lease_current_generation_conversation_session,
    public_conversation_session_authority_reason,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_scope_record import (
    rejected,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_scope_store import (
    AgentDbConversationScopeStore,
)
from modules.communication.moltbot_bridge.src.reddog_resident_conversation_new_scope_resolution import (
    resolve_resident_conversation_new_scope_request,
)


UNAVAILABLE_REASON = "resident_conversation_new_scope_unavailable"


def create_current_generation_resident_conversation_scope(
    *, repo_root: Path, intent: Mapping[str, Any], grounding_receipt_id: str,
    serialized_credential: str, owner_config_path: str, now_epoch: int,
    scope_store: AgentDbConversationScopeStore,
    request: ResidentConversationRequest,
) -> AuthenticatedConversationScopeResult:
    """Resolve, authenticate, and durably create one empty-ID TURN scope."""

    creation, reason = resolve_resident_conversation_new_scope_request(
        repo_root=repo_root, intent=intent,
        grounding_receipt_id=grounding_receipt_id,
        request=request, now_epoch=now_epoch,
    )
    if reason or creation is None:
        return rejected(reason or "resident_conversation_new_scope_intent_invalid")
    try:
        with lease_current_generation_conversation_session(
            repo_root=repo_root,
            intent=intent,
            grounding_receipt_id=grounding_receipt_id,
            serialized_credential=serialized_credential,
            owner_config_path=owner_config_path,
            now_epoch=now_epoch,
            include_principal_scope_capability=False,
            require_record_signing_context=True,
        ) as session:
            return create_authenticated_conversation_scope_from_verified_authority(
                store=scope_store,
                authority=session.authority,
                repo_root=repo_root,
                request=creation,
                now_epoch=now_epoch,
                record_epoch=request.issued_at,
                minimum_expires_at=request.expires_at,
            )
    except ConversationSessionAuthoritySourceError as exc:
        return rejected(_session_reason(exc))
    except Exception:
        return rejected(UNAVAILABLE_REASON)


def _session_reason(error: ConversationSessionAuthoritySourceError) -> str:
    return public_conversation_session_authority_reason(
        error, unavailable_reason=UNAVAILABLE_REASON
    )


__all__ = [
    "UNAVAILABLE_REASON",
    "create_current_generation_resident_conversation_scope",
]
