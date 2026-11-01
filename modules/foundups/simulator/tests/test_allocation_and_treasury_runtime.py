"""Runtime wiring tests for 012 allocation and pAVS treasury telemetry."""

from __future__ import annotations

from modules.foundups.agent_market.src.fam_daemon import FAMDaemon
from modules.foundups.simulator.config import SimulatorConfig
from modules.foundups.simulator.mesa_model import FoundUpsModel
import modules.foundups.simulator.mesa_model as mesa_model_module


def test_012_allocation_updates_state_and_emits_events(tmp_path, monkeypatch) -> None:
    """Allocation engine should execute against live pools and emit telemetry."""
    daemon = FAMDaemon(data_dir=tmp_path, heartbeat_interval_sec=60.0, auto_start=False)
    model = FoundUpsModel(
        config=SimulatorConfig(
            num_founder_agents=0,
            num_user_agents=1,
            seed=11,
            agent_action_probability=0.0,
            agent_cooldown_ticks=0,
        ),
        fam_daemon=daemon,
    )

    # Ensure a FoundUp exists and token pool is synced for allocation routing.
    ok, msg, foundup_id = model._fam_bridge.create_foundup(
        name="Allocation Runtime",
        owner_id="founder_0",
        token_symbol="ALOC",
    )
    assert ok, msg
    assert foundup_id is not None
    model._sync_token_econ_foundup_pools()

    account = model.token_economics.human_accounts["user_000"]
    assert account.ups_balance > 0

    # Force allocation branch execution deterministically.
    monkeypatch.setattr(mesa_model_module.random, "random", lambda: 0.0)
    model._simulate_012_allocations()

    assert model.allocation_engine.allocation_count > 0
    assert model.state_store.get_state().total_stakes > 0

    allocation_events = model.event_bus.get_events_by_type("ups_allocation_executed", limit=20)
    result_events = model.event_bus.get_events_by_type("ups_allocation_result", limit=20)
    assert allocation_events
    assert result_events
    assert any(evt.foundup_id == foundup_id for evt in result_events)


def test_demurrage_emits_treasury_separation_events(tmp_path) -> None:
    """Demurrage cycle should emit pAVS/network separation telemetry."""
    daemon = FAMDaemon(data_dir=tmp_path, heartbeat_interval_sec=60.0, auto_start=False)
    model = FoundUpsModel(
        config=SimulatorConfig(
            num_founder_agents=0,
            num_user_agents=1,
            seed=13,
            agent_action_probability=0.0,
            agent_cooldown_ticks=0,
        ),
        fam_daemon=daemon,
    )

    # Force one demurrage cycle.
    model._apply_demurrage_cycle()

    demurrage_events = model.event_bus.get_events_by_type("demurrage_cycle_completed", limit=10)
    treasury_events = model.event_bus.get_events_by_type("pavs_treasury_updated", limit=10)
    snapshot_events = model.event_bus.get_events_by_type("treasury_separation_snapshot", limit=10)

    assert demurrage_events
    assert treasury_events
    assert snapshot_events

    stats = model.get_stats()
    assert stats["pavs_treasury_ups"] >= 0
    assert stats["network_pool_ups"] >= 0


import copy
from decimal import Decimal
from fractions import Fraction

import pytest

from modules.foundups.simulator.adapters.metagpt_adapter import (
    AgentSpecialization, SwarmFoundUp,
)
from modules.foundups.simulator.economics.pool_distribution import ParticipantType
from modules.foundups.simulator.economics.token_economics import (
    AgentExecutionWallet, HumanUPSAccount, TokenEconomicsEngine,
)


class _Hooks:
    calls = 0

    def fail(self, *args, **kwargs):
        _Hooks.calls += 1
        raise AssertionError("numeric hook invoked")

    __float__ = __lt__ = __le__ = __gt__ = __ge__ = __eq__ = __ne__ = fail
    __add__ = __radd__ = __sub__ = __rsub__ = __format__ = fail


class _Int(_Hooks, int):
    pass


class _Float(_Hooks, float):
    pass


def _bad(kind):
    return {"negative-int": -1, "negative-float": -0.25,
            "nan": float("nan"), "inf": float("inf"), "negative-inf": -float("inf"),
            "true": True, "false": False, "text": "1.5", "none": None,
            "decimal": Decimal("1.5"), "fraction": Fraction(3, 2),
            "coercible": _Hooks(), "int-subclass": _Int(1),
            "float-subclass": _Float(1.5), "unsupported-int": 10**400}[kind]


def _fixture(entry):
    engine = swarm = None
    if entry == "engine":
        engine = TokenEconomicsEngine()
        human = engine.register_human("owner", initial_ups=100)
        wallet = engine.register_agent("worker", "owner")
    elif entry == "metagpt":
        swarm = SwarmFoundUp("project", "Project", "test")
        human = swarm.register_human("owner", ParticipantType.DU, initial_ups=100)
        wallet = swarm.register_agent("existing", AgentSpecialization.CODE, "owner", 0)
    else:
        human = HumanUPSAccount("owner", ups_balance=100)
        wallet = AgentExecutionWallet("worker", "owner")
    wallet.ups_balance = wallet.total_allocated = 0
    wallet.total_spent = 7
    wallet.policy_gates = {"allowed_ops": ["old"], "max_per_task": 2}
    return human, wallet, engine, swarm


def _state(parts):
    human, wallet, engine, swarm = parts
    registration = None if swarm is None else [swarm.human_participants,
        swarm.human_types, swarm.agent_wallets, swarm.agent_specializations,
        swarm.completed_tasks, swarm.work_this_epoch, swarm.total_work]
    return repr(copy.deepcopy([vars(human), vars(wallet),
                               None if engine is None else vars(engine), registration]))


def _call(entry, parts, amount, policy=None):
    human, wallet, engine, swarm = parts
    if entry == "wallet":
        return wallet.receive_allocation(amount, policy)
    if entry == "human":
        return human.allocate_to_agent(amount, wallet)
    if entry == "engine":
        return engine.human_allocates_to_agent("owner", "worker", amount, policy)
    return swarm.register_agent("new", AgentSpecialization.QUALITY, "owner", amount)


@pytest.mark.parametrize("entry", ["wallet", "human", "engine", "metagpt"])
@pytest.mark.parametrize("kind", ["negative-int", "negative-float", "nan", "inf",
    "negative-inf", "true", "false", "text", "none", "decimal", "fraction",
    "coercible", "int-subclass", "float-subclass", "unsupported-int"])
def test_allocation_invalid_amount_has_no_effects_or_numeric_hooks(entry, kind):
    parts = _fixture(entry)
    policy = {"allowed_ops": ["new"], "max_per_task": 1}
    before, policy_before = _state(parts), copy.deepcopy(policy)
    _Hooks.calls = 0
    with pytest.raises(ValueError):
        _call(entry, parts, _bad(kind), policy)
    assert _Hooks.calls == 0
    assert _state(parts) == before
    assert policy == policy_before


@pytest.mark.parametrize("entry,field", [
    ("human", "human"), ("engine", "human"), ("metagpt", "human"),
    ("wallet", "balance"), ("human", "balance"), ("engine", "balance"),
    ("wallet", "allocated"), ("human", "allocated"), ("engine", "allocated")])
@pytest.mark.parametrize("kind", ["negative-int", "nan", "inf", "true", "int-subclass", "unsupported-int"])
def test_allocation_invalid_participating_state_rejects_before_writes(entry, field, kind):
    parts = _fixture(entry)
    target, name = ((parts[0], "ups_balance") if field == "human" else
                    (parts[1], "ups_balance" if field == "balance" else "total_allocated"))
    setattr(target, name, _bad(kind))
    before = _state(parts)
    _Hooks.calls = 0
    with pytest.raises(ValueError):
        _call(entry, parts, 1, {"allowed_ops": ["new"]})
    assert _Hooks.calls == 0
    assert _state(parts) == before


@pytest.mark.parametrize("entry", ["wallet", "human", "engine"])
@pytest.mark.parametrize("field", ["ups_balance", "total_allocated"])
def test_allocation_float_result_overflow_has_no_partial_credit_or_debit(entry, field):
    parts = _fixture(entry)
    parts[0].ups_balance = 1.7e308
    setattr(parts[1], field, 1.7e308)
    before = _state(parts)
    with pytest.raises(ValueError):
        _call(entry, parts, 1e308, {"allowed_ops": ["new"]})
    assert _state(parts) == before


@pytest.mark.parametrize("entry", ["wallet", "human", "engine"])
def test_allocation_unsupported_integer_result_has_no_partial_effect(entry):
    parts = _fixture(entry)
    amount = 1 << 1023
    parts[0].ups_balance = amount
    parts[1].ups_balance = parts[1].total_allocated = amount
    before = _state(parts)
    with pytest.raises(ValueError):
        _call(entry, parts, amount)
    assert _state(parts) == before


@pytest.mark.parametrize("entry", ["wallet", "human", "engine", "metagpt"])
@pytest.mark.parametrize("amount", [0, -0.0, 0.25, 3, 9007199254740993, 1e100])
def test_allocation_valid_math_returns_and_unrelated_fields_preserved(entry, amount):
    parts = _fixture(entry)
    human, wallet, engine, swarm = parts
    human.ups_balance = 2 * amount + 20
    original_human, original_wallet = copy.deepcopy(vars(human)), copy.deepcopy(vars(wallet))
    before_balance = human.ups_balance
    result = _call(entry, parts, amount)
    receiver = result if entry == "metagpt" else wallet
    if entry == "wallet":
        assert result is None
    elif entry == "metagpt":
        assert type(result) is AgentExecutionWallet
    else:
        assert result is True
    assert human.ups_balance == (before_balance if entry == "wallet" else before_balance - amount)
    expected_credit = 0.0 + amount if entry == "metagpt" else 0 + amount
    assert receiver.ups_balance == expected_credit and receiver.total_allocated == expected_credit
    if entry != "metagpt" and type(amount) is int:
        assert type(receiver.ups_balance) is int and type(receiver.total_allocated) is int
    assert {k: v for k, v in vars(human).items() if k != "ups_balance"} == {k: v for k, v in original_human.items() if k != "ups_balance"}
    if entry != "metagpt":
        assert {k: v for k, v in vars(wallet).items() if k not in ("ups_balance", "total_allocated")} == {k: v for k, v in original_wallet.items() if k not in ("ups_balance", "total_allocated")}
    else:
        assert swarm.agent_wallets["new"] is result
        assert swarm.agent_specializations["new"] is AgentSpecialization.QUALITY
        assert vars(wallet) == original_wallet


@pytest.mark.parametrize("entry", ["wallet", "engine"])
@pytest.mark.parametrize("policy", [None, {}, {"allowed_ops": ["new"], "max_per_task": 1}])
def test_allocation_zero_and_policy_installation_remain_compatible(entry, policy):
    policy = copy.deepcopy(policy)
    parts = _fixture(entry)
    assert _call(entry, parts, 0, policy) is (None if entry == "wallet" else True)
    expected = {"allowed_ops": ("new",), "max_per_task": 1} if policy else {"allowed_ops": ("old",), "max_per_task": 2}
    assert dict(parts[1].policy_gates) == expected
    if policy:
        policy["allowed_ops"].append("drain")
        assert not parts[1]._policy_allows("drain", 0)


@pytest.mark.parametrize("entry", ["wallet", "engine"])
@pytest.mark.parametrize("policy", [{"max_per_task": True}, {"allowed_ops": "build"}, {"unknown": 1}])
def test_allocation_invalid_policy_leaves_numeric_and_installed_state_unchanged(entry, policy):
    parts = _fixture(entry)
    before, original_policy = _state(parts), copy.deepcopy(policy)
    with pytest.raises(ValueError):
        _call(entry, parts, 1, policy)
    assert _state(parts) == before and policy == original_policy


@pytest.mark.parametrize("entry", ["human", "engine"])
def test_allocation_insufficient_funds_has_no_effects(entry):
    parts = _fixture(entry)
    before = _state(parts)
    assert _call(entry, parts, 101, {"allowed_ops": ["new"]}) is False
    assert _state(parts) == before


@pytest.mark.parametrize("lookup", ["missing-human", "missing-wallet", "wrong-allocator"])
def test_allocation_engine_lookup_precedence_is_unchanged(lookup):
    parts = _fixture("engine")
    human, wallet, engine, swarm = parts
    owner_id, agent_id = "owner", "worker"
    if lookup == "missing-human":
        owner_id = "absent"
    elif lookup == "missing-wallet":
        agent_id = "absent"
    else:
        wallet.allocator_id = "different"
    before = _state(parts)
    _Hooks.calls = 0
    assert engine.human_allocates_to_agent(owner_id, agent_id, _Hooks(), {"unknown": 1}) is False
    assert _Hooks.calls == 0 and _state(parts) == before


def test_allocation_metagpt_unknown_owner_precedes_budget_and_preserves_registries():
    parts = _fixture("metagpt")
    before = _state(parts)
    _Hooks.calls = 0
    with pytest.raises(ValueError, match="Owner"):
        parts[3].register_agent("new", AgentSpecialization.CODE, "absent", _Hooks())
    assert _Hooks.calls == 0 and _state(parts) == before


def test_allocation_metagpt_valid_insufficient_still_registers_zero_wallet():
    parts = _fixture("metagpt")
    human_before, wallet_before = copy.deepcopy(vars(parts[0])), copy.deepcopy(vars(parts[1]))
    result = _call("metagpt", parts, 101)
    assert type(result) is AgentExecutionWallet
    assert result.ups_balance == result.total_allocated == result.total_spent == 0
    assert parts[3].agent_wallets["new"] is result
    assert parts[3].agent_specializations["new"] is AgentSpecialization.QUALITY
    assert vars(parts[0]) == human_before and vars(parts[1]) == wallet_before


@pytest.mark.parametrize("entry", ["human", "engine"])
def test_allocation_repeated_valid_calls_preserve_transfer_math_without_new_fee(entry):
    parts = _fixture(entry)
    for _ in range(3):
        assert _call(entry, parts, 7) is True
    assert parts[0].ups_balance == 79
    assert parts[1].ups_balance == parts[1].total_allocated == 21
    assert parts[1].total_spent == 7


@pytest.mark.parametrize("entry", ["wallet", "human", "engine"])
def test_allocation_does_not_newly_validate_or_change_nonparticipating_fields(entry):
    parts = _fixture(entry)
    parts[0].total_allocated = -1
    parts[1].total_spent = None
    assert _call(entry, parts, 1) is (None if entry == "wallet" else True)
    assert parts[0].total_allocated == -1 and parts[1].total_spent is None


from copy import deepcopy
from types import SimpleNamespace
from modules.foundups.simulator.economics.fi_orderbook import EntryProtectionConfig, OrderBookManager, OrderStatus
from modules.foundups.simulator.economics.allocation_engine import AllocationEngine, AllocationPath


def _b11_allocator():
    manager = OrderBookManager(entry_protection_config=EntryProtectionConfig(enabled=False))
    pool = SimpleNamespace(remaining_mintable=0, available_supply=100)
    engine = AllocationEngine(SimpleNamespace(foundup_pools={"f": pool}), manager)
    return engine, manager.get_or_create_book("f")


@pytest.mark.parametrize("partial", [False, True])
def test_b11_actual_allocator_reports_only_completed_notional_when_cancelled(partial):
    engine, book = _b11_allocator()
    if partial:
        external, _ = book.place_sell_order("external", 5, 2)
    maker, _ = book.place_sell_order("same", 5, 10)
    # Two equal-price ordinary asks: this fixture root is external, not a FIFO promise.
    assert book.sell_orders[0] is (external if partial else maker)
    maker_before = deepcopy(vars(maker))
    batch = engine.allocate_fixed("same", 25, {"f": 1.0})
    result, = batch.results
    order = book.all_orders[result.order_id]
    assert order.status is OrderStatus.CANCELLED and order.rejection_reason == "self_trade_prevention"
    assert result.path is (AllocationPath.DEX_BUY if partial else AllocationPath.FAILED)
    assert (result.ups_allocated, result.fi_received, result.fee_paid) == pytest.approx((10, 2, .2) if partial else (0, 0, 0))
    assert "cancel" in result.message.lower() and "pending" not in result.message.lower()
    assert batch.pending_orders == [] and batch.success_count == int(partial)
    assert (batch.total_fi_received, batch.total_fees) == pytest.approx((2, .2) if partial else (0, 0))
    assert (engine.total_allocated_ups, engine.total_fi_acquired) == pytest.approx((10, 2) if partial else (0, 0))
    assert engine.allocation_count == 1 and vars(maker) == maker_before
    assert book.buy_orders == [] and book.sell_orders == [maker]


@pytest.mark.parametrize("partial", [False, True])
def test_b11_actual_allocator_live_open_and_partial_paths_stay_compatible(partial):
    engine, book = _b11_allocator()
    if partial:
        book.place_sell_order("external", 5, 2)
    batch = engine.allocate_fixed("same", 25, {"f": 1.0})
    result, = batch.results
    assert result.path is (AllocationPath.DEX_BUY if partial else AllocationPath.DEX_PENDING)
    assert result.ups_allocated == 25 and result.fi_received == (2 if partial else 0)
    assert result.fee_paid == pytest.approx(.2 if partial else 0)
    order = book.all_orders[result.order_id]
    assert order.status is (OrderStatus.PARTIAL if partial else OrderStatus.OPEN)
    assert order.rejection_reason is None and book.buy_orders == [order]
    assert batch.pending_orders == ([] if partial else [result])
    assert engine.total_allocated_ups == 25 and engine.allocation_count == 1
    if partial:
        assert "pending" in result.message.lower()
