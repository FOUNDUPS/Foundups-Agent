"""Real disposable MAC/SQLite state; no installed authority or credentials."""
import pytest
from modules.communication.moltbot_bridge.tests import grant_rate_store_test_support as support
from modules.communication.moltbot_bridge.src.reddog_signer_secret_grant_durable_nonce_store import SignerGrantReplayStoreConfig
from modules.communication.moltbot_bridge.src.reddog_proposal_authenticity_nonce_store import AtomicProposalAuthenticityNonceStore
from modules.communication.moltbot_bridge.src.reddog_sqlite_monotonic_authority_store import SqliteMonotonicAuthorityStore


def configured(tmp_path):
    config = SignerGrantReplayStoreConfig(tmp_path/'nonce/state.json', tmp_path/'nonce',
        tmp_path/'water/state.sqlite3', tmp_path/'water', tmp_path/'repo',
        'sha256:'+'a'*64, 'synthetic-consensus', 'sha256:'+'b'*64)
    config.repo_root.mkdir()
    return config


def open_store(config):
    high = SqliteMonotonicAuthorityStore(config.high_water_path, allowed_root=config.high_water_root,
        repo_root=config.repo_root, store_id=config.replay_store_id,
        durability_receipt_id=config.durability_receipt_id, require_existing=True)
    return AtomicProposalAuthenticityNonceStore(config.nonce_path, allowed_root=config.nonce_root,
        repo_root=config.repo_root, integrity_key=support.stores.INTEGRITY_KEY,
        replay_store_binding_digest=config.replay_store_binding_digest, high_water_store=high)


def test_existing_state_is_checked_without_reserving(tmp_path):
    config = configured(tmp_path)
    support.provision(config)
    before = config.nonce_path.read_bytes()
    open_store(config).validate_existing_state()
    assert config.nonce_path.read_bytes() == before


@pytest.mark.parametrize('damage', ['missing', 'empty', 'corrupt', 'foreign_water'])
def test_existing_state_rejects_missing_or_unauthenticated_state(tmp_path, damage):
    config = configured(tmp_path)
    support.provision(config)
    if damage == 'missing': config.nonce_path.unlink()
    elif damage == 'empty': config.nonce_path.write_bytes(b'{}')
    elif damage == 'corrupt': config.nonce_path.write_bytes(b'{invalid')
    else:
        config.high_water_path.unlink()
        SqliteMonotonicAuthorityStore(config.high_water_path, allowed_root=config.high_water_root,
            repo_root=config.repo_root, store_id=config.replay_store_id,
            durability_receipt_id=config.durability_receipt_id)
    with pytest.raises((ValueError, OSError)):
        open_store(config).validate_existing_state()


def test_existing_state_recovers_only_authenticated_one_step_ahead(monkeypatch, tmp_path):
    import time
    config = configured(tmp_path)
    support.provision(config)
    store = open_store(config)
    advance = store._high_water_store.advance
    def fail(*args, **kwargs): raise RuntimeError('synthetic persistence interruption')
    monkeypatch.setattr(store._high_water_store, 'advance', fail)
    with pytest.raises(RuntimeError):
        store.reserve('fixture-crash', expires_at=int(time.time())+20, subject='fixture')
    before = config.nonce_path.read_bytes()
    monkeypatch.setattr(store._high_water_store, 'advance', advance)
    restarted = open_store(config)
    restarted.validate_existing_state()
    assert config.nonce_path.read_bytes() == before
    assert restarted.reserve('fixture-crash', expires_at=int(time.time())+20, subject='fixture') is None
