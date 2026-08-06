"""Client verification for E0 conversation-scope state signatures."""

from __future__ import annotations

from typing import Any, Mapping

from modules.communication.moltbot_bridge.src.reddog_conversation_scope_signing_contract import (
    AUTH_RESPONSE_FIELDS,
    AUTH_SCHEME as CONVERSATION_SCOPE_AUTH_SCHEME,
    MAX_SIGNING_INPUT_BYTES,
    MIN_SOCKET_REQUEST_BYTES,
    RECOVERY_SIGNING_OPERATION as CONVERSATION_SCOPE_RECOVERY_SIGNING_OPERATION,
    SCHEMA_VERSION as CONVERSATION_SCOPE_SIGNING_SCHEMA_VERSION,
    SIGNING_OPERATION as CONVERSATION_SCOPE_SIGNING_OPERATION,
    SIGNING_PREFIX as CONVERSATION_SCOPE_SIGNING_PREFIX,
    ConversationScopeSignerPolicy,
    ConversationScopeSigningContext,
    build_conversation_scope_signing_request,
    canonical_conversation_scope_signing_input,
    unsigned_conversation_scope_record,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_scope_signing_validation import (
    validate_conversation_scope_signing_request,
)
from modules.communication.moltbot_bridge.src.reddog_ed25519_signature_verifier_backend import (
    Ed25519SignatureVerifier,
)
from modules.communication.moltbot_bridge.src.reddog_signer_audit_attestation import (
    CONVERSATION_SCOPE_AUDIT_ATTESTATION_PREFIX,
    canonical_signer_audit_attestation_input,
)
from modules.communication.moltbot_bridge.src.reddog_signer_delegated_authority_runtime import (
    SigningRequest,
    SigningResponse,
    public_key_fingerprint,
)


def sign_conversation_scope_record(
    context: ConversationScopeSigningContext,
    record: Mapping[str, Any],
    *,
    require_replay: bool = False,
) -> dict[str, Any] | None:
    request = build_conversation_scope_signing_request(
        context, record, require_replay=require_replay
    )
    if request is None:
        return None
    try:
        response = context.signer.sign(request)
    except Exception:
        return None
    if not _response_valid(response, request, context):
        return None
    return {
        "record_auth_signature": response.signature,
        "record_auth_signer_public_key": response.signer_public_key,
        "record_auth_key_fingerprint": response.key_fingerprint,
        "record_auth_key_epoch": response.key_epoch,
        "record_auth_audit_mac": response.audit_mac,
        "record_auth_audit_attestation_signature": response.audit_attestation_signature,
    }


def verify_signed_conversation_scope_record(
    context: ConversationScopeSigningContext, record: Mapping[str, Any]
) -> bool:
    request = build_conversation_scope_signing_request(context, record)
    if request is None:
        return False
    public_key = str(record.get("record_auth_signer_public_key") or "")
    signature = str(record.get("record_auth_signature") or "")
    return bool(
        record.get("record_auth_scheme") == CONVERSATION_SCOPE_AUTH_SCHEME
        and public_key == context.signer_public_key
        and record.get("record_auth_key_epoch") == context.key_epoch
        and record.get("record_auth_key_fingerprint")
        == public_key_fingerprint(public_key)
        and signature
        and Ed25519SignatureVerifier().verify(public_key, request.signing_input, signature)
        is True
        and _audit_attestation_valid(
            request, signature, str(record.get("record_auth_audit_mac") or ""),
            str(record.get("record_auth_audit_attestation_signature") or ""),
        )
    )


def _response_valid(
    response: SigningResponse,
    request: SigningRequest,
    context: ConversationScopeSigningContext,
) -> bool:
    return bool(
        type(response) is SigningResponse
        and response.accepted is True
        and response.signer_public_key == context.signer_public_key
        and response.key_epoch == context.key_epoch
        and response.key_fingerprint == public_key_fingerprint(context.signer_public_key)
        and response.boundary_attested is True
        and response.requester_identity_attested is True
        and response.signer_loads_no_untrusted_code is True
        and response.no_secret_material_returned is True
        and response.audit_mac
        and response.audit_attestation_signature
        and Ed25519SignatureVerifier().verify(
            context.signer_public_key, request.signing_input, response.signature
        )
        is True
        and _audit_attestation_valid(
            request, response.signature, response.audit_mac,
            response.audit_attestation_signature,
        )
    )


def _audit_attestation_valid(
    request: SigningRequest,
    signature: str,
    audit_mac: str,
    audit_attestation_signature: str,
) -> bool:
    try:
        value = canonical_signer_audit_attestation_input(
            signing_input=request.signing_input,
            signature=signature,
            audit_mac=audit_mac,
            signer_public_key=request.signer_public_key,
            key_epoch=request.key_epoch,
            requester_principal_id=request.requester_principal_id,
            domain_prefix=CONVERSATION_SCOPE_AUDIT_ATTESTATION_PREFIX,
        )
        return Ed25519SignatureVerifier().verify(
            request.signer_public_key, value, audit_attestation_signature
        ) is True
    except Exception:
        return False


__all__ = [
    "AUTH_RESPONSE_FIELDS", "CONVERSATION_SCOPE_AUDIT_ATTESTATION_PREFIX",
    "CONVERSATION_SCOPE_AUTH_SCHEME", "CONVERSATION_SCOPE_SIGNING_OPERATION",
    "CONVERSATION_SCOPE_RECOVERY_SIGNING_OPERATION",
    "CONVERSATION_SCOPE_SIGNING_PREFIX", "ConversationScopeSignerPolicy",
    "ConversationScopeSigningContext", "MAX_SIGNING_INPUT_BYTES",
    "MIN_SOCKET_REQUEST_BYTES",
    "build_conversation_scope_signing_request",
    "canonical_conversation_scope_signing_input", "sign_conversation_scope_record",
    "unsigned_conversation_scope_record", "validate_conversation_scope_signing_request",
    "verify_signed_conversation_scope_record",
]
