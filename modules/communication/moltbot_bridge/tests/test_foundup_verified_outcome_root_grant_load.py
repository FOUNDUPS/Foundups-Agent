"""Issuer LOAD dispatch: real signatures/stores, synthetic installed owner/peer.

Existing fixture substitutes generation selection and root filesystem custody.
No service is installed and these results do not prove native grant admission.
"""
import copy
import json
import time
from dataclasses import asdict, replace
from types import SimpleNamespace

import pytest

from modules.communication.moltbot_bridge.src import (
    foundup_verified_outcome_root_revocation_protocol as wire,
    foundup_verified_outcome_root_revocation_client as client,
    reddog_signer_system_service_manifest_selection_loader as loader,
)
from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_authority_router import handle_root_authority_wire_request
from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_authority_service_entrypoint import _peer_policy
from modules.communication.moltbot_bridge.src.reddog_signer_socket_peer_credential_attestor import KernelPeerCredentialAttestor
from modules.communication.moltbot_bridge.src.reddog_signer_secret_grant_root_protected_use_oracle import build_grant_issuer_revocation_oracle
from modules.communication.moltbot_bridge.src.reddog_signer_secret_grant_revocation_durable_oracle import UncomposedDurableSignerGrantRevocationOracle
from modules.communication.moltbot_bridge.src.reddog_ed25519_signature_verifier_backend import Ed25519SignatureVerifier
from modules.communication.moltbot_bridge.tests.root_revocation_service_fixtures import runtime, signed_snapshot, stage
from modules.communication.moltbot_bridge.tests.test_foundup_verified_outcome_root_authority import _sha, _sign
from modules.communication.moltbot_bridge.tests.test_foundup_verified_outcome_root_authority_service import _peer
from modules.communication.moltbot_bridge.tests.test_foundup_verified_outcome_root_revocation_service import _request


def _install_snapshot(values, revoked=False, expired=False):
    from modules.communication.moltbot_bridge.src.reddog_signer_secret_grant_revocation_contract import (
        canonical_signer_grant_revocation_snapshot_input, signer_grant_revocation_snapshot_id,
    )
    candidate = signed_snapshot(values)
    if revoked:
        candidate['revoked_key_epochs'] = [values['policy']['grant_authority_key_epoch']]
    if expired:
        candidate['issued_at'], candidate['expires_at'] = int(time.time())-200, int(time.time())-100
    candidate['snapshot_id'] = signer_grant_revocation_snapshot_id(candidate)
    candidate['signature'] = _sign(values['revocation_private'], canonical_signer_grant_revocation_snapshot_input(candidate))
    stage(values, candidate)
    if not expired:
        values['client'].advance_snapshot(candidate['snapshot_id'])
    else:
        from modules.communication.moltbot_bridge.src.reddog_proposal_authenticity_nonce_store import ProposalReplayHighWater
        values['state'].advance_revocation(values['binding'].anchor_binding_digest(), expected=None,
            next_value=ProposalReplayHighWater(1, candidate['snapshot_id'][7:]))
    values['store']._finalize_under_lock(candidate['snapshot_id'])


def _runtime(tmp_path, monkeypatch, *, install=True, revoked=False, expired=False):
    values = runtime(tmp_path, monkeypatch)
    if install:
        _install_snapshot(values, revoked, expired)
    from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_authority import descriptor_id_for
    descriptor = copy.deepcopy(values['snapshot'].descriptor)
    for left, right in [('signer_key_epoch','target_signer_key_epoch'),
        ('signer_manifest_id','manifest_id'), ('signer_config_digest','config_digest'),
        ('signer_artifact_generation_digest','artifact_generation_digest')]:
        descriptor[left] = values['policy'][right]
    descriptor['descriptor_id'] = descriptor_id_for(descriptor)
    values['snapshot'] = replace(values['snapshot'], descriptor=descriptor)
    snapshot = values['snapshot']
    owner = dict(config_id=values['policy']['owner_config_id'],
        independent_grant_authority=dict(authority_service_uid=1002, authority_service_gid=1001),
        verified_outcome_authority=dict(descriptor=snapshot.descriptor,
            signer_uid=snapshot.signer_uid, signer_gid=snapshot.signer_gid,
            signer_principal_id=snapshot.signer_principal_id))
    monkeypatch.setattr(loader, '_load_owner_config', lambda *a, **k: owner)
    values['owner'] = owner
    return values


def _grant_peer():
    peer = _peer()
    return replace(peer, uid=1002, gid=1001,
        attestation=replace(peer.attestation, peer_principal_id=wire.GRANT_PEER_PRINCIPAL))


def _issuer_request(values, **changes):
    request = replace(_request(values), requester_role=wire.GRANT_ROLE,
        requester_principal_id=values['policy']['grant_authority_principal_id'],
        requester_key_epoch=values['policy']['grant_authority_key_epoch'], **changes)
    return _sign_request(values, request)


def _sign_request(values, request, key='grant_private'):
    request = replace(request, signer_instance_signature=_sign(values[key], wire.canonical_signer_input(request)))
    return replace(request, request_id=wire.request_id_for(asdict(request)))


def _dispatch(values, request, peer=None):
    return wire.response_from_bytes(handle_root_authority_wire_request(request.to_bytes(),
        peer=peer or _grant_peer(), state=values['state'], snapshot_supplier=lambda: values['snapshot'],
        revocation_authority=values['server_authority'], now_epoch=int(time.time())))


def test_issuer_load_dispatch_uses_own_signature_and_leaves_state_unchanged(tmp_path, monkeypatch):
    values = _runtime(tmp_path, monkeypatch)
    before = values['state'].load(values['binding'].anchor_binding_digest())
    request = _issuer_request(values)
    response = _dispatch(values, request)
    assert response.accepted and response.state == 'LOADED' and response.sequence == 1
    assert values['state'].load(values['binding'].anchor_binding_digest()) == before
    assert wire.request_from_bytes(request.to_bytes()).to_bytes() == request.to_bytes()


@pytest.mark.parametrize('mutation', ['uid','gid','principal','unattested','target-key','epoch',
    'issuer-principal','descriptor','policy','owner','owner-drift','expired-request'])
def test_identity_and_current_context_substitutions_reject(tmp_path, monkeypatch, mutation):
    values = _runtime(tmp_path, monkeypatch)
    request, peer = _issuer_request(values), _grant_peer()
    if mutation in ('uid','gid'):
        peer = replace(peer, **{mutation:9876})
    elif mutation in ('principal','unattested'):
        peer = replace(peer, attestation=replace(peer.attestation,
            **({'peer_principal_id':'attacker'} if mutation=='principal' else {'boundary_attested':False})))
    elif mutation == 'target-key':
        request = _sign_request(values, request, 'target_private')
    elif mutation == 'owner-drift':
        values['owner']['independent_grant_authority']['authority_service_uid'] += 1
    else:
        changes = {'epoch':{'requester_key_epoch':'changed'}, 'issuer-principal':{'requester_principal_id':'attacker'},
            'descriptor':{'descriptor_id':_sha('other')}, 'owner':{'owner_config_id':_sha('other')},
            'policy':{'policy':dict(request.policy, rate_limit_max_requests=999)},
            'expired-request':{'issued_at':int(time.time())-60}}[mutation]
        request = _sign_request(values, replace(request, **changes))
    assert not _dispatch(values, request, peer).accepted


@pytest.mark.parametrize('state', ['absent','revoked','expired'])
def test_revocation_is_checked_without_recursive_load(tmp_path, monkeypatch, state):
    values = _runtime(tmp_path, monkeypatch, install=state!='absent', revoked=state=='revoked', expired=state=='expired')
    assert not _dispatch(values, _issuer_request(values)).accepted


@pytest.mark.parametrize('mutation', ['advance','other-role','v1-label','v2-target','missing-epoch'])
def test_wire_role_version_confusion_rejects_before_dispatch(tmp_path, monkeypatch, mutation):
    values = _runtime(tmp_path, monkeypatch)
    payload = json.loads(_issuer_request(values).to_bytes())
    if mutation == 'advance':
        payload.update(operation=wire.OP_ADVANCE, snapshot_id=_sha('candidate'))
    elif mutation == 'other-role':
        payload['requester_role'] = 'architect'
    elif mutation == 'v1-label':
        payload['schema_version'] = wire.SCHEMA_VERSION
    elif mutation == 'v2-target':
        payload['requester_role'] = wire.TARGET_ROLE
    else:
        del payload['requester_key_epoch']
    with pytest.raises(ValueError):
        wire.request_from_bytes(json.dumps(payload).encode())


def _issuer_client(values, monkeypatch):
    from modules.communication.moltbot_bridge.src import foundup_verified_outcome_root_authority_client as transport
    monkeypatch.setattr(transport, '_root_socket_roundtrip', lambda _path, raw, _uid, _timeout:
        handle_root_authority_wire_request(raw, peer=_grant_peer(), state=values['state'],
            snapshot_supplier=lambda: values['snapshot'], revocation_authority=values['server_authority'],
            now_epoch=int(time.time())))
    target = client._lookup_client(values['client'])
    return client._create_root_revocation_anchor_authority(values['snapshot'].descriptor,
        owner_config_id=target.owner_config_id, policy=values['policy'], binding=values['binding'],
        exchange=target.exchange, request_signer=lambda text:_sign(values['grant_private'],text),
        now_epoch=int(time.time()), requester_role=wire.GRANT_ROLE)


def test_issuer_client_and_oracle_cannot_advance_or_authorize_target_use(tmp_path, monkeypatch):
    values = _runtime(tmp_path, monkeypatch)
    anchor = _issuer_client(values, monkeypatch)
    assert anchor.load().sequence == 1
    with pytest.raises(ValueError, match='load_only'):
        anchor.advance_snapshot(_sha('other'))
    now = int(time.time())  # Bind the claimed epoch and injected clock to one fixture instant.
    resolver = SimpleNamespace(resolve=lambda principal, provider: values['policy']['revocation_authority_public_key'])
    durable = UncomposedDurableSignerGrantRevocationOracle(binding=values['binding'], policy=values['policy'],
        reader=values['store'].reader(), witness=values['witness'].reader(), anchor=anchor,
        principal_key_resolver=resolver, signature_verifier=Ed25519SignatureVerifier(), clock=lambda:now)
    oracle = build_grant_issuer_revocation_oracle(durable=durable, policy=values['policy'], binding=values['binding'])
    assert oracle.matches_owner(policy=values['policy'], binding=values['binding'])
    assert oracle.authorize_key_epoch_use(key_epoch=values['policy']['grant_authority_key_epoch'],
        at_epoch=now, expires_at=now+20, action=lambda:'checked') == 'checked'
    assert oracle.authorize_current_key_epoch_use(key_epoch=values['policy']['grant_authority_key_epoch'],
        expires_at=now+20, action=lambda:'current') == 'current'
    with pytest.raises(ValueError, match='cannot_authorize_target_grant'):
        oracle.authorize_grant_use({}, lambda:pytest.fail('no target effect'))
    with pytest.raises(ValueError, match='epoch_invalid'):
        oracle.authorize_key_epoch_use(key_epoch='target-epoch', at_epoch=now,
            expires_at=now+20, action=lambda:pytest.fail('no foreign epoch use'))
    with pytest.raises(ValueError, match='epoch_invalid'):
        oracle.authorize_current_key_epoch_use(key_epoch='target-epoch',
            expires_at=now+20, action=lambda:pytest.fail('no foreign current epoch use'))
    durable.anchor = values['client']
    with pytest.raises(ValueError, match='epoch_invalid'):
        oracle.authorize_current_key_epoch_use(key_epoch=values['policy']['grant_authority_key_epoch'],
            expires_at=now+20, action=lambda:pytest.fail('no changed owner use'))
    with pytest.raises(ValueError, match='owner_mismatch'):
        build_grant_issuer_revocation_oracle(durable=durable, policy=values['policy'], binding=values['binding'])


def test_kernel_attestor_policy_separates_transport_roles():
    import struct
    dependencies = SimpleNamespace(signer_uid=1001, signer_gid=1001,
        signer_principal_id='target', grant_peer_identity=(1002,1001))
    policy = _peer_policy(dependencies)
    class SocketFixture:
        def getsockopt(self, *args):
            return struct.pack('3i', 42, 1002, 1001)
    import modules.communication.moltbot_bridge.src.reddog_signer_socket_peer_credential_attestor as peers
    original = peers._SO_PEERCRED
    peers._SO_PEERCRED = 17
    try:
        identity = KernelPeerCredentialAttestor(policy).attest_identity(SocketFixture())
    finally:
        peers._SO_PEERCRED = original
    assert identity.uid == 1002 and identity.attestation.peer_principal_id == wire.GRANT_PEER_PRINCIPAL
    dependencies.grant_peer_identity = (1001,1001)
    with pytest.raises(ValueError):
        _peer_policy(dependencies)


def test_legacy_v1_golden_bytes_and_signing_domain_unchanged():
    """Golden values captured from unmodified 3d81fee277, not candidate output."""
    import hashlib
    payload = dict(operation=wire.OP_LOAD, request_id='sha256:'+'0'*64, request_nonce='a'*64,
        descriptor_id='sha256:'+'1'*64, owner_config_id='sha256:'+'2'*64, policy_id='sha256:'+'3'*64,
        binding_digest='sha256:'+'4'*64, policy={'fixture':'legacy'}, snapshot_id=None,
        issued_at=1700000000, signer_instance_signature='ed25519-sig-v1:'+'A'*86)
    payload['request_id'] = wire.request_id_for(payload)
    request = wire.RootRevocationRequest(**payload)
    assert request.request_id == 'sha256:69e0890eaec5d5bc2b8dfabe90d3ef054fccccc38267cab23f0efaf168c44ccf'
    assert hashlib.sha256(request.to_bytes()).hexdigest() == 'e219f14334cd2ba51c74794918ffc6d3f95c2a1b213681ae64494b61d695f392'
    assert hashlib.sha256(wire.canonical_signer_input(request).encode()).hexdigest() == '8940c921b2d4362fd65c95da47e27485ce0f0d7998e2b6fd73f69bd09aa60c38'
    assert wire.request_from_bytes(request.to_bytes()).to_bytes() == request.to_bytes()


def test_issuer_client_needs_live_identity_not_unrelated_outcome_grant(tmp_path, monkeypatch):
    from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_authority import descriptor_id_for
    values = _runtime(tmp_path, monkeypatch)
    target = client._lookup_client(values['client'])
    descriptor = copy.deepcopy(values['snapshot'].descriptor)
    descriptor['grants'][0]['expires_at'] = int(time.time())-1
    descriptor['descriptor_id'] = descriptor_id_for(descriptor)
    kwargs = dict(owner_config_id=target.owner_config_id, policy=values['policy'],
        binding=values['binding'], exchange=target.exchange, now_epoch=int(time.time()),
        request_signer=lambda text:_sign(values['grant_private'],text))
    issuer = client._create_root_revocation_anchor_authority(descriptor, **kwargs, requester_role=wire.GRANT_ROLE)
    assert client._lookup_client(issuer).requester_role == wire.GRANT_ROLE
    with pytest.raises(ValueError):
        client._create_root_revocation_anchor_authority(descriptor, **kwargs)


@pytest.mark.parametrize('field', ['signer_key_epoch','signer_manifest_id',
    'signer_config_digest','signer_artifact_generation_digest'])
def test_protected_descriptor_must_match_current_e0(tmp_path, monkeypatch, field):
    from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_authority import descriptor_id_for
    values = _runtime(tmp_path, monkeypatch)
    descriptor = copy.deepcopy(values['snapshot'].descriptor)
    descriptor[field] = 'other-epoch' if field=='signer_key_epoch' else _sha('other-runtime')
    descriptor['descriptor_id'] = descriptor_id_for(descriptor)
    values['snapshot'] = replace(values['snapshot'], descriptor=descriptor)
    values['owner']['verified_outcome_authority']['descriptor'] = descriptor
    assert not _dispatch(values, _issuer_request(values)).accepted
