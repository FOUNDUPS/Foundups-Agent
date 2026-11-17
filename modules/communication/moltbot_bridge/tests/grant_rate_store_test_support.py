"""Synthetic authority fixtures; real durable stores and signing implementations."""
import json
import os
import time
from dataclasses import replace

from modules.communication.moltbot_bridge.src import (
    reddog_grant_authority_startup_custody as custody,
    reddog_signer_system_service_manifest_selection_loader as loader,
)
from modules.communication.moltbot_bridge.src.reddog_signer_secret_grant_durable_nonce_store import (
    DurableSignerSecretGrantNonceStore,
)
from modules.communication.moltbot_bridge.tests.grant_startup_custody_fixture import custody_metadata
from modules.communication.moltbot_bridge.tests import test_reddog_external_signer_authoritative_use_lease as stores


def rate_metadata(root):
    return dict(purpose=custody.RATE_STORE_PURPOSE, nonce_path=str(root/'rate/nonces.json'),
        nonce_root=str(root/'rate'), high_water_path=str(root/'rate-water/authority.sqlite3'),
        high_water_root=str(root/'rate-water'), replay_store_binding_digest='sha256:'+'c'*64,
        replay_store_id='synthetic-issuer-rate', durability_receipt_id='sha256:'+'d'*64)


def separate_grant_socket(owner, root):
    socket_root = root / 'grant-socket'
    socket_root.mkdir(exist_ok=True)
    owner['independent_grant_authority']['authority_socket_path'] = str(
        (socket_root / 'grant-authority.sock').resolve())
    # Legacy synthetic owners put the root socket directly under the test root.
    # V10 models distinct server-owned directories, without opening listeners.
    owner['verified_outcome_authority']['authority_socket_path'] = str(
        (root / 'root-socket' / 'outcome-authority.sock').resolve())


def provision(config):
    now = int(time.time())
    high = stores.SqliteMonotonicAuthorityStore(config.high_water_path,
        allowed_root=config.high_water_root, repo_root=config.repo_root,
        store_id=config.replay_store_id, durability_receipt_id=config.durability_receipt_id)
    raw = stores.AtomicProposalAuthenticityNonceStore(config.nonce_path,
        allowed_root=config.nonce_root, repo_root=config.repo_root,
        integrity_key=stores.INTEGRITY_KEY, replay_store_binding_digest=config.replay_store_binding_digest,
        high_water_store=high, clock=time.time)
    reservation = raw.reserve('fixture-init', expires_at=now+1000, subject='fixture')
    raw.rollback(reservation)
    if os.name == 'posix':
        for path in (config.nonce_root, config.high_water_root): path.chmod(0o700)
        for path in (config.nonce_path, config.high_water_path): path.chmod(0o600)
    return DurableSignerSecretGrantNonceStore(config, integrity_key=stores.INTEGRITY_KEY, clock=time.time)


def upgrade_case(case, tmp_path, monkeypatch):
    policy = case.deps.owner_policy
    policy.update(issued_at=int(time.time())-1, expires_at=int(time.time())+120)
    uid, gid = (os.geteuid(), os.getegid()) if os.name == 'posix' else (997, 997)
    case.owner['independent_grant_authority'].update(authority_service_uid=uid, authority_service_gid=gid)
    case.owner.update(schema_version=loader.SCHEMA_VERSION_V10, grant_rate_store=rate_metadata(tmp_path))
    separate_grant_socket(case.owner, tmp_path)
    raw = case.deps.replay_store._config
    case.target_store = case.deps.replay_store
    case.owner['startup_custody'] = dict(policy_path=str(tmp_path/'policy.json'), replay_store=dict(
        high_water_path=str(raw.high_water_path), high_water_root=str(raw.high_water_root),
        replay_store_binding_digest=raw.replay_store_binding_digest))
    case.owner['grant_startup_custody'] = custody_metadata(case.owner, policy['grant_authority_public_key'],
        signer_agent=policy['grant_authority_signer_agent_id'], principal=policy['grant_authority_principal_id'])
    case.owner['grant_startup_custody']['replay_integrity_permission']['purpose'] = custody.RATE_PURPOSE
    store = provision(custody.grant_rate_store_config(case.owner, case.repo))
    case.deps = replace(case.deps, replay_store=store,
        credential_binding=replace(case.deps.credential_binding, expected_uid=uid, expected_gid=gid))
    monkeypatch.setattr(loader, '_load_owner_config', lambda *a, **kw: case.owner)
    monkeypatch.setattr(loader, '_read_root_owned_bytes', lambda *a, **kw: json.dumps(policy).encode('ascii'))
    if os.name != 'posix':
        monkeypatch.setattr(custody, 'require_private_grant_rate_store', lambda *a: None)
    return case
