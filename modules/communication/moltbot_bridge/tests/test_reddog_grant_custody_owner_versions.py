"""Owner v9 retains v8 model-verifier checks and exact issuer custody shape."""
import copy
import json
import time
from pathlib import Path

import pytest

from modules.communication.moltbot_bridge.src import reddog_signer_system_service_manifest_selection_loader as loader
from modules.communication.moltbot_bridge.tests.grant_startup_custody_fixture import custody_metadata
from modules.communication.moltbot_bridge.tests.test_reddog_effect_consent_startup_owner import startup_owner_fixture
from modules.communication.moltbot_bridge.tests import test_reddog_effect_consent_owner_versions as legacy
from modules.communication.moltbot_bridge.tests.model_runtime_binding_receipt_test_helpers import (
    model_selection_and_runtime_binding_receipts, model_runtime_binding_test_verifier,
)
from modules.communication.moltbot_bridge.tests.test_reddog_signer_owner_controlled_e0_admission import _keypair


def _owner(tmp_path, monkeypatch):
    values, owner, payloads = _v8_owner(tmp_path, monkeypatch)
    _, public = _keypair()
    owner.update(schema_version=loader.SCHEMA_VERSION_V9,
        grant_startup_custody=custody_metadata(owner, public))
    _write(values, owner)
    return values, owner, payloads


def _write(values, owner):
    owner['config_id'] = loader.digest({k:v for k,v in owner.items() if k != 'config_id'})
    values['raw'][0] = json.dumps(owner).encode('ascii')


def _v8_owner(tmp_path, monkeypatch):
    _, repo, path, owner, raw = startup_owner_fixture(monkeypatch, tmp_path)
    _, binding = model_selection_and_runtime_binding_receipts(runtime_surface='reddog_artifact_generation')
    verifier = model_runtime_binding_test_verifier(binding)
    payloads = dict(catalog=verifier.catalog_snapshot,
        benchmarks={'benchmark_evidence_receipts':verifier.benchmark_evidence_receipts},
        promotions={'promotion_evidence_receipts':verifier.promotion_evidence_receipts},
        evidence=verifier.verified_evidence_bundle, policy=verifier.runtime_policy,
        trusted_keys=verifier.trusted_keys_payload)
    inputs = {}
    for name, payload in payloads.items():
        target = Path(owner['runtime_root']) / ('model-' + name + '.json')
        target.parent.mkdir(parents=True, exist_ok=True)
        content = json.dumps(payload, sort_keys=True).encode('utf-8')
        target.write_bytes(content)
        inputs[name] = dict(path=str(target), raw_digest=loader.raw_digest(content))
    now = int(time.time())
    owner.update(schema_version=loader.SCHEMA_VERSION_V8,
        model_verifier_authority=dict(issued_at=now-1, expires_at=now+30, inputs=inputs))
    values = dict(repo=repo, owner_config_path=path, raw=raw)
    _write(values, owner)
    return values, owner, payloads


def test_v9_extends_exact_v8_shape_and_keeps_model_verifier(tmp_path, monkeypatch):
    values, owner, payloads = _owner(tmp_path, monkeypatch)
    assert loader.V9_FIELDS == loader.V8_FIELDS | {'grant_startup_custody'}
    assert loader._load_owner_config(values['owner_config_path'], repo=values['repo']) == owner
    verifier = loader.load_system_service_model_runtime_verifier(
        owner_config_path=values['owner_config_path'], repo_root=values['repo'],
        expected_owner_config_id=owner['config_id'], trusted_now_epoch=lambda: int(time.time()))
    assert verifier.runtime_policy == payloads['policy']
    assert type(verifier.signature_verifier).__name__ == 'Ed25519SignatureVerifier'


@pytest.mark.parametrize('mutation', ['missing','extra','signing_id','loader_id','audit_overlap',
    'target_uid','target_principal','proof_ref','proof_purpose','proof_key','permission_boolean',
    'permission_encoding','directory','model_missing','model_extra','model_path','duplicate',
    'downgrade','unknown_schema','replay_root'])
def test_v9_custody_and_inherited_checks_fail_closed(tmp_path, monkeypatch, mutation):
    values, owner, _ = _owner(tmp_path, monkeypatch)
    block = owner['grant_startup_custody']
    if mutation == 'missing': block.pop('root_load_permission')
    elif mutation == 'extra': block['root_control_permission'] = {}
    elif mutation == 'signing_id': block['credential_binding']['credential_ids'].append('replay')
    elif mutation == 'loader_id': block['loader_credential_binding']['credential_ids'].append('grant-audit')
    elif mutation == 'audit_overlap': block['audit_mac_key_ref'] = block['signing_key_ref']
    elif mutation == 'target_uid': block['loader_credential_binding']['expected_uid'] = owner['verified_outcome_authority']['signer_uid']
    elif mutation == 'target_principal': block['credential_binding']['expected_requester'] = owner['verified_outcome_authority']['signer_principal_id']
    elif mutation == 'proof_ref': block['root_load_permission']['reference'] = block['audit_mac_key_ref']
    elif mutation == 'proof_purpose': block['root_load_permission']['purpose'] = 'protected-use-acquire-finish.v1'
    elif mutation == 'proof_key': block['root_load_permission']['public_key'] = owner['verified_outcome_authority']['descriptor']['signer_public_key']
    elif mutation == 'permission_boolean': block['root_load_permission']['issued_at'] = True
    elif mutation == 'permission_encoding': block['replay_integrity_permission']['encoding'] = 'base64'
    elif mutation == 'directory': block['loader_credential_binding']['credential_directory'] = '/tmp/credentials'
    elif mutation == 'model_missing': owner['model_verifier_authority']['inputs'].pop('policy')
    elif mutation == 'model_extra': owner['model_verifier_authority']['authority'] = True
    elif mutation == 'model_path': owner['model_verifier_authority']['inputs']['policy']['path'] = str(values['repo']/'escape')
    elif mutation == 'downgrade': owner['schema_version'] = loader.SCHEMA_VERSION_V8
    elif mutation == 'unknown_schema': owner['schema_version'] = 'reddog_signer_system_service_owner_config.v10'
    elif mutation == 'replay_root': owner['startup_custody']['replay_store']['high_water_root'] = str(values['repo'])
    _write(values, owner)
    if mutation == 'duplicate':
        raw = values['raw'][0].decode('ascii').replace('"grant_startup_custody": {',
            '"grant_startup_custody": {"signing_key_ref":"duplicate",', 1)
        values['raw'][0] = raw.encode('ascii')
    with pytest.raises(ValueError): loader._load_owner_config(values['owner_config_path'], repo=values['repo'])


def test_v8_rejects_issuer_extension_but_still_accepts_original_shape(tmp_path, monkeypatch):
    values, owner, _ = _v8_owner(tmp_path, monkeypatch)
    assert loader._load_owner_config(values['owner_config_path'], repo=values['repo']) == owner
    original = copy.deepcopy(owner)
    owner['grant_startup_custody'] = {}
    _write(values, owner)
    with pytest.raises(ValueError): loader._load_owner_config(values['owner_config_path'], repo=values['repo'])
    _write(values, original)
    assert loader._load_owner_config(values['owner_config_path'], repo=values['repo']) == original


@pytest.mark.parametrize('edge', ['owner','grant_client'])
def test_v9_retains_existing_grant_and_effect_owner_routes(tmp_path, monkeypatch, edge):
    def fixture(patch, path):
        values, owner, _ = _owner(path, patch)
        return loader, values['repo'], values['owner_config_path'], owner, values['raw']
    monkeypatch.setattr(legacy, 'owner_fixture', fixture)
    if edge == 'owner':
        legacy.test_effect_consent_v6_startup_policy_and_grant_owner_edges(monkeypatch, tmp_path)
    else:
        legacy.test_effect_consent_v6_grant_supply_schema_edge_only(monkeypatch, tmp_path)
