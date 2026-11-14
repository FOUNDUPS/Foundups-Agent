"""Actual v13 schema and domain validation; root-file read provenance is synthetic."""
from copy import deepcopy
import pytest
from .consensus_nonce_test_support import owner_case, current, custody, legacy


def test_v13_owner_extends_v12_without_changing_old_shape(monkeypatch, tmp_path):
    values, owner, _, _ = owner_case(monkeypatch, tmp_path)
    assert current.loader.V13_FIELDS == current.loader.V12_FIELDS | {'consensus_nonce_authority'}
    assert current.loader._load_owner_config(values['owner_config_path'], repo=values['repo']) == owner
    owner.pop('consensus_nonce_authority')
    owner['schema_version'] = current.loader.SCHEMA_VERSION_V12
    legacy._write(values, owner)
    assert current.loader._load_owner_config(values['owner_config_path'], repo=values['repo']) == owner


@pytest.mark.parametrize('fault', ['missing', 'extra', 'purpose', 'permission', 'identity', 'credential',
    'directory', 'root', 'store_id', 'binding', 'durability', 'boolean', 'duplicate'])
def test_v13_rejects_malformed_or_borrowed_authority(monkeypatch, tmp_path, fault):
    values, owner, _, _ = owner_case(monkeypatch, tmp_path)
    value = owner['consensus_nonce_authority']
    if fault == 'missing': owner.pop('consensus_nonce_authority')
    elif fault == 'extra': value['admitted'] = True
    elif fault == 'purpose': value['store']['purpose'] = 'grant-issuer-rate.v1'
    elif fault == 'permission': value['integrity_permission']['purpose'] = 'grant-issuer-rate-integrity.v1'
    elif fault == 'identity': value['credential_binding']['expected_requester'] += '-other'
    elif fault == 'credential':
        value['credential_binding']['credential_ids'] = ['replay']
        value['integrity_permission']['reference'] = 'systemd-creds://replay'
    elif fault == 'directory': value['credential_binding']['credential_directory'] = '/run/credentials/other.service'
    elif fault == 'root':
        value['store']['nonce_root'] = owner['grant_rate_store']['nonce_root']
        value['store']['nonce_path'] = owner['grant_rate_store']['nonce_path']
    elif fault in ('store_id', 'binding', 'durability'):
        key = dict(store_id='replay_store_id', binding='replay_store_binding_digest', durability='durability_receipt_id')[fault]
        value['store'][key] = owner['grant_rate_store'][key]
    elif fault == 'boolean': value['integrity_permission']['expires_at'] = True
    legacy._write(values, owner)
    if fault == 'duplicate': values['raw'][0] = values['raw'][0][:-1] + b',"consensus_nonce_authority":null}'
    with pytest.raises(ValueError): current.loader._load_owner_config(values['owner_config_path'], repo=values['repo'])


def test_v13_model_loader_preserves_distinct_signed_inputs(monkeypatch, tmp_path):
    from .test_reddog_parent_model_inputs import check
    values, owner, records, now = owner_case(monkeypatch, tmp_path)
    author, resolver = check(values, owner, records, now)
    assert author is not None and resolver is not None
