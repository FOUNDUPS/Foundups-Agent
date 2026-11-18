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


# Exact-native source-backed simulation; no live funding authority.
from copy import deepcopy
from fractions import Fraction
from random import Random
import pytest
from modules.foundups.agent_market.src.fam_daemon import FAMDaemon
from modules.foundups.simulator.config import SimulatorConfig
from modules.foundups.simulator.mesa_model import FoundUpsModel
from modules.foundups.simulator.economics.pool_distribution import (
    PoolDistributor, ParticipantType as PT, ActivityLevel as AL, StakerPosition)
from modules.foundups.simulator.economics import epoch_ledger as lm

MODE = "sim_native_epoch_transfer_v1"


def _model(path, mode=MODE, explicit=True):
    options = dict(num_founder_agents=0, num_user_agents=0, use_ai=False, seed=710007,
        agent_action_probability=0, layer_d_anchor_enabled=False)
    if explicit:
        options["epoch_funding_mode"] = mode
    daemon = FAMDaemon(data_dir=path / "fam", auto_start=False)
    return FoundUpsModel(SimulatorConfig(**options), fam_daemon=daemon)


def _setup(model, source=10000.0, opening=0, cohort="full9", position=None):
    pool = model.pool_distributor
    people = [(pt, al) for pt in PT for al in AL] if cohort == "full9" else [
        (PT.DU, AL.DU) if cohort == "du" else (PT.UN, AL.UN)]
    for i, (pt, al) in enumerate(people):
        pool.register_participant("p" + str(i), pt, al, staker_position=position).ups_balance = opening
    model._demurrage.pavs_treasury_balance = source
    return pool


def _money(model):
    p = model.pool_distributor
    return model._demurrage.pavs_treasury_balance, {k: v.ups_balance for k, v in p.participants.items()}, p.accumulated_fund


def _state(model):
    p, ledger = model.pool_distributor, model._epoch_ledger
    cache = {epoch: (amount, context, {**vars(r), "participant_rewards": dict(r.participant_rewards)},
        None if entry is None else (id(entry), entry.to_dict(), dict(entry.participant_rewards)))
        for epoch, (amount, context, r, entry) in p._epochs.items()}
    value = model._demurrage.pavs_treasury_balance
    scalar = (type(value).__name__, repr(value)) if type(value) in (int, float, bool) else (type(value).__name__, id(value))
    return _a07_state(p, ledger), deepcopy(cache), scalar, dict(p._funding._settlements)


def _conserved(model, before, receipt):
    source, people, fund = before
    pool = model.pool_distributor
    gains = {k: Fraction(v.ups_balance) - Fraction(people[k]) for k, v in pool.participants.items()}
    assert gains == {k: Fraction(receipt.participant_rewards.get(k, 0)) for k in people}
    fund_gain = Fraction(pool.accumulated_fund) - Fraction(fund)
    assert fund_gain == Fraction(receipt.fund_pool)
    posted = sum(gains.values(), Fraction()) + fund_gain
    assert 0 <= posted <= Fraction(receipt.total_rewards)
    assert Fraction(source) - Fraction(model._demurrage.pavs_treasury_balance) == posted
    assert all(type(v) in (int, float) for v in (*[p.ups_balance for p in pool.participants.values()],
        pool.accumulated_fund, pool.total_drip_distributed, model._demurrage.pavs_treasury_balance))


def test_funded_model_binds_fresh_real_source_pool_and_ledger(tmp_path):
    model = _model(tmp_path)
    pool = model.pool_distributor
    funding = pool._funding
    assert funding._source is model._demurrage and funding._ledger is model._epoch_ledger
    assert funding._pool is pool and type(funding._liabilities) is tuple and funding._liabilities == ()
    assert funding._settlements == {} and model._demurrage.pavs_treasury_balance == 0
    assert not model._demurrage.wallets and not model._epoch_ledger.entries


@pytest.mark.parametrize("mode", [None, True, "unknown"], ids=["none", "bool", "unknown"])
def test_unknown_funding_mode_refuses(tmp_path, mode):
    with pytest.raises(ValueError):
        _model(tmp_path, mode)


def test_default_legacy_model_preserves_unfunded_pool_behavior(tmp_path):
    model = _model(tmp_path, explicit=False)
    pool = _setup(model, source=0)
    result = pool.distribute_epoch(1, 3750)
    assert getattr(pool, "_funding", None) is None
    assert model._demurrage.pavs_treasury_balance == 0 and pool.accumulated_fund == 150
    assert result.participant_rewards["p0"] == 38


@pytest.mark.parametrize("reward,source,opening", [(0, 0.0, 0), (3750, 3750.0, 0), (1875, 10000.0, 1.25),
    (468.75, 10000.0, 1.25), (29.296875, 10000.0, 1.25),
    (480000, 1152921504606846976.0, 0)], ids=["zero", "whole", "half", "eighth", "small_dyadic", "large_exact"])
def test_useful_exact_native_cohorts_transfer_once(tmp_path, reward, source, opening):
    model = _model(tmp_path)
    pool = _setup(model, source, opening)
    before = _money(model)
    result = pool.distribute_epoch(1, reward)
    _conserved(model, before, result)
    assert len(model._epoch_ledger.entries) == len(pool._funding._settlements) == 1
    assert model._epoch_ledger.verify_chain()


def test_successive_fractional_epochs_preserve_actual_nonzero_books(tmp_path):
    model = _model(tmp_path)
    pool = _setup(model)
    for epoch, reward in enumerate((3750, 1875, 468.75), 1):
        before = _money(model)
        _conserved(model, before, pool.distribute_epoch(epoch, reward))
    assert model._demurrage.pavs_treasury_balance == 3906.25
    assert pool.participants["p0"].ups_balance == 61.75 and pool.accumulated_fund == 243.75


@pytest.mark.parametrize("source", [0.0, 1000.0], ids=["zero", "net_only"])
def test_full_nominal_budget_refuses_even_when_net_credit_is_smaller(tmp_path, source):
    model = _model(tmp_path)
    pool = _setup(model, source=source, cohort="single")
    before = _state(model)
    with pytest.raises(ValueError):
        pool.distribute_epoch(1, 3750)
    assert _state(model) == before


def test_unallocated_empty_tier_shares_remain_source_owned(tmp_path):
    model = _model(tmp_path)
    pool = _setup(model, source=4000.0, cohort="single")
    before = _money(model)
    result = pool.distribute_epoch(1, 3750)
    _conserved(model, before, result)
    assert result.participant_rewards == {"p0": 114} and pool.accumulated_fund == 150
    assert model._demurrage.pavs_treasury_balance == 3736 and len(pool.participants) == 1


@pytest.mark.parametrize("kind", ["decimal", "seed", "partial", "source", "fund", "drip", "local", "hurdle"])
def test_native_loss_at_any_required_component_refuses_without_effects(tmp_path, kind):
    model = _model(tmp_path)
    reward = {"decimal": 0.1, "seed": 10000, "partial": 400, "local": 100}.get(kind, 3750)
    cohort = "du" if kind in ("local", "hurdle") else "single" if kind in ("seed", "partial") else "full9"
    position = StakerPosition(original_stake_btc=10**15, cumulative_distributions_btc=float(2**53)) if kind == "hurdle" else None
    opening = 0.1 if kind == "seed" else float(2**53) if kind == "partial" else 0
    pool = _setup(model, source=float(2**60) if kind == "source" else 20000.0,
        opening=opening, cohort=cohort, position=position)
    if kind == "fund":
        pool.accumulated_fund = float(2**60)
    if kind == "drip":
        pool.total_drip_distributed = float(2**60)
    before = _state(model)
    with pytest.raises(ValueError):
        pool.distribute_epoch(1, reward)
    assert _state(model) == before


@pytest.mark.parametrize("kind", ["bool", "nan", "rational", "hostile", "oversized"])
def test_invalid_source_state_refuses_without_numeric_hooks(tmp_path, kind):
    class Hostile:
        def __float__(self):
            raise AssertionError("numeric hook")
    bad = {"bool": True, "nan": float("nan"), "rational": Fraction(1, 2),
           "hostile": Hostile(), "oversized": 1 << 1024}[kind]
    model = _model(tmp_path)
    pool = _setup(model, source=bad)
    before = _state(model)
    with pytest.raises(ValueError):
        pool.distribute_epoch(1, 3750)
    assert _state(model) == before and model._demurrage.pavs_treasury_balance is bad


@pytest.mark.parametrize("liability", [None, ("pending",), ("ambiguous",), 0, []],
    ids=["unknown", "pending", "ambiguous", "number", "empty_list"])
def test_nonempty_or_unknown_liability_holds_new_epochs_but_not_saved_late_replay(tmp_path, liability):
    model = _model(tmp_path)
    pool = _setup(model)
    first = pool.distribute_epoch(1, 3750)
    pool.distribute_epoch(3, 1875)
    pool._funding._liabilities = liability
    before = _state(model)
    with pytest.raises(ValueError):
        pool.distribute_epoch(4, 468.75)
    again = pool.distribute_epoch(1, 3750)
    assert vars(again) == vars(first) and again is not first and _state(model) == before
    assert pool._funding._liabilities is liability


def test_saved_exact_replay_does_not_reread_current_invalid_source(tmp_path):
    model = _model(tmp_path)
    pool = _setup(model)
    first = pool.distribute_epoch(1, 3750)
    model._demurrage.pavs_treasury_balance = float("nan")
    before = _state(model)
    assert vars(pool.distribute_epoch(1, 3750)) == vars(first)
    assert _state(model) == before


@pytest.mark.parametrize("change", ["amount", "context"])
def test_conflicting_epoch_does_not_debit_or_replace_funded_record(tmp_path, change):
    model = _model(tmp_path)
    pool = _setup(model)
    pool.distribute_epoch(1, 3750)
    before = _state(model)
    with pytest.raises(ValueError):
        pool.distribute_epoch(1, 3751 if change == "amount" else 3750,
            "other" if change == "context" else None)
    assert _state(model) == before


def test_ledger_only_evidence_is_not_source_consumption(tmp_path):
    model = _model(tmp_path)
    pool = _setup(model)
    model._epoch_ledger.record_epoch(1, 3750, {"fund": 150}, {"p0": 38})
    before = _state(model)
    with pytest.raises(ValueError):
        pool.distribute_epoch(1, 3750)
    assert _state(model) == before


def test_tree_preparation_failure_leaves_source_and_settlement_unpublished(tmp_path, monkeypatch):
    model = _model(tmp_path)
    pool = _setup(model)
    before = _state(model)
    def fail(*args):
        raise RuntimeError("tree_abort")
    with monkeypatch.context() as patch:
        patch.setattr(lm, "_build_tree", fail)
        with pytest.raises(RuntimeError):
            pool.distribute_epoch(1, 3750)
    assert _state(model) == before
    before_money = _money(model)
    _conserved(model, before_money, pool.distribute_epoch(1, 3750))


def test_real_mesa_failed_tail_keeps_request_and_does_not_repeat_decay(tmp_path):
    model = _model(tmp_path)
    pool = _setup(model, source=1000.0)
    model.state_store.get_state().total_stakes = 375000
    model._demurrage.register_wallet("budget", 1000)
    before = _a07_state(pool, model._epoch_ledger)
    with pytest.raises(ValueError):
        model._apply_demurrage_cycle()
    assert _a07_state(pool, model._epoch_ledger) == before and not pool._funding._settlements
    assert model._epoch_counter == 0 and model._epoch_tail._pending == (1, 3750.0)
    decayed = model._demurrage.total_decayed
    assert decayed > 0
    model._demurrage.pavs_treasury_balance = 10000.0
    model.state_store.get_state().total_stakes = 750000
    model._apply_demurrage_cycle()
    assert model._demurrage.total_decayed == decayed and model._epoch_counter == 1
    assert model._epoch_ledger.entries[0].total_fi_distributed == 3750
    assert model._demurrage.pavs_treasury_balance == 6250 and model._epoch_tail._pending is None


def test_postcommit_observer_failure_cannot_repeat_source_debit(tmp_path, monkeypatch):
    model = _model(tmp_path)
    pool = _setup(model, source=4000.0)
    model.state_store.get_state().total_stakes = 375000
    daemon = model._fam_bridge.get_daemon()
    original, attempts = daemon.emit, []
    def emit(*args, **kwargs):
        if kwargs.get("event_type", args[0] if args else None) == "epoch_ledger_recorded":
            attempts.append("epoch")
            raise RuntimeError("observer_abort")
        return original(*args, **kwargs)
    monkeypatch.setattr(daemon, "emit", emit)
    model._apply_demurrage_cycle()
    assert model._demurrage.pavs_treasury_balance == 250 and model._epoch_counter == 1
    before = _state(model)
    model._record_epoch_distribution(pool.distribute_epoch(1, 3750))
    assert attempts == ["epoch"] and _state(model) == before


@pytest.mark.parametrize("source", [6000.0, 4000.0], ids=["cross_healthy", "cross_critical"])
def test_actual_funded_mesa_debit_changes_existing_treasury_health_routing(tmp_path, source):
    model = _model(tmp_path)
    _setup(model, source=source)
    model.state_store.get_state().total_stakes = 375000
    before = model._demurrage.get_redistribution_ratios()[1]
    model._apply_demurrage_cycle()
    assert model._demurrage.pavs_treasury_balance == source - 3750
    assert model._demurrage.get_redistribution_ratios()[1] > before


@pytest.mark.parametrize("seed", [11, 29, 710007], ids=["seed11", "seed29", "seed710007"])
def test_seeded_dyadic_sequences_preserve_aggregate_assets_and_exact_replays(tmp_path, seed):
    model = _model(tmp_path)
    pool = _setup(model, source=4000.0)
    rng = Random(seed)
    for epoch in range(1, 33):
        reward = rng.choice((29.296875, 58.59375, 117.1875, 234.375, 468.75, 937.5, 1875, 3750))
        before, money = _state(model), _money(model)
        if Fraction(reward) > Fraction(money[0]):
            with pytest.raises(ValueError):
                pool.distribute_epoch(epoch, reward)
            assert _state(model) == before
        else:
            receipt = pool.distribute_epoch(epoch, reward)
            _conserved(model, money, receipt)
            committed = _state(model)
            replay = pool.distribute_epoch(epoch, reward)
            assert vars(replay) == vars(receipt) and replay is not receipt
            assert _state(model) == committed
        assets = Fraction(model._demurrage.pavs_treasury_balance) + Fraction(pool.accumulated_fund)
        assets += sum((Fraction(p.ups_balance) for p in pool.participants.values()), Fraction())
        assert assets == 4000


# Independent strict-builtin rejection control, frozen before execution.
import pytest
from modules.foundups.simulator._mesa_epoch import _build_epoch_pool
from modules.foundups.simulator.economics.btc_reserve import BTCReserve
from modules.foundups.simulator.economics.demurrage import DemurrageEngine
from modules.foundups.simulator.economics.epoch_ledger import EpochLedger
from modules.foundups.simulator.economics.pool_distribution import ActivityLevel, ParticipantType


def test_nonbuiltin_source_rejects_without_metaclass_equality_hook():
    calls = []
    class HostileMeta(type):
        def __eq__(cls, other):
            calls.append('eq')
            raise AssertionError('unsupported type equality hook invoked')
    class Unsupported(metaclass=HostileMeta):
        pass
    source = DemurrageEngine(btc_reserve=BTCReserve())
    ledger = EpochLedger('strict-source')
    pool = _build_epoch_pool('sim_native_epoch_transfer_v1', source, ledger)
    participant = pool.register_participant('p', ParticipantType.UN, ActivityLevel.UN)
    bad = Unsupported()
    source.pavs_treasury_balance = bad
    before = (participant.ups_balance, pool.accumulated_fund, pool.total_drip_distributed)
    try:
        with pytest.raises(ValueError):
            pool.distribute_epoch(1, 3750, 'strict-source')
    finally:
        assert source.pavs_treasury_balance is bad
        assert (participant.ups_balance, pool.accumulated_fund, pool.total_drip_distributed) == before
        assert not ledger.entries and not pool._epochs and not pool._funding._settlements
    assert calls == []


# Independent connected amount-validator rejection controls.
import pytest
from modules.foundups.simulator._mesa_epoch import _build_epoch_pool
from modules.foundups.simulator.economics.btc_reserve import BTCReserve
from modules.foundups.simulator.economics.demurrage import DemurrageEngine
from modules.foundups.simulator.economics.epoch_ledger import EpochLedger
from modules.foundups.simulator.economics.pool_distribution import ActivityLevel, ParticipantType


@pytest.mark.parametrize('location', ['nominal', 'balance'])
def test_funded_inputs_reject_without_metaclass_equality_hook(location):
    calls = []
    class HostileMeta(type):
        def __eq__(cls, other):
            calls.append('eq')
            raise AssertionError('unsupported type equality hook invoked')
    class Unsupported(metaclass=HostileMeta):
        pass
    source, ledger = DemurrageEngine(btc_reserve=BTCReserve()), EpochLedger('strict-input')
    pool = _build_epoch_pool('sim_native_epoch_transfer_v1', source, ledger)
    participant = pool.register_participant('p', ParticipantType.UN, ActivityLevel.UN)
    source.pavs_treasury_balance = 3750
    bad = Unsupported()
    if location == 'balance':
        participant.ups_balance = bad
    before = (source.pavs_treasury_balance, pool.accumulated_fund, pool.total_drip_distributed)
    try:
        with pytest.raises(ValueError):
            pool.distribute_epoch(1, bad if location == 'nominal' else 3750, 'strict-input')
    finally:
        assert (source.pavs_treasury_balance, pool.accumulated_fund, pool.total_drip_distributed) == before
        assert participant.ups_balance is bad if location == 'balance' else participant.ups_balance == 0
        assert not ledger.entries and not pool._epochs and not pool._funding._settlements
    assert calls == []
