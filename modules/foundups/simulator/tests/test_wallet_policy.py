"""Agent budget policies are detached host inputs, not mutable caller grants."""

from collections import UserDict
from decimal import Decimal

import pytest

from modules.foundups.simulator.economics.token_economics import (
    AgentExecutionWallet, TokenEconomicsEngine,
)


class HostileDict(dict):
    def __bool__(self):
        raise AssertionError("custom truth hook executed")

    def items(self):
        raise AssertionError("custom iteration executed")


class HostileInt(int):
    def __float__(self):
        raise AssertionError("custom conversion executed")


def _engine():
    engine = TokenEconomicsEngine()
    engine.register_human("owner", initial_ups=100)
    engine.register_agent("worker", "owner")
    return engine, engine.agent_wallets["worker"]


def _state(wallet):
    return (wallet.ups_balance, wallet.total_allocated, wallet.total_spent,
            dict(wallet.policy_gates))


@pytest.mark.parametrize("entry", ["constructor", "replacement", "allocation", "engine"])
def test_policy_caller_mutation_cannot_expand_spending(entry):
    policy = {"allowed_ops": ["build"], "max_per_task": 2}
    engine, wallet = _engine()
    if entry == "constructor":
        wallet = AgentExecutionWallet("worker", "owner", ups_balance=20, policy_gates=policy)
    elif entry == "replacement":
        wallet.receive_allocation(20)
        wallet.policy_gates = policy
    elif entry == "allocation":
        wallet.receive_allocation(20, policy)
    else:
        assert engine.human_allocates_to_agent("owner", "worker", 20, policy)
    policy["allowed_ops"].append("drain")
    policy["max_per_task"] = 100
    before = _state(wallet)
    assert wallet.spend(2, "drain") == (False, 0.0)
    assert wallet.spend(3, "build") == (False, 0.0)
    assert _state(wallet) == before
    assert wallet.spend(2, "build") == (True, 0.002)


def test_public_policy_view_is_readonly_and_nested_operations_are_not_mutable():
    wallet = AgentExecutionWallet("worker", "owner", policy_gates={"allowed_ops": ["build"]})
    with pytest.raises(TypeError):
        wallet.policy_gates["max_per_task"] = 100
    with pytest.raises((AttributeError, TypeError)):
        wallet.policy_gates["allowed_ops"].append("drain")
    assert not wallet._policy_allows("drain", 1)


_BAD = [True, [], UserDict(), HostileDict(), {"typo": 1}, {1: 2},
        {"allowed_ops": "build"}, {"allowed_ops": {"build"}},
        {"allowed_ops": [""]}, {"allowed_ops": [1]},
        {"max_per_task": True}, {"max_per_task": -1},
        {"max_per_task": float("nan")}, {"max_per_task": float("inf")},
        {"max_per_task": Decimal("2")}, {"max_per_task": HostileInt(2)}]


@pytest.mark.parametrize("policy", _BAD)
@pytest.mark.parametrize("entry", ["constructor", "replacement", "allocation", "engine"])
def test_invalid_policy_rejects_before_budget_or_policy_changes(policy, entry):
    engine, wallet = _engine()
    wallet.policy_gates = {"allowed_ops": ["build"]}
    before, owner_before = _state(wallet), engine.human_accounts["owner"].ups_balance
    with pytest.raises(ValueError):
        if entry == "constructor":
            AgentExecutionWallet("worker", "owner", policy_gates=policy)
        elif entry == "replacement":
            wallet.policy_gates = policy
        elif entry == "allocation":
            wallet.receive_allocation(10, policy)
        else:
            engine.human_allocates_to_agent("owner", "worker", 10, policy)
    assert _state(wallet) == before
    assert engine.human_accounts["owner"].ups_balance == owner_before


def test_insufficient_funding_cannot_rebind_policy_and_invalid_policy_still_rejects():
    engine, wallet = _engine()
    wallet.policy_gates = {"allowed_ops": ["build"]}
    before = _state(wallet)
    assert not engine.human_allocates_to_agent("owner", "worker", 101, {"allowed_ops": ["drain"]})
    assert _state(wallet) == before
    with pytest.raises(ValueError):
        engine.human_allocates_to_agent("owner", "worker", 101, {"max_per_task": True})
    assert _state(wallet) == before
    assert engine.human_accounts["owner"].ups_balance == 100


@pytest.mark.parametrize("policy", [None, {}])
@pytest.mark.parametrize("entry", ["allocation", "engine"])
def test_omitted_or_empty_allocation_policy_retains_installed_policy(policy, entry):
    engine, wallet = _engine()
    wallet.policy_gates = {"allowed_ops": ["build"]}
    if entry == "allocation":
        wallet.receive_allocation(10, policy)
    else:
        assert engine.human_allocates_to_agent("owner", "worker", 10, policy)
    assert wallet.spend(1, "drain") == (False, 0.0)
    assert wallet.spend(1, "build") == (True, 0.001)


def test_explicit_host_replacement_and_unrestricted_legacy_policy():
    wallet = AgentExecutionWallet("worker", "owner", ups_balance=20)
    assert wallet.spend(1, "build")[0]
    wallet.policy_gates = {"allowed_ops": ["build"], "max_per_task": 0}
    assert wallet.spend(1, "build") == (False, 0.0)
    assert wallet.spend(0, "build") == (True, 0.0)
    wallet.policy_gates = {"allowed_ops": ("drain",), "max_per_task": 2}
    assert wallet.spend(1, "drain")[0]
    wallet.policy_gates = {}
    assert wallet.spend(1, "any")[0]
    wallet.policy_gates = {"allowed_ops": []}
    assert wallet.spend(1, "any")[0]


def test_integer_policy_limits_are_exact_without_float_coercion():
    wallet = AgentExecutionWallet("worker", "owner", ups_balance=20)
    wallet.policy_gates = {"max_per_task": 2**53}
    assert wallet._policy_allows("build", 2**53)
    assert not wallet._policy_allows("build", 2**53 + 1)
    wallet.policy_gates = {"max_per_task": 10**400}
    assert wallet.policy_gates["max_per_task"] == 10**400
    assert wallet.spend(1, "build") == (True, 0.001)
