"""Simulator alignment and tokenomics math validation tests."""

from __future__ import annotations

import pytest

from modules.foundups.agent_market.src.fam_daemon import FAMDaemon
from modules.foundups.simulator.config import SimulatorConfig
from modules.foundups.simulator.economics import (
    BondingCurveManager,
    InvestorPool,
    TokenEconomicsEngine,
    adoption_curve,
)
from modules.foundups.simulator.mesa_model import FoundUpsModel


def test_shared_daemon_drives_state_store_updates(tmp_path) -> None:
    """FoundUp events emitted by bridge must be visible in simulator state."""
    daemon = FAMDaemon(
        data_dir=tmp_path,
        heartbeat_interval_sec=60.0,
        auto_start=False,
    )
    config = SimulatorConfig(
        num_founder_agents=1,
        num_user_agents=0,
        seed=7,
        agent_action_probability=1.0,
        agent_cooldown_ticks=0,
        foundup_creation_cost=100,
    )
    model = FoundUpsModel(config=config, fam_daemon=daemon)
    for _ in range(12):
        model.step()

    state = model.state_store.get_state()
    created_events = model.event_bus.get_events_by_type("foundup_created", limit=20)

    assert len(created_events) > 0
    assert state.total_foundups > 0


def test_adoption_curve_bounds() -> None:
    assert adoption_curve(0.0) == pytest.approx(0.0, abs=1e-12)
    assert adoption_curve(1.0) == pytest.approx(1.0, abs=1e-12)
    assert 0.0 <= adoption_curve(0.5) <= 1.0


def test_foundup_mint_respects_available_supply_cap() -> None:
    engine = TokenEconomicsEngine()
    engine.register_human("h1", initial_ups=1000.0)
    engine.register_agent("a1", "h1")
    pool = engine.register_foundup("f1")
    pool.update_adoption(users=1500, revenue_ups=150000.0, work_completed=15000.0, milestone=True)

    minted_total = 0.0
    for _ in range(200):
        minted_total += pool.mint_for_work(1_000_000.0, "a1")

    assert minted_total == pytest.approx(pool.available_supply, rel=1e-9, abs=1e-6)
    assert minted_total <= pool.available_supply + 1e-6
    assert pool.remaining_mintable == pytest.approx(0.0, abs=1e-6)


def test_staking_roundtrip_fee_math() -> None:
    engine = TokenEconomicsEngine()
    engine.register_human("h1", initial_ups=1000.0)
    engine.register_foundup("f1")

    fi_received, entry_fee = engine.human_stakes_ups("h1", "f1", 200.0)
    ups_back, exit_fee = engine.human_unstakes_fi("h1", "f1", fi_received)

    assert fi_received == pytest.approx(194.0, abs=1e-9)  # 3% entry fee
    assert entry_fee == pytest.approx(6.0, abs=1e-9)
    assert ups_back == pytest.approx(184.3, abs=1e-9)  # 5% unstake fee on 194
    assert exit_fee == pytest.approx(9.7, abs=1e-9)
    assert 200.0 - ups_back == pytest.approx(15.7, abs=1e-9)


def test_bonding_curve_monotonic_price_direction() -> None:
    manager = BondingCurveManager()
    curve = manager.get_or_create_curve("f_curve", initial_ups=1000.0, initial_price=1.0)

    p0 = curve.get_spot_price()
    fi_out, _ = curve.buy(100.0, "buyer_1")
    p1 = curve.get_spot_price()
    curve.sell(fi_out * 0.2, "seller_1")
    p2 = curve.get_spot_price()

    assert p1 > p0
    assert p2 < p1


def test_investor_pool_early_entry_advantage() -> None:
    pool = InvestorPool()
    first_tokens, _ = pool.invest_btc("seed", 1.0)
    second_tokens, _ = pool.invest_btc("early", 1.0)

    assert first_tokens > second_tokens
    seed_returns = pool.get_investor_returns("seed")
    assert seed_returns["price_return_multiple"] > 1.0


def test_numeric_valid_integer_cost_keeps_existing_float_policy_normalization():
    engine = TokenEconomicsEngine()
    engine.register_human("owner", initial_ups=1e20)
    wallet = engine.register_agent("worker", allocator_id="owner")
    engine.register_foundup("project")
    assert engine.human_allocates_to_agent("owner", "worker", 1e19)
    wallet.policy_gates = {"max_per_task": 2**53}
    success, earned = engine.agent_completes_task("worker", "project", 2**53 + 1, 1)
    assert success is True
    assert earned == 1.0
    assert wallet.total_spent == float(2**53 + 1)
    assert engine.human_accounts["owner"].foundup_tokens["project"] == 1.0



@pytest.mark.parametrize("operation", ["wallet", "engine-work"])
def test_numeric_total_debit_overflow_rejects_before_insufficient_funds(operation):
    engine = _numeric_engine()
    wallet = engine.agent_wallets["worker"]
    largest_float = float.fromhex("0x1.fffffffffffffp+1023")
    assert largest_float > wallet.ups_balance
    before = _numeric_snapshot(engine)
    with pytest.raises(ValueError):
        if operation == "wallet":
            wallet.spend(largest_float, "task:project")
        else:
            engine.agent_completes_task("worker", "project", largest_float, 1.0)
    assert _numeric_snapshot(engine) == before


@pytest.mark.parametrize("operation", ["pool-stake", "pool-unstake", "engine-stake", "engine-unstake"])
def test_numeric_positive_quantity_that_rounds_to_zero_net_rejects_before_effects(operation):
    engine = _numeric_engine(staked=True)
    pool = engine.foundup_pools["project"]
    amount = float.fromhex("0x0.0000000000001p-1022")
    rate = 0.9999999999999999
    assert amount > 0 and 0 <= rate < 1
    assert amount * rate == amount
    if operation == "engine-stake":
        engine.fee_config.staked_fi_entry_fee = rate
        action = lambda: engine.human_stakes_ups("owner", "project", amount)
    elif operation == "engine-unstake":
        engine.fee_config.staked_fi_exit_fee = rate
        action = lambda: engine.human_unstakes_fi("owner", "project", amount)
    elif operation == "pool-stake":
        action = lambda: pool.stake_ups(amount, "owner", rate)
    else:
        action = lambda: pool.unstake_fi(amount, "owner", rate)
    before = _numeric_snapshot(engine)
    with pytest.raises(ValueError):
        action()
    assert _numeric_snapshot(engine) == before



# Numeric admission stays in the existing tokenomics owner/test surface.
import copy
from decimal import Decimal

from modules.foundups.simulator.economics.token_economics import (
    AgentExecutionWallet,
    FeeConfig,
    FoundUpTokenPool,
    HumanUPSAccount,
)


_NUMERIC_INVALID_QUANTITIES = [
    pytest.param(-1.0, id="negative"),
    pytest.param(float("nan"), id="nan"),
    pytest.param(float("inf"), id="positive-infinity"),
    pytest.param(float("-inf"), id="negative-infinity"),
    pytest.param(True, id="true"),
    pytest.param(False, id="false"),
    pytest.param("1.5", id="coercible-text"),
    pytest.param(None, id="none"),
    pytest.param(Decimal("1.5"), id="decimal"),
    pytest.param(10**400, id="unrepresentable-integer"),
]


_NUMERIC_INVALID_RATES = [
    pytest.param(-0.1, id="negative"),
    pytest.param(float("nan"), id="nan"),
    pytest.param(float("inf"), id="positive-infinity"),
    pytest.param(float("-inf"), id="negative-infinity"),
    pytest.param(True, id="bool"),
    pytest.param("0.1", id="coercible-text"),
    pytest.param(None, id="none"),
    pytest.param(1.0, id="unsupported-full-fee"),
    pytest.param(1.1, id="over-one"),
]


def _numeric_snapshot(*objects):
    """Capture all participating state, including nested registries and NaNs."""
    return repr(copy.deepcopy([vars(obj) for obj in objects]))


def _numeric_engine(staked=False):
    engine = TokenEconomicsEngine()
    engine.register_human("owner", initial_ups=1000.0)
    engine.register_agent("worker", allocator_id="owner")
    engine.register_foundup("project")
    assert engine.human_allocates_to_agent("owner", "worker", 100.0)
    engine.foundup_pools["project"].adoption_score = 0.5
    if staked:
        assert engine.human_stakes_ups("owner", "project", 100.0) == (97.0, 3.0)
    return engine


def _numeric_operation(operation, amount):
    engine = _numeric_engine(staked=True)
    pool = FoundUpTokenPool(
        "direct", adoption_score=0.5, ups_treasury=100.0,
        staked_fi_outstanding=100.0,
    )
    wallet = AgentExecutionWallet("direct-worker", "owner", ups_balance=100.0)
    account = HumanUPSAccount("direct-owner", ups_balance=100.0)
    account.staked_positions["direct"] = 10.0
    calls = {
        "pool-mint": lambda: pool.mint_for_work(amount, "worker"),
        "pool-stake": lambda: pool.stake_ups(amount, "owner"),
        "pool-unstake": lambda: pool.unstake_fi(amount, "owner"),
        "adoption-work": lambda: pool.update_adoption(work_completed=amount),
        "engine-work-cost": lambda: engine.agent_completes_task("worker", "project", amount, 1.0),
        "engine-work-reward": lambda: engine.agent_completes_task("worker", "project", 1.0, amount),
        "engine-stake": lambda: engine.human_stakes_ups("owner", "project", amount),
        "engine-unstake": lambda: engine.human_unstakes_fi("owner", "project", amount),
        "wallet-spend": lambda: wallet.spend(amount, "task:direct"),
        "account-receive-fi": lambda: account.receive_fi("direct", amount),
        "account-record-stake-ups": lambda: account.record_stake("direct", amount, 1.0),
        "account-record-stake-fi": lambda: account.record_stake("direct", 1.0, amount),
        "account-record-unstake-fi": lambda: account.record_unstake("direct", amount, 1.0),
        "account-record-unstake-ups": lambda: account.record_unstake("direct", 1.0, amount),
    }
    return (engine, pool, wallet, account), calls[operation]


_NUMERIC_OPERATIONS = [
    "pool-mint", "pool-stake", "pool-unstake", "adoption-work",
    "engine-work-cost", "engine-work-reward", "engine-stake", "engine-unstake",
    "wallet-spend", "account-receive-fi", "account-record-stake-ups",
    "account-record-stake-fi", "account-record-unstake-fi",
    "account-record-unstake-ups",
]
_NUMERIC_INVALID_CASES = [
    pytest.param(operation, case.values[0], id=f"{operation}-{case.id}")
    for operation in _NUMERIC_OPERATIONS
    for case in _NUMERIC_INVALID_QUANTITIES
    if not (operation == "adoption-work" and case.values[0] is None)
]


@pytest.mark.parametrize("operation,amount", _NUMERIC_INVALID_CASES)
def test_numeric_invalid_quantity_rejects_before_any_participant_changes(operation, amount):
    objects, action = _numeric_operation(operation, amount)
    before = _numeric_snapshot(*objects)
    with pytest.raises(ValueError):
        action()
    assert _numeric_snapshot(*objects) == before


def test_numeric_optional_none_work_matches_existing_omitted_work_admission():
    explicit = FoundUpTokenPool("project", adoption_score=0.5, total_work_completed=3.0)
    omitted = FoundUpTokenPool("project", adoption_score=0.5, total_work_completed=3.0)
    explicit.update_adoption(users=10, work_completed=None)
    omitted.update_adoption(users=10)
    assert explicit.total_users == 10
    assert explicit.total_work_completed == 3.0
    assert _numeric_snapshot(explicit) == _numeric_snapshot(omitted)


@pytest.mark.parametrize("rate", _NUMERIC_INVALID_RATES)
@pytest.mark.parametrize("operation", ["pool-stake", "pool-unstake", "engine-stake", "engine-unstake"])
def test_numeric_invalid_mutable_fee_rejects_before_pool_or_owner_changes(operation, rate):
    engine = _numeric_engine(staked=True)
    pool = engine.foundup_pools["project"]
    if operation == "engine-stake":
        engine.fee_config.staked_fi_entry_fee = rate
        action = lambda: engine.human_stakes_ups("owner", "project", 10.0)
    elif operation == "engine-unstake":
        engine.fee_config.staked_fi_exit_fee = rate
        action = lambda: engine.human_unstakes_fi("owner", "project", 10.0)
    elif operation == "pool-stake":
        action = lambda: pool.stake_ups(10.0, "owner", rate)
    else:
        action = lambda: pool.unstake_fi(10.0, "owner", rate)
    before = _numeric_snapshot(engine)
    with pytest.raises(ValueError):
        action()
    assert _numeric_snapshot(engine) == before


def test_numeric_mixed_adoption_rejects_invalid_work_before_any_metric_changes():
    pool = FoundUpTokenPool("project")
    before = _numeric_snapshot(pool)
    with pytest.raises(ValueError):
        pool.update_adoption(users=10, revenue_ups=10.0, work_completed=float("nan"), milestone=True)
    assert _numeric_snapshot(pool) == before


@pytest.mark.parametrize("discount", [2.0, -100.0, float("nan"), float("inf")])
def test_numeric_invalid_effective_discounted_fee_rejects_before_stake(monkeypatch, discount):
    engine = _numeric_engine()
    account = engine.human_accounts["owner"]
    config = account.get_subscription_config()
    monkeypatch.setattr(config, "staking_fee_discount", discount)
    assert engine.fee_config.staked_fi_entry_fee == 0.03
    before = _numeric_snapshot(engine, config)
    with pytest.raises(ValueError):
        engine.human_stakes_ups("owner", "project", 10.0)
    assert _numeric_snapshot(engine, config) == before


def test_numeric_valid_effective_discount_keeps_existing_fee_math(monkeypatch):
    engine = _numeric_engine()
    config = engine.human_accounts["owner"].get_subscription_config()
    monkeypatch.setattr(config, "staking_fee_discount", 0.5)
    fi, fee = engine.human_stakes_ups("owner", "project", 10.0)
    assert fi == pytest.approx(9.85)
    assert fee == pytest.approx(0.15)
    assert engine.foundup_pools["project"].ups_treasury == pytest.approx(fi)
    assert engine.human_accounts["owner"].ups_balance == pytest.approx(890.0)


@pytest.mark.parametrize("operation", ["work", "stake", "unstake"])
def test_numeric_invalid_operands_reject_even_when_funds_are_insufficient(operation):
    engine = _numeric_engine(staked=True)
    if operation == "work":
        action = lambda: engine.agent_completes_task("worker", "project", 10000.0, float("nan"))
    elif operation == "stake":
        engine.fee_config.staked_fi_entry_fee = float("nan")
        action = lambda: engine.human_stakes_ups("owner", "project", 10000.0)
    else:
        engine.fee_config.staked_fi_exit_fee = float("nan")
        action = lambda: engine.human_unstakes_fi("owner", "project", 10000.0)
    before = _numeric_snapshot(engine)
    with pytest.raises(ValueError):
        action()
    assert _numeric_snapshot(engine) == before


@pytest.mark.parametrize("operation", ["work-adoption", "work-owner-credit", "stake-owner-total"])
def test_numeric_late_participant_overflow_rejects_before_gas_or_pool_commit(operation):
    engine = _numeric_engine()
    pool = engine.foundup_pools["project"]
    owner = engine.human_accounts["owner"]
    if operation == "work-adoption":
        pool.total_work_completed = 1e308
        action = lambda: engine.agent_completes_task("worker", "project", 1.0, 1e308)
    elif operation == "work-owner-credit":
        pool.total_supply = 1.7e308
        owner.foundup_tokens["project"] = 1.5e308
        action = lambda: engine.agent_completes_task("worker", "project", 1.0, 6e307)
    else:
        owner.ups_balance, owner.total_ups_staked = 1.7e308, 1.5e308
        assert pool.ups_treasury == pool.staked_fi_outstanding == 0.0
        action = lambda: engine.human_stakes_ups("owner", "project", 6e307)
    before = _numeric_snapshot(engine)
    with pytest.raises(ValueError):
        action()
    assert _numeric_snapshot(engine) == before


@pytest.mark.parametrize("operation", [
    "wallet-spent", "owner-receive-fi", "owner-stake-position",
    "owner-stake-total", "owner-unstake-ups",
])
def test_numeric_called_mutators_reject_overflow_before_their_first_assignment(operation):
    wallet = AgentExecutionWallet("worker", "owner", ups_balance=1.7e308, total_spent=1.5e308)
    account = HumanUPSAccount("owner", ups_balance=1.5e308)
    account.staked_positions["project"] = 1.5e308
    account.foundup_tokens["project"] = 1.5e308
    account.total_ups_staked = 1.5e308
    calls = {
        "wallet-spent": lambda: wallet.spend(6e307, "task:project"),
        "owner-receive-fi": lambda: account.receive_fi("project", 6e307),
        "owner-stake-position": lambda: account.record_stake("project", 1.0, 6e307),
        "owner-stake-total": lambda: account.record_stake("project", 6e307, 1.0),
        "owner-unstake-ups": lambda: account.record_unstake("project", 1.0, 6e307),
    }
    before = _numeric_snapshot(wallet, account)
    with pytest.raises(ValueError):
        calls[operation]()
    assert _numeric_snapshot(wallet, account) == before


def test_numeric_builtin_integer_and_signed_zero_remain_admissible():
    engine = _numeric_engine()
    assert engine.agent_completes_task("worker", "project", 0, 2) == (True, 2)
    before = _numeric_snapshot(engine)
    assert engine.agent_completes_task("worker", "project", -0.0, -0.0) == (True, 0.0)
    assert _numeric_snapshot(engine) == before



@pytest.mark.parametrize("operand", ["cost", "reward"])
def test_numeric_invalid_work_creates_no_unknown_actor_or_pool(operand):
    engine = TokenEconomicsEngine()
    before = _numeric_snapshot(engine)
    cost, reward = ("1.0", 1.0) if operand == "cost" else (0.0, "1.0")
    with pytest.raises(ValueError):
        engine.agent_completes_task("new-worker", "new-project", cost, reward)
    assert _numeric_snapshot(engine) == before


@pytest.mark.parametrize("operation", [
    "pool-mint", "pool-stake", "pool-unstake", "engine-work",
    "engine-stake", "engine-unstake", "wallet-spend",
])
def test_numeric_zero_quantities_retain_existing_no_balance_effect(operation):
    engine = _numeric_engine(staked=True)
    pool = engine.foundup_pools["project"]
    wallet = engine.agent_wallets["worker"]
    calls = {
        "pool-mint": lambda: pool.mint_for_work(0.0, "worker"),
        "pool-stake": lambda: pool.stake_ups(0.0, "owner"),
        "pool-unstake": lambda: pool.unstake_fi(0.0, "owner"),
        "engine-work": lambda: engine.agent_completes_task("worker", "project", 0.0, 0.0),
        "engine-stake": lambda: engine.human_stakes_ups("owner", "project", 0.0),
        "engine-unstake": lambda: engine.human_unstakes_fi("owner", "project", 0.0),
        "wallet-spend": lambda: wallet.spend(0.0, "task:project"),
    }
    before = _numeric_snapshot(engine)
    result = calls[operation]()
    assert result in (0.0, (0.0, 0.0), (True, 0.0))
    assert _numeric_snapshot(engine) == before


def test_numeric_fractional_work_keeps_gas_and_owner_reward_arithmetic():
    engine = _numeric_engine()
    wallet_before = engine.agent_wallets["worker"].ups_balance
    ok, minted = engine.agent_completes_task("worker", "project", 0.25, 2.5)
    assert ok is True
    assert minted == pytest.approx(2.5)
    assert engine.agent_wallets["worker"].ups_balance == pytest.approx(wallet_before - 0.25025)
    assert engine.human_accounts["owner"].foundup_tokens["project"] == pytest.approx(2.5)
    assert engine.foundup_pools["project"].minted == pytest.approx(2.5)
    assert engine.foundup_pools["project"].total_work_completed == pytest.approx(5.0)


def test_numeric_valid_first_work_keeps_existing_registration_behavior():
    engine = TokenEconomicsEngine()
    assert engine.agent_completes_task("new-worker", "new-project", 0.0, 1.25) == (True, 1.25)
    assert engine.agent_wallets["new-worker"].allocator_id == "new-worker"
    assert engine.foundup_pools["new-project"].minted == pytest.approx(1.25)
    assert engine.human_accounts["new-worker"].foundup_tokens["new-project"] == pytest.approx(1.25)


@pytest.mark.parametrize("rate", [0.0, 0.25])
def test_numeric_valid_mutable_fees_keep_pool_owner_roundtrip_arithmetic(rate):
    engine = _numeric_engine()
    engine.fee_config.staked_fi_entry_fee = rate
    engine.fee_config.staked_fi_exit_fee = rate
    account = engine.human_accounts["owner"]
    pool = engine.foundup_pools["project"]
    before_balance = account.ups_balance
    fi, entry_fee = engine.human_stakes_ups("owner", "project", 2.5)
    assert fi == pytest.approx(2.5 * (1.0 - rate))
    assert entry_fee == pytest.approx(2.5 * rate)
    assert account.ups_balance == pytest.approx(before_balance - 2.5)
    assert pool.ups_treasury == pytest.approx(fi)
    assert account.staked_positions["project"] == pytest.approx(fi)
    returned, exit_fee = engine.human_unstakes_fi("owner", "project", fi)
    assert returned == pytest.approx(fi * (1.0 - rate))
    assert exit_fee == pytest.approx(fi * rate)
    assert account.ups_balance == pytest.approx(before_balance - 2.5 + returned)
    assert pool.ups_treasury == pytest.approx(0.0)
    assert pool.staked_fi_outstanding == pytest.approx(0.0)
    assert "project" not in account.staked_positions


@pytest.mark.parametrize("operation", ["work", "stake", "unstake"])
def test_numeric_insufficient_funds_preserve_existing_failure_outcomes(operation):
    engine = _numeric_engine(staked=True)
    before = _numeric_snapshot(engine)
    if operation == "work":
        result = engine.agent_completes_task("worker", "project", 1000.0, 2.5)
        assert result == (False, 0.0)
    elif operation == "stake":
        assert engine.human_stakes_ups("owner", "project", 10000.0) == (0.0, 0.0)
    else:
        assert engine.human_unstakes_fi("owner", "project", 10000.0) == (0.0, 0.0)
    assert _numeric_snapshot(engine) == before


@pytest.mark.parametrize("operation", [
    "pool-stake", "pool-mint", "adoption-work",
    "engine-work-spent", "engine-stake", "engine-unstake",
])
def test_numeric_finite_inputs_cannot_commit_nonfinite_prospective_results(operation):
    engine = _numeric_engine(staked=True)
    pool = engine.foundup_pools["project"]
    account = engine.human_accounts["owner"]
    wallet = engine.agent_wallets["worker"]
    if operation == "pool-stake":
        pool.ups_treasury = pool.staked_fi_outstanding = 1e308
        action = lambda: pool.stake_ups(1e308, "owner", 0.0)
    elif operation == "pool-mint":
        pool.adoption_score, pool.total_supply = 1.0, 1.7e308
        pool.minted, pool.total_work_completed = 1e308, 1.7e308
        action = lambda: pool.mint_for_work(1e308, "worker")
    elif operation == "adoption-work":
        pool.total_work_completed = 1e308
        action = lambda: pool.update_adoption(work_completed=1e308)
    elif operation == "engine-work-spent":
        wallet.ups_balance, wallet.total_spent = 1.7e308, 1e308
        action = lambda: engine.agent_completes_task("worker", "project", 1e308, 1.0)
    elif operation == "engine-stake":
        account.ups_balance, account.total_ups_staked = 1.7e308, 1e308
        pool.ups_treasury = pool.staked_fi_outstanding = 1e308
        action = lambda: engine.human_stakes_ups("owner", "project", 1e308)
    else:
        account.ups_balance = 1.7e308
        account.staked_positions["project"] = 1e308
        pool.ups_treasury = pool.staked_fi_outstanding = 1e308
        action = lambda: engine.human_unstakes_fi("owner", "project", 1e308)
    before = _numeric_snapshot(engine)
    with pytest.raises(ValueError):
        action()
    assert _numeric_snapshot(engine) == before
