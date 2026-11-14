"""Independent strict wire oracles; signatures use only disposable test keys."""

from copy import deepcopy
import pytest

from modules.communication.moltbot_bridge.tests.reddog_reviewer_authority_test_support import (
    PREFIX, canonical, contract, digest, fixture,
)


@pytest.mark.parametrize("case", ["golden", "defensive_copy"])
def test_designation_independent_canonical_contract(case):
    api = contract()
    authority, designation, _, _ = fixture()
    assert api.reviewer_designation_authority_digest(authority) == digest(authority)
    expected = PREFIX + canonical({k: v for k, v in designation.items() if k != "signature"})
    assert api.reviewer_designation_signing_input(designation) == expected
    assert len(expected.encode("ascii")) <= 65536
    checked = api.validate_reviewer_designation(designation)
    root = api.validate_reviewer_designation_authority(authority)
    assert checked == designation and root == authority
    assert root is not authority and checked is not designation
    if case == "defensive_copy":
        checked["reviewers"][0]["authorized_roles"].append("verifier")
        root["issuer_principal_id"] = "changed"
        assert designation["reviewers"][0]["authorized_roles"] == ["critic"]
        assert authority["issuer_principal_id"] == "issuer:test"


CASES = ["authority_extra", "authority_missing", "authority_bool_time", "authority_float_time",
    "authority_empty_interval", "authority_negative_time", "authority_text_long", "authority_nonascii",
    "authority_privilege", "authority_domain", "authority_key", "authority_digest", "inner_extra",
    "inner_digest", "inner_signature", "inner_empty", "inner_nine", "inner_duplicate", "entry_extra",
    "entry_bool_time", "entry_empty_interval", "roles_empty", "roles_nine", "roles_duplicate",
    "roles_long", "roles_nonascii", "roles_tuple", "signing_input_oversize"]


def _mutate(authority, value, case):
    entry = value["reviewers"][0]
    changes = {
        "authority_extra": (authority, "trusted", True), "authority_bool_time": (authority, "issued_at", True),
        "authority_float_time": (authority, "expires_at", 1100.0),
        "authority_empty_interval": (authority, "issued_at", 1100),
        "authority_negative_time": (authority, "issued_at", -1),
        "authority_text_long": (authority, "issuer_principal_id", "x" * 1025),
        "authority_nonascii": (authority, "foundup_id", "\u00e9"),
        "authority_privilege": (authority, "privilege", "sign_anything"),
        "authority_domain": (authority, "decision_schema_version", "reddog_elevated_authority_reviewer_decision.v1"),
        "authority_key": (authority, "issuer_public_key", "invalid"),
        "authority_digest": (authority, "policy_digest", "SHA256:" + "a" * 64),
        "inner_extra": (value, "verified", True), "inner_digest": (value, "owner_authority_digest", "bad"),
        "inner_signature": (value, "signature", "bad"), "inner_empty": (value, "reviewers", []),
        "entry_extra": (entry, "verified", True), "entry_bool_time": (entry, "issued_at", True),
        "entry_empty_interval": (entry, "expires_at", entry["issued_at"]),
        "roles_empty": (entry, "authorized_roles", []),
        "roles_nine": (entry, "authorized_roles", ["role" + str(i) for i in range(9)]),
        "roles_duplicate": (entry, "authorized_roles", ["critic", "critic"]),
        "roles_long": (entry, "authorized_roles", ["r" * 65]),
        "roles_nonascii": (entry, "authorized_roles", ["\u00e9"]),
        "roles_tuple": (entry, "authorized_roles", ("critic",)),
    }
    if case == "authority_missing":
        authority.pop("privilege")
    elif case == "signing_input_oversize":
        value["reviewers"] = [dict(deepcopy(entry), principal_id=str(i) + "\x01" * 1023,
            principal_provider="p" + "\x01" * 1023, key_epoch="e" + "\x01" * 1023) for i in range(8)]
        assert all(len(item[key]) == 1024 and item[key].isascii() for item in value["reviewers"]
                   for key in ("principal_id", "principal_provider", "key_epoch"))
        assert len((PREFIX + canonical({k: v for k, v in value.items() if k != "signature"})).encode("ascii")) > 65536
    elif case in {"inner_nine", "inner_duplicate"}:
        value["reviewers"] = [dict(deepcopy(entry), principal_id="reviewer:" + str(i)) for i in range(9)] if case == "inner_nine" else [entry, deepcopy(entry)]
    else:
        target, field, replacement = changes[case]
        target[field] = replacement


@pytest.mark.parametrize("case", CASES)
def test_designation_strict_rejection(case):
    api = contract()
    authority, designation, _, _ = fixture()
    _mutate(authority, designation, case)
    before = deepcopy((authority, designation))
    if case.startswith("authority_"):
        with pytest.raises(ValueError):
            api.validate_reviewer_designation_authority(authority)
        with pytest.raises(ValueError):
            api.reviewer_designation_authority_digest(authority)
    else:
        with pytest.raises(ValueError):
            api.validate_reviewer_designation(designation)
        with pytest.raises(ValueError):
            api.reviewer_designation_signing_input(designation)
    assert (authority, designation) == before
