"""Signer-boundary regressions for elevated RedDog consensus."""

from __future__ import annotations

from modules.communication.moltbot_bridge.src.reddog_elevated_authority_consensus_capability import (
    consume_elevated_authority_signing_permit,
    prepare_elevated_authority_signing_permit,
)
from modules.communication.moltbot_bridge.src.reddog_elevated_authority_consensus_verification import (
    ElevatedConsensusSignerAuthority,
)
from modules.communication.moltbot_bridge.src.reddog_elevated_consensus_signer_reservation import (
    rollback_elevated_consensus_nonce,
)
from modules.communication.moltbot_bridge.src.reddog_signer_delegated_authority_runtime import (
    HIGH_AUTHORITY_TIER,
    build_delegated_authority_signing_requests,
)
from modules.communication.moltbot_bridge.src.reddog_signer_secret_access_grant_contract import (
    signer_secret_access_request_digest,
)
from modules.communication.moltbot_bridge.tests.reddog_elevated_consensus_test_doubles import (
    TestConsensusNonceAuthority,
)
from modules.communication.moltbot_bridge.tests.reddog_elevated_consensus_test_support import (
    TestAuthorRuntimeEvidenceResolver,
    TestConsensusVerifier,
    TestPolicyResolver,
    TestReviewerKeyResolver,
    TestReviewerRuntimeEvidenceResolver,
    TestSovereignAuthorizationResolver,
    verified_consensus_for_request,
)
from modules.communication.moltbot_bridge.tests.test_reddog_signer_delegated_authority_runtime import (
    _NOW,
    _principal,
    _request,
)


def _proof_and_authority():
    request, capability, _ = verified_consensus_for_request(_request(), now=_NOW)
    signing_requests = build_delegated_authority_signing_requests(
        request, _principal(), authority_tier=HIGH_AUTHORITY_TIER,
        has_runtime_binding=True,
    )[2:]
    permit = prepare_elevated_authority_signing_permit(
        capability, authority_request=request,
        signing_requests=signing_requests, now=_NOW,
    )
    proof = consume_elevated_authority_signing_permit(
        permit, signing_request=signing_requests[0], now=_NOW
    )
    assert proof is not None
    digest = signer_secret_access_request_digest(signing_requests[0].to_dict())
    authority = ElevatedConsensusSignerAuthority(
        signature_verifier=TestConsensusVerifier(),
        reviewer_key_resolver=TestReviewerKeyResolver(),
        runtime_evidence_resolver=TestReviewerRuntimeEvidenceResolver(_NOW),
        author_runtime_evidence_resolver=TestAuthorRuntimeEvidenceResolver(
            request, _NOW
        ),
        sovereign_authorization_resolver=TestSovereignAuthorizationResolver(
            request, _NOW
        ),
        policy_resolver=TestPolicyResolver(),
        nonce_authority=TestConsensusNonceAuthority(),
    )
    return proof, digest, authority


def test_signer_reverifies_full_grant_request_without_committing_nonce() -> None:
    proof, digest, authority = _proof_and_authority()
    reservation = authority.reserve(
        proof, signing_request_digest=digest, now=_NOW
    )
    assert reservation is not None
    assert authority.reserve(proof, signing_request_digest=digest, now=_NOW) is None
    assert authority.reserve(
        proof, signing_request_digest="sha256:" + "0" * 64, now=_NOW
    ) is None
    rollback_elevated_consensus_nonce(reservation)
    assert authority.reserve(proof, signing_request_digest=digest, now=_NOW) is not None
