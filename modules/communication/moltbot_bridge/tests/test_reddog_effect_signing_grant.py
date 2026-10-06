"""Real provider/socket/grant signatures with synthetic owner/runtime provenance."""

from dataclasses import replace
from types import SimpleNamespace
import pytest

from .reddog_effect_signing_test_support import setup, reset_owner_reads
from . import test_reddog_signer_independent_secret_grant_provider as fixtures
from .reddog_elevated_consensus_e2e_support import _socket_client
from modules.communication.moltbot_bridge.src.reddog_elevated_authority_consensus_signer_verification import ElevatedConsensusSignerAuthority


def provider_route(monkeypatch, tmp_path, state, *, store=None):
    tmp_path.mkdir(parents=True, exist_ok=True)
    monkeypatch.setitem(fixtures._store.__globals__, "NOW", state.now)
    store = fixtures._store(tmp_path) if store is None else store
    private = fixtures.Ed25519PrivateKey.generate()
    target = state.kw["target"]
    binding = replace(fixtures._binding(store, fixtures._public(private)),
        signer_public_key=target.signer_public_key,
        signer_key_fingerprint=fixtures.public_key_fingerprint(target.signer_public_key),
        key_epoch=target.key_epoch)
    state.grant_binding = binding
    policy = fixtures._owner_policy(binding)
    policy.update(allowed_operations=[target.requested_operation], expires_at=state.now + 120)
    signer_policy = replace(fixtures._policy(binding), allowed_operations=(target.requested_operation,))
    consensus = ElevatedConsensusSignerAuthority(None, None, None, None, None, None,
        state.nonces, effect_authority=state.signing)
    backend = fixtures.Ed25519SignerBackend(private_key=private, public_key=fixtures._public(private),
        key_epoch="grant-epoch-1", audit_mac_builder=fixtures._AuditMac(),
        proposal_clock=lambda: state.now, secret_grant_authority_policy=signer_policy,
        secret_grant_rate_authority=fixtures.DurableSignerSecretGrantRateAuthority(store),
        elevated_consensus_signer_authority=consensus)
    client = _socket_client(tmp_path / "effect-grant.sock", backend, "provider:grant-client")
    state.grant_requests, state.grant_responses = [], []
    def sign(request):
        state.grant_requests.append(request)
        response = client.sign(request)
        state.grant_responses.append(response)
        return response
    provider = fixtures._provider_for(tmp_path, monkeypatch, store=store, private=private,
        client=SimpleNamespace(sign=sign), policy=policy)
    return replace(provider, clock=lambda: state.now), backend


def test_real_provider_and_independent_grant_signer_consume_effect_permission(monkeypatch, tmp_path):
    state = setup(monkeypatch, tmp_path / "approval")
    provider, backend = provider_route(monkeypatch, tmp_path / "grant", state)
    target = state.kw["target"]
    permit = state.signing.prepare_permit(state.proof)
    assert permit is not None
    reset_owner_reads(state)
    try:
        grant = provider.issue_grant(target, elevated_consensus_signing_permit=permit)
    except ValueError:
        pytest.fail("grant response codes: " + repr([r.rejection_code for r in state.grant_responses]))
    assert fixtures.Ed25519SignatureVerifier().verify(backend.public_key,
        fixtures.canonical_signer_secret_access_grant_input(grant), grant["signature"])
    assert grant["signing_request_digest"] == fixtures.signer_secret_access_request_digest(target.to_dict())
    assert target.consensus_receipt_digest is None
    assert len(state.nonces.consumed) == 1 and not state.nonces.reserved
    with pytest.raises(ValueError, match="secret_grant_consensus_invalid"):
        provider.issue_grant(target, elevated_consensus_signing_permit=permit)


def test_independent_signer_rechecks_revocation_after_permission_preparation(monkeypatch, tmp_path):
    state = setup(monkeypatch, tmp_path / "approval")
    provider, backend = provider_route(monkeypatch, tmp_path / "grant", state)
    permit = state.signing.prepare_permit(state.proof)
    assert permit is not None
    state.runtime_records.clear()
    reset_owner_reads(state)
    with pytest.raises(ValueError):
        provider.issue_grant(state.kw["target"], elevated_consensus_signing_permit=permit)
    assert not state.nonces.consumed and not state.nonces.reserved


@pytest.mark.parametrize("change", ["none", "rotation", "cleanup"])
def test_grant_rpc_releases_fence_and_rechecks_owner(monkeypatch, tmp_path, change):
    from contextlib import contextmanager
    from modules.communication.moltbot_bridge.src import reddog_signer_independent_secret_grant_provider as owner
    state = setup(monkeypatch, tmp_path / "approval")
    provider, _ = provider_route(monkeypatch, tmp_path / "grant", state)
    permit = state.signing.prepare_permit(state.proof)
    reset_owner_reads(state)
    original_lease = owner.lease_validated_owner_e0_current_admission
    active, entries = [], []
    @contextmanager
    def lease(**kwargs):
        with original_lease(**kwargs) as selected:
            entries.append(1)
            active.append(1)
            try:
                if change == "rotation" and len(entries) == 2:
                    selected.policy = dict(selected.policy, owner_revision="rotated")
                yield selected
            finally:
                active.pop()
        if change == "cleanup":
            raise RuntimeError("synthetic cleanup failure")
    monkeypatch.setattr(owner, "lease_validated_owner_e0_current_admission", lease)
    original_sign = provider.grant_authority.client.sign
    def sign(request):
        assert not active, "provider fence must be released before independent signer RPC"
        return original_sign(request)
    provider = replace(provider, grant_authority=replace(provider.grant_authority,
        client=SimpleNamespace(sign=sign)))
    if change == "none":
        assert provider.issue_grant(state.kw["target"], elevated_consensus_signing_permit=permit)
        assert len(entries) == 2
    else:
        with pytest.raises((ValueError, RuntimeError)):
            provider.issue_grant(state.kw["target"], elevated_consensus_signing_permit=permit)
        assert len(state.grant_requests) == (0 if change == "cleanup" else 1)
    assert not active


def test_effect_permission_cannot_use_held_fence_api(monkeypatch, tmp_path):
    state = setup(monkeypatch, tmp_path / "approval")
    provider, _ = provider_route(monkeypatch, tmp_path / "grant", state)
    permit = state.signing.prepare_permit(state.proof)
    with pytest.raises(ValueError, match="effect_grant_requires_unfenced_issue"):
        with provider.lease(state.kw["target"], elevated_consensus_signing_permit=permit):
            pytest.fail("effect grant entered legacy held-fence API")
    assert not state.grant_requests
