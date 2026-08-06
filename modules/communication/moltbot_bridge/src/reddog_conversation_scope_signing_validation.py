"""Signer-side validation for E0 conversation-scope requests."""

from __future__ import annotations

from typing import Any, Mapping

from modules.communication.moltbot_bridge.src.reddog_authority_runtime_store import (
    PrincipalAuthorityResolver,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_scope_contract import (
    validate_unsigned_record,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_scope_digest import (
    canonical_digest,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_scope_signing_contract import (
    SHA256_RE,
    ConversationScopeSignerPolicy,
    decode_conversation_scope_signing_input,
    signing_input_digest,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_session_credential import (
    VerifiedConversationSessionCredential,
    verify_conversation_session_credential,
)
from modules.communication.moltbot_bridge.src.reddog_signer_delegated_authority_runtime import (
    SigningRequest,
)


def validate_conversation_scope_signing_request(
    request: SigningRequest,
    policy: ConversationScopeSignerPolicy,
    resolver: PrincipalAuthorityResolver,
    *,
    now_epoch: int,
) -> dict[str, Any] | None:
    decoded = decode_conversation_scope_signing_input(request.signing_input)
    if decoded is None:
        return None
    record, serialized = decoded
    if validate_unsigned_record(record):
        return None
    credential = verify_conversation_session_credential(
        serialized,
        principal_resolver=resolver,
        expected_repo_full_name=policy.repo_full_name,
        expected_transport=str(record.get("transport") or ""),
        now_epoch=int(now_epoch),
    )
    if credential is None or not _request_matches(
        request, policy, record, credential, now_epoch
    ):
        return None
    return {
        "conversation_id": str(record["conversation_id"]),
        "conversation_revision": int(record["conversation_revision"]),
        "previous_record_auth_signature_digest": str(
            record["previous_record_auth_signature_digest"]
        ),
        "record_state_digest": canonical_digest(record),
        "record_auth_nonce": str(record["record_auth_nonce"]),
        "credential_id": credential.credential_id,
        "principal_id": credential.principal_id,
        "principal_provider": credential.principal_provider,
        "repo_full_name": credential.repo_full_name,
        "session_id": credential.session_id,
    }


def _request_matches(
    request: SigningRequest,
    policy: ConversationScopeSignerPolicy,
    record: Mapping[str, Any],
    credential: VerifiedConversationSessionCredential,
    now_epoch: int,
) -> bool:
    try:
        scope = set(credential.foundup_scope)
        discussions = set(map(str, record["discussion_foundup_ids"]))
        updated_at = int(record["updated_at"])
        expires_at = int(record["expires_at"])
        bindings = (
            record.get("schema_version") == "reddog_authenticated_conversation_scope.v2",
            record.get("record_auth_scheme") == "ed25519-e0-v1",
            record.get("credential_id") == credential.credential_id,
            record.get("session_id") == credential.session_id,
            record.get("repo_full_name") == credential.repo_full_name,
            record.get("principal_id") == credential.principal_id,
            record.get("principal_provider") == credential.principal_provider,
            record.get("authorized_foundup_id") in scope,
            bool(discussions) and discussions.issubset(scope),
            request.requester_principal_id == credential.principal_id,
            request.signer_public_key == policy.signer_public_key,
            request.key_epoch == policy.key_epoch,
            request.nonce == record.get("record_auth_nonce"),
            request.authority_tier == "NONE",
            request.consensus_receipt_digest is None,
            request.payload_digest == signing_input_digest(request.signing_input),
            credential.principal_id == policy.issuer_principal_id,
            credential.principal_provider == policy.issuer_principal_provider,
            credential.repo_full_name == policy.repo_full_name,
            updated_at <= int(now_epoch) < expires_at <= credential.expires_at,
            0 < expires_at - updated_at <= int(policy.max_scope_ttl_seconds),
            SHA256_RE.fullmatch(str(record.get("conversation_id") or "")),
            SHA256_RE.fullmatch(str(record.get("record_auth_nonce") or "")),
        )
    except (KeyError, TypeError, ValueError):
        return False
    return all(bindings)


__all__ = ["validate_conversation_scope_signing_request"]
