"""Synthetic consent provenance; real codecs/crypto and disposable artifact reads."""

from copy import deepcopy
from dataclasses import asdict, replace
import hashlib
import importlib
import json
from types import SimpleNamespace

from modules.communication.moltbot_bridge.tests.reddog_reviewer_authority_test_support import (
    ROOT, Ed25519PrivateKey, canonical, digest, fixture, public, sign,
)
from modules.communication.moltbot_bridge.tests.reddog_reviewer_composition_test_support import Lease, assert_closed
from modules.communication.moltbot_bridge.tests import test_reddog_effect_sovereign_evidence as supplied

PREFIX = "reddog-effect-consent.v1."
AUTHORITY = "reddog_effect_consent_authority.v1"
ASSERTION = "reddog_effect_consent.v1"
PRIVILEGE = "authorize_exact_high_worktree_effect"
CURRENT = ("manifest_id", "artifact_generation_digest", "generation", "generation_revision", "owner_config_id", "config_digest")


def api():
    name = ROOT + "reddog_effect_consent_contract"
    assert importlib.util.find_spec(name) is not None, "effect_consent_contract_api_missing"
    value = importlib.import_module(name)
    for field in ("validate_effect_consent_authority", "validate_effect_consent_assertion",
                  "canonical_effect_consent_signing_input", "effect_consent_authority_digest"):
        assert callable(getattr(value, field, None)), field + "_api_missing"
    return value


def materials(monkeypatch):
    _, _, _, evidence, kw = supplied._case(monkeypatch)
    issuer, beneficiary, signer = [Ed25519PrivateKey.generate() for _ in range(3)]
    kw["parent"] = replace(kw["parent"], principal_public_key=public(beneficiary), reddog_public_key=public(signer))
    supplied._target(kw, signer_public_key=public(signer))
    evidence = supplied._refresh(evidence, kw)
    payload = json.loads(kw["target"].signing_input.split(".", 2)[2])
    parent = kw["parent"]
    authority = dict(schema_version=AUTHORITY, privilege=PRIVILEGE, issuer_principal_id="issuer:test",
        issuer_principal_provider="consent-test", issuer_public_key=public(issuer), issuer_key_epoch="consent-1",
        repo_full_name=parent.repo_full_name, foundup_id=parent.foundup_id, policy_digest=kw["policy"].policy_digest,
        authority_tier="HIGH", effect_kind="worktree_create", requester_principal_id=kw["target"].requester_principal_id,
        requester_principal_provider="requester-test", beneficiary_principal_id=parent.principal_id,
        beneficiary_principal_provider=parent.principal_provider, reddog_id=parent.reddog_id,
        target_signer_profile_id=payload["signer_profile_id"], target_signer_public_key=kw["target"].signer_public_key,
        target_signer_key_epoch=kw["target"].key_epoch, issued_at=900, expires_at=1100)
    assertion = {k: v for k, v in authority.items() if k != "issuer_public_key"}
    assertion.update(schema_version=ASSERTION, issued_at=999, expires_at=1020,
        owner_authority_digest=digest(authority), parent_authorization=asdict(evidence.parent_authorization),
        **{k: getattr(evidence, k) for k in ("parent_authority_request_digest", "target_signing_request_digest", "effect_request_digest")})
    state = SimpleNamespace(authority=authority, assertion=assertion, issuer=issuer, evidence=evidence, kw=kw, payload=payload)
    resign(state)
    return state


def resign(state, prefix=PREFIX):
    state.message = sign(state.assertion, state.issuer, prefix)
    value = "sha256:" + hashlib.sha256(state.message.encode("ascii")).hexdigest()
    state.kw["context"] = replace(state.kw["context"], sovereign_authorization_digest=value)
    state.evidence = replace(state.evidence, authorization_digest=value)
    if hasattr(state, "call"):
        state.call["context"] = state.kw["context"]


def record(state, principal_id, provider, key):
    return dict(principal_id=principal_id, principal_provider=provider, principal_public_key=key,
        repo_scope=[state.authority["repo_full_name"]], foundup_scope=[state.authority["foundup_id"]],
        verified_subject_digest="sha256:" + "b" * 64, reward_account=None, owner_dae=None, principal_wallet=None)


def setup(monkeypatch, tmp_path):
    facade = importlib.import_module(ROOT + "reddog_signer_current_principal_authority_resolver")
    resolve = getattr(facade, "resolve_current_effect_sovereign_authorization", None)
    assert callable(resolve), "current_effect_consent_resolver_api_missing"
    state = materials(monkeypatch)
    state.runtime = importlib.import_module(ROOT + "reddog_current_effect_consent_verification")
    state.loader = importlib.import_module(ROOT + "reddog_signer_system_service_manifest_selection_loader")
    state.repo, state.store = tmp_path / "repo", tmp_path / "runtime"
    state.repo.mkdir(); state.store.mkdir()
    state.owner = dict(schema_version="reddog_signer_system_service_owner_config.v6",
        effect_consent_authority=state.authority, config_id=state.payload["owner_config_id"])
    state.selection = {k: state.payload[k] for k in CURRENT}
    state.selection.update(runtime_root=str(state.store), manifest_expires_at=1060, selection_expires_at=1060,
        selection_issued_at=1000, principal_authority_records_path=str(state.store / "principal_authority_records.json"))
    pairs = [("issuer:test", "consent-test", state.authority["issuer_public_key"]),
        (state.authority["requester_principal_id"], "requester-test", state.authority["issuer_public_key"]),
        (state.kw["parent"].principal_id, state.kw["parent"].principal_provider, state.kw["parent"].principal_public_key)]
    state.artifact = dict(schema_version="reddog_authority_runtime_resolver_supply.v1",
        principals={p + "|" + i: record(state, i, p, k) for i, p, k in pairs}, principal_count=3,
        resolver_supply_receipt_id="sha256:" + "c" * 64, no_holoindex_reindex_performed=True)
    state.now, state.reads, state.artifact_reads = 1000, 0, 0
    state.lease_error = state.owner_error = False
    state.callback = state.owner_callback = state.clock_callback = None
    state.crypto, state.loaded_records = [], None
    state.lease = Lease(state)
    state.call = dict(owner_config_path=tmp_path / "owner.json", repo_root=state.repo,
        assertion=state.assertion, **{k: v for k, v in state.kw.items() if k != "now"})
    refresh(state)
    install(monkeypatch, state)
    return resolve, state


def refresh(state):
    state.artifact["principal_count"] = len(state.artifact["principals"])
    raw = canonical(state.artifact).encode("ascii")
    (state.store / "principal_authority_records.json").write_bytes(raw)
    state.selection["principal_authority_records_digest"] = "sha256:" + hashlib.sha256(raw).hexdigest()


def install(monkeypatch, state):
    principals = importlib.import_module(ROOT + "reddog_signer_owner_e0_principal_authority")
    backend = importlib.import_module(ROOT + "reddog_ed25519_signature_verifier_backend")
    original, read = backend.Ed25519SignatureVerifier.verify, principals.load_current_generation_principal_artifact
    def owner(*args, **kwargs):
        state.reads += 1
        if state.owner_error:
            raise ValueError("synthetic owner failure")
        if state.reads > 1:
            assert state.lease.active
            if state.owner_callback:
                state.owner_callback(state)
        return deepcopy(state.owner)
    def select(owner, *, repo):
        state.lease.selected += 1
        return state.lease.token, state.lease
    def observe(self, key, message, signature):
        assert state.lease.active
        result = original(self, key, message, signature)
        state.crypto.append((key, message, signature, result))
        if state.callback:
            state.callback(state)
        return result
    def artifact_read(**kwargs):
        assert state.lease.active
        state.artifact_reads += 1
        result = read(**kwargs)
        state.loaded_records = result[0]
        return result
    def clock():
        if state.reads >= 2 and state.clock_callback:
            state.clock_callback(state)
        return state.now
    monkeypatch.setattr(state.loader, "_load_owner_config", owner)
    monkeypatch.setattr(state.loader, "_manifest_selection_from_owner", select)
    monkeypatch.setattr(state.runtime, "_now_epoch", clock)
    monkeypatch.setattr(backend.Ed25519SignatureVerifier, "verify", observe)
    monkeypatch.setattr(principals, "load_current_generation_principal_artifact", artifact_read)


def closed(state):
    assert_closed(state)
    assert state.artifact_reads <= 1


def positive(resolve, state):
    result = resolve(**state.call)
    assert type(result) is type(state.evidence) and result == state.evidence
    assert supplied._api()[3](result, **{**state.kw, "now": state.now}) is True
    assert state.crypto == [(state.authority["issuer_public_key"], state.message, state.assertion["signature"], True)]
    assert state.reads == 2 and state.artifact_reads == 1
    assert state.lease.selected == state.lease.entered == state.lease.exited == 1
    assert not hasattr(result, "consume") and not hasattr(result, "authority_granted")
    closed(state)


def reset(state):
    closed(state)
    state.reads = state.artifact_reads = 0
    state.lease.selected = state.lease.entered = state.lease.exited = 0
    state.crypto.clear()
