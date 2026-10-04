"""Canonical request data is not a signing permit or runtime authority."""

import hashlib
import inspect
import json
from collections import UserDict
from copy import deepcopy
from dataclasses import replace
from types import SimpleNamespace

import pytest

from modules.communication.moltbot_bridge.tests import (
    test_reddog_external_signer_authoritative_use_lease as fixtures,
    test_reddog_elevated_authority_consensus_canonicalization as bindings,
)
owner = fixtures.issuer_module

def _json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)


def _digest(value):
    return "sha256:" + hashlib.sha256(_json(value).encode("ascii")).hexdigest()

def _snapshot(case):
    files = {p.relative_to(case.root).as_posix(): p.read_bytes() if p.is_file() else None
             for p in case.root.rglob("*")}
    return files, deepcopy(case.store._config), fixtures._replay_binding(case.store)


def _case(tmp_path, monkeypatch):
    monkeypatch.setattr(fixtures, "_public_key", lambda: "inert-effect-key")
    store = fixtures._store(tmp_path)
    authority = fixtures._authority(tmp_path, monkeypatch)
    blocked = []

    def forbidden(*args, **kwargs):
        blocked.append("unexpected_effect")
        raise AssertionError("preparation attempted an effect")

    for name in ("consume_grant", "consume_authoritative_use_lease", "consume_scoped_nonce"):
        monkeypatch.setattr(store, name, forbidden)
    for name in ("reserve", "commit", "rollback"):
        monkeypatch.setattr(store._store, name, forbidden)
    monkeypatch.setattr(type(authority), "resolve", forbidden)
    monkeypatch.setattr(owner, "time", SimpleNamespace(time=forbidden))
    issuer = owner.ExternalSignerAuthoritativeUseLeaseIssuer(
        SimpleNamespace(sign_with_secret_grant=forbidden), SimpleNamespace(lease=forbidden),
        store, authority,
    )
    payload = fixtures._payload(store, generation=1, issued_at=1000, expires_at=1020,
                                socket_path_digest="sha256:" + "a" * 64)
    case = SimpleNamespace(issuer=issuer, store=store, payload=payload, root=tmp_path, blocked=blocked)
    case.before = _snapshot(case)
    return case


def _api(case):
    method = getattr(case.issuer, "prepare_request", None)
    assert callable(method), "canonical prepare_request API missing"
    return method


def _quiet(case):
    assert case.blocked == []
    assert _snapshot(case) == case.before

def _expected(payload, tier="HIGH"):
    return dict(signing_input="reddog-authoritative-use-lease.v1." + _json(payload),
                payload_digest=_digest(payload), signer_role="signer:authoritative-use-lease",
                signer_public_key=payload["signer_public_key"],
                requester_principal_id=payload["requester_principal_id"],
                nonce="authoritative-use-lease:" + payload["lease_nonce"],
                key_epoch=payload["key_epoch"], requested_operation="issue_authoritative_use_lease",
                authority_tier=tier, consensus_receipt_digest=None)


@pytest.mark.parametrize("tier", ["HIGH", "ULTRA"])
@pytest.mark.parametrize("mode", ["missing", "equal", "mapping"])
def test_prepare_canonical_without_effects(tmp_path, monkeypatch, tier, mode):
    case = _case(tmp_path, monkeypatch)
    payload = deepcopy(case.payload)
    if mode == "missing":
        for key in fixtures._replay_binding(case.store):
            payload.pop(key)
    if mode == "mapping":
        payload = UserDict(payload)
    before = deepcopy(payload)
    method = _api(case)
    assert set(inspect.signature(method).parameters) == {"payload", "authority_tier"}
    assert all(p.kind is inspect.Parameter.KEYWORD_ONLY for p in inspect.signature(method).parameters.values())
    first = method(payload=payload, authority_tier=tier)
    second = method(payload=payload, authority_tier=tier)
    assert type(first) is fixtures.SigningRequest and second == first
    assert first.to_dict() == _expected(case.payload, tier)
    assert first.elevated_consensus_proof is None and "elevated_consensus_proof" not in first.to_dict()
    assert payload == before
    _quiet(case)


@pytest.mark.parametrize("field", ["replay_store_binding_digest", "replay_store_id",
                                  "replay_store_durability_receipt_id", "replay_store_instance_digest"])
def test_prepare_rejects_each_replay_mismatch(tmp_path, monkeypatch, field):
    case = _case(tmp_path, monkeypatch)
    method = _api(case)
    assert method(payload=case.payload, authority_tier="HIGH") is not None
    changed = dict(case.payload, **{field: "different"})
    before = deepcopy(changed)
    assert method(payload=changed, authority_tier="HIGH") is None
    assert changed == before
    _quiet(case)


@pytest.mark.parametrize("fault", ["none", "missing", "extra", "boolean_generation", "effect_digest",
                                  "LOW", "unknown", "null_tier", "boolean_tier", "list_tier"])
def test_prepare_rejects_malformed_request(tmp_path, monkeypatch, fault):
    case = _case(tmp_path, monkeypatch)
    method = _api(case)
    assert method(payload=case.payload, authority_tier="HIGH") is not None
    payload, tier = deepcopy(case.payload), "HIGH"
    if fault == "none": payload = None
    elif fault == "missing": payload.pop("lease_nonce")
    elif fault == "extra": payload["unexpected"] = "data"
    elif fault == "boolean_generation": payload["generation"] = True
    elif fault == "effect_digest": payload["effect_request_digest"] = "sha256:" + "0" * 64
    else: tier = {"LOW": "LOW", "unknown": "OTHER", "null_tier": None,
                  "boolean_tier": True, "list_tier": []}[fault]
    before = deepcopy(payload)
    assert method(payload=payload, authority_tier=tier) is None
    assert payload == before
    _quiet(case)


@pytest.mark.parametrize("field,subclass", [("replay_store", False), ("replay_store", True),
                                          ("current_generation_authority", False),
                                          ("current_generation_authority", True)],
                         ids=["store_object", "store_subclass", "authority_object", "authority_subclass"])
def test_prepare_and_issue_reject_wrong_owner_types(tmp_path, monkeypatch, field, subclass):
    case = _case(tmp_path, monkeypatch)
    value = getattr(case.issuer, field)
    bad = object.__new__(type("Derived", (type(value),), {})) if subclass else object()
    case.issuer = replace(case.issuer, **{field: bad})
    assert case.issuer.issue(payload=case.payload, authority_tier="HIGH") is None
    assert _api(case)(payload=case.payload, authority_tier="HIGH") is None
    _quiet(case)


@pytest.mark.parametrize("exception", [RuntimeError, KeyboardInterrupt], ids=["ordinary", "interrupt"])
def test_prepare_exception_boundary_and_no_clock(tmp_path, monkeypatch, exception):
    case = _case(tmp_path, monkeypatch)
    method, error = _api(case), exception("inert")

    def fail(*args):
        raise error

    monkeypatch.setattr(owner, "_bind_replay_store", fail)
    if exception is RuntimeError:
        assert method(payload=case.payload, authority_tier="HIGH") is None
    else:
        with pytest.raises(KeyboardInterrupt) as caught:
            method(payload=case.payload, authority_tier="HIGH")
        assert caught.value is error
    _quiet(case)


@pytest.mark.parametrize("variant", ["valid", "stale_replay", "stale_effect", "ULTRA", "live_enqueue"])
def test_prepared_request_connects_to_effect_binding(tmp_path, monkeypatch, variant):
    case = _case(tmp_path, monkeypatch)
    method = _api(case)
    args, _ = bindings._binding_inputs(monkeypatch)
    payload = deepcopy(case.payload)
    if variant == "live_enqueue":
        payload.update(effect_kind="live_enqueue", effect_payload={
            "work_order_id": "work-order-1", "evidence_digest": "sha256:" + "a" * 64})
        payload["effect_request_digest"] = _digest({k: payload[k] for k in ("effect_kind", "effect_payload")})
    tier = "ULTRA" if variant == "ULTRA" else "HIGH"
    target = method(payload=payload, authority_tier=tier)
    assert type(target) is fixtures.SigningRequest  # Clock-free, including old fixture timestamps.
    expected = _expected(payload, tier)
    if variant in ("stale_replay", "stale_effect"):
        old = deepcopy(payload)
        if variant == "stale_replay": old["replay_store_id"] = "signer-grant-replay:old"
        else:
            old["effect_payload"]["queue_item_id"] = "old-queue"
            old["effect_request_digest"] = _digest({k: old[k] for k in ("effect_kind", "effect_payload")})
        expected = _expected(old, tier)
    actual = bindings.binding_owner.build_effect_target_binding(**dict(args, target=target, expected_target=expected))
    if variant == "valid":
        parent = args["parent"].to_dict()
        for key in ("consensus_receipt_digest", "sovereign_authorization_digest"): parent.pop(key, None)
        golden = dict(schema_version="reddog_effect_target_binding.v1", parent_authority_request_digest=_digest(parent),
                      target_signing_request_digest=_digest(expected), effect_request_digest=_digest({
                          "effect_kind": payload["effect_kind"], "effect_payload": payload["effect_payload"]}))
        assert golden["parent_authority_request_digest"] == bindings._BINDING_GOLDEN["parent_authority_request_digest"]
        assert golden["effect_request_digest"] == bindings._BINDING_GOLDEN["effect_request_digest"]
        assert actual == golden and _digest(actual) == _digest(golden)
    else:
        assert actual is None
    _quiet(case)
