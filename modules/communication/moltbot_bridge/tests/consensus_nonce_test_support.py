"""Synthetic OS/current-generation seams; actual MAC, SQLite and credential owner."""
import copy
import json
import time
from contextlib import contextmanager
from types import SimpleNamespace

from modules.communication.moltbot_bridge.src import reddog_consensus_nonce_authority as adapter
from modules.communication.moltbot_bridge.src import reddog_consensus_nonce_current_owner as current
from modules.communication.moltbot_bridge.src import reddog_consensus_nonce_custody as custody
from modules.communication.moltbot_bridge.tests import grant_rate_store_test_support as durable
from modules.communication.moltbot_bridge.tests.test_reddog_parent_model_inputs import fixture, legacy
from modules.infrastructure.secrets_mcp.src import systemd_credential_secret_resolver as credentials

NONCE = 'sha256:' + '7' * 64
SUBJECT = 'elevated-consensus:' + 'sha256:' + '8' * 64


def metadata(owner, root):
    old = owner['grant_startup_custody']
    binding = copy.deepcopy(old['loader_credential_binding'])
    binding['credential_ids'] = ['consensus-integrity']
    permission = dict(old['replay_integrity_permission'], reference='systemd-creds://consensus-integrity',
                      purpose=custody.INTEGRITY_PURPOSE)
    store = dict(durable.rate_metadata(root), purpose=custody.PURPOSE,
        nonce_path=str(root/'consensus/nonces.json'), nonce_root=str(root/'consensus'),
        high_water_path=str(root/'consensus-water/state.sqlite3'), high_water_root=str(root/'consensus-water'),
        replay_store_id='synthetic-consensus', replay_store_binding_digest='sha256:'+'6'*64,
        durability_receipt_id='sha256:'+'f'*64)
    return dict(store=store, credential_binding=binding, integrity_permission=permission)


def owner_case(monkeypatch, tmp_path):
    values, owner, records, now = fixture(monkeypatch, tmp_path)
    owner.update(schema_version=current.loader.SCHEMA_VERSION_V13,
                 consensus_nonce_authority=metadata(owner, tmp_path))
    legacy._write(values, owner)
    return values, owner, records, now


def case(monkeypatch, tmp_path):
    values, owner, records, _ = owner_case(monkeypatch, tmp_path)
    now = int(time.time())
    raw = owner['startup_custody']['replay_store']
    policy = dict(owner_config_id=owner['config_id'], allowed_operations=['worktree_create'],
        allowed_authority_tiers=['HIGH'], consensus_required_tiers=['HIGH'],
        issued_at=now-1, expires_at=now+30,
        grant_authority_principal_id=owner['consensus_nonce_authority']['credential_binding']['expected_requester'],
        replay_path=str(tmp_path/'target/state.json'), replay_root=str(tmp_path/'target'),
        replay_store_id='synthetic-target', replay_store_durability_receipt_id='sha256:'+'1'*64)
    state = SimpleNamespace(values=values, owner=owner, records=records, policy=policy, active=0,
        wall=float(now), mono=100.0, finish=None, exit_failure=False, reads=0)
    state.selection = dict(owner_config_id=owner['config_id'], manifest_id='sha256:'+'2'*64,
        artifact_generation_digest='sha256:'+'3'*64, generation_revision='sha256:'+'4'*64,
        selection_issued_at=now-1, selection_expires_at=now+30)
    config = custody.consensus_nonce_config(owner, values['repo'])
    durable.provision(config)
    state.config = config
    read_owner = current.loader._read_root_owned_bytes
    policy_path = owner['startup_custody']['policy_path']
    monkeypatch.setattr(current.loader, '_read_root_owned_bytes', lambda path, root:
        json.dumps(state.policy).encode('ascii') if str(path) == policy_path else read_owner(path, root))
    @contextmanager
    def lease(**kwargs):
        state.active += 1
        try:
            yield SimpleNamespace(policy=copy.deepcopy(state.policy), selection=copy.deepcopy(state.selection))
            if state.finish: state.finish()
            if state.exit_failure: raise ValueError('synthetic_generation_lease_exit_failed')
        finally:
            state.active -= 1
    monkeypatch.setattr(current, 'lease_validated_owner_e0_current_admission', lease)
    monkeypatch.setattr(current, 'require_private_grant_rate_store', lambda *a: None)
    monkeypatch.setattr(current.time, 'time', lambda: state.wall)
    monkeypatch.setattr(current.time, 'monotonic', lambda: state.mono)
    monkeypatch.setattr(credentials, '_identity_matches', lambda binding: True)
    def read_credential(binding, identifier):
        assert state.active == 1 and identifier == 'consensus-integrity'
        state.reads += 1
        return durable.stores.INTEGRITY_KEY.decode('utf-8')
    monkeypatch.setattr(credentials, '_read_credential', read_credential)
    return state


def load(state):
    return adapter.load_protected_consensus_nonce_authority(owner_config_path=state.values['owner_config_path'],
        repo_root=state.values['repo'], expected_owner_config_id=state.owner['config_id'])
