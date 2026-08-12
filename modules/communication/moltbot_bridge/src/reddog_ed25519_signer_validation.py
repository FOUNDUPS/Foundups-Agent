"""Pure request and control-policy validation for the Ed25519 signer backend."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Mapping

from modules.communication.moltbot_bridge.src import reddog_signer_mutual_peer_handshake as peer_handshake
from modules.communication.moltbot_bridge.src.reddog_architect_proposal_authenticity import (
    PROPOSAL_AUTHENTICITY_SIGNING_OPERATION,
    PROPOSAL_AUTHENTICITY_SIGNING_PREFIX,
)
from modules.communication.moltbot_bridge.src.reddog_authoritative_use_lease_contract import (
    AUTHORITATIVE_USE_LEASE_SIGNING_OPERATION,
    AUTHORITATIVE_USE_LEASE_SIGNING_PREFIX,
)
from modules.communication.moltbot_bridge.src.reddog_ed25519_conversation_scope_backend import (
    CONVERSATION_SCOPE_RECOVERY_SIGNING_OPERATION,
    CONVERSATION_SCOPE_SIGNING_OPERATION,
    conversation_signing_domain_pair,
)
from modules.communication.moltbot_bridge.src.foundup_memex_verified_outcome_signing import (
    VERIFIED_OUTCOME_SIGNING_OPERATION,
    VERIFIED_OUTCOME_SIGNING_PREFIX,
)
from modules.communication.moltbot_bridge.src.reddog_signed_runtime_artifact_manifest import (
    RUNTIME_ARTIFACT_MANIFEST_SIGNING_OPERATION,
    RUNTIME_ARTIFACT_MANIFEST_SIGNING_PREFIX,
)
from modules.communication.moltbot_bridge.src.reddog_signer_delegated_authority_runtime import (
    SigningRequest,
)
from modules.communication.moltbot_bridge.src.reddog_signer_audit_attestation import (
    canonical_signer_audit_attestation_input,
)
from modules.communication.moltbot_bridge.src.reddog_signer_secret_grant_authority_policy import (
    SECRET_GRANT_SIGNING_OPERATION,
)
from modules.communication.moltbot_bridge.src.reddog_signer_secret_grant_issuance import (
    SECRET_GRANT_SIGNING_PREFIX,
)
from modules.communication.moltbot_bridge.src.reddog_work_order_signature_verifier import (
    PREFIX_IDENTITY,
    PREFIX_WORKAUTH,
)


CONTROL_LOOP_RECEIPT_SCHEMA_VERSION = "reddog_resident_control_loop_receipt.v2"
CONTROL_LOOP_SIGNING_OPERATION = "attest_control_loop_receipt"
CONTROL_LOOP_SIGNING_PREFIX = "reddog-control-loop.v2."
_RESERVED_SIGNING_OPERATIONS = frozenset(
    {
        CONTROL_LOOP_SIGNING_OPERATION,
        PROPOSAL_AUTHENTICITY_SIGNING_OPERATION,
        RUNTIME_ARTIFACT_MANIFEST_SIGNING_OPERATION,
        peer_handshake.SIGNER_PEER_HANDSHAKE_SIGNING_OPERATION,
        VERIFIED_OUTCOME_SIGNING_OPERATION,
        CONVERSATION_SCOPE_SIGNING_OPERATION,
        CONVERSATION_SCOPE_RECOVERY_SIGNING_OPERATION,
        AUTHORITATIVE_USE_LEASE_SIGNING_OPERATION,
        SECRET_GRANT_SIGNING_OPERATION,
        "delegate_reddog_identity",
    }
)
_CONTROL_LOOP_SIGNED_FIELDS = frozenset(
    {
        "schema_version", "receipt_id", "sequence_number", "cycle_id", "nonce",
        "previous_receipt_id", "legacy_prefix_digest", "accepted", "status", "rounds",
        "serial_progress", "claim_progress", "receipt_ids", "source_receipt_ids_digest",
        "rejection_reasons", "child_execution_receipt_ids",
        "child_execution_evidence_digests", "child_execution_outcomes",
        "child_execution_evidence_digest", "child_execution_evidence_count", "created_at",
        "repo_root_digest", "control_lock_acquired", "dispatched_stages",
        "authority_issuance_count", "worker_claim_count", "worker_execution_count",
        "worker_completion_count", "worker_requeue_count", "worker_failure_count",
        "worktree_creation_count", "bounded_file_edit_count", "slice_verification_count",
        "draft_pr_publish_count", "pattern_memory_admission_count",
        "worker_process_spawn_count", "shell_command_count", "worker_effects_unverified_count",
        "authority_issued", "worker_claim_performed", "worker_execution_performed",
        "worktree_creation_observed", "bounded_file_edit_observed",
        "slice_verification_observed", "draft_pr_publish_observed",
        "pattern_memory_admission_observed", "worker_process_spawn_observed",
        "shell_command_execution_observed", "issuer_principal_id", "signer_public_key",
        "signer_key_fingerprint", "key_epoch", "consensus_receipt_digest",
        "authority_profile_digest", "authority_profile_source_receipt_id",
        "authentication_status",
    }
)


@dataclass(frozen=True)
class ControlLoopAuthorityPolicy:
    """Signer-owned authorization bindings for control-loop attestations."""

    issuer_principal_id: str
    signer_public_key: str
    key_epoch: str
    consensus_receipt_digest: str
    authority_profile_digest: str
    authority_profile_source_receipt_id: str


def signing_domain_pairs(request: SigningRequest) -> tuple[tuple[bool, bool], ...]:
    """Return operation/prefix equivalence checks for every signer domain."""

    return (
        (
            request.requested_operation == CONTROL_LOOP_SIGNING_OPERATION,
            request.signing_input.startswith(CONTROL_LOOP_SIGNING_PREFIX),
        ),
        (
            request.requested_operation == PROPOSAL_AUTHENTICITY_SIGNING_OPERATION,
            request.signing_input.startswith(PROPOSAL_AUTHENTICITY_SIGNING_PREFIX),
        ),
        (
            request.requested_operation == RUNTIME_ARTIFACT_MANIFEST_SIGNING_OPERATION,
            request.signing_input.startswith(RUNTIME_ARTIFACT_MANIFEST_SIGNING_PREFIX),
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
        conversation_signing_domain_pair(request),
        (
            request.requested_operation == AUTHORITATIVE_USE_LEASE_SIGNING_OPERATION,
            request.signing_input.startswith(AUTHORITATIVE_USE_LEASE_SIGNING_PREFIX),
        ),
        (
            request.requested_operation == SECRET_GRANT_SIGNING_OPERATION,
            request.signing_input.startswith(SECRET_GRANT_SIGNING_PREFIX),
        ),
        (
            request.requested_operation == "delegate_reddog_identity",
            request.signing_input.startswith(PREFIX_IDENTITY + "."),
        ),
        (
            request.requested_operation not in _RESERVED_SIGNING_OPERATIONS,
            request.signing_input.startswith(PREFIX_WORKAUTH + "."),
        ),
    )


def public_bytes_from_private_key(private_key: Any) -> bytes:
    from cryptography.hazmat.primitives import serialization

    return private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )


def valid_control_receipt_signing_payload(request: SigningRequest) -> dict[str, Any] | None:
    prefix = "reddog-control-loop.v2."
    if not request.signing_input.startswith(prefix):
        return None
    raw = request.signing_input[len(prefix):]
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
    expected_id = "reddog_resident_control_loop_v2_" + sha256_json(unsigned)
    expected_request_digest = "sha256:" + sha256_json({"signing_input": request.signing_input})
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
        and is_sha256_digest(payload.get("consensus_receipt_digest"))
        and is_sha256_digest(payload.get("authority_profile_digest"))
        and is_sha256_digest(payload.get("authority_profile_source_receipt_id"))
        and payload.get("authentication_status") == "AUTHENTICATED"
        and request.payload_digest == expected_request_digest
    )
    return payload if valid else None


def control_authority_policy_matches(payload: Mapping[str, Any], policy: Any) -> bool:
    if policy is None:
        return False
    policy_payload = {
        "issuer_principal_id": policy.issuer_principal_id,
        "signer_public_key": policy.signer_public_key,
        "key_epoch": policy.key_epoch,
        "consensus_receipt_digest": policy.consensus_receipt_digest,
        "authority_profile_digest": policy.authority_profile_digest,
        "authority_profile_source_receipt_id": policy.authority_profile_source_receipt_id,
    }
    if not assert_ascii_deep(policy_payload):
        return False
    if not all(is_sha256_digest(policy_payload[field]) for field in (
        "consensus_receipt_digest", "authority_profile_digest",
        "authority_profile_source_receipt_id",
    )):
        return False
    return all(payload.get(field) == value for field, value in policy_payload.items())


def canonical_control_audit_attestation_input(
    *,
    signing_input: str,
    signature: str,
    audit_mac: str,
    signer_public_key: str,
    key_epoch: str,
    requester_principal_id: str,
) -> str:
    return canonical_signer_audit_attestation_input(
        signing_input=signing_input,
        signature=signature,
        audit_mac=audit_mac,
        signer_public_key=signer_public_key,
        key_epoch=key_epoch,
        requester_principal_id=requester_principal_id,
    )


def is_sha256_digest(value: object) -> bool:
    text = str(value or "")
    return len(text) == 71 and text.startswith("sha256:") and all(
        char in "0123456789abcdef" for char in text[7:]
    )


def sha256_json(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def is_ascii(value: object) -> bool:
    return isinstance(value, str) and value.isascii()


def assert_ascii_deep(value: object) -> bool:
    if isinstance(value, str):
        return is_ascii(value)
    if isinstance(value, Mapping):
        return all(is_ascii(key) and assert_ascii_deep(item) for key, item in value.items())
    if isinstance(value, (list, tuple)):
        return all(assert_ascii_deep(item) for item in value)
    return value is None or isinstance(value, (bool, int, float))


__all__ = [
    "CONTROL_LOOP_SIGNING_OPERATION",
    "CONTROL_LOOP_SIGNING_PREFIX",
    "ControlLoopAuthorityPolicy",
    "assert_ascii_deep",
    "canonical_control_audit_attestation_input",
    "control_authority_policy_matches",
    "is_ascii",
    "public_bytes_from_private_key",
    "signing_domain_pairs",
    "valid_control_receipt_signing_payload",
]
