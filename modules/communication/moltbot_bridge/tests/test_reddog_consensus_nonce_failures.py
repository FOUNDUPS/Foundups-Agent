"""Store failure/concurrency probes with labeled OS/generation fixture seams."""
from concurrent.futures import ThreadPoolExecutor
import pytest
from .consensus_nonce_test_support import case, load, NONCE, SUBJECT, legacy, adapter


def test_independent_instances_serialize_actual_file_transactions(monkeypatch, tmp_path):
    state = case(monkeypatch, tmp_path)
    stores = [load(state), load(state)]
    def reserve(store):
        return store.reserve(NONCE, expires_at=int(state.wall)+10, subject=SUBJECT)
    with ThreadPoolExecutor(max_workers=2) as pool:
        handles = list(pool.map(reserve, stores))
    assert sum(token is not None for token in handles) == 1
    index = next(i for i, token in enumerate(handles) if token)
    stores[index].commit(handles[index])
    assert load(state).reserve(NONCE, expires_at=int(state.wall)+10, subject=SUBJECT) is None


@pytest.mark.parametrize('phase', ['before', 'after'])
def test_commit_error_cleanup_does_not_undo_durable_consumption(monkeypatch, tmp_path, phase):
    state = case(monkeypatch, tmp_path)
    store = load(state)
    token = store.reserve(NONCE, expires_at=int(state.wall)+10, subject=SUBJECT)
    original = store._store.commit
    def fail(value):
        if phase == 'after': original(value)
        raise RuntimeError('synthetic commit failure')
    monkeypatch.setattr(store._store, 'commit', fail)
    with pytest.raises(RuntimeError) as error: store.commit(token)
    assert 'consensus_nonce_owned_cleanup_completed' in error.value.__notes__
    again = load(state).reserve(NONCE, expires_at=int(state.wall)+10, subject=SUBJECT)
    assert (again is None) == (phase == 'after')


def test_reserve_cleanup_failure_preserves_original_and_cleanup_only_handle(monkeypatch, tmp_path):
    state = case(monkeypatch, tmp_path)
    store = load(state)
    original = store._store.rollback
    def fail(*args): raise OSError('synthetic cleanup failure')
    monkeypatch.setattr(store._store, 'rollback', fail)
    state.exit_failure = True
    with pytest.raises(ValueError, match='lease_exit') as error:
        store.reserve(NONCE, expires_at=int(state.wall)+10, subject=SUBJECT)
    handle = error.value.consensus_nonce_cleanup_handle
    assert 'consensus_nonce_owned_cleanup_failed' in error.value.__notes__
    with pytest.raises(ValueError, match='cleanup_only'): store.commit(handle)
    monkeypatch.setattr(store._store, 'rollback', original)
    store.rollback(handle)
    state.exit_failure = False
    assert load(state).reserve(NONCE, expires_at=int(state.wall)+10, subject=SUBJECT)


@pytest.mark.parametrize('phase', ['credential', 'reserve_exit', 'commit_exit'])
def test_post_action_expiry_withholds_success(monkeypatch, tmp_path, phase):
    state = case(monkeypatch, tmp_path)
    if phase == 'credential':
        original = adapter.SystemdCredentialSecretResolver.resolve
        def resolve(self, *args):
            result = original(self, *args)
            state.wall += 31
            return result
        monkeypatch.setattr(adapter.SystemdCredentialSecretResolver, 'resolve', resolve)
        with pytest.raises(ValueError): load(state)
        return
    store = load(state)
    if phase == 'commit_exit':
        token = store.reserve(NONCE, expires_at=int(state.wall)+10, subject=SUBJECT)
    state.finish = lambda: setattr(state, 'wall', state.wall + 31)
    with pytest.raises(ValueError):
        if phase == 'reserve_exit': store.reserve(NONCE, expires_at=int(state.wall)+10, subject=SUBJECT)
        else: store.commit(token)


@pytest.mark.parametrize('damage', ['state', 'database', 'mac', 'high_water', 'credential'])
def test_loader_requires_existing_authenticated_inputs(monkeypatch, tmp_path, damage):
    state = case(monkeypatch, tmp_path)
    if damage == 'state': state.config.nonce_path.unlink()
    elif damage == 'database': state.config.high_water_path.unlink()
    elif damage == 'mac': state.config.nonce_path.write_bytes(b'{}')
    elif damage == 'high_water': state.config.high_water_path.write_bytes(b'invalid')
    else:
        from modules.infrastructure.secrets_mcp.src import systemd_credential_secret_resolver as os_seam
        monkeypatch.setattr(os_seam, '_read_credential', lambda *args: 'wrong fixture integrity material of adequate size')
    with pytest.raises(Exception): load(state)


def test_no_public_clock_key_store_or_signature_injection():
    import inspect
    assert set(inspect.signature(adapter.load_protected_consensus_nonce_authority).parameters) == {
        'owner_config_path', 'repo_root', 'expected_owner_config_id'}
    with pytest.raises(TypeError): adapter.ProtectedConsensusNonceAuthority()


def test_hostile_nonce_object_is_not_converted(monkeypatch, tmp_path):
    state = case(monkeypatch, tmp_path)
    store = load(state)
    class Trap:
        def __str__(self): raise AssertionError('must not dispatch')
        def __bool__(self): raise AssertionError('must not dispatch')
    with pytest.raises(ValueError): store.reserve(Trap(), expires_at=int(state.wall)+10, subject=SUBJECT)
