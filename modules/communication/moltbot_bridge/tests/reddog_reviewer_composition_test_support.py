"""Explicit inert owner/lease seams around real parser and signature checks."""

from contextlib import contextmanager
from copy import deepcopy
import importlib
from types import SimpleNamespace

from modules.communication.moltbot_bridge.tests.reddog_reviewer_authority_test_support import (
    ROOT, artifact, canonical, digest, fixture, public, sign,
)
from modules.communication.moltbot_bridge.tests.test_reddog_elevated_authority_consensus_effect_reviewer import (
    _case,
)


class Lease:
    def __init__(self, state):
        self.state = state
        self.active = False
        self.entered = self.exited = self.selected = 0
        self.token = object()

    def select(self, *args, **kwargs):
        raise AssertionError("must use the selection already returned by owner loader")

    @contextmanager
    def _lease_current(self, token):
        assert token is self.token
        self.entered += 1
        if self.state.lease_error:
            raise ValueError("test-only lease rejection")
        self.active = True
        try:
            yield self.state.selection
        finally:
            self.active = False
            self.exited += 1


def setup(monkeypatch, tmp_path):
    api = importlib.import_module(ROOT + "reddog_elevated_authority_consensus_verification")
    verify = getattr(api, "verify_current_effect_reviewer_decision", None)
    assert callable(verify), "current_effect_reviewer_api_missing"
    runtime = importlib.import_module(ROOT + "reddog_current_effect_reviewer_verification")
    loader = importlib.import_module(ROOT + "reddog_signer_system_service_manifest_selection_loader")
    backend = importlib.import_module(ROOT + "reddog_ed25519_signature_verifier_backend")
    _, kw = _case(monkeypatch)
    authority, designation, issuer, reviewer = fixture()
    authority["policy_digest"] = kw["policy"].policy_digest
    designation["policy_digest"] = kw["policy"].policy_digest
    designation["owner_authority_digest"] = digest(authority)
    kw["decision"]["reviewer_public_key"] = public(reviewer)
    sign(kw["decision"], reviewer, "reddog-effect-consensus-review.v1.")
    sign(designation, issuer)
    repo, store = tmp_path / "repo", tmp_path / "runtime"
    repo.mkdir()
    store.mkdir()
    owner = dict(schema_version="reddog_signer_system_service_owner_config.v5",
        reviewer_designation_authority=authority, config_id="sha256:" + "d" * 64)
    state = SimpleNamespace(now=1000, owner=owner, authority=authority, designation=designation,
        issuer=issuer, reviewer=reviewer, kw=kw, loader=loader, runtime=runtime, reads=0,
        lease_error=False, owner_error=False, callback=None, crypto=[], captured_resolver=None,
        artifact=artifact(authority, designation), store=store)
    state.selection = dict(runtime_root=str(store), principal_authority_records_path=str(store / "principal_authority_records.json"),
        principal_authority_records_digest="pending", manifest_expires_at=1060, selection_expires_at=1060, selection_issued_at=1000,
        owner_config_id=owner["config_id"])
    state.lease = Lease(state)
    _install(monkeypatch, state, backend)
    state.call = dict(owner_config_path=tmp_path / "owner.json", repo_root=repo,
        **{k: v for k, v in kw.items() if k not in ("signature_verifier", "reviewer_key_resolver", "now")})
    refresh(state)
    return verify, state


def _install(monkeypatch, state, backend):
    def load_owner(*args, **kwargs):
        state.reads += 1
        if state.owner_error:
            raise ValueError("test-only owner rejection")
        if state.reads > 1:
            assert state.lease.active, "owner revalidation must occur inside the lease"
        return deepcopy(state.owner)

    def select(owner, *, repo):
        assert owner == state.owner
        state.lease.selected += 1
        return state.lease.token, state.lease

    original = backend.Ed25519SignatureVerifier.verify

    def observe(self, key, message, signature):
        assert state.lease.active, "both cryptographic checks require a live lease"
        result = original(self, key, message, signature)
        state.crypto.append((key, message, signature, result))
        if state.callback:
            state.callback(state, message)
        return result

    monkeypatch.setattr(state.loader, "_load_owner_config", load_owner)
    monkeypatch.setattr(state.loader, "_manifest_selection_from_owner", select)
    monkeypatch.setattr(state.runtime, "_now_epoch", lambda: state.now)
    monkeypatch.setattr(backend.Ed25519SignatureVerifier, "verify", observe)


def refresh(state, *, sign_designation=True, sign_review=True):
    if sign_designation:
        sign(state.designation, state.issuer)
    if sign_review:
        sign(state.kw["decision"], state.reviewer, "reddog-effect-consensus-review.v1.")
    state.artifact["reviewer_authorizations"] = [deepcopy(state.designation)]
    raw = canonical(state.artifact).encode("ascii")
    (state.store / "principal_authority_records.json").write_bytes(raw)
    import hashlib
    state.selection["principal_authority_records_digest"] = "sha256:" + hashlib.sha256(raw).hexdigest()


def assert_closed(state):
    assert not state.lease.active
    assert state.lease.exited == state.lease.entered - int(state.lease_error)
    assert state.lease.selected <= 1
