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

import hashlib
import json
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
from modules.communication.moltbot_bridge.src.reddog_architect_proposal_authenticity import (
    ArchitectProposalSignerPolicy,
    PROPOSAL_AUTHENTICITY_SIGNING_OPERATION,
    PROPOSAL_AUTHENTICITY_SIGNING_PREFIX,
    ProposalAuthenticityNonceStore,
    validate_proposal_signing_request,
)
from modules.communication.moltbot_bridge.src.reddog_signed_runtime_artifact_manifest import (
    RUNTIME_ARTIFACT_MANIFEST_SIGNING_OPERATION,
    RUNTIME_ARTIFACT_MANIFEST_SIGNING_PREFIX,
    RuntimeArtifactManifestAuthority,
    validate_runtime_artifact_manifest_signing_request,
)
from modules.communication.moltbot_bridge.src.reddog_runtime_artifact_manifest_authority import (
    RuntimeArtifactManifestAuthorityBoundary,
)
from modules.communication.moltbot_bridge.src.reddog_signer_audit_attestation import (
    RUNTIME_ARTIFACT_MANIFEST_AUDIT_ATTESTATION_PREFIX,
    canonical_signer_audit_attestation_input,
)
from modules.communication.moltbot_bridge.src import reddog_signer_mutual_peer_handshake as peer_handshake
from modules.communication.moltbot_bridge.src.foundup_memex_verified_outcome_signing import (
    VERIFIED_OUTCOME_AUDIT_ATTESTATION_PREFIX,
    VERIFIED_OUTCOME_SIGNING_OPERATION,
    VERIFIED_OUTCOME_SIGNING_PREFIX,
    VerifiedOutcomeSigningAuthority,
    VerifiedOutcomeSignerPolicy,
    validate_verified_outcome_signing_request,
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
REJECT_ED25519_SIGNER_OUTCOME_AUTHORITY_MISSING = (
    "REJECT_ED25519_SIGNER_OUTCOME_AUTHORITY_MISSING"
)
REJECT_ED25519_SIGNER_OUTCOME_AUTHORITY_REJECTED = (
    "REJECT_ED25519_SIGNER_OUTCOME_AUTHORITY_REJECTED"
)

CONTROL_LOOP_SIGNING_OPERATION = "attest_control_loop_receipt"
CONTROL_LOOP_SIGNING_PREFIX = "reddog-control-loop.v2."
CONTROL_LOOP_AUDIT_ATTESTATION_PREFIX = "reddog-control-loop-audit.v1."
CONTROL_LOOP_RECEIPT_SCHEMA_VERSION = "reddog_resident_control_loop_receipt.v2"
_CONTROL_LOOP_SIGNED_FIELDS = frozenset(
    {
        "schema_version", "receipt_id", "sequence_number", "cycle_id", "nonce",
        "previous_receipt_id",
        "legacy_prefix_digest", "accepted", "status", "rounds", "serial_progress",
        "claim_progress", "receipt_ids", "source_receipt_ids_digest", "rejection_reasons",
        "child_execution_receipt_ids",
        "child_execution_evidence_digests", "child_execution_outcomes",
        "child_execution_evidence_digest",
        "child_execution_evidence_count",
        "created_at", "repo_root_digest", "control_lock_acquired", "dispatched_stages",
        "authority_issuance_count", "worker_claim_count", "worker_execution_count",
        "worker_completion_count", "worker_requeue_count", "worker_failure_count",
        "worktree_creation_count", "bounded_file_edit_count", "slice_verification_count",
        "draft_pr_publish_count", "pattern_memory_admission_count",
        "worker_process_spawn_count", "shell_command_count",
        "worker_effects_unverified_count", "authority_issued",
        "worker_claim_performed", "worker_execution_performed",
        "worktree_creation_observed", "bounded_file_edit_observed",
        "slice_verification_observed", "draft_pr_publish_observed",
        "pattern_memory_admission_observed", "worker_process_spawn_observed",
        "shell_command_execution_observed",
        "issuer_principal_id", "signer_public_key", "signer_key_fingerprint", "key_epoch",
        "consensus_receipt_digest", "authority_profile_digest",
        "authority_profile_source_receipt_id", "authentication_status",
    }
)


class SignerAuditMacBuilder(Protocol):
    """Injected audit-MAC boundary owned by the isolated signer process."""

    def build(self, request: SigningRequest, signature: str, peer: SignerPeerAttestation) -> str:
        """Return a signer-side audit MAC. Empty or non-ASCII values reject."""


@dataclass(frozen=True)
class ControlLoopAuthorityPolicy:
    """Signer-owned authorization bindings for control-loop attestations."""

    issuer_principal_id: str
    signer_public_key: str
    key_epoch: str
    consensus_receipt_digest: str
    authority_profile_digest: str
    authority_profile_source_receipt_id: str


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

    def sign(self, request: SigningRequest, peer: SignerPeerAttestation) -> SigningResponse:
        reason = _signer_request_rejection(self, request, peer)
        if reason:
            return _reject(reason)
        control_payload, preparation, reason = _prepare_control_signing(
            self, request
        )
        if reason:
            return _reject(reason)
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
        response, reason = _sign_response(
            self,
            request,
            peer,
            _requires_audit_attestation(
                control_payload, manifest_payload, outcome_payload
            ),
        )
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
        )


def _finalize_signing(
    backend: Ed25519SignerBackend,
    response: SigningResponse,
    proposal_reservation: Any,
    manifest_reservation: Any,
    outcome_reservation: Any,
    control_payload: Mapping[str, Any] | None,
    preparation: Any,
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
    if not _commit_outcome_reservation(backend, outcome_reservation):
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
    return response


def _requires_audit_attestation(*payloads: Mapping[str, Any] | None) -> bool:
    return any(payload is not None for payload in payloads)


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
    if any(operation is not prefix for operation, prefix in _signing_domain_pairs(request)):
        return REJECT_ED25519_SIGNER_DOMAIN_MISMATCH
    configured = (
        backend.proposal_authority_policy is not None
        or backend.runtime_artifact_manifest_authority is not None
        or backend.runtime_artifact_manifest_authority_boundary is not None
        or backend.verified_outcome_signer_policy is not None
    )
    if configured:
        allowed_operations = {peer_handshake.SIGNER_PEER_HANDSHAKE_SIGNING_OPERATION}
        if backend.proposal_authority_policy is not None:
            allowed_operations.add(PROPOSAL_AUTHENTICITY_SIGNING_OPERATION)
        if backend.control_loop_authority_policy is not None:
            allowed_operations.add(CONTROL_LOOP_SIGNING_OPERATION)
        if (backend.runtime_artifact_manifest_authority is not None
                and backend.runtime_artifact_manifest_authority_boundary is not None):
            allowed_operations.add(RUNTIME_ARTIFACT_MANIFEST_SIGNING_OPERATION)
        if backend.verified_outcome_signer_policy is not None:
            allowed_operations.add(VERIFIED_OUTCOME_SIGNING_OPERATION)
        if request.requested_operation not in allowed_operations:
            return REJECT_ED25519_SIGNER_PROPOSAL_DOMAIN_ONLY
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


def _signing_domain_pairs(
    request: SigningRequest,
) -> tuple[tuple[bool, bool], ...]:
    return (
        (
            request.requested_operation == CONTROL_LOOP_SIGNING_OPERATION,
            request.signing_input.startswith(CONTROL_LOOP_SIGNING_PREFIX),
        ),
        (
            request.requested_operation
            == PROPOSAL_AUTHENTICITY_SIGNING_OPERATION,
            request.signing_input.startswith(
                PROPOSAL_AUTHENTICITY_SIGNING_PREFIX
            ),
        ),
        (
            request.requested_operation
            == RUNTIME_ARTIFACT_MANIFEST_SIGNING_OPERATION,
            request.signing_input.startswith(
                RUNTIME_ARTIFACT_MANIFEST_SIGNING_PREFIX
            ),
        ),
        (
            request.requested_operation
            == peer_handshake.SIGNER_PEER_HANDSHAKE_SIGNING_OPERATION,
            request.signing_input.startswith(
                peer_handshake.SIGNER_PEER_HANDSHAKE_SIGNING_PREFIX
            ),
        ),
        (
            request.requested_operation == VERIFIED_OUTCOME_SIGNING_OPERATION,
            request.signing_input.startswith(VERIFIED_OUTCOME_SIGNING_PREFIX),
        ),
    )


def _prepare_verified_outcome_signing(
    backend: Ed25519SignerBackend,
    request: SigningRequest,
) -> tuple[dict[str, Any] | None, Any, str]:
    if request.requested_operation != VERIFIED_OUTCOME_SIGNING_OPERATION:
        return None, None, ""
    policy = backend.verified_outcome_signer_policy
    if policy is None:
        return None, None, REJECT_ED25519_SIGNER_DOMAIN_MISMATCH
    authority = backend.verified_outcome_signing_authority
    if authority is None:
        return None, None, REJECT_ED25519_SIGNER_OUTCOME_AUTHORITY_MISSING
    payload = validate_verified_outcome_signing_request(
        request,
        policy,
        now_epoch=int(backend.proposal_clock()),
    )
    if payload is None:
        return None, None, REJECT_ED25519_SIGNER_REQUEST_INVALID
    try:
        reservation = authority.reserve(
            receipt_id=str(payload["receipt_id"]),
            work_order_id=str(payload["work_order_id"]),
            evidence_digest=str(payload["covered_action_digest"]),
            issued_at=int(payload["issued_at"]),
        )
    except Exception:
        reservation = None
    if reservation is None:
        return None, None, REJECT_ED25519_SIGNER_OUTCOME_AUTHORITY_REJECTED
    return dict(payload), reservation, ""


def _commit_outcome_reservation(
    backend: Ed25519SignerBackend, reservation: Any
) -> bool:
    if reservation is None:
        return True
    try:
        assert backend.verified_outcome_signing_authority is not None
        backend.verified_outcome_signing_authority.commit(reservation)
        return True
    except Exception:
        _rollback_outcome_reservation(backend, reservation)
        return False


def _rollback_outcome_reservation(
    backend: Ed25519SignerBackend, reservation: Any
) -> None:
    if reservation is None or backend.verified_outcome_signing_authority is None:
        return
    try:
        backend.verified_outcome_signing_authority.rollback(reservation)
    except Exception:
        return


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
    if not is_control:
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


def _public_bytes_from_private_key(private_key: Any) -> bytes:
    from cryptography.hazmat.primitives import serialization

    return private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )


def _valid_control_receipt_signing_payload(
    request: SigningRequest,
) -> dict[str, Any] | None:
    raw = request.signing_input[len(CONTROL_LOOP_SIGNING_PREFIX) :]
    try:
        payload = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict) or set(payload) != _CONTROL_LOOP_SIGNED_FIELDS:
        return None
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    if raw != canonical:
        return None
    unsigned = {key: value for key, value in payload.items() if key != "receipt_id"}
    expected_id = "reddog_resident_control_loop_v2_" + _sha256_json(unsigned)
    expected_request_digest = "sha256:" + _sha256_json({"signing_input": request.signing_input})
    valid = bool(
        request.signer_role == "reddog_control_loop"
        and request.authority_tier in {"HIGH", "ULTRA"}
        and payload.get("schema_version") == CONTROL_LOOP_RECEIPT_SCHEMA_VERSION
        and payload.get("receipt_id") == expected_id
        and payload.get("nonce") == request.nonce
        and payload.get("issuer_principal_id") == request.requester_principal_id
        and payload.get("signer_public_key") == request.signer_public_key
        and payload.get("key_epoch") == request.key_epoch
        and payload.get("consensus_receipt_digest") == request.consensus_receipt_digest
        and _is_sha256_digest(payload.get("consensus_receipt_digest"))
        and _is_sha256_digest(payload.get("authority_profile_digest"))
        and _is_sha256_digest(payload.get("authority_profile_source_receipt_id"))
        and payload.get("authentication_status") == "AUTHENTICATED"
        and request.payload_digest == expected_request_digest
    )
    return payload if valid else None


def _control_authority_policy_matches(
    payload: dict[str, Any], policy: ControlLoopAuthorityPolicy
) -> bool:
    if not isinstance(policy, ControlLoopAuthorityPolicy):
        return False
    policy_payload = {
        "authority_profile_digest": policy.authority_profile_digest,
        "authority_profile_source_receipt_id": (
            policy.authority_profile_source_receipt_id
        ),
        "consensus_receipt_digest": policy.consensus_receipt_digest,
        "issuer_principal_id": policy.issuer_principal_id,
        "key_epoch": policy.key_epoch,
        "signer_public_key": policy.signer_public_key,
    }
    if not _assert_ascii_deep(policy_payload):
        return False
    if not all(
        _is_sha256_digest(policy_payload[field])
        for field in (
            "authority_profile_digest",
            "authority_profile_source_receipt_id",
            "consensus_receipt_digest",
        )
    ):
        return False
    return all(payload.get(field) == expected for field, expected in policy_payload.items())


def canonical_control_audit_attestation_input(
    *,
    signing_input: str,
    signature: str,
    audit_mac: str,
    signer_public_key: str,
    key_epoch: str,
    requester_principal_id: str,
) -> str:
    """Return the public, deterministic attestation input for a signer audit MAC."""

    return canonical_signer_audit_attestation_input(
        signing_input=signing_input,
        signature=signature,
        audit_mac=audit_mac,
        signer_public_key=signer_public_key,
        key_epoch=key_epoch,
        requester_principal_id=requester_principal_id,
    )


def _is_sha256_digest(value: object) -> bool:
    text = str(value or "")
    return len(text) == 71 and text.startswith("sha256:") and all(
        char in "0123456789abcdef" for char in text[7:]
    )


def _sha256_json(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _reject(code: str) -> SigningResponse:
    return SigningResponse(
        accepted=False,
        rejection_code=str(code),
        no_secret_material_returned=True,
    )


def _is_ascii(value: object) -> bool:
    return isinstance(value, str) and all(ord(char) < 128 for char in value)


def _assert_ascii_deep(value: object) -> bool:
    if isinstance(value, str):
        return _is_ascii(value)
    if isinstance(value, dict):
        return all(_is_ascii(key) and _assert_ascii_deep(item) for key, item in value.items())
    if isinstance(value, (list, tuple)):
        return all(_assert_ascii_deep(item) for item in value)
    if value is None or isinstance(value, (bool, int, float)):
        return True
    return False


__all__ = [
    "CONTROL_LOOP_AUDIT_ATTESTATION_PREFIX",
    "CONTROL_LOOP_SIGNING_OPERATION",
    "CONTROL_LOOP_SIGNING_PREFIX",
    "ControlLoopAuthorityPolicy",
    "canonical_control_audit_attestation_input",
    "Ed25519SignerBackend",
    "REJECT_ED25519_SIGNER_AUDIT_MAC_MISSING",
    "REJECT_ED25519_SIGNER_CONTROL_ANCHOR_MISSING",
    "REJECT_ED25519_SIGNER_CONTROL_ANCHOR_REJECTED",
    "REJECT_ED25519_SIGNER_CONTROL_AUTHORITY_POLICY_MISSING",
    "REJECT_ED25519_SIGNER_CONTROL_AUTHORITY_POLICY_MISMATCH",
    "REJECT_ED25519_SIGNER_DOMAIN_MISMATCH",
    "REJECT_ED25519_SIGNER_KEY_EPOCH_MISMATCH",
    "REJECT_ED25519_SIGNER_KEY_INVALID",
    "REJECT_ED25519_SIGNER_PUBLIC_KEY_MISMATCH",
    "REJECT_ED25519_SIGNER_PROPOSAL_AUTHORITY_POLICY_MISMATCH",
    "REJECT_ED25519_SIGNER_PROPOSAL_AUTHORITY_POLICY_MISSING",
    "REJECT_ED25519_SIGNER_PROPOSAL_DOMAIN_ONLY",
    "REJECT_ED25519_SIGNER_PROPOSAL_NONCE_REPLAY",
    "REJECT_ED25519_SIGNER_PROPOSAL_NONCE_STORE_MISSING",
    "REJECT_ED25519_SIGNER_REQUEST_INVALID",
    "REJECT_ED25519_SIGNER_SIGN_FAILED",
    "SignerAuditMacBuilder",
]
