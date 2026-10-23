"""Installed HIGH composition; disposable crypto, explicit OS/admission seams."""
from types import SimpleNamespace

from .installed_work_admission_test_support import setup_installed_work
from modules.communication.moltbot_bridge.src import reddog_grant_authority_service as service
from modules.communication.moltbot_bridge.src import reddog_grant_authority_service_manifest_verifier as manifests
from modules.communication.moltbot_bridge.src import reddog_grant_authority_installed_runtime_guard as guard


def test_v11_real_signed_manifest_reaches_full_runtime_guard(tmp_path, monkeypatch):
    state = setup_installed_work(tmp_path, monkeypatch)
    policy = state['e0']['policy']
    seen = []
    monkeypatch.setattr(guard, 'verify_installed_grant_runtime', lambda descriptor: seen.append(descriptor))
    service._verify_installed_runtime(state['harness'].repo_root,
        tmp_path / 'owner' / 'owner.json', policy)
    assert len(seen) == 1
    assert seen[0]['source_commit_sha'] == policy['grant_authority_source_commit_sha']


def test_v11_exact_policy_scope_is_selected_without_changing_low(tmp_path, monkeypatch):
    state = setup_installed_work(tmp_path, monkeypatch)
    assert service._service_policy_scope(state['e0']['policy']) == 'HIGH'
    assert service._policy_scope(dict(allowed_operations=[service.LOW_OPERATION],
        allowed_authority_tiers=['LOW'], consensus_required_tiers=[])) is None
import pytest
from copy import deepcopy
from contextlib import contextmanager
from modules.communication.moltbot_bridge.src import reddog_grant_authority_runtime_dependencies as runtime


@pytest.mark.parametrize('field,value', [('generation', 1), ('generation', True),
    ('allowed_operations', ['signer_socket_peer_handshake']), ('allowed_authority_tiers', ['LOW']),
    ('consensus_required_tiers', []), ('grant_authority_installed_runtime_descriptor_digest', 'unbound')])
def test_v11_scope_never_downgrades_or_accepts_unbound_inputs(tmp_path, monkeypatch, field, value):
    state = setup_installed_work(tmp_path, monkeypatch)
    policy = dict(state['e0']['policy'], **{field: value})
    with pytest.raises(ValueError):
        service._service_policy_scope(policy)


@pytest.mark.parametrize('stage', ['guard', 'models'])
def test_high_startup_rejects_before_any_custody(tmp_path, monkeypatch, stage):
    state = setup_installed_work(tmp_path, monkeypatch)
    policy = state['e0']['policy']
    owner = dict(state['owner'], schema_version=runtime.SCHEMA_VERSION_V13,
        startup_custody={'policy_path': str(tmp_path / 'policy')})
    calls = []
    monkeypatch.setattr(runtime, '_load_owner_config', lambda *a, **k: deepcopy(owner))
    from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_authority_wire_codec import canonical_bytes
    monkeypatch.setattr(runtime, '_read_root_owned_bytes', lambda *a: canonical_bytes(policy))
    monkeypatch.setattr(runtime, '_isolate', lambda *a: calls.append('isolate'))
    @contextmanager
    def admission(**kwargs):
        yield SimpleNamespace(policy=policy)
    monkeypatch.setattr(runtime, 'lease_validated_owner_e0_current_admission', admission)
    monkeypatch.setattr(runtime, '_current_owner', lambda *a: (None, None, None, None))
    def checked(*args):
        calls.append('guard')
        service._verify_installed_runtime(*args)
    monkeypatch.setattr(runtime, '_verify_installed_runtime', checked)
    def full_guard(descriptor):
        if stage == 'guard':
            raise ValueError('synthetic_runtime_guard_rejected')
    monkeypatch.setattr(guard, 'verify_installed_grant_runtime', full_guard)
    def missing(*args):
        calls.append('models')
        raise ValueError('synthetic_missing_models')
    monkeypatch.setattr(runtime, '_high_models', missing)
    monkeypatch.setattr(runtime, 'SystemdCredentialSecretResolver', lambda *a: pytest.fail('custody reached'))
    with pytest.raises(ValueError):
        runtime.materialize_grant_authority_runtime_dependencies(owner_config_path=tmp_path / 'owner' / 'owner.json',
            repo_root=state['harness'].repo_root, expected_owner_config_id=policy['owner_config_id'])
    assert calls == (['isolate', 'guard'] if stage == 'guard' else ['isolate', 'guard', 'models'])


def test_nonce_materialization_requires_separate_unheld_lease(monkeypatch, tmp_path):
    from .reddog_live_lease_composition_support import setup, scope
    state = setup(monkeypatch, tmp_path)
    path = state.call['owner_config_path']
    assert runtime._consensus_custody('LOW', path, state.repo, state.owner['config_id']) is None
    loaded = runtime._consensus_custody('HIGH', path, state.repo, state.owner['config_id'])
    assert type(loaded) is type(state.nonces) and not state.lease.active
    with scope(state):
        with pytest.raises(AssertionError, match='nested_generation_acquisition'):
            runtime._consensus_custody('HIGH', path, state.repo, state.owner['config_id'])
