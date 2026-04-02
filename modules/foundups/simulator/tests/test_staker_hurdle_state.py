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
