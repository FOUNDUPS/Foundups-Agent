"""Opaque-capability regressions for elevated RedDog consensus."""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace

import pytest

from modules.communication.moltbot_bridge.src.reddog_elevated_authority_consensus_capability import (
    VerifiedElevatedAuthorityConsensusCapability,
    consume_elevated_authority_signing_permit,
    prepare_elevated_authority_signing_permit,
)
from modules.communication.moltbot_bridge.src.reddog_elevated_authority_consensus_rehydration import (
    MAX_CONSENSUS_DECISIONS,
    MAX_CONSENSUS_RECEIPT_BYTES,
    rehydrate_consensus_receipt,
)
from modules.communication.moltbot_bridge.src.reddog_isolated_signer_socket_protocol import (
    DEFAULT_SIGNER_SOCKET_MAX_REQUEST_BYTES,
)
from modules.communication.moltbot_bridge.src.reddog_signer_delegated_authority_runtime import (
    HIGH_AUTHORITY_TIER,
    build_delegated_authority_signing_requests,
)
from modules.communication.moltbot_bridge.tests.reddog_elevated_consensus_test_support import (
    verified_consensus_for_request,
)
from modules.communication.moltbot_bridge.tests.test_reddog_signer_delegated_authority_runtime import (
    _NOW,
    _principal,
    _request,
)


def _valid():
    return verified_consensus_for_request(_request(), now=_NOW)


def _signing_requests(request):
    return build_delegated_authority_signing_requests(
        request, _principal(), authority_tier=HIGH_AUTHORITY_TIER,
        has_runtime_binding=True,
    )[2:]


def test_valid_consensus_mints_exact_two_child_signing_uses() -> None:
    request, capability, receipt = _valid()
    signing_requests = _signing_requests(request)
    permit = prepare_elevated_authority_signing_permit(
        capability, authority_request=request,
        signing_requests=signing_requests, now=_NOW,
    )

    assert receipt.receipt_id == request.consensus_receipt_digest
    assert permit is not None
    proofs = [
        consume_elevated_authority_signing_permit(
            permit, signing_request=item, now=_NOW
        )
        for item in signing_requests
    ]
    assert all(
        proof and proof["target_signing_request"] == item.to_dict()
        for proof, item in zip(proofs, signing_requests)
    )
    assert consume_elevated_authority_signing_permit(
        permit, signing_request=signing_requests[0], now=_NOW
    ) is None


def test_returned_proof_mutation_cannot_poison_remaining_child() -> None:
    request, capability, _ = _valid()
    signing_requests = _signing_requests(request)
    permit = prepare_elevated_authority_signing_permit(
        capability, authority_request=request,
        signing_requests=signing_requests, now=_NOW,
    )
    first = consume_elevated_authority_signing_permit(
        permit, signing_request=signing_requests[0], now=_NOW
    )
    assert first is not None
    first["consensus_receipt"]["context"]["nonce"] = "attacker-mutated"
    second = consume_elevated_authority_signing_permit(
        permit, signing_request=signing_requests[1], now=_NOW
    )
    assert second is not None
    assert second["consensus_receipt"]["context"]["nonce"] != "attacker-mutated"


def test_canonical_proof_fits_bounded_socket_transport() -> None:
    request, capability, _ = _valid()
    signing_requests = _signing_requests(request)
    permit = prepare_elevated_authority_signing_permit(
        capability, authority_request=request,
        signing_requests=signing_requests, now=_NOW,
    )
    proof = consume_elevated_authority_signing_permit(
        permit, signing_request=signing_requests[0], now=_NOW
    )
    proof_bytes = len(
        json.dumps(proof, sort_keys=True, separators=(",", ":")).encode("ascii")
    )
    assert proof_bytes + 8192 <= DEFAULT_SIGNER_SOCKET_MAX_REQUEST_BYTES


def test_rehydration_rejects_oversized_or_excessive_decision_receipts() -> None:
    _, _, receipt = _valid()
    too_many = receipt.to_dict()
    too_many["decisions"] *= MAX_CONSENSUS_DECISIONS + 1
    oversized = receipt.to_dict()
    oversized["decisions"][0]["signature"] = "x" * MAX_CONSENSUS_RECEIPT_BYTES

    with pytest.raises(ValueError):
        rehydrate_consensus_receipt(too_many)
    with pytest.raises(ValueError):
        rehydrate_consensus_receipt(oversized)


def test_wrong_request_does_not_destroy_capability() -> None:
    request, capability, _ = _valid()
    signing_requests = _signing_requests(request)
    changed = replace(request, work_order_digest="sha256:" + "f" * 64)
    assert prepare_elevated_authority_signing_permit(
        capability, authority_request=changed,
        signing_requests=signing_requests, now=_NOW,
    ) is None
    assert prepare_elevated_authority_signing_permit(
        capability, authority_request=request,
        signing_requests=signing_requests, now=_NOW,
    ) is not None


def test_concurrent_capability_consumers_have_one_winner() -> None:
    request, capability, _ = _valid()
    signing_requests = _signing_requests(request)

    def consume():
        return prepare_elevated_authority_signing_permit(
            capability, authority_request=request,
            signing_requests=signing_requests, now=_NOW,
        )

    with ThreadPoolExecutor(max_workers=8) as executor:
        permits = list(executor.map(lambda _: consume(), range(8)))
    assert sum(item is not None for item in permits) == 1


def test_capability_is_opaque() -> None:
    with pytest.raises(TypeError):
        VerifiedElevatedAuthorityConsensusCapability()
