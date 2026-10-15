"""Separate issuer rate state with explicit synthetic authority/OS fixture seams."""
import copy
import os
import time
from pathlib import Path
from dataclasses import replace
from types import SimpleNamespace

import pytest
from modules.communication.moltbot_bridge.src import (
    reddog_grant_authority_service as service,
    reddog_grant_authority_startup_custody as custody,
    reddog_signer_secret_grant_durable_rate_authority as rate,
    reddog_signer_secret_grant_authority_policy as authority,
    reddog_signer_secret_grant_signer_admission as admission,
    reddog_signer_system_service_manifest_selection_loader as loader,
)
from modules.communication.moltbot_bridge.tests import test_reddog_grant_authority_service as legacy
from modules.communication.moltbot_bridge.tests import test_reddog_grant_custody_owner_versions as versions
from modules.communication.moltbot_bridge.tests.grant_rate_store_test_support import (
    rate_metadata, upgrade_case, separate_grant_socket,
)

case = legacy.case


def test_v10_real_signing_keeps_target_binding_and_separate_rate(case, tmp_path, monkeypatch):
    upgrade_case(case, tmp_path, monkeypatch)
    _, policy = service._current_inputs(case.repo, case.owner_path, case.deps)
    assert policy.replay_store_instance_digest == case.target_store.replay_store_instance_digest
    assert policy.replay_store_instance_digest != case.deps.replay_store.replay_store_instance_digest
    assert authority.secret_grant_policy_rejected(policy) is False
    backend = legacy._backend(case)
    for nonce in ('rate-one', 'rate-two'):
        response = backend.sign(legacy._request(case, nonce), legacy.fixture._peer())
        assert response.accepted, response.rejection_code
    response = backend.sign(legacy._request(case, 'rate-three'), legacy.fixture._peer())
    assert response.accepted is False
    assert case.target_store.consume_scoped_nonce(nonce='target-only', expires_at=int(time.time())+30, subject='grant')
    assert not case.target_store.consume_scoped_nonce(nonce='target-only', expires_at=int(time.time())+30, subject='grant')


@pytest.mark.parametrize('mutation', ['rate_id', 'rate_role', 'custody_expired', 'owner_drift'])
def test_v10_changed_custody_rejects_before_factory_resolution(case, tmp_path, monkeypatch, mutation):
    upgrade_case(case, tmp_path, monkeypatch)
    request = legacy._request(case)
    if mutation == 'rate_id': case.owner['grant_rate_store']['replay_store_id'] = 'foreign-store'
    elif mutation == 'rate_role': case.owner['grant_rate_store']['purpose'] = custody.REPLAY_PURPOSE
    elif mutation == 'custody_expired': case.owner['grant_startup_custody']['replay_integrity_permission']['expires_at'] = 1
    elif mutation == 'owner_drift': case.owner['config_id'] = 'sha256:'+'f'*64
    response = legacy._backend(case).sign(request, legacy.fixture._peer())
    assert response.accepted is False
    assert 'resolve' not in case.events and 'new-custody' not in case.events


@pytest.mark.parametrize('mutation', ['dict','object','copy','replace','wrong_policy','wrong_store',
    'owner_id','policy_expiry','custody_expiry','rate_path','rate_role','target_root'])
def test_separate_rate_binding_rejects_forgery_and_current_drift(case, tmp_path, monkeypatch, mutation):
    upgrade_case(case, tmp_path, monkeypatch)
    _, policy = service._current_inputs(case.repo, case.owner_path, case.deps)
    cap = policy.issuer_rate_binding
    if mutation == 'dict': policy = replace(policy, issuer_rate_binding={})
    elif mutation == 'object': policy = replace(policy, issuer_rate_binding=object())
    elif mutation == 'copy': policy = replace(policy, issuer_rate_binding=copy.copy(cap))
    elif mutation == 'replace': policy = replace(policy, issuer_rate_binding=replace(cap))
    elif mutation == 'wrong_policy': policy = replace(policy, signer_generation_id='sha256:'+'f'*64)
    elif mutation == 'wrong_store':
        backend = SimpleNamespace(secret_grant_rate_authority=rate.DurableSignerSecretGrantRateAuthority(case.target_store))
        assert admission._rate_rejection(backend, policy, int(time.time()))
        return
    elif mutation == 'owner_id': case.owner['config_id'] = 'sha256:'+'f'*64
    elif mutation == 'policy_expiry': case.deps.owner_policy['expires_at'] = int(time.time())-1
    elif mutation == 'custody_expiry': case.owner['grant_startup_custody']['replay_integrity_permission']['expires_at'] = 1
    elif mutation == 'rate_path': case.owner['grant_rate_store']['nonce_path'] += '.changed'
    elif mutation == 'rate_role': case.owner['grant_rate_store']['purpose'] = 'signer-grant-replay.v1'
    elif mutation == 'target_root': case.deps.owner_policy['replay_root'] = case.owner['grant_rate_store']['nonce_root']
    assert authority.secret_grant_policy_rejected(policy) is True
    assert case.events == []


def test_v10_exact_schema_and_inherited_owner_validation(tmp_path, monkeypatch):
    values, owner, _ = versions._owner(tmp_path, monkeypatch)
    owner.update(schema_version=loader.SCHEMA_VERSION_V10, grant_rate_store=rate_metadata(tmp_path))
    separate_grant_socket(owner, tmp_path)
    owner['grant_startup_custody']['replay_integrity_permission']['purpose'] = custody.RATE_PURPOSE
    versions._write(values, owner)
    assert loader.V10_FIELDS == loader.V9_FIELDS | {'grant_rate_store'}
    assert loader._load_owner_config(values['owner_config_path'], repo=values['repo']) == owner


@pytest.mark.parametrize('mutation', ['missing','extra','purpose','permission_purpose','repo','owner',
    'runtime','high_water','witness','target_water','self_overlap','escape','downgrade','bad_digest'])
def test_v10_metadata_rejects_before_credentials(tmp_path, monkeypatch, mutation):
    values, owner, _ = versions._owner(tmp_path, monkeypatch)
    owner.update(schema_version=loader.SCHEMA_VERSION_V10, grant_rate_store=rate_metadata(tmp_path))
    separate_grant_socket(owner, tmp_path)
    owner['grant_startup_custody']['replay_integrity_permission']['purpose'] = custody.RATE_PURPOSE
    raw = owner['grant_rate_store']
    if mutation == 'missing': raw.pop('nonce_path')
    elif mutation == 'extra': raw['caller_approved'] = True
    elif mutation == 'purpose': raw['purpose'] = custody.REPLAY_PURPOSE
    elif mutation == 'permission_purpose': owner['grant_startup_custody']['replay_integrity_permission']['purpose'] = custody.REPLAY_PURPOSE
    elif mutation == 'repo': raw['nonce_root'] = str(values['repo'])
    elif mutation == 'owner': raw['nonce_root'] = str(values['owner_config_path'].parent)
    elif mutation == 'runtime': raw['nonce_root'] = owner['runtime_root']
    elif mutation == 'high_water': raw['nonce_root'] = owner['high_water_root']
    elif mutation == 'witness': raw['nonce_root'] = owner['witness_root']
    elif mutation == 'target_water': raw['nonce_root'] = owner['startup_custody']['replay_store']['high_water_root']
    elif mutation == 'self_overlap': raw['high_water_root'] = raw['nonce_root']
    elif mutation == 'escape': raw['nonce_path'] = str(tmp_path/'escape.json')
    elif mutation == 'downgrade': owner['schema_version'] = loader.SCHEMA_VERSION_V9
    elif mutation == 'bad_digest': raw['durability_receipt_id'] = 'bad'
    versions._write(values, owner)
    with pytest.raises(ValueError): loader._load_owner_config(values['owner_config_path'], repo=values['repo'])


def _runtime_case(tmp_path, monkeypatch):
    from modules.communication.moltbot_bridge.tests import grant_startup_custody_fixture as fixtures
    from modules.communication.moltbot_bridge.tests.grant_rate_store_test_support import provision
    from modules.communication.moltbot_bridge.src import reddog_grant_authority_runtime_dependencies as runtime
    value = fixtures.build_case(tmp_path, monkeypatch)
    uid, gid = (os.geteuid(), os.getegid()) if os.name == 'posix' else (997, 997)
    target_uid = 1002 if uid == 1001 else 1001
    value.owner['verified_outcome_authority']['signer_uid'] = target_uid
    value.values['snapshot'] = replace(value.values['snapshot'], signer_uid=target_uid)
    value.owner['independent_grant_authority'].update(authority_service_uid=uid, authority_service_gid=gid)
    original_peer = fixtures.root_fixture._grant_peer
    monkeypatch.setattr(fixtures.root_fixture, '_grant_peer',
                        lambda: replace(original_peer(), uid=uid, gid=gid))
    value.owner.update(schema_version=loader.SCHEMA_VERSION_V10, grant_rate_store=rate_metadata(tmp_path))
    separate_grant_socket(value.owner, tmp_path)
    for field in ('credential_binding', 'loader_credential_binding'):
        value.owner['grant_startup_custody'][field].update(expected_uid=uid, expected_gid=gid)
    value.owner['grant_startup_custody']['replay_integrity_permission']['purpose'] = custody.RATE_PURPOSE
    provision(custody.grant_rate_store_config(value.owner, value.values['repo']))
    def forbidden(*a, **kw): raise AssertionError('issuer opened target private replay store')
    monkeypatch.setattr(runtime, '_materialize_startup_replay', forbidden)
    if os.name != 'posix': monkeypatch.setattr(runtime, 'require_private_grant_rate_store', lambda *a: None)
    return value, fixtures


def test_v10_runtime_materializes_only_issuer_store(tmp_path, monkeypatch):
    value, fixtures = _runtime_case(tmp_path, monkeypatch)
    result = fixtures.materialize(value)
    assert result.replay_store._config == custody.grant_rate_store_config(value.owner, value.values['repo'])
    assert result.replay_store._config.nonce_path != value.replay_config.nonce_path
    assert value.events.count('replay') == 1


@pytest.mark.parametrize('mutation', ['target_root','target_id','target_receipt','target_digest','missing'])
def test_v10_runtime_store_rejection_precedes_integrity_and_signing_keys(tmp_path, monkeypatch, mutation):
    value, fixtures = _runtime_case(tmp_path, monkeypatch)
    raw, policy = value.owner['grant_rate_store'], value.values['policy']
    if mutation == 'target_root': raw['nonce_root'] = policy['replay_root']
    elif mutation == 'target_id': raw['replay_store_id'] = policy['replay_store_id']
    elif mutation == 'target_receipt': raw['durability_receipt_id'] = policy['replay_store_durability_receipt_id']
    elif mutation == 'target_digest': raw['replay_store_binding_digest'] = value.owner['startup_custody']['replay_store']['replay_store_binding_digest']
    elif mutation == 'missing':
        from pathlib import Path
        Path(raw['nonce_path']).unlink()
    with pytest.raises((ValueError, FileNotFoundError)): fixtures.materialize(value)
    assert value.events == ['isolate']


def _socket_owner(tmp_path, schema=loader.SCHEMA_VERSION_V10):
    from modules.communication.moltbot_bridge.tests import test_reddog_signer_independent_grant_authority_client_supply as transport
    owner = transport._owner(tmp_path, config_id='sha256:'+'1'*64, schema_version=schema)
    owner.update(anchor_path=str(tmp_path/'anchor/generation-anchor.json'),
                 grant_rate_store=rate_metadata(tmp_path), startup_custody={
                     'replay_store': {'high_water_root': str(tmp_path/'target-replay-water')}})
    if schema == loader.SCHEMA_VERSION_V10:
        separate_grant_socket(owner, tmp_path)
    return owner


@pytest.mark.parametrize('version', range(3, 11))
def test_socket_layout_version_boundary(tmp_path, version):
    from modules.communication.moltbot_bridge.src import reddog_signer_independent_grant_authority_client_supply as supply
    owner = _socket_owner(tmp_path, getattr(loader, f'SCHEMA_VERSION_V{version}'))
    supply.validate_independent_grant_authority_owner_config(
        owner, repo=tmp_path/'repo', owner_root=tmp_path/'owner')
    raw = owner['independent_grant_authority']
    if version == 10:
        raw['authority_socket_path'] = str(Path(raw['authority_root'])/'grant-authority.sock')
    else:
        separate_grant_socket(owner, tmp_path)
    with pytest.raises(ValueError):
        supply.validate_independent_grant_authority_owner_config(
            owner, repo=tmp_path/'repo', owner_root=tmp_path/'owner')


@pytest.mark.parametrize('domain', ['owner','runtime_root','high_water_root','witness_root',
    'state_root','state_witness_root','installation_root','anchor','root_socket',
    'nonce_root','rate_water','target_water','artifact_child','artifact_parent','repo','missing',
    'relative','traversal','wrong_filename'])
def test_v10_socket_rejects_domain_escape(tmp_path, domain):
    from modules.communication.moltbot_bridge.src import reddog_signer_independent_grant_authority_client_supply as supply
    owner = _socket_owner(tmp_path)
    raw = owner['independent_grant_authority']
    roots = {name: Path(owner[name]) for name in ('runtime_root','high_water_root','witness_root')}
    roots.update({name: Path(owner['verified_outcome_authority'][name])
                  for name in ('state_root','state_witness_root','installation_root')})
    roots.update(owner=tmp_path/'owner', anchor=tmp_path/'anchor', root_socket=tmp_path/'root-socket',
        nonce_root=tmp_path/'rate', rate_water=tmp_path/'rate-water', target_water=tmp_path/'target-replay-water',
        artifact_child=Path(raw['authority_root'])/'child', artifact_parent=tmp_path, repo=tmp_path/'repo',
        missing=tmp_path/'absent', relative=tmp_path/'grant-socket', traversal=tmp_path/'grant-socket',
        wrong_filename=tmp_path/'grant-socket')
    root = roots[domain]
    if domain != 'missing': root.mkdir(parents=True, exist_ok=True)
    path = str(root/'grant-authority.sock')
    if domain == 'relative': path = 'grant-authority.sock'
    elif domain == 'traversal': path = str(root/'..'/'grant-socket'/'grant-authority.sock')
    elif domain == 'wrong_filename': path = str(root/'other.sock')
    raw['authority_socket_path'] = path
    with pytest.raises(ValueError):
        supply.validate_independent_grant_authority_owner_config(
            owner, repo=tmp_path/'repo', owner_root=tmp_path/'owner')


@pytest.mark.parametrize('overlap', [None,'replay_root','revocation_root','revocation_witness_root'])
def test_v10_authenticated_builder_uses_socket_parent_keeps_artifact_binding(tmp_path, monkeypatch, overlap):
    from modules.communication.moltbot_bridge.src import reddog_signer_independent_grant_authority_client_supply as supply
    from modules.communication.moltbot_bridge.tests import test_reddog_signer_independent_grant_authority_client_supply as transport
    owner = _socket_owner(tmp_path)
    policy = transport._policy_value(tmp_path/'policy', owner_config_id=owner['config_id'],
                                    grant_public=transport._public(transport.Ed25519PrivateKey.generate()))
    socket_root = Path(owner['independent_grant_authority']['authority_socket_path']).parent
    observed = []
    def build(**kwargs):
        observed.append(kwargs)
        return SimpleNamespace(accepted=True, client=object())
    monkeypatch.setattr(supply, 'build_reddog_isolated_signer_socket_client', build)
    if overlap is not None: policy[overlap] = str(socket_root)
    def run():
        return supply._build_authenticated_supply(owner=owner, policy=policy,
            owner_config_path=tmp_path/'owner/owner.json', repo=tmp_path/'repo',
            required_schemas={loader.SCHEMA_VERSION_V10})
    if overlap is not None:
        with pytest.raises(ValueError): run()
        assert observed == []
    else:
        result = run()
        assert observed[0]['trusted_socket_root'] == socket_root
        assert result.binding.authority_root == owner['independent_grant_authority']['authority_root']
        assert result.authority_root == result.binding.authority_root


@pytest.mark.skipif(os.name != 'posix', reason='native symlink creation needs Linux fixture')
def test_v10_socket_symlink_ancestor_rejected(tmp_path):
    from modules.communication.moltbot_bridge.src import reddog_signer_independent_grant_authority_client_supply as supply
    owner = _socket_owner(tmp_path)
    link = tmp_path/'alias'
    link.symlink_to(tmp_path/'grant-socket', target_is_directory=True)
    owner['independent_grant_authority']['authority_socket_path'] = str(link/'grant-authority.sock')
    with pytest.raises(ValueError, match='link_rejected'):
        supply.validate_independent_grant_authority_owner_config(
            owner, repo=tmp_path/'repo', owner_root=tmp_path/'owner')
