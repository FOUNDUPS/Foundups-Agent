"""Real separate Linux UIDs/stores; synthetic authority, keys and revocation.

No installed authority or service is invoked. The owner-validation seam supplies
an explicit test owner from root-owned bytes; protected reads, credential-free
policy/custody checks, signing, durable rate and target replay owners are real.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from dataclasses import asdict, replace
from types import SimpleNamespace

import pytest
from modules.communication.moltbot_bridge.src import (
    reddog_grant_authority_startup_custody as custody,
    reddog_signer_secret_grant_durable_rate_authority as rates,
    reddog_signer_system_service_manifest_selection_loader as loader,
)
from modules.communication.moltbot_bridge.src.reddog_signer_independent_secret_grant_binding import (
    build_secret_grant_authority_policy, resolve_secret_grant_target_binding_from_config,
)
from modules.communication.moltbot_bridge.src.reddog_signer_secret_grant_durable_nonce_store import DurableSignerSecretGrantNonceStore
from modules.communication.moltbot_bridge.tests import test_reddog_grant_authority_service as service_fixture
from modules.communication.moltbot_bridge.tests import test_reddog_signer_independent_secret_grant_provider as fixture
from modules.communication.moltbot_bridge.tests.grant_rate_store_test_support import (
    rate_metadata, provision, separate_grant_socket,
)
from modules.communication.moltbot_bridge.tests.grant_startup_custody_fixture import custody_metadata

TARGET, ISSUER, GROUP = 62001, 62002, 62000
KEY_STARTED = False
pytestmark = pytest.mark.skipif(sys.platform != 'linux' or getattr(os, 'geteuid', lambda: -1)() != 0,
    reason='requires Linux root solely to start disposable unregistered numeric UIDs')


def _claim_numeric_ids():
    import pwd
    import grp
    for value in (TARGET, ISSUER):
        with pytest.raises(KeyError): pwd.getpwuid(value)
    with pytest.raises(KeyError): grp.getgrgid(GROUP)


def _chown_tree(path, uid):
    for item in [path, *path.rglob('*')]:
        assert not item.is_symlink()
        os.chown(item, uid, GROUP)
        item.chmod(0o700 if item.is_dir() else 0o600)


def _prepare(root, monkeypatch):
    now = int(time.time())
    monkeypatch.setattr(fixture, 'NOW', now)
    monkeypatch.setattr(service_fixture.store_fixture, 'NOW', now)
    case = service_fixture._fixture_inputs(root/'target')
    policy = case.deps.owner_policy
    policy.update(issued_at=now-1, expires_at=now+120, rate_limit_max_requests=1)
    owner = case.owner
    owner.update(schema_version=loader.SCHEMA_VERSION_V10, grant_rate_store=rate_metadata(root/'issuer'))
    separate_grant_socket(owner, root)
    owner['independent_grant_authority'].update(authority_service_uid=ISSUER, authority_service_gid=GROUP)
    owner['verified_outcome_authority'].update(signer_uid=TARGET, signer_gid=GROUP)
    raw = case.deps.replay_store._config
    owner['startup_custody'] = dict(policy_path=str(root/'owner/policy.json'), replay_store=dict(
        high_water_path=str(raw.high_water_path), high_water_root=str(raw.high_water_root),
        replay_store_binding_digest=raw.replay_store_binding_digest))
    owner['grant_startup_custody'] = custody_metadata(owner, policy['grant_authority_public_key'],
        signer_agent=policy['grant_authority_signer_agent_id'], principal=policy['grant_authority_principal_id'])
    owner['grant_startup_custody']['replay_integrity_permission']['purpose'] = custody.RATE_PURPOSE
    provision(custody.grant_rate_store_config(owner, case.repo))
    _chown_tree(root/'issuer', ISSUER)
    _chown_tree(root/'target', TARGET)
    (root/'owner').mkdir(mode=0o755)
    for name, value in [('owner', owner), ('policy', policy)]:
        path = root/'owner'/f'{name}.json'
        path.write_text(json.dumps(value))
        path.chmod(0o444)
    return case


def _run(root, uid, operation, grant=None):
    source = Path(__file__).resolve().parents[4]
    code = ('import sys,runpy,json;sys.path[:]=json.loads(sys.argv.pop(1));'
            'runpy.run_path(sys.argv[1],run_name="__main__")')
    paths = [str(source), *(str(Path(p).resolve()) for p in sys.path if p)]
    read_fd, write_fd = os.pipe()
    try:
        try:
            completed = subprocess.run(['/usr/bin/setpriv', f'--reuid={uid}', f'--regid={GROUP}',
                '--clear-groups', '--no-new-privs', sys.executable, '-I', '-S', '-B', '-c', code,
                json.dumps(paths), str(Path(__file__).resolve()), str(write_fd), str(root), operation],
                input=json.dumps(grant), text=True, capture_output=True, timeout=30, pass_fds=(write_fd,),
                env={'PATH':'/usr/bin:/bin', 'PYTHONDONTWRITEBYTECODE':'1', 'PYTHON_DOTENV_DISABLED':'1'})
        finally:
            os.close(write_fd)
        assert completed.returncode == 0, completed.stderr
        assert completed.stdout == ''
        return json.loads(os.read(read_fd, os.fpathconf(read_fd, 'PC_PIPE_BUF') + 1))
    finally:
        os.close(read_fd)


def _public_inputs(root):
    path = root/'owner/owner.json'
    # This fixture replaces full deployment admission only. It still requires
    # root-owned, no-link file and ancestor reads in each unprivileged process.
    def fixture_owner(owner_path, *, repo):
        return json.loads(loader._read_root_owned_bytes(Path(owner_path), path.parent))
    loader._load_owner_config = fixture_owner
    owner = fixture_owner(path, repo=root/'target/repo')
    policy = json.loads(loader._read_root_owned_bytes(root/'owner/policy.json', path.parent))
    fixture.NOW = policy["issued_at"] + 1
    config = custody.target_replay_store_config(owner, policy, root/'target/repo')
    return owner, policy, config, path


def _issuer(root):
    owner, policy, target, owner_path = _public_inputs(root)
    config = custody.grant_rate_store_config(owner, target.repo_root)
    custody.require_private_grant_rate_store(owner, config)
    store = DurableSignerSecretGrantNonceStore(config, integrity_key=fixture.INTEGRITY_KEY, clock=lambda: fixture.NOW)
    binding = resolve_secret_grant_target_binding_from_config(policy, target)
    cap = rates.bind_protected_issuer_rate_store(owner_config_path=owner_path,
        repo_root=target.repo_root, owner_policy=policy, replay_store=store)
    authority = build_secret_grant_authority_policy(policy, binding, store,
        authority_principal_id=policy['grant_authority_principal_id'],
        authority_principal_provider=policy['grant_authority_principal_provider'],
        authority_public_key=policy['grant_authority_public_key'],
        authority_key_epoch=policy['grant_authority_key_epoch'],
        requester_principal_id=policy['grant_requester_principal_id'], issuer_rate_binding=cap)
    request = replace(fixture._target_request(), requested_operation=service_fixture.service.LOW_OPERATION)
    grant = fixture._grant(request, binding)
    signing = fixture.build_secret_grant_signing_request(grant, policy=authority, consensus_receipt_digest=None)
    global KEY_STARTED
    KEY_STARTED = True
    private = fixture.Ed25519PrivateKey.from_private_bytes(bytes(range(1, 33)))
    backend = fixture.Ed25519SignerBackend(private_key=private, public_key=fixture._public(private),
        key_epoch='grant-epoch-1', audit_mac_builder=fixture._AuditMac(), proposal_clock=lambda: fixture.NOW,
        secret_grant_authority_policy=authority,
        secret_grant_rate_authority=rates.DurableSignerSecretGrantRateAuthority(store))
    response = backend.sign(signing, fixture._peer())
    grant['signature'] = response.signature if response.accepted else 'rejected'
    return dict(accepted=response.accepted, rejection=response.rejection_code,
                other_store_denied=_other_store_denied(target.nonce_path),
                grant=grant if response.accepted else None)


def _target(root, grant):
    from modules.communication.moltbot_bridge.src.reddog_signer_secret_access_grant import (
        SignerSecretAccessGrantBoundary, ExpectedSignerSecretGrantBinding,
    )
    owner, policy, config, _ = _public_inputs(root)
    store = DurableSignerSecretGrantNonceStore(config, integrity_key=fixture.INTEGRITY_KEY, clock=lambda: fixture.NOW)
    binding = resolve_secret_grant_target_binding_from_config(policy, config)
    request = replace(fixture._target_request(), requested_operation=service_fixture.service.LOW_OPERATION)
    expected = ExpectedSignerSecretGrantBinding(**asdict(binding),
        signing_request_digest=fixture.signer_secret_access_request_digest(request.to_dict()),
        requested_operation=request.requested_operation, authority_tier='LOW',
        attested_peer_principal_id=request.requester_principal_id)
    boundary = SignerSecretAccessGrantBoundary(nonce_store=store,
        revocation_oracle=SimpleNamespace(is_revoked=lambda **kw: False), clock=lambda: fixture.NOW)
    cap = boundary.verify(grant, expected=expected, signature_verifier=fixture.Ed25519SignatureVerifier(),
        principal_key_resolver=fixture._Resolver(binding.issuer_public_key))
    assert boundary.replay_store_matches(expected)
    boundary.consume(cap)
    return dict(accepted=True, target_action='verified-consumption',
                other_store_denied=_other_store_denied(Path(owner['grant_rate_store']['nonce_path'])))


def _other_store_denied(path):
    try:
        path.read_bytes()
    except PermissionError:
        return True
    return False


def _worker():
    root, operation = Path(sys.argv[-2]), sys.argv[-1]
    try:
        value = _issuer(root) if operation == 'issue' else _target(root, json.load(sys.stdin))
    except Exception as exc:
        value = dict(accepted=False, error_type=type(exc).__name__)
    value.update(uid=os.geteuid(), gid=os.getegid(), key_started=KEY_STARTED)
    # Grant-shaped replies are private IPC, never stdout/stderr diagnostics.
    reply_fd = int(sys.argv[-3])
    payload = json.dumps(value).encode('utf-8')
    assert len(payload) <= os.fpathconf(reply_fd, 'PC_PIPE_BUF')
    assert os.write(reply_fd, payload) == len(payload)
    os.close(reply_fd)


def test_separate_uid_issuer_then_target_and_restart_rejections(monkeypatch):
    _claim_numeric_ids()
    with tempfile.TemporaryDirectory(prefix='rsi-rate-two-uid-', dir='/run') as directory:
        root = Path(directory); root.chmod(0o755)
        _prepare(root, monkeypatch)
        issued = _run(root, ISSUER, 'issue')
        assert issued['accepted'], {key:value for key,value in issued.items() if key != 'grant'}
        consumed = _run(root, TARGET, 'consume', issued['grant'])
        assert consumed['accepted'], consumed
        assert issued['other_store_denied'] and consumed['other_store_denied']
        assert not _run(root, TARGET, 'consume', issued['grant'])['accepted']
        assert not _run(root, ISSUER, 'issue')['accepted']
        assert issued['uid'] == ISSUER and consumed['uid'] == TARGET


@pytest.mark.parametrize('mutation', ['shared_mode', 'wrong_uid', 'hardlink', 'wrong_role'])
def test_native_custody_rejects_before_signing(monkeypatch, mutation):
    _claim_numeric_ids()
    with tempfile.TemporaryDirectory(prefix='rsi-rate-custody-', dir='/run') as directory:
        root = Path(directory); root.chmod(0o755)
        _prepare(root, monkeypatch)
        nonce = root/'issuer/rate/nonces.json'
        if mutation == 'shared_mode': nonce.chmod(0o660)
        elif mutation == 'wrong_uid': os.chown(nonce, TARGET, GROUP)
        elif mutation == 'hardlink': os.link(nonce, nonce.with_suffix('.alias'))
        elif mutation == 'wrong_role':
            path = root/'owner/owner.json'
            owner = json.loads(path.read_text()); owner['grant_rate_store']['purpose'] = custody.REPLAY_PURPOSE
            path.write_text(json.dumps(owner))
        result = _run(root, ISSUER, 'issue')
        assert result['accepted'] is False
        assert result['error_type'] == 'ValueError'
        assert result['key_started'] is False


if __name__ == '__main__':
    _worker()
