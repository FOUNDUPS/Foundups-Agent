"""Private scalar arithmetic for simulator work/stake/unstake admission.

No identities, stores, logging, I/O or effects belong here. Result records are
transient calculations, not settlement or economic authority.
"""

import math
from typing import NamedTuple


class _WalletValues(NamedTuple):
    success: bool
    balance: float
    spent: float
    fee: float


class _AdoptionValues(NamedTuple):
    users: int
    revenue: float
    work: float
    milestones: int
    score: float


class _MintValues(NamedTuple):
    received: float
    minted: float
    work: float


class _PoolValues(NamedTuple):
    received: float
    fee: float
    treasury: float
    outstanding: float


class _WorkValues(NamedTuple):
    wallet_balance: float
    wallet_spent: float
    adoption_score: float
    total_work: float
    minted: float
    earned: float
    owner_fi: float


def _require_numbers(*values, rate: bool = False) -> None:
    """Reject unsupported numerical inputs before any mutation."""
    for value in values:
        if type(value) not in (int, float):
            raise ValueError("quantity must be a built-in int or float")
        try:
            valid = math.isfinite(value) and value >= 0 and (not rate or value < 1)
        except OverflowError:
            valid = False
        if not valid:
            raise ValueError("quantity must be finite and nonnegative; rates must be below one")


def _checked_add(*values) -> float:
    """Use the existing addition order, rejecting nonfinite prospective totals."""
    _require_numbers(*values)
    result = sum(values)
    _require_numbers(result)
    return result


def _fee_values(amount: float, rate: float) -> tuple[float, float]:
    _require_numbers(amount)
    _require_numbers(rate, rate=True)
    fee = amount * rate
    net = amount - fee
    _require_numbers(fee, net)
    if amount > 0 and net == 0:
        raise ValueError("positive quantity has an unsupported zero net")
    return fee, net


def _discount_rate(base_rate: float, discount: float) -> float:
    _require_numbers(base_rate, rate=True)
    _require_numbers(discount)
    if discount > 1:
        raise ValueError("staking discount must be at most one")
    effective = base_rate * (1.0 - discount)
    _require_numbers(effective, rate=True)
    return effective


def _wallet_values(amount: float, balance: float, spent: float, rate: float) -> _WalletValues:
    _require_numbers(amount, balance, spent)
    _require_numbers(rate, rate=True)
    fee = amount * rate
    total_debit = _checked_add(amount, fee)
    if total_debit > balance:
        return _WalletValues(False, balance, spent, 0.0)
    return _WalletValues(True, balance - total_debit, _checked_add(spent, amount), fee)


def _adoption_values(
    current: _AdoptionValues, users=None, revenue=None, work=None, milestone=False,
) -> _AdoptionValues:
    if work is not None:
        _require_numbers(work)
        next_work = _checked_add(current.work, work)
    else:
        next_work = current.work
    next_users = current.users if users is None else users
    next_revenue = current.revenue if revenue is None else current.revenue + revenue
    next_milestones = current.milestones + (1 if milestone else 0)
    user_factor = math.log10(max(1, next_users) + 1) / 5.0
    revenue_factor = math.log10(max(1, next_revenue) + 1) / 8.0
    work_factor = math.log10(max(1, next_work) + 1) / 6.0
    milestone_factor = min(0.2, next_milestones * 0.05)
    score = min(1.0, max(0.0,
        user_factor * 0.35 + revenue_factor * 0.30 +
        work_factor * 0.25 + milestone_factor
    ))
    return _AdoptionValues(next_users, next_revenue, next_work, next_milestones, score)


def _remaining_value(available: float, minted: float) -> float:
    _require_numbers(available, minted)
    return max(0.0, available - minted)


def _mint_values(amount: float, available: float, minted: float, work: float) -> _MintValues:
    _require_numbers(amount)
    received = min(amount, _remaining_value(available, minted))
    if received <= 0:
        return _MintValues(0.0, minted, work)
    return _MintValues(received, _checked_add(minted, received), _checked_add(work, received))


def _stake_values(amount: float, rate: float, treasury: float, outstanding: float) -> _PoolValues:
    fee, received = _fee_values(amount, rate)
    return _PoolValues(
        received, fee, _checked_add(treasury, received), _checked_add(outstanding, received),
    )


def _unstake_values(amount: float, rate: float, treasury: float, outstanding: float) -> _PoolValues:
    fee, received = _fee_values(amount, rate)
    _require_numbers(treasury, outstanding)
    if amount > treasury or amount > outstanding:
        return _PoolValues(0.0, 0.0, treasury, outstanding)
    return _PoolValues(received, fee, treasury - amount, outstanding - amount)


def _unstake_record_values(
    position: float, balance: float, amount: float, received: float,
) -> tuple[float, float]:
    _require_numbers(position, amount, received)
    return max(0.0, position - amount), _checked_add(balance, received)

