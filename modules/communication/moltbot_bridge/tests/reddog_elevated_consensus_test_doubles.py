"""Test-only authority resolvers for elevated RedDog consensus."""

from __future__ import annotations

import hashlib
import hmac
import threading
from typing import Any

from modules.communication.moltbot_bridge.src.reddog_elevated_authority_consensus_contract import (
    canonical_authority_request_digest,
    canonical_reviewer_decision_signing_input,
)
from modules.communication.moltbot_bridge.src.reddog_elevated_authority_consensus_policy import (
    AuthorRuntimeEvidence,
    ElevatedConsensusPolicy,
    ReviewerKeyAuthority,
    ReviewerRuntimeEvidence,
    SovereignAuthorizationEvidence,
)

REVIEWERS = (
    ("reviewer:critic", "critic", "model:critic", "pub:critic", b"critic-secret"),
    ("reviewer:verifier", "verifier", "model:verifier", "pub:verifier", b"verifier-secret"),
)


class TestAuthorRuntimeEvidenceResolver:
    __test__ = False

    def __init__(self, request: Any, now: int) -> None:
        self.request = request
        self.now = now

    def resolve(self, verification_receipt_id: str):
        request = self.request
        if verification_receipt_id != request.model_runtime_binding_verification_receipt_id:
            return None
        return AuthorRuntimeEvidence(
            model_selection_receipt_id=request.model_selection_receipt_id,
            model_selection_digest=request.model_selection_digest,
            model_runtime_binding_receipt_id=request.model_runtime_binding_receipt_id,
            model_runtime_binding_digest=request.model_runtime_binding_digest,
            verification_receipt_id=verification_receipt_id,
            verification_digest=request.model_runtime_binding_verification_digest,
            expires_at=self.now + 600,
        )


class TestConsensusVerifier:
    __test__ = False

    def verify(self, public_key: str, signing_input: str, signature: str) -> bool:
        secret = {row[3]: row[4] for row in REVIEWERS}.get(public_key)
        if secret is None:
            return False
        expected = hmac.new(
            secret, signing_input.encode("utf-8"), hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(expected, signature)


class TestReviewerKeyResolver:
    __test__ = False

    def resolve(self, principal_id: str, principal_provider: str):
        if principal_provider != "test":
            return None
        row = next((item for item in REVIEWERS if item[0] == principal_id), None)
        return (
            ReviewerKeyAuthority(
                public_key=row[3], key_epoch="reviewer-epoch-1", expires_at=10**12
            )
            if row is not None
            else None
        )


class TestReviewerRuntimeEvidenceResolver:
    __test__ = False

    def __init__(self, now: int) -> None:
        self.now = now

    def resolve(self, reviewer_principal_id: str, selection_id: str, binding_id: str):
        row = next((item for item in REVIEWERS if item[0] == reviewer_principal_id), None)
        expected_selection = f"selection:{reviewer_principal_id}"
        expected_binding = f"binding:{reviewer_principal_id}"
        if (
            row is None
            or selection_id != expected_selection
            or binding_id != expected_binding
        ):
            return None
        return ReviewerRuntimeEvidence(
            reviewer_model_id=row[2],
            model_selection_receipt_id=expected_selection,
            model_selection_digest=sha_digest(expected_selection),
            model_runtime_binding_receipt_id=expected_binding,
            model_runtime_binding_digest=sha_digest(expected_binding),
            expires_at=self.now + 300,
        )


class TestPolicyResolver:
    __test__ = False

    def __init__(self, policy: ElevatedConsensusPolicy | None = None) -> None:
        if policy is None:
            from modules.communication.moltbot_bridge.tests.reddog_elevated_consensus_test_support import (
                consensus_policy_fixture,
            )

            policy = consensus_policy_fixture()
        self.policy = policy

    def resolve(self, policy_digest: str):
        return self.policy if policy_digest == self.policy.policy_digest else None


class TestSovereignAuthorizationResolver:
    __test__ = False

    def __init__(self, request: Any, now: int) -> None:
        self.evidence = SovereignAuthorizationEvidence(
            authorization_digest=str(request.sovereign_authorization_digest),
            authority_request_digest=canonical_authority_request_digest(request),
            principal_id=request.principal_id,
            principal_provider=request.principal_provider,
            principal_public_key=request.principal_public_key,
            reddog_id=request.reddog_id,
            reddog_public_key=request.reddog_public_key,
            repo_full_name=request.repo_full_name,
            foundup_id=request.foundup_id,
            work_order_id=request.work_order_id,
            key_epoch=request.key_epoch,
            expires_at=now + 300,
        )

    def resolve(self, authorization_digest: str):
        return (
            self.evidence
            if authorization_digest == self.evidence.authorization_digest
            else None
        )


class TestConsensusNonceAuthority:
    __test__ = False

    def __init__(self) -> None:
        self.reserved: dict[str, tuple[str, str, int]] = {}
        self.consumed: set[tuple[str, str]] = set()
        self.lock = threading.Lock()

    def reserve(self, nonce: str, *, expires_at: int, subject: str):
        with self.lock:
            key = (subject, nonce)
            if key in self.consumed or any(
                item[:2] == key for item in self.reserved.values()
            ):
                return None
            token = sha_digest(subject + ":" + nonce)
            self.reserved[token] = (subject, nonce, expires_at)
            return token

    def commit(self, reservation: str) -> None:
        with self.lock:
            subject, nonce, _ = self.reserved.pop(reservation)
            self.consumed.add((subject, nonce))

    def rollback(self, reservation: str) -> None:
        with self.lock:
            self.reserved.pop(reservation, None)


def sign_reviewer_decision(unsigned: Any, secret: bytes) -> str:
    return hmac.new(
        secret,
        canonical_reviewer_decision_signing_input(unsigned).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def sha_digest(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


__all__ = [
    "REVIEWERS",
    "TestAuthorRuntimeEvidenceResolver",
    "TestConsensusNonceAuthority",
    "TestConsensusVerifier",
    "TestPolicyResolver",
    "TestReviewerKeyResolver",
    "TestReviewerRuntimeEvidenceResolver",
    "TestSovereignAuthorizationResolver",
    "sha_digest",
    "sign_reviewer_decision",
]
