"""Pure effect/parent coverage and exception boundaries; no issued permit."""

from dataclasses import asdict, replace
import json
import time

import pytest

from modules.communication.moltbot_bridge.tests.test_reddog_effect_sovereign_evidence import (
    DIGESTS, _case, _check, _refresh, _target, fixtures, reviews,
)


@pytest.mark.parametrize("field", ["now", "issued_at", "expires_at", "parent_expires_at"])
def test_effect_sovereign_exact_integer_times(monkeypatch, field):
    _, _, match, evidence, kw = _case(monkeypatch)
    _check(match, evidence, kw, True)
    for bad in (True, 1000.0, "1000", type("Integer", (int,), {})(1000)):
        changed, args = evidence, dict(kw)
        if field == "now":
            args["now"] = bad
        elif field == "parent_expires_at":
            changed = replace(evidence, parent_authorization=replace(evidence.parent_authorization, expires_at=bad))
        else:
            changed = replace(evidence, **{field: bad})
        _check(match, changed, args, False)


@pytest.mark.parametrize("case", ["negative_issue", "issue_after_context", "context_after_now", "context_expired",
                                 "evidence_short", "parent_evidence_short", "identity_short", "authority_short",
                                 "target_short", "negative_now", "zero_parent_expiry", "excessive_skew"])
def test_effect_sovereign_lifetime_coverage(monkeypatch, case):
    _, _, match, evidence, kw = _case(monkeypatch)
    _check(match, evidence, kw, True)
    if case in ("negative_issue", "issue_after_context", "evidence_short"):
        evidence = replace(evidence, **{"negative_issue": {"issued_at": -1}, "issue_after_context": {"issued_at": 1001},
                                       "evidence_short": {"expires_at": 1019}}[case])
    elif case in ("context_after_now", "context_expired"):
        kw["context"] = replace(kw["context"], **({"issued_at": 1001} if case == "context_after_now" else {"expires_at": 1000}))
    elif case in ("parent_evidence_short", "zero_parent_expiry"):
        evidence = replace(evidence, parent_authorization=replace(evidence.parent_authorization,
                           expires_at=1019 if case == "parent_evidence_short" else 0))
    elif case in ("identity_short", "authority_short"):
        kw["parent"] = replace(kw["parent"], **{("identity_expires_at" if case == "identity_short" else "work_authority_expires_at"): 1019})
        evidence = _refresh(evidence, kw)
    elif case == "negative_now":
        kw["now"] = -1
    else:
        _target(kw, **({"expires_at": 1019} if case == "target_short" else {"issued_at": 1006}))
        kw["context"] = replace(kw["context"], expires_at=1015)
        evidence = _refresh(evidence, kw)
    _check(match, evidence, kw, False)


@pytest.mark.parametrize("field", DIGESTS[1:4])
def test_effect_sovereign_recomputes_each_binding_even_if_context_agrees(monkeypatch, field):
    _, _, match, evidence, kw = _case(monkeypatch)
    _check(match, evidence, kw, True)
    forged = "sha256:" + "0" * 64
    kw["context"] = replace(kw["context"], **{field: forged})
    evidence = replace(evidence, **{field: forged})
    if field == "parent_authority_request_digest":
        evidence = replace(evidence, parent_authorization=replace(evidence.parent_authorization, authority_request_digest=forged))
    _check(match, evidence, kw, False)


@pytest.mark.parametrize("case", ["requester", "signer", "epoch", "nonce", "replay", "generation", "effect",
                                 "proof", "ultra", "live_enqueue", "expected_stale"])
def test_effect_sovereign_rechecks_complete_actual_target(monkeypatch, case):
    _, _, match, evidence, kw = _case(monkeypatch)
    _check(match, evidence, kw, True)
    patches = {"requester": {"requester_principal_id": "github:other"}, "signer": {"signer_public_key": "other-key"},
               "epoch": {"key_epoch": "other-epoch"}, "nonce": {"lease_nonce": "b" * 64},
               "replay": {"replay_store_id": "signer-grant-replay:other"}, "generation": {"generation": 2}}
    if case in patches:
        _target(kw, **patches[case])
    elif case == "effect":
        payload = json.loads(kw["target"].signing_input.split(".", 2)[2])
        payload["effect_payload"]["valve_decision_digest"] = "sha256:" + "9" * 64
        _target(kw, effect_payload=payload["effect_payload"])
    elif case in ("proof", "ultra"):
        kw["target"] = replace(kw["target"], **({"elevated_consensus_proof": {}} if case == "proof" else {"authority_tier": "ULTRA"}))
        kw["expected_target"] = kw["target"].to_dict()
    elif case == "live_enqueue":
        _target(kw, effect_kind="live_enqueue", effect_payload={"work_order_id": "work-order-1", "evidence_digest": "sha256:" + "a" * 64})
    else:
        kw["expected_target"]["requester_principal_id"] = "github:other"
    _check(match, evidence, kw, False)
    if case in patches or case == "effect":
        _check(match, _refresh(evidence, kw), kw, True)


@pytest.mark.parametrize("case", ["digest", "roles", "threshold", "ttl", "mapping"])
def test_effect_sovereign_rechecks_explicit_policy(monkeypatch, case):
    _, _, match, evidence, kw = _case(monkeypatch)
    _check(match, evidence, kw, True)
    if case == "mapping":
        kw["policy"] = asdict(kw["policy"])
    else:
        patches = {"digest": {"policy_digest": "sha256:" + "0" * 64}, "roles": {"required_roles": ("critic",)},
                   "threshold": {"minimum_approvals": 1}, "ttl": {"maximum_ttl_seconds": 1}}
        kw["policy"] = replace(kw["policy"], **patches[case])
        if case != "digest":
            data = asdict(kw["policy"]); data.pop("policy_digest")
            kw["policy"] = replace(kw["policy"], policy_digest=reviews._digest(data))
        evidence = _refresh(evidence, kw)
    _check(match, evidence, kw, False)


def test_effect_sovereign_parent_backreferences_remain_separate(monkeypatch):
    _, _, match, evidence, kw = _case(monkeypatch)
    before = evidence.parent_authority_request_digest
    kw["parent"] = replace(kw["parent"], consensus_receipt_digest="sha256:" + "5" * 64)
    _check(match, evidence, kw, True)
    kw["parent"] = replace(kw["parent"], sovereign_authorization_digest="sha256:" + "7" * 64)
    _check(match, evidence, kw, False)
    evidence = _refresh(evidence, kw)
    assert evidence.parent_authority_request_digest == before
    assert evidence.authorization_digest != evidence.parent_authorization.authorization_digest
    _check(match, evidence, kw, True)


@pytest.mark.parametrize("case", ["parent_mapping", "context_mapping", "target_mapping", "expected_subclass", "parent_future"])
def test_effect_sovereign_reuses_existing_input_validation(monkeypatch, case):
    _, _, match, evidence, kw = _case(monkeypatch)
    _check(match, evidence, kw, True)
    if case.endswith("mapping"):
        field = case.split("_")[0]
        kw[field] = kw[field].to_dict()
    elif case == "expected_subclass":
        kw["expected_target"] = type("Mapping", (dict,), {})(kw["expected_target"])
    else:
        kw["parent"] = replace(kw["parent"], issued_at=1001)
        evidence = _refresh(evidence, kw)
    _check(match, evidence, kw, False)


@pytest.mark.parametrize("error", [ValueError, KeyboardInterrupt, SystemExit], ids=["exception", "interrupt", "exit"])
def test_effect_sovereign_helper_failure_boundary(monkeypatch, error):
    owner, _, match, evidence, kw = _case(monkeypatch)
    _check(match, evidence, kw, True)
    instance = error("inert marker")
    def fail(**kwargs):
        raise instance
    monkeypatch.setattr(owner, "build_effect_target_binding", fail)
    if error is ValueError:
        _check(match, evidence, kw, False)
    else:
        with pytest.raises(error) as caught:
            match(evidence, **kw)
        assert caught.value is instance


def test_effect_sovereign_no_clock_resolver_issuer_or_storage_call(monkeypatch):
    _, policies, match, evidence, kw = _case(monkeypatch)
    calls = []
    def forbidden(*args, **kwargs):
        calls.append("effect")
        raise AssertionError("pure matcher attempted an effect")
    issuer = fixtures.lease_fixture.issuer_module.ExternalSignerAuthoritativeUseLeaseIssuer
    store = fixtures.lease_fixture.DurableSignerSecretGrantNonceStore
    with monkeypatch.context() as patch:
        patch.setattr(time, "time", forbidden)
        patch.setattr(policies.SovereignAuthorizationEvidenceResolver, "resolve", forbidden)
        for name in ("issue", "prepare_request"):
            patch.setattr(issuer, name, forbidden)
        for name in ("consume_grant", "consume_authoritative_use_lease", "consume_scoped_nonce"):
            patch.setattr(store, name, forbidden)
        _check(match, evidence, kw, True)
    assert calls == []


@pytest.mark.parametrize("case", ["digest_type", "negative_now", "nested_text"])
def test_effect_sovereign_rejects_bad_scalars_before_correlation(monkeypatch, case):
    owner, _, match, evidence, kw = _case(monkeypatch)
    _check(match, evidence, kw, True)
    if case == "digest_type":
        evidence = replace(evidence, authorization_digest=17)
    elif case == "negative_now":
        kw["now"] = -1
    else:
        evidence = replace(evidence, parent_authorization=replace(evidence.parent_authorization, principal_id="x" * 257))
    calls = []
    monkeypatch.setattr(owner, "build_effect_target_binding", lambda **kwargs: calls.append(kwargs))
    assert match(evidence, **kw) is False
    assert calls == []
