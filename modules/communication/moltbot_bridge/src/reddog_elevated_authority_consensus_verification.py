"""Canonical outer verification for elevated-authority consensus receipts."""

from __future__ import annotations

from typing import Any, Mapping

from modules.communication.moltbot_bridge.src.reddog_elevated_authority_consensus_capability import (
    VerifiedElevatedAuthorityConsensusCapability,
    _mint_elevated_authority_consensus_capability,
)
from modules.communication.moltbot_bridge.src.reddog_elevated_authority_consensus_contract import (
    canonical_authority_request_digest,
)
from modules.communication.moltbot_bridge.src.reddog_elevated_authority_consensus_evidence import (
    author_runtime_evidence_matches,
    consensus_receipt_matches,
)
from modules.communication.moltbot_bridge.src.reddog_elevated_authority_consensus_policy import (
    AuthorRuntimeEvidenceResolver,
    ElevatedConsensusPolicyResolver,
    ReviewerKeyAuthorityResolver,
    ReviewerRuntimeEvidenceResolver,
    SovereignAuthorizationEvidenceResolver,
)
from modules.communication.moltbot_bridge.src.reddog_elevated_authority_consensus_rehydration import (
    rehydrate_consensus_receipt,
)
from modules.communication.moltbot_bridge.src.reddog_elevated_authority_consensus_reviewer_evidence import (
    consensus_decisions_verify,
)
from modules.communication.moltbot_bridge.src.reddog_elevated_authority_consensus_signer_verification import (
    ElevatedConsensusSignerAuthority,
)
from modules.communication.moltbot_bridge.src.reddog_work_order_signature_verifier import (
    SignatureVerifier,
)


def verify_elevated_authority_consensus(
    *,
    consensus_receipt: Mapping[str, Any],
    authority_request: Any,
    signature_verifier: SignatureVerifier,
    reviewer_key_resolver: ReviewerKeyAuthorityResolver,
    runtime_evidence_resolver: ReviewerRuntimeEvidenceResolver,
    author_runtime_evidence_resolver: AuthorRuntimeEvidenceResolver,
    sovereign_authorization_resolver: SovereignAuthorizationEvidenceResolver,
    policy_resolver: ElevatedConsensusPolicyResolver,
    now: int,
    revoked_key_epochs: frozenset[str] = frozenset(),
) -> VerifiedElevatedAuthorityConsensusCapability | None:
    """Verify current policy, sovereign authority, and all signed reviews."""
    try:
        receipt = rehydrate_consensus_receipt(consensus_receipt)
        request_digest = canonical_authority_request_digest(authority_request)
        policy = policy_resolver.resolve(receipt.context.consensus_policy_digest)
        sovereign = sovereign_authorization_resolver.resolve(
            receipt.context.sovereign_authorization_digest
        )
        author_runtime = author_runtime_evidence_resolver.resolve(
            authority_request.model_runtime_binding_verification_receipt_id
        )
        if not author_runtime_evidence_matches(
            author_runtime, authority_request, now
        ):
            return None
        if not consensus_receipt_matches(
            receipt, authority_request, request_digest, policy, sovereign, now
        ):
            return None
        if not consensus_decisions_verify(
            receipt,
            authority_request,
            signature_verifier,
            reviewer_key_resolver,
            runtime_evidence_resolver,
            policy,
            now,
            revoked_key_epochs,
        ):
            return None
    except Exception:
        return None
    return _mint_verified_capability(receipt, request_digest, authority_request)


def _mint_verified_capability(receipt, request_digest, authority_request):
    return _mint_elevated_authority_consensus_capability(
        authority_request_digest=request_digest,
        consensus_receipt_digest=receipt.receipt_id,
        expires_at=receipt.context.expires_at,
        authorized_signing_request_digests=frozenset(
            receipt.context.authorized_signing_request_digests
        ),
        consensus_proof={
            "schema_version": "reddog_elevated_consensus_proof.v1",
            "consensus_receipt": receipt.to_dict(),
            "authority_request": authority_request.to_dict(),
        },
    )


__all__ = [
    "ElevatedConsensusSignerAuthority",
    "verify_elevated_authority_consensus",
]
