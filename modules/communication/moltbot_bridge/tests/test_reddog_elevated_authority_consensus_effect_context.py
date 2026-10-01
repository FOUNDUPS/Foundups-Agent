"""Inert effect-context wire contracts; synthetic values confer no authority."""

from copy import deepcopy
from dataclasses import FrozenInstanceError, replace
import importlib
import importlib.util
import json

import pytest


OWNER = "modules.communication.moltbot_bridge.src.reddog_elevated_authority_consensus_effect_context"
PREFIX = b"reddog-effect-approval-context.v1."
DIGEST_FIELDS = (
    "parent_authority_request_digest", "target_signing_request_digest",
    "effect_request_digest", "sovereign_authorization_digest", "consensus_policy_digest",
)


def _wire():
    return {
        "schema_version": "reddog_effect_approval_context.v1",
        "binding_schema_version": "reddog_effect_target_binding.v1",
        **{name: "sha256:" + str(index) * 64 for index, name in enumerate(DIGEST_FIELDS, 1)},
        "required_approvals": 3, "required_roles": ["critic", "verifier"],
        "nonce": "effect-context-fixture", "issued_at": 100, "expires_at": 101,
    }


def _api():
    assert importlib.util.find_spec(OWNER) is not None, "effect_context_api_missing"
    owner = importlib.import_module(OWNER)
    for name in ("EffectApprovalContext", "rehydrate_effect_approval_context",
                 "canonical_effect_approval_context_bytes", "canonical_effect_approval_context_digest"):
        assert callable(getattr(owner, name, None)), "effect_context_api_missing:" + name
    assert callable(getattr(owner.EffectApprovalContext, "to_dict", None))
    return owner


GOLDEN_BYTES = PREFIX + (
    b'{"binding_schema_version":"reddog_effect_target_binding.v1",'
    b'"consensus_policy_digest":"sha256:' + b"5" * 64 + b'",'
    b'"effect_request_digest":"sha256:' + b"3" * 64 + b'",'
    b'"expires_at":101,"issued_at":100,"nonce":"effect-context-fixture",'
    b'"parent_authority_request_digest":"sha256:' + b"1" * 64 + b'",'
    b'"required_approvals":3,"required_roles":["critic","verifier"],'
    b'"schema_version":"reddog_effect_approval_context.v1",'
    b'"sovereign_authorization_digest":"sha256:' + b"4" * 64 + b'",'
    b'"target_signing_request_digest":"sha256:' + b"2" * 64 + b'"}'
)
GOLDEN_DIGEST = "sha256:ead96b833bf78afdb245fa1d108af1bf83e4814388720341846dbb76d5d93869"


def test_effect_context_golden_roundtrip_and_immutable_copies():
    api = _api()
    wire = _wire()
    before = deepcopy(wire)
    context = api.rehydrate_effect_approval_context(wire)
    assert type(context) is api.EffectApprovalContext
    assert context.required_roles == ("critic", "verifier")
    assert type(context.required_roles) is tuple
    assert context.to_dict() == before and wire == before
    assert api.canonical_effect_approval_context_bytes(context) == GOLDEN_BYTES
    assert api.canonical_effect_approval_context_digest(context) == GOLDEN_DIGEST
    reordered = api.rehydrate_effect_approval_context(dict(reversed(list(before.items()))))
    assert api.canonical_effect_approval_context_bytes(reordered) == GOLDEN_BYTES
    exported = context.to_dict()
    exported["required_roles"].append("altered")
    wire["required_roles"].clear()
    assert context.to_dict() == before
    with pytest.raises(FrozenInstanceError):
        context.nonce = "altered"


@pytest.mark.parametrize("times", [(0, 1), (10**18, 10**18 + 10**12)], ids=["past", "future_long"])
def test_effect_context_has_no_clock_or_ttl_admission(times):
    api = _api()
    wire = _wire()
    wire["issued_at"], wire["expires_at"] = times
    context = api.rehydrate_effect_approval_context(wire)
    assert context.to_dict() == wire


def test_effect_context_accepts_exact_field_bounds():
    api = _api()
    wire = _wire()
    wire.update(required_approvals=8, required_roles=[str(i) + "r" * 255 for i in range(8)], nonce="n" * 256)
    assert api.rehydrate_effect_approval_context(wire).to_dict() == wire


@pytest.mark.parametrize("size", [8192, 8193], ids=["at_limit", "over_limit"])
def test_effect_context_whole_wire_byte_bound(size):
    api = _api()
    wire = _wire()
    wire["required_roles"] = [str(i) + "\x01" * 150 for i in range(8)]
    extra = size - len(json.dumps(wire, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode())
    wire["required_roles"][-1] += "\x01" * (extra // 6) + "x" * (extra % 6)
    assert all(len(role) <= 256 for role in wire["required_roles"])
    assert len(json.dumps(wire, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()) == size
    if size == 8192:
        assert api.rehydrate_effect_approval_context(wire).to_dict() == wire
    else:
        with pytest.raises(ValueError):
            api.rehydrate_effect_approval_context(wire)


WIRE_CASES = [
    "non_mapping", "dict_subclass", "missing", "extra", "context_domain", "binding_domain",
    *["digest_" + name for name in DIGEST_FIELDS], "uppercase_digest",
    "approval_bool", "approval_zero", "approval_nine", "approval_float",
    "roles_tuple", "roles_empty", "roles_duplicate", "roles_nine", "role_type",
    "role_non_ascii", "role_too_long", "nonce_empty", "nonce_type", "nonce_non_ascii",
    "nonce_too_long", "issued_bool", "expires_bool", "issued_negative", "equal_times",
    "reversed_times", "expires_float", "json_error",
]


def _invalid_wire(case):
    wire = _wire()
    replacements = {
        "context_domain": ("schema_version", "reddog_elevated_authority_consensus.v1"),
        "binding_domain": ("binding_schema_version", "reddog_effect_target_binding.v2"),
        "uppercase_digest": (DIGEST_FIELDS[0], "sha256:" + "A" * 64),
        "approval_bool": ("required_approvals", True), "approval_zero": ("required_approvals", 0),
        "approval_nine": ("required_approvals", 9), "approval_float": ("required_approvals", 3.0),
        "roles_tuple": ("required_roles", ("critic",)), "roles_empty": ("required_roles", []),
        "roles_duplicate": ("required_roles", ["critic", "critic"]),
        "roles_nine": ("required_roles", [str(i) for i in range(9)]),
        "role_type": ("required_roles", [1]), "role_non_ascii": ("required_roles", ["\u00e9"]),
        "role_too_long": ("required_roles", ["r" * 257]), "nonce_empty": ("nonce", ""),
        "nonce_type": ("nonce", 1), "nonce_non_ascii": ("nonce", "\u00e9"),
        "nonce_too_long": ("nonce", "n" * 257), "issued_bool": ("issued_at", True),
        "expires_bool": ("expires_at", True), "issued_negative": ("issued_at", -1),
        "equal_times": ("expires_at", 100), "reversed_times": ("expires_at", 99),
        "expires_float": ("expires_at", 101.0), "json_error": ("nonce", object()),
    }
    if case == "non_mapping":
        return None
    if case == "dict_subclass":
        return type("WireSubclass", (dict,), {})(wire)
    if case == "missing":
        del wire["nonce"]
    elif case == "extra":
        wire["approved"] = True
    elif case.startswith("digest_"):
        wire[case.removeprefix("digest_")] = "sha256:" + "g" * 64
    else:
        field, value = replacements[case]
        wire[field] = value
    return wire


@pytest.mark.parametrize("case", WIRE_CASES, ids=WIRE_CASES)
def test_effect_context_rejects_invalid_wire(case):
    api = _api()
    wire = _invalid_wire(case)
    before = deepcopy(wire) if case != "json_error" else None
    with pytest.raises(ValueError):
        api.rehydrate_effect_approval_context(wire)
    if case != "json_error":
        assert wire == before


@pytest.mark.parametrize("case", ["mapping", "subclass", "roles_list", "role_type", "approval_bool", "digest", "time"])
def test_effect_context_canonical_apis_reject_invalid_internal_context(case):
    api = _api()
    context = api.rehydrate_effect_approval_context(_wire())
    if case == "mapping":
        invalid = _wire()
    elif case == "subclass":
        invalid = type("ContextSubclass", (api.EffectApprovalContext,), {})(
            **{**context.to_dict(), "required_roles": context.required_roles})
    else:
        mutations = {"roles_list": {"required_roles": ["critic"]},
                     "role_type": {"required_roles": (1,)}, "approval_bool": {"required_approvals": True},
                     "digest": {"effect_request_digest": "sha256:bad"}, "time": {"expires_at": 100}}
        invalid = replace(context, **mutations[case])
    for function in (api.canonical_effect_approval_context_bytes, api.canonical_effect_approval_context_digest):
        with pytest.raises(ValueError):
            function(invalid)
