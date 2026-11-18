"""BTC staker hurdle state machine tests.

Tests the local hurdle mechanics for BTC stakers in the Du-pool partition.
This is SEPARATE from I_i investor hurdle logic in investor_staking.py.
"""

from __future__ import annotations

import pytest

from modules.foundups.simulator.economics.pool_distribution import (
    STAKER_HURDLE_TARGET_MULTIPLE,
    STAKER_POST_HURDLE_RATE_FACTOR,
    UPS_TO_BTC_RATE,
    StakerHurdleState,
    StakerPosition,
    EpochDistribution,
)


class TestStakerHurdleStateEnum:
    """Test StakerHurdleState enum values and semantics."""

    def test_pre_hurdle_is_zero(self) -> None:
        """PRE_HURDLE has value 0."""
        assert StakerHurdleState.PRE_HURDLE == 0

    def test_hurdle_met_is_one(self) -> None:
        """HURDLE_MET has value 1 (transition state)."""
        assert StakerHurdleState.HURDLE_MET == 1

    def test_post_hurdle_locked_is_two(self) -> None:
        """POST_HURDLE_LOCKED has value 2."""
        assert StakerHurdleState.POST_HURDLE_LOCKED == 2

    def test_default_target_multiple_is_10(self) -> None:
        """Default hurdle target multiple is 10x."""
        assert STAKER_HURDLE_TARGET_MULTIPLE == 10.0


class TestStakerPositionHurdleFields:
    """Test StakerPosition hurdle-related fields."""

    def test_default_cumulative_distributions_is_zero(self) -> None:
        """New position starts with zero cumulative distributions."""
        position = StakerPosition(original_stake_btc=1.0)
        assert position.cumulative_distributions_btc == 0.0

    def test_default_hurdle_target_multiple_is_10(self) -> None:
        """Default hurdle target multiple is 10x."""
        position = StakerPosition(original_stake_btc=1.0)
        assert position.hurdle_target_multiple == 10.0

    def test_default_post_hurdle_locked_is_false(self) -> None:
        """New position is not hurdle-locked."""
        position = StakerPosition(original_stake_btc=1.0)
        assert position.post_hurdle_locked is False

    def test_default_hurdle_locked_at_btc_is_none(self) -> None:
        """New position has no hurdle lock timestamp."""
        position = StakerPosition(original_stake_btc=1.0)
        assert position.hurdle_locked_at_btc is None


class TestHurdleTargetBtc:
    """Test hurdle_target_btc property."""

    def test_target_is_stake_times_multiple(self) -> None:
        """Target = original_stake_btc * hurdle_target_multiple."""
        position = StakerPosition(original_stake_btc=1.0)
        assert position.hurdle_target_btc == pytest.approx(10.0, rel=1e-9)

    def test_target_with_5_btc_stake(self) -> None:
        """5 BTC stake has 50 BTC target."""
        position = StakerPosition(original_stake_btc=5.0)
        assert position.hurdle_target_btc == pytest.approx(50.0, rel=1e-9)

    def test_target_with_custom_multiple(self) -> None:
        """Custom multiple affects target."""
        position = StakerPosition(
            original_stake_btc=1.0,
            hurdle_target_multiple=5.0,
        )
        assert position.hurdle_target_btc == pytest.approx(5.0, rel=1e-9)

    def test_target_with_zero_stake_is_zero(self) -> None:
        """Zero stake has zero target."""
        position = StakerPosition(original_stake_btc=0.0)
        assert position.hurdle_target_btc == 0.0


class TestHurdleProgress:
    """Test hurdle_progress property."""

    def test_zero_distributions_is_zero_progress(self) -> None:
        """No distributions = 0% progress."""
        position = StakerPosition(original_stake_btc=1.0)
        assert position.hurdle_progress == pytest.approx(0.0, rel=1e-9)

    def test_half_distributions_is_50_percent_progress(self) -> None:
        """5 BTC distributions on 1 BTC stake (target 10) = 50%."""
        position = StakerPosition(
            original_stake_btc=1.0,
            cumulative_distributions_btc=5.0,
        )
        assert position.hurdle_progress == pytest.approx(0.5, rel=1e-9)

    def test_at_target_is_100_percent_progress(self) -> None:
        """At target = 100% progress."""
        position = StakerPosition(
            original_stake_btc=1.0,
            cumulative_distributions_btc=10.0,
        )
        assert position.hurdle_progress == pytest.approx(1.0, rel=1e-9)

    def test_past_target_is_over_100_percent(self) -> None:
        """Past target > 100%."""
        position = StakerPosition(
            original_stake_btc=1.0,
            cumulative_distributions_btc=15.0,
        )
        assert position.hurdle_progress == pytest.approx(1.5, rel=1e-9)

    def test_zero_stake_zero_progress(self) -> None:
        """Zero stake = zero progress (avoid division by zero)."""
        position = StakerPosition(original_stake_btc=0.0)
        assert position.hurdle_progress == 0.0


class TestHurdleState:
    """Test hurdle_state property."""

    def test_initial_state_is_pre_hurdle(self) -> None:
        """New position starts in PRE_HURDLE."""
        position = StakerPosition(original_stake_btc=1.0)
        assert position.hurdle_state == StakerHurdleState.PRE_HURDLE

    def test_below_target_is_pre_hurdle(self) -> None:
        """Below target = PRE_HURDLE."""
        position = StakerPosition(
            original_stake_btc=1.0,
            cumulative_distributions_btc=9.9,
        )
        assert position.hurdle_state == StakerHurdleState.PRE_HURDLE

    def test_at_target_is_hurdle_met(self) -> None:
        """Exactly at target = HURDLE_MET (before lock)."""
        position = StakerPosition(
            original_stake_btc=1.0,
            cumulative_distributions_btc=10.0,
        )
        assert position.hurdle_state == StakerHurdleState.HURDLE_MET

    def test_past_target_is_hurdle_met_if_not_locked(self) -> None:
        """Past target but not locked = HURDLE_MET."""
        position = StakerPosition(
            original_stake_btc=1.0,
            cumulative_distributions_btc=15.0,
            post_hurdle_locked=False,
        )
        assert position.hurdle_state == StakerHurdleState.HURDLE_MET

    def test_locked_is_post_hurdle_locked(self) -> None:
        """Locked = POST_HURDLE_LOCKED."""
        position = StakerPosition(
            original_stake_btc=1.0,
            cumulative_distributions_btc=10.0,
            post_hurdle_locked=True,
        )
        assert position.hurdle_state == StakerHurdleState.POST_HURDLE_LOCKED

    def test_locked_overrides_cumulative_check(self) -> None:
        """Once locked, state is POST_HURDLE_LOCKED regardless of distributions."""
        # Edge case: locked but cumulative was reset (shouldn't happen, but state is permanent)
        position = StakerPosition(
            original_stake_btc=1.0,
            cumulative_distributions_btc=0.0,
            post_hurdle_locked=True,
        )
        assert position.hurdle_state == StakerHurdleState.POST_HURDLE_LOCKED


class TestRecordDistributionBtc:
    """Test record_distribution_btc method."""

    def test_records_positive_amount(self) -> None:
        """Positive amount is added to cumulative."""
        position = StakerPosition(original_stake_btc=1.0)
        position.record_distribution_btc(2.5)
        assert position.cumulative_distributions_btc == pytest.approx(2.5, rel=1e-9)

    def test_accumulates_multiple_distributions(self) -> None:
        """Multiple distributions accumulate."""
        position = StakerPosition(original_stake_btc=1.0)
        position.record_distribution_btc(2.0)
        position.record_distribution_btc(3.0)
        position.record_distribution_btc(1.5)
        assert position.cumulative_distributions_btc == pytest.approx(6.5, rel=1e-9)

    def test_ignores_zero_amount(self) -> None:
        """Zero amount is ignored."""
        position = StakerPosition(original_stake_btc=1.0)
        position.record_distribution_btc(0.0)
        assert position.cumulative_distributions_btc == 0.0

    def test_ignores_negative_amount(self) -> None:
        """Negative amount is ignored."""
        position = StakerPosition(original_stake_btc=1.0)
        position.record_distribution_btc(-1.0)
        assert position.cumulative_distributions_btc == 0.0

    def test_returns_current_state(self) -> None:
        """Method returns current hurdle state."""
        position = StakerPosition(original_stake_btc=1.0)
        state = position.record_distribution_btc(5.0)
        assert state == StakerHurdleState.PRE_HURDLE


class TestHurdleLocking:
    """Test hurdle locking mechanics."""

    def test_reaching_target_triggers_lock(self) -> None:
        """Reaching exactly 10x triggers post_hurdle_locked."""
        position = StakerPosition(original_stake_btc=1.0)
        position.record_distribution_btc(10.0)

        assert position.post_hurdle_locked is True
        assert position.hurdle_state == StakerHurdleState.POST_HURDLE_LOCKED

    def test_exceeding_target_triggers_lock(self) -> None:
        """Exceeding 10x triggers post_hurdle_locked."""
        position = StakerPosition(original_stake_btc=1.0)
        position.record_distribution_btc(15.0)

        assert position.post_hurdle_locked is True
        assert position.hurdle_state == StakerHurdleState.POST_HURDLE_LOCKED

    def test_incremental_crossing_triggers_lock(self) -> None:
        """Incrementally crossing threshold triggers lock."""
        position = StakerPosition(original_stake_btc=1.0)
        position.record_distribution_btc(8.0)
        assert position.post_hurdle_locked is False

        position.record_distribution_btc(3.0)  # 8 + 3 = 11 > 10
        assert position.post_hurdle_locked is True

    def test_lock_records_btc_level(self) -> None:
        """Lock records the BTC level when triggered."""
        position = StakerPosition(original_stake_btc=1.0)
        position.record_distribution_btc(12.5)

        assert position.hurdle_locked_at_btc == pytest.approx(12.5, rel=1e-9)

    def test_lock_is_permanent(self) -> None:
        """Once locked, stays locked even with more distributions."""
        position = StakerPosition(original_stake_btc=1.0)
        position.record_distribution_btc(10.0)
        assert position.post_hurdle_locked is True

        # More distributions don't change locked state
        position.record_distribution_btc(100.0)
        assert position.post_hurdle_locked is True
        assert position.hurdle_state == StakerHurdleState.POST_HURDLE_LOCKED

    def test_lock_preserves_original_lock_level(self) -> None:
        """Lock level is preserved even with more distributions."""
        position = StakerPosition(original_stake_btc=1.0)
        position.record_distribution_btc(10.5)
        original_lock_level = position.hurdle_locked_at_btc

        position.record_distribution_btc(50.0)
        assert position.hurdle_locked_at_btc == original_lock_level


class TestHurdleWithWeightedStake:
    """Test that hurdle mechanics integrate with weighted stake from Slice 3."""

    def test_weighted_stake_unaffected_by_hurdle(self) -> None:
        """Weighted stake is independent of hurdle state."""
        position = StakerPosition(original_stake_btc=10.0)

        # Before hurdle
        weighted_before = position.weighted_stake
        assert position.hurdle_state == StakerHurdleState.PRE_HURDLE

        # Cross hurdle
        position.record_distribution_btc(100.0)
        assert position.hurdle_state == StakerHurdleState.POST_HURDLE_LOCKED

        # Weighted stake unchanged
        assert position.weighted_stake == weighted_before

    def test_hurdle_progress_independent_of_weighted_stake(self) -> None:
        """Hurdle progress uses original stake, not weighted stake."""
        position = StakerPosition(original_stake_btc=100.0)  # weighted = 1000

        # 500 BTC distributions on 100 BTC stake = 50% progress
        position.record_distribution_btc(500.0)
        assert position.hurdle_progress == pytest.approx(0.5, rel=1e-9)

        # NOT based on weighted stake (1000), based on original (100)
        # target = 100 * 10 = 1000, progress = 500/1000 = 0.5


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_zero_stake_never_locks(self) -> None:
        """Zero stake position never reaches hurdle."""
        position = StakerPosition(original_stake_btc=0.0)
        position.record_distribution_btc(1000.0)

        # Target is 0, so threshold check passes but no lock because target <= 0
        assert position.post_hurdle_locked is False

    def test_very_small_stake_locks_correctly(self) -> None:
        """Very small stake still locks at 10x."""
        position = StakerPosition(original_stake_btc=0.001)  # 0.001 BTC
        position.record_distribution_btc(0.01)  # 10x

        assert position.post_hurdle_locked is True
        assert position.hurdle_target_btc == pytest.approx(0.01, rel=1e-9)

    def test_custom_multiple_respected(self) -> None:
        """Custom hurdle multiple is respected."""
        position = StakerPosition(
            original_stake_btc=1.0,
            hurdle_target_multiple=5.0,  # 5x instead of 10x
        )
        position.record_distribution_btc(5.0)

        assert position.post_hurdle_locked is True
        assert position.hurdle_target_btc == pytest.approx(5.0, rel=1e-9)


class TestConservation:
    """Test that hurdle mechanics don't break conservation properties."""

    def test_distributions_fully_tracked(self) -> None:
        """All distributions are tracked cumulatively."""
        position = StakerPosition(original_stake_btc=1.0)

        total = 0.0
        for i in range(20):
            amount = 0.5
            position.record_distribution_btc(amount)
            total += amount

        assert position.cumulative_distributions_btc == pytest.approx(total, rel=1e-9)

    def test_hurdle_state_deterministic(self) -> None:
        """Same inputs produce same hurdle state."""
        def create_position() -> StakerPosition:
            p = StakerPosition(original_stake_btc=1.0)
            p.record_distribution_btc(5.0)
            p.record_distribution_btc(3.0)
            p.record_distribution_btc(2.5)
            return p

        p1 = create_position()
        p2 = create_position()

        assert p1.hurdle_state == p2.hurdle_state
        assert p1.post_hurdle_locked == p2.post_hurdle_locked
        assert p1.cumulative_distributions_btc == p2.cumulative_distributions_btc


class TestDistributionRateFactor:
    """Test distribution_rate_factor property for rate reduction."""

    def test_post_hurdle_rate_factor_constant(self) -> None:
        """Post-hurdle rate factor matches investor lane ratio (~5.26%)."""
        assert STAKER_POST_HURDLE_RATE_FACTOR == pytest.approx(0.0526, rel=1e-3)

    def test_ups_to_btc_rate_exists(self) -> None:
        """UPS-to-BTC conversion rate is defined."""
        assert UPS_TO_BTC_RATE > 0
        assert UPS_TO_BTC_RATE == 0.00001  # Same as F_i rate placeholder

    def test_pre_hurdle_rate_factor_is_1(self) -> None:
        """PRE_HURDLE staker gets full rate (factor = 1.0)."""
        position = StakerPosition(original_stake_btc=1.0)
        assert position.hurdle_state == StakerHurdleState.PRE_HURDLE
        assert position.distribution_rate_factor == 1.0

    def test_hurdle_met_rate_factor_is_1(self) -> None:
        """HURDLE_MET staker gets full rate (factor = 1.0)."""
        position = StakerPosition(
            original_stake_btc=1.0,
            cumulative_distributions_btc=10.0,
            post_hurdle_locked=False,
        )
        assert position.hurdle_state == StakerHurdleState.HURDLE_MET
        assert position.distribution_rate_factor == 1.0

    def test_post_hurdle_locked_rate_factor_is_reduced(self) -> None:
        """POST_HURDLE_LOCKED staker gets reduced rate."""
        position = StakerPosition(original_stake_btc=1.0)
        position.record_distribution_btc(10.0)  # Triggers lock

        assert position.hurdle_state == StakerHurdleState.POST_HURDLE_LOCKED
        assert position.distribution_rate_factor == pytest.approx(
            STAKER_POST_HURDLE_RATE_FACTOR, rel=1e-9
        )

    def test_rate_factor_reduction_ratio(self) -> None:
        """Post-hurdle rate is ~5.26% of pre-hurdle rate."""
        position_pre = StakerPosition(original_stake_btc=1.0)
        position_post = StakerPosition(original_stake_btc=1.0, post_hurdle_locked=True)

        ratio = position_post.distribution_rate_factor / position_pre.distribution_rate_factor
        assert ratio == pytest.approx(0.0526, rel=1e-3)

    def test_rate_factor_after_crossing_threshold(self) -> None:
        """Rate factor changes after crossing hurdle threshold."""
        position = StakerPosition(original_stake_btc=1.0)

        # Before crossing
        assert position.distribution_rate_factor == 1.0

        # Cross threshold incrementally
        position.record_distribution_btc(5.0)
        assert position.distribution_rate_factor == 1.0  # Still pre-hurdle

        position.record_distribution_btc(5.0)  # Now at 10.0, triggers lock
        assert position.distribution_rate_factor == pytest.approx(
            STAKER_POST_HURDLE_RATE_FACTOR, rel=1e-9
        )

    def test_rate_factor_permanence(self) -> None:
        """Rate factor stays reduced permanently after lock."""
        position = StakerPosition(original_stake_btc=1.0)
        position.record_distribution_btc(10.0)

        # Record more distributions
        for _ in range(10):
            position.record_distribution_btc(100.0)
            assert position.distribution_rate_factor == pytest.approx(
                STAKER_POST_HURDLE_RATE_FACTOR, rel=1e-9
            )


class TestDuConservationAccounting:
    """Test Du pool conservation accounting on EpochDistribution."""

    def test_epoch_distribution_has_withheld_field(self) -> None:
        """EpochDistribution tracks du_hurdle_withheld."""
        result = EpochDistribution(epoch=1, total_rewards=1000.0)
        assert hasattr(result, "du_hurdle_withheld")
        assert result.du_hurdle_withheld == 0.0

    def test_epoch_distribution_has_actual_distributed_field(self) -> None:
        """EpochDistribution tracks du_actual_distributed."""
        result = EpochDistribution(epoch=1, total_rewards=1000.0)
        assert hasattr(result, "du_actual_distributed")
        assert result.du_actual_distributed == 0.0

    def test_conservation_check_passes_when_balanced(self) -> None:
        """Conservation check passes when distributed + withheld == pool."""
        result = EpochDistribution(epoch=1, total_rewards=1000.0)
        result.du_pool = 100.0
        result.du_actual_distributed = 80.0
        result.du_hurdle_withheld = 20.0

        assert result.du_conservation_check is True

    def test_conservation_check_fails_when_unbalanced(self) -> None:
        """Conservation check fails when distributed + withheld != pool."""
        result = EpochDistribution(epoch=1, total_rewards=1000.0)
        result.du_pool = 100.0
        result.du_actual_distributed = 80.0
        result.du_hurdle_withheld = 10.0  # Missing 10

        assert result.du_conservation_check is False

    def test_conservation_check_handles_floating_point(self) -> None:
        """Conservation check tolerates floating point imprecision."""
        result = EpochDistribution(epoch=1, total_rewards=1000.0)
        result.du_pool = 100.0
        # Simulate floating point accumulation
        result.du_actual_distributed = 80.0 + 1e-12
        result.du_hurdle_withheld = 20.0 - 1e-12

        assert result.du_conservation_check is True

    def test_withheld_amount_calculation(self) -> None:
        """Withheld amount is (1 - rate_factor) * pre_reduction_share."""
        pre_reduction = 100.0
        rate_factor = STAKER_POST_HURDLE_RATE_FACTOR
        expected_actual = pre_reduction * rate_factor
        expected_withheld = pre_reduction - expected_actual

        assert expected_withheld == pytest.approx(
            pre_reduction * (1 - rate_factor), rel=1e-9
        )
        assert expected_actual + expected_withheld == pytest.approx(
            pre_reduction, rel=1e-9
        )


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

def _a07_receipt(r):
    return {**vars(r), "participant_rewards": dict(r.participant_rewards)}

def test_a01_exact_retry_has_no_effects():
    pool, _ = _a07_pool()
    first = pool.distribute_epoch(1, 100, "a")
    before = _a07_state(pool)
    again = pool.distribute_epoch(1, 100.0, "a")
    assert _a07_state(pool) == before
    assert _a07_receipt(again) == _a07_receipt(first) and again is not first

def test_a02_late_retry_owns_first_receipt_and_configuration(monkeypatch):
    pool, _ = _a07_pool()
    result = pool.distribute_epoch(1, 100, "a")
    expected = _a07_receipt(result)
    pool.distribute_epoch(3, 50, "a")
    pool.register_participant("new", PT.UN, AL.UN)
    monkeypatch.setitem(pm.POOL_PERCENTAGES, "fund", 0.01)
    try:
        result.participant_rewards["alice"] = 999
        result.total_rewards = 999
    except (TypeError, AttributeError):
        pass
    before = _a07_state(pool)
    retry = pool.distribute_epoch(1, 100, "a")
    assert _a07_receipt(retry) == expected and _a07_state(pool) == before
    assert retry is not result

@pytest.mark.parametrize("total,context", [(101, "a"), (100, "b"), (100, None)])
def test_a03_conflicts_leave_complete_state_unchanged(total, context):
    pool, _ = _a07_pool()
    pool.distribute_epoch(1, 100, "a")
    before = _a07_state(pool)
    with pytest.raises(ValueError):
        pool.distribute_epoch(1, total, context)
    assert _a07_state(pool) == before

@pytest.mark.parametrize("label", ["bool", "negative", "nan", "inf", "string",
    "decimal", "float_subclass", "hostile", "epoch_bool", "epoch_float", "epoch_negative",
    "context_empty", "context_whitespace", "context_number"])
def test_a04_invalid_request_rejects_before_effects(label):
    class Hostile:
        def __float__(self): raise AssertionError("coercion hook")
        def __mul__(self, other): raise AssertionError("arithmetic hook")
    class FloatSubclass(float): pass
    values = {"bool": True, "negative": -1, "nan": float("nan"), "inf": float("inf"),
        "string": "100", "decimal": Decimal("100"), "float_subclass": FloatSubclass(100),
        "hostile": Hostile()}
    epoch = {"epoch_bool": True, "epoch_float": 1.0, "epoch_negative": -1}.get(label, 1)
    context = {"context_empty": "", "context_whitespace": " ", "context_number": 1}.get(label, "a")
    pool, _ = _a07_pool()
    before = _a07_state(pool)
    with pytest.raises(ValueError):
        pool.distribute_epoch(epoch, values.get(label, 100), context)
    assert _a07_state(pool) == before

def test_a05_unrecorded_old_epoch_rejects_but_gaps_allowed():
    pool, _ = _a07_pool()
    pool.distribute_epoch(3, 100)
    before = _a07_state(pool)
    with pytest.raises(ValueError): pool.distribute_epoch(2, 100)
    assert _a07_state(pool) == before
    assert pool.distribute_epoch(8, 100).epoch == 8

def test_a06_zero_normalization_and_empty_roster_preserve_math():
    pool = PoolDistributor()
    pool.distribute_epoch(0, -0.0)
    before = _a07_state(pool)
    assert pool.distribute_epoch(0, 0).total_rewards == 0
    assert _a07_state(pool) == before
    r = pool.distribute_epoch(1, 100)
    assert r.fund_pool == 4 and r.fund_accumulated == 4
    assert r.participant_rewards == {} and r.drip_distributed == 0
    before = _a07_state(pool)
    pool.distribute_epoch(1, 100.0)
    assert _a07_state(pool) == before

def test_a07_late_participant_failure_is_atomic():
    pool, _ = _a07_pool()
    bad = pool.register_participant("late", PT.DU, AL.DU)
    bad.ups_balance = "invalid"
    before = _a07_state(pool)
    with pytest.raises((TypeError, ValueError)):
        pool.distribute_epoch(1, 100)
    assert _a07_state(pool) == before

@pytest.mark.parametrize("field", ["balance", "fund", "drip"])
def test_a08_finite_request_cannot_publish_infinite_prospective_state(field):
    pool, p = _a07_pool()
    maximum = float.fromhex("0x1.fffffffffffffp+1023")
    if field == "balance": p.ups_balance = maximum
    elif field == "fund": pool.accumulated_fund = maximum
    else: pool.total_drip_distributed = maximum
    before = _a07_state(pool)
    with pytest.raises(ValueError): pool.distribute_epoch(1, 1e308)
    assert _a07_state(pool) == before

def test_a12_concurrent_exact_requests_commit_once():
    pool, _ = _a07_pool()
    barrier = Barrier(4)
    def call():
        barrier.wait(timeout=3)
        return pool.distribute_epoch(1, 100, "a")
    with ThreadPoolExecutor(4) as executor: results = list(executor.map(lambda _: call(), range(4)))
    assert pool.accumulated_fund == 4
    assert pool.participants["alice"].ups_balance == pytest.approx(76.8)
    assert all(_a07_receipt(x) == _a07_receipt(results[0]) for x in results)
    assert len({id(x) for x in results}) == 4

def test_a13_concurrent_conflicts_have_one_winner():
    pool, _ = _a07_pool()
    barrier = Barrier(2)
    def call(total):
        barrier.wait(timeout=3)
        try: return (total, pool.distribute_epoch(1, total, "a"))
        except ValueError: return (total, None)
    with ThreadPoolExecutor(2) as executor: results = list(executor.map(call, (100, 200)))
    winners = [(n, r) for n, r in results if r is not None]
    assert len(winners) == 1
    amount, receipt = winners[0]
    assert pool.accumulated_fund == pytest.approx(amount * 0.04)
    assert pool.participants["alice"].ups_balance == pytest.approx(amount * 0.768)

def test_a15_hurdle_crossing_and_retry_keep_first_lock():
    pool, p = _a07_pool()
    position = p.staker_position
    position.cumulative_distributions_btc = 0.00999
    first = pool.distribute_epoch(1, 100)
    assert first.du_actual_distributed == pytest.approx(3.2)
    locked = position.hurdle_locked_at_btc
    before = _a07_state(pool)
    pool.distribute_epoch(1, 100)
    assert _a07_state(pool) == before
    second = pool.distribute_epoch(2, 100)
    assert second.du_actual_distributed == pytest.approx(3.2 * 0.0526)
    assert position.hurdle_locked_at_btc == locked

def test_a16_shared_position_keeps_original_sequential_crossing_formula():
    pool, p = _a07_pool()
    position = p.staker_position
    position.cumulative_distributions_btc = 0.00999
    q = pool.register_participant("bob", PT.DU, AL.DU, staker_position=position)
    receipt = pool.distribute_epoch(1, 100)
    assert p.staker_position is q.staker_position is position
    assert receipt.participant_rewards["alice"] == pytest.approx(38.4)
    assert receipt.participant_rewards["bob"] == pytest.approx(36.88416)
    assert position.hurdle_locked_at_btc == pytest.approx(0.010006)
    assert position.cumulative_distributions_btc == pytest.approx(0.0100068416)

def test_a17_missing_tiers_do_not_get_new_redistribution_policy():
    pool, _ = _a07_pool()
    receipt = pool.distribute_epoch(1, 100)
    assert receipt.participant_rewards["alice"] == pytest.approx(76.8)
    assert receipt.drip_distributed == pytest.approx(12.8)
    assert receipt.fund_pool == pytest.approx(4)
    assert receipt.du_actual_distributed == pytest.approx(3.2)
    assert receipt.du_hurdle_withheld == 0


import json

_SLOTS = ("stakeholder", "participant_drip", "fund", "lifetime_drip")
_PRIORS = (9007199254740993, 9007199254740992.0)


def _credit_set(pool, person, slot, value):
    if slot in ("stakeholder", "participant_drip"):
        person.ups_balance = value
    else:
        field = "accumulated_fund" if slot == "fund" else "total_drip_distributed"
        setattr(pool, field, value)


def _credit_pool(slot, prior, bound):
    ledger = EpochLedger("a") if bound else None
    pool = PoolDistributor(ledger=ledger)
    person = pool.register_participant("alice", PT.UN,
        AL.DU if slot == "participant_drip" else AL.UN)
    _credit_set(pool, person, slot, prior)
    return pool, person, ledger, 4 if slot == "participant_drip" else 1


def _credit_snapshot(pool, ledger):
    cache = {epoch: (amount, context, _a07_receipt(receipt), None if entry is None else
        (id(entry), entry.to_dict(), dict(entry.participant_rewards)))
        for epoch, (amount, context, receipt, entry) in pool._epochs.items()}
    return _a07_state(pool, ledger), deepcopy(cache)


def _credit_emit(pool, receipt, tmp_path):
    people = {pid: {**vars(person), "staker_position": None if person.staker_position is None else
        {k: v for k, v in vars(person.staker_position).items() if k != "stake_timestamp"}}
        for pid, person in pool.participants.items()}
    data = {"receipt": _a07_receipt(receipt), "participants": people,
        "fund": pool.accumulated_fund, "drip": pool.total_drip_distributed,
        "epochs": {epoch: {"amount": value[0], "context": value[1],
            "receipt": _a07_receipt(value[2])} for epoch, value in pool._epochs.items()},
        "ledger": [] if pool._ledger is None else [{"epoch": e.epoch_number,
            "total": e.total_fi_distributed, "pools": dict(e.pool_allocations),
            "rewards": dict(e.participant_rewards)} for e in pool._ledger.entries]}
    (tmp_path / "native-control.json").write_text(json.dumps(data, sort_keys=True,
        separators=(",", ":"), allow_nan=False) + "\n", encoding="utf-8")


@pytest.mark.parametrize("slot,prior,bound", [
    (slot, prior, bound) for slot in _SLOTS for prior in _PRIORS for bound in (False, True)],
    ids=[f"{slot}-{kind}-{mode}" for slot in _SLOTS
         for kind in ("large_int", "large_float") for mode in ("standalone", "ledger")])
def test_positive_credit_absorption_refuses_before_all_publication(slot, prior, bound):
    pool, person, ledger, total = _credit_pool(slot, prior, bound)
    if slot == "participant_drip":
        stakeholder_after = prior + 1.92
        assert stakeholder_after > prior
        assert stakeholder_after + 0.512 == stakeholder_after
    before = _credit_snapshot(pool, ledger)
    with pytest.raises(ValueError):
        pool.distribute_epoch(1, total, "a")
    assert _credit_snapshot(pool, ledger) == before


@pytest.mark.parametrize("bound", [False, True], ids=["standalone", "ledger"])
def test_late_absorption_preserves_earlier_participant_hurdle_and_existing_epoch(bound):
    ledger = EpochLedger("a") if bound else None
    pool, first = _a07_pool(ledger)
    pool.distribute_epoch(1, 100, "a")
    late = pool.register_participant("late", PT.UN, AL.UN)
    late.ups_balance = 9007199254740992.0
    before = _credit_snapshot(pool, ledger)
    with pytest.raises(ValueError):
        pool.distribute_epoch(2, 1, "a")
    assert _credit_snapshot(pool, ledger) == before


@pytest.mark.parametrize("slot,bound", [(slot, b) for slot in _SLOTS for b in (False, True)],
    ids=[f"{slot}-{mode}" for slot in _SLOTS for mode in ("standalone", "ledger")])
def test_refused_epoch_can_commit_after_repair_then_replay_without_revalidating_books(slot, bound):
    pool, person, ledger, total = _credit_pool(slot, 9007199254740992.0, bound)
    before = _credit_snapshot(pool, ledger)
    with pytest.raises(ValueError):
        pool.distribute_epoch(1, total, "a")
    assert _credit_snapshot(pool, ledger) == before
    _credit_set(pool, person, slot, 0)
    first = pool.distribute_epoch(1, total, "a")
    assert first.participant_rewards["alice"] > 0 and first.fund_pool > 0
    assert ledger is None or len(ledger.entries) == 1
    _credit_set(pool, person, slot, 9007199254740992.0)
    committed = _credit_snapshot(pool, ledger)
    again = pool.distribute_epoch(1, total, "a")
    assert _a07_receipt(again) == _a07_receipt(first) and again is not first
    assert _credit_snapshot(pool, ledger) == committed


@pytest.mark.parametrize("prior,bound", [(n, b) for n in (9007199254740992, 9007199254740992.0)
    for b in (False, True)], ids=[f"{kind}-{mode}" for kind in ("int", "float")
    for mode in ("standalone", "ledger")])
def test_zero_increments_are_admitted_with_large_books(prior, bound, tmp_path):
    pool, person, ledger, _ = _credit_pool("stakeholder", prior, bound)
    pool.accumulated_fund = pool.total_drip_distributed = prior
    result = pool.distribute_epoch(1, 0, "a")
    assert person.ups_balance == pool.accumulated_fund == pool.total_drip_distributed == prior
    assert result.participant_rewards == {"alice": 0.0}
    assert result.fund_pool == result.drip_distributed == 0
    _credit_emit(pool, result, tmp_path)


@pytest.mark.parametrize("label,total,opening,expected,bound", [
    (label, total, opening, expected, bound)
    for label, total, opening, expected in (("full9_fraction", 0.1, 1.25, None),
        ("single_fraction", 1, 0.1, 0.1304), ("single_seeded", 10000, 0.1, 304.1),
        ("single_large", 10000, 9007199254740992.0, 9007199254741296))
    for bound in (False, True)], ids=[f"{label}-{mode}" for label in
    ("full9_fraction", "single_fraction", "single_seeded", "single_large")
    for mode in ("standalone", "ledger")])
def test_useful_fractional_and_representable_large_credits_remain_admitted(label, total, opening, expected, bound, tmp_path):
    ledger = EpochLedger("a") if bound else None
    pool = PoolDistributor(ledger=ledger)
    cohort = [(pt, al) for pt in PT for al in AL] if label == "full9_fraction" else [(PT.UN, AL.UN)]
    for i, (pt, al) in enumerate(cohort):
        pool.register_participant("p" + str(i), pt, al).ups_balance = opening
    result = pool.distribute_epoch(1, total, "a")
    assert all(p.ups_balance > opening for p in pool.participants.values())
    assert all(v > 0 for v in result.participant_rewards.values())
    if expected is not None:
        actual = pool.participants["p0"].ups_balance
        assert actual == expected if label == "single_large" else actual == pytest.approx(expected)
    _credit_emit(pool, result, tmp_path)


@pytest.mark.parametrize("bound", [False, True], ids=["standalone", "ledger"])
def test_shared_hurdle_first_crossing_order_retains_original_rewards(bound, tmp_path):
    ledger = EpochLedger("a") if bound else None
    pool, alice = _a07_pool(ledger)
    position = alice.staker_position
    position.cumulative_distributions_btc = 0.00999
    bob = pool.register_participant("bob", PT.DU, AL.DU, staker_position=position)
    result = pool.distribute_epoch(1, 100, "a")
    assert alice.staker_position is bob.staker_position is position
    assert result.participant_rewards["alice"] == pytest.approx(38.4)
    assert result.participant_rewards["bob"] == pytest.approx(36.88416)
    assert position.hurdle_locked_at_btc == pytest.approx(0.010006)
    assert position.cumulative_distributions_btc == pytest.approx(0.0100068416)
    _credit_emit(pool, result, tmp_path)
