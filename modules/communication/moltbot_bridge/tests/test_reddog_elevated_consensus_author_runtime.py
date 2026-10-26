"""Author-runtime and reviewer-provider trust-boundary regressions."""

from __future__ import annotations

import hashlib
import hmac
from dataclasses import replace

from modules.communication.moltbot_bridge.src.reddog_elevated_authority_consensus_contract import (
    canonical_consensus_receipt_digest,
    canonical_reviewer_decision_signing_input,
)
from modules.communication.moltbot_bridge.src.reddog_elevated_authority_consensus_evidence import (
    author_runtime_evidence_matches,
)
from modules.communication.moltbot_bridge.src.reddog_elevated_authority_consensus_policy import (
    AuthorRuntimeEvidence,
)
from modules.communication.moltbot_bridge.src.reddog_elevated_authority_consensus_verification import (
    verify_elevated_authority_consensus,
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
    _request,
)


def test_absent_or_malformed_author_runtime_evidence_rejects() -> None:
    request = _request()
    absent = replace(
        request,
        model_selection_receipt_id=None,
        model_selection_digest=None,
        model_runtime_binding_receipt_id=None,
        model_runtime_binding_digest=None,
        model_runtime_binding_verification_receipt_id=None,
        model_runtime_binding_verification_digest=None,
    )
    malformed = replace(
        request,
        model_selection_digest="sha256:x",
        model_runtime_binding_digest="sha256:y",
        model_runtime_binding_verification_digest="sha256:z",
    )
    assert not author_runtime_evidence_matches(
        TestAuthorRuntimeEvidenceResolver(absent, _NOW).resolve(None), absent, _NOW
    )
    assert not author_runtime_evidence_matches(
        TestAuthorRuntimeEvidenceResolver(malformed, _NOW).resolve(
            malformed.model_runtime_binding_verification_receipt_id
        ),
        malformed,
        _NOW,
    )


def test_substituted_author_runtime_evidence_rejects_capability() -> None:
    request, _, receipt = verified_consensus_for_request(_request(), now=_NOW)

    class SubstitutedResolver:
        def resolve(self, _receipt_id):
            return AuthorRuntimeEvidence(
                model_selection_receipt_id=str(request.model_selection_receipt_id),
                model_selection_digest="sha256:" + ("0" * 64),
                model_runtime_binding_receipt_id=str(
                    request.model_runtime_binding_receipt_id
                ),
                model_runtime_binding_digest=str(request.model_runtime_binding_digest),
                verification_receipt_id=str(
                    request.model_runtime_binding_verification_receipt_id
                ),
                verification_digest=str(
                    request.model_runtime_binding_verification_digest
                ),
                expires_at=_NOW + 300,
            )

    assert _verify(receipt.to_dict(), request, SubstitutedResolver()) is None


def test_authorized_reviewer_id_with_unapproved_provider_rejects() -> None:
    request, _, receipt = verified_consensus_for_request(_request(), now=_NOW)
    decision = replace(
        receipt.decisions[0],
        reviewer_principal_provider="attacker-provider",
        signature="pending",
    )
    decision = replace(
        decision,
        signature=hmac.new(
            b"critic-secret",
            canonical_reviewer_decision_signing_input(decision).encode("utf-8"),
            hashlib.sha256,
        ).hexdigest(),
    )
    forged = replace(
        receipt,
        receipt_id="pending",
        decisions=(decision, receipt.decisions[1]),
    )
    forged = replace(forged, receipt_id=canonical_consensus_receipt_digest(forged))
    request = replace(request, consensus_receipt_digest=forged.receipt_id)

    class AlternateProviderResolver(TestReviewerKeyResolver):
        def resolve(self, principal_id, _principal_provider):
            return super().resolve(principal_id, "test")

    assert _verify(
        forged.to_dict(), request, TestAuthorRuntimeEvidenceResolver(request, _NOW),
        key_resolver=AlternateProviderResolver(),
    ) is None


def _verify(receipt, request, author_resolver, *, key_resolver=None):
    return verify_elevated_authority_consensus(
        consensus_receipt=receipt,
        authority_request=request,
        signature_verifier=TestConsensusVerifier(),
        reviewer_key_resolver=key_resolver or TestReviewerKeyResolver(),
        runtime_evidence_resolver=TestReviewerRuntimeEvidenceResolver(_NOW),
        author_runtime_evidence_resolver=author_resolver,
        sovereign_authorization_resolver=TestSovereignAuthorizationResolver(
            request, _NOW
        ),
        policy_resolver=TestPolicyResolver(),
        now=_NOW,
    )
