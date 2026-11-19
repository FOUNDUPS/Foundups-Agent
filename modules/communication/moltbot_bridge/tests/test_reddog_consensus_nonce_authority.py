"""Actual credential resolver/MAC/SQLite; OS and signed-generation seams labeled."""
import pytest
from .consensus_nonce_test_support import case, load, NONCE, SUBJECT, legacy


def test_independent_instance_restart_replay_and_owned_rollback(monkeypatch, tmp_path):
    state = case(monkeypatch, tmp_path)
    first, second = load(state), load(state)
    token = first.reserve(NONCE, expires_at=int(state.wall)+10, subject=SUBJECT)
    assert token and second.reserve(NONCE, expires_at=int(state.wall)+10, subject=SUBJECT) is None
    with pytest.raises(ValueError, match='not_owned'): second.rollback(token)
    first.rollback(token)
    token = second.reserve(NONCE, expires_at=int(state.wall)+10, subject=SUBJECT)
    second.commit(token)
    assert load(state).reserve(NONCE, expires_at=int(state.wall)+10, subject=SUBJECT) is None
    assert state.reads == 3 and state.active == 0


@pytest.mark.parametrize('fault', ['owner', 'policy', 'generation', 'expiry', 'clock', 'lease_exit'])
def test_currentness_failure_prevents_use_but_owned_cleanup_survives(monkeypatch, tmp_path, fault):
    state = case(monkeypatch, tmp_path)
    store = load(state)
    token = store.reserve(NONCE, expires_at=int(state.wall)+10, subject=SUBJECT)
    if fault == 'owner':
        state.owner['consensus_nonce_authority']['integrity_permission']['expires_at'] -= 1
        legacy._write(state.values, state.owner)
    elif fault == 'policy': state.policy['expires_at'] -= 1
    elif fault == 'generation': state.selection['generation_revision'] = 'sha256:'+'9'*64
    elif fault == 'expiry': state.wall += 31
    elif fault == 'clock': state.wall -= 1
    else: state.exit_failure = True
    with pytest.raises(ValueError): store.commit(token)
    assert state.active == 0
    # Failed commit reports cleanup; consumption, if already durable, is not undone.
    with pytest.raises(ValueError, match='not_owned'): store.rollback(token)


def test_withdrawal_allows_only_owned_rollback(monkeypatch, tmp_path):
    state = case(monkeypatch, tmp_path)
    store = load(state)
    token = store.reserve(NONCE, expires_at=int(state.wall)+10, subject=SUBJECT)
    state.owner.pop('consensus_nonce_authority')
    legacy._write(state.values, state.owner)
    store.rollback(token)
    with pytest.raises(ValueError): store.reserve(NONCE, expires_at=int(state.wall)+10, subject=SUBJECT)


def test_failed_reserve_lease_exit_rolls_back_exact_reservation(monkeypatch, tmp_path):
    state = case(monkeypatch, tmp_path)
    store = load(state)
    state.exit_failure = True
    with pytest.raises(ValueError) as failure:
        store.reserve(NONCE, expires_at=int(state.wall)+10, subject=SUBJECT)
    assert 'consensus_nonce_owned_cleanup_completed' in failure.value.__notes__
    state.exit_failure = False
    assert load(state).reserve(NONCE, expires_at=int(state.wall)+10, subject=SUBJECT)


@pytest.mark.parametrize('fault', ['boolean', 'expired', 'long', 'nonce', 'subject'])
def test_invalid_reservation_has_no_transaction(monkeypatch, tmp_path, fault):
    state = case(monkeypatch, tmp_path)
    store = load(state)
    before = state.config.nonce_path.read_bytes()
    expires = dict(boolean=True, expired=int(state.wall), long=int(state.wall)+31).get(fault, int(state.wall)+10)
    with pytest.raises(ValueError):
        store.reserve('invalid' if fault == 'nonce' else NONCE, expires_at=expires,
                      subject='foreign' if fault == 'subject' else SUBJECT)
    assert state.config.nonce_path.read_bytes() == before
