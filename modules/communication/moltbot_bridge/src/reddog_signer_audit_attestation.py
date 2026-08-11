"""Public canonical input for isolated-signer audit attestations."""

from __future__ import annotations

import hashlib
import json


CONTROL_LOOP_AUDIT_ATTESTATION_PREFIX = "reddog-control-loop-audit.v1."
RUNTIME_ARTIFACT_MANIFEST_AUDIT_ATTESTATION_PREFIX = (
    "reddog-runtime-artifact-manifest-audit.v1."
)
VERIFIED_OUTCOME_AUDIT_ATTESTATION_PREFIX = "reddog-verified-outcome-audit.v1."
CONVERSATION_SCOPE_AUDIT_ATTESTATION_PREFIX = (
    "reddog-conversation-scope-state-audit.v1."
)
AUTHORITATIVE_USE_LEASE_AUDIT_ATTESTATION_PREFIX = (
    "reddog-authoritative-use-lease-audit.v1."
)
SIGNER_AUDIT_ATTESTATION_PREFIX = CONTROL_LOOP_AUDIT_ATTESTATION_PREFIX


def canonical_signer_audit_attestation_input(
    *,
    signing_input: str,
    signature: str,
    audit_mac: str,
    signer_public_key: str,
    key_epoch: str,
    requester_principal_id: str,
    domain_prefix: str = CONTROL_LOOP_AUDIT_ATTESTATION_PREFIX,
) -> str:
    """Bind one public signature to the signer's private audit-MAC result."""

    payload = {
        "audit_mac": audit_mac,
        "key_epoch": key_epoch,
        "requester_principal_id": requester_principal_id,
        "signature": signature,
        "signer_public_key": signer_public_key,
        "signing_input_digest": "sha256:"
        + hashlib.sha256(signing_input.encode("utf-8")).hexdigest(),
    }
    if domain_prefix not in {
        CONTROL_LOOP_AUDIT_ATTESTATION_PREFIX,
        RUNTIME_ARTIFACT_MANIFEST_AUDIT_ATTESTATION_PREFIX,
        VERIFIED_OUTCOME_AUDIT_ATTESTATION_PREFIX,
        CONVERSATION_SCOPE_AUDIT_ATTESTATION_PREFIX,
        AUTHORITATIVE_USE_LEASE_AUDIT_ATTESTATION_PREFIX,
    }:
        raise ValueError("signer_audit_attestation_domain_invalid")
    return domain_prefix + json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )


__all__ = [
    "AUTHORITATIVE_USE_LEASE_AUDIT_ATTESTATION_PREFIX",
    "CONVERSATION_SCOPE_AUDIT_ATTESTATION_PREFIX",
    "CONTROL_LOOP_AUDIT_ATTESTATION_PREFIX",
    "RUNTIME_ARTIFACT_MANIFEST_AUDIT_ATTESTATION_PREFIX",
    "SIGNER_AUDIT_ATTESTATION_PREFIX",
    "VERIFIED_OUTCOME_AUDIT_ATTESTATION_PREFIX",
    "canonical_signer_audit_attestation_input",
]
