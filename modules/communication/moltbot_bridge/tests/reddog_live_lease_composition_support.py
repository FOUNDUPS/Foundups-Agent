"""Real signed model/parent/effect and MAC/SQLite; explicit OS/E0 credential seams."""
import json
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

from . import consensus_nonce_test_support as nonce
from .reddog_parent_consensus_test_support import setup as parent_setup
from .reddog_reviewer_composition_test_support import Lease
from .reddog_live_lease_test_support import live
from modules.communication.moltbot_bridge.src import reddog_grant_authority_wsp71_permission_rehydration as permission


def _probe(path, channel):
    import fcntl
    import os
    try:
        while channel.recv() == 'probe':
            with Path(path).open('rb') as stream:
                try:
                    fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError:
                    held = True
                else:
                    held = False
                    fcntl.flock(stream, fcntl.LOCK_UN)
                channel.send((held, os.fstat(stream.fileno()).st_ino))
    finally:
        channel.close()


class StrictLease(Lease):
    @contextmanager
    def _lease_current(self, token):
        assert not self.active, 'nested_generation_acquisition'
        with super()._lease_current(token) as selected:
            yield deepcopy(selected)
            if self.state.exit_failure:
                raise ValueError('synthetic_lease_exit_failure')

    def _recheck_current_locked(self, selected):
        assert self.active
        self.state.rechecks += 1
        if selected != self.state.selection:
            raise ValueError('synthetic_selection_drift')


def setup(monkeypatch, tmp_path):
    (tmp_path / 'nonce').mkdir(parents=True)
    durable = nonce.case(monkeypatch, tmp_path / 'nonce')
    state = parent_setup(monkeypatch, tmp_path / 'approval', real_models=True)
    state.owner = {**durable.owner, **state.owner, 'schema_version': live_owner_version()}
    state.owner['consensus_nonce_authority']['credential_binding'].update(issued_at=900, expires_at=1100)
    state.owner['consensus_nonce_authority']['integrity_permission'].update(issued_at=900, expires_at=1100)
    state.policy = dict(durable.policy, owner_config_id=state.owner['config_id'], issued_at=999, expires_at=1030)
    state.mono, state.rechecks, state.validations = 100.0, 0, 0
    state.exit_failure = False
    state.lease = StrictLease(state)
    monkeypatch.setattr(live.time, 'time', lambda: float(state.now))
    monkeypatch.setattr(live.time, 'monotonic', lambda: state.mono)
    _selection_seams(monkeypatch, state)
    _nonce_inputs(monkeypatch, state)
    state.nonces = nonce.adapter.load_protected_consensus_nonce_authority(
        owner_config_path=state.call['owner_config_path'], repo_root=state.repo,
        expected_owner_config_id=state.owner['config_id'])
    state.signing = replace(state.signing, nonce_authority=state.nonces)
    return state


def live_owner_version():
    return nonce.current.loader.SCHEMA_VERSION_V13


def _selection_seams(monkeypatch, state):
    monkeypatch.setattr(live, 'load_system_service_manifest_selection',
                        lambda **kw: (state.lease.token, state.lease))
    def validate(repo, selected, policy):
        assert state.lease.active and repo == state.repo.resolve()
        state.validations += 1
        return SimpleNamespace(policy=deepcopy(state.policy), selection=deepcopy(selected))
    monkeypatch.setattr(live, '_validated_selected_lease', validate)
    @contextmanager
    def admission(**kw):
        with state.lease._lease_current(state.lease.token) as selected:
            yield validate(state.repo.resolve(), selected, state.policy)
    monkeypatch.setattr(nonce.current, 'lease_validated_owner_e0_current_admission', admission)
    monkeypatch.setattr(permission, 'lease_validated_owner_e0_current_admission', admission)


def _nonce_inputs(monkeypatch, state):
    # The existing resolver captures its default clock at import; align only
    # this disposable credential fixture with the signed approval epoch.
    monkeypatch.setattr(nonce.adapter, 'SystemdCredentialSecretResolver', lambda binding:
        nonce.credentials.SystemdCredentialSecretResolver(binding,
            clock=lambda: state.now, monotonic=lambda: state.mono))
    old_read = nonce.current.loader._read_root_owned_bytes
    path = state.owner['startup_custody']['policy_path']
    monkeypatch.setattr(nonce.current.loader, '_read_root_owned_bytes', lambda target, root:
        json.dumps(state.policy).encode('ascii') if str(target) == path else old_read(target, root))
    def credential(binding, identifier):
        assert state.lease.active and identifier == 'consensus-integrity'
        return nonce.durable.stores.INTEGRITY_KEY.decode('utf-8')
    monkeypatch.setattr(nonce.credentials, '_read_credential', credential)


def scope(state):
    return live._lease_validated_owner_e0_current_scope(owner_config_path=state.call['owner_config_path'],
        repo_root=state.repo, policy=state.policy)


def authorize(monkeypatch, state, action):
    """Synthetic permission artifact/root oracle; canonical action/lease ordering."""
    receipt = dict(issued_at=999, expires_at=1030, issuer_key_epoch='synthetic-epoch')
    monkeypatch.setattr(permission, '_permission_state', lambda *args: ('synthetic-current-receipt', receipt))
    class Oracle:
        def authorize_current_key_epoch_use(self, *, action, **kw):
            assert not state.lease.active
            return action()
    return permission._authorize_current_grant_authority_scoped_use(
        owner_config_path=state.call['owner_config_path'], repo_root=state.repo,
        owner_policy=state.policy, now_epoch=state.now, revocation_oracle=Oracle(), action=action)
