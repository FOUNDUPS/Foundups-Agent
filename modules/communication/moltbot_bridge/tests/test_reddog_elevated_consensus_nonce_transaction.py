"""Transactional consensus nonce regressions at the Ed25519 signer boundary."""

from __future__ import annotations

from dataclasses import replace
from concurrent.futures import ThreadPoolExecutor

from modules.communication.moltbot_bridge.tests.reddog_elevated_consensus_e2e_support import (
    NOW,
)
from modules.communication.moltbot_bridge.tests.reddog_elevated_consensus_nonce_test_support import (
    build_grant_signing_case,
)
from modules.communication.moltbot_bridge.tests.reddog_elevated_consensus_test_doubles import (
    TestConsensusNonceAuthority,
)


def test_rate_rejection_rolls_back_consensus_nonce_for_later_window(tmp_path) -> None:
    nonce_authority = TestConsensusNonceAuthority()
    backend, request, peer = build_grant_signing_case(
        tmp_path, nonce_authority
    )
    policy, rate = backend.secret_grant_authority_policy, backend.secret_grant_rate_authority
    for _ in range(policy.rate_limit_max_requests):
        assert rate.consume_issuance_attempt(
            authority_subject=policy.issuer_public_key,
            now_epoch=NOW,
            window_seconds=policy.rate_limit_window_seconds,
            max_requests=policy.rate_limit_max_requests,
        )
    clock = [NOW]
    backend = replace(backend, proposal_clock=lambda: clock[0])

    assert backend.sign(request, peer).accepted is False
    assert nonce_authority.reserved == {} and nonce_authority.consumed == set()
    clock[0] += policy.rate_limit_window_seconds
    assert backend.sign(request, peer).accepted is True
    assert len(nonce_authority.consumed) == 1


def test_signature_failure_rolls_back_consensus_nonce_for_retry(tmp_path) -> None:
    class FailingPrivateKey:
        def __init__(self, delegate):
            self.delegate = delegate

        def public_key(self):
            return self.delegate.public_key()

        def sign(self, _payload):
            raise ValueError("test signing failure")

    nonce_authority = TestConsensusNonceAuthority()
    backend, request, peer = build_grant_signing_case(
        tmp_path, nonce_authority
    )
    failed = replace(backend, private_key=FailingPrivateKey(backend.private_key))

    assert failed.sign(request, peer).accepted is False
    assert nonce_authority.reserved == {} and nonce_authority.consumed == set()
    assert backend.sign(request, peer).accepted is True
    assert len(nonce_authority.consumed) == 1


def test_mismatched_proof_never_signs_or_exhausts_rate_limit(tmp_path) -> None:
    class CountingPrivateKey:
        def __init__(self, delegate):
            self.delegate = delegate
            self.sign_calls = 0

        def public_key(self):
            return self.delegate.public_key()

        def sign(self, payload):
            self.sign_calls += 1
            return self.delegate.sign(payload)

    nonce_authority = TestConsensusNonceAuthority()
    backend, request, peer = build_grant_signing_case(tmp_path, nonce_authority)
    key = CountingPrivateKey(backend.private_key)
    guarded = replace(backend, private_key=key)
    proof = dict(request.elevated_consensus_proof or {})
    target = dict(proof["target_signing_request"])
    target["requested_operation"] = "attacker-selected-operation"
    proof["target_signing_request"] = target
    invalid = replace(request, elevated_consensus_proof=proof)

    for _ in range(10):
        assert guarded.sign(invalid, peer).accepted is False
    assert key.sign_calls == 0
    assert nonce_authority.reserved == {} and nonce_authority.consumed == set()
    assert guarded.sign(request, peer).accepted is True
    assert key.sign_calls == 2


def test_concurrent_real_signer_path_has_one_accepted_signature(tmp_path) -> None:
    nonce_authority = TestConsensusNonceAuthority()
    backend, request, peer = build_grant_signing_case(tmp_path, nonce_authority)
    with ThreadPoolExecutor(max_workers=8) as executor:
        responses = list(executor.map(lambda _: backend.sign(request, peer), range(8)))
    assert sum(response.accepted is True for response in responses) == 1
    assert len(nonce_authority.consumed) == 1
