"""Fail-closed resident request admission for a current signed session."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from modules.ai_intelligence.digital_twin.src.resident_conversation_transport_contract import (
    ResidentConversationRequest,
    enforce_request_freshness,
    resident_conversation_request_reasons,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_session_authority_source import (
    ConversationSessionAuthoritySourceError,
    lease_current_generation_conversation_session,
    public_conversation_session_authority_reason,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_scope_store import (
    AgentDbConversationScopeStore,
)
from modules.communication.moltbot_bridge.src.reddog_resident_conversation_request_journal import (
    AgentDbResidentConversationRequestJournal,
    reserve_bound_resident_conversation_request,
)
from modules.communication.moltbot_bridge.src.reddog_resident_conversation_request_reservation_contract import (
    ResidentConversationRequestReservationResult,
    rejected_result,
)
from modules.communication.moltbot_bridge.src.reddog_resident_conversation_scope_binding import (
    bind_resident_conversation_request_to_verified_scope_authority,
)


UNAVAILABLE_REASON = "resident_conversation_admission_unavailable"


def reserve_current_generation_resident_conversation_request(
    *,
    repo_root: Path,
    intent: Mapping[str, Any],
    grounding_receipt_id: str,
    serialized_credential: str,
    owner_config_path: str,
    now_epoch: int,
    scope_store: AgentDbConversationScopeStore,
    journal: AgentDbResidentConversationRequestJournal,
    request: ResidentConversationRequest,
) -> ResidentConversationRequestReservationResult:
    """Authenticate, scope-bind, and reserve one existing-scope request."""

    reason = _request_rejection_reason(request, now_epoch)
    if reason:
        return rejected_result(reason)
    if not request.conversation_id:
        return rejected_result(
            "resident_conversation_new_scope_resolution_required"
        )
    try:
        with lease_current_generation_conversation_session(
            repo_root=repo_root,
            intent=intent,
            grounding_receipt_id=grounding_receipt_id,
            serialized_credential=serialized_credential,
            owner_config_path=owner_config_path,
            now_epoch=now_epoch,
            include_principal_scope_capability=False,
        ) as session:
            binding = bind_resident_conversation_request_to_verified_scope_authority(
                store=scope_store,
                authority=session.authority,
                request=request,
                now_epoch=now_epoch,
            )
            if not binding.accepted:
                return rejected_result(_binding_rejection_reason(binding))
            return reserve_bound_resident_conversation_request(
                journal=journal,
                request=request,
                binding=binding,
                now_epoch=now_epoch,
            )
    except ConversationSessionAuthoritySourceError as exc:
        return rejected_result(_session_source_rejection_reason(exc))
    except Exception:
        return rejected_result(UNAVAILABLE_REASON)


def _request_rejection_reason(
    request: ResidentConversationRequest, now_epoch: int
) -> str:
    try:
        if type(now_epoch) is not int or now_epoch < 0:
            return "resident_conversation_now_invalid"
        reasons = resident_conversation_request_reasons(request)
        if reasons:
            return reasons[0]
        enforce_request_freshness(request, now_epoch=now_epoch)
    except ValueError as exc:
        return str(exc) or "resident_conversation_request_invalid"
    except Exception:
        return "resident_conversation_request_invalid"
    return ""


def _session_source_rejection_reason(
    error: ConversationSessionAuthoritySourceError,
) -> str:
    return public_conversation_session_authority_reason(
        error, unavailable_reason=UNAVAILABLE_REASON
    )


def _binding_rejection_reason(binding: Any) -> str:
    reasons = getattr(binding, "rejection_reasons", ())
    return (
        reasons[0]
        if type(reasons) is tuple and reasons and type(reasons[0]) is str
        else "resident_conversation_access_denied"
    )


__all__ = [
    "UNAVAILABLE_REASON",
    "reserve_current_generation_resident_conversation_request",
]
