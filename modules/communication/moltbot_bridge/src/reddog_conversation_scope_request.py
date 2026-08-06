"""Typed request inputs for RedDog authenticated conversation scope."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class ConversationScopeCreateRequest:
    work_focus: str
    grounding_receipt: Mapping[str, Any]
    discussion_foundup_ids: tuple[str, ...]
    conversation_nonce: str
    turn_id: str
    active_topic: str
    current_objective: str
    accepted_decisions: tuple[Mapping[str, Any], ...] = ()
    rejected_options: tuple[Mapping[str, Any], ...] = ()
    open_questions: tuple[Mapping[str, Any], ...] = ()
    repository_evidence_refs: tuple[str, ...] = ()
    source_snapshot_id: str = ""
    source_snapshot_digest: str = ""
    ttl_seconds: int = 3600
    scope_kind: str = "foundup"


@dataclass(frozen=True)
class ConversationScopeAdvanceRequest:
    conversation_id: str
    expected_revision: int
    work_focus: str
    grounding_receipt: Mapping[str, Any]
    state_patch: Mapping[str, Any]
    expected_source_snapshot_id: str
    expected_source_snapshot_digest: str


__all__ = ["ConversationScopeAdvanceRequest", "ConversationScopeCreateRequest"]
