"""Pure current correlation; synthetic contexts never authorize an effect."""

from copy import deepcopy
from dataclasses import replace
import importlib

import pytest


OWNER = "modules.communication.moltbot_bridge.src.reddog_elevated_authority_consensus_effect_context"


def _api():
    owner = importlib.import_module(OWNER)
    matches = getattr(owner, "effect_approval_context_matches", None)
    assert callable(matches), "effect_approval_context_matches_api_missing"
    return owner, matches


def _inputs(owner, monkeypatch):
    from modules.communication.moltbot_bridge.tests import test_reddog_elevated_authority_consensus_canonicalization as fixture
    args, payload = fixture._binding_inputs(monkeypatch)
    golden = fixture._BINDING_GOLDEN
    context = owner.EffectApprovalContext(
        schema_version="reddog_effect_approval_context.v1",
        binding_schema_version=golden["schema_version"],
        **{key: value for key, value in golden.items() if key != "schema_version"},
        sovereign_authorization_digest="sha256:" + "e" * 64,
        consensus_policy_digest="sha256:" + "f" * 64,
        required_approvals=3, required_roles=("critic", "verifier"),
        nonce="independent-context-nonce", issued_at=999, expires_at=1020,
    )
    return context, args, payload, fixture


def _assert_matches(matches, context, args, expected):
    before = deepcopy((context, args))
    assert matches(context, **args) is expected
    assert (context, args) == before


@pytest.mark.parametrize("case", ["golden", "issue_boundary", "last_current", "references", "parent_backrefs"])
def test_effect_context_current_correlation_is_not_authority(monkeypatch, case):
    owner, matches = _api()
    context, args, _, fixture = _inputs(owner, monkeypatch)
    assert fixture.binding_owner.build_effect_target_binding(**args) == fixture._BINDING_GOLDEN
    if case == "issue_boundary":
        context = replace(context, issued_at=args["now"])
    elif case == "last_current":
        args["now"] = 1019
    elif case == "references":
        context = replace(context, sovereign_authorization_digest="sha256:" + "1" * 64,
                          consensus_policy_digest="sha256:" + "2" * 64, nonce="arbitrary-other-context")
    elif case == "parent_backrefs":
        args["parent"] = replace(args["parent"], consensus_receipt_digest="sha256:" + "5" * 64,
                                  sovereign_authorization_digest="sha256:" + "6" * 64)
    assert context.required_approvals > len(context.required_roles)
    assert context.nonce != args["target"].nonce
    _assert_matches(matches, context, args, True)


@pytest.mark.parametrize("case", ["mapping", "subclass", "roles_list", "roles_duplicate", "approval_bool",
                                 "schema", "binding_schema", "policy", "sovereign", "nonce", "issued_bool", "oversized"])
def test_effect_context_revalidates_manual_context(monkeypatch, case):
    owner, matches = _api()
    context, args, _, _ = _inputs(owner, monkeypatch)
    if case == "mapping":
        context = context.to_dict()
    elif case == "subclass":
        context = type("ContextSubclass", (owner.EffectApprovalContext,), {})(
            **{**context.to_dict(), "required_roles": context.required_roles})
    else:
        patches = {"roles_list": {"required_roles": ["critic", "verifier"]},
                   "roles_duplicate": {"required_roles": ("critic", "critic")},
                   "approval_bool": {"required_approvals": True}, "schema": {"schema_version": "old.v1"},
                   "binding_schema": {"binding_schema_version": "old.v1"},
                   "policy": {"consensus_policy_digest": "sha256:bad"},
                   "sovereign": {"sovereign_authorization_digest": "sha256:bad"},
                   "nonce": {"nonce": ""}, "issued_bool": {"issued_at": True},
                   "oversized": {"required_roles": tuple("\x01" * 255 + str(i) for i in range(8))}}
        context = replace(context, **patches[case])
    _assert_matches(matches, context, args, False)


@pytest.mark.parametrize("case", ["now_bool", "now_float", "now_text", "not_yet_issued", "own_expiry",
                                 "past_expiry", "beyond_target", "equal_invalid", "expires_bool"])
def test_effect_context_requires_exact_current_time_and_target_bound(monkeypatch, case):
    owner, matches = _api()
    context, args, _, _ = _inputs(owner, monkeypatch)
    if case.startswith("now_"):
        args["now"] = {"now_bool": True, "now_float": 1000.0, "now_text": "1000"}[case]
    else:
        patches = {"not_yet_issued": {"issued_at": 1001}, "own_expiry": {"expires_at": 1000},
                   "past_expiry": {"expires_at": 1001}, "beyond_target": {"expires_at": 1021},
                   "equal_invalid": {"expires_at": 999}, "expires_bool": {"expires_at": True}}
        context = replace(context, **patches[case])
        if case == "past_expiry":
            args["now"] = 1002
    _assert_matches(matches, context, args, False)


@pytest.mark.parametrize("field", ["parent_authority_request_digest", "target_signing_request_digest", "effect_request_digest"])
def test_effect_context_rejects_stale_binding_fields(monkeypatch, field):
    owner, matches = _api()
    context, args, _, _ = _inputs(owner, monkeypatch)
    context = replace(context, **{field: "sha256:" + "0" * 64})
    _assert_matches(matches, context, args, False)


@pytest.mark.parametrize("case", ["requester", "generation", "replay", "nonce", "shorter_lifetime", "effect"])
def test_effect_context_rejects_consistently_changed_valid_target(monkeypatch, case):
    owner, matches = _api()
    context, args, payload, fixture = _inputs(owner, monkeypatch)
    patches = {"requester": {"requester_principal_id": "github:other"}, "generation": {"generation": 2},
               "replay": {"replay_store_id": "signer-grant-replay:other"},
               "nonce": {"lease_nonce": "b" * 64}, "shorter_lifetime": {"expires_at": 1019}}
    if case == "effect":
        payload["effect_payload"]["valve_decision_digest"] = "sha256:" + "9" * 64
        payload["effect_request_digest"] = fixture.lease_owner.authoritative_use_effect_digest(
            payload["effect_kind"], payload["effect_payload"])
    else:
        payload.update(patches[case])
    args["target"] = fixture.lease_owner.build_authoritative_use_lease_request(payload, authority_tier="HIGH")
    args["expected_target"] = args["target"].to_dict()
    assert fixture.lease_owner.validate_authoritative_use_lease_request(args["target"], now_epoch=args["now"]) == payload
    changed_binding = fixture.binding_owner.build_effect_target_binding(**args)
    assert changed_binding is not None and changed_binding != fixture._BINDING_GOLDEN
    _assert_matches(matches, context, args, False)


@pytest.mark.parametrize("case", ["valid_parent_change", "parent_mapping", "parent_future", "parent_bound",
                                 "target_mapping", "target_proof", "expected_mapping", "expected_stale"])
def test_effect_context_rechecks_actual_binding_inputs(monkeypatch, case):
    owner, matches = _api()
    context, args, _, fixture = _inputs(owner, monkeypatch)
    if case == "valid_parent_change":
        args["parent"] = replace(args["parent"], identity_nonce="identity:other")
        changed_binding = fixture.binding_owner.build_effect_target_binding(**args)
        assert changed_binding is not None and changed_binding != fixture._BINDING_GOLDEN
    elif case == "parent_mapping":
        args["parent"] = args["parent"].to_dict()
    elif case in {"parent_future", "parent_bound"}:
        args["parent"] = replace(args["parent"], **({"issued_at": 1001} if case == "parent_future"
                                                  else {"identity_expires_at": 1019}))
    elif case == "target_mapping":
        args["target"] = args["target"].to_dict()
    elif case == "target_proof":
        args["target"] = replace(args["target"], elevated_consensus_proof={})
        args["expected_target"] = args["target"].to_dict()
    elif case == "expected_mapping":
        args["expected_target"] = type("ExpectedSubclass", (dict,), {})(args["expected_target"])
    else:
        args["expected_target"]["requester_principal_id"] = "github:other"
    _assert_matches(matches, context, args, False)
