"""Weighted stake allocation tests for BTCStakerPool mechanics."""

from __future__ import annotations

import pytest

from modules.foundups.simulator.economics.pool_distribution import (
    STAKE_WEIGHT_EXPONENT,
    StakerPosition,
    btc_stake_weight,
    calculate_weighted_share,
    calculate_total_weighted_stake,
    distribute_weighted_staker_pool,
)


class TestStakeWeight:
    """Test btc_stake_weight function."""

    def test_weight_ratio_100x_stake_equals_1000x_weight(self) -> None:
        """100x stake produces 1000x weight at exponent 1.5."""
        weight_1 = btc_stake_weight(1.0)
        weight_100 = btc_stake_weight(100.0)

        ratio = weight_100 / weight_1
        assert ratio == pytest.approx(1000.0, rel=1e-9)

    def test_weight_at_1_btc_equals_1(self) -> None:
        """1 BTC stake has weight 1.0."""
        assert btc_stake_weight(1.0) == pytest.approx(1.0, rel=1e-9)

    def test_weight_at_10_btc(self) -> None:
        """10 BTC stake has weight ~31.62 (10^1.5)."""
        expected = 10.0 ** 1.5  # ≈ 31.62
        assert btc_stake_weight(10.0) == pytest.approx(expected, rel=1e-9)

    def test_weight_at_01_btc(self) -> None:
        """0.1 BTC stake has weight ~0.0316 (0.1^1.5)."""
        expected = 0.1 ** 1.5  # ≈ 0.0316
        assert btc_stake_weight(0.1) == pytest.approx(expected, rel=1e-9)

    def test_zero_stake_returns_zero_weight(self) -> None:
        """Zero stake returns zero weight."""
        assert btc_stake_weight(0.0) == 0.0

    def test_negative_stake_returns_zero_weight(self) -> None:
        """Negative stake returns zero weight (edge case protection)."""
        assert btc_stake_weight(-1.0) == 0.0

    def test_custom_exponent(self) -> None:
        """Custom exponent works correctly."""
        # At exponent 2.0: 10^2 = 100
        assert btc_stake_weight(10.0, exponent=2.0) == pytest.approx(100.0, rel=1e-9)

    def test_default_exponent_is_1_5(self) -> None:
        """Default exponent is 1.5."""
        assert STAKE_WEIGHT_EXPONENT == 1.5


class TestCalculateWeightedShare:
    """Test calculate_weighted_share function."""

    def test_single_staker_gets_full_amount(self) -> None:
        """Single staker gets the full pool amount."""
        stake = 1.0
        pool_amount = 1000.0
        total_weighted = btc_stake_weight(stake)

        share = calculate_weighted_share(stake, total_weighted, pool_amount)
        assert share == pytest.approx(pool_amount, rel=1e-9)

    def test_equal_stakes_get_equal_shares(self) -> None:
        """Equal stakes get equal shares."""
        stake = 1.0
        pool_amount = 1000.0
        # 2 stakers with equal stakes
        total_weighted = 2 * btc_stake_weight(stake)

        share = calculate_weighted_share(stake, total_weighted, pool_amount)
        assert share == pytest.approx(500.0, rel=1e-9)

    def test_zero_total_weight_returns_zero(self) -> None:
        """Zero total weight returns zero share."""
        share = calculate_weighted_share(1.0, 0.0, 1000.0)
        assert share == 0.0

    def test_zero_pool_amount_returns_zero(self) -> None:
        """Zero pool amount returns zero share."""
        share = calculate_weighted_share(1.0, btc_stake_weight(1.0), 0.0)
        assert share == 0.0


class TestDistributeWeightedStakerPool:
    """Test distribute_weighted_staker_pool function."""

    def test_conservation_of_pool_amount(self) -> None:
        """Sum of distributions equals pool amount (with tolerance)."""
        stakes = {
            "staker_a": 1.0,
            "staker_b": 5.0,
            "staker_c": 10.0,
            "staker_d": 0.5,
        }
        pool_amount = 10000.0

        distributions = distribute_weighted_staker_pool(stakes, pool_amount)

        total_distributed = sum(distributions.values())
        assert total_distributed == pytest.approx(pool_amount, rel=1e-9)

    def test_equal_stakes_equal_shares(self) -> None:
        """Equal stakes produce equal shares."""
        stakes = {
            "staker_a": 1.0,
            "staker_b": 1.0,
            "staker_c": 1.0,
        }
        pool_amount = 3000.0

        distributions = distribute_weighted_staker_pool(stakes, pool_amount)

        for staker_id, share in distributions.items():
            assert share == pytest.approx(1000.0, rel=1e-9)

    def test_weighted_share_advantage_in_two_staker_pool(self) -> None:
        """Larger staker gets exponentially larger share in 2-staker pool."""
        stakes = {
            "small": 1.0,    # weight = 1.0
            "large": 100.0,  # weight = 1000.0
        }
        pool_amount = 10010.0  # Convenient number for calculation

        distributions = distribute_weighted_staker_pool(stakes, pool_amount)

        # Total weight = 1 + 1000 = 1001
        # small share = (1/1001) * 10010 = 10.0
        # large share = (1000/1001) * 10010 = 10000.0
        assert distributions["small"] == pytest.approx(10.0, rel=1e-6)
        assert distributions["large"] == pytest.approx(10000.0, rel=1e-6)

        # Large staker gets 1000x more than small staker
        ratio = distributions["large"] / distributions["small"]
        assert ratio == pytest.approx(1000.0, rel=1e-6)

    def test_empty_stakes_returns_empty_dict(self) -> None:
        """Empty stakes dict returns empty distributions."""
        distributions = distribute_weighted_staker_pool({}, 1000.0)
        assert distributions == {}

    def test_zero_pool_amount_returns_empty_dict(self) -> None:
        """Zero pool amount returns empty dict."""
        stakes = {"staker_a": 1.0}
        distributions = distribute_weighted_staker_pool(stakes, 0.0)
        assert distributions == {}

    def test_single_staker_gets_full_amount(self) -> None:
        """Single staker gets the entire pool."""
        stakes = {"solo": 5.0}
        pool_amount = 500.0

        distributions = distribute_weighted_staker_pool(stakes, pool_amount)

        assert distributions["solo"] == pytest.approx(pool_amount, rel=1e-9)

    def test_all_zero_stakes_returns_zero_shares(self) -> None:
        """All zero stakes returns zero shares for all."""
        stakes = {
            "staker_a": 0.0,
            "staker_b": 0.0,
        }
        pool_amount = 1000.0

        distributions = distribute_weighted_staker_pool(stakes, pool_amount)

        assert distributions["staker_a"] == 0.0
        assert distributions["staker_b"] == 0.0


class TestCalculateTotalWeightedStake:
    """Test calculate_total_weighted_stake function."""

    def test_sum_of_weights(self) -> None:
        """Total weighted stake is sum of individual weights."""
        stakes = [1.0, 10.0, 100.0]

        total = calculate_total_weighted_stake(stakes)

        expected = btc_stake_weight(1.0) + btc_stake_weight(10.0) + btc_stake_weight(100.0)
        assert total == pytest.approx(expected, rel=1e-9)

    def test_empty_list_returns_zero(self) -> None:
        """Empty list returns zero."""
        assert calculate_total_weighted_stake([]) == 0.0


class TestStakerPositionWeightedStake:
    """Test StakerPosition.weighted_stake property."""

    def test_weighted_stake_property(self) -> None:
        """StakerPosition has weighted_stake property."""
        position = StakerPosition(original_stake_btc=10.0)

        expected = btc_stake_weight(10.0)
        assert position.weighted_stake == pytest.approx(expected, rel=1e-9)

    def test_zero_btc_stake_weighted_stake(self) -> None:
        """Zero stake has zero weighted stake."""
        position = StakerPosition(original_stake_btc=0.0)
        assert position.weighted_stake == 0.0
