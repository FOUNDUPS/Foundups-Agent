"""Detached parent consent is a distinct capability, never an effective grant."""

import importlib.util
from copy import deepcopy
import pytest

from modules.communication.moltbot_bridge.tests.reddog_parent_consent_test_support import setup, contract, resign


def test_parent_consent_contract_has_distinct_owner():
    name = "modules.communication.moltbot_bridge.src.reddog_parent_consent_contract"
    assert importlib.util.find_spec(name) is not None, "parent_consent_contract_api_missing"


@pytest.mark.parametrize("field,value", [
    ("privilege", "authorize_exact_high_worktree_effect"), ("privilege", "designate_effect_reviewers"),
    ("schema_version", "reddog_effect_consent.v1"), ("authority_tier", "LOW"),
    ("requested_operation", "write_repo"), ("issuer_principal_id", " "),
    ("issuer_principal_provider", "x" * 257), ("issuer_key_epoch", "\u00e9"),
    ("issuer_public_key", "invalid"), ("beneficiary_public_key", "invalid"), ("reddog_public_key", "invalid"),
    ("issued_at", True), ("expires_at", 1.5), ("generation", True),
    ("generation_revision", 1), ("generation_revision", "revision-1"),
    ("generation_revision", "sha256:" + "1" * 64), ("manifest_id", "manifest"),
    ("owner_authority_digest", "bad"), ("authority_request_digest", "bad"),
    ("policy_digest", "bad"), ("expires_at", 2**63), ("issued_at", -1),
])
def test_parent_consent_exact_wire_shape(monkeypatch, tmp_path, field, value):
    _, state = setup(monkeypatch, tmp_path)
    assertion = deepcopy(state.assertion)
    assertion[field] = value
    with pytest.raises(ValueError):
        contract.validate_parent_consent_assertion(assertion)


@pytest.mark.parametrize("mutation", ["missing", "extra", "foreign_key", "wrong_domain", "tamper"])
def test_parent_consent_signature_and_shape_cannot_be_substituted(monkeypatch, tmp_path, mutation):
    from modules.communication.moltbot_bridge.tests.reddog_reviewer_authority_test_support import sign, Ed25519PrivateKey
    resolve, state = setup(monkeypatch, tmp_path)
    if mutation == "missing": state.assertion.pop("owner_authority_digest")
    elif mutation == "extra": state.assertion["authority_granted"] = True
    elif mutation == "foreign_key": sign(state.assertion, Ed25519PrivateKey.generate(), contract.SIGNING_PREFIX)
    elif mutation == "wrong_domain": sign(state.assertion, state.issuer, "reddog-effect-consent.v1.")
    elif mutation == "tamper": state.assertion["issued_at"] = 998
    assert resolve(**state.call) is None


def test_parent_consent_assertion_size_is_bounded(monkeypatch, tmp_path):
    _, state = setup(monkeypatch, tmp_path)
    monkeypatch.setattr(contract, "MAX_CONSENSUS_RECEIPT_BYTES", 1)
    with pytest.raises(ValueError):
        contract.validate_parent_consent_assertion(state.assertion)
