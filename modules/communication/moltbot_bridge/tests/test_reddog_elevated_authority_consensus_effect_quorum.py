"""Conditional effect-review quorum tests; inert evidence grants no authority."""

from dataclasses import asdict, replace

import pytest

from modules.communication.moltbot_bridge.tests.test_reddog_elevated_authority_consensus_effect_reviewer import (
    PREFIX, _check, _digest, _json, _preimage,
)
from modules.communication.moltbot_bridge.tests.reddog_elevated_consensus_effect_quorum_test_support import (
    _quorum_bind, _quorum_case, _quorum_evidence,
)


@pytest.mark.parametrize("case", ["list", "tuple", "eight", "one_allowed", "last_current", "arbitrary_sovereign"])
def test_effect_review_set_positive_retains_verified_pairs(monkeypatch, case):
    verify, kw = _quorum_case(monkeypatch, 8 if case == "eight" else 2)
    if case == "one_allowed":
        kw["decisions"] = kw["decisions"][:1]
        kw["policy"] = replace(kw["policy"], minimum_approvals=1, required_roles=("critic",))
        kw["context"] = replace(kw["context"], required_approvals=1, required_roles=("critic",))
    elif case == "last_current":
        kw["now"] = 1019
    elif case == "arbitrary_sovereign":
        kw["context"] = replace(kw["context"], sovereign_authorization_digest="sha256:" + "a" * 64)
    _quorum_bind(kw)
    _quorum_evidence(kw)
    if case == "tuple":
        kw["decisions"] = tuple(kw["decisions"])
    assert len(_json({"decisions": kw["decisions"]}).encode("ascii")) <= 8192
    _check(verify, kw, True)
    decisions = kw["decisions"]
    assert kw["reviewer_key_resolver"].calls == [(d["reviewer_principal_id"], d["reviewer_principal_provider"]) for d in decisions]
    assert kw["runtime_evidence_resolver"].calls == [
        (d["reviewer_principal_id"], d["model_selection_receipt_id"], d["model_runtime_binding_receipt_id"]) for d in decisions]
    assert kw["signature_verifier"].calls == [(d["reviewer_public_key"], _preimage(d), d["signature"]) for d in decisions]


@pytest.mark.parametrize("case", ["none", "empty", "mapping", "text", "list_subclass", "tuple_subclass", "nine",
    "second_none", "second_extra", "second_legacy", "second_non_ascii", "second_long_field"])
def test_effect_review_set_decodes_all_before_collaborators(monkeypatch, case):
    verify, kw = _quorum_case(monkeypatch)
    decisions = kw["decisions"]
    containers = {"none": None, "empty": [], "mapping": {"decisions": decisions}, "text": "decisions",
        "list_subclass": type("ListSubclass", (list,), {})(decisions),
        "tuple_subclass": type("TupleSubclass", (tuple,), {})(decisions), "nine": decisions[:1] * 9}
    if case in containers:
        kw["decisions"] = containers[case]
    elif case == "second_none":
        decisions[1] = None
    else:
        field, value = {"second_extra": ("untrusted", True),
            "second_legacy": ("schema_version", "reddog_elevated_authority_reviewer_decision.v1"),
            "second_non_ascii": ("decision_id", "\u00e9"), "second_long_field": ("decision_id", "d" * 4097)}[case]
        decisions[1][field] = value
    _check(verify, kw, False, early=True)


@pytest.mark.parametrize("size,expected", [(8192, True), (8193, False)])
def test_effect_review_set_aggregate_envelope_boundary(monkeypatch, size, expected):
    verify, kw = _quorum_case(monkeypatch)
    for d in kw["decisions"]:
        d["signature"] = "s"
    padding = size - len(_json({"decisions": kw["decisions"]}).encode("ascii"))
    assert 0 < padding < 8190
    kw["decisions"][0]["signature"] += "s" * (padding // 2)
    kw["decisions"][1]["signature"] += "s" * (padding - padding // 2)
    assert all(0 < len(d["signature"]) <= 4096 and len(_json(d).encode("ascii")) <= 8192 for d in kw["decisions"])
    assert len(_json({"decisions": kw["decisions"]}).encode("ascii")) == size
    _quorum_evidence(kw)
    _check(verify, kw, expected, early=not expected)


@pytest.mark.parametrize("case", ["below_minimum", "missing_role", "duplicate_id", "duplicate_key", "duplicate_model",
    "duplicate_runtime", "parent_id", "reddog_id", "worker_id", "parent_key", "reddog_key", "author_runtime", "membership"])
def test_effect_review_set_quorum_independence_and_membership(monkeypatch, case):
    verify, kw = _quorum_case(monkeypatch)
    first, second = kw["decisions"]
    if case == "below_minimum":
        kw["decisions"] = [first]
    elif case == "missing_role":
        second["reviewer_role"] = "critic"
    elif case.startswith("duplicate_"):
        field = {"duplicate_id": "reviewer_principal_id", "duplicate_key": "reviewer_public_key",
            "duplicate_model": "reviewer_model_id", "duplicate_runtime": "model_runtime_binding_digest"}[case]
        second[field] = first[field]
        if case == "duplicate_id":
            second["reviewer_principal_provider"] = "another-provider"
    elif case in {"parent_id", "reddog_id", "worker_id"}:
        if case == "worker_id":
            kw["authority_request"] = replace(kw["authority_request"], queue_consumer_receipt={"worker_id": "queue-worker"})
        second["reviewer_principal_id"] = {"parent_id": kw["authority_request"].principal_id,
            "reddog_id": kw["authority_request"].reddog_id, "worker_id": "queue-worker"}[case]
    elif case in {"parent_key", "reddog_key"}:
        second["reviewer_public_key"] = getattr(kw["authority_request"],
            "principal_public_key" if case == "parent_key" else "reddog_public_key")
    elif case == "author_runtime":
        kw["authority_request"] = replace(kw["authority_request"], model_runtime_binding_digest=second["model_runtime_binding_digest"])
    if case != "membership":
        members = tuple((d["reviewer_principal_id"], d["reviewer_principal_provider"], d["reviewer_role"]) for d in kw["decisions"])
        kw["policy"] = replace(kw["policy"], reviewer_membership=members + (("unused", "test", "verifier"),))
    else:
        second["reviewer_principal_provider"] = "not-member"
    _quorum_bind(kw)
    _quorum_evidence(kw)
    _check(verify, kw, False)


@pytest.mark.parametrize("case", ["context_mapping", "context_digest", "target", "expected_target", "parent", "expired",
    "future", "boolean_now", "policy_digest", "policy_minimum", "policy_roles", "policy_ttl"])
def test_effect_review_set_context_policy_target_before_collaborators(monkeypatch, case):
    verify, kw = _quorum_case(monkeypatch)
    if case == "context_mapping":
        kw["context"] = kw["context"].to_dict()
    elif case == "context_digest":
        kw["context"] = replace(kw["context"], target_signing_request_digest="sha256:" + "0" * 64)
    elif case == "target":
        kw["target"] = replace(kw["target"], authority_tier="ULTRA")
    elif case == "expected_target":
        kw["expected_target"]["authority_tier"] = "ULTRA"
    elif case == "parent":
        kw["authority_request"] = replace(kw["authority_request"], work_order_id="other")
    elif case in {"expired", "future", "boolean_now"}:
        kw["now"] = {"expired": 1020, "future": 999, "boolean_now": True}[case]
    else:
        changes = {"policy_digest": {"policy_digest": "sha256:" + "0" * 64},
            "policy_minimum": {"minimum_approvals": 1}, "policy_roles": {"required_roles": ("critic",)},
            "policy_ttl": {"maximum_ttl_seconds": 19}}
        kw["policy"] = replace(kw["policy"], **changes[case])
        if case != "policy_digest":
            payload = asdict(kw["policy"])
            payload.pop("policy_digest")
            kw["policy"] = replace(kw["policy"], policy_digest=_digest(payload))
            kw["context"] = replace(kw["context"], consensus_policy_digest=kw["policy"].policy_digest)
    _check(verify, kw, False, early=True)


@pytest.mark.parametrize("case", ["missing_key", "missing_runtime", "key_exception", "runtime_exception", "key_expired",
    "runtime_expired", "key_epoch", "key_public", "runtime_model", "runtime_digest", "revoked", "decision_context", "reject"])
def test_effect_review_set_any_invalid_evidence_rejects_whole_set(monkeypatch, case):
    verify, kw = _quorum_case(monkeypatch)
    second = kw["decisions"][1]
    keys, runtimes = kw["reviewer_key_resolver"], kw["runtime_evidence_resolver"]
    key_id = (second["reviewer_principal_id"], second["reviewer_principal_provider"])
    runtime_id = (second["reviewer_principal_id"], second["model_selection_receipt_id"], second["model_runtime_binding_receipt_id"])
    if case in {"missing_key", "missing_runtime"}:
        (keys if case == "missing_key" else runtimes).value.pop(key_id if case == "missing_key" else runtime_id)
    elif case in {"key_exception", "runtime_exception"}:
        (keys if case == "key_exception" else runtimes).error = True
    elif case in {"key_expired", "key_epoch", "key_public"}:
        changes = {"key_expired": {"expires_at": 1000}, "key_epoch": {"key_epoch": "other"}, "key_public": {"public_key": "other"}}
        keys.value[key_id] = replace(keys.value[key_id], **changes[case])
    elif case in {"runtime_expired", "runtime_model", "runtime_digest"}:
        changes = {"runtime_expired": {"expires_at": 1000}, "runtime_model": {"reviewer_model_id": "other"},
            "runtime_digest": {"model_runtime_binding_digest": "sha256:" + "0" * 64}}
        runtimes.value[runtime_id] = replace(runtimes.value[runtime_id], **changes[case])
    elif case == "revoked":
        kw["revoked_key_epochs"] = frozenset({second["reviewer_key_epoch"]})
    elif case == "decision_context":
        second["consensus_context_digest"] = "sha256:" + "0" * 64
    else:
        second["decision"] = "REJECT"
    _check(verify, kw, False)


@pytest.mark.parametrize("case", ["false", "truthy", "exception", "second_signature", "delegated_domain"])
def test_effect_review_set_requires_each_exact_effect_signature(monkeypatch, case):
    verify, kw = _quorum_case(monkeypatch)
    verifier = kw["signature_verifier"]
    if case in {"false", "truthy"}:
        verifier.override = False if case == "false" else 1
    elif case == "exception":
        verifier.error = True
    elif case == "second_signature":
        kw["decisions"][1]["signature"] = "tampered"
    else:
        key, preimage, signature = verifier.value[1]
        verifier.value = (verifier.value[0], (key, preimage.replace(PREFIX, "reddog-elevated-consensus-review.v1.", 1), signature))
    _check(verify, kw, False)
    assert verifier.calls
    assert all(call[1].startswith(PREFIX) for call in verifier.calls)
    if case in {"second_signature", "delegated_domain"}:
        assert len(verifier.calls) == 2
