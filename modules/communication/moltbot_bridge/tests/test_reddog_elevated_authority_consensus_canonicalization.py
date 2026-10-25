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

# Pure effect-binding fixtures carry no authenticated authority.
import hashlib
import json
from copy import deepcopy
from modules.communication.moltbot_bridge.src import reddog_elevated_authority_consensus_evidence as binding_owner
from modules.communication.moltbot_bridge.src import reddog_signer_delegated_authority_runtime as runtime_owner
from modules.communication.moltbot_bridge.src import reddog_authoritative_use_lease_contract as lease_owner
from modules.communication.moltbot_bridge.tests import test_reddog_external_signer_authoritative_use_lease as lease_fixture

def _binding_api():
    build = getattr(binding_owner, "build_effect_target_binding", None)
    matches = getattr(binding_owner, "effect_target_binding_matches", None)
    assert callable(build) and callable(matches), "pure effect binding API not implemented"
    return build, matches

def _binding_inputs(monkeypatch):
    monkeypatch.setattr(lease_fixture, "_public_key", lambda: "inert-effect-key")
    parent = runtime_owner.DelegatedAuthorityRuntimeRequest(
        work_order_id="work-order-1", work_order_digest="sha256:" + "c" * 64, base_ref="main",
        principal_id="github:parent", principal_provider="github", principal_public_key="inert-parent-key",
        reddog_id="reddog:test", reddog_public_key="inert-reddog-key", repo_full_name="test/repo",
        foundup_id="test-foundup", allowed_paths=("src/",), denied_paths=(".git/",),
        requested_operation="worktree_create", permission_snapshot_digest="sha256:" + "1" * 64,
        queue_consumer_receipt_digest="sha256:" + "2" * 64, queue_consumer_receipt={},
        wsp15_allocation_receipt={}, wsp15_allocation_receipt_id="allocation:test",
        wsp15_allocation_digest="sha256:" + "3" * 64, wsp15_priority="P1", wsp15_mps_total=13,
        wsp15_reasoning_tier="HIGH", progressive_policy_stage_receipt_id="stage:test",
        progressive_policy_stage_digest="sha256:" + "4" * 64, progressive_policy_stage_receipt={},
        identity_nonce="identity:test", work_authority_nonce="authority:test", issued_at=1000,
        identity_expires_at=1100, work_authority_expires_at=1100, valve_state_required="closed", key_epoch="epoch-1")
    payload = lease_fixture._payload(generation=1, issued_at=1000, expires_at=1020,
                                    socket_path_digest="sha256:" + "a" * 64)
    target = lease_owner.build_authoritative_use_lease_request(payload, authority_tier="HIGH")
    return dict(parent=parent, target=target, expected_target=target.to_dict(), now=1000), payload

_BINDING_GOLDEN = {
    "schema_version": "reddog_effect_target_binding.v1",
    "parent_authority_request_digest": "sha256:b9241ea0707f24d3fee6fc3aba1e400bf0513b984bbbaf51ed8a4827769866a2",
    "target_signing_request_digest": "sha256:0253315aeba8059120097b8fbf485b79459f9c60f4912edfc74fab2b86e3b0f4",
    "effect_request_digest": "sha256:3be61a0dd162879ffafa2446d2381eb30539ec39e3b446e82fa6d721dfc2a67d",
}

def test_effect_binding_golden_projection_and_no_mutation(monkeypatch):
    build, matches = _binding_api()
    args, payload = _binding_inputs(monkeypatch)
    before = deepcopy((args, payload))
    binding = build(**args)
    assert type(binding) is dict and binding == _BINDING_GOLDEN
    assert args["parent"].principal_id != args["target"].requester_principal_id
    assert matches(binding, **args) is True
    assert build(**args) == binding and build(**args) is not binding
    projected = dict(args, parent=replace(args["parent"], consensus_receipt_digest="sha256:" + "5" * 64,
                                         sovereign_authorization_digest="sha256:" + "6" * 64),
                     expected_target=dict(reversed(list(args["expected_target"].items()))))
    assert build(**projected) == binding
    assert before == (args, payload)

_PARENT_REJECTIONS = [
    ("mapping", None), ("operation", {"requested_operation": "run_shell"}),
    ("work_order_id", {"work_order_id": "other"}),
    ("work_order_digest", {"work_order_digest": "sha256:" + "0" * 64}),
    ("boolean_time", {"issued_at": True}), ("future", {"issued_at": 1001}),
    ("identity_bound", {"identity_expires_at": 1019}),
    ("authority_bound", {"work_authority_expires_at": 1019}),
    ("expired", {"identity_expires_at": 1000}),
]

@pytest.mark.parametrize("case,patch", _PARENT_REJECTIONS, ids=[row[0] for row in _PARENT_REJECTIONS])
def test_effect_binding_rejects_parent_mismatch(monkeypatch, case, patch):
    build, matches = _binding_api()
    args, _ = _binding_inputs(monkeypatch)
    args["parent"] = args["parent"].to_dict() if patch is None else replace(args["parent"], **patch)
    assert build(**args) is None
    assert matches(None, **args) is False and matches(_BINDING_GOLDEN, **args) is False


@pytest.mark.parametrize("case", ["proof", "ultra", "target_mapping", "expected_subclass", "proof_key", "boolean_now", "live_enqueue"])
def test_effect_binding_rejects_target_shape(monkeypatch, case):
    build, matches = _binding_api()
    args, payload = _binding_inputs(monkeypatch)
    if case in {"proof", "ultra"}:
        patch = {"elevated_consensus_proof": {}} if case == "proof" else {"authority_tier": "ULTRA"}
        args["target"] = replace(args["target"], **patch)
        args["expected_target"] = args["target"].to_dict()
    if case == "target_mapping":
        args["target"] = args["target"].to_dict()
    if case == "expected_subclass":
        args["expected_target"] = type("NonPlainExpected", (dict,), {})(args["expected_target"])
    if case == "proof_key":
        args["expected_target"]["elevated_consensus_proof"] = None
    if case == "boolean_now":
        args["now"] = True
    if case == "live_enqueue":
        effect = {"work_order_id": "work-order-1", "evidence_digest": "sha256:" + "a" * 64}
        payload.update(effect_kind="live_enqueue", effect_payload=effect,
                       effect_request_digest=lease_owner.authoritative_use_effect_digest("live_enqueue", effect))
        args["target"] = lease_owner.build_authoritative_use_lease_request(payload, authority_tier="HIGH")
        args["expected_target"] = args["target"].to_dict()
        assert lease_owner.validate_authoritative_use_lease_request(args["target"], now_epoch=args["now"]) == payload
    assert build(**args) is None and matches(None, **args) is False


_EXPECTED_SUBSTITUTIONS = [
    ("requester_principal_id", "github:other"), ("signer_public_key", "another-inert-key"),
    ("generation", 2), ("replay_store_id", "signer-grant-replay:other"),
    ("lease_nonce", "b" * 64), ("expires_at", 1021), ("generation", True), ("generation", 1.0),
]


@pytest.mark.parametrize("field,value", _EXPECTED_SUBSTITUTIONS,
                         ids=["requester", "key", "generation", "replay", "nonce", "lifetime", "bool_int", "float_int"])
def test_effect_binding_rejects_expected_target_substitution(monkeypatch, field, value):
    build, matches = _binding_api()
    args, payload = _binding_inputs(monkeypatch)
    changed = dict(payload, **{field: value})
    if type(value) in {bool, float}:
        assert changed == payload  # Python equality hides the canonical numeric type change.
        encoded = json.dumps(changed, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)
        target = replace(args["target"], signing_input="reddog-authoritative-use-lease.v1." + encoded,
                         payload_digest="sha256:" + hashlib.sha256(encoded.encode()).hexdigest())
    else:
        target = lease_owner.build_authoritative_use_lease_request(changed, authority_tier="HIGH")
    args["expected_target"] = target.to_dict()
    assert build(**args) is None and matches(_BINDING_GOLDEN, **args) is False


@pytest.mark.parametrize("field", [None, "schema_version", "parent_authority_request_digest",
                                   "target_signing_request_digest", "effect_request_digest", "extra", "missing"])
def test_effect_binding_rejects_supplied_binding_substitution(monkeypatch, field):
    build, matches = _binding_api()
    args, _ = _binding_inputs(monkeypatch)
    forged = deepcopy(_BINDING_GOLDEN)
    if field == "missing":
        forged.pop("effect_request_digest")
    elif field is not None:
        forged[field] = "sha256:" + "0" * 64
    else:
        forged = None
    assert build(**args) == _BINDING_GOLDEN and matches(forged, **args) is False
