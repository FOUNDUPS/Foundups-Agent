"""Ed25519 signer backend for the isolated RedDog signer process.

Slice: REDDOG_ED25519_SIGNER_BACKEND_PHASE1

This module signs ``SigningRequest`` records using an already-held Ed25519 key
object supplied by the isolated signer process. It does not generate keys, load
keys from disk, read vault secrets, inspect environment variables, bind sockets,
spawn processes, execute shell commands, mutate repository files, enqueue
OpenClaw, dispatch Hermes, or re-index HoloIndex.

The backend requires an injected audit-MAC builder. If the key object, public
key binding, key epoch, or audit-MAC boundary is missing, it rejects fail-closed.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Protocol

from modules.communication.moltbot_bridge.src.reddog_signer_control_loop_anchor import (
    ControlLoopAnchorStore,
)
from modules.communication.moltbot_bridge.src.reddog_ed25519_signature_verifier_backend import (
    encode_ed25519_public_key,
    encode_ed25519_signature,
)
from modules.communication.moltbot_bridge.src.reddog_isolated_signer_socket_protocol import (
    IsolatedSignerBackend,
    SignerPeerAttestation,
)
from modules.communication.moltbot_bridge.src.reddog_signer_delegated_authority_runtime import (
    SigningRequest,
    SigningResponse,
    public_key_fingerprint,
)
from modules.communication.moltbot_bridge.src.reddog_ed25519_signer_policy_gate import (
    REJECT_ED25519_SIGNER_EXACT_REQUEST_MISMATCH,
    REJECT_ED25519_SIGNER_POLICY_MISSING,
    bind_exact_signing_request,
    signer_policy_rejection,
)
from modules.communication.moltbot_bridge.src.reddog_architect_proposal_authenticity import (
    ArchitectProposalSignerPolicy,
    PROPOSAL_AUTHENTICITY_SIGNING_OPERATION,
    ProposalAuthenticityNonceStore,
    validate_proposal_signing_request,
)
from modules.communication.moltbot_bridge.src.reddog_signed_runtime_artifact_manifest import (
    RUNTIME_ARTIFACT_MANIFEST_SIGNING_OPERATION,
    RuntimeArtifactManifestAuthority,
    validate_runtime_artifact_manifest_signing_request,
)
from modules.communication.moltbot_bridge.src.reddog_runtime_artifact_manifest_authority import (
    RuntimeArtifactManifestAuthorityBoundary,
)
from modules.communication.moltbot_bridge.src.reddog_signer_audit_attestation import (
    AUTHORITATIVE_USE_LEASE_AUDIT_ATTESTATION_PREFIX,
    RUNTIME_ARTIFACT_MANIFEST_AUDIT_ATTESTATION_PREFIX,
    canonical_signer_audit_attestation_input,
)
from modules.communication.moltbot_bridge.src.reddog_authoritative_use_lease_contract import (
    AUTHORITATIVE_USE_LEASE_SIGNING_OPERATION,
    digest_text,
    validate_authoritative_use_lease_request,
)
from modules.communication.moltbot_bridge.src.reddog_signer_secret_grant_authority_policy import (
    SECRET_GRANT_SIGNING_OPERATION,
    SignerSecretGrantAuthorityPolicy,
)
from modules.communication.moltbot_bridge.src.reddog_signer_secret_grant_durable_rate_authority import (
    DurableSignerSecretGrantRateAuthority,
)
from modules.communication.moltbot_bridge.src.reddog_signer_secret_grant_signer_admission import (
    secret_grant_signer_rejection,
)
from modules.communication.moltbot_bridge.src.reddog_signer_audit_attestation import (
    SECRET_GRANT_AUDIT_ATTESTATION_PREFIX,
)
from modules.communication.moltbot_bridge.src import reddog_signer_mutual_peer_handshake as peer_handshake
from modules.communication.moltbot_bridge.src.reddog_ed25519_signer_validation import (
    CONTROL_LOOP_SIGNING_OPERATION,
    CONTROL_LOOP_SIGNING_PREFIX,
    ControlLoopAuthorityPolicy,
    assert_ascii_deep as _assert_ascii_deep,
    canonical_control_audit_attestation_input,
    control_authority_policy_matches,
    is_ascii as _is_ascii,
    public_bytes_from_private_key as _public_bytes_from_private_key,
    signing_domain_pairs,
    valid_control_receipt_signing_payload,
)
from modules.communication.moltbot_bridge.src.foundup_memex_verified_outcome_signing import (
    VERIFIED_OUTCOME_AUDIT_ATTESTATION_PREFIX,
    VERIFIED_OUTCOME_SIGNING_OPERATION,
    VerifiedOutcomeSigningAuthority,
    VerifiedOutcomeSignerPolicy,
)
from modules.communication.moltbot_bridge.src.reddog_ed25519_verified_outcome_signing import (
    REJECT_ED25519_SIGNER_OUTCOME_AUTHORITY_MISSING,
    REJECT_ED25519_SIGNER_OUTCOME_AUTHORITY_REJECTED,
    commit_outcome_reservation as _commit_outcome_reservation,
    prepare_verified_outcome_signing,
    rollback_outcome_reservation as _rollback_outcome_reservation,
)
from modules.communication.moltbot_bridge.src.reddog_ed25519_conversation_scope_backend import (
    CONVERSATION_SCOPE_AUDIT_ATTESTATION_PREFIX,
    CONVERSATION_SCOPE_RECOVERY_SIGNING_OPERATION,
    CONVERSATION_SCOPE_SIGNING_OPERATION,
    ConversationScopeSignerPolicy,
    PrincipalAuthorityResolver,
    ConversationScopeAnchorStore,
    REJECT_ED25519_SIGNER_CONVERSATION_ANCHOR_MISSING,
    REJECT_ED25519_SIGNER_CONVERSATION_POLICY_MISSING,
    REJECT_ED25519_SIGNER_CONVERSATION_REJECTED,
    REJECT_ED25519_SIGNER_CONVERSATION_RESOLVER_MISSING,
    commit_conversation_signing,
    conversation_replay_response,
    prepare_conversation_signing,
)


REJECT_ED25519_SIGNER_REQUEST_INVALID = "REJECT_ED25519_SIGNER_REQUEST_INVALID"
REJECT_ED25519_SIGNER_KEY_INVALID = "REJECT_ED25519_SIGNER_KEY_INVALID"
REJECT_ED25519_SIGNER_PUBLIC_KEY_MISMATCH = "REJECT_ED25519_SIGNER_PUBLIC_KEY_MISMATCH"
REJECT_ED25519_SIGNER_KEY_EPOCH_MISMATCH = "REJECT_ED25519_SIGNER_KEY_EPOCH_MISMATCH"
REJECT_ED25519_SIGNER_AUDIT_MAC_MISSING = "REJECT_ED25519_SIGNER_AUDIT_MAC_MISSING"
REJECT_ED25519_SIGNER_DOMAIN_MISMATCH = "REJECT_ED25519_SIGNER_DOMAIN_MISMATCH"
REJECT_ED25519_SIGNER_SIGN_FAILED = "REJECT_ED25519_SIGNER_SIGN_FAILED"
REJECT_ED25519_SIGNER_CONTROL_ANCHOR_MISSING = (
    "REJECT_ED25519_SIGNER_CONTROL_ANCHOR_MISSING"
)
REJECT_ED25519_SIGNER_CONTROL_ANCHOR_REJECTED = (
    "REJECT_ED25519_SIGNER_CONTROL_ANCHOR_REJECTED"
)
REJECT_ED25519_SIGNER_CONTROL_AUTHORITY_POLICY_MISSING = (
    "REJECT_ED25519_SIGNER_CONTROL_AUTHORITY_POLICY_MISSING"
)
REJECT_ED25519_SIGNER_CONTROL_AUTHORITY_POLICY_MISMATCH = (
    "REJECT_ED25519_SIGNER_CONTROL_AUTHORITY_POLICY_MISMATCH"
)
REJECT_ED25519_SIGNER_PROPOSAL_AUTHORITY_POLICY_MISSING = (
    "REJECT_ED25519_SIGNER_PROPOSAL_AUTHORITY_POLICY_MISSING"
)
REJECT_ED25519_SIGNER_PROPOSAL_AUTHORITY_POLICY_MISMATCH = (
    "REJECT_ED25519_SIGNER_PROPOSAL_AUTHORITY_POLICY_MISMATCH"
)
REJECT_ED25519_SIGNER_PROPOSAL_NONCE_STORE_MISSING = (
    "REJECT_ED25519_SIGNER_PROPOSAL_NONCE_STORE_MISSING"
)
REJECT_ED25519_SIGNER_PROPOSAL_NONCE_REPLAY = (
    "REJECT_ED25519_SIGNER_PROPOSAL_NONCE_REPLAY"
)
REJECT_ED25519_SIGNER_PROPOSAL_DOMAIN_ONLY = (
    "REJECT_ED25519_SIGNER_PROPOSAL_DOMAIN_ONLY"
)
REJECT_ED25519_SIGNER_MANIFEST_NONCE_STORE_MISSING = (
    "REJECT_ED25519_SIGNER_MANIFEST_NONCE_STORE_MISSING"
)
REJECT_ED25519_SIGNER_MANIFEST_NONCE_REPLAY = (
    "REJECT_ED25519_SIGNER_MANIFEST_NONCE_REPLAY"
)
CONTROL_LOOP_AUDIT_ATTESTATION_PREFIX = "reddog-control-loop-audit.v1."
class SignerAuditMacBuilder(Protocol):
    """Injected audit-MAC boundary owned by the isolated signer process."""

    def build(self, request: SigningRequest, signature: str, peer: SignerPeerAttestation) -> str:
        """Return a signer-side audit MAC. Empty or non-ASCII values reject."""


@dataclass(frozen=True)
class Ed25519SignerBackend(IsolatedSignerBackend):
    """Sign requests with an already-held Ed25519 private key object."""

    private_key: Any
    public_key: str
    key_epoch: str
    audit_mac_builder: SignerAuditMacBuilder
    control_loop_anchor_store: ControlLoopAnchorStore | None = None
    control_loop_authority_policy: ControlLoopAuthorityPolicy | None = None
    proposal_authority_policy: ArchitectProposalSignerPolicy | None = None
    proposal_nonce_store: ProposalAuthenticityNonceStore | None = None
    proposal_clock: Callable[[], float] = time.time
    runtime_artifact_manifest_authority: (
        RuntimeArtifactManifestAuthority | None
    ) = None
    runtime_artifact_manifest_authority_boundary: (
        RuntimeArtifactManifestAuthorityBoundary | None
    ) = None
    runtime_artifact_manifest_nonce_store: (
        ProposalAuthenticityNonceStore | None
    ) = None
    signer_peer_instance_binding: peer_handshake.SignerPeerInstanceBinding | None = None
    verified_outcome_signer_policy: VerifiedOutcomeSignerPolicy | None = None
    verified_outcome_signing_authority: (
        VerifiedOutcomeSigningAuthority | None
    ) = None
    conversation_scope_signer_policy: ConversationScopeSignerPolicy | None = None
    conversation_scope_principal_resolver: PrincipalAuthorityResolver | None = None
    conversation_scope_anchor_store: ConversationScopeAnchorStore | None = None
    secret_grant_authority_policy: SignerSecretGrantAuthorityPolicy | None = None
    secret_grant_rate_authority: DurableSignerSecretGrantRateAuthority | None = None
    exact_signing_request_digest: str | None = None

    def sign(self, request: SigningRequest, peer: SignerPeerAttestation) -> SigningResponse:
        reason = _signer_request_rejection(self, request, peer)
        if reason:
            return _reject(reason)
        control_payload, preparation, reason = _prepare_control_signing(
            self, request
        )
        if reason:
            return _reject(reason)
        conversation_payload, conversation_preparation, early = (
            _prepare_conversation_or_replay(self, request)
        )
        if early is not None:
            return early
        proposal_reservation, reason = _prepare_proposal_signing(self, request)
        if reason:
            return _reject(reason)
        manifest_payload, manifest_reservation, reason = (
            _prepare_manifest_signing(self, request)
        )
        if reason:
            _rollback_proposal_reservation(self, proposal_reservation)
            return _reject(reason)
        outcome_payload, outcome_reservation, rejection = _prepare_outcome_or_reject(
            self, request, proposal_reservation, manifest_reservation
        )
        if rejection is not None:
            return rejection
        requires_attestation = _requires_audit_attestation(
            request,
            control_payload,
            manifest_payload,
            outcome_payload,
            conversation_payload,
        )
        response, reason = _sign_response(self, request, peer, requires_attestation)
        if reason:
            _rollback_proposal_reservation(self, proposal_reservation)
            _rollback_manifest_reservation(self, manifest_reservation)
            _rollback_outcome_reservation(self, outcome_reservation)
            return _reject(reason)
        return _finalize_signing(
            self,
            response,
            proposal_reservation,
            manifest_reservation,
            outcome_reservation,
            control_payload,
            preparation,
            conversation_payload,
            conversation_preparation,
        )


def _prepare_conversation_or_replay(
    backend: Ed25519SignerBackend, request: SigningRequest
) -> tuple[Mapping[str, Any] | None, Any, SigningResponse | None]:
    payload, preparation, reason = prepare_conversation_signing(backend, request)
    if reason:
        return None, preparation, _reject(reason)
    replay, reason = conversation_replay_response(backend, request, preparation)
    return payload, preparation, (_reject(reason) if reason else replay)


def _finalize_signing(
    backend: Ed25519SignerBackend,
    response: SigningResponse,
    proposal_reservation: Any,
    manifest_reservation: Any,
    outcome_reservation: Any,
    control_payload: Mapping[str, Any] | None,
    preparation: Any,
    conversation_payload: Mapping[str, Any] | None,
    conversation_preparation: Any,
) -> SigningResponse:
    if proposal_reservation is not None:
        try:
            assert backend.proposal_nonce_store is not None
            backend.proposal_nonce_store.commit(proposal_reservation)
        except Exception:
            _rollback_proposal_reservation(backend, proposal_reservation)
            _rollback_manifest_reservation(backend, manifest_reservation)
            _rollback_outcome_reservation(backend, outcome_reservation)
            return _reject(REJECT_ED25519_SIGNER_PROPOSAL_NONCE_REPLAY)
    if not _commit_manifest_reservation(backend, manifest_reservation):
        _rollback_outcome_reservation(backend, outcome_reservation)
        return _reject(REJECT_ED25519_SIGNER_MANIFEST_NONCE_REPLAY)
    if not _commit_outcome_reservation(
        backend, outcome_reservation, response.signature
    ):
        return _reject(REJECT_ED25519_SIGNER_OUTCOME_AUTHORITY_REJECTED)
    if control_payload is not None and preparation is not None:
        try:
            backend.control_loop_anchor_store.commit(
                control_payload,
                response.to_dict(),
                expected_revision=preparation.expected_revision,
            )
        except Exception:
            return _reject(REJECT_ED25519_SIGNER_CONTROL_ANCHOR_REJECTED)
    conversation_reason = commit_conversation_signing(
        backend, response, conversation_payload, conversation_preparation
    )
    if conversation_reason:
        return _reject(conversation_reason)
    return response


def _requires_audit_attestation(
    request: SigningRequest, *payloads: Mapping[str, Any] | None
) -> bool:
    return bool(
        request.requested_operation == SECRET_GRANT_SIGNING_OPERATION
        or any(payload is not None for payload in payloads)
    )


def _prepare_outcome_or_reject(
    backend: Ed25519SignerBackend,
    request: SigningRequest,
    proposal_reservation: Any,
    manifest_reservation: Any,
) -> tuple[Mapping[str, Any] | None, Any, SigningResponse | None]:
    payload, reservation, reason = _prepare_verified_outcome_signing(
        backend, request
    )
    if not reason:
        return payload, reservation, None
    _rollback_proposal_reservation(backend, proposal_reservation)
    _rollback_manifest_reservation(backend, manifest_reservation)
    return None, None, _reject(reason)


def _signer_request_rejection(
    backend: Ed25519SignerBackend,
    request: SigningRequest,
    peer: SignerPeerAttestation,
) -> str:
    if not isinstance(request, SigningRequest) or not isinstance(peer, SignerPeerAttestation):
        return REJECT_ED25519_SIGNER_REQUEST_INVALID
    if not _assert_ascii_deep(request.to_dict()) or not _assert_ascii_deep(peer.to_dict()):
        return REJECT_ED25519_SIGNER_REQUEST_INVALID
    if not _is_ascii(backend.public_key) or not _is_ascii(backend.key_epoch):
        return REJECT_ED25519_SIGNER_KEY_INVALID
    if request.signer_public_key != backend.public_key:
        return REJECT_ED25519_SIGNER_PUBLIC_KEY_MISMATCH
    if request.key_epoch != backend.key_epoch:
        return REJECT_ED25519_SIGNER_KEY_EPOCH_MISMATCH
    if not request.signing_input:
        return REJECT_ED25519_SIGNER_REQUEST_INVALID
    domain_pairs = signing_domain_pairs(request)
    if (
        any(operation is not prefix for operation, prefix in domain_pairs)
        or sum(operation and prefix for operation, prefix in domain_pairs) != 1
    ):
        return REJECT_ED25519_SIGNER_DOMAIN_MISMATCH
    policy_reason = (
        signer_policy_rejection(backend, request)
        or _lease_request_rejection(backend, request)
        or secret_grant_signer_rejection(
            backend, request, now_epoch=int(backend.proposal_clock())
        )
    )
    if policy_reason:
        return policy_reason
    if request.requested_operation == peer_handshake.SIGNER_PEER_HANDSHAKE_SIGNING_OPERATION:
        if not peer_handshake.signer_handshake_request_matches_instance(
            request, backend.signer_peer_instance_binding,
            now_epoch=int(backend.proposal_clock()),
        ):
            return REJECT_ED25519_SIGNER_REQUEST_INVALID
    try:
        derived = encode_ed25519_public_key(_public_bytes_from_private_key(backend.private_key))
    except Exception:
        return REJECT_ED25519_SIGNER_KEY_INVALID
    return "" if derived == backend.public_key else REJECT_ED25519_SIGNER_PUBLIC_KEY_MISMATCH


def _lease_request_rejection(
    backend: Ed25519SignerBackend, request: SigningRequest
) -> str:
    if request.requested_operation != AUTHORITATIVE_USE_LEASE_SIGNING_OPERATION:
        return ""
    payload = validate_authoritative_use_lease_request(
        request, now_epoch=int(backend.proposal_clock())
    )
    return (
        ""
        if payload is not None
        and _lease_matches_peer_instance(payload, backend.signer_peer_instance_binding)
        else REJECT_ED25519_SIGNER_REQUEST_INVALID
    )


def _prepare_verified_outcome_signing(
    backend: Ed25519SignerBackend,
    request: SigningRequest,
) -> tuple[dict[str, Any] | None, Any, str]:
    return prepare_verified_outcome_signing(
        backend,
        request,
        domain_mismatch_code=REJECT_ED25519_SIGNER_DOMAIN_MISMATCH,
        request_invalid_code=REJECT_ED25519_SIGNER_REQUEST_INVALID,
    )


def _prepare_manifest_signing(
    backend: Ed25519SignerBackend,
    request: SigningRequest,
) -> tuple[dict[str, Any] | None, str | None, str]:
    if (
        request.requested_operation
        != RUNTIME_ARTIFACT_MANIFEST_SIGNING_OPERATION
    ):
        return None, None, ""
    if (
        backend.runtime_artifact_manifest_authority is None
        or backend.runtime_artifact_manifest_authority_boundary is None
    ):
        return None, None, REJECT_ED25519_SIGNER_DOMAIN_MISMATCH
    payload = validate_runtime_artifact_manifest_signing_request(
        request,
        backend.runtime_artifact_manifest_authority,
        backend.runtime_artifact_manifest_authority_boundary,
        now_epoch=int(backend.proposal_clock()),
    )
    if payload is None:
        return None, None, REJECT_ED25519_SIGNER_REQUEST_INVALID
    store = backend.runtime_artifact_manifest_nonce_store
    if store is None:
        return (
            None,
            None,
            REJECT_ED25519_SIGNER_MANIFEST_NONCE_STORE_MISSING,
        )
    try:
        reservation = store.reserve(
            str(payload["nonce"]),
            expires_at=int(payload["expires_at"]),
            subject=":".join(
                (
                    "runtime-artifact-manifest",
                    public_key_fingerprint(backend.public_key),
                    str(payload["issuer_principal_id"]),
                    str(payload["queue_item_id"]),
                    str(payload["work_state_revision"]),
                )
            ),
        )
    except Exception:
        reservation = None
    if not reservation:
        return None, None, REJECT_ED25519_SIGNER_MANIFEST_NONCE_REPLAY
    return payload, reservation, ""


def _prepare_control_signing(
    backend: Ed25519SignerBackend, request: SigningRequest
) -> tuple[dict[str, Any] | None, Any, str]:
    if request.requested_operation != CONTROL_LOOP_SIGNING_OPERATION:
        return None, None, ""
    payload = _valid_control_receipt_signing_payload(request)
    if payload is None:
        return None, None, REJECT_ED25519_SIGNER_REQUEST_INVALID
    if backend.control_loop_authority_policy is None:
        return None, None, REJECT_ED25519_SIGNER_CONTROL_AUTHORITY_POLICY_MISSING
    if not _control_authority_policy_matches(payload, backend.control_loop_authority_policy):
        return None, None, REJECT_ED25519_SIGNER_CONTROL_AUTHORITY_POLICY_MISMATCH
    if backend.control_loop_anchor_store is None:
        return None, None, REJECT_ED25519_SIGNER_CONTROL_ANCHOR_MISSING
    try:
        preparation = backend.control_loop_anchor_store.prepare(payload)
    except Exception:
        return None, None, REJECT_ED25519_SIGNER_CONTROL_ANCHOR_REJECTED
    return payload, preparation, ""


def _prepare_proposal_signing(
    backend: Ed25519SignerBackend,
    request: SigningRequest,
) -> tuple[str | None, str]:
    if request.requested_operation != PROPOSAL_AUTHENTICITY_SIGNING_OPERATION:
        return None, ""
    if backend.proposal_authority_policy is None:
        return None, REJECT_ED25519_SIGNER_PROPOSAL_AUTHORITY_POLICY_MISSING
    payload = validate_proposal_signing_request(
        request,
        backend.proposal_authority_policy,
        now_epoch=int(backend.proposal_clock()),
    )
    if payload is None:
        return None, REJECT_ED25519_SIGNER_PROPOSAL_AUTHORITY_POLICY_MISMATCH
    if backend.proposal_nonce_store is None:
        return None, REJECT_ED25519_SIGNER_PROPOSAL_NONCE_STORE_MISSING
    try:
        reservation = backend.proposal_nonce_store.reserve(
            str(payload["nonce"]),
            expires_at=int(payload["expires_at"]),
            subject=str(payload["requester_principal_id"]),
        )
    except Exception:
        reservation = None
    if not reservation:
        return None, REJECT_ED25519_SIGNER_PROPOSAL_NONCE_REPLAY
    return reservation, ""


def _rollback_proposal_reservation(
    backend: Ed25519SignerBackend,
    reservation: str | None,
) -> None:
    if reservation is None or backend.proposal_nonce_store is None:
        return
    try:
        backend.proposal_nonce_store.rollback(reservation)
    except Exception:
        pass


def _rollback_manifest_reservation(
    backend: Ed25519SignerBackend,
    reservation: str | None,
) -> None:
    store = backend.runtime_artifact_manifest_nonce_store
    if reservation is None or store is None:
        return
    try:
        store.rollback(reservation)
    except Exception:
        pass


def _commit_manifest_reservation(
    backend: Ed25519SignerBackend,
    reservation: str | None,
) -> bool:
    if reservation is None:
        return True
    store = backend.runtime_artifact_manifest_nonce_store
    if store is None:
        return False
    try:
        store.commit(reservation)
        return True
    except Exception:
        _rollback_manifest_reservation(backend, reservation)
        return False


def _sign_response(
    backend: Ed25519SignerBackend, request: SigningRequest,
    peer: SignerPeerAttestation, is_control: bool,
) -> tuple[SigningResponse, str]:
    try:
        signature = encode_ed25519_signature(
            backend.private_key.sign(request.signing_input.encode("utf-8"))
        )
    except Exception:
        return SigningResponse(accepted=False), REJECT_ED25519_SIGNER_SIGN_FAILED
    try:
        audit_mac = backend.audit_mac_builder.build(request, signature, peer)
    except Exception:
        return SigningResponse(accepted=False), REJECT_ED25519_SIGNER_AUDIT_MAC_MISSING
    if not _is_ascii(audit_mac) or not audit_mac:
        return SigningResponse(accepted=False), REJECT_ED25519_SIGNER_AUDIT_MAC_MISSING
    attestation, reason = _signer_audit_attestation(
        backend, request, signature, audit_mac, peer, is_control
    )
    if reason:
        return SigningResponse(accepted=False), reason
    return SigningResponse(
        accepted=True, signature=signature, signer_public_key=backend.public_key,
        key_fingerprint=public_key_fingerprint(backend.public_key),
        key_epoch=backend.key_epoch, audit_mac=audit_mac,
        audit_attestation_signature=attestation,
        boundary_attested=peer.boundary_attested,
        requester_identity_attested=True, signer_loads_no_untrusted_code=True,
        no_secret_material_returned=True,
    ), ""


def _signer_audit_attestation(
    backend: Ed25519SignerBackend, request: SigningRequest,
    signature: str, audit_mac: str, peer: SignerPeerAttestation,
    is_control: bool,
) -> tuple[str, str]:
    if (
        request.requested_operation
        == peer_handshake.SIGNER_PEER_HANDSHAKE_SIGNING_OPERATION
    ):
        return _sign_peer_response_attestation(
            backend, request, signature, audit_mac, peer
        )
    if (
        not is_control
        and request.requested_operation != AUTHORITATIVE_USE_LEASE_SIGNING_OPERATION
    ):
        return "", ""
    domain_prefix = CONTROL_LOOP_AUDIT_ATTESTATION_PREFIX
    if (
        request.requested_operation
        == RUNTIME_ARTIFACT_MANIFEST_SIGNING_OPERATION
    ):
        domain_prefix = (
            RUNTIME_ARTIFACT_MANIFEST_AUDIT_ATTESTATION_PREFIX
        )
    elif request.requested_operation == VERIFIED_OUTCOME_SIGNING_OPERATION:
        domain_prefix = VERIFIED_OUTCOME_AUDIT_ATTESTATION_PREFIX
    elif request.requested_operation in {
        CONVERSATION_SCOPE_SIGNING_OPERATION,
        CONVERSATION_SCOPE_RECOVERY_SIGNING_OPERATION,
    }:
        domain_prefix = CONVERSATION_SCOPE_AUDIT_ATTESTATION_PREFIX
    elif request.requested_operation == AUTHORITATIVE_USE_LEASE_SIGNING_OPERATION:
        domain_prefix = AUTHORITATIVE_USE_LEASE_AUDIT_ATTESTATION_PREFIX
    elif request.requested_operation == SECRET_GRANT_SIGNING_OPERATION:
        domain_prefix = SECRET_GRANT_AUDIT_ATTESTATION_PREFIX
    try:
        value = canonical_signer_audit_attestation_input(
            signing_input=request.signing_input, signature=signature,
            audit_mac=audit_mac, signer_public_key=backend.public_key,
            key_epoch=backend.key_epoch,
            requester_principal_id=request.requester_principal_id,
            domain_prefix=domain_prefix,
        )
        return encode_ed25519_signature(
            backend.private_key.sign(value.encode("utf-8"))
        ), ""
    except Exception:
        return "", REJECT_ED25519_SIGNER_SIGN_FAILED


def _lease_matches_peer_instance(
    payload: Mapping[str, Any],
    binding: peer_handshake.SignerPeerInstanceBinding | None,
) -> bool:
    if binding is None:
        return False
    profile = next(
        (
            item
            for item in binding.signer_profiles
            if item.signer_profile_id == payload.get("signer_profile_id")
        ),
        None,
    )
    return profile is not None and all(
        (
            payload.get("manifest_id") == binding.manifest_id,
            payload.get("artifact_generation_digest")
            == binding.artifact_generation_digest,
            payload.get("generation") == binding.generation,
            payload.get("generation_revision") == binding.generation_revision,
            payload.get("owner_config_id") == binding.owner_config_id,
            payload.get("run_packet_id") == binding.run_packet_id,
            payload.get("config_digest") == binding.config_digest,
            payload.get("session_id") == binding.session_id,
            payload.get("socket_path_digest") == digest_text(binding.socket_path),
            payload.get("signer_public_key") == profile.signer_public_key,
            payload.get("key_epoch") == profile.key_epoch,
        )
    )


def _sign_peer_response_attestation(
    backend: Ed25519SignerBackend,
    request: SigningRequest,
    signature: str,
    audit_mac: str,
    peer: SignerPeerAttestation,
) -> tuple[str, str]:
    response = SigningResponse(
        accepted=True,
        signature=signature,
        signer_public_key=backend.public_key,
        key_fingerprint=public_key_fingerprint(backend.public_key),
        key_epoch=backend.key_epoch,
        audit_mac=audit_mac,
        boundary_attested=peer.boundary_attested,
        requester_identity_attested=True,
        signer_loads_no_untrusted_code=True,
        no_secret_material_returned=True,
    )
    try:
        signing_input = (
            peer_handshake.canonical_signer_peer_response_attestation_input(
                request, response
            )
        )
        signed = backend.private_key.sign(signing_input.encode("utf-8"))
        return encode_ed25519_signature(signed), ""
    except Exception:
        return "", REJECT_ED25519_SIGNER_SIGN_FAILED


def _valid_control_receipt_signing_payload(request: SigningRequest) -> dict[str, Any] | None:
    return valid_control_receipt_signing_payload(request)


def _control_authority_policy_matches(
    payload: dict[str, Any], policy: ControlLoopAuthorityPolicy
) -> bool:
    return isinstance(policy, ControlLoopAuthorityPolicy) and (
        control_authority_policy_matches(payload, policy)
    )


def _reject(code: str) -> SigningResponse:
    return SigningResponse(
        accepted=False,
        rejection_code=str(code),
        no_secret_material_returned=True,
    )


__all__ = [
    "CONTROL_LOOP_AUDIT_ATTESTATION_PREFIX",
    "CONTROL_LOOP_SIGNING_OPERATION", "CONTROL_LOOP_SIGNING_PREFIX",
    "ControlLoopAuthorityPolicy",
    "bind_exact_signing_request",
    "canonical_control_audit_attestation_input",
    "Ed25519SignerBackend",
    "REJECT_ED25519_SIGNER_AUDIT_MAC_MISSING",
    "REJECT_ED25519_SIGNER_CONTROL_ANCHOR_MISSING",
    "REJECT_ED25519_SIGNER_CONTROL_ANCHOR_REJECTED",
    "REJECT_ED25519_SIGNER_CONTROL_AUTHORITY_POLICY_MISSING",
    "REJECT_ED25519_SIGNER_CONTROL_AUTHORITY_POLICY_MISMATCH",
    "REJECT_ED25519_SIGNER_CONVERSATION_ANCHOR_MISSING",
    "REJECT_ED25519_SIGNER_CONVERSATION_POLICY_MISSING",
    "REJECT_ED25519_SIGNER_CONVERSATION_REJECTED",
    "REJECT_ED25519_SIGNER_CONVERSATION_RESOLVER_MISSING",
    "REJECT_ED25519_SIGNER_DOMAIN_MISMATCH",
    "REJECT_ED25519_SIGNER_EXACT_REQUEST_MISMATCH",
    "REJECT_ED25519_SIGNER_KEY_EPOCH_MISMATCH",
    "REJECT_ED25519_SIGNER_KEY_INVALID",
    "REJECT_ED25519_SIGNER_OUTCOME_AUTHORITY_MISSING",
    "REJECT_ED25519_SIGNER_OUTCOME_AUTHORITY_REJECTED",
    "REJECT_ED25519_SIGNER_PUBLIC_KEY_MISMATCH",
    "REJECT_ED25519_SIGNER_PROPOSAL_AUTHORITY_POLICY_MISMATCH",
    "REJECT_ED25519_SIGNER_PROPOSAL_AUTHORITY_POLICY_MISSING",
    "REJECT_ED25519_SIGNER_PROPOSAL_DOMAIN_ONLY",
    "REJECT_ED25519_SIGNER_PROPOSAL_NONCE_REPLAY",
    "REJECT_ED25519_SIGNER_PROPOSAL_NONCE_STORE_MISSING",
    "REJECT_ED25519_SIGNER_POLICY_MISSING",
    "REJECT_ED25519_SIGNER_REQUEST_INVALID",
    "REJECT_ED25519_SIGNER_SIGN_FAILED",
    "SignerAuditMacBuilder",
]
