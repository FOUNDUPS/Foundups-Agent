"""Authenticated conversation binding for the existing architect proposal chain."""

from __future__ import annotations

import threading
from dataclasses import asdict, dataclass
from typing import Any, Mapping
from weakref import WeakKeyDictionary

from modules.communication.moltbot_bridge.src.reddog_architect_proposal_admission_contract import (
    CONVERSATION_WORK_BINDING_SCHEMA,
    validate_architect_proposal_executability_receipt,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_scope_capability import (
    AuthenticatedConversationScopeCapability,
    VerifiedConversationScopeAuthority,
    consume_conversation_scope_capability,
    conversation_scope_authority_view,
    sign_record_with_scope_authority,
    verify_record_with_scope_authority,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_scope_contract import (
    canonical_digest,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_scope_record import (
    AuthenticatedConversationScopeResult,
    authority_matches,
    rejected,
    revision_receipt,
    stored_result,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_scope_store import (
    AgentDbConversationScopeStore,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_scope_signing import (
    unsigned_conversation_scope_record,
)


class _OpaqueCapability:
    __slots__ = ("__weakref__",)

    def __new__(cls, *_args: Any, **_kwargs: Any) -> "_OpaqueCapability":
        raise TypeError("conversation_work_capability_direct_construction_forbidden")

    def __setattr__(self, _name: str, _value: Any) -> None:
        raise TypeError("conversation_work_capability_is_immutable")

    def __copy__(self) -> Any:
        raise TypeError("conversation_work_capability_copy_forbidden")

    def __deepcopy__(self, _memo: Any) -> Any:
        raise TypeError("conversation_work_capability_copy_forbidden")

    def __reduce__(self) -> Any:
        raise TypeError("conversation_work_capability_pickle_forbidden")


class AuthenticatedConversationWorkContext(_OpaqueCapability):
    """Process-local proof used while one proposal is being determined."""


class VerifiedPendingConversationProposalCapability(_OpaqueCapability):
    """One-use proof that the exact proposal remains pending and current."""


@dataclass(frozen=True)
class ConversationWorkBinding:
    schema_version: str
    conversation_id: str
    conversation_revision: int
    conversation_revision_receipt_id: str
    conversation_scope_record_digest: str
    authorized_foundup_id: str
    resident_intent_id: str
    resident_intent_digest: str
    conversation_grounding_receipt_id: str
    snapshot_receipt_id: str
    snapshot_content_digest: str
    repo_head_sha: str
    holoindex_generation_id: str
    holoindex_freshness_receipt_digest: str
    conversation_binding_digest: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ConversationWorkContextResult:
    accepted: bool
    status: str
    context: AuthenticatedConversationWorkContext | None = None
    binding: ConversationWorkBinding | None = None
    rejection_reasons: tuple[str, ...] = ()
    no_work_authority_granted: bool = True
    no_worker_dispatch_performed: bool = True
    no_repo_mutation_performed: bool = True
    no_holoindex_reindex_performed: bool = True


@dataclass(frozen=True)
class _ContextSeal:
    store: AgentDbConversationScopeStore
    record: Mapping[str, Any]
    authority: VerifiedConversationScopeAuthority
    binding: ConversationWorkBinding


@dataclass(frozen=True)
class _PendingSeal:
    store: AgentDbConversationScopeStore
    proposal_id: str
    proposal_digest: str
    conversation_id: str
    current_record_digest: str


_LOCK = threading.Lock()
_CONTEXTS: WeakKeyDictionary[AuthenticatedConversationWorkContext, _ContextSeal] = (
    WeakKeyDictionary()
)
_PENDING: WeakKeyDictionary[
    VerifiedPendingConversationProposalCapability, _PendingSeal
] = WeakKeyDictionary()


def prepare_conversation_work_context(
    *,
    store: AgentDbConversationScopeStore,
    capability: AuthenticatedConversationScopeCapability,
    conversation_id: str,
    expected_revision: int,
    resident_cycle: Mapping[str, Any],
    now_epoch: int,
) -> ConversationWorkContextResult:
    """Authenticate one current scope and bind it to one resident intent."""

    loaded = store.load(conversation_id)
    record = loaded.get("record") if loaded.get("ok") else None
    if not isinstance(record, Mapping):
        return _context_rejected("conversation_work_scope_unavailable")
    authority = _consume_for_record(capability, record, now_epoch)
    if authority is None:
        return _context_rejected("conversation_work_scope_access_denied")
    reasons = _context_reasons(record, resident_cycle, expected_revision, now_epoch)
    if reasons:
        return _context_rejected(*reasons)
    binding = _binding(record, resident_cycle)
    context = object.__new__(AuthenticatedConversationWorkContext)
    with _LOCK:
        _CONTEXTS[context] = _ContextSeal(store, dict(record), authority, binding)
    return ConversationWorkContextResult(
        True, "CONVERSATION_WORK_CONTEXT_ACCEPT", context, binding
    )


def conversation_work_binding(
    context: Any,
) -> Mapping[str, Any] | None:
    if type(context) is not AuthenticatedConversationWorkContext:
        return None
    with _LOCK:
        seal = _CONTEXTS.get(context)
    return seal.binding.to_dict() if seal is not None else None


def commit_pending_conversation_work_proposal(
    *,
    context: AuthenticatedConversationWorkContext,
    architect_determination: Mapping[str, Any],
    now_epoch: int,
) -> AuthenticatedConversationScopeResult:
    """CAS-persist the exact admitted proposal as a non-authorizing preview."""

    seal = _take_context(context)
    if seal is None:
        return rejected("conversation_work_context_invalid_or_replayed")
    admission, reason = _bound_admission(
        architect_determination, seal.binding, seal.record
    )
    if admission is None:
        return rejected(reason)
    current = seal.store.load(seal.binding.conversation_id)
    record = current.get("record") if current.get("ok") else None
    if not _same_source_record(record, seal.record, seal.binding):
        return rejected("conversation_work_scope_changed")
    unsigned = _pending_unsigned_record(seal, admission.to_dict(), int(now_epoch))
    transactions = seal.store.pending_transactions()
    staged = transactions.stage(
        unsigned_conversation_scope_record(unsigned),
        expected_revision=seal.binding.conversation_revision,
    )
    if not staged.get("ok") or not isinstance(staged.get("record"), Mapping):
        return rejected(
            str(staged.get("reason") or "conversation_scope_pending_rejected")
        )
    updated = dict(staged["record"])
    envelope = sign_record_with_scope_authority(
        seal.authority, updated, require_replay=bool(staged.get("recovery_only"))
    )
    if not isinstance(envelope, Mapping):
        return rejected("conversation_scope_record_authentication_unavailable")
    updated.update(envelope)
    return stored_result(
        transactions.finalize(
            updated,
            expected_revision=seal.binding.conversation_revision,
        )
    )


def verify_pending_conversation_work_proposal(
    *,
    store: AgentDbConversationScopeStore,
    capability: AuthenticatedConversationScopeCapability,
    architect_determination: Mapping[str, Any],
    now_epoch: int,
) -> VerifiedPendingConversationProposalCapability | None:
    """Issue one-use proof that an authorized principal still sees this preview."""

    receipt = _determination_receipt(architect_determination)
    admission_value = receipt.get("proposal_admission")
    try:
        admission = validate_architect_proposal_executability_receipt(
            admission_value if isinstance(admission_value, Mapping) else {}
        )
    except (TypeError, ValueError):
        return None
    if not admission.conversation_binding_present:
        return None
    loaded = store.load(admission.conversation_id)
    record = loaded.get("record") if loaded.get("ok") else None
    if not isinstance(record, Mapping):
        return None
    authority = _consume_for_record(capability, record, now_epoch)
    proposal_digest = canonical_digest(admission.to_dict())
    if authority is None or _pending_reasons(
        record, admission, proposal_digest, now_epoch
    ):
        return None
    pending = object.__new__(VerifiedPendingConversationProposalCapability)
    with _LOCK:
        _PENDING[pending] = _PendingSeal(
            store,
            admission.receipt_id,
            proposal_digest,
            admission.conversation_id,
            str(record["record_digest"]),
        )
    return pending


def consume_pending_conversation_proposal_capability(
    capability: Any,
    *,
    proposal_admission: Mapping[str, Any],
    now_epoch: int,
) -> bool:
    if type(capability) is not VerifiedPendingConversationProposalCapability:
        return False
    with _LOCK:
        seal = _PENDING.pop(capability, None)
    if seal is None:
        return False
    try:
        receipt = validate_architect_proposal_executability_receipt(proposal_admission)
    except (TypeError, ValueError):
        return False
    loaded = seal.store.load(seal.conversation_id)
    record = loaded.get("record") if loaded.get("ok") else None
    current = record if isinstance(record, Mapping) else {}
    return bool(
        receipt.conversation_binding_present
        and seal.proposal_id == receipt.receipt_id
        and seal.proposal_digest == canonical_digest(receipt.to_dict())
        and seal.conversation_id == receipt.conversation_id
        and seal.current_record_digest == current.get("record_digest")
        and not _pending_reasons(current, receipt, seal.proposal_digest, int(now_epoch))
    )


def _consume_for_record(
    capability: Any, record: Mapping[str, Any], now_epoch: int
) -> VerifiedConversationScopeAuthority | None:
    authority = consume_conversation_scope_capability(
        capability,
        active_foundup_id=str(record.get("authorized_foundup_id") or ""),
        discussion_foundup_ids=tuple(record.get("discussion_foundup_ids") or ()),
        now_epoch=int(now_epoch),
    )
    view = conversation_scope_authority_view(authority)
    if (
        authority is None
        or view is None
        or not authority_matches(record, view)
        or not verify_record_with_scope_authority(authority, record)
    ):
        return None
    return authority


def _context_reasons(
    record: Mapping[str, Any], cycle: Mapping[str, Any], revision: int, now_epoch: int
) -> tuple[str, ...]:
    reasons: list[str] = []
    intent = cycle.get("intent") if isinstance(cycle.get("intent"), Mapping) else {}
    principal = str(
        intent.get("principal_id")
        or intent.get("principal_ref")
        or intent.get("origin_principal")
        or ""
    )
    if int(record.get("conversation_revision", -1)) != int(revision):
        reasons.append("conversation_work_revision_conflict")
    if int(now_epoch) >= int(record.get("expires_at", 0)):
        reasons.append("conversation_work_scope_expired")
    if record.get("pending_work_proposal_id") or record.get(
        "pending_work_proposal_digest"
    ):
        reasons.append("conversation_work_proposal_already_pending")
    if cycle.get("_store_integrity_valid") is not True:
        reasons.append("conversation_work_resident_cycle_unverified")
    if (
        intent.get("schema_version") != "reddog_intent.v2"
        or str(cycle.get("intent_id") or "") != str(intent.get("intent_id") or "")
        or str(cycle.get("intent_digest") or "") != _resident_intent_digest(intent)
    ):
        reasons.append("conversation_work_resident_intent_invalid")
    if principal != record.get("principal_id"):
        reasons.append("conversation_work_principal_mismatch")
    if str(intent.get("foundup_id") or "") != record.get("authorized_foundup_id"):
        reasons.append("conversation_work_foundup_mismatch")
    if str(cycle.get("snapshot_id") or "") != record.get("source_snapshot_id"):
        reasons.append("conversation_work_snapshot_mismatch")
    grounding = intent.get("grounding_receipt")
    grounding_id = (
        str(grounding.get("receipt_id") or "") if isinstance(grounding, Mapping) else ""
    )
    if grounding_id != record.get("grounding_receipt_id"):
        reasons.append("conversation_work_grounding_mismatch")
    return tuple(dict.fromkeys(reasons))


def _binding(
    record: Mapping[str, Any], cycle: Mapping[str, Any]
) -> ConversationWorkBinding:
    payload = {
        "schema_version": CONVERSATION_WORK_BINDING_SCHEMA,
        "conversation_id": record["conversation_id"],
        "conversation_revision": int(record["conversation_revision"]),
        "conversation_revision_receipt_id": record["revision_receipts"][-1][
            "receipt_id"
        ],
        "conversation_scope_record_digest": record["record_digest"],
        "authorized_foundup_id": record["authorized_foundup_id"],
        "resident_intent_id": cycle["intent_id"],
        "resident_intent_digest": cycle["intent_digest"],
        "conversation_grounding_receipt_id": record["grounding_receipt_id"],
        "snapshot_receipt_id": record["source_snapshot_id"],
        "snapshot_content_digest": record["source_snapshot_digest"],
        "repo_head_sha": record["last_grounded_head_sha"],
        "holoindex_generation_id": record["holoindex_generation_id"],
        "holoindex_freshness_receipt_digest": record["holoindex_freshness_receipt_id"],
    }
    return ConversationWorkBinding(
        **payload, conversation_binding_digest=canonical_digest(payload)
    )


def _take_context(context: Any) -> _ContextSeal | None:
    if type(context) is not AuthenticatedConversationWorkContext:
        return None
    with _LOCK:
        return _CONTEXTS.pop(context, None)


def _bound_admission(
    determination: Mapping[str, Any],
    binding: ConversationWorkBinding,
    record: Mapping[str, Any],
) -> tuple[Any | None, str]:
    receipt = _determination_receipt(determination)
    if receipt.get("accepted") is not True or receipt.get("action") != "FIX":
        return None, "conversation_work_determination_not_fix"
    value = receipt.get("proposal_admission")
    try:
        admission = validate_architect_proposal_executability_receipt(
            value if isinstance(value, Mapping) else {}
        )
    except (TypeError, ValueError):
        return None, "conversation_work_proposal_invalid"
    expected = binding.to_dict()
    if any(
        getattr(admission, key) != expected[key]
        for key in expected
        if key != "schema_version"
    ):
        return None, "conversation_work_proposal_binding_mismatch"
    current_bindings = {
        "snapshot_receipt_id": record["source_snapshot_id"],
        "snapshot_content_digest": record["source_snapshot_digest"],
        "repo_head_sha": record["last_grounded_head_sha"],
        "holoindex_generation_id": record["holoindex_generation_id"],
        "holoindex_freshness_receipt_digest": record["holoindex_freshness_receipt_id"],
    }
    if any(getattr(admission, key) != value for key, value in current_bindings.items()):
        return None, "conversation_work_current_binding_mismatch"
    candidate = receipt.get("queue_candidate")
    if not isinstance(candidate, Mapping) or (
        candidate.get("source_determination_receipt_id")
        != receipt.get("determination_receipt_id")
        or candidate.get("proposal_admission_receipt_id") != admission.receipt_id
        or candidate.get("proposal_admission_digest")
        != canonical_digest(admission.to_dict())
    ):
        return None, "conversation_work_queue_candidate_mismatch"
    return admission, ""


def _determination_receipt(value: Mapping[str, Any]) -> Mapping[str, Any]:
    nested = value.get("receipt")
    return nested if isinstance(nested, Mapping) else value


def _same_source_record(
    current: Any, original: Mapping[str, Any], binding: ConversationWorkBinding
) -> bool:
    return bool(
        isinstance(current, Mapping)
        and current.get("record_digest") == original.get("record_digest")
        and current.get("record_digest") == binding.conversation_scope_record_digest
        and current.get("conversation_revision") == binding.conversation_revision
    )


def _pending_unsigned_record(
    seal: _ContextSeal, admission: Mapping[str, Any], now_epoch: int
) -> Mapping[str, Any]:
    current = dict(seal.record)
    proposal_id = str(admission["receipt_id"])
    current.update(
        {
            "conversation_revision": seal.binding.conversation_revision + 1,
            "parent_turn_id": current["turn_id"],
            "turn_id": canonical_digest(
                {"action": "bind_pending_work_proposal", "proposal_id": proposal_id}
            ),
            "pending_work_proposal_id": proposal_id,
            "pending_work_proposal_digest": canonical_digest(admission),
            "updated_at": now_epoch,
        }
    )
    current["previous_record_auth_signature_digest"] = canonical_digest(
        {"record_auth_signature": seal.record["record_auth_signature"]}
    )
    current["record_auth_nonce"] = canonical_digest(
        {
            "conversation_id": current["conversation_id"],
            "conversation_revision": current["conversation_revision"],
            "turn_id": current["turn_id"],
            "updated_at": current["updated_at"],
            "previous_record_auth_signature_digest": current[
                "previous_record_auth_signature_digest"
            ],
        }
    )
    previous = str(current["revision_receipts"][-1]["receipt_id"])
    current["revision_receipts"] = [
        *current["revision_receipts"],
        revision_receipt(
            current,
            previous=previous,
            revision=seal.binding.conversation_revision + 1,
        ),
    ]
    return current


def _pending_reasons(
    record: Mapping[str, Any], admission: Any, proposal_digest: str, now_epoch: int
) -> tuple[str, ...]:
    reasons: list[str] = []
    if int(now_epoch) < int(record.get("updated_at", 0)):
        reasons.append("conversation_work_clock_rollback")
    if int(now_epoch) >= int(record.get("expires_at", 0)):
        reasons.append("conversation_work_scope_expired")
    if (
        record.get("pending_work_proposal_id") != admission.receipt_id
        or record.get("pending_work_proposal_digest") != proposal_digest
    ):
        reasons.append("conversation_work_pending_proposal_mismatch")
    if (
        int(record.get("conversation_revision", -1))
        != admission.conversation_revision + 1
    ):
        reasons.append("conversation_work_revision_mismatch")
    receipts = record.get("revision_receipts") or ()
    if (
        len(receipts) <= admission.conversation_revision
        or receipts[admission.conversation_revision].get("receipt_id")
        != admission.conversation_revision_receipt_id
    ):
        reasons.append("conversation_work_revision_lineage_mismatch")
    expected = {
        "authorized_foundup_id": admission.authorized_foundup_id,
        "source_snapshot_id": admission.snapshot_receipt_id,
        "source_snapshot_digest": admission.snapshot_content_digest,
        "last_grounded_head_sha": admission.repo_head_sha,
        "holoindex_generation_id": admission.holoindex_generation_id,
        "holoindex_freshness_receipt_id": admission.holoindex_freshness_receipt_digest,
        "grounding_receipt_id": admission.conversation_grounding_receipt_id,
    }
    if any(record.get(key) != value for key, value in expected.items()):
        reasons.append("conversation_work_current_binding_mismatch")
    return tuple(reasons)


def _context_rejected(*reasons: str) -> ConversationWorkContextResult:
    return ConversationWorkContextResult(
        False,
        "CONVERSATION_WORK_CONTEXT_REJECT",
        rejection_reasons=tuple(dict.fromkeys(reasons)),
    )


def _resident_intent_digest(intent: Mapping[str, Any]) -> str:
    return canonical_digest(
        {
            "schema_version": "reddog_resident_intent_binding.v1",
            "intent": dict(intent),
        }
    )


__all__ = [
    "AuthenticatedConversationWorkContext",
    "CONVERSATION_WORK_BINDING_SCHEMA",
    "ConversationWorkBinding",
    "ConversationWorkContextResult",
    "VerifiedPendingConversationProposalCapability",
    "commit_pending_conversation_work_proposal",
    "consume_pending_conversation_proposal_capability",
    "conversation_work_binding",
    "prepare_conversation_work_context",
    "verify_pending_conversation_work_proposal",
]
