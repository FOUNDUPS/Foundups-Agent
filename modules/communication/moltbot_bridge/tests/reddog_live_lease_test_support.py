"""Synthetic authenticated selection seam; real protected nonce MAC/SQLite IO."""
from contextlib import contextmanager
from copy import deepcopy
from types import SimpleNamespace

from .consensus_nonce_test_support import case, load
from modules.communication.moltbot_bridge.src import reddog_signer_owner_e0_current_selection as live


def setup(monkeypatch, tmp_path):
    state = case(monkeypatch, tmp_path)
    state.nonces = load(state)
    state.entries = state.rechecks = state.validations = 0
    state.validation_hook = None
    state.boundary = Boundary(state)
    monkeypatch.setattr(live, 'load_system_service_manifest_selection',
                        lambda **kw: (state, state.boundary))
    def validate(repo, selected, policy):
        assert state.active == 1 and repo == state.values['repo'].resolve()
        state.validations += 1
        if state.validation_hook:
            state.validation_hook(state)
        return SimpleNamespace(policy=deepcopy(state.policy), selection=deepcopy(selected))
    monkeypatch.setattr(live, '_validated_selected_lease', validate)
    return state


class Boundary:
    def __init__(self, state):
        self.state = state

    @contextmanager
    def _lease_current(self, token):
        state = self.state
        assert token is state and state.active == 0
        state.active += 1
        state.entries += 1
        try:
            yield deepcopy(state.selection)
            if state.finish:
                state.finish()
            if state.exit_failure:
                raise ValueError('synthetic_generation_lease_exit_failed')
        finally:
            state.active -= 1

    def _recheck_current_locked(self, selected):
        self.state.rechecks += 1
        assert self.state.active == 1
        if selected != self.state.selection:
            raise ValueError('synthetic_generation_changed')


def scope(state):
    return live._lease_validated_owner_e0_current_scope(
        owner_config_path=state.values['owner_config_path'],
        repo_root=state.values['repo'], policy=state.policy)


def current(state, token):
    return live._scope_admission(token, owner_config_path=state.values['owner_config_path'],
                                 repo_root=state.values['repo'])
