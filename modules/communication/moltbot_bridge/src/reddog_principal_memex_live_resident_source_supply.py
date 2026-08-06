"""Defer one bounded Principal Memex disclosure to final architect admission."""

from __future__ import annotations

import re
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Mapping
from weakref import WeakKeyDictionary

from modules.ai_intelligence.ai_gateway.src.model_runtime_binding_digest import (
    canonical_model_runtime_binding_digest,
)
from modules.ai_intelligence.ai_gateway.src.model_signed_evidence import (
    rehydrate_model_runtime_binding_receipt,
)
from modules.communication.moltbot_bridge.src.reddog_authority_runtime_store import (
    AuthorityRuntimeStore,
    PrincipalAuthorityResolver,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_scope_capability import (
    PrincipalContextReadConversationScopeCapability,
    discard_conversation_scope_capability,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_scope_store import (
    AgentDbConversationScopeStore,
)
from modules.communication.moltbot_bridge.src.reddog_model_runtime_binding_query import (
    runtime_binding_rejections,
)
from modules.communication.moltbot_bridge.src.reddog_principal_memex_disclosure import (
    AuthorityRuntimePrincipalMemexDisclosureGuard,
)
from modules.communication.moltbot_bridge.src.reddog_principal_memex_resident_admission import (
    AuthenticatedPrincipalMemexContext,
    prepare_authenticated_principal_memex_context,
)
from modules.communication.moltbot_bridge.src.reddog_resident_model_runtime_bindings import (
    ARCHITECT_SURFACE,
)


SUPPLY_FIELDS = frozenset(
    {"serialized_disclosure", "conversation_id", "expected_conversation_revision"}
)
MAX_DISCLOSURE_BYTES = 12_288
_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


class _OpaqueSource:
    __slots__ = ("__weakref__",)

    def __new__(cls, *_args: Any, **_kwargs: Any) -> "_OpaqueSource":
        raise TypeError("principal_memex_source_direct_construction_forbidden")

    def __setattr__(self, _name: str, _value: Any) -> None:
        raise TypeError("principal_memex_source_immutable")

    def __copy__(self) -> Any:
        raise TypeError("principal_memex_source_copy_forbidden")

    def __deepcopy__(self, _memo: Any) -> Any:
        raise TypeError("principal_memex_source_copy_forbidden")

    def __reduce__(self) -> Any:
        raise TypeError("principal_memex_source_pickle_forbidden")

    def __repr__(self) -> str:
        return f"<{type(self).__name__} opaque>"


class PrincipalMemexSessionAuthorization(_OpaqueSource):
    """Current-generation session identity restricted to Principal Memex read."""


class DeferredPrincipalMemexResidentSource(_OpaqueSource):
    """One-use source consumed only after resident duplicate/active checks."""


@dataclass(frozen=True, repr=False)
class PrincipalMemexLiveResidentSourceSupply:
    """Sensitive one-call input that must never enter AgentDB or model output."""

    serialized_disclosure: str = field(repr=False, compare=False)
    conversation_id: str
    expected_conversation_revision: int

    def __post_init__(self) -> None:
        if not _supply_values_valid(
            self.serialized_disclosure,
            self.conversation_id,
            self.expected_conversation_revision,
        ):
            raise ValueError("principal_memex_source_supply_invalid")

    def __reduce__(self) -> Any:
        raise TypeError("principal_memex_source_supply_pickle_forbidden")


@dataclass(frozen=True)
class PrincipalMemexLiveSourceAdmission:
    accepted: bool
    context: AuthenticatedPrincipalMemexContext | None = None
    now_epoch: int = 0
    trusted_now_epoch: Callable[[], int] | None = field(
        default=None, repr=False, compare=False
    )
    rejection_reasons: tuple[str, ...] = ()


@dataclass(frozen=True)
class PrincipalMemexCycleContextAdmission:
    """Final-cycle Principal context or a bounded rejection."""

    accepted: bool
    context: AuthenticatedPrincipalMemexContext | None
    trusted_now_epoch: Callable[[], int] | None
    rejection_reasons: tuple[str, ...] = ()


@dataclass(frozen=True)
class _SessionSeal:
    capability: PrincipalContextReadConversationScopeCapability
    principal_resolver: PrincipalAuthorityResolver
    repo_full_name: str
    intent_id: str
    grounding_receipt_id: str
    session_binding_digest: str
    generation_manifest_id: str
    artifact_generation_digest: str
    runtime_root: Path


@dataclass(frozen=True)
class _SourceSeal:
    session: _SessionSeal
    supply: PrincipalMemexLiveResidentSourceSupply
    authority_store: AuthorityRuntimeStore
    model_binding: Any
    now_epoch: Callable[[], int]
    conversation_store: AgentDbConversationScopeStore | None


_LOCK = threading.Lock()
_SESSIONS: WeakKeyDictionary[PrincipalMemexSessionAuthorization, _SessionSeal] = (
    WeakKeyDictionary()
)
_SOURCES: WeakKeyDictionary[DeferredPrincipalMemexResidentSource, _SourceSeal] = (
    WeakKeyDictionary()
)


def issue_principal_memex_session_authorization(
    *, capability: PrincipalContextReadConversationScopeCapability,
    principal_resolver: PrincipalAuthorityResolver, repo_full_name: str,
    intent_id: str, grounding_receipt_id: str, session_binding_digest: str,
    generation_manifest_id: str, artifact_generation_digest: str,
    runtime_root: Path,
) -> PrincipalMemexSessionAuthorization:
    """Move one restricted child into an opaque current-generation source."""

    authorization = object.__new__(PrincipalMemexSessionAuthorization)
    seal = _SessionSeal(
        capability, principal_resolver, repo_full_name, intent_id,
        grounding_receipt_id, session_binding_digest, generation_manifest_id,
        artifact_generation_digest, runtime_root.resolve(),
    )
    with _LOCK:
        _SESSIONS[authorization] = seal
    return authorization


def principal_memex_session_runtime_root(
    authorization: Any,
) -> Path | None:
    if type(authorization) is not PrincipalMemexSessionAuthorization:
        return None
    with _LOCK:
        seal = _SESSIONS.get(authorization)
    return seal.runtime_root if seal is not None else None


def defer_principal_memex_live_resident_source(
    *, supply: PrincipalMemexLiveResidentSourceSupply,
    authorization: PrincipalMemexSessionAuthorization,
    authority_store: AuthorityRuntimeStore,
    model_runtime_binding_receipt: Mapping[str, Any],
    now_epoch: Callable[[], int],
    conversation_store: AgentDbConversationScopeStore | None = None,
) -> DeferredPrincipalMemexResidentSource | None:
    binding = _validated_architect_binding(model_runtime_binding_receipt)
    if (
        binding is None
        or not callable(now_epoch)
        or type(authorization) is not PrincipalMemexSessionAuthorization
    ):
        return None
    with _LOCK:
        session = _SESSIONS.pop(authorization, None)
    if session is None:
        return None
    source = object.__new__(DeferredPrincipalMemexResidentSource)
    with _LOCK:
        _SOURCES[source] = _SourceSeal(
            session, supply, authority_store, binding, now_epoch,
            conversation_store,
        )
    return source


def consume_principal_memex_live_resident_source(
    source: Any,
    *,
    resident_cycle_id: str,
    conversation_store: AgentDbConversationScopeStore | None = None,
) -> PrincipalMemexLiveSourceAdmission:
    if type(source) is not DeferredPrincipalMemexResidentSource:
        return _rejected("principal_memex_live_source_invalid")
    with _LOCK:
        seal = _SOURCES.pop(source, None)
    if seal is None:
        return _rejected("principal_memex_live_source_invalid_or_replayed")
    try:
        now_epoch = seal.now_epoch()
        if type(now_epoch) is not int or now_epoch < 0:
            return _rejected("principal_memex_live_source_clock_invalid")
        return _prepare_source(
            seal,
            resident_cycle_id,
            conversation_store or seal.conversation_store,
            now_epoch,
        )
    except Exception:
        return _rejected("principal_memex_live_source_admission_failed")
    finally:
        discard_conversation_scope_capability(seal.session.capability)


def admit_principal_memex_cycle_context(
    *, direct_context: AuthenticatedPrincipalMemexContext | None,
    source: DeferredPrincipalMemexResidentSource | None, resident_cycle_id: str,
) -> PrincipalMemexCycleContextAdmission:
    if direct_context is not None and source is not None:
        return PrincipalMemexCycleContextAdmission(
            False, None, None, ("principal_memex_source_conflict",)
        )
    if source is None:
        return PrincipalMemexCycleContextAdmission(True, direct_context, None, ())
    admission = consume_principal_memex_live_resident_source(
        source, resident_cycle_id=resident_cycle_id
    )
    if not admission.accepted or admission.context is None:
        return PrincipalMemexCycleContextAdmission(
            False, None, None, admission.rejection_reasons
        )
    return PrincipalMemexCycleContextAdmission(
        True, admission.context, admission.trusted_now_epoch, ()
    )


def _prepare_source(
    seal: _SourceSeal, resident_cycle_id: str,
    conversation_store: AgentDbConversationScopeStore | None, now_epoch: int,
) -> PrincipalMemexLiveSourceAdmission:
    session = seal.session
    binding = seal.model_binding
    prepared = prepare_authenticated_principal_memex_context(
        store=conversation_store or AgentDbConversationScopeStore(),
        capability=session.capability,
        serialized_disclosure=seal.supply.serialized_disclosure,
        principal_resolver=session.principal_resolver,
        guard=AuthorityRuntimePrincipalMemexDisclosureGuard(seal.authority_store),
        conversation_id=seal.supply.conversation_id,
        expected_revision=seal.supply.expected_conversation_revision,
        expected_repo_full_name=session.repo_full_name,
        expected_transport="editor",
        model_runtime_binding_receipt_id=binding.receipt_id,
        model_runtime_binding_digest=canonical_model_runtime_binding_digest(binding),
        expected_intent_id=session.intent_id,
        expected_grounding_receipt_id=session.grounding_receipt_id,
        expected_resident_cycle_id=resident_cycle_id,
        expected_session_binding_digest=session.session_binding_digest,
        current_generation_manifest_id=session.generation_manifest_id,
        artifact_generation_digest=session.artifact_generation_digest,
        now_epoch=now_epoch,
    )
    if not prepared.accepted or prepared.context is None:
        return _rejected(*prepared.rejection_reasons, now_epoch=now_epoch)
    return PrincipalMemexLiveSourceAdmission(
        True, prepared.context, now_epoch, seal.now_epoch, ()
    )


def discard_principal_memex_live_resident_source(value: Any) -> None:
    if type(value) not in {
        PrincipalMemexSessionAuthorization,
        DeferredPrincipalMemexResidentSource,
    }:
        return
    with _LOCK:
        session = _SESSIONS.pop(value, None)
        source = _SOURCES.pop(value, None)
    seal = session or (source.session if source is not None else None)
    if seal is not None:
        discard_conversation_scope_capability(seal.capability)


def principal_memex_live_resident_source_pending(value: Any) -> bool:
    """Return whether final-cycle admission has not consumed the source."""
    if type(value) is not DeferredPrincipalMemexResidentSource:
        return False
    with _LOCK:
        return value in _SOURCES


def parse_principal_memex_live_resident_source_supply(
    value: Any,
) -> tuple[PrincipalMemexLiveResidentSourceSupply | None, tuple[str, ...]]:
    if value is None:
        return None, ()
    if type(value) is not dict or set(value) != SUPPLY_FIELDS:
        return None, ("principal_memex_source_supply_invalid",)
    serialized = value.get("serialized_disclosure")
    conversation_id = value.get("conversation_id")
    revision = value.get("expected_conversation_revision")
    if not _supply_values_valid(serialized, conversation_id, revision):
        return None, ("principal_memex_source_supply_invalid",)
    return PrincipalMemexLiveResidentSourceSupply(
        serialized, conversation_id, revision
    ), ()


def _validated_architect_binding(value: Mapping[str, Any]) -> Any:
    try:
        receipt = rehydrate_model_runtime_binding_receipt(value)
    except Exception:
        return None
    if runtime_binding_rejections(receipt, expected_surface=ARCHITECT_SURFACE):
        return None
    return receipt


def _supply_values_valid(
    serialized: Any, conversation_id: Any, revision: Any,
) -> bool:
    return bool(
        type(serialized) is str
        and serialized.isascii()
        and 0 < len(serialized.encode("ascii")) <= MAX_DISCLOSURE_BYTES
        and type(conversation_id) is str
        and _SHA256_RE.fullmatch(conversation_id)
        and type(revision) is int
        and revision >= 0
    )


def _rejected(
    *reasons: str, now_epoch: int = 0,
) -> PrincipalMemexLiveSourceAdmission:
    values = tuple(dict.fromkeys(reason for reason in reasons if reason))
    return PrincipalMemexLiveSourceAdmission(
        False,
        None,
        now_epoch,
        None,
        values or ("principal_memex_live_source_rejected",),
    )


__all__ = [
    "DeferredPrincipalMemexResidentSource",
    "PrincipalMemexCycleContextAdmission",
    "PrincipalMemexLiveResidentSourceSupply",
    "PrincipalMemexLiveSourceAdmission",
    "PrincipalMemexSessionAuthorization",
    "consume_principal_memex_live_resident_source",
    "admit_principal_memex_cycle_context",
    "defer_principal_memex_live_resident_source",
    "discard_principal_memex_live_resident_source",
    "issue_principal_memex_session_authorization",
    "parse_principal_memex_live_resident_source_supply",
    "principal_memex_live_resident_source_pending",
    "principal_memex_session_runtime_root",
]
