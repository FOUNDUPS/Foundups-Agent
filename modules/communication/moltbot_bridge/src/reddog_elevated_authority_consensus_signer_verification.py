"""Signer-owned re-verification and replay admission for elevated consensus."""

from __future__ import annotations

from dataclasses import dataclass, fields
from typing import Any, Mapping

from modules.communication.moltbot_bridge.src.reddog_elevated_authority_consensus_capability import (
    ConsensusNonceAuthority,
)
from modules.communication.moltbot_bridge.src.reddog_elevated_authority_consensus_contract import (
    ElevatedAuthorityConsensusReceipt,
    canonical_authority_request_digest,
    canonical_consensus_context_digest,
    canonical_elevated_signing_request_digest,
    canonical_json_digest,
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
from modules.communication.moltbot_bridge.src.reddog_work_order_signature_verifier import (
    SignatureVerifier,
)
from modules.communication.moltbot_bridge.src.reddog_elevated_consensus_signer_reservation import (
    VerifiedElevatedConsensusSignerReservation,
    reserve_elevated_consensus_nonce,
)


@dataclass(frozen=True, slots=True)
class ElevatedConsensusSignerAuthority:
    """Re-verify proof and consume replay state at the key-release boundary."""

    signature_verifier: SignatureVerifier
    reviewer_key_resolver: ReviewerKeyAuthorityResolver
    runtime_evidence_resolver: ReviewerRuntimeEvidenceResolver
    author_runtime_evidence_resolver: AuthorRuntimeEvidenceResolver
    sovereign_authorization_resolver: SovereignAuthorizationEvidenceResolver
    policy_resolver: ElevatedConsensusPolicyResolver
    nonce_authority: ConsensusNonceAuthority
    revoked_key_epochs: frozenset[str] = frozenset()

    def reserve(
        self, proof: Mapping[str, Any], *, signing_request_digest: str, now: int
    ) -> VerifiedElevatedConsensusSignerReservation | None:
        try:
            receipt, request, target = _rehydrate_proof(proof)
            policy = self.policy_resolver.resolve(
                receipt.context.consensus_policy_digest
            )
            sovereign = self.sovereign_authorization_resolver.resolve(
                receipt.context.sovereign_authorization_digest
            )
            author_runtime = self.author_runtime_evidence_resolver.resolve(
                request.model_runtime_binding_verification_receipt_id
            )
            if not author_runtime_evidence_matches(author_runtime, request, now):
                return None
            projected = canonical_elevated_signing_request_digest(target)
            if projected not in set(receipt.context.authorized_signing_request_digests):
                return None
            if not _grant_request_matches(target, proof, signing_request_digest):
                return None
            request_digest = canonical_authority_request_digest(request)
            if not consensus_receipt_matches(
                receipt, request, request_digest, policy, sovereign, now
            ) or not consensus_decisions_verify(
                receipt,
                request,
                self.signature_verifier,
                self.reviewer_key_resolver,
                self.runtime_evidence_resolver,
                policy,
                now,
                self.revoked_key_epochs,
            ):
                return None
            return _reserve_signer_nonce(
                self.nonce_authority, receipt, projected
            )
        except Exception:
            return None


def _rehydrate_proof(proof: Any) -> tuple[Any, Any, Any]:
    expected = {
        "schema_version",
        "consensus_receipt",
        "authority_request",
        "target_signing_request",
    }
    if not isinstance(proof, Mapping) or set(proof) != expected:
        raise ValueError("elevated_consensus_proof_invalid")
    if proof.get("schema_version") != "reddog_elevated_consensus_proof.v1":
        raise ValueError("elevated_consensus_proof_invalid")
    return (
        rehydrate_consensus_receipt(proof["consensus_receipt"]),
        _rehydrate_authority_request(proof["authority_request"]),
        _rehydrate_signing_request(proof["target_signing_request"]),
    )


def _grant_request_matches(target: Any, proof: Any, expected_digest: str) -> bool:
    from modules.communication.moltbot_bridge.src.reddog_signer_secret_access_grant_contract import (
        signer_secret_access_request_digest,
    )

    if proof.get("target_signing_request") != target.to_dict():
        return False
    return signer_secret_access_request_digest(target.to_dict()) == expected_digest


def _rehydrate_authority_request(value: Any) -> Any:
    from modules.communication.moltbot_bridge.src.reddog_signer_delegated_authority_runtime import (
        DelegatedAuthorityRuntimeRequest,
    )

    if not isinstance(value, Mapping):
        raise ValueError("elevated_consensus_authority_request_invalid")
    raw = dict(value)
    if set(raw) != {item.name for item in fields(DelegatedAuthorityRuntimeRequest)}:
        raise ValueError("elevated_consensus_authority_request_schema_invalid")
    raw["allowed_paths"] = tuple(raw["allowed_paths"])
    raw["denied_paths"] = tuple(raw["denied_paths"])
    return DelegatedAuthorityRuntimeRequest(**raw)


def _rehydrate_signing_request(value: Any) -> Any:
    from modules.communication.moltbot_bridge.src.reddog_signer_delegated_authority_runtime import (
        SigningRequest,
    )

    if not isinstance(value, Mapping):
        raise ValueError("elevated_consensus_signing_request_invalid")
    raw = dict(value)
    expected = {item.name for item in fields(SigningRequest)}
    if set(raw) != expected - {"elevated_consensus_proof"}:
        raise ValueError("elevated_consensus_signing_request_schema_invalid")
    raw["elevated_consensus_proof"] = None
    return SigningRequest(**raw)


def _reserve_signer_nonce(
    authority: ConsensusNonceAuthority,
    receipt: ElevatedAuthorityConsensusReceipt,
    signing_request_digest: str,
) -> VerifiedElevatedConsensusSignerReservation | None:
    nonce = canonical_json_digest(
        {
            "consensus_context_digest": canonical_consensus_context_digest(
                receipt.context
            ),
            "signing_request_digest": signing_request_digest,
        }
    )
    try:
        return reserve_elevated_consensus_nonce(
            authority,
            nonce,
            expires_at=receipt.context.expires_at,
            subject="elevated-consensus:" + receipt.receipt_id,
        )
    except Exception:
        return None


__all__ = ["ElevatedConsensusSignerAuthority"]
