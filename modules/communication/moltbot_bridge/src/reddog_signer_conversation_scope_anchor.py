"""Signer-owned monotonic heads for durable conversation-scope signatures."""

from __future__ import annotations

import json
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Protocol

from modules.communication.moltbot_bridge.src.reddog_authority_runtime_store import (
    AtomicJsonAuthorityRuntimeStore,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_scope_digest import (
    canonical_digest,
)


SCHEMA_VERSION = "reddog_signer_conversation_scope_anchor.v1"
MAX_CONVERSATION_HEADS = 4096
@dataclass(frozen=True)
class ConversationScopeAnchorPreparation:
    expected_revision: str | None
    replay_response: Mapping[str, Any] | None = None
class ConversationScopeAnchorStore(Protocol):
    def prepare(self, payload: Mapping[str, Any]) -> ConversationScopeAnchorPreparation: ...

    def commit(
        self,
        payload: Mapping[str, Any],
        response: Mapping[str, Any],
        *,
        expected_revision: str | None,
    ) -> None: ...
class AtomicSignerConversationScopeAnchorStore:
    """Persist conversation heads under the isolated signer runtime root."""

    def __init__(
        self,
        path: Path | str,
        *,
        runtime_root: Path | str,
        repo_root: Path | str,
    ) -> None:
        self._store = AtomicJsonAuthorityRuntimeStore(
            path,
            allowed_root=runtime_root,
            repo_root=repo_root,
        )

    def prepare(self, payload: Mapping[str, Any]) -> ConversationScopeAnchorPreparation:
        return _prepare(self._store.load(), payload)

    def commit(
        self,
        payload: Mapping[str, Any],
        response: Mapping[str, Any],
        *,
        expected_revision: str | None,
    ) -> None:
        current = self._store.load()
        if current.get("revision") != expected_revision:
            raise ValueError("conversation_scope_anchor_revision_conflict")
        prepared = _prepare(current, payload)
        if prepared.replay_response is not None:
            if dict(prepared.replay_response) != dict(response):
                raise ValueError("conversation_scope_anchor_replay_conflict")
            return
        self._store.commit(
            _next_state(current, payload, response),
            expected_revision=expected_revision,
        )
class InMemorySignerConversationScopeAnchorStore:
    """Thread-safe deterministic anchor used by focused tests."""

    def __init__(self) -> None:
        self._state: dict[str, Any] = {}
        self._lock = threading.Lock()

    def prepare(self, payload: Mapping[str, Any]) -> ConversationScopeAnchorPreparation:
        with self._lock:
            return _prepare(self._state, payload)

    def commit(
        self,
        payload: Mapping[str, Any],
        response: Mapping[str, Any],
        *,
        expected_revision: str | None,
    ) -> None:
        with self._lock:
            if self._state.get("revision") != expected_revision:
                raise ValueError("conversation_scope_anchor_revision_conflict")
            prepared = _prepare(self._state, payload)
            if prepared.replay_response is not None:
                if dict(prepared.replay_response) != dict(response):
                    raise ValueError("conversation_scope_anchor_replay_conflict")
                return
            next_state = _next_state(self._state, payload, response)
            next_state["revision"] = canonical_digest(next_state)
            self._state = next_state

    def load(self) -> dict[str, Any]:
        with self._lock:
            return json.loads(json.dumps(self._state, sort_keys=True))
def _prepare(state: Mapping[str, Any], payload: Mapping[str, Any]) -> ConversationScopeAnchorPreparation:
    _validate_state(state)
    _validate_payload(payload)
    expected = state.get("revision")
    heads = state.get("heads", {})
    head = heads.get(payload["conversation_id"]) if isinstance(heads, Mapping) else None
    if not isinstance(head, Mapping):
        if int(payload["conversation_revision"]) != 0:
            raise ValueError("conversation_scope_anchor_initial_revision_invalid")
        if payload["previous_record_auth_signature_digest"]:
            raise ValueError("conversation_scope_anchor_initial_lineage_invalid")
        if len(heads) >= MAX_CONVERSATION_HEADS:
            raise ValueError("conversation_scope_anchor_capacity_exceeded")
        return ConversationScopeAnchorPreparation(expected_revision=expected)
    if payload["record_state_digest"] == head.get("record_state_digest"):
        return ConversationScopeAnchorPreparation(
            expected_revision=str(expected),
            replay_response=dict(head["signing_response"]),
        )
    if not _advances(head, payload):
        raise ValueError("conversation_scope_anchor_rollback_or_fork")
    return ConversationScopeAnchorPreparation(expected_revision=str(expected))


def _advances(head: Mapping[str, Any], payload: Mapping[str, Any]) -> bool:
    return bool(
        int(payload["conversation_revision"])
        == int(head["conversation_revision"]) + 1
        and payload["previous_record_auth_signature_digest"]
        == head["record_auth_signature_digest"]
        and payload["principal_id"] == head["principal_id"]
        and payload["principal_provider"] == head["principal_provider"]
        and payload["repo_full_name"] == head["repo_full_name"]
        and payload["session_id"] == head["session_id"]
        and payload["record_auth_nonce"] != head["record_auth_nonce"]
    )


def _next_state(
    state: Mapping[str, Any],
    payload: Mapping[str, Any],
    response: Mapping[str, Any],
) -> dict[str, Any]:
    heads = dict(state.get("heads", {}))
    signature = str(response.get("signature") or "")
    if not signature:
        raise ValueError("conversation_scope_anchor_signature_missing")
    heads[str(payload["conversation_id"])] = {
        **dict(payload),
        "record_auth_signature_digest": canonical_digest(
            {"record_auth_signature": signature}
        ),
        "signing_response": dict(response),
    }
    return {"schema_version": SCHEMA_VERSION, "heads": heads}


def _validate_payload(payload: Mapping[str, Any]) -> None:
    required = {
        "conversation_id", "conversation_revision", "record_state_digest",
        "previous_record_auth_signature_digest", "record_auth_nonce",
        "credential_id", "principal_id", "principal_provider",
        "repo_full_name", "session_id",
    }
    if set(payload) != required or type(payload.get("conversation_revision")) is not int:
        raise ValueError("conversation_scope_anchor_payload_invalid")
    if any(
        not isinstance(payload.get(field), str)
        for field in required - {"conversation_revision"}
    ):
        raise ValueError("conversation_scope_anchor_payload_invalid")


def _validate_state(state: Mapping[str, Any]) -> None:
    if not state:
        return
    if (
        state.get("schema_version") != SCHEMA_VERSION
        or not isinstance(state.get("heads"), Mapping)
        or not isinstance(state.get("revision"), str)
        or len(state["heads"]) > MAX_CONVERSATION_HEADS
    ):
        raise ValueError("conversation_scope_anchor_state_invalid")


__all__ = [
    "AtomicSignerConversationScopeAnchorStore", "ConversationScopeAnchorPreparation",
    "ConversationScopeAnchorStore", "InMemorySignerConversationScopeAnchorStore",
    "MAX_CONVERSATION_HEADS", "SCHEMA_VERSION",
]
