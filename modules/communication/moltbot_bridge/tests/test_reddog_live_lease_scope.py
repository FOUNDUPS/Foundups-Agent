"""Bounded lifetime/currentness controls; authenticated OS selection is a fixture."""
import copy
import pickle
from concurrent.futures import ThreadPoolExecutor

import pytest

from .reddog_live_lease_test_support import setup, scope, current, live
from .consensus_nonce_test_support import NONCE, SUBJECT


def test_same_scope_nonce_transactions_revalidate_without_reacquiring(monkeypatch, tmp_path):
    state = setup(monkeypatch, tmp_path)
    with scope(state) as token:
        handle = state.nonces._reserve(NONCE, expires_at=int(state.wall)+10,
                                      subject=SUBJECT, _scope=token)
        assert handle is not None
        state.nonces._commit(handle, _scope=token)
        assert state.entries == 1 and state.active == 1
        assert state.rechecks >= 5 and state.validations >= 6
    assert state.active == 0
    assert state.nonces.reserve(NONCE, expires_at=int(state.wall)+10, subject=SUBJECT) is None


@pytest.mark.parametrize('change', ['owner', 'generation', 'policy', 'wall', 'mono', 'expiry'])
def test_live_scope_rejects_current_drift(monkeypatch, tmp_path, change):
    state = setup(monkeypatch, tmp_path)
    with pytest.raises(ValueError):
        with scope(state) as token:
            if change == 'owner':
                state.owner['consensus_nonce_authority']['integrity_permission']['expires_at'] -= 1
                from .test_reddog_parent_model_inputs import legacy
                legacy._write(state.values, state.owner)
            elif change == 'generation':
                state.selection['generation_revision'] = 'sha256:'+'f'*64
            elif change == 'policy':
                state.policy['expires_at'] += 1
            elif change == 'wall':
                state.wall -= 1
            elif change == 'mono':
                state.mono -= 1
            else:
                state.wall += 31
            current(state, token)
    assert state.active == 0
    with pytest.raises(ValueError, match='not_live'):
        current(state, token)


def test_scope_cannot_be_forged_copied_or_used_from_another_thread(monkeypatch, tmp_path):
    state = setup(monkeypatch, tmp_path)
    with pytest.raises(TypeError):
        live._CurrentOwnerUseScope()
    with scope(state) as token:
        for operation in (copy.copy, copy.deepcopy, pickle.dumps):
            with pytest.raises(TypeError):
                operation(token)
        with ThreadPoolExecutor(max_workers=1) as pool:
            with pytest.raises(ValueError, match='not_live'):
                pool.submit(current, state, token).result()
        forged = object.__new__(live._CurrentOwnerUseScope)
        with pytest.raises(ValueError, match='not_live'):
            current(state, forged)
    with pytest.raises(ValueError, match='not_live'):
        current(state, token)


def test_scope_revoked_when_lease_exit_fails(monkeypatch, tmp_path):
    state = setup(monkeypatch, tmp_path)
    with pytest.raises(ValueError, match='lease_exit_failed'):
        with scope(state) as token:
            state.exit_failure = True
    with pytest.raises(ValueError, match='not_live'):
        current(state, token)


def test_owned_reservation_can_roll_back_after_scope_ends(monkeypatch, tmp_path):
    state = setup(monkeypatch, tmp_path)
    with scope(state) as token:
        handle = state.nonces._reserve(NONCE, expires_at=int(state.wall)+10,
                                      subject=SUBJECT, _scope=token)
    with pytest.raises(ValueError, match='not_live'):
        state.nonces._commit(handle, _scope=token)
    # Failed commit performs owned rollback; the stale handle must not survive.
    assert handle not in state.nonces._owned
    with scope(state) as next_token:
        retry = state.nonces._reserve(NONCE, expires_at=int(state.wall)+10,
                                     subject=SUBJECT, _scope=next_token)
        assert retry is not None
        state.nonces.rollback(retry)


def test_scope_facade_preserves_one_private_owner(monkeypatch, tmp_path):
    from modules.communication.moltbot_bridge.src import reddog_signer_owner_e0_current_scope as owner
    assert live._CurrentOwnerUseScope is owner._CurrentOwnerUseScope
    assert live._scope_admission is owner._scope_admission
    assert live._lease_validated_owner_e0_current_scope is owner._lease_validated_owner_e0_current_scope
    state = setup(monkeypatch, tmp_path)
    with scope(state) as token:
        assert token in owner._LIVE_SCOPES
        before = state.validations
        current(state, token)
        assert state.validations == before + 1
    assert token not in owner._LIVE_SCOPES
    with pytest.raises(ValueError, match="not_live"):
        current(state, token)
