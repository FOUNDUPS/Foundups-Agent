"""Authenticate RedDog conversation scope against signed session identity."""

from __future__ import annotations

import re
from typing import Callable

from modules.ai_intelligence.ai_overseer.src.foundup_genesis.intake_auth_provider import (
    build_intake_context,
    default_secret_provider,
)
from modules.communication.moltbot_bridge.src.reddog_authority_runtime_store import (
    PrincipalAuthorityRecord,
    PrincipalAuthorityResolver,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_scope_capability import (
    AuthenticatedConversationScopeCapability,
    _ConversationScopeAuthoritySeal,
    _issue_conversation_scope_capability,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_scope_contract import (
    canonical_digest,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_scope_mac import (
    derive_conversation_scope_mac_key,
)


CAPABILITY_TTL_SECONDS = 60
SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


def authenticate_conversation_scope(
    *,
    session_token: str,
    principal_provider: str,
    transport: str,
    session_binding: str,
    principal_resolver: PrincipalAuthorityResolver,
    now_epoch: int,
    secret_provider: Callable[[], tuple[str | None, str | None]] | None = None,
) -> AuthenticatedConversationScopeCapability | None:
    """Verify token subject and resolve its current principal authority record."""

    if not all(
        isinstance(value, str) and value.strip()
        for value in (session_token, principal_provider, transport, session_binding)
    ):
        return None
    try:
        current, previous = (secret_provider or default_secret_provider)()
    except Exception:
        return None
    if not current:
        return None
    secrets = tuple(
        dict.fromkeys(str(value).encode("utf-8") for value in (current, previous) if value)
    )
    context = build_intake_context(
        session_token,
        None,
        now=now_epoch,
        secret_provider=lambda: (current, previous),
    )
    principal_id = str(context.requester_handle or "")
    if context.authenticated is not True or not principal_id:
        return None
    try:
        record = principal_resolver.resolve(principal_id, principal_provider)
    except Exception:
        return None
    if not _valid_principal(record, principal_id, principal_provider):
        return None
    assert record is not None
    return _issue_conversation_scope_capability(
        _authority_seal(record, secrets, principal_provider, principal_id, transport, session_binding, now_epoch)
    )


def _authority_seal(
    record: PrincipalAuthorityRecord,
    secrets: tuple[bytes, ...],
    principal_provider: str,
    principal_id: str,
    transport: str,
    session_binding: str,
    now_epoch: int,
) -> _ConversationScopeAuthoritySeal:
    return _ConversationScopeAuthoritySeal(
        principal_id=record.principal_id,
        principal_provider=record.principal_provider,
        verified_subject_digest=record.verified_subject_digest,
        principal_record_digest=canonical_digest(record.to_dict()),
        principal_key_fingerprint=canonical_digest(
            {"principal_public_key": record.principal_public_key}
        ),
        foundup_scope=tuple(dict.fromkeys(record.foundup_scope)),
        transport=transport.strip(),
        session_binding_digest=canonical_digest(
            {"transport": transport.strip(), "session_binding": session_binding.strip()}
        ),
        expires_at=int(now_epoch) + CAPABILITY_TTL_SECONDS,
        record_sign_key=derive_conversation_scope_mac_key(
            secrets[0], principal_provider, principal_id
        ),
        record_verify_keys=tuple(
            derive_conversation_scope_mac_key(secret, principal_provider, principal_id)
            for secret in secrets
        ),
    )


def _valid_principal(
    record: PrincipalAuthorityRecord | None,
    principal_id: str,
    principal_provider: str,
) -> bool:
    return bool(
        type(record) is PrincipalAuthorityRecord
        and record.principal_id == principal_id
        and record.principal_provider == principal_provider
        and record.principal_public_key
        and SHA256_RE.fullmatch(record.verified_subject_digest)
        and record.foundup_scope
    )


__all__ = ["AuthenticatedConversationScopeCapability", "authenticate_conversation_scope"]
