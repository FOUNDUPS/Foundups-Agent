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
    PrincipalContextReadConversationScopeCapability,
    VerifiedConversationScopeAuthority,
    consume_conversation_scope_capability,
    conversation_scope_authority_view,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_scope_contract import (
    SHA256_RE,
    canonical_digest,
    validate_record,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_scope_kind import (
    SCOPE_KIND_PRINCIPAL,
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
_CONTEXT_FIELDS = frozenset({
    "source_class", "admission_receipt_id", "projection_id", "conversation_id",
    "conversation_revision", "items", "authority_effect",
})
_CONTEXT_ITEM_FIELDS = frozenset({"item_id", "category", "statement"})
_RECEIPT_FIELDS = frozenset({
    "schema_version", "principal_id", "conversation_id", "conversation_revision",
    "conversation_record_digest", "projection_id", "projection_manifest_digest",
    "context_view_digest", "source_decision_item_ids", "admitted_item_ids",
    "disclosure_id", "conversation_scope_authority_digest",
    "model_runtime_binding_receipt_id", "model_runtime_binding_digest",
    "resident_cycle_id", "current_generation_manifest_id",
    "artifact_generation_digest",
    "admitted_at", "expires_at", "authority_effect",
    "no_work_authority_granted", "no_foundup_projection_performed", "receipt_id",
})


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
    context_items: tuple[Mapping[str, str], ...]
    resident_cycle_id: str
    current_generation_manifest_id: str
    artifact_generation_digest: str


_LOCK = threading.Lock()
_CONTEXTS: WeakKeyDictionary[AuthenticatedPrincipalMemexContext, _ContextSeal] = (
    WeakKeyDictionary()
)


def prepare_authenticated_principal_memex_context(
    *, store: AgentDbConversationScopeStore,
    capability: PrincipalContextReadConversationScopeCapability,
    serialized_disclosure: str, principal_resolver: PrincipalAuthorityResolver,
    guard: PrincipalMemexDisclosureGuard, conversation_id: str,
    expected_revision: int, expected_repo_full_name: str,
    expected_transport: str, model_runtime_binding_receipt_id: str,
    model_runtime_binding_digest: str, expected_intent_id: str,
    expected_grounding_receipt_id: str, expected_resident_cycle_id: str,
    expected_session_binding_digest: str,
    current_generation_manifest_id: str, artifact_generation_digest: str,
    now_epoch: int,
) -> PrincipalMemexAdmissionResult:
    if not all(
        SHA256_RE.fullmatch(str(value or ""))
        for value in (
            expected_resident_cycle_id,
            current_generation_manifest_id,
            artifact_generation_digest,
        )
    ):
        return _rejected("principal_memex_resident_cycle_invalid")
    disclosure = verify_principal_memex_disclosure(
        serialized_disclosure, principal_resolver=principal_resolver,
        expected_repo_full_name=expected_repo_full_name,
        expected_transport=expected_transport,
        expected_model_runtime_binding_receipt_id=model_runtime_binding_receipt_id,
        expected_model_runtime_binding_digest=model_runtime_binding_digest,
        expected_intent_id=expected_intent_id,
        expected_grounding_receipt_id=expected_grounding_receipt_id,
        expected_session_binding_digest=expected_session_binding_digest,
        now_epoch=int(now_epoch),
    )
    loaded = store.load(str(conversation_id))
    record = loaded.get("record") if loaded.get("ok") else None
    if disclosure is None or type(record) is not dict:
        return _rejected("principal_memex_source_unavailable")
    reasons = _record_reasons(record, disclosure, expected_revision, now_epoch)
    if reasons or guard.is_revoked(disclosure):
        return _rejected(*(reasons or ("principal_memex_access_denied",)))
    projection_result = _projection_from_record(record, disclosure)
    if projection_result is None:
        return _rejected("principal_memex_decision_projection_invalid")
    projection, context_items = projection_result
    authority = _consume_authority(capability, disclosure, int(now_epoch))
    if authority is None:
        return _rejected("principal_memex_access_denied")
    context = object.__new__(AuthenticatedPrincipalMemexContext)
    with _LOCK:
        _CONTEXTS[context] = _ContextSeal(
            store, authority, dict(record), disclosure, guard, projection,
            context_items, expected_resident_cycle_id, current_generation_manifest_id,
            artifact_generation_digest,
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
    if validate_principal_memex_admission_output(receipt, view) is None:
        return _rejected("principal_memex_admission_output_invalid")
    return PrincipalMemexAdmissionResult(
        True, ADMISSION_ACCEPT,
        admission_receipt=_deep_freeze(receipt),
        context_view=_deep_freeze(view),
    )


def validate_principal_memex_admission_output(
    receipt: Any, context_view: Any,
) -> tuple[dict[str, Any], dict[str, Any]] | None:
    try:
        receipt_value = _deep_thaw(receipt)
        context_value = _deep_thaw(context_view)
    except (TypeError, ValueError):
        return None
    if not _admission_receipt_valid(receipt_value, context_value):
        return None
    return receipt_value, context_value


def _consume_authority(
    capability: Any, disclosure: VerifiedPrincipalMemexDisclosure, now_epoch: int,
) -> VerifiedConversationScopeAuthority | None:
    authority = consume_conversation_scope_capability(
        capability, active_foundup_id="", discussion_foundup_ids=(),
        now_epoch=now_epoch, scope_kind=SCOPE_KIND_PRINCIPAL,
    )
    view = conversation_scope_authority_view(authority)
    if (
        authority is None
        or view is None
        or not _request_authority_matches(view, disclosure)
    ):
        return None
    return authority


def _request_authority_matches(
    authority: Mapping[str, Any], disclosure: VerifiedPrincipalMemexDisclosure,
) -> bool:
    expected = {
        "principal_id": disclosure.principal_id,
        "principal_provider": disclosure.principal_provider,
        "repo_full_name": disclosure.repo_full_name,
        "transport": disclosure.transport,
        "session_binding_digest": disclosure.session_binding_digest,
    }
    return all(authority.get(field) == value for field, value in expected.items())


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
) -> tuple[Mapping[str, Any], tuple[Mapping[str, str], ...]] | None:
    decisions = {
        str(item.get("item_id") or ""): item
        for item in record.get("accepted_decisions", ())
        if type(item) is dict and item.get("kind") == "operator_statement"
    }
    if any(item_id not in decisions for item_id in disclosure.decision_item_ids):
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
    if not result.accepted or result.projection is None:
        return None
    context_items = tuple(
        {
            "item_id": item.item_id,
            "category": item.category,
            "statement": item.statement,
        }
        for item in items
    )
    return result.projection.to_dict(), context_items


def _current_record_valid(
    current: Any, seal: _ContextSeal, now_epoch: int,
) -> bool:
    return bool(
        type(current) is dict
        and seal.disclosure.issued_at <= now_epoch < seal.disclosure.expires_at
        and current.get("record_digest") == seal.record.get("record_digest")
        and current.get("conversation_revision") == seal.record.get("conversation_revision")
        and int(current.get("expires_at") or 0) > now_epoch
        and int((conversation_scope_authority_view(seal.authority) or {}).get("expires_at") or 0)
        > now_epoch
        and not validate_record(current)
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
        "context_view_digest": canonical_digest(_context_payload(seal)),
        "source_decision_item_ids": list(disclosure.decision_item_ids),
        "admitted_item_ids": [item["item_id"] for item in seal.context_items],
        "disclosure_id": disclosure.disclosure_id,
        "conversation_scope_authority_digest": canonical_digest(authority_view or {}),
        "model_runtime_binding_receipt_id": disclosure.model_runtime_binding_receipt_id,
        "model_runtime_binding_digest": disclosure.model_runtime_binding_digest,
        "resident_cycle_id": seal.resident_cycle_id,
        "current_generation_manifest_id": seal.current_generation_manifest_id,
        "artifact_generation_digest": seal.artifact_generation_digest,
        "admitted_at": now_epoch,
        "expires_at": min(disclosure.expires_at, int(seal.record["expires_at"])),
        "authority_effect": "none",
        "no_work_authority_granted": True,
        "no_foundup_projection_performed": True,
    }
    return {**payload, "receipt_id": canonical_digest(payload)}


def _context_view(seal: _ContextSeal, receipt: Mapping[str, Any]) -> dict[str, Any]:
    return {
        **_context_payload(seal),
        "admission_receipt_id": receipt["receipt_id"],
    }


def _context_payload(seal: _ContextSeal) -> dict[str, Any]:
    projection = seal.projection
    return {
        "source_class": "principal_memex",
        "projection_id": projection["projection_id"],
        "conversation_id": seal.disclosure.conversation_id,
        "conversation_revision": seal.disclosure.conversation_revision,
        "items": [dict(item) for item in seal.context_items],
        "authority_effect": "none",
    }


def _admission_receipt_valid(
    receipt: dict[str, Any], context: dict[str, Any],
) -> bool:
    if set(context) != _CONTEXT_FIELDS or set(receipt) != _RECEIPT_FIELDS:
        return False
    payload = {key: value for key, value in receipt.items() if key != "receipt_id"}
    items = context.get("items")
    if type(items) is not list or not items:
        return False
    item_ids = [item.get("item_id") for item in items if type(item) is dict]
    context_payload = {
        key: value for key, value in context.items() if key != "admission_receipt_id"
    }
    return bool(
        len(item_ids) == len(items)
        and all(set(item) == _CONTEXT_ITEM_FIELDS for item in items)
        and all(type(value) is str and value for item in items for value in item.values())
        and type(receipt.get("conversation_revision")) is int
        and int(receipt["conversation_revision"]) >= 0
        and type(receipt.get("admitted_at")) is int
        and type(receipt.get("expires_at")) is int
        and int(receipt["admitted_at"]) < int(receipt["expires_at"])
        and type(receipt.get("source_decision_item_ids")) is list
        and SHA256_RE.fullmatch(str(receipt.get("resident_cycle_id") or ""))
        and SHA256_RE.fullmatch(
            str(receipt.get("current_generation_manifest_id") or "")
        )
        and SHA256_RE.fullmatch(
            str(receipt.get("artifact_generation_digest") or "")
        )
        and len(receipt["source_decision_item_ids"])
        == len(set(receipt["source_decision_item_ids"])) > 0
        and len(item_ids) == len(set(item_ids))
        and receipt.get("schema_version") == ADMISSION_SCHEMA_VERSION
        and receipt.get("receipt_id") == canonical_digest(payload)
        and receipt.get("context_view_digest") == canonical_digest(context_payload)
        and context.get("admission_receipt_id") == receipt.get("receipt_id")
        and context.get("source_class") == "principal_memex"
        and context.get("authority_effect") == receipt.get("authority_effect") == "none"
        and context.get("projection_id") == receipt.get("projection_id")
        and context.get("conversation_id") == receipt.get("conversation_id")
        and context.get("conversation_revision") == receipt.get("conversation_revision")
        and item_ids == receipt.get("admitted_item_ids")
        and receipt.get("no_work_authority_granted") is True
        and receipt.get("no_foundup_projection_performed") is True
    )


def _deep_freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({str(key): _deep_freeze(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_deep_freeze(item) for item in value)
    return value


def _deep_thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _deep_thaw(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_deep_thaw(item) for item in value]
    if value is None or type(value) in {str, int, bool}:
        return value
    raise TypeError("principal_memex_admission_output_type_invalid")


def _rejected(*reasons: str) -> PrincipalMemexAdmissionResult:
    return PrincipalMemexAdmissionResult(
        False, ADMISSION_REJECT, rejection_reasons=tuple(dict.fromkeys(reasons))
    )


__all__ = [
    "ADMISSION_ACCEPT", "ADMISSION_REJECT", "AuthenticatedPrincipalMemexContext",
    "PrincipalMemexAdmissionResult", "consume_authenticated_principal_memex_context",
    "prepare_authenticated_principal_memex_context",
    "validate_principal_memex_admission_output",
]
