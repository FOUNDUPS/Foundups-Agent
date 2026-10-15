"""Real custody composition with disposable signatures; OS installation is synthetic."""
import copy
import json
import time
from dataclasses import replace
from types import SimpleNamespace

import pytest

from modules.communication.moltbot_bridge.tests.grant_startup_custody_fixture import build_case, materialize
from modules.communication.moltbot_bridge.src import reddog_grant_authority_runtime_dependencies as runtime
from modules.communication.moltbot_bridge.src import reddog_grant_authority_root_request_signer as proof
from modules.communication.moltbot_bridge.src.reddog_grant_authority_startup_custody import validate_grant_startup_custody
from modules.communication.moltbot_bridge.src.reddog_signer_secret_grant_root_protected_use_oracle import RootAuthorizedSignerGrantRevocationOracle
from modules.communication.moltbot_bridge.tests import test_foundup_verified_outcome_root_grant_load as root_fixture


@pytest.fixture
def case(tmp_path, monkeypatch):
    return build_case(tmp_path, monkeypatch)


def test_composes_real_replay_resolver_issuer_oracle_and_load_signature(case):
    validate_grant_startup_custody(case.owner, repo_root=case.values['repo'],
                                 owner_root=case.values['owner_config_path'].parent)
    deps = materialize(case)
    assert type(deps.revocation_oracle) is RootAuthorizedSignerGrantRevocationOracle
    assert deps.revocation_oracle._protected_use is None
    assert deps.issuer_profile.signer_agent_id == 'grant:fixture'
    assert deps.credential_binding.credential_ids == frozenset({'grant-signing', 'grant-audit'})
    assert case.events[0] == 'isolate' and case.events.count('replay') == 1
    assert case.events.count('root-rpc') >= 2 and case.events.count('grant-signing') >= 2
    assert 'grant-audit' not in case.events and case.active == 0
    with pytest.raises(ValueError, match='cannot_authorize_target'):
        deps.revocation_oracle.authorize_grant_use({}, lambda: pytest.fail('target authority'))


@pytest.mark.parametrize('mutation', ['schema', 'owner', 'isolation', 'policy_scope', 'missing_custody',
    'signing_hash', 'audit_hash', 'issuer_key', 'issuer_epoch', 'signer_requester', 'loader_requester',
    'expired', 'missing_nonce', 'missing_high_water'])
def test_bad_inputs_reject_without_credential_resolution(case, monkeypatch, mutation):
    custody, policy = case.owner['grant_startup_custody'], case.values['policy']
    if mutation == 'schema': case.owner['schema_version'] = runtime.SCHEMA_VERSION_V9 + '-unknown'
    elif mutation == 'owner': case.owner['config_id'] = 'sha256:' + '0'*64
    elif mutation == 'isolation': monkeypatch.setattr(runtime, 'enforce_signer_process_isolation', lambda *a, **k: SimpleNamespace(accepted=False))
    elif mutation == 'policy_scope': policy['allowed_operations'] = ['write_repo']
    elif mutation == 'missing_custody': case.owner.pop('grant_startup_custody')
    elif mutation == 'signing_hash': custody['signing_key_ref'] = 'systemd-creds://unknown'
    elif mutation == 'audit_hash': custody['audit_mac_key_ref'] = 'systemd-creds://unknown'
    elif mutation == 'issuer_key': custody['root_load_permission']['public_key'] = policy['target_signer_public_key']
    elif mutation == 'issuer_epoch': custody['root_load_permission']['key_epoch'] = 'other'
    elif mutation == 'signer_requester': custody['credential_binding']['expected_requester'] = 'other'
    elif mutation == 'loader_requester': custody['loader_credential_binding']['expected_requester'] = 'other'
    elif mutation == 'expired': custody['root_load_permission']['expires_at'] = 1
    elif mutation == 'missing_nonce': case.replay_config.nonce_path.unlink()
    else: case.replay_config.high_water_path.unlink()
    with pytest.raises((ValueError, KeyError, OSError)):
        materialize(case)
    assert not any(event in case.events for event in ('replay','grant-signing','root-rpc'))


@pytest.mark.parametrize('mutation', ['owner', 'policy', 'permission'])
def test_owner_and_policy_drift_after_credential_read_reject(case, mutation):
    def drift():
        if mutation == 'owner': case.owner['config_id'] = 'sha256:' + '0'*64
        elif mutation == 'policy': case.values['policy']['rate_limit_max_requests'] += 1
        else: case.owner['grant_startup_custody']['root_load_permission']['expires_at'] -= 1
    case.after_read = drift
    with pytest.raises(ValueError): materialize(case)
    assert 'root-rpc' not in case.events


def test_owner_drift_after_root_reply_never_returns_dependencies(case):
    case.after_rpc = lambda: case.owner.update(config_id='sha256:' + '0'*64)
    with pytest.raises(ValueError): materialize(case)
    assert 'root-rpc' in case.events


@pytest.mark.parametrize('mutation', ['wrong-key','expired-proof','owner-after-proof'])
def test_proof_resolution_rechecks_key_permission_and_owner(case, mutation):
    def change():
        if case.events[-1] != 'grant-signing':
            return
        if mutation == 'wrong-key': case.secret_override = 'malformed-test-key'
        elif mutation == 'expired-proof':
            case.owner['grant_startup_custody']['root_load_permission']['expires_at'] = int(time.time())
        else: case.owner['config_id'] = 'sha256:'+'0'*64
    case.after_read = change
    with pytest.raises(ValueError): materialize(case)
    assert 'grant-signing' in case.events and 'root-rpc' not in case.events


@pytest.mark.parametrize('kind', ['legacy', 'advance', 'foreign-principal', 'foreign-epoch', 'foreign-policy'])
def test_proof_rejects_nonissuer_context_before_secret(case, kind):
    custody = case.owner['grant_startup_custody']
    _, _, binding, _ = runtime.current_grant_custody(case.owner, case.values['policy'])
    signer = proof.build_grant_root_request_signer(owner_config_path=case.values['owner_config_path'],
        repo_root=case.values['repo'], policy=case.values['policy'],
        descriptor=case.values['snapshot'].descriptor, credential_binding=binding)
    request = root_fixture._issuer_request(case.values)
    if kind == 'legacy': request = root_fixture._request(case.values)
    elif kind == 'advance': request = replace(request, operation=root_fixture.wire.OP_ADVANCE)
    elif kind == 'foreign-principal': request = replace(request, requester_principal_id='other')
    elif kind == 'foreign-epoch': request = replace(request, requester_key_epoch='other')
    else: request = replace(request, policy_id='sha256:'+'0'*64)
    with pytest.raises(ValueError): signer(root_fixture.wire.canonical_signer_input(request))
    assert case.events == []
