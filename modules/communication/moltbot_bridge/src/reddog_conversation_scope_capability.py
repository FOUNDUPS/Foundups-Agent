"""Opaque one-use capabilities for authenticated RedDog conversation scope."""

from __future__ import annotations

import threading
from dataclasses import dataclass, replace
from typing import Any, Mapping
from weakref import WeakKeyDictionary

from modules.communication.moltbot_bridge.src.reddog_conversation_scope_mac import (
    sign_conversation_scope_record as sign_hmac_conversation_scope_record,
    verify_conversation_scope_record as verify_hmac_conversation_scope_record,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_scope_signing import (
    CONVERSATION_SCOPE_AUTH_SCHEME,
    ConversationScopeSigningContext,
    sign_conversation_scope_record as sign_e0_conversation_scope_record,
    verify_signed_conversation_scope_record,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_scope_kind import (
    SCOPE_KIND_FOUNDUP,
    SCOPE_KIND_PRINCIPAL,
    scope_request_authorized,
)


class _OpaqueCapability:
    __slots__ = ("__weakref__",)

    def __new__(cls, *_args: Any, **_kwargs: Any) -> "_OpaqueCapability":
        raise TypeError("conversation_scope_capability_direct_construction_forbidden")

    def __setattr__(self, _name: str, _value: Any) -> None:
        raise TypeError("conversation_scope_capability_is_immutable")

    def __copy__(self) -> Any:
        raise TypeError("conversation_scope_capability_copy_forbidden")

    def __deepcopy__(self, _memo: Any) -> Any:
        raise TypeError("conversation_scope_capability_copy_forbidden")

    def __reduce__(self) -> Any:
        raise TypeError("conversation_scope_capability_pickle_forbidden")

    def __repr__(self) -> str:
        return f"<{type(self).__name__} opaque>"


class AuthenticatedConversationScopeCapability(_OpaqueCapability):
    """One-use authenticated session and principal proof."""


class FoundUpConversationScopeCapability(_OpaqueCapability):
    """One-use child restricted to FoundUp authority consumption."""


class PrincipalContextReadConversationScopeCapability(_OpaqueCapability):
    """One-use child restricted to principal-context read consumption."""


class VerifiedConversationScopeAuthority(_OpaqueCapability):
    """Consumed operation-local authority that never exposes MAC keys."""


class ResidentConversationRequestJournalAuthority(_OpaqueCapability):
    """One-use child derived from live verified scope authority."""


@dataclass(frozen=True)
class _ConversationScopeAuthoritySeal:
    principal_id: str
    principal_provider: str
    verified_subject_digest: str
    principal_record_digest: str
    principal_key_fingerprint: str
    foundup_scope: tuple[str, ...]
    transport: str
    session_binding_digest: str
    expires_at: int
    record_sign_key: bytes
    record_verify_keys: tuple[bytes, ...]
    record_auth_scheme: str = "hmac-sha256-v1"
    credential_id: str = ""
    session_id: str = ""
    repo_full_name: str = ""
    record_signing_context: ConversationScopeSigningContext | None = None
    authorized_scope_kind: str = ""
    authorized_active_foundup_id: str = ""
    authorized_discussion_foundup_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class _DelegatedConversationScopeSeal:
    authority: _ConversationScopeAuthoritySeal
    permitted_scope_kind: str


@dataclass(frozen=True)
class _ResidentConversationRequestJournalSeal:
    reservation_id: str
    not_before_epoch: int
    scope_expires_at: int


_LOCK = threading.Lock()
_CAPABILITIES: WeakKeyDictionary[AuthenticatedConversationScopeCapability, _ConversationScopeAuthoritySeal] = WeakKeyDictionary()
_DELEGATED_CAPABILITIES: WeakKeyDictionary[_OpaqueCapability, _DelegatedConversationScopeSeal] = WeakKeyDictionary()
_AUTHORITIES: WeakKeyDictionary[VerifiedConversationScopeAuthority, _ConversationScopeAuthoritySeal] = WeakKeyDictionary()
_JOURNAL_AUTHORITIES: WeakKeyDictionary[ResidentConversationRequestJournalAuthority, _ResidentConversationRequestJournalSeal] = WeakKeyDictionary()


def _issue_conversation_scope_capability(
    seal: _ConversationScopeAuthoritySeal,
) -> AuthenticatedConversationScopeCapability:
    capability = object.__new__(AuthenticatedConversationScopeCapability)
    with _LOCK:
        _CAPABILITIES[capability] = seal
    return capability


def split_conversation_scope_capability(
    capability: Any,
) -> tuple[
    FoundUpConversationScopeCapability,
    PrincipalContextReadConversationScopeCapability,
] | None:
    """Atomically retire one root and issue two scope-restricted children."""
    children = _split_delegated_capabilities(
        capability,
        (
            (FoundUpConversationScopeCapability, SCOPE_KIND_FOUNDUP),
            (PrincipalContextReadConversationScopeCapability, SCOPE_KIND_PRINCIPAL),
        ),
    )
    return children if children is None else (children[0], children[1])


def split_foundup_conversation_scope_capability_pair(
    capability: Any,
) -> tuple[FoundUpConversationScopeCapability, FoundUpConversationScopeCapability] | None:
    """Retire one root into two separately registered FoundUp children."""
    children = _split_delegated_capabilities(
        capability,
        ((FoundUpConversationScopeCapability, SCOPE_KIND_FOUNDUP),) * 2,
    )
    return children if children is None else (children[0], children[1])


def _split_delegated_capabilities(
    capability: Any, specifications: tuple[tuple[type[_OpaqueCapability], str], ...],
) -> tuple[Any, ...] | None:
    if type(capability) is not AuthenticatedConversationScopeCapability:
        return None
    children = tuple(object.__new__(child_type) for child_type, _kind in specifications)
    with _LOCK:
        seal = _CAPABILITIES.pop(capability, None)
        if seal is None:
            return None
        try:
            for child, (_child_type, kind) in zip(children, specifications):
                _DELEGATED_CAPABILITIES[child] = _DelegatedConversationScopeSeal(
                    seal, kind
                )
        except Exception:
            for child in children:
                _DELEGATED_CAPABILITIES.pop(child, None)
            return None
    return children


def consume_conversation_scope_capability(
    capability: Any,
    *,
    active_foundup_id: str,
    discussion_foundup_ids: tuple[str, ...],
    now_epoch: int,
    scope_kind: str = SCOPE_KIND_FOUNDUP,
) -> VerifiedConversationScopeAuthority | None:
    seal = _consume_capability_seal(capability, scope_kind=scope_kind)
    if (
        seal is None
        or int(now_epoch) >= seal.expires_at
        or not scope_request_authorized(
            scope_kind=scope_kind,
            active_foundup_id=active_foundup_id,
            discussion_foundup_ids=discussion_foundup_ids,
            allowed_foundup_ids=seal.foundup_scope,
        )
    ):
        return None
    authority = object.__new__(VerifiedConversationScopeAuthority)
    authority_seal = replace(
        seal,
        authorized_scope_kind=scope_kind,
        authorized_active_foundup_id=active_foundup_id,
        authorized_discussion_foundup_ids=discussion_foundup_ids,
    )
    with _LOCK:
        _AUTHORITIES[authority] = authority_seal
    return authority


def _consume_capability_seal(
    capability: Any, *, scope_kind: str
) -> _ConversationScopeAuthoritySeal | None:
    with _LOCK:
        if type(capability) is AuthenticatedConversationScopeCapability:
            return _CAPABILITIES.pop(capability, None)
        if type(capability) not in {
            FoundUpConversationScopeCapability,
            PrincipalContextReadConversationScopeCapability,
        }:
            return None
        delegated = _DELEGATED_CAPABILITIES.pop(capability, None)
    if delegated is None or delegated.permitted_scope_kind != scope_kind:
        return None
    return delegated.authority


def conversation_scope_authority_view(authority: Any) -> Mapping[str, Any] | None:
    seal = _authority_seal(authority)
    return None if seal is None else _conversation_scope_authority_view(seal)


def _conversation_scope_authority_view(
    seal: _ConversationScopeAuthoritySeal,
) -> Mapping[str, Any]:
    return {
        "principal_id": seal.principal_id,
        "principal_provider": seal.principal_provider,
        "verified_subject_digest": seal.verified_subject_digest,
        "principal_record_digest": seal.principal_record_digest,
        "principal_key_fingerprint": seal.principal_key_fingerprint,
        "foundup_scope": tuple(seal.foundup_scope),
        "transport": seal.transport,
        "session_binding_digest": seal.session_binding_digest,
        "record_auth_scheme": seal.record_auth_scheme,
        "credential_id": seal.credential_id,
        "session_id": seal.session_id,
        "repo_full_name": seal.repo_full_name,
        "expires_at": seal.expires_at,
    }


def consume_and_verify_record_with_scope_authority(
    authority: Any, record: Mapping[str, Any],
) -> Mapping[str, Any] | None:
    """Atomically retire authority, then verify its exact signed scope record."""
    if type(authority) is not VerifiedConversationScopeAuthority:
        return None
    with _LOCK:
        seal = _AUTHORITIES.pop(authority, None)
    return (
        _conversation_scope_authority_view(seal)
        if seal is not None and _verify_record_with_seal(seal, record) else None
    )


def consume_verified_scope_authority_for_scope_creation(
    authority: Any,
    *,
    active_foundup_id: str,
    discussion_foundup_ids: tuple[str, ...],
    scope_kind: str,
    now_epoch: int,
) -> VerifiedConversationScopeAuthority | None:
    """Atomically retire one parent into an exact new-scope operation child."""

    if type(authority) is not VerifiedConversationScopeAuthority:
        return None
    child = object.__new__(VerifiedConversationScopeAuthority)
    with _LOCK:
        seal = _AUTHORITIES.pop(authority, None)
        try:
            admitted = bool(
                seal is not None
                and type(now_epoch) is int
                and 0 <= now_epoch < seal.expires_at
                and scope_kind == seal.authorized_scope_kind
                and active_foundup_id == seal.authorized_active_foundup_id
                and discussion_foundup_ids
                == seal.authorized_discussion_foundup_ids
                and scope_request_authorized(
                    scope_kind=scope_kind,
                    active_foundup_id=active_foundup_id,
                    discussion_foundup_ids=discussion_foundup_ids,
                    allowed_foundup_ids=seal.foundup_scope,
                )
            )
        except Exception:
            admitted = False
        if not admitted:
            return None
        _AUTHORITIES[child] = seal
    return child


def consume_verified_scope_authority_for_request_journal(
    authority: Any,
    *,
    record: Mapping[str, Any],
    reservation_id: str,
    not_before_epoch: int,
    scope_expires_at: int,
) -> ResidentConversationRequestJournalAuthority | None:
    """Atomically retire one verified parent and issue one journal child."""

    if type(authority) is not VerifiedConversationScopeAuthority:
        return None
    child = object.__new__(ResidentConversationRequestJournalAuthority)
    with _LOCK:
        parent = _AUTHORITIES.pop(authority, None)
        if not _journal_child_admission_valid(
            parent, record, reservation_id, not_before_epoch, scope_expires_at
        ):
            return None
        _JOURNAL_AUTHORITIES[child] = _ResidentConversationRequestJournalSeal(
            reservation_id=reservation_id,
            not_before_epoch=not_before_epoch,
            scope_expires_at=scope_expires_at,
        )
    return child


def _journal_child_admission_valid(
    parent: _ConversationScopeAuthoritySeal | None,
    record: Mapping[str, Any],
    reservation_id: str,
    not_before_epoch: int,
    scope_expires_at: int,
) -> bool:
    try:
        return bool(
            parent is not None
            and isinstance(record, Mapping)
            and type(reservation_id) is str
            and type(not_before_epoch) is int
            and type(scope_expires_at) is int
            and 0 <= not_before_epoch < scope_expires_at <= parent.expires_at
            and _verify_record_with_seal(parent, record)
        )
    except Exception:
        return False


def resident_conversation_request_journal_authority_matches(
    authority: Any, *, reservation_id: str, reserved_at: int
) -> bool:
    """Check a registered child without consuming its mutation authority."""

    if type(authority) is not ResidentConversationRequestJournalAuthority:
        return False
    with _LOCK:
        seal = _JOURNAL_AUTHORITIES.get(authority)
        return bool(
            seal is not None
            and reservation_id == seal.reservation_id
            and seal.not_before_epoch <= reserved_at < seal.scope_expires_at
        )


def consume_resident_conversation_request_journal_authority(
    authority: Any, *, reservation_id: str, reserved_at: int, observed_at: int
) -> bool:
    """Consume an exact verified-authority child at the mutation boundary."""

    if type(authority) is not ResidentConversationRequestJournalAuthority:
        return False
    with _LOCK:
        seal = _JOURNAL_AUTHORITIES.pop(authority, None)
    return bool(
        seal is not None
        and reservation_id == seal.reservation_id
        and seal.not_before_epoch <= reserved_at <= observed_at
        and observed_at < seal.scope_expires_at
    )


def sign_record_with_scope_authority(
    authority: Any,
    record: Mapping[str, Any],
    *,
    require_replay: bool = False,
) -> Mapping[str, Any] | None:
    seal = _authority_seal(authority)
    if seal is None or not _record_matches_authorized_scope(seal, record):
        return None
    if seal.record_auth_scheme == CONVERSATION_SCOPE_AUTH_SCHEME:
        if seal.record_signing_context is None:
            return None
        return sign_e0_conversation_scope_record(
            seal.record_signing_context, record, require_replay=require_replay
        )
    if require_replay:
        return None
    if seal.record_auth_scheme == "hmac-sha256-v1" and seal.record_sign_key:
        return {
            "record_auth_signature": sign_hmac_conversation_scope_record(
                record, seal.record_sign_key
            ),
            "record_auth_signer_public_key": "",
            "record_auth_key_fingerprint": "",
            "record_auth_key_epoch": "",
            "record_auth_audit_mac": "",
            "record_auth_audit_attestation_signature": "",
        }
    return None


def verify_record_with_scope_authority(
    authority: Any, record: Mapping[str, Any]
) -> bool:
    seal = _authority_seal(authority)
    return _verify_record_with_seal(seal, record)


def _verify_record_with_seal(
    seal: _ConversationScopeAuthoritySeal | None,
    record: Mapping[str, Any],
) -> bool:
    if (
        seal is None
        or not _record_matches_authority_identity(seal, record)
        or not _record_matches_authorized_scope(seal, record)
        or record.get("record_auth_scheme") != seal.record_auth_scheme
    ):
        return False
    if seal.record_auth_scheme == CONVERSATION_SCOPE_AUTH_SCHEME:
        return bool(seal.record_signing_context) and verify_signed_conversation_scope_record(
            seal.record_signing_context, record
        )
    return verify_hmac_conversation_scope_record(record, seal.record_verify_keys)


def _record_matches_authority_identity(
    seal: _ConversationScopeAuthoritySeal,
    record: Mapping[str, Any],
) -> bool:
    return all(
        record.get(field) == getattr(seal, field)
        for field in (
            "principal_id", "principal_provider", "verified_subject_digest",
            "principal_record_digest", "principal_key_fingerprint", "transport",
            "session_binding_digest", "credential_id", "session_id",
            "repo_full_name", "record_auth_scheme",
        )
    )


def discard_conversation_scope_capability(capability: Any) -> None:
    with _LOCK:
        if type(capability) is AuthenticatedConversationScopeCapability:
            _CAPABILITIES.pop(capability, None)
        elif type(capability) in {
            FoundUpConversationScopeCapability,
            PrincipalContextReadConversationScopeCapability,
        }:
            _DELEGATED_CAPABILITIES.pop(capability, None)
        elif type(capability) is VerifiedConversationScopeAuthority:
            _AUTHORITIES.pop(capability, None)
        elif type(capability) is ResidentConversationRequestJournalAuthority:
            _JOURNAL_AUTHORITIES.pop(capability, None)


def _authority_seal(authority: Any) -> _ConversationScopeAuthoritySeal | None:
    if type(authority) is not VerifiedConversationScopeAuthority:
        return None
    with _LOCK:
        return _AUTHORITIES.get(authority)


def _record_matches_authorized_scope(
    seal: _ConversationScopeAuthoritySeal, record: Mapping[str, Any]
) -> bool:
    discussions = record.get("discussion_foundup_ids")
    return bool(
        isinstance(discussions, list)
        and all(type(item) is str for item in discussions)
        and record.get("scope_kind") == seal.authorized_scope_kind
        and record.get("authorized_foundup_id") == seal.authorized_active_foundup_id
        and tuple(discussions) == seal.authorized_discussion_foundup_ids
    )


__all__ = [
    "AuthenticatedConversationScopeCapability", "FoundUpConversationScopeCapability",
    "PrincipalContextReadConversationScopeCapability",
    "ResidentConversationRequestJournalAuthority",
    "VerifiedConversationScopeAuthority",
    "consume_and_verify_record_with_scope_authority",
    "consume_conversation_scope_capability",
    "consume_resident_conversation_request_journal_authority",
    "consume_verified_scope_authority_for_scope_creation",
    "consume_verified_scope_authority_for_request_journal",
    "conversation_scope_authority_view", "discard_conversation_scope_capability",
    "resident_conversation_request_journal_authority_matches",
    "split_foundup_conversation_scope_capability_pair",
    "split_conversation_scope_capability",
    "sign_record_with_scope_authority", "verify_record_with_scope_authority",
]
