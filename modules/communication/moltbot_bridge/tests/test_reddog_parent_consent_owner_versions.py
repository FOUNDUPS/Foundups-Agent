"""Actual owner schema validation; protected file reads are test-only seams."""

from pathlib import Path
import pytest

from modules.communication.moltbot_bridge.src import reddog_signer_system_service_manifest_selection_loader as loader
from modules.communication.moltbot_bridge.src.reddog_grant_authority_startup_custody import RATE_PURPOSE
from modules.communication.moltbot_bridge.tests import test_reddog_grant_custody_owner_versions as legacy
from modules.communication.moltbot_bridge.tests.grant_rate_store_test_support import rate_metadata, separate_grant_socket
from modules.communication.moltbot_bridge.tests.reddog_parent_consent_test_support import setup


def owner_fixture(monkeypatch, tmp_path):
    # Isolate the consent fixture patches; this test exercises the actual owner loader.
    with monkeypatch.context() as local:
        materials = tmp_path / "materials"
        materials.mkdir()
        _, consent = setup(local, materials)
        authority = dict(consent.authority)
    values, owner, _ = legacy._owner(tmp_path, monkeypatch)
    owner.update(schema_version=loader.SCHEMA_VERSION_V11,
                 grant_rate_store=rate_metadata(tmp_path), parent_consent_authority=authority)
    separate_grant_socket(owner, tmp_path)
    owner['grant_startup_custody']['replay_integrity_permission']['purpose'] = RATE_PURPOSE
    legacy._write(values, owner)
    return values, owner


def test_parent_v11_preserves_v10_socket_and_rate_shape(monkeypatch, tmp_path):
    values, owner = owner_fixture(monkeypatch, tmp_path)
    assert loader.V11_FIELDS == loader.V10_FIELDS | {"parent_consent_authority"}
    assert loader._load_owner_config(values['owner_config_path'], repo=values['repo']) == owner
    owner.pop('parent_consent_authority')
    owner['schema_version'] = loader.SCHEMA_VERSION_V10
    legacy._write(values, owner)
    assert loader._load_owner_config(values['owner_config_path'], repo=values['repo']) == owner


@pytest.mark.parametrize('case', ['missing', 'extra', 'duplicate', 'config_digest', 'privilege',
    'effect_privilege', 'rate_purpose', 'old_socket', 'reviewer', 'model', 'custody'])
def test_parent_v11_inherits_fail_closed_owner_validation(monkeypatch, tmp_path, case):
    values, owner = owner_fixture(monkeypatch, tmp_path)
    if case == 'missing': owner.pop('parent_consent_authority')
    elif case == 'extra': owner['parent_granted'] = True
    elif case == 'privilege': owner['parent_consent_authority']['privilege'] = 'authorize_exact_high_worktree_effect'
    elif case == 'effect_privilege': owner['effect_consent_authority']['privilege'] = 'authorize_exact_high_delegated_request'
    elif case == 'rate_purpose': owner['grant_rate_store']['purpose'] = 'signer-grant-replay.v1'
    elif case == 'old_socket': owner['independent_grant_authority']['authority_socket_path'] = str(Path(owner['independent_grant_authority']['authority_root']) / 'grant-authority.sock')
    elif case == 'reviewer': owner['reviewer_designation_authority']['privilege'] = 'authorize_exact_high_delegated_request'
    elif case == 'model': owner['model_verifier_authority']['expires_at'] = True
    elif case == 'custody': owner['grant_startup_custody']['replay_integrity_permission']['purpose'] = 'signer-grant-replay.v1'
    legacy._write(values, owner)
    if case == 'config_digest': values['raw'][0] = values['raw'][0].replace(owner['config_id'].encode(), b'sha256:' + b'0' * 64)
    if case == 'duplicate': values['raw'][0] = values['raw'][0][:-1] + b',"parent_consent_authority":null}'
    with pytest.raises(ValueError):
        loader._load_owner_config(values['owner_config_path'], repo=values['repo'])


def test_parent_v11_existing_startup_and_policy_edges_remain_inert(monkeypatch, tmp_path):
    from modules.communication.moltbot_bridge.src import reddog_grant_authority_service_owner_binding as binding
    from modules.communication.moltbot_bridge.src import reddog_grant_authority_source_policy_authority as source
    values, owner = owner_fixture(monkeypatch, tmp_path)
    selected, boundary = object(), object()
    monkeypatch.setattr(loader, '_manifest_selection_from_owner', lambda *a, **kw: (selected, boundary))
    def forbidden(*args, **kwargs):
        raise AssertionError('construction must not resolve or issue authority')
    monkeypatch.setattr(loader, '_verified_outcome_authority_from_owner', forbidden)
    startup = loader.load_system_service_startup_selection(owner_config_path=values['owner_config_path'],
                                                         repo_root=values['repo'])
    assert startup.manifest_selection is selected and startup.manifest_selection_boundary is boundary
    assert callable(startup.runtime_dependencies_supplier)
    assert binding.grant_authority_owner_runtime_root(values['owner_config_path'], values['repo'],
        owner['config_id']) == Path(owner['independent_grant_authority']['authority_root']).resolve()
    token, current = source.load_grant_authority_source_policy_authority(
        owner_config_path=values['owner_config_path'], repo_root=values['repo'])
    assert current.revalidate(token)['owner_config_id'] == owner['config_id']
    owner['parent_consent_authority']['issuer_key_epoch'] = 'rotated'
    legacy._write(values, owner)
    with pytest.raises(ValueError):
        current.revalidate(token)
