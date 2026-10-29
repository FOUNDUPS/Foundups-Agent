"""Actual crypto/store/factory connection under one scope; no installed HIGH service."""
from dataclasses import replace
from types import SimpleNamespace
import pytest

from .reddog_live_lease_composition_support import setup, authorize
from .test_reddog_parent_consensus_signer import factory_backend
from .test_reddog_effect_signing_grant import provider_route
from .reddog_elevated_consensus_e2e_support import _socket_client
from modules.communication.moltbot_bridge.src.reddog_elevated_authority_consensus_signer_verification import ElevatedConsensusSignerAuthority
from modules.communication.moltbot_bridge.src.reddog_elevated_authority_consensus_capability import prepare_elevated_authority_signing_permit


def route(monkeypatch, tmp_path, state, domain, mutate=None):
    if domain == 'parent':
        state.kw['target'] = state.signing_requests[0]
    provider, original = provider_route(monkeypatch, tmp_path, state)
    authority = ElevatedConsensusSignerAuthority(None, None, None, None, None, None,
        state.nonces, effect_authority=state.signing, parent_authority=state.parent_authority)
    state.responses, state.scopes = [], []
    def sign(request):
        def action(token):
            state.scopes.append(token)
            if hasattr(state, 'scope_probe'):
                state.scope_probe()
            before = state.lease.entered
            backend = factory_backend(original, replace(authority, _live_scope=token))
            client = _socket_client(tmp_path / 'scoped.sock', backend, 'provider:grant-client')
            result = client.sign(request)
            if hasattr(state, 'scope_probe'):
                state.scope_probe()
            assert state.lease.entered == before
            state.responses.append(result)
            if mutate:
                mutate(state)
            return result
        return authorize(monkeypatch, state, action)
    return replace(provider, grant_authority=replace(provider.grant_authority, client=SimpleNamespace(sign=sign)))


def permit(state, domain):
    if domain == 'effect':
        return state.signing.prepare_permit(state.proof)
    capability = replace(state.parent_authority, proof=state.parent_proof)(state.kw['parent'])
    assert capability is not None
    return prepare_elevated_authority_signing_permit(capability, authority_request=state.kw['parent'],
        signing_requests=state.signing_requests, now=state.now)


@pytest.mark.parametrize('domain', ['parent', 'effect'])
def test_actual_model_parent_effect_factory_uses_one_scope(monkeypatch, tmp_path, domain):
    state = setup(monkeypatch, tmp_path)
    provider = route(monkeypatch, tmp_path / 'grant', state, domain)
    admitted = permit(state, domain)
    assert admitted is not None
    grant = provider.issue_grant(state.kw['target'], elevated_consensus_signing_permit=admitted)
    assert grant['expires_at'] <= 1020 and state.responses[-1].accepted is True
    assert not state.nonces._owned and not state.lease.active
    assert state.rechecks >= 8 and state.validations > state.rechecks
    with pytest.raises(ValueError):
        provider.issue_grant(state.kw['target'], elevated_consensus_signing_permit=admitted)


@pytest.mark.parametrize('change', ['exit', 'expiry', 'owner'])
def test_post_signature_failure_withholds_result_without_undoing_effect(monkeypatch, tmp_path, change):
    state = setup(monkeypatch, tmp_path)
    def mutate(current):
        if change == 'exit':
            current.exit_failure = True
        elif change == 'expiry':
            current.now = 1031
        else:
            current.owner['parent_consent_authority']['issuer_key_epoch'] = 'withdrawn'
    provider = route(monkeypatch, tmp_path / 'grant', state, 'parent', mutate)
    admitted = permit(state, 'parent')
    assert admitted is not None
    with pytest.raises(ValueError):
        provider.issue_grant(state.kw['target'], elevated_consensus_signing_permit=admitted)
    assert state.responses[-1].accepted is True
    assert not state.lease.active and not state.nonces._owned
