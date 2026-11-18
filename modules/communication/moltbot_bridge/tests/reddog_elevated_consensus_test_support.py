"""Test-only signed consensus fixtures for elevated RedDog authority."""

from __future__ import annotations

from dataclasses import replace
from typing import Any
from modules.communication.moltbot_bridge.src.reddog_authority_runtime_store import (
    PrincipalAuthorityRecord,
)
from modules.communication.moltbot_bridge.src.reddog_elevated_authority_consensus_capability import (
    consume_elevated_authority_signing_permit,
)
from modules.communication.moltbot_bridge.src.reddog_elevated_authority_consensus_contract import (
    APPROVE,
    CONSENSUS_SCHEMA_VERSION,
    DECISION_SCHEMA_VERSION,
    ElevatedAuthorityConsensusContext,
    ElevatedAuthorityConsensusReceipt,
    ElevatedAuthorityReviewerDecision,
    canonical_authority_request_digest,
    canonical_consensus_context_digest,
    canonical_consensus_receipt_digest,
    canonical_elevated_signing_request_digest,
)
from modules.communication.moltbot_bridge.src.reddog_elevated_authority_consensus_policy import (
    ElevatedConsensusPolicy,
    elevated_consensus_policy_digest,
)
from modules.communication.moltbot_bridge.src.reddog_elevated_authority_consensus_verification import (
    verify_elevated_authority_consensus,
)
from modules.communication.moltbot_bridge.src.reddog_signer_delegated_authority_runtime import (
    HIGH_AUTHORITY_TIER,
    build_delegated_authority_signing_requests,
)
from modules.communication.moltbot_bridge.src.reddog_signer_optional_authority_bindings import (
    runtime_binding_request_valid,
)
from modules.communication.moltbot_bridge.tests.reddog_elevated_consensus_test_doubles import (
    REVIEWERS,
    TestAuthorRuntimeEvidenceResolver,
    TestConsensusVerifier,
    TestPolicyResolver,
    TestReviewerKeyResolver,
    TestReviewerRuntimeEvidenceResolver,
    TestSovereignAuthorizationResolver,
    sha_digest,
    sign_reviewer_decision,
)


def consensus_policy_fixture() -> ElevatedConsensusPolicy:
    pending = ElevatedConsensusPolicy(
        policy_receipt_id="elevated-consensus-policy:test-v1",
        policy_digest="pending",
        authority_principal_id="authority:consensus",
        reviewer_membership=tuple((row[0], "test", row[1]) for row in REVIEWERS),
        minimum_approvals=2,
        required_roles=("critic", "verifier"),
    )
    return replace(pending, policy_digest=elevated_consensus_policy_digest(pending))


def verified_consensus_for_request(
    request: Any,
    *,
    now: int,
    principal: PrincipalAuthorityRecord | None = None,
):
    sovereign_digest = str(request.sovereign_authorization_digest)
    if not _is_digest(sovereign_digest):
        request = replace(
            request, sovereign_authorization_digest=sha_digest(sovereign_digest)
        )
    principal = principal or _principal_for_request(request)
    has_runtime_binding = runtime_binding_request_valid(request)
    if has_runtime_binding is None:
        raise ValueError("test_consensus_runtime_binding_invalid")
    plan = build_delegated_authority_signing_requests(
        request,
        principal,
        authority_tier=HIGH_AUTHORITY_TIER,
        has_runtime_binding=has_runtime_binding,
    )
    signing_digests = tuple(
        canonical_elevated_signing_request_digest(item) for item in plan[2:]
    )
    policy = consensus_policy_fixture()
    context = _consensus_context(request, policy, signing_digests, now)
    decisions = tuple(
        _decision(row, canonical_consensus_context_digest(context))
        for row in REVIEWERS
    )
    unsigned = ElevatedAuthorityConsensusReceipt(
        schema_version=CONSENSUS_SCHEMA_VERSION,
        receipt_id="pending",
        context=context,
        decisions=decisions,
    )
    receipt = replace(unsigned, receipt_id=canonical_consensus_receipt_digest(unsigned))
    bound_request = replace(request, consensus_receipt_digest=receipt.receipt_id)
    capability = _verify_fixture(receipt, bound_request, policy, now)
    assert capability is not None
    return bound_request, capability, receipt


def sign_with_test_consensus(signer: Any, request: Any, permit: Any, *, now: int):
    """Explicit test-only permit consumption before a deterministic mock sign."""

    proof = consume_elevated_authority_signing_permit(
        permit, signing_request=request, now=now
    )
    if proof is None:
        from modules.communication.moltbot_bridge.src.reddog_signer_delegated_authority_runtime import (
            RuntimeRejectCode,
            SigningResponse,
        )

        return SigningResponse(
            accepted=False,
            rejection_code=RuntimeRejectCode.ELEVATED_CONSENSUS_NOT_VERIFIED,
            no_secret_material_returned=True,
        )
    return signer.sign(request)


def _consensus_context(request, policy, signing_digests, now):
    return ElevatedAuthorityConsensusContext(
        schema_version=CONSENSUS_SCHEMA_VERSION,
        authority_request_digest=canonical_authority_request_digest(request),
        sovereign_authorization_digest=str(request.sovereign_authorization_digest),
        consensus_policy_digest=policy.policy_digest,
        authorized_signing_request_digests=signing_digests,
        required_approvals=2,
        required_roles=("critic", "verifier"),
        nonce=f"consensus-{request.work_authority_nonce}",
        issued_at=now - 5,
        expires_at=now + 300,
    )


def _verify_fixture(receipt, request, policy, now):
    return verify_elevated_authority_consensus(
        consensus_receipt=receipt.to_dict(),
        authority_request=request,
        signature_verifier=TestConsensusVerifier(),
        reviewer_key_resolver=TestReviewerKeyResolver(),
        runtime_evidence_resolver=TestReviewerRuntimeEvidenceResolver(now),
        author_runtime_evidence_resolver=TestAuthorRuntimeEvidenceResolver(
            request, now
        ),
        sovereign_authorization_resolver=TestSovereignAuthorizationResolver(
            request, now
        ),
        policy_resolver=TestPolicyResolver(policy),
        now=now,
    )


def _principal_for_request(request: Any) -> PrincipalAuthorityRecord:
    return PrincipalAuthorityRecord(
        principal_id=request.principal_id,
        principal_provider=request.principal_provider,
        principal_public_key=request.principal_public_key,
        repo_scope=(request.repo_full_name,),
        foundup_scope=(request.foundup_id,),
        verified_subject_digest=sha_digest("verified-subject"),
        reward_account="reward:012",
        owner_dae="dae:012",
    )


def _decision(row: tuple[Any, ...], context_digest: str):
    principal_id, role, model_id, public_key, secret = row
    unsigned = ElevatedAuthorityReviewerDecision(
        schema_version=DECISION_SCHEMA_VERSION,
        decision_id="decision:" + principal_id,
        reviewer_principal_id=principal_id,
        reviewer_principal_provider="test",
        reviewer_public_key=public_key,
        reviewer_key_epoch="reviewer-epoch-1",
        reviewer_role=role,
        reviewer_model_id=model_id,
        model_selection_receipt_id=f"selection:{principal_id}",
        model_selection_digest=sha_digest(f"selection:{principal_id}"),
        model_runtime_binding_receipt_id=f"binding:{principal_id}",
        model_runtime_binding_digest=sha_digest(f"binding:{principal_id}"),
        consensus_context_digest=context_digest,
        decision=APPROVE,
        signature="pending",
    )
    return replace(unsigned, signature=sign_reviewer_decision(unsigned, secret))


def _is_digest(value: str) -> bool:
    return bool(
        len(value) == 71
        and value.startswith("sha256:")
        and all(char in "0123456789abcdef" for char in value[7:])
    )
