"""Real signed model/approval/grant flow; disposable keys and OS-owner seams."""

from dataclasses import replace
import base64
import pytest

from .reddog_parent_consensus_test_support import setup
from .test_reddog_effect_signing_grant import provider_route
from .reddog_elevated_consensus_e2e_support import _socket_client
from modules.communication.moltbot_bridge.tests.test_reddog_signer_wsp71_ephemeral_backend_factory import (
    _Resolver, SignerKeyProviderProfile, SIGNING_KEY_PREFIX, AUDIT_KEY_PREFIX,
)
from modules.communication.moltbot_bridge.src.reddog_signer_wsp71_ephemeral_backend_factory import Wsp71EphemeralSignerBackendFactory
from modules.communication.moltbot_bridge.src.reddog_elevated_authority_consensus_signer_verification import ElevatedConsensusSignerAuthority
from modules.communication.moltbot_bridge.src.reddog_elevated_authority_consensus_capability import prepare_elevated_authority_signing_permit
from modules.communication.moltbot_bridge.src.reddog_signer_delegated_authority_runtime import public_key_fingerprint


def factory_backend(backend, authority):
    from cryptography.hazmat.primitives import serialization
    raw = backend.private_key.private_bytes(serialization.Encoding.Raw,
        serialization.PrivateFormat.Raw, serialization.NoEncryption())
    refs = ('op://synthetic/grant/sign', 'op://synthetic/grant/audit')
    resolver = _Resolver({refs[0]: SIGNING_KEY_PREFIX + base64.b64encode(raw).decode('ascii'),
                          refs[1]: AUDIT_KEY_PREFIX + base64.b64encode(bytes(range(32))).decode('ascii')})
    profile = SignerKeyProviderProfile(signer_profile_id='synthetic-grant', signer_agent_id='signer:grant',
        signing_key_ref=refs[0], audit_mac_key_ref=refs[1], expected_public_key=backend.public_key,
        expected_key_fingerprint=public_key_fingerprint(backend.public_key), expected_key_epoch=backend.key_epoch,
        permission_snapshot_digest='sha256:' + 'a' * 64, ttl_seconds=60)
    factory = Wsp71EphemeralSignerBackendFactory(profile, resolver,
        secret_grant_authority_policy=backend.secret_grant_authority_policy,
        secret_grant_rate_authority=backend.secret_grant_rate_authority,
        elevated_consensus_signer_authority=authority)
    built = factory()
    assert built.ok and built.backend.elevated_consensus_signer_authority is authority
    assert len(resolver.calls) == 2
    return replace(built.backend, proposal_clock=backend.proposal_clock)


@pytest.mark.parametrize('domain', ['parent', 'effect'])
def test_current_model_parent_effect_authority_reaches_actual_factory_signer(monkeypatch, tmp_path, domain):
    state = setup(monkeypatch, tmp_path / 'approval', real_models=True)
    if domain == 'parent': state.kw['target'] = state.signing_requests[0]
    provider, original = provider_route(monkeypatch, tmp_path / 'grant', state)
    authority = ElevatedConsensusSignerAuthority(None, None, None, None, None, None,
        state.nonces, effect_authority=state.signing, parent_authority=state.parent_authority)
    backend = factory_backend(original, authority)
    client = _socket_client(tmp_path / 'factory.sock', backend, 'provider:grant-client')
    provider = replace(provider, grant_authority=replace(provider.grant_authority, client=client))
    if domain == 'parent':
        supplier = replace(state.parent_authority, proof=state.parent_proof)
        capability = supplier(state.kw['parent'])
        assert capability is not None
        permit = prepare_elevated_authority_signing_permit(capability, authority_request=state.kw['parent'],
            signing_requests=state.signing_requests, now=state.now)
        assert permit is not None
    else:
        permit = state.signing.prepare_permit(state.proof)
    grant = provider.issue_grant(state.kw['target'], elevated_consensus_signing_permit=permit)
    assert grant['expires_at'] <= 1020 and len(state.nonces.consumed) == 1
    assert not state.nonces.reserved and not state.lease.active
    with pytest.raises(ValueError):
        provider.issue_grant(state.kw['target'], elevated_consensus_signing_permit=permit)
