"""Real factory/Ed25519/model/nonce; synthetic installed owner, permission and OS reads."""
import base64
import json
import traceback
from dataclasses import replace
from types import SimpleNamespace
from cryptography.hazmat.primitives import serialization
from .reddog_live_lease_composition_support import setup, authorize
from .test_reddog_effect_signing_grant import provider_route
from .reddog_elevated_consensus_e2e_support import SignerPeerAttestation
from .test_reddog_parent_consensus_signer import _Resolver, SignerKeyProviderProfile, SIGNING_KEY_PREFIX, AUDIT_KEY_PREFIX
from modules.communication.moltbot_bridge.src import reddog_grant_authority_high_service as high
from modules.communication.moltbot_bridge.src import reddog_parent_consensus_model_evidence as models
from modules.communication.moltbot_bridge.src.reddog_signer_delegated_authority_runtime import public_key_fingerprint
from modules.communication.moltbot_bridge.src.reddog_grant_authority_service import GrantAuthorityServiceDependencies


def service_case(monkeypatch, tmp_path, domain='parent'):
    state = setup(monkeypatch, tmp_path)
    if domain == 'parent':
        state.kw['target'] = state.signing_requests[0]
    provider, original = provider_route(monkeypatch, tmp_path / 'grant', state)
    path = state.call['owner_config_path']
    state.model_path = path.parent / models.PARENT_MODEL_ARTIFACTS_FILENAME
    state.model_path.write_text(json.dumps(state.parent_authority.model_artifacts))
    old_read = state.loader._read_root_owned_bytes
    def read(target, root, **kwargs):
        if target == state.model_path:
            raw = target.read_bytes()
            if len(raw) > kwargs['max_bytes']:
                raise ValueError('synthetic_read_budget')
            return raw
        return old_read(target, root)
    monkeypatch.setattr(state.loader, '_read_root_owned_bytes', read)
    profile, resolver = custody(original)
    state.resolver, state.responses, state.requests = resolver, [], []
    policy = dict(state.policy, grant_requester_principal_id='provider:grant-client')
    deps = GrantAuthorityServiceDependencies(policy, profile, object(),
        original.secret_grant_rate_authority.replay_store, object(), state.nonces)
    backend = high._CurrentHighGrantBackend(state.repo.resolve(), path, deps)
    # Installation/custody and permission/root-oracle seams only. The actual
    # model verifiers, canonical scope, proof owners, factory and stores run.
    monkeypatch.setattr(high, '_current_inputs', lambda *args: (state.owner, original.secret_grant_authority_policy))
    monkeypatch.setattr(high, 'SystemdCredentialSecretResolver', lambda binding: resolver)
    state.provider = _route(monkeypatch, state, provider, backend)
    state.backend, state.original = backend, original
    return state


def _route(monkeypatch, state, provider, backend):
    state.failures, state.builds = [], []
    def authorized(self, action):
        try:
            return authorize(monkeypatch, state, action)
        except Exception as error:
            state.failures.append((type(error).__name__, [(f.name, f.lineno) for f in traceback.extract_tb(error.__traceback__)]))
            raise
    monkeypatch.setattr(high._CurrentHighGrantBackend, 'authorize', authorized)
    original_factory = high.Wsp71EphemeralSignerBackendFactory
    def factory(**kwargs):
        built = original_factory(**kwargs)()
        state.builds.append((built.ok, built.rejection_code))
        if built.backend is not None:
            built = replace(built, backend=replace(built.backend, proposal_clock=lambda: state.now))
        return lambda: built
    monkeypatch.setattr(high, 'Wsp71EphemeralSignerBackendFactory', factory)
    def sign(request):
        if hasattr(state, "before_request"):
            request = state.before_request(request)
        state.requests.append(request)
        entered = state.lease.entered
        result = backend.sign(request, SignerPeerAttestation('provider:grant-client', 'unix_socket', 'SO_PEERCRED', True))
        state.responses.append(result)
        state.service_entries = state.lease.entered - entered
        return result
    provider = replace(provider, grant_authority=replace(provider.grant_authority, client=SimpleNamespace(sign=sign)))
    return provider


def custody(backend):
    raw = backend.private_key.private_bytes(serialization.Encoding.Raw,
        serialization.PrivateFormat.Raw, serialization.NoEncryption())
    refs = ('op://synthetic/grant/sign', 'op://synthetic/grant/audit')
    resolver = _Resolver({refs[0]: SIGNING_KEY_PREFIX + base64.b64encode(raw).decode('ascii'),
        refs[1]: AUDIT_KEY_PREFIX + base64.b64encode(bytes(range(32))).decode('ascii')})
    profile = SignerKeyProviderProfile(signer_profile_id='synthetic-grant', signer_agent_id='signer:grant',
        signing_key_ref=refs[0], audit_mac_key_ref=refs[1], expected_public_key=backend.public_key,
        expected_key_fingerprint=public_key_fingerprint(backend.public_key), expected_key_epoch=backend.key_epoch,
        permission_snapshot_digest='sha256:' + 'a' * 64, ttl_seconds=60)
    return profile, resolver
