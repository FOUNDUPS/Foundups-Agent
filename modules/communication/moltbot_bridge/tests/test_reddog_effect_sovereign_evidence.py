"""Untrusted effect-sovereign records: structural matches grant no authority."""

from copy import deepcopy
from dataclasses import MISSING, FrozenInstanceError, asdict, fields, replace
import importlib
import json

import pytest

from modules.communication.moltbot_bridge.tests import test_reddog_elevated_authority_consensus_effect_reviewer as reviews
from modules.communication.moltbot_bridge.tests import test_reddog_elevated_authority_consensus_canonicalization as fixtures

TEXT = ("principal_id", "principal_provider", "principal_public_key", "reddog_id", "reddog_public_key",
        "repo_full_name", "foundup_id", "work_order_id", "key_epoch")
DIGESTS = ("authorization_digest", "parent_authority_request_digest", "target_signing_request_digest",
           "effect_request_digest", "consensus_policy_digest")
FIELDS = ("authorization_digest", "parent_authorization", *DIGESTS[1:], "issued_at", "expires_at")


def _api():
    owner = importlib.import_module("modules.communication.moltbot_bridge.src.reddog_elevated_authority_consensus_evidence")
    policy = importlib.import_module("modules.communication.moltbot_bridge.src.reddog_elevated_authority_consensus_policy")
    record = getattr(policy, "EffectSovereignAuthorizationEvidence", None)
    match = getattr(owner, "effect_sovereign_authorization_matches", None)
    assert isinstance(record, type), "EffectSovereignAuthorizationEvidence_api_missing"
    assert callable(match), "effect_sovereign_authorization_matches_api_missing"
    return owner, policy, record, match


def _refresh(evidence, kw):
    parent = kw["parent"].to_dict()
    for name in ("consensus_receipt_digest", "sovereign_authorization_digest"):
        parent.pop(name, None)
    payload = json.loads(kw["target"].signing_input.split(".", 2)[2])
    binding = dict(parent_authority_request_digest=reviews._digest(parent),
                   target_signing_request_digest=reviews._digest(kw["target"].to_dict()),
                   effect_request_digest=reviews._digest({"effect_kind": payload["effect_kind"],
                                                         "effect_payload": payload["effect_payload"]}))
    kw["expected_target"] = kw["target"].to_dict()
    kw["context"] = replace(kw["context"], **binding, consensus_policy_digest=kw["policy"].policy_digest)
    nested = replace(evidence.parent_authorization, **{name: getattr(kw["parent"], name) for name in TEXT},
                     authorization_digest=kw["parent"].sovereign_authorization_digest,
                     authority_request_digest=binding["parent_authority_request_digest"])
    return replace(evidence, **binding, parent_authorization=nested,
                   consensus_policy_digest=kw["policy"].policy_digest)


def _case(monkeypatch):
    owner, policies, record, match = _api()
    _, source = reviews._case(monkeypatch)
    kw = {name: source[name] for name in ("context", "target", "expected_target", "policy", "now")}
    kw["parent"] = replace(source["authority_request"], sovereign_authorization_digest="sha256:" + "6" * 64)
    nested = policies.SovereignAuthorizationEvidence("sha256:" + "6" * 64,
        fixtures._BINDING_GOLDEN["parent_authority_request_digest"],
        **{name: getattr(kw["parent"], name) for name in TEXT}, expires_at=1100)
    evidence = record(kw["context"].sovereign_authorization_digest, nested,
        *(fixtures._BINDING_GOLDEN[name] for name in DIGESTS[1:4]), kw["policy"].policy_digest, 999, 1020)
    return owner, policies, match, _refresh(evidence, kw), kw


def _check(match, evidence, kw, expected):
    before = deepcopy((evidence, kw))
    assert match(evidence, **kw) is expected
    assert (evidence, kw) == before


def _target(kw, **patch):
    payload = json.loads(kw["target"].signing_input.split(".", 2)[2])
    payload.update(patch)
    payload["effect_request_digest"] = reviews._digest(
        {"effect_kind": payload["effect_kind"], "effect_payload": payload["effect_payload"]})
    kw["target"] = fixtures.lease_owner.build_authoritative_use_lease_request(payload, authority_tier="HIGH")
    kw["expected_target"] = kw["target"].to_dict()


def test_effect_sovereign_exact_data_record(monkeypatch):
    _, policies, match, evidence, kw = _case(monkeypatch)
    assert tuple(field.name for field in fields(evidence)) == FIELDS
    assert all(field.default is MISSING and field.default_factory is MISSING for field in fields(evidence))
    for field in fields(evidence):
        kind = policies.SovereignAuthorizationEvidence if field.name == "parent_authorization" else (
            int if field.name in ("issued_at", "expires_at") else str)
        assert field.type in (kind, kind.__name__)
    assert not hasattr(evidence, "__dict__")
    with pytest.raises(FrozenInstanceError):
        evidence.issued_at = 998
    for name in ("issue", "sign", "consume", "resolve"):
        assert not hasattr(evidence, name)
    assert type(evidence.parent_authorization) is policies.SovereignAuthorizationEvidence
    assert kw["parent"].principal_id != kw["target"].requester_principal_id != kw["policy"].authority_principal_id
    assert kw["target"].signer_public_key not in (kw["parent"].principal_public_key, kw["parent"].reddog_public_key)
    assert kw["target"].nonce != kw["context"].nonce
    _check(match, evidence, kw, True)


@pytest.mark.parametrize("case", ["issue_boundary", "last_current", "all_bounds_equal", "long_evidence",
                                 "zero_digest", "same_references", "target_future_skew"])
def test_effect_sovereign_valid_boundaries_are_data_only(monkeypatch, case):
    _, _, match, evidence, kw = _case(monkeypatch)
    if case == "issue_boundary":
        evidence = replace(evidence, issued_at=1000)
    elif case == "last_current":
        kw["now"] = 1019
    elif case == "all_bounds_equal":
        kw["parent"] = replace(kw["parent"], identity_expires_at=1020, work_authority_expires_at=1020)
        evidence = replace(evidence, parent_authorization=replace(evidence.parent_authorization, expires_at=1020))
    elif case == "long_evidence":
        evidence = replace(evidence, issued_at=0)
    elif case in ("zero_digest", "same_references"):
        value = "sha256:" + "0" * 64 if case == "zero_digest" else evidence.parent_authorization.authorization_digest
        evidence = replace(evidence, authorization_digest=value)
        kw["context"] = replace(kw["context"], sovereign_authorization_digest=value)
    else:
        _target(kw, issued_at=1005)
    _check(match, _refresh(evidence, kw), kw, True)


@pytest.mark.parametrize("case", ["mapping", "subclass", "nested_mapping", "nested_subclass"])
def test_effect_sovereign_requires_exact_records_before_correlation(monkeypatch, case):
    owner, _, match, evidence, kw = _case(monkeypatch)
    _check(match, evidence, kw, True)
    value = evidence.parent_authorization if case.startswith("nested") else evidence
    changed = asdict(value) if case.endswith("mapping") else type("Subclass", (type(value),), {})(
        **{field.name: getattr(value, field.name) for field in fields(value)})
    evidence = replace(evidence, parent_authorization=changed) if case.startswith("nested") else changed
    calls = []
    monkeypatch.setattr(owner, "build_effect_target_binding", lambda **kw: calls.append(kw))
    assert match(evidence, **kw) is False
    assert calls == []


@pytest.mark.parametrize("field", [*DIGESTS, "parent.authorization_digest", "parent.authority_request_digest"])
def test_effect_sovereign_each_digest_is_exact_and_correlated(monkeypatch, field):
    _, _, match, evidence, kw = _case(monkeypatch)
    _check(match, evidence, kw, True)
    nested = field.startswith("parent."); name = field.split(".")[-1]
    value = evidence.parent_authorization if nested else evidence
    for wrong in ("sha256:" + "0" * 64, None, type("Text", (str,), {})(getattr(value, name))):
        changed = replace(value, **{name: wrong})
        changed = replace(evidence, parent_authorization=changed) if nested else changed
        _check(match, changed, kw, False)


@pytest.mark.parametrize("value", ["a" * 64, "sha256:" + "A" * 64, " sha256:" + "a" * 64,
                                  "sha512:" + "a" * 64, "sha256:" + "a" * 63, 17],
                         ids=["bare", "uppercase", "space", "prefix", "short", "integer"])
def test_effect_sovereign_digest_wire_format(monkeypatch, value):
    _, _, match, evidence, kw = _case(monkeypatch)
    _check(match, replace(evidence, authorization_digest=value), kw, False)


@pytest.mark.parametrize("field", TEXT)
def test_effect_sovereign_nested_identity_mismatch_and_text_bound(monkeypatch, field):
    _, _, match, evidence, kw = _case(monkeypatch)
    _check(match, evidence, kw, True)
    _check(match, replace(evidence, parent_authorization=replace(evidence.parent_authorization, **{field: "other"})), kw, False)
    for value, expected in (("x" * 256, True), ("x" * 257, False), ("", False), ("\u00e9", False),
                            (type("Text", (str,), {})("ascii"), False)):
        kw["parent"] = replace(kw["parent"], **{field: value})
        if field == "work_order_id":
            payload = json.loads(kw["target"].signing_input.split(".", 2)[2])
            payload["effect_payload"][field] = value
            if not value or not value.isascii():
                _check(match, replace(evidence, parent_authorization=replace(evidence.parent_authorization, **{field: value})), kw, False)
                continue
            _target(kw, effect_payload=payload["effect_payload"])
        evidence = _refresh(evidence, kw)
        _check(match, evidence, kw, expected)


def test_effect_sovereign_prepared_target_is_still_only_data(tmp_path, monkeypatch):
    _, _, match, evidence, kw = _case(monkeypatch)
    from modules.communication.moltbot_bridge.tests import test_reddog_authoritative_use_request_preparation as prepared
    producer = prepared._case(tmp_path, monkeypatch)
    kw["target"] = prepared._api(producer)(payload=producer.payload, authority_tier="HIGH")
    assert kw["target"] is not None
    evidence = _refresh(evidence, kw)
    _check(match, evidence, kw, True)
    prepared._quiet(producer)
