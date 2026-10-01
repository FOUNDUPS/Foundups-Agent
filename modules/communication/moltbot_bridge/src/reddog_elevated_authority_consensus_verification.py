"""Canonical outer verification for elevated-authority consensus receipts."""

from __future__ import annotations

import json
from typing import Any, Mapping

from modules.communication.moltbot_bridge.src.reddog_elevated_authority_consensus_capability import (
    VerifiedElevatedAuthorityConsensusCapability,
    _mint_elevated_authority_consensus_capability,
)
from modules.communication.moltbot_bridge.src.reddog_elevated_authority_consensus_contract import (
    canonical_authority_request_digest,
    EFFECT_DECISION_SCHEMA_VERSION, EFFECT_DECISION_SIGNING_PREFIX,
)
from modules.communication.moltbot_bridge.src.reddog_elevated_authority_consensus_effect_context import (
    canonical_effect_approval_context_digest, effect_approval_context_matches,
)
from modules.communication.moltbot_bridge.src.reddog_elevated_authority_consensus_evidence import (
    author_runtime_evidence_matches,
    consensus_receipt_matches,
)
from modules.communication.moltbot_bridge.src.reddog_elevated_authority_consensus_policy import (
    AuthorRuntimeEvidenceResolver, elevated_consensus_policy_valid,
    ElevatedConsensusPolicyResolver,
    ReviewerKeyAuthorityResolver,
    ReviewerRuntimeEvidenceResolver,
    SovereignAuthorizationEvidenceResolver,
)
from modules.communication.moltbot_bridge.src.reddog_elevated_authority_consensus_rehydration import (
    rehydrate_consensus_receipt, rehydrate_effect_reviewer_decision,
)
from modules.communication.moltbot_bridge.src.reddog_elevated_authority_consensus_reviewer_evidence import (
    consensus_decisions_verify, _verified_decision_evidence,
    _forbidden_reviewer_ids, _reviewer_membership,
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



def verify_effect_reviewer_decision(
    *, decision, context, authority_request, target, expected_target, policy,
    signature_verifier, reviewer_key_resolver, runtime_evidence_resolver,
    now: int, revoked_key_epochs: frozenset[str] = frozenset(),
) -> bool:
    """Check one review relative to supplied evidence, not quorum or authority."""
    try:
        review = rehydrate_effect_reviewer_decision(decision)
        if not effect_approval_context_matches(
            context, parent=authority_request, target=target,
            expected_target=expected_target, now=now,
        ) or not _effect_policy_matches(context, policy):
            return False
        if any((
            _reviewer_membership(review) not in policy.reviewer_membership,
            review.reviewer_principal_id in _forbidden_reviewer_ids(authority_request),
            review.reviewer_public_key in {
                authority_request.principal_public_key, authority_request.reddog_public_key,
            },
            review.model_runtime_binding_digest == authority_request.model_runtime_binding_digest,
        )):
            return False
        key, evidence = _verified_decision_evidence(
            review, canonical_effect_approval_context_digest(context),
            signature_verifier, reviewer_key_resolver, runtime_evidence_resolver,
            now, revoked_key_epochs, schema_version=EFFECT_DECISION_SCHEMA_VERSION,
            signing_input=_effect_reviewer_signing_input,
        )
        return key is not None and evidence is not None
    except Exception:
        return False


def verify_current_effect_reviewer_decision(
    *, owner_config_path, repo_root, decision, context, authority_request, target,
    expected_target, policy, runtime_evidence_resolver,
    revoked_key_epochs: frozenset[str] = frozenset(),
) -> bool:
    """Verify one review with current scoped keys; runtime evidence is supplied."""
    from .reddog_current_effect_reviewer_verification import verify_current_effect_review

    return verify_current_effect_review(
        owner_config_path=owner_config_path, repo_root=repo_root, decision=decision,
        context=context, authority_request=authority_request, target=target,
        expected_target=expected_target, policy=policy,
        runtime_evidence_resolver=runtime_evidence_resolver,
        revoked_key_epochs=revoked_key_epochs,
    )


def _effect_policy_matches(context, policy) -> bool:
    return elevated_consensus_policy_valid(policy) and all((
        context.consensus_policy_digest == policy.policy_digest,
        context.required_approvals == policy.minimum_approvals,
        context.required_roles == policy.required_roles,
        context.expires_at - context.issued_at <= policy.maximum_ttl_seconds,
    ))


def _effect_reviewer_signing_input(decision) -> str:
    payload = decision.to_dict()
    payload.pop("signature")
    return EFFECT_DECISION_SIGNING_PREFIX + "." + json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
        allow_nan=False,
    )


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
    "verify_elevated_authority_consensus", "verify_effect_reviewer_decision",
    "verify_current_effect_reviewer_decision",
]
