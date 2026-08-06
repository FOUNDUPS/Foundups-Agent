"""Authenticate and admit bounded 012 Principal Memex context once."""

from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from types import MappingProxyType
from typing import Any, Mapping
from weakref import WeakKeyDictionary

from modules.ai_intelligence.digital_twin.src.principal_memex_projection import (
    build_principal_memex_item,
    project_principal_memex_readonly,
)
from modules.communication.moltbot_bridge.src.reddog_authority_runtime_store import (
    PrincipalAuthorityResolver,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_scope_capability import (
    AuthenticatedConversationScopeCapability,
    VerifiedConversationScopeAuthority,
    consume_conversation_scope_capability,
    conversation_scope_authority_view,
    verify_record_with_scope_authority,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_scope_contract import (
    canonical_digest,
    validate_record,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_scope_kind import (
    SCOPE_KIND_PRINCIPAL,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_scope_record import (
    authority_matches,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_scope_store import (
    AgentDbConversationScopeStore,
)
from modules.communication.moltbot_bridge.src.reddog_principal_memex_disclosure import (
    PrincipalMemexDisclosureGuard,
    VerifiedPrincipalMemexDisclosure,
    verify_principal_memex_disclosure,
)


ADMISSION_SCHEMA_VERSION = "reddog_principal_memex_admission.v1"
ADMISSION_ACCEPT = "PRINCIPAL_MEMEX_ADMISSION_ACCEPT"
ADMISSION_REJECT = "PRINCIPAL_MEMEX_ADMISSION_REJECT"


class _OpaqueContext:
    __slots__ = ("__weakref__",)

    def __new__(cls, *_args: Any, **_kwargs: Any) -> "_OpaqueContext":
        raise TypeError("principal_memex_context_direct_construction_forbidden")

    def __setattr__(self, _name: str, _value: Any) -> None:
        raise TypeError("principal_memex_context_immutable")

    def __reduce__(self) -> Any:
        raise TypeError("principal_memex_context_pickle_forbidden")

    def __copy__(self) -> Any:
        raise TypeError("principal_memex_context_copy_forbidden")

    def __deepcopy__(self, _memo: Any) -> Any:
        raise TypeError("principal_memex_context_copy_forbidden")


class AuthenticatedPrincipalMemexContext(_OpaqueContext):
    """Process-local, one-use Principal Memex model-context capability."""


@dataclass(frozen=True)
class PrincipalMemexAdmissionResult:
    accepted: bool
    status: str
    context: AuthenticatedPrincipalMemexContext | None = None
    admission_receipt: Mapping[str, Any] | None = None
    context_view: Mapping[str, Any] | None = None
    rejection_reasons: tuple[str, ...] = ()
    no_work_authority_granted: bool = True
    no_foundup_projection_performed: bool = True
    no_repo_mutation_performed: bool = True
    no_holoindex_write_performed: bool = True


@dataclass(frozen=True)
class _ContextSeal:
    store: AgentDbConversationScopeStore
    authority: VerifiedConversationScopeAuthority
    record: Mapping[str, Any]
    disclosure: VerifiedPrincipalMemexDisclosure
    guard: PrincipalMemexDisclosureGuard
    projection: Mapping[str, Any]


_LOCK = threading.Lock()
_CONTEXTS: WeakKeyDictionary[AuthenticatedPrincipalMemexContext, _ContextSeal] = (
    WeakKeyDictionary()
)


def prepare_authenticated_principal_memex_context(
    *, store: AgentDbConversationScopeStore,
    capability: AuthenticatedConversationScopeCapability,
    serialized_disclosure: str, principal_resolver: PrincipalAuthorityResolver,
    guard: PrincipalMemexDisclosureGuard, conversation_id: str,
    expected_revision: int, expected_repo_full_name: str,
    expected_transport: str, model_runtime_binding_receipt_id: str,
    model_runtime_binding_digest: str, now_epoch: int,
) -> PrincipalMemexAdmissionResult:
    disclosure = verify_principal_memex_disclosure(
        serialized_disclosure, principal_resolver=principal_resolver,
        expected_repo_full_name=expected_repo_full_name,
        expected_transport=expected_transport,
        expected_model_runtime_binding_receipt_id=model_runtime_binding_receipt_id,
        expected_model_runtime_binding_digest=model_runtime_binding_digest,
        now_epoch=int(now_epoch),
    )
    loaded = store.load(str(conversation_id))
    record = loaded.get("record") if loaded.get("ok") else None
    if disclosure is None or type(record) is not dict:
        return _rejected("principal_memex_source_unavailable")
    reasons = _record_reasons(record, disclosure, expected_revision, now_epoch)
    if reasons or guard.is_revoked(disclosure):
        return _rejected(*(reasons or ("principal_memex_access_denied",)))
    projection = _projection_from_record(record, disclosure)
    if projection is None:
        return _rejected("principal_memex_decision_projection_invalid")
    authority = _consume_authority(capability, record, int(now_epoch))
    if authority is None:
        return _rejected("principal_memex_access_denied")
    context = object.__new__(AuthenticatedPrincipalMemexContext)
    with _LOCK:
        _CONTEXTS[context] = _ContextSeal(
            store, authority, dict(record), disclosure, guard, projection
        )
    return PrincipalMemexAdmissionResult(True, ADMISSION_ACCEPT, context=context)


def consume_authenticated_principal_memex_context(
    context: Any, *, model_runtime_binding_receipt_id: str,
    model_runtime_binding_digest: str, now_epoch: int,
) -> PrincipalMemexAdmissionResult:
    if type(context) is not AuthenticatedPrincipalMemexContext:
        return _rejected("principal_memex_context_invalid")
    with _LOCK:
        seal = _CONTEXTS.pop(context, None)
    if seal is None:
        return _rejected("principal_memex_context_invalid_or_replayed")
    loaded = seal.store.load(str(seal.record["conversation_id"]))
    current = loaded.get("record") if loaded.get("ok") else None
    if not _current_record_valid(current, seal, int(now_epoch)):
        return _rejected("principal_memex_source_changed")
    disclosure = seal.disclosure
    if (
        disclosure.model_runtime_binding_receipt_id != model_runtime_binding_receipt_id
        or disclosure.model_runtime_binding_digest != model_runtime_binding_digest
        or seal.guard.admit_once(disclosure) is not True
    ):
        return _rejected("principal_memex_disclosure_rejected")
    receipt = _admission_receipt(seal, int(now_epoch))
    view = _context_view(seal, receipt)
    return PrincipalMemexAdmissionResult(
        True, ADMISSION_ACCEPT,
        admission_receipt=MappingProxyType(receipt),
        context_view=MappingProxyType(view),
    )


def _consume_authority(
    capability: Any, record: Mapping[str, Any], now_epoch: int,
) -> VerifiedConversationScopeAuthority | None:
    authority = consume_conversation_scope_capability(
        capability, active_foundup_id="", discussion_foundup_ids=(),
        now_epoch=now_epoch, scope_kind=SCOPE_KIND_PRINCIPAL,
    )
    view = conversation_scope_authority_view(authority)
    if (
        authority is None or view is None or not authority_matches(record, view)
        or not verify_record_with_scope_authority(authority, record)
    ):
        return None
    return authority


def _record_reasons(
    record: Mapping[str, Any], disclosure: VerifiedPrincipalMemexDisclosure,
    expected_revision: int, now_epoch: int,
) -> tuple[str, ...]:
    reasons = list(validate_record(record))
    expected = {
        "scope_kind": SCOPE_KIND_PRINCIPAL,
        "conversation_id": disclosure.conversation_id,
        "conversation_revision": disclosure.conversation_revision,
        "record_digest": disclosure.conversation_record_digest,
        "principal_id": disclosure.principal_id,
        "principal_provider": disclosure.principal_provider,
        "credential_id": disclosure.credential_id,
        "session_id": disclosure.session_id,
        "repo_full_name": disclosure.repo_full_name,
    }
    if any(record.get(field) != value for field, value in expected.items()):
        reasons.append("principal_memex_disclosure_binding_mismatch")
    if expected_revision != disclosure.conversation_revision:
        reasons.append("principal_memex_revision_mismatch")
    if int(record.get("expires_at") or 0) <= int(now_epoch):
        reasons.append("principal_memex_conversation_expired")
    return tuple(dict.fromkeys(reasons))


def _projection_from_record(
    record: Mapping[str, Any], disclosure: VerifiedPrincipalMemexDisclosure,
) -> Mapping[str, Any] | None:
    decisions = {
        str(item.get("item_id") or ""): item
        for item in record.get("accepted_decisions", ())
        if type(item) is dict and item.get("kind") == "operator_statement"
    }
    if set(decisions) != set(disclosure.decision_item_ids):
        return None
    created_at = datetime.fromtimestamp(int(record["updated_at"]), timezone.utc).isoformat()
    revision_receipt = str(record["revision_receipts"][-1]["receipt_id"])
    source_revision = f"{record['conversation_id']}:{record['conversation_revision']}:{revision_receipt}"
    try:
        items = [
            build_principal_memex_item(
                principal_id=str(record["principal_id"]), category="decision_history",
                statement=str(decisions[item_id]["summary"]), source_kind="accepted_decision",
                source_receipt_id=str(record["record_digest"]), source_revision=source_revision,
                created_at=created_at, sensitivity="public",
            )
            for item_id in disclosure.decision_item_ids
        ]
        result = project_principal_memex_readonly(
            principal_id=str(record["principal_id"]), items=items, created_at=created_at
        )
    except (KeyError, TypeError, ValueError):
        return None
    return result.projection.to_dict() if result.accepted and result.projection else None


def _current_record_valid(
    current: Any, seal: _ContextSeal, now_epoch: int,
) -> bool:
    return bool(
        type(current) is dict
        and seal.disclosure.issued_at <= now_epoch < seal.disclosure.expires_at
        and current.get("record_digest") == seal.record.get("record_digest")
        and current.get("conversation_revision") == seal.record.get("conversation_revision")
        and int(current.get("expires_at") or 0) > now_epoch
        and not validate_record(current)
        and verify_record_with_scope_authority(seal.authority, current)
        and not seal.guard.is_revoked(seal.disclosure)
    )


def _admission_receipt(seal: _ContextSeal, now_epoch: int) -> dict[str, Any]:
    projection = seal.projection
    disclosure = seal.disclosure
    authority_view = conversation_scope_authority_view(seal.authority)
    payload = {
        "schema_version": ADMISSION_SCHEMA_VERSION,
        "principal_id": disclosure.principal_id,
        "conversation_id": disclosure.conversation_id,
        "conversation_revision": disclosure.conversation_revision,
        "conversation_record_digest": disclosure.conversation_record_digest,
        "projection_id": projection["projection_id"],
        "projection_manifest_digest": projection["manifest_digest"],
        "source_decision_item_ids": list(disclosure.decision_item_ids),
        "admitted_item_ids": list(projection["item_ids"]),
        "disclosure_id": disclosure.disclosure_id,
        "conversation_scope_authority_digest": canonical_digest(authority_view or {}),
        "model_runtime_binding_receipt_id": disclosure.model_runtime_binding_receipt_id,
        "model_runtime_binding_digest": disclosure.model_runtime_binding_digest,
        "admitted_at": now_epoch,
        "expires_at": min(disclosure.expires_at, int(seal.record["expires_at"])),
        "authority_effect": "none",
        "no_work_authority_granted": True,
        "no_foundup_projection_performed": True,
    }
    return {**payload, "receipt_id": canonical_digest(payload)}


def _context_view(seal: _ContextSeal, receipt: Mapping[str, Any]) -> dict[str, Any]:
    projection = seal.projection
    return {
        "source_class": "principal_memex",
        "admission_receipt_id": receipt["receipt_id"],
        "projection_id": projection["projection_id"],
        "conversation_id": seal.disclosure.conversation_id,
        "conversation_revision": seal.disclosure.conversation_revision,
        "items": [
            {"item_id": item["item_id"], "category": item["category"], "statement": item["statement"]}
            for item in projection["items"]
        ],
        "authority_effect": "none",
    }


def _rejected(*reasons: str) -> PrincipalMemexAdmissionResult:
    return PrincipalMemexAdmissionResult(
        False, ADMISSION_REJECT, rejection_reasons=tuple(dict.fromkeys(reasons))
    )


__all__ = [
    "ADMISSION_ACCEPT", "ADMISSION_REJECT", "AuthenticatedPrincipalMemexContext",
    "PrincipalMemexAdmissionResult", "consume_authenticated_principal_memex_context",
    "prepare_authenticated_principal_memex_context",
]
