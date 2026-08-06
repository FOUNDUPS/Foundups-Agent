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
from modules.communication.moltbot_bridge.src.reddog_conversation_session_credential import (
    VerifiedConversationSessionCredential,
    verify_conversation_session_credential,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_scope_signing import (
    CONVERSATION_SCOPE_AUTH_SCHEME,
    ConversationScopeSigningContext,
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
        for value in (session_token, transport, session_binding)
    ) or not isinstance(principal_provider, str):
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
    provider = principal_provider.strip()
    try:
        if provider:
            record = principal_resolver.resolve(principal_id, provider)
        else:
            resolve_unique = getattr(principal_resolver, "resolve_unique", None)
            record = resolve_unique(principal_id) if callable(resolve_unique) else None
            provider = record.principal_provider if record is not None else ""
    except Exception:
        return None
    if not _valid_principal(record, principal_id, provider):
        return None
    assert record is not None
    return _issue_conversation_scope_capability(
        _authority_seal(record, secrets, provider, principal_id, transport, session_binding, now_epoch)
    )


def authenticate_signed_conversation_scope(
    *,
    serialized_credential: str,
    transport: str,
    session_binding: str,
    expected_repo_full_name: str,
    principal_resolver: PrincipalAuthorityResolver,
    now_epoch: int,
    record_signing_context: ConversationScopeSigningContext | None = None,
) -> tuple[
    AuthenticatedConversationScopeCapability,
    VerifiedConversationSessionCredential,
] | None:
    """Verify a principal-signed session credential using public material only."""

    if not all(
        isinstance(value, str) and value.strip()
        for value in (serialized_credential, transport, session_binding, expected_repo_full_name)
    ):
        return None
    verified = verify_conversation_session_credential(
        serialized_credential,
        principal_resolver=principal_resolver,
        expected_repo_full_name=expected_repo_full_name,
        expected_transport=transport,
        now_epoch=int(now_epoch),
    )
    if verified is None:
        return None
    if (
        record_signing_context is not None
        and record_signing_context.serialized_session_credential
        != serialized_credential
    ):
        return None
    seal = _authority_seal(
        verified.principal_record,
        (),
        verified.principal_provider,
        verified.principal_id,
        transport,
        session_binding,
        now_epoch,
        foundup_scope=verified.foundup_scope,
        record_auth_scheme=CONVERSATION_SCOPE_AUTH_SCHEME,
        credential_id=verified.credential_id,
        session_id=verified.session_id,
        repo_full_name=verified.repo_full_name,
        record_signing_context=record_signing_context,
    )
    return _issue_conversation_scope_capability(seal), verified


def _authority_seal(
    record: PrincipalAuthorityRecord,
    secrets: tuple[bytes, ...],
    principal_provider: str,
    principal_id: str,
    transport: str,
    session_binding: str,
    now_epoch: int,
    foundup_scope: tuple[str, ...] | None = None,
    record_auth_scheme: str = "hmac-sha256-v1",
    credential_id: str = "",
    session_id: str = "",
    repo_full_name: str = "",
    record_signing_context: ConversationScopeSigningContext | None = None,
) -> _ConversationScopeAuthoritySeal:
    sign_key = (
        derive_conversation_scope_mac_key(
            secrets[0], principal_provider, principal_id
        )
        if secrets
        else b""
    )
    return _ConversationScopeAuthoritySeal(
        principal_id=record.principal_id,
        principal_provider=record.principal_provider,
        verified_subject_digest=record.verified_subject_digest,
        principal_record_digest=canonical_digest(record.to_dict()),
        principal_key_fingerprint=canonical_digest(
            {"principal_public_key": record.principal_public_key}
        ),
        foundup_scope=tuple(dict.fromkeys(foundup_scope or record.foundup_scope)),
        transport=transport.strip(),
        session_binding_digest=canonical_digest(
            {"transport": transport.strip(), "session_binding": session_binding.strip()}
        ),
        expires_at=int(now_epoch) + CAPABILITY_TTL_SECONDS,
        record_sign_key=sign_key,
        record_verify_keys=tuple(
            derive_conversation_scope_mac_key(secret, principal_provider, principal_id)
            for secret in secrets
        ),
        record_auth_scheme=record_auth_scheme,
        credential_id=credential_id,
        session_id=session_id,
        repo_full_name=repo_full_name,
        record_signing_context=record_signing_context,
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


__all__ = [
    "AuthenticatedConversationScopeCapability",
    "authenticate_conversation_scope",
    "authenticate_signed_conversation_scope",
]
