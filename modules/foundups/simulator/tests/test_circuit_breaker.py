"""Adversarial checks of the existing simulator breaker, not chain authority."""
from dataclasses import asdict
from datetime import datetime, timedelta

import pytest

import modules.foundups.simulator.economics.circuit_breaker as breaker_module
from modules.foundups.simulator.economics.circuit_breaker import (
    BreakerState, BreakerTrigger, CircuitBreaker,
)


@pytest.fixture
def clock(monkeypatch):
    class Clock(datetime):
        current = datetime(2026, 10, 31, 12)

        @classmethod
        def now(cls):
            return cls.current
    monkeypatch.setattr(breaker_module, "datetime", Clock)
    return Clock


@pytest.mark.parametrize("backing,outflow", [(0.85, 0.11), (0.75, 0.11), (1.0, 0.11)])
def test_most_severe_signal_controls_state(clock, backing, outflow) -> None:
    breaker = CircuitBreaker(daily_outflow=outflow)
    assert breaker.check_conditions(backing, 100000.0) == BreakerState.RESTRICTED
    assert not breaker.can_exit()


@pytest.mark.parametrize("backing,outflow", [(0.85, 0.0), (0.75, 0.0), (1.0, 0.11), (1.0, 0.0)])
def test_emergency_cannot_downgrade_during_cooldown(clock, backing, outflow) -> None:
    breaker = CircuitBreaker()
    assert breaker.check_conditions(0.4, 100000.0) == BreakerState.EMERGENCY
    original = breaker.triggered_at
    breaker.daily_outflow = outflow
    clock.current += timedelta(hours=23)
    assert breaker.check_conditions(backing, 100000.0) == BreakerState.EMERGENCY
    assert breaker.triggered_at == original
    assert breaker.exits_blocked()


def test_restricted_state_cannot_downgrade_to_caution_early(clock) -> None:
    breaker = CircuitBreaker()
    breaker.check_conditions(0.7, 100000.0)
    assert breaker.check_conditions(0.85, 100000.0) == BreakerState.RESTRICTED


def test_emergency_queue_prevents_downgrade_after_cooldown(clock) -> None:
    breaker = CircuitBreaker()
    breaker.check_conditions(0.4, 100000.0)
    queued = breaker.queue_exit("human", "foundup", 1.0)
    clock.current += timedelta(hours=25)
    assert breaker.check_conditions(0.85, 100000.0) == BreakerState.EMERGENCY
    assert breaker.process_queue() == []
    assert breaker.exit_queue == [queued]


def test_healthy_empty_queue_recovers_after_existing_cooldown(clock) -> None:
    """A12 partial: recovery arithmetic, not authenticated governance/recovery."""
    breaker = CircuitBreaker()
    breaker.check_conditions(0.4, 100000.0)
    clock.current += timedelta(hours=24)
    assert breaker.check_conditions(1.0, 100000.0) == BreakerState.NORMAL
    assert breaker.trigger is None
    assert breaker.can_exit()


def test_new_emergency_escalates_immediately(clock) -> None:
    breaker = CircuitBreaker()
    breaker.check_conditions(0.85, 100000.0)
    assert breaker.check_conditions(1.0, 60000.0) == BreakerState.EMERGENCY
    assert breaker.trigger == BreakerTrigger.BTC_CRASH


@pytest.mark.parametrize("value", [True, "1", float("nan"), float("inf"), -1.0, 10**400])
@pytest.mark.parametrize("field", ["backing", "price", "outflow", "reference_price"])
def test_invalid_oracle_or_metric_fails_before_transition(clock, field, value) -> None:
    """A11 partial: reject invalid numbers, not plausible but false signed data."""
    breaker = CircuitBreaker()
    backing, price = 1.0, 100000.0
    if field == "backing": backing = value
    elif field == "price": price = value
    elif field == "outflow": breaker.daily_outflow = value
    else: breaker.btc_price_24h_ago = value
    before = asdict(breaker)
    with pytest.raises(ValueError):
        breaker.check_conditions(backing, price)
    assert asdict(breaker) == before
