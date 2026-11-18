"""Real consent signatures under explicitly synthetic owner/lease provenance."""

from contextlib import contextmanager
from copy import deepcopy
from dataclasses import replace
import importlib
import pytest

from modules.communication.moltbot_bridge.tests.reddog_effect_consent_test_support import (
    ROOT, PREFIX, closed, digest, fixture, positive, record, refresh, reset, resign, setup,
)


@pytest.mark.parametrize("version", ["v1", "v2"])
def test_current_consent_exact_signature_and_matching_path(monkeypatch, tmp_path, version):
    resolve, state = setup(monkeypatch, tmp_path)
    if version == "v2":
        state.artifact["schema_version"] = "reddog_authority_runtime_resolver_supply.v2"
        state.artifact["reviewer_authorizations"] = [fixture()[1]]
        refresh(state)
    before = deepcopy((state.owner, state.artifact, state.call))
    assert state.authority["requester_principal_id"] != state.authority["beneficiary_principal_id"]
    assert state.authority["requester_principal_provider"] != state.authority["beneficiary_principal_provider"]
    positive(resolve, state)
    assert (state.owner, state.artifact, state.call) == before


SCOPE = ["tamper", "domain", "unknown_issuer", "issuer_key", "issuer_scope", "issuer_alias",
    "requester_ambiguous", "requester_provider", "beneficiary_key", "beneficiary_scope",
    "issuer_epoch", "owner_digest", "requester", "beneficiary", "signer_profile", "policy",
    "parent_reference", "P", "T", "E", "current_generation", "legacy_v5"]


def scope_change(state, case):
    signed, authority, records = state.assertion, state.authority, state.artifact["principals"]
    issuer = records["consent-test|issuer:test"]
    beneficiary = records[authority["beneficiary_principal_provider"] + "|" + authority["beneficiary_principal_id"]]
    if case == "unknown_issuer":
        records.pop("consent-test|issuer:test")
    elif case in {"issuer_key", "issuer_scope", "beneficiary_key", "beneficiary_scope"}:
        item = issuer if case.startswith("issuer") else beneficiary
        item["principal_public_key" if case.endswith("key") else "repo_scope"] = "different-key" if case.endswith("key") else ["other/repo"]
    elif case == "issuer_alias":
        records.pop("consent-test|issuer:test")
        authority["issuer_principal_id"] = signed["issuer_principal_id"] = "issuer|test"
        records["consent-test|issuer|test"] = dict(issuer, principal_id="test", principal_provider="consent-test|issuer")
        signed["owner_authority_digest"] = digest(authority)
    elif case == "requester_ambiguous":
        identity = authority["requester_principal_id"]
        records["other|" + identity] = record(state, identity, "other", issuer["principal_public_key"])
    elif case == "current_generation":
        state.selection["generation"] += 1
    elif case == "legacy_v5":
        state.owner["schema_version"] = "reddog_signer_system_service_owner_config.v5"
    elif case == "parent_reference":
        signed["parent_authorization"]["authorization_digest"] = "sha256:" + "0" * 64
    else:
        fields = {"issuer_epoch": "issuer_key_epoch", "owner_digest": "owner_authority_digest",
            "requester": "requester_principal_id", "requester_provider": "requester_principal_provider",
            "beneficiary": "beneficiary_principal_id", "signer_profile": "target_signer_profile_id",
            "policy": "policy_digest", "P": "parent_authority_request_digest",
            "T": "target_signing_request_digest", "E": "effect_request_digest"}
        if case in fields:
            key = fields[case]
            signed[key] = "sha256:" + "0" * 64 if key.endswith("digest") else "other"
    resign(state, "reddog-reviewer-designation.v1." if case == "domain" else PREFIX)
    if case == "tamper":
        signed["issued_at"] -= 1
    refresh(state)


@pytest.mark.parametrize("case", SCOPE)
def test_current_consent_rejects_signed_scope_mismatch(monkeypatch, tmp_path, case):
    resolve, state = setup(monkeypatch, tmp_path)
    positive(resolve, state); reset(state)
    scope_change(state, case)
    assert resolve(**state.call) is None
    closed(state)


LIFETIME = ["authority_future", "assertion_future", "context_future", "authority_expiry", "assertion_expiry",
    "manifest_expiry", "selection_expiry", "selection_future", "nested_expiry", "owner_drift", "rollback",
    "finish_expiry", "final_owner_mutation", "finish_clock_mutation", "record_mutation"]


def lifetime_change(state, case):
    signed = state.assertion
    if case in {"authority_future", "authority_expiry"}:
        state.authority["issued_at" if case.endswith("future") else "expires_at"] = 1001 if case.endswith("future") else 1019
        signed["owner_authority_digest"] = digest(state.authority)
    elif case in {"assertion_future", "assertion_expiry"}:
        signed["issued_at" if case.endswith("future") else "expires_at"] = 1001 if case.endswith("future") else 1019
    elif case == "context_future":
        state.kw["context"] = replace(state.kw["context"], issued_at=1001)
    elif case in {"manifest_expiry", "selection_expiry", "selection_future"}:
        field = "selection_issued_at" if case.endswith("future") else case.split("_")[0] + "_expires_at"
        state.selection[field] = 1001 if case.endswith("future") else 1019
    elif case == "nested_expiry":
        signed["parent_authorization"]["expires_at"] = 1019
    elif case == "owner_drift":
        state.callback = lambda s: s.owner.update(config_id="sha256:" + "0" * 64)
    elif case in {"rollback", "finish_expiry"}:
        state.callback = lambda s: setattr(s, "now", 999 if case == "rollback" else 1020)
    elif case in {"final_owner_mutation", "finish_clock_mutation"}:
        action = lambda s: s.call["assertion"]["parent_authorization"].update(work_order_id="changed")
        setattr(state, "owner_callback" if case.startswith("final") else "clock_callback", action)
    else:
        state.callback = lambda s: object.__setattr__(s.loaded_records["consent-test|issuer:test"], "repo_scope", ("other",))
    resign(state)


@pytest.mark.parametrize("case", LIFETIME)
def test_current_consent_rechecks_lifetime_and_sampled_inputs(monkeypatch, tmp_path, case):
    resolve, state = setup(monkeypatch, tmp_path)
    positive(resolve, state); reset(state)
    lifetime_change(state, case)
    assert resolve(**state.call) is None
    closed(state)


@pytest.mark.parametrize("error", [ValueError, KeyboardInterrupt, SystemExit], ids=["exception", "interrupt", "exit"])
def test_current_consent_failure_identity_and_lease_cleanup(monkeypatch, tmp_path, error):
    resolve, state = setup(monkeypatch, tmp_path)
    positive(resolve, state); reset(state)
    failure = error("inert verification failure")
    def fail(s):
        raise failure
    state.callback = fail
    if error is ValueError:
        assert resolve(**state.call) is None
    else:
        with pytest.raises(error) as caught:
            resolve(**state.call)
        assert caught.value is failure
    closed(state)


def test_current_consent_ordinary_lease_exit_failure_rejects(monkeypatch, tmp_path):
    resolve, state = setup(monkeypatch, tmp_path)
    positive(resolve, state); reset(state)
    original = state.lease._lease_current
    @contextmanager
    def fails_on_exit(token):
        with original(token) as selected:
            yield selected
        raise RuntimeError("inert exit failure")
    monkeypatch.setattr(state.lease, "_lease_current", fails_on_exit)
    assert resolve(**state.call) is None
    closed(state)


@pytest.mark.parametrize("case", ["extra", "subclass", "huge_time"])
def test_current_consent_shape_rejected_before_owner(monkeypatch, tmp_path, case):
    resolve, state = setup(monkeypatch, tmp_path)
    if case == "extra":
        state.assertion["verified"] = True
    elif case == "subclass":
        state.call["assertion"] = type("DictSubclass", (dict,), {})(state.assertion)
    else:
        state.assertion["issued_at"] = 2 ** 63
    assert resolve(**state.call) is None
    assert state.reads == state.artifact_reads == state.lease.selected == 0 and not state.crypto


def test_current_consent_never_calls_signer_provider_or_nonce_consumer(monkeypatch, tmp_path):
    resolve, state = setup(monkeypatch, tmp_path)
    calls = []
    def forbidden(*args, **kwargs):
        calls.append(True)
        raise AssertionError("consent resolution attempted an effect")
    targets = [("reddog_external_signer_authoritative_use_lease", "ExternalSignerAuthoritativeUseLeaseIssuer", ("issue",)),
        ("reddog_signer_independent_secret_grant_provider", "IndependentSignerSecretGrantProvider", ("lease",)),
        ("reddog_signer_secret_grant_durable_nonce_store", "DurableSignerSecretGrantNonceStore",
         ("consume_grant", "consume_authoritative_use_lease", "consume_scoped_nonce"))]
    for module, name, methods in targets:
        owner = getattr(importlib.import_module(ROOT + module), name)
        for method in methods:
            monkeypatch.setattr(owner, method, forbidden)
    positive(resolve, state)
    assert calls == []


@pytest.mark.parametrize("case", ["initial_clock", "requester_key"])
def test_current_consent_rejects_snapshot_gaps(monkeypatch, tmp_path, case):
    resolve, state = setup(monkeypatch, tmp_path)
    positive(resolve, state); reset(state)
    if case == "initial_clock":
        def clock():
            state.assertion["issuer_key_epoch"] = "changed-at-first-clock"
            return state.now
        monkeypatch.setattr(state.runtime, "_now_epoch", clock)
    else:
        key = state.authority["requester_principal_provider"] + "|" + state.authority["requester_principal_id"]
        state.callback = lambda s: object.__setattr__(s.loaded_records[key], "principal_public_key",
                                                     s.authority["target_signer_public_key"])
    assert resolve(**state.call) is None
    closed(state)
