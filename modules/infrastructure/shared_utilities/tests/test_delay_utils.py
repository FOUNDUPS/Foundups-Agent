"""Offline acceptance tests for the exact activity polling policy."""

import pytest

from modules.infrastructure.shared_utilities.delay_utils import DelayUtils


def test_empty_reads_follow_requested_schedule_and_remain_capped():
    delay = DelayUtils.calculate_activity_poll_delay()
    observed = [delay]
    for _ in range(7):
        delay = DelayUtils.calculate_activity_poll_delay(delay, activity=False)
        observed.append(delay)
    assert observed == [60, 120, 240, 480, 960, 1920, 3600, 3600]
    for _ in range(1000):
        delay = DelayUtils.calculate_activity_poll_delay(delay, activity=False)
    assert delay == 3600


@pytest.mark.parametrize("delay", [60, 120, 240, 480, 960, 1920, 3600])
def test_new_activity_resets_each_interval_and_empty_read_restarts_backoff(delay):
    reset = DelayUtils.calculate_activity_poll_delay(delay, activity=True)
    assert reset == 60
    assert DelayUtils.calculate_activity_poll_delay(reset, activity=False) == 120


@pytest.mark.parametrize("delay", [60, 120, 240, 480, 960, 1920, 3600])
def test_missing_observation_does_not_advance_or_reset_interval(delay):
    assert DelayUtils.calculate_activity_poll_delay(delay, activity=None) == delay


@pytest.mark.parametrize("delay", [-1, 0, 1, 59, 61, 3840, 10**100, 60.0, True, "60", None])
def test_invalid_prior_state_is_refused_even_when_activity_would_reset(delay):
    with pytest.raises(ValueError, match="invalid_activity_poll_delay_seconds"):
        DelayUtils.calculate_activity_poll_delay(delay, activity=True)


@pytest.mark.parametrize("activity", [0, 1, "false", [], {}])
def test_activity_requires_explicit_bool_or_unknown(activity):
    with pytest.raises(ValueError, match="activity_must_be_bool_or_none"):
        DelayUtils.calculate_activity_poll_delay(activity=activity)


def test_existing_youtube_delay_contract_is_unchanged(monkeypatch):
    monkeypatch.setattr("modules.infrastructure.shared_utilities.delay_utils.random.uniform", lambda low, high: 0)
    assert DelayUtils.calculate_enhanced_delay(force_dev_delay=True) == 1.0
    assert DelayUtils.calculate_enhanced_delay() == 5.0
    assert DelayUtils.calculate_enhanced_delay(consecutive_failures=100) == 1800.0
    assert DelayUtils.calculate_enhanced_delay(active_users=1) == 30.0
    assert DelayUtils.calculate_circuit_breaker_delay(4) == 600
