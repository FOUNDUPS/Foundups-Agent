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

import time
from inspect import signature

@pytest.fixture
def cadence_clock(monkeypatch):
    current = [10000.0]
    monkeypatch.setattr(time, "monotonic", lambda: current[0])
    return current

def _cadence_queue(count, **kwargs):
    breaker = CircuitBreaker(**kwargs)
    items = [breaker.queue_exit(f"owner_{n}", "foundup", 1.0) for n in range(count)]
    return breaker, items

def _cadence_order(breaker, original, released):
    assert [id(item) for item in released + breaker.exit_queue] == [id(item) for item in original]

@pytest.mark.parametrize("count,batch", [(1, 1), (2, 1), (9, 1), (19, 1), (100, 10)],
                         ids=["one", "two", "nine", "nineteen", "hundred"])
def test_queue_cadence_first_release_fifo_and_minimum_one(cadence_clock, count, batch):
    breaker, items = _cadence_queue(count)
    ready = breaker.process_queue()
    assert len(ready) == batch
    _cadence_order(breaker, items, ready)

def test_queue_cadence_repeated_calls_are_no_effect(cadence_clock):
    breaker, items = _cadence_queue(100)
    ready = breaker.process_queue()
    for _ in range(5):
        assert breaker.process_queue() == []
    _cadence_order(breaker, items, ready)

@pytest.mark.parametrize("elapsed,batch", [(3599.999, 0), (3600.0, 9), (3600.001, 9)],
                         ids=["before", "equal", "after"])
def test_queue_cadence_inclusive_hour_boundary(cadence_clock, elapsed, batch):
    breaker, items = _cadence_queue(100)
    released = breaker.process_queue()
    cadence_clock[0] += elapsed
    ready = breaker.process_queue()
    assert len(ready) == batch
    _cadence_order(breaker, items, released + ready)

def test_queue_cadence_rollback_and_early_calls_do_not_reset_interval(cadence_clock):
    breaker, items = _cadence_queue(100)
    released = breaker.process_queue()
    for current in (9999.0, 13599.999):
        cadence_clock[0] = current
        assert breaker.process_queue() == []
    cadence_clock[0] = 13600.0
    ready = breaker.process_queue()
    assert len(ready) == 9
    _cadence_order(breaker, items, released + ready)

def test_queue_cadence_long_gap_earns_no_catchup(cadence_clock):
    breaker, items = _cadence_queue(100)
    released = breaker.process_queue()
    cadence_clock[0] += 24 * 3600
    ready = breaker.process_queue()
    assert len(ready) == 9
    assert breaker.process_queue() == []
    _cadence_order(breaker, items, released + ready)

def test_queue_cadence_hourly_series_preserves_original_batches(cadence_clock):
    breaker, items = _cadence_queue(100)
    released = []
    for count in (10, 9, 8, 7):
        ready = breaker.process_queue()
        assert len(ready) == count
        released.extend(ready)
        cadence_clock[0] += 3600
    _cadence_order(breaker, items, released)

def test_queue_cadence_existing_nondefault_rate_is_preserved(cadence_clock):
    config = breaker_module.BreakerConfig(queue_release_per_hour=0.25)
    breaker, items = _cadence_queue(100, config=config)
    ready = breaker.process_queue()
    assert len(ready) == 25
    _cadence_order(breaker, items, ready)

def test_queue_cadence_empty_first_drain_poll_and_refill_keep_timer(cadence_clock):
    breaker = CircuitBreaker()
    assert breaker.process_queue() == []
    cadence_clock[0] += 1
    first = breaker.queue_exit("owner", "foundup", 1.0)
    assert breaker.process_queue() == [first]
    cadence_clock[0] += 3599
    assert breaker.process_queue() == []
    item = breaker.queue_exit("next_owner", "foundup", 2.0)
    assert breaker.process_queue() == []
    cadence_clock[0] += 1
    assert breaker.process_queue() == [item]

def test_queue_cadence_initial_emergency_does_not_consume_timer(cadence_clock):
    breaker, items = _cadence_queue(100, state=BreakerState.EMERGENCY)
    assert breaker.process_queue() == []
    breaker.state = BreakerState.RESTRICTED
    ready = breaker.process_queue()
    assert len(ready) == 10
    _cadence_order(breaker, items, ready)

def test_queue_cadence_emergency_polls_do_not_postpone_earned_release(cadence_clock):
    breaker, items = _cadence_queue(100)
    released = breaker.process_queue()
    breaker.state = BreakerState.EMERGENCY
    cadence_clock[0] += 3600
    assert breaker.process_queue() == []
    breaker.state = BreakerState.RESTRICTED
    ready = breaker.process_queue()
    assert len(ready) == 9
    _cadence_order(breaker, items, released + ready)

def test_queue_cadence_wall_clock_cannot_open_release(cadence_clock, monkeypatch):
    breaker, items = _cadence_queue(100)
    released = breaker.process_queue()
    class FutureClock(datetime):
        now = classmethod(lambda cls: datetime(2040, 1, 1))
    monkeypatch.setattr(breaker_module, "datetime", FutureClock)
    assert breaker.process_queue() == []
    cadence_clock[0] += 3600
    ready = breaker.process_queue()
    assert len(ready) == 9
    _cadence_order(breaker, items, released + ready)

def test_queue_cadence_logging_failure_retains_committed_interval(cadence_clock, monkeypatch):
    breaker, items = _cadence_queue(100)
    def fail_log(*args, **kwargs):
        raise RuntimeError("fixture logging failure")
    with monkeypatch.context() as patch:
        patch.setattr(breaker_module.logger, "info", fail_log)
        with pytest.raises(RuntimeError, match="fixture logging failure"):
            breaker.process_queue()
    assert breaker.process_queue() == []
    cadence_clock[0] += 3600
    ready = breaker.process_queue()
    assert len(ready) == 9
    _cadence_order(breaker, items, items[:10] + ready)

def test_queue_cadence_constructor_equality_and_repr_compatibility(cadence_clock):
    expected = ("config", "state", "trigger", "triggered_at", "exit_queue", "daily_outflow",
                "last_outflow_reset", "btc_price_24h_ago", "times_triggered", "total_queued_exits")
    assert tuple(signature(CircuitBreaker).parameters) == expected
    left, items = _cadence_queue(100)
    right = CircuitBreaker(exit_queue=list(items), last_outflow_reset=left.last_outflow_reset,
                           total_queued_exits=left.total_queued_exits)
    left.process_queue()
    cadence_clock[0] += 1
    right.process_queue()
    assert left == right
    assert repr(left) == repr(right)
