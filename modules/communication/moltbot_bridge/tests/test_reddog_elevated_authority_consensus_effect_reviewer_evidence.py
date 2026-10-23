"""Supplied evidence checks for one effect reviewer, without signing or stores."""

from dataclasses import asdict, replace

import pytest

from modules.communication.moltbot_bridge.tests.test_reddog_elevated_authority_consensus_effect_reviewer import (
    _bind_decision_context, _case, _check, _digest, _json, _sync,
)


@pytest.mark.parametrize("size", [8192, 8193], ids=["at_limit", "over_limit"])
def test_effect_review_enforces_whole_decision_wire_bound(monkeypatch, size):
    verify, kw = _case(monkeypatch)
    decision = kw["decision"]
    decision.update(decision_id="d" * 4096, signature="")
    decision["signature"] = "s" * (size - len(_json(decision).encode("ascii")))
    assert 0 < len(decision["signature"]) <= 4096
    assert len(_json(decision).encode("ascii")) == size
    _check(verify, kw, size == 8192, early=size == 8193)


@pytest.mark.parametrize("case", ["context_expired", "context_future", "parent_stale", "target_stale", "expected_stale", "now_float", "context_mapping"])
def test_effect_review_correlates_actual_current_inputs_before_collaborators(monkeypatch, case):
    verify, kw = _case(monkeypatch)
    if case in {"context_expired", "context_future"}:
        patch = {"issued_at": 999, "expires_at": 1000} if case == "context_expired" else {"issued_at": 1001}
        kw["context"] = replace(kw["context"], **patch)
        _bind_decision_context(kw)
    elif case == "parent_stale":
        kw["authority_request"] = replace(kw["authority_request"], identity_nonce="identity:other")
    elif case == "target_stale":
        kw["target"] = replace(kw["target"], requester_principal_id="github:other")
        kw["expected_target"] = kw["target"].to_dict()
    elif case == "expected_stale":
        kw["expected_target"]["requester_principal_id"] = "github:other"
    elif case == "context_mapping":
        kw["context"] = kw["context"].to_dict()
    else:
        kw["now"] = 1000.0
    _check(verify, kw, False, early=True)


@pytest.mark.parametrize("case", ["mapping", "subclass", "bad_digest", "unreferenced", "roles_order", "minimum", "ttl", "boolean_minimum"])
def test_effect_review_requires_valid_matching_supplied_policy(monkeypatch, case):
    verify, kw = _case(monkeypatch)
    policy = kw["policy"]
    if case == "mapping":
        kw["policy"] = asdict(policy)
    elif case == "subclass":
        kw["policy"] = type("PolicySubclass", (type(policy),), {})(**asdict(policy))
    elif case == "bad_digest":
        kw["policy"] = replace(policy, policy_digest="sha256:" + "0" * 64)
    elif case == "unreferenced":
        payload = asdict(policy)
        payload.pop("policy_digest")
        payload["authority_principal_id"] = "authority:other"
        kw["policy"] = type(policy)(**payload, policy_digest=_digest(payload))
    else:
        patches = {"roles_order": {"required_roles": ("verifier", "critic")}, "minimum": {"minimum_approvals": 1},
                   "ttl": {"maximum_ttl_seconds": 19}, "boolean_minimum": {"minimum_approvals": True}}
        kw["policy"] = replace(policy, **patches[case])
        _sync(kw)
    _check(verify, kw, False, early=True)


@pytest.mark.parametrize("field", ["reviewer_principal_id", "reviewer_principal_provider", "reviewer_role"])
def test_effect_review_requires_exact_policy_membership(monkeypatch, field):
    verify, kw = _case(monkeypatch)
    kw["decision"][field] = "not-a-member"
    _check(verify, kw, False)


EVIDENCE_CASES = [(kind, case) for kind in ("key", "runtime") for case in (
    "missing", "mapping", "subclass", "expiry_now", "expired", "expiry_bool", "expiry_float",
    "expiry_infinite", "expiry_nan", "expiry_text", "exception")]


@pytest.mark.parametrize("kind,case", EVIDENCE_CASES, ids=[kind + "-" + case for kind, case in EVIDENCE_CASES])
def test_effect_review_rejects_missing_invalid_or_stale_evidence(monkeypatch, kind, case):
    verify, kw = _case(monkeypatch)
    resolver = kw["reviewer_key_resolver" if kind == "key" else "runtime_evidence_resolver"]
    if case == "missing":
        resolver.value = None
    elif case == "mapping":
        resolver.value = asdict(resolver.value)
    elif case == "subclass":
        resolver.value = type("EvidenceSubclass", (type(resolver.value),), {})(**asdict(resolver.value))
    elif case == "exception":
        resolver.error = True
    else:
        expiry = {"expiry_now": 1000, "expired": 999, "expiry_bool": True, "expiry_float": 1001.0,
                  "expiry_infinite": float("inf"), "expiry_nan": float("nan"), "expiry_text": "1001"}[case]
        resolver.value = replace(resolver.value, expires_at=expiry)
    _check(verify, kw, False)
    assert not kw["signature_verifier"].calls


MISMATCHES = [("key", "public_key"), ("key", "key_epoch"), ("runtime", "reviewer_model_id"),
    ("runtime", "model_selection_receipt_id"), ("runtime", "model_selection_digest"),
    ("runtime", "model_runtime_binding_receipt_id"), ("runtime", "model_runtime_binding_digest")]


@pytest.mark.parametrize("kind,field", MISMATCHES, ids=[kind + "-" + field for kind, field in MISMATCHES])
def test_effect_review_rejects_evidence_field_substitution(monkeypatch, kind, field):
    verify, kw = _case(monkeypatch)
    resolver = kw["reviewer_key_resolver" if kind == "key" else "runtime_evidence_resolver"]
    value = "sha256:" + "7" * 64 if field.endswith("digest") else "other"
    resolver.value = replace(resolver.value, **{field: value})
    _check(verify, kw, False)
    assert not kw["signature_verifier"].calls


@pytest.mark.parametrize("case", ["parent_id", "reddog_id", "worker_id", "parent_key", "reddog_key", "author_runtime"])
def test_effect_review_requires_reviewer_independence_after_consistent_rebinding(monkeypatch, case):
    verify, kw = _case(monkeypatch)
    parent = kw["authority_request"]
    if case in {"parent_id", "reddog_id"}:
        identity = parent.principal_id if case == "parent_id" else parent.reddog_id
        kw["decision"]["reviewer_principal_id"] = identity
        membership = ((identity, "test", "critic"), ("reviewer:second", "test", "verifier"))
        kw["policy"] = replace(kw["policy"], reviewer_membership=membership)
    elif case == "worker_id":
        kw["authority_request"] = replace(parent, queue_consumer_receipt={"worker_id": "reviewer:test"})
    elif case in {"parent_key", "reddog_key"}:
        key = parent.principal_public_key if case == "parent_key" else parent.reddog_public_key
        kw["decision"]["reviewer_public_key"] = key
        resolver = kw["reviewer_key_resolver"]
        resolver.value = replace(resolver.value, public_key=key)
    else:
        kw["authority_request"] = replace(parent, model_runtime_binding_digest=kw["decision"]["model_runtime_binding_digest"])
    _sync(kw)
    from modules.communication.moltbot_bridge.src.reddog_elevated_authority_consensus_effect_context import effect_approval_context_matches
    assert effect_approval_context_matches(kw["context"], parent=kw["authority_request"], target=kw["target"],
        expected_target=kw["expected_target"], now=kw["now"]) is True
    _check(verify, kw, False)


def test_effect_review_rejects_revoked_reviewer_epoch(monkeypatch):
    verify, kw = _case(monkeypatch)
    kw["revoked_key_epochs"] = frozenset({"reviewer-epoch"})
    _check(verify, kw, False)
    assert not kw["signature_verifier"].calls
