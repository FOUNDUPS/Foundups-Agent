"""Opaque one-use capabilities for authenticated RedDog conversation scope."""

from __future__ import annotations

import threading
from dataclasses import dataclass
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


class AuthenticatedConversationScopeCapability(_OpaqueCapability):
    """One-use authenticated session and principal proof."""


class VerifiedConversationScopeAuthority(_OpaqueCapability):
    """Consumed operation-local authority that never exposes MAC keys."""


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


_LOCK = threading.Lock()
_CAPABILITIES: WeakKeyDictionary[AuthenticatedConversationScopeCapability, _ConversationScopeAuthoritySeal] = WeakKeyDictionary()
_AUTHORITIES: WeakKeyDictionary[VerifiedConversationScopeAuthority, _ConversationScopeAuthoritySeal] = WeakKeyDictionary()


def _issue_conversation_scope_capability(
    seal: _ConversationScopeAuthoritySeal,
) -> AuthenticatedConversationScopeCapability:
    capability = object.__new__(AuthenticatedConversationScopeCapability)
    with _LOCK:
        _CAPABILITIES[capability] = seal
    return capability


def consume_conversation_scope_capability(
    capability: Any,
    *,
    active_foundup_id: str,
    discussion_foundup_ids: tuple[str, ...],
    now_epoch: int,
) -> VerifiedConversationScopeAuthority | None:
    if type(capability) is not AuthenticatedConversationScopeCapability:
        return None
    with _LOCK:
        seal = _CAPABILITIES.pop(capability, None)
    allowed = set(seal.foundup_scope) if seal is not None else set()
    requested = set(discussion_foundup_ids)
    if (
        seal is None or int(now_epoch) >= seal.expires_at or not active_foundup_id
        or active_foundup_id not in requested or not requested
        or not requested.issubset(allowed)
    ):
        return None
    authority = object.__new__(VerifiedConversationScopeAuthority)
    with _LOCK:
        _AUTHORITIES[authority] = seal
    return authority


def conversation_scope_authority_view(authority: Any) -> Mapping[str, Any] | None:
    seal = _authority_seal(authority)
    if seal is None:
        return None
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
    }


def sign_record_with_scope_authority(
    authority: Any,
    record: Mapping[str, Any],
    *,
    require_replay: bool = False,
) -> Mapping[str, Any] | None:
    seal = _authority_seal(authority)
    if seal is None:
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
    if seal is None or record.get("record_auth_scheme") != seal.record_auth_scheme:
        return False
    if seal.record_auth_scheme == CONVERSATION_SCOPE_AUTH_SCHEME:
        return bool(seal.record_signing_context) and verify_signed_conversation_scope_record(
            seal.record_signing_context, record
        )
    return verify_hmac_conversation_scope_record(record, seal.record_verify_keys)


def discard_conversation_scope_capability(capability: Any) -> None:
    with _LOCK:
        if type(capability) is AuthenticatedConversationScopeCapability:
            _CAPABILITIES.pop(capability, None)
        elif type(capability) is VerifiedConversationScopeAuthority:
            _AUTHORITIES.pop(capability, None)


def _authority_seal(authority: Any) -> _ConversationScopeAuthoritySeal | None:
    if type(authority) is not VerifiedConversationScopeAuthority:
        return None
    with _LOCK:
        return _AUTHORITIES.get(authority)


__all__ = [
    "AuthenticatedConversationScopeCapability", "VerifiedConversationScopeAuthority",
    "consume_conversation_scope_capability",
    "conversation_scope_authority_view", "discard_conversation_scope_capability",
    "sign_record_with_scope_authority", "verify_record_with_scope_authority",
]
