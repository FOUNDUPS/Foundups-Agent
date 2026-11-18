"""Authority-evidence regressions for elevated RedDog consensus."""

from __future__ import annotations

import hashlib
import hmac
from dataclasses import replace

from modules.communication.moltbot_bridge.src.reddog_elevated_authority_consensus_contract import (
    canonical_authority_request_digest,
    canonical_consensus_receipt_digest,
    canonical_reviewer_decision_signing_input,
)
from modules.communication.moltbot_bridge.src.reddog_elevated_authority_consensus_rehydration import (
    rehydrate_consensus_receipt,
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
    consensus_policy_fixture,
    verified_consensus_for_request,
)
from modules.communication.moltbot_bridge.tests.test_reddog_signer_delegated_authority_runtime import (
    _NOW,
    _request,
)


def _valid():
    return verified_consensus_for_request(_request(), now=_NOW)


def _verify(receipt, request, *, now=_NOW, policy=None, sovereign=None):
    policy = policy or consensus_policy_fixture()
    return verify_elevated_authority_consensus(
        consensus_receipt=receipt,
        authority_request=request,
        signature_verifier=TestConsensusVerifier(),
        reviewer_key_resolver=TestReviewerKeyResolver(),
        runtime_evidence_resolver=TestReviewerRuntimeEvidenceResolver(_NOW),
        author_runtime_evidence_resolver=TestAuthorRuntimeEvidenceResolver(
            request, _NOW
        ),
        sovereign_authorization_resolver=(
            sovereign or TestSovereignAuthorizationResolver(request, _NOW)
        ),
        policy_resolver=TestPolicyResolver(policy),
        now=now,
    )


def test_attacker_rehashed_receipt_with_changed_decision_rejects() -> None:
    request, _, receipt = _valid()
    raw = receipt.to_dict()
    raw["decisions"][0]["reviewer_role"] = "verifier"
    raw["receipt_id"] = canonical_consensus_receipt_digest(
        rehydrate_consensus_receipt(raw)
    )
    request = replace(request, consensus_receipt_digest=raw["receipt_id"])
    assert _verify(raw, request) is None


def test_duplicate_reviewer_does_not_satisfy_quorum() -> None:
    request, _, receipt = _valid()
    duplicate = replace(
        receipt, receipt_id="pending",
        decisions=(receipt.decisions[0], receipt.decisions[0]),
    )
    duplicate = replace(
        duplicate, receipt_id=canonical_consensus_receipt_digest(duplicate)
    )
    request = replace(request, consensus_receipt_digest=duplicate.receipt_id)
    assert _verify(duplicate.to_dict(), request) is None


def test_two_reviewer_aliases_cannot_reuse_one_public_key() -> None:
    request, _, receipt = _valid()
    second = replace(
        receipt.decisions[1], reviewer_public_key="pub:critic", signature="pending"
    )
    second = replace(
        second,
        signature=hmac.new(
            b"critic-secret",
            canonical_reviewer_decision_signing_input(second).encode("utf-8"),
            hashlib.sha256,
        ).hexdigest(),
    )
    forged = replace(
        receipt, receipt_id="pending", decisions=(receipt.decisions[0], second)
    )
    forged = replace(forged, receipt_id=canonical_consensus_receipt_digest(forged))
    request = replace(request, consensus_receipt_digest=forged.receipt_id)

    class AliasedKeyResolver(TestReviewerKeyResolver):
        def resolve(self, principal_id: str, principal_provider: str):
            resolved = super().resolve("reviewer:critic", principal_provider)
            return resolved if principal_id.startswith("reviewer:") else None

    result = verify_elevated_authority_consensus(
        consensus_receipt=forged.to_dict(), authority_request=request,
        signature_verifier=TestConsensusVerifier(),
        reviewer_key_resolver=AliasedKeyResolver(),
        runtime_evidence_resolver=TestReviewerRuntimeEvidenceResolver(_NOW),
        author_runtime_evidence_resolver=TestAuthorRuntimeEvidenceResolver(
            request, _NOW
        ),
        sovereign_authorization_resolver=TestSovereignAuthorizationResolver(
            request, _NOW
        ),
        policy_resolver=TestPolicyResolver(), now=_NOW,
    )
    assert result is None


def test_revoked_reviewer_key_epoch_rejects() -> None:
    request, _, receipt = _valid()
    result = verify_elevated_authority_consensus(
        consensus_receipt=receipt.to_dict(), authority_request=request,
        signature_verifier=TestConsensusVerifier(),
        reviewer_key_resolver=TestReviewerKeyResolver(),
        runtime_evidence_resolver=TestReviewerRuntimeEvidenceResolver(_NOW),
        author_runtime_evidence_resolver=TestAuthorRuntimeEvidenceResolver(
            request, _NOW
        ),
        sovereign_authorization_resolver=TestSovereignAuthorizationResolver(
            request, _NOW
        ),
        policy_resolver=TestPolicyResolver(), now=_NOW,
        revoked_key_epochs=frozenset({"reviewer-epoch-1"}),
    )
    assert result is None


def test_stale_consensus_rejects() -> None:
    request, _, receipt = _valid()
    assert _verify(receipt.to_dict(), request, now=_NOW + 301) is None


def test_attacker_selected_sovereign_digest_rejects() -> None:
    request, _, receipt = _valid()
    forged = replace(request, sovereign_authorization_digest="sha256:" + "e" * 64)
    assert _verify(
        receipt.to_dict(), forged,
        sovereign=TestSovereignAuthorizationResolver(request, _NOW),
    ) is None


def test_parent_digest_excludes_only_self_referential_proof_identifiers() -> None:
    request = _request()
    changed_proofs = replace(
        request, consensus_receipt_digest="sha256:" + "d" * 64,
        sovereign_authorization_digest="sha256:" + "e" * 64,
    )
    changed_scope = replace(request, foundup_id="foundup-other")
    assert canonical_authority_request_digest(changed_proofs) == (
        canonical_authority_request_digest(request)
    )
    assert canonical_authority_request_digest(changed_scope) != (
        canonical_authority_request_digest(request)
    )


def test_self_selected_policy_rejects() -> None:
    request, _, receipt = _valid()
    weak = replace(
        consensus_policy_fixture(),
        policy_receipt_id="elevated-consensus-policy:weak",
        minimum_approvals=1, required_roles=("critic",),
        policy_digest="sha256:" + "a" * 64,
    )
    assert _verify(receipt.to_dict(), request, policy=weak) is None


def test_verification_does_not_consume_signer_nonce() -> None:
    request, _, receipt = _valid()
    assert _verify(receipt.to_dict(), request) is not None
    assert _verify(receipt.to_dict(), request) is not None
