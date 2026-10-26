"""Conversation-scope domain adapter for the isolated Ed25519 signer."""

from __future__ import annotations

from typing import Any, Callable, Mapping, Protocol

from modules.communication.moltbot_bridge.src.reddog_authority_runtime_store import (
    PrincipalAuthorityResolver,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_scope_signing import (
    CONVERSATION_SCOPE_AUDIT_ATTESTATION_PREFIX,
    CONVERSATION_SCOPE_RECOVERY_SIGNING_OPERATION,
    CONVERSATION_SCOPE_SIGNING_OPERATION,
    CONVERSATION_SCOPE_SIGNING_PREFIX,
    ConversationScopeSignerPolicy,
    validate_conversation_scope_signing_request,
)
from modules.communication.moltbot_bridge.src.reddog_ed25519_signature_verifier_backend import (
    Ed25519SignatureVerifier,
)
from modules.communication.moltbot_bridge.src.reddog_signer_audit_attestation import (
    canonical_signer_audit_attestation_input,
)
from modules.communication.moltbot_bridge.src.reddog_signer_conversation_scope_anchor import (
    ConversationScopeAnchorStore,
)
from modules.communication.moltbot_bridge.src.reddog_signer_delegated_authority_runtime import (
    SigningRequest,
    SigningResponse,
    public_key_fingerprint,
)


REJECT_ED25519_SIGNER_CONVERSATION_POLICY_MISSING = (
    "REJECT_ED25519_SIGNER_CONVERSATION_POLICY_MISSING"
)
REJECT_ED25519_SIGNER_CONVERSATION_RESOLVER_MISSING = (
    "REJECT_ED25519_SIGNER_CONVERSATION_RESOLVER_MISSING"
)
REJECT_ED25519_SIGNER_CONVERSATION_ANCHOR_MISSING = (
    "REJECT_ED25519_SIGNER_CONVERSATION_ANCHOR_MISSING"
)
REJECT_ED25519_SIGNER_CONVERSATION_REJECTED = (
    "REJECT_ED25519_SIGNER_CONVERSATION_REJECTED"
)
CONVERSATION_SCOPE_SIGNING_OPERATIONS = frozenset(
    {
        CONVERSATION_SCOPE_SIGNING_OPERATION,
        CONVERSATION_SCOPE_RECOVERY_SIGNING_OPERATION,
    }
)


class ConversationSignerBackend(Protocol):
    """Minimum signer surface needed by the conversation domain."""

    public_key: str
    key_epoch: str
    proposal_clock: Callable[[], float]
    conversation_scope_signer_policy: ConversationScopeSignerPolicy | None
    conversation_scope_principal_resolver: PrincipalAuthorityResolver | None
    conversation_scope_anchor_store: ConversationScopeAnchorStore | None


def conversation_signing_configured(backend: ConversationSignerBackend) -> bool:
    return backend.conversation_scope_signer_policy is not None


def conversation_signing_domain_pair(request: SigningRequest) -> tuple[bool, bool]:
    return (
        request.requested_operation in CONVERSATION_SCOPE_SIGNING_OPERATIONS,
        request.signing_input.startswith(CONVERSATION_SCOPE_SIGNING_PREFIX),
    )


def prepare_conversation_signing(
    backend: ConversationSignerBackend,
    request: SigningRequest,
) -> tuple[dict[str, Any] | None, Any, str]:
    if request.requested_operation not in CONVERSATION_SCOPE_SIGNING_OPERATIONS:
        return None, None, ""
    if backend.conversation_scope_signer_policy is None:
        return None, None, REJECT_ED25519_SIGNER_CONVERSATION_POLICY_MISSING
    if backend.conversation_scope_principal_resolver is None:
        return None, None, REJECT_ED25519_SIGNER_CONVERSATION_RESOLVER_MISSING
    if backend.conversation_scope_anchor_store is None:
        return None, None, REJECT_ED25519_SIGNER_CONVERSATION_ANCHOR_MISSING
    payload = validate_conversation_scope_signing_request(
        request,
        backend.conversation_scope_signer_policy,
        backend.conversation_scope_principal_resolver,
        now_epoch=int(backend.proposal_clock()),
    )
    if payload is None:
        return None, None, REJECT_ED25519_SIGNER_CONVERSATION_REJECTED
    try:
        preparation = backend.conversation_scope_anchor_store.prepare(payload)
    except Exception:
        return None, None, REJECT_ED25519_SIGNER_CONVERSATION_REJECTED
    if (
        request.requested_operation == CONVERSATION_SCOPE_RECOVERY_SIGNING_OPERATION
        and preparation.replay_response is None
    ):
        return None, None, REJECT_ED25519_SIGNER_CONVERSATION_REJECTED
    return payload, preparation, ""


def conversation_replay_response(
    backend: ConversationSignerBackend,
    request: SigningRequest,
    preparation: Any,
) -> tuple[SigningResponse | None, str]:
    if request.requested_operation not in CONVERSATION_SCOPE_SIGNING_OPERATIONS:
        return None, ""
    if preparation is None or preparation.replay_response is None:
        return None, ""
    try:
        response = SigningResponse(**dict(preparation.replay_response))
        audit_input = canonical_signer_audit_attestation_input(
            signing_input=request.signing_input,
            signature=response.signature,
            audit_mac=response.audit_mac,
            signer_public_key=backend.public_key,
            key_epoch=backend.key_epoch,
            requester_principal_id=request.requester_principal_id,
            domain_prefix=CONVERSATION_SCOPE_AUDIT_ATTESTATION_PREFIX,
        )
        verifier = Ed25519SignatureVerifier()
        valid = (
            response.accepted is True
            and not response.rejection_code
            and response.signer_public_key == backend.public_key
            and response.key_epoch == backend.key_epoch
            and response.key_fingerprint == public_key_fingerprint(backend.public_key)
            and response.boundary_attested is True
            and response.requester_identity_attested is True
            and response.signer_loads_no_untrusted_code is True
            and response.no_secret_material_returned is True
            and bool(response.audit_mac)
            and verifier.verify(
                backend.public_key, request.signing_input, response.signature
            )
            is True
            and verifier.verify(
                backend.public_key,
                audit_input,
                response.audit_attestation_signature,
            )
            is True
        )
    except Exception:
        valid = False
        response = None
    if not valid or response is None:
        return None, REJECT_ED25519_SIGNER_CONVERSATION_REJECTED
    return response, ""


def commit_conversation_signing(
    backend: ConversationSignerBackend,
    response: SigningResponse,
    payload: Mapping[str, Any] | None,
    preparation: Any,
) -> str:
    if payload is None or preparation is None:
        return ""
    try:
        if backend.conversation_scope_anchor_store is None:
            raise ValueError("conversation anchor missing")
        backend.conversation_scope_anchor_store.commit(
            payload,
            response.to_dict(),
            expected_revision=preparation.expected_revision,
        )
    except Exception:
        return REJECT_ED25519_SIGNER_CONVERSATION_REJECTED
    return ""


__all__ = [
    "CONVERSATION_SCOPE_AUDIT_ATTESTATION_PREFIX",
    "CONVERSATION_SCOPE_RECOVERY_SIGNING_OPERATION",
    "CONVERSATION_SCOPE_SIGNING_OPERATION",
    "CONVERSATION_SCOPE_SIGNING_OPERATIONS",
    "ConversationScopeAnchorStore",
    "ConversationScopeSignerPolicy",
    "PrincipalAuthorityResolver",
    "REJECT_ED25519_SIGNER_CONVERSATION_ANCHOR_MISSING",
    "REJECT_ED25519_SIGNER_CONVERSATION_POLICY_MISSING",
    "REJECT_ED25519_SIGNER_CONVERSATION_REJECTED",
    "REJECT_ED25519_SIGNER_CONVERSATION_RESOLVER_MISSING",
    "commit_conversation_signing",
    "conversation_replay_response",
    "conversation_signing_configured",
    "conversation_signing_domain_pair",
    "prepare_conversation_signing",
]
