"""Real two-process LOAD/flock ordering; installed ownership/permission synthetic.

Uses production permission orchestration, revocation oracle, request/client/router,
Ed25519 verification and stores. No root service or real credential is installed.
"""
from contextlib import contextmanager
from dataclasses import replace
import json
import multiprocessing
import os
from pathlib import Path
import socket
import sys
import tempfile
import time
from types import SimpleNamespace

import pytest

from modules.communication.moltbot_bridge.src import (
    reddog_grant_authority_wsp71_permission_rehydration as permission,
    foundup_verified_outcome_root_revocation_validation as validation,
    foundup_verified_outcome_root_authority_client as transport,
    foundup_verified_outcome_root_revocation_client as client,
    foundup_verified_outcome_root_revocation_protocol as wire,
)
from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_authority_router import handle_root_authority_wire_request
from modules.communication.moltbot_bridge.src.reddog_signer_socket_peer_credential_attestor import KernelPeerCredentialAttestor, PeerCredentialPolicy
from modules.communication.moltbot_bridge.src.reddog_signer_secret_grant_root_protected_use_oracle import build_grant_issuer_revocation_oracle
from modules.communication.moltbot_bridge.src.reddog_signer_secret_grant_revocation_durable_oracle import UncomposedDurableSignerGrantRevocationOracle
from modules.communication.moltbot_bridge.src.reddog_ed25519_signature_verifier_backend import Ed25519SignatureVerifier
from modules.infrastructure.shared_utilities.runtime_artifact_safety import confined_runtime_operation_lock
from modules.communication.moltbot_bridge.tests.test_foundup_verified_outcome_root_grant_load import _runtime, _sign

pytestmark = pytest.mark.skipif(sys.platform != 'linux', reason='Linux AF_UNIX and flock required')
_REAL_ROUNDTRIP = transport._root_socket_roundtrip


def _lock(root):
    return confined_runtime_operation_lock(root/'owner'/'generation.lock',
        repo_root=root/'repo', allowed_root=root/'owner')


def _current(root):
    return json.loads((root/'owner'/'current.json').read_text())


def _locked(root):
    import fcntl
    with (root/'owner'/'generation.lock').open('rb') as handle:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return True
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    return False


def _serve(root, values, mode, ready, entered, acquired, result):
    lease = validation.lease_root_revocation_policy
    @contextmanager
    def fenced(*args, **kwargs):
        with _lock(root):
            acquired.set()
            with lease(*args, **kwargs) as current:
                yield current
    validation.lease_root_revocation_policy = fenced
    path = root/'root.sock'
    attestor = KernelPeerCredentialAttestor(PeerCredentialPolicy(
        {os.getuid():wire.GRANT_PEER_PRINCIPAL}, (os.getgid(),)))
    handled = 0
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as listener:
            listener.bind(str(path)); listener.listen(2); listener.settimeout(3)
            ready.set()
            for index in range(1 if mode == 'old-order' else 2):
                connection, _ = listener.accept()
                with connection:
                    connection.settimeout(2)
                    raw = b''
                    while True:
                        chunk = connection.recv(65536)
                        if not chunk:
                            break
                        raw += chunk
                    entered.set()
                    response = handle_root_authority_wire_request(raw,
                        peer=attestor.attest_identity(connection), state=values['state'],
                        snapshot_supplier=lambda:values['snapshot'],
                        revocation_authority=values['server_authority'], now_epoch=int(time.time()))
                    if index == 0 and mode in ('policy','generation','expiry'):
                        current = _current(root)
                        current[mode] = 'changed'
                        (root/'owner'/'current.json').write_text(json.dumps(current))
                    try:
                        connection.sendall(response)
                    except BrokenPipeError:
                        pass
                    handled += 1
                if mode in ('policy','generation','expiry'):
                    break
    finally:
        path.unlink(missing_ok=True)
        result.put((os.getpid(), (root/'owner'/'generation.lock').stat().st_ino, handled))


def _oracle(root, values, monkeypatch):
    # Only root-UID custody is synthetic; real peer credentials still checked.
    monkeypatch.setattr(transport, '_root_socket_roundtrip',
        lambda path, raw, _uid, timeout: _REAL_ROUNDTRIP(path, raw, os.getuid(), .4))
    exchange = transport.build_root_authority_socket_exchange(repo_root=values['repo'], socket_path=root/'root.sock')
    anchor = client._create_root_revocation_anchor_authority(values['snapshot'].descriptor,
        owner_config_id=values['policy']['owner_config_id'], policy=values['policy'],
        binding=values['binding'], exchange=exchange, now_epoch=int(time.time()),
        request_signer=lambda text:_sign(values['grant_private'],text), requester_role=wire.GRANT_ROLE)
    durable = UncomposedDurableSignerGrantRevocationOracle(binding=values['binding'], policy=values['policy'],
        reader=values['store'].reader(), witness=values['witness'].reader(), anchor=anchor,
        principal_key_resolver=SimpleNamespace(resolve=lambda *_:values['policy']['revocation_authority_public_key']),
        signature_verifier=Ed25519SignatureVerifier(), clock=lambda:int(time.time()))
    return build_grant_issuer_revocation_oracle(durable=durable, policy=values['policy'], binding=values['binding'])


def _permission_fixture(root, values, monkeypatch):
    @contextmanager
    def lease(**kwargs):
        with _lock(root):
            yield SimpleNamespace()
    def captured(*args):
        current = _current(root)
        if current['expiry'] != 'live':
            raise ValueError('synthetic permission expired')
        epoch = int(time.time())
        return current, dict(issuer_key_epoch=values['policy']['grant_authority_key_epoch'],
                             issued_at=epoch-1, expires_at=epoch+30)
    monkeypatch.setattr(permission, 'lease_validated_owner_e0_current_admission', lease)
    monkeypatch.setattr(permission, '_permission_state', captured)
    return lease


def _fixed_epoch_runtime(root, monkeypatch):
    # Lock ordering uses a fixed wall clock; real monotonic time still bounds RPCs.
    epoch = int(time.time())
    monkeypatch.setattr(time, 'time', lambda: epoch)
    return _runtime(root, monkeypatch)


@pytest.mark.parametrize('mode', ['old-order','current','policy','generation','expiry'])
def test_permission_root_load_generation_lock_across_processes(monkeypatch, mode):
    with tempfile.TemporaryDirectory(prefix='issuer-load-') as directory:
        root = Path(directory)
        (root/'owner').mkdir(); (root/'repo').mkdir()
        (root/'owner'/'current.json').write_text(json.dumps(dict(policy='original', generation=1, expiry='live')))
        with _lock(root):
            pass
        values = _fixed_epoch_runtime(root/'fixture', monkeypatch)
        # Keep the synthetic target distinct from the real issuer on UID1001 CI hosts.
        target_uid = 1002 if os.getuid() == 1001 else 1001
        values['snapshot'] = replace(values['snapshot'], signer_uid=target_uid)
        values['owner']['verified_outcome_authority']['signer_uid'] = target_uid
        values['owner']['independent_grant_authority'].update(authority_service_uid=os.getuid(), authority_service_gid=os.getgid())
        lease = _permission_fixture(root, values, monkeypatch)
        oracle = _oracle(root, values, monkeypatch)
        context = multiprocessing.get_context('fork')
        ready, entered, acquired, results = context.Event(), context.Event(), context.Event(), context.Queue()
        process = context.Process(target=_serve, args=(root,values,mode,ready,entered,acquired,results))
        process.start()
        try:
            assert ready.wait(5)
            calls = []
            def action():
                assert _locked(root)
                calls.append('used')
                return 'accepted'
            started = time.monotonic()
            if mode == 'old-order':
                with lease():
                    with pytest.raises((TimeoutError, OSError)):
                        oracle.authorize_key_epoch_use(key_epoch=values['policy']['grant_authority_key_epoch'],
                            at_epoch=int(time.time()), expires_at=int(time.time())+30, action=action)
                    assert entered.is_set() and not acquired.is_set()
                assert time.monotonic()-started >= .35
            else:
                kwargs = dict(owner_config_path=values['owner_config_path'], repo_root=values['repo'],
                    owner_policy=values['policy'], now_epoch=int(time.time()), revocation_oracle=oracle, action=action)
                if mode == 'current':
                    assert permission.authorize_current_grant_authority_wsp71_use(**kwargs) == 'accepted'
                    assert calls == ['used']
                else:
                    with pytest.raises(ValueError):
                        permission.authorize_current_grant_authority_wsp71_use(**kwargs)
                    assert calls == []
                assert acquired.is_set()
            process.join(5)
            assert not process.is_alive() and process.exitcode == 0
            pid, inode, handled = results.get(timeout=1)
            assert pid != os.getpid() and inode == (root/'owner'/'generation.lock').stat().st_ino
            assert handled == (2 if mode == 'current' else 1)
            assert not (root/'root.sock').exists() and time.monotonic()-started < 5
        finally:
            if process.is_alive():
                process.terminate(); process.join(2)
            results.close()
