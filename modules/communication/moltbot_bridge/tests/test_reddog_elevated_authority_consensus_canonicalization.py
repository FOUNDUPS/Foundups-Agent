"""Canonical-byte regressions for elevated consensus child requests."""

from __future__ import annotations

from dataclasses import replace

import pytest

from modules.communication.moltbot_bridge.src.reddog_elevated_authority_consensus_contract import (
    canonical_elevated_signing_request_digest,
    canonical_json_digest,
)
from modules.communication.moltbot_bridge.src.reddog_signer_delegated_authority_runtime import (
    HIGH_AUTHORITY_TIER,
    build_delegated_authority_signing_requests,
)
from modules.communication.moltbot_bridge.tests.test_reddog_signer_delegated_authority_runtime import (
    _principal,
    _request,
)


def _child_request():
    return build_delegated_authority_signing_requests(
        _request(),
        _principal(),
        authority_tier=HIGH_AUTHORITY_TIER,
        has_runtime_binding=True,
    )[2]


@pytest.mark.parametrize("mutation", ["spacing", "duplicate"])
def test_child_digest_rejects_noncanonical_signed_bytes(mutation: str) -> None:
    child = _child_request()
    altered = (
        child.signing_input.replace(":", ": ", 1)
        if mutation == "spacing"
        else child.signing_input.replace("{", '{"nonce":"attacker",', 1)
    )
    forged = replace(
        child,
        signing_input=altered,
        payload_digest=canonical_json_digest({"signing_input": altered}),
    )

    with pytest.raises(ValueError):
        canonical_elevated_signing_request_digest(forged)


def test_child_digest_rejects_wrong_payload_digest() -> None:
    with pytest.raises(ValueError):
        canonical_elevated_signing_request_digest(
            replace(_child_request(), payload_digest="sha256:" + "0" * 64)
        )


def test_child_digest_accepts_exact_canonical_bytes() -> None:
    assert canonical_elevated_signing_request_digest(_child_request()).startswith(
        "sha256:"
    )
