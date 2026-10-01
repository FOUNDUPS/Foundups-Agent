"""Real test-only effect-review signatures; supplied resolver provenance is unproven."""

import base64
from copy import deepcopy
from dataclasses import replace
import json

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
import pytest

from modules.communication.moltbot_bridge.src.reddog_ed25519_signature_verifier_backend import (
    Ed25519SignatureVerifier,
)
from modules.communication.moltbot_bridge.tests.test_reddog_elevated_authority_consensus_effect_reviewer import (
    _case,
)


CASES = (
    "valid_effect_signature", "signed_payload_tampered", "signature_bit_tampered",
    "foreign_key_consistently_rebound", "delegated_prefix_signature",
    "unrelated_message_signature",
)


def _wire(prefix, raw):
    return prefix + base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _public_key(private_key):
    raw = private_key.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw,
    )
    return _wire("ed25519-pub-v1:", raw)


def _independent_preimage(decision, prefix="reddog-effect-consensus-review.v1."):
    payload = {key: value for key, value in decision.items() if key != "signature"}
    return prefix + json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False,
    )


class _ObservedRealVerifier(Ed25519SignatureVerifier):
    """Record only; every result is decided by the unchanged real backend."""

    def __init__(self):
        self.calls = []

    def verify(self, public_key, signing_input, signature):
        result = super().verify(public_key, signing_input, signature)
        self.calls.append((public_key, signing_input, signature, result))
        return result


@pytest.mark.parametrize("case", CASES)
def test_effect_review_real_ed25519_signature(monkeypatch, case):
    verify, kw = _case(monkeypatch)
    private_key = Ed25519PrivateKey.generate()
    public_key = _public_key(private_key)
    kw["decision"]["reviewer_public_key"] = public_key
    resolver = kw["reviewer_key_resolver"]
    resolver.value = replace(resolver.value, public_key=public_key)
    signed_input = _independent_preimage(kw["decision"])
    if case == "delegated_prefix_signature":
        signed_input = _independent_preimage(kw["decision"], "reddog-elevated-consensus-review.v1.")
    elif case == "unrelated_message_signature":
        signed_input = "test-only unrelated message; no effect approval"
    raw_signature = private_key.sign(signed_input.encode("ascii"))
    if case == "signature_bit_tampered":
        raw_signature = bytes([raw_signature[0] ^ 1]) + raw_signature[1:]
    kw["decision"]["signature"] = _wire("ed25519-sig-v1:", raw_signature)
    if case == "signed_payload_tampered":
        kw["decision"]["decision_id"] = "decision:changed-after-signing"
    elif case == "foreign_key_consistently_rebound":
        public_key = _public_key(Ed25519PrivateKey.generate())
        kw["decision"]["reviewer_public_key"] = public_key
        resolver.value = replace(resolver.value, public_key=public_key)
    backend = _ObservedRealVerifier()
    kw["signature_verifier"] = backend
    data = {key: value for key, value in kw.items() if key not in (
        "signature_verifier", "reviewer_key_resolver", "runtime_evidence_resolver",
    )}
    before = deepcopy(data)
    expected = case == "valid_effect_signature"
    assert verify(**kw) is expected
    assert data == before
    assert backend.calls == [(public_key, _independent_preimage(kw["decision"]),
                              kw["decision"]["signature"], expected)]
    assert resolver.calls == [("reviewer:test", "test")]
    assert kw["runtime_evidence_resolver"].calls == [
        ("reviewer:test", "selection:reviewer", "runtime:reviewer"),
    ]
