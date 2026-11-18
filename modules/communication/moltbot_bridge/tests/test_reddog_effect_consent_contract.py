"""Independent fixed wire oracles; no signature production API is invoked."""

from copy import deepcopy
import pytest

from modules.communication.moltbot_bridge.tests.reddog_effect_consent_test_support import (
    AUTHORITY, ASSERTION, PREFIX, PRIVILEGE, api, canonical, digest, materials,
)


def test_effect_consent_exact_domains_bytes_and_defensive_copy(monkeypatch):
    owner, state = api(), materials(monkeypatch)
    assert (owner.AUTHORITY_SCHEMA, owner.ASSERTION_SCHEMA, owner.PRIVILEGE, owner.SIGNING_PREFIX) == (
        AUTHORITY, ASSERTION, PRIVILEGE, PREFIX)
    authority, signed = state.authority, state.assertion
    body = {k: v for k, v in signed.items() if k != "signature"}
    assert len(authority) == 21 and len(signed) == 26 and len(body) == 25
    assert owner.effect_consent_authority_digest(authority) == digest(authority)
    assert owner.canonical_effect_consent_signing_input(body) == PREFIX + canonical(body) == state.message
    assert "authorization_digest" not in body and "signature" not in body
    checked, registered = owner.validate_effect_consent_assertion(signed), owner.validate_effect_consent_authority(authority)
    assert checked == signed and registered == authority
    assert checked is not signed and registered is not authority
    checked["parent_authorization"]["principal_id"] = "changed"
    registered["issuer_principal_id"] = "changed"
    assert signed["parent_authorization"]["principal_id"] != "changed"
    assert authority["issuer_principal_id"] != "changed"
    with pytest.raises(ValueError):
        owner.canonical_effect_consent_signing_input(signed)


INVALID = ["authority_extra", "authority_missing", "authority_domain", "authority_privilege", "authority_tier",
    "authority_effect", "authority_key", "authority_bool", "authority_float", "authority_negative", "authority_huge",
    "authority_interval", "assertion_extra", "assertion_missing", "assertion_domain", "assertion_signature",
    "assertion_digest", "assertion_upper_digest", "assertion_subclass", "parent_subclass", "parent_extra",
    "parent_bool", "parent_key", "parent_long", "parent_nonascii", "body_nonstring_key"]


def invalid_value(state, case):
    authority, signed = state.authority, state.assertion
    parent = signed["parent_authorization"]
    changes = {
        "authority_extra": (authority, "trusted", True), "authority_domain": (authority, "schema_version", ASSERTION),
        "authority_privilege": (authority, "privilege", "designate_effect_reviewers"),
        "authority_tier": (authority, "authority_tier", "ULTRA"), "authority_effect": (authority, "effect_kind", "live_enqueue"),
        "authority_key": (authority, "issuer_public_key", "bad"), "authority_bool": (authority, "issued_at", True),
        "authority_float": (authority, "expires_at", 1100.0), "authority_negative": (authority, "issued_at", -1),
        "authority_huge": (authority, "expires_at", 2 ** 63), "authority_interval": (authority, "expires_at", 900),
        "assertion_extra": (signed, "verified", True), "assertion_domain": (signed, "schema_version", AUTHORITY),
        "assertion_signature": (signed, "signature", "bad"), "assertion_digest": (signed, "effect_request_digest", 17),
        "assertion_upper_digest": (signed, "effect_request_digest", "sha256:" + "A" * 64),
        "parent_extra": (parent, "trusted", True), "parent_bool": (parent, "expires_at", True),
        "parent_key": (parent, "principal_public_key", "invalid"), "parent_long": (parent, "principal_id", "x" * 257),
        "parent_nonascii": (parent, "principal_provider", "\u00e9"), "body_nonstring_key": (signed, 1, "x"),
    }
    if case.endswith("missing"):
        (authority if case.startswith("authority") else signed).pop("privilege")
    elif case == "assertion_subclass":
        state.assertion = type("MappingSubclass", (dict,), {})(signed)
    elif case == "parent_subclass":
        signed["parent_authorization"] = type("MappingSubclass", (dict,), {})(parent)
    else:
        mapping, key, value = changes[case]
        mapping[key] = value


@pytest.mark.parametrize("case", INVALID)
def test_effect_consent_rejects_malformed_wire(monkeypatch, case):
    owner, state = api(), materials(monkeypatch)
    assert owner.validate_effect_consent_authority(state.authority) == state.authority
    assert owner.validate_effect_consent_assertion(state.assertion) == state.assertion
    invalid_value(state, case)
    before = deepcopy((state.authority, state.assertion))
    if case.startswith("authority"):
        with pytest.raises(ValueError):
            owner.validate_effect_consent_authority(state.authority)
        with pytest.raises(ValueError):
            owner.effect_consent_authority_digest(state.authority)
    else:
        with pytest.raises(ValueError):
            owner.validate_effect_consent_assertion(state.assertion)
    assert (state.authority, state.assertion) == before


def padded(value, length, prefix):
    value = deepcopy(value)
    fields = ("issuer_principal_id", "requester_principal_id", "beneficiary_principal_id",
              "reddog_id", "issuer_key_epoch", "target_signer_profile_id")
    for field in fields:
        gap = length - len((prefix + canonical(value)).encode("ascii"))
        count = min(max(gap // 6, 0), 256 - len(value[field]))
        value[field] += "\x01" * count
        gap = length - len((prefix + canonical(value)).encode("ascii"))
        value[field] += "x" * min(max(gap, 0), 256 - len(value[field]))
    assert len((prefix + canonical(value)).encode("ascii")) == length
    assert all(1 <= len(value[field]) <= 256 for field in fields)
    return value


@pytest.mark.parametrize("case", ["wire_exact", "wire_over", "input_exact", "input_over"])
def test_effect_consent_aggregate_boundary(monkeypatch, case):
    owner, state = api(), materials(monkeypatch)
    signed = state.assertion
    input_case = case.startswith("input")
    value = {k: v for k, v in signed.items() if k != "signature"} if input_case else signed
    value = padded(value, 8193 if case.endswith("over") else 8192, PREFIX if input_case else "")
    function = owner.canonical_effect_consent_signing_input if input_case else owner.validate_effect_consent_assertion
    if case.endswith("over"):
        with pytest.raises(ValueError):
            function(value)
    else:
        result = function(value)
        assert result == (PREFIX + canonical(value) if input_case else value)


@pytest.mark.parametrize("case", ["exact", "blank", "over"])
def test_effect_consent_text_boundary(monkeypatch, case):
    owner, state = api(), materials(monkeypatch)
    state.authority["issuer_principal_id"] = {"exact": "x" * 256, "blank": " " * 256, "over": "x" * 257}[case]
    if case == "exact":
        assert owner.validate_effect_consent_authority(state.authority) == state.authority
    else:
        with pytest.raises(ValueError):
            owner.validate_effect_consent_authority(state.authority)
