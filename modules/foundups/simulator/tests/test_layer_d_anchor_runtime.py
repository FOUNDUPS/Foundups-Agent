"""Runtime wiring tests for epoch ledger and Layer-D anchoring."""

from __future__ import annotations

import pytest
from types import SimpleNamespace

from modules.foundups.simulator.config import SimulatorConfig
from modules.foundups.simulator.economics.pool_distribution import (
    ActivityLevel,
    ParticipantType,
)
from modules.foundups.simulator.mesa_model import FoundUpsModel


def _prime_epoch_distribution_inputs(model: FoundUpsModel) -> None:
    """Ensure pool distribution has participants + stake base."""
    model.pool_distributor.register_participant(
        participant_id="anchor_participant_001",
        p_type=ParticipantType.UN,
        activity=ActivityLevel.UN,
    )
    model.state_store.get_state().total_stakes = 10_000


def test_layer_d_anchor_publishes_on_configured_cadence(tmp_path) -> None:
    """Anchor should publish only on configured epoch cadence."""
    model = FoundUpsModel(
        config=SimulatorConfig(
            num_founder_agents=0,
            num_user_agents=0,
            seed=17,
            agent_action_probability=0.0,
            layer_d_anchor_enabled=True,
            layer_d_anchor_every_n_epochs=2,
            layer_d_anchor_mode="mock",
            layer_d_anchor_db_path=str(tmp_path / "anchor_state.db"),
        )
    )
    _prime_epoch_distribution_inputs(model)

    for _ in range(3):
        model._apply_demurrage_cycle()

    stats = model.get_stats()
    assert stats["epochs_completed"] == 3
    assert stats["layer_d_anchor_enabled"] is True
    assert stats["layer_d_anchor_total_published"] == 1
    assert len(model._epoch_ledger.entries) == 3

    assert model._anchor_connector is not None
    records = model._anchor_connector.get_anchor_status("F_0")
    assert len(records) == 1
    assert records[0]["epoch"] == 2
    assert records[0]["status"] == "published"


def test_layer_d_anchor_disabled_records_epoch_without_publish() -> None:
    """Ledger recording should still happen when Layer-D publish is disabled."""
    model = FoundUpsModel(
        config=SimulatorConfig(
            num_founder_agents=0,
            num_user_agents=0,
            seed=23,
            agent_action_probability=0.0,
            layer_d_anchor_enabled=False,
        )
    )
    _prime_epoch_distribution_inputs(model)

    model._apply_demurrage_cycle()

    stats = model.get_stats()
    assert stats["epochs_completed"] == 1
    assert stats["layer_d_anchor_enabled"] is False
    assert stats["layer_d_anchor_total_published"] == 0
    assert len(model._epoch_ledger.entries) == 1


@pytest.mark.parametrize("selected", ["unknown", "", None, 1, "testnet", "mainnet"])
def test_layer_d_selected_mode_never_falls_back_to_mock(tmp_path, selected):
    config = SimpleNamespace(layer_d_anchor_enabled=True, layer_d_anchor_mode=selected,
        layer_d_anchor_db_path=str(tmp_path / "unused" / "anchor.db"))
    model = SimpleNamespace(_config=config)
    with pytest.raises(ValueError):
        FoundUpsModel._build_anchor_connector(model)
    assert not (tmp_path / "unused").exists()


# A07/B02 frozen process-local replay/atomicity acceptance.
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from decimal import Decimal
from threading import Barrier, Event
from modules.foundups.simulator.economics import epoch_ledger as lm
from modules.foundups.simulator.economics import pool_distribution as pm
from modules.foundups.simulator.economics.epoch_ledger import EpochLedger
from modules.foundups.simulator.economics.pool_distribution import (
    PoolDistributor, ParticipantType as PT, ActivityLevel as AL, StakerPosition)
from modules.foundups.agent_market.src.fam_daemon import FAMDaemon
from modules.foundups.simulator.config import SimulatorConfig
from modules.foundups.simulator.mesa_model import FoundUpsModel


def _a07_pool(ledger=None):
    pool = PoolDistributor() if ledger is None else PoolDistributor(ledger=ledger)
    p = pool.register_participant("alice", PT.DU, AL.DU,
        staker_position=StakerPosition(original_stake_btc=0.001))
    return pool, p

def _a07_state(pool, ledger=None):
    people = {k: (id(p), int(p.activity_level), p.ups_balance,
        dict(p.foundup_tokens), None if p.staker_position is None else
        (id(p.staker_position), dict(vars(p.staker_position))))
        for k, p in pool.participants.items()}
    evidence = None if ledger is None else (
        [(e.to_dict(), dict(e.participant_rewards)) for e in ledger.entries],
        dict(ledger.merkle_roots), dict(ledger.merkle_trees))
    return deepcopy((pool.accumulated_fund, pool.total_drip_distributed,
                     people, evidence))

def _a07_mesa(tmp_path, anchor=False):
    daemon = FAMDaemon(data_dir=tmp_path / "fam", auto_start=False)
    model = FoundUpsModel(SimulatorConfig(num_founder_agents=0, num_user_agents=0,
        use_ai=False, seed=710007, agent_action_probability=0,
        layer_d_anchor_enabled=anchor,
        layer_d_anchor_db_path=str(tmp_path / "anchor.db")), fam_daemon=daemon)
    model.pool_distributor.register_participant("alice", PT.DU, AL.DU,
        staker_position=StakerPosition(original_stake_btc=0.001))
    model.state_store.get_state().total_stakes = 10000
    return model, daemon

def test_a18_mesa_failed_tail_retries_same_identity_without_repeating_decay(tmp_path, monkeypatch):
    model, _ = _a07_mesa(tmp_path)
    model._demurrage.register_wallet("budget", 1000)
    before = _a07_state(model.pool_distributor, model._epoch_ledger)
    with monkeypatch.context() as m:
        m.setattr(lm, "_build_tree", lambda *a: (_ for _ in ()).throw(RuntimeError("tree")))
        with pytest.raises(RuntimeError): model._apply_demurrage_cycle()
    assert _a07_state(model.pool_distributor, model._epoch_ledger) == before
    assert model._epoch_counter == 0
    decayed = model._demurrage.total_decayed
    assert decayed > 0
    model._apply_demurrage_cycle()
    assert model._demurrage.total_decayed == decayed
    assert model._epoch_counter == 1 and len(model._epoch_ledger.entries) == 1
    assert model._epoch_ledger.verify_chain()

def test_a19_mesa_postcommit_observer_failure_is_one_attempt_not_abort(tmp_path, monkeypatch):
    model, daemon = _a07_mesa(tmp_path)
    captured, attempts = [], []
    distribute = model.pool_distributor.distribute_epoch
    def capture(*args, **kwargs):
        result = distribute(*args, **kwargs)
        captured.append(result)
        return result
    monkeypatch.setattr(model.pool_distributor, "distribute_epoch", capture)
    emit = daemon.emit
    def observe(*args, **kwargs):
        kind = kwargs.get("event_type", args[0] if args else None)
        if kind == "epoch_ledger_recorded":
            attempts.append(kind)
            raise RuntimeError("observer")
        return emit(*args, **kwargs)
    monkeypatch.setattr(daemon, "emit", observe)
    model._apply_demurrage_cycle()
    assert model._epoch_counter == 1 and len(model._epoch_ledger.entries) == 1
    before = _a07_state(model.pool_distributor, model._epoch_ledger)
    model._record_epoch_distribution(captured[0])
    assert attempts == ["epoch_ledger_recorded"] and _a07_state(model.pool_distributor, model._epoch_ledger) == before

def test_a20_mesa_known_finalized_retry_does_not_republish_anchor(tmp_path, monkeypatch):
    model, _ = _a07_mesa(tmp_path, anchor=True)
    captured, attempts = [], []
    distribute = model.pool_distributor.distribute_epoch
    publish = model._anchor_connector.publish_commitment
    def capture(*args, **kwargs):
        result = distribute(*args, **kwargs)
        captured.append(result)
        return result
    def observe(*args, **kwargs):
        attempts.append(1)
        return publish(*args, **kwargs)
    monkeypatch.setattr(model.pool_distributor, "distribute_epoch", capture)
    monkeypatch.setattr(model._anchor_connector, "publish_commitment", observe)
    model._apply_demurrage_cycle()
    before = _a07_state(model.pool_distributor, model._epoch_ledger)
    model._record_epoch_distribution(captured[0])
    assert attempts == [1] and _a07_state(model.pool_distributor, model._epoch_ledger) == before


def test_existing_epoch_record_callback_returns_none(tmp_path, monkeypatch):
    model = FoundUpsModel(SimulatorConfig(num_founder_agents=0, num_user_agents=0,
        use_ai=False, seed=17, agent_action_probability=0),
        fam_daemon=FAMDaemon(data_dir=tmp_path / "fam", auto_start=False))
    model.pool_distributor.register_participant("alice", ParticipantType.UN, ActivityLevel.DU)
    model.state_store.get_state().total_stakes = 10000
    captured = []
    distribute = model.pool_distributor.distribute_epoch
    def capture(*args, **kwargs):
        result = distribute(*args, **kwargs)
        captured.append(result)
        return result
    monkeypatch.setattr(model.pool_distributor, "distribute_epoch", capture)
    model._apply_demurrage_cycle()
    assert model._record_epoch_distribution(captured[0]) is None
