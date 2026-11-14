"""Actual HIGH service backend/factory signature and durable consensus consumption."""
import pytest
import json
from dataclasses import replace
from modules.communication.moltbot_bridge.src import reddog_grant_authority_high_service as high
from .installed_high_service_test_support import service_case
from .test_reddog_live_lease_composition import permit
from .test_reddog_effect_signing_grant import fixtures


@pytest.mark.parametrize('domain', ['parent', 'effect'])
def test_actual_service_factory_signature_and_nonce_commit(monkeypatch, tmp_path, domain):
    state = service_case(monkeypatch, tmp_path, domain)
    admitted = permit(state, domain)
    assert admitted is not None
    try:
        grant = state.provider.issue_grant(state.kw['target'], elevated_consensus_signing_permit=admitted)
    except ValueError:
        pytest.fail(repr((state.failures, state.builds, [r.rejection_code for r in state.responses])))
    assert state.responses[-1].accepted is True
    assert len(state.resolver.calls) == 2 and state.service_entries == 2
    assert fixtures.Ed25519SignatureVerifier().verify(state.original.public_key,
        fixtures.canonical_signer_secret_access_grant_input(grant), grant['signature'])
    assert not state.nonces._owned and not state.lease.active
    assert state.rechecks >= 8
    with pytest.raises(ValueError):
        state.provider.issue_grant(state.kw['target'], elevated_consensus_signing_permit=admitted)


@pytest.mark.parametrize('change', ['missing', 'duplicate', 'oversized', 'selection', 'author-binding',
    'reviewer-binding', 'unknown-proof', 'legacy-effect', 'missing-nonce', 'withdrawn'])
def test_invalid_inputs_never_resolve_signing_credentials(monkeypatch, tmp_path, change):
    state = service_case(monkeypatch, tmp_path)
    admitted = permit(state, 'parent')
    if change == 'missing':
        state.model_path.unlink()
    elif change == 'duplicate':
        state.model_path.write_text('{"author":{},"author":{},"reviewers":{}}')
    elif change == 'oversized':
        state.model_path.write_bytes(b' ' * (1024 * 1024 + 1))
    elif change in {'selection', 'author-binding', 'reviewer-binding'}:
        data = json.loads(state.model_path.read_text())
        if change == 'selection':
            data['author']['selection']['receipt_id'] = 'unbound-selection'
        elif change == 'author-binding':
            data['author']['binding']['unbound'] = True
        else:
            next(iter(data['reviewers'].values()))['binding']['unbound'] = True
        state.model_path.write_text(json.dumps(data))
    elif change in {'unknown-proof', 'legacy-effect'}:
        schema = 'unknown' if change == 'unknown-proof' else 'reddog_effect_consensus_proof.v1'
        state.before_request = lambda request: replace(request,
            elevated_consensus_proof=dict(request.elevated_consensus_proof, schema_version=schema))
    elif change == 'missing-nonce':
        object.__setattr__(state.backend, 'dependencies', replace(state.backend.dependencies, consensus_nonce_authority=None))
    else:
        state.before_request = lambda request: (setattr(state, 'exit_failure', True) or request)
    with pytest.raises(ValueError):
        state.provider.issue_grant(state.kw['target'], elevated_consensus_signing_permit=admitted)
    assert not state.resolver.calls and not state.nonces._owned and not state.lease.active


@pytest.mark.parametrize('change', ['models', 'lease-exit', 'owner', 'expired'])
def test_post_signature_failure_withholds_result_and_preserves_consumption(monkeypatch, tmp_path, change):
    state = service_case(monkeypatch, tmp_path)
    admitted = permit(state, 'parent')
    original_factory = high.Wsp71EphemeralSignerBackendFactory
    signed = []
    def factory(**kwargs):
        built = original_factory(**kwargs)()
        backend = built.backend
        class AfterSign:
            def sign(self, request, peer):
                result = backend.sign(request, peer)
                signed.append(result.accepted)
                if change == 'models':
                    state.model_path.write_text('{}')
                elif change == 'lease-exit':
                    state.exit_failure = True
                elif change == 'owner':
                    state.owner['parent_consent_authority']['issuer_key_epoch'] = 'withdrawn'
                else:
                    state.now = 1031
                return result
        return lambda: replace(built, backend=AfterSign())
    monkeypatch.setattr(high, 'Wsp71EphemeralSignerBackendFactory', factory)
    with pytest.raises(ValueError):
        state.provider.issue_grant(state.kw['target'], elevated_consensus_signing_permit=admitted)
    assert signed == [True] and state.responses[-1].accepted is False
    assert not state.nonces._owned and not state.lease.active
    # The completed signature/commit cannot be undone by withholding its result.
    state.exit_failure, state.now = False, 1000
    with pytest.raises(ValueError):
        state.provider.issue_grant(state.kw['target'], elevated_consensus_signing_permit=admitted)
