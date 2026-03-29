"""Tests for unified sustainability calculator.

Includes ROC-first validation suite (2026-03-28):
- ROC boundary tests (negative, zero, positive)
- Gate combination matrix (ROC × ROI)
- Invariant assertions
- FAM/pAVS baseline pinning
"""

from __future__ import annotations

import pytest

from modules.foundups.simulator.economics.unified_sustainability import (
    UnifiedSustainabilityCalculator,
    ComputeBackingState,
    RevenueSnapshot,
    F0_MONTHLY_BURN_USD,
)


def test_fee_only_ratio_below_one() -> None:
    """Fee-only revenue is insufficient for sustainability."""
    calc = UnifiedSustainabilityCalculator()
    metrics = calc.calculate_sustainability(
        total_subscribers=0,
        total_angels=0,
        tasks_per_month=0,
        monthly_dex_volume_usd=50_000,
    )
    # Without subscriptions/angels, fee-only ratio should be < 1
    assert metrics.fee_only_ratio < 1.0
    assert not metrics.is_sustainable


def test_combined_ratio_with_subscriptions() -> None:
    """Combined revenue with subscriptions achieves sustainability."""
    calc = UnifiedSustainabilityCalculator()
    metrics = calc.calculate_sustainability(
        total_subscribers=25_000,
        total_angels=200,
        tasks_per_month=500_000,
        monthly_dex_volume_usd=50_000,
    )
    # With subscriptions, combined ratio should be > 1
    assert metrics.combined_ratio > 1.0
    assert metrics.is_sustainable
    assert metrics.sustainability_margin_usd > 0


def test_compute_backing_accumulates() -> None:
    """Compute backing tracks task expenditure."""
    backing = ComputeBackingState()
    backing.record_task("openclaw", cost_usd=0.03, fi_earned=0.01)
    backing.record_task("openclaw", cost_usd=0.03, fi_earned=0.01)

    assert backing.total_tasks_executed == 2
    assert backing.total_compute_usd == 0.06
    assert backing.total_fi_mined == 0.02
    assert backing.compute_per_fi == 3.0  # $0.06 / 0.02 F_i


def test_burn_baseline_is_27k() -> None:
    """Verify burn baseline matches ten_year_projection."""
    assert F0_MONTHLY_BURN_USD == 27_000


def test_sustainability_at_minimum_subscribers() -> None:
    """Find minimum subscribers for ROI-path sustainability (subscription breakeven).

    NOTE: This tests ROI-path (revenue > burn), not ROC-first (compute productivity).
    With tasks_per_month=0, ROC gate cannot pass (no compute activity).
    """
    calc = UnifiedSustainabilityCalculator()

    # Binary search for minimum sustainable subscribers
    low, high = 0, 50_000
    while high - low > 100:
        mid = (low + high) // 2
        metrics = calc.calculate_sustainability(
            total_subscribers=mid,
            total_angels=0,
            tasks_per_month=0,
            monthly_dex_volume_usd=0,
        )
        # Use ROI-path gate (not ROC-first) since no compute activity
        if metrics.is_roi_sustainable:
            high = mid
        else:
            low = mid

    # Should need roughly 6,000-7,000 paying subscribers to break even
    # (60% free × 0 + 40% paying × ~$4.50 ARPU × 85% margin ≈ burn)
    assert 4_000 < high < 10_000


def test_return_on_compute_ratio_matches_margin_over_spend() -> None:
    """RoC should equal compute_margin / compute_spend."""
    calc = UnifiedSustainabilityCalculator()
    metrics = calc.calculate_sustainability(
        total_subscribers=25_000,
        total_angels=200,
        tasks_per_month=500_000,
        monthly_dex_volume_usd=50_000,
    )

    expected = metrics.revenue.compute_margin_usd / metrics.revenue.compute_spend_usd
    assert metrics.return_on_compute_ratio == pytest.approx(expected)
    assert metrics.return_on_compute_ratio == pytest.approx(0.60)
    assert metrics.return_on_compute_percent == pytest.approx(60.0)
    assert metrics.value_per_compute_dollar == pytest.approx(1.60)
    assert metrics.compute_generated_value_usd == pytest.approx(
        metrics.revenue.compute_spend_usd + metrics.revenue.compute_margin_usd
    )
    assert metrics.is_compute_profitable


def test_return_on_compute_zero_when_no_compute_spend() -> None:
    """RoC metrics should stay zero-safe when no compute is executed."""
    calc = UnifiedSustainabilityCalculator()
    metrics = calc.calculate_sustainability(
        total_subscribers=0,
        total_angels=0,
        tasks_per_month=0,
        monthly_dex_volume_usd=0,
        monthly_exits_usd=0,
        monthly_creations_usd=0,
    )

    assert metrics.revenue.compute_spend_usd == 0
    assert metrics.revenue.compute_margin_usd == 0
    assert metrics.return_on_compute_ratio == 0
    assert metrics.return_on_compute_percent == 0
    assert metrics.value_per_compute_dollar == 0
    assert metrics.compute_generated_value_usd == 0
    assert not metrics.is_compute_profitable


def test_to_dict_exports_return_on_compute_fields() -> None:
    """Serialized metrics should include RoC for paper/export paths."""
    calc = UnifiedSustainabilityCalculator()
    metrics = calc.calculate_sustainability(
        total_subscribers=25_000,
        total_angels=200,
        tasks_per_month=500_000,
        monthly_dex_volume_usd=50_000,
    )

    blob = metrics.to_dict()
    # Legacy RoC fields
    assert "return_on_compute_ratio" in blob
    assert "return_on_compute_percent" in blob
    assert "value_per_compute_dollar" in blob
    assert "compute_generated_value_usd" in blob
    assert "is_compute_profitable" in blob
    # ROC-FIRST gates (2026-03-28)
    assert "roc_ratio" in blob
    assert "is_compute_positive" in blob
    assert "is_roi_sustainable" in blob
    assert "is_sustainable" in blob
    # Value assertions
    assert blob["roc_ratio"] == pytest.approx(metrics.roc_ratio)
    assert blob["is_compute_positive"] == metrics.is_compute_positive
    assert blob["is_roi_sustainable"] == metrics.is_roi_sustainable
    assert blob["is_sustainable"] == metrics.is_sustainable
    assert blob["revenue"]["compute_spend_usd"] == pytest.approx(
        metrics.revenue.compute_spend_usd
    )


def test_compute_backing_tracks_true_task_count() -> None:
    """Task telemetry should reflect actual workload, not agent-type count."""
    calc = UnifiedSustainabilityCalculator()
    metrics = calc.calculate_sustainability(
        total_subscribers=0,
        total_angels=0,
        tasks_per_month=500_000,
        monthly_dex_volume_usd=0,
        monthly_exits_usd=0,
        monthly_creations_usd=0,
    )

    assert metrics.compute_backing.total_tasks_executed == 500_000
    assert sum(metrics.compute_backing.tasks_by_agent.values()) == 500_000


# ============================================================================
# ROC-FIRST VALIDATION SUITE (2026-03-28)
# ============================================================================


class TestRocBoundaries:
    """ROC boundary tests: negative, zero, positive."""

    def test_roc_negative_when_margin_negative(self) -> None:
        """ROC < 0 when compute margin is negative (loss scenario)."""
        snapshot = RevenueSnapshot(
            compute_spend_usd=100.0,
            compute_margin_usd=-50.0,  # Loss: cost more than generated
        )
        assert snapshot.return_on_compute_ratio == pytest.approx(-0.5)
        assert snapshot.return_on_compute_ratio < 0

    def test_roc_zero_when_margin_zero(self) -> None:
        """ROC == 0 when compute margin is zero (break-even)."""
        snapshot = RevenueSnapshot(
            compute_spend_usd=100.0,
            compute_margin_usd=0.0,  # Break-even: V_generated == C_compute
        )
        assert snapshot.return_on_compute_ratio == 0.0

    def test_roc_positive_when_margin_positive(self) -> None:
        """ROC > 0 when compute margin is positive (profit)."""
        snapshot = RevenueSnapshot(
            compute_spend_usd=100.0,
            compute_margin_usd=60.0,  # Profit: 60% margin
        )
        assert snapshot.return_on_compute_ratio == pytest.approx(0.6)
        assert snapshot.return_on_compute_ratio > 0

    def test_roc_zero_safe_when_spend_zero(self) -> None:
        """ROC returns 0 (not inf/nan) when compute spend is zero."""
        snapshot = RevenueSnapshot(
            compute_spend_usd=0.0,
            compute_margin_usd=0.0,
        )
        assert snapshot.return_on_compute_ratio == 0.0


class TestGateCombinationMatrix:
    """Gate combination matrix: ROC × ROI through calculator.

    NOTE: The calculator assumes COMPUTE_GROSS_MARGIN=0.60, so ROC is either:
    - 0.60 (positive tasks) → ROC+ gate passes
    - 0.00 (zero tasks) → ROC gate fails (roc_ratio > 0 is False)

    Negative ROC requires negative compute margin, which the current calculator
    design doesn't produce. See TestRocBoundaries for formula-level negative ROC.
    """

    def test_roc_zero_roi_negative_via_calculator(self) -> None:
        """ROC=0 / ROI- → NOT sustainable (no compute, revenue < burn).

        Calculator path: zero tasks + zero revenue vs $27K burn.
        """
        calc = UnifiedSustainabilityCalculator()
        metrics = calc.calculate_sustainability(
            total_subscribers=0,
            total_angels=0,
            tasks_per_month=0,  # ROC = 0 (no compute activity)
            monthly_dex_volume_usd=0,
            monthly_exits_usd=0,
            monthly_creations_usd=0,
        )
        # Verify calculator computed the gates
        assert metrics.roc_ratio == 0.0
        assert not metrics.is_compute_positive  # ROC=0 fails > 0 check
        assert not metrics.is_roi_sustainable  # 0 revenue < $27K burn
        assert not metrics.is_sustainable

    def test_roc_positive_roi_negative_via_calculator(self) -> None:
        """ROC+ / ROI- → NOT sustainable (compute productive, but revenue < burn).

        Calculator path: high tasks (ROC=0.60) + minimal revenue vs $27K burn.
        """
        calc = UnifiedSustainabilityCalculator()
        metrics = calc.calculate_sustainability(
            total_subscribers=1_000,  # ~$300 margin after free tier
            total_angels=0,
            tasks_per_month=500_000,  # ROC = 0.60 (positive)
            monthly_dex_volume_usd=0,
            monthly_exits_usd=0,
            monthly_creations_usd=0,
        )
        # Verify calculator computed the gates
        assert metrics.roc_ratio == pytest.approx(0.60, rel=0.01)
        assert metrics.is_compute_positive  # ROC > 0
        assert not metrics.is_roi_sustainable  # Low revenue < $27K burn
        assert not metrics.is_sustainable

    def test_roc_zero_roi_positive_via_calculator(self) -> None:
        """ROC=0 / ROI+ → NOT sustainable (revenue > burn, but no compute).

        Calculator path: zero tasks + high subscription revenue.
        """
        calc = UnifiedSustainabilityCalculator()
        metrics = calc.calculate_sustainability(
            total_subscribers=25_000,  # High subscription revenue
            total_angels=200,
            tasks_per_month=0,  # ROC = 0 (no compute activity)
            monthly_dex_volume_usd=50_000,
        )
        # Verify calculator computed the gates
        assert metrics.roc_ratio == 0.0
        assert not metrics.is_compute_positive  # ROC=0 fails > 0 check
        assert metrics.is_roi_sustainable  # High revenue > $27K burn
        assert not metrics.is_sustainable  # Both gates required

    def test_roc_positive_roi_positive_via_calculator(self) -> None:
        """ROC+ / ROI+ → sustainable (both gates pass).

        Calculator path: high tasks + high revenue = Year1 baseline.
        """
        calc = UnifiedSustainabilityCalculator()
        metrics = calc.calculate_sustainability(
            total_subscribers=25_000,
            total_angels=200,
            tasks_per_month=500_000,  # ROC = 0.60 (positive)
            monthly_dex_volume_usd=50_000,
        )
        # Verify calculator computed the gates
        assert metrics.roc_ratio == pytest.approx(0.60, rel=0.01)
        assert metrics.is_compute_positive  # ROC > 0
        assert metrics.is_roi_sustainable  # Revenue > burn
        assert metrics.is_sustainable  # Both gates pass


class TestRocNegativeFormula:
    """Formula-level tests for negative ROC scenarios.

    NOTE: The calculator design assumes positive compute margin (60%).
    These tests validate that RevenueSnapshot correctly handles negative
    margin inputs, which would occur if compute costs exceeded revenue.
    """

    def test_negative_margin_produces_negative_roc(self) -> None:
        """ROC < 0 when compute margin is negative (loss scenario)."""
        snapshot = RevenueSnapshot(
            compute_spend_usd=100.0,
            compute_margin_usd=-50.0,  # Loss: cost more than generated
        )
        assert snapshot.return_on_compute_ratio == pytest.approx(-0.5)
        assert snapshot.return_on_compute_ratio < 0

    def test_negative_roc_fails_gate(self) -> None:
        """Negative ROC would fail is_compute_positive gate."""
        # This tests the gate logic directly since calculator can't produce this
        roc_ratio = -0.2
        is_compute_positive = roc_ratio > 0  # Gate logic from calculator
        assert not is_compute_positive


class TestInvariants:
    """Invariant checks for ROC-first sustainability logic."""

    def test_roc_ratio_equals_margin_over_spend(self) -> None:
        """Invariant: roc_ratio == compute_margin / compute_spend when spend > 0."""
        snapshot = RevenueSnapshot(
            compute_spend_usd=1234.56,
            compute_margin_usd=789.01,
        )
        expected = 789.01 / 1234.56
        assert snapshot.return_on_compute_ratio == pytest.approx(expected)

    def test_sustainable_requires_both_gates(self) -> None:
        """Invariant: is_sustainable == is_compute_positive AND is_roi_sustainable."""
        calc = UnifiedSustainabilityCalculator()

        # Scenario with both gates passing
        metrics = calc.calculate_sustainability(
            total_subscribers=25_000,
            total_angels=200,
            tasks_per_month=500_000,
        )
        assert metrics.is_sustainable == (
            metrics.is_compute_positive and metrics.is_roi_sustainable
        )

        # Scenario with ROC gate failing (no compute)
        metrics_no_compute = calc.calculate_sustainability(
            total_subscribers=25_000,
            total_angels=200,
            tasks_per_month=0,  # No compute activity
        )
        assert metrics_no_compute.is_sustainable == (
            metrics_no_compute.is_compute_positive
            and metrics_no_compute.is_roi_sustainable
        )
        # With no compute, ROC = 0, so is_compute_positive = False
        assert not metrics_no_compute.is_compute_positive
        assert not metrics_no_compute.is_sustainable

    def test_value_per_compute_dollar_equals_one_plus_roc(self) -> None:
        """Invariant: value_per_compute_dollar == 1 + ROC."""
        snapshot = RevenueSnapshot(
            compute_spend_usd=100.0,
            compute_margin_usd=60.0,  # ROC = 0.6
        )
        # V_generated = spend + margin = 100 + 60 = 160
        # value_per_dollar = V_generated / spend = 160/100 = 1.6 = 1 + ROC
        assert snapshot.value_per_compute_dollar == pytest.approx(1.6)
        assert snapshot.value_per_compute_dollar == pytest.approx(
            1 + snapshot.return_on_compute_ratio
        )


class TestPavsBaselineScenarios:
    """FAM/pAVS baseline scenarios with pinned expected values.

    Reference: FOUNDUPS_PAVS_PAPER_MANUSCRIPT.md Section 2.6
    """

    def test_year1_baseline_roc_60_percent(self) -> None:
        """Year 1 baseline: ROC = 0.60 (60%), sustainable.

        Per paper E0.3: compute_spend=$6,725, compute_margin=$4,035
        ROC = 4035 / 6725 = 0.60
        """
        calc = UnifiedSustainabilityCalculator()
        metrics = calc.calculate_sustainability(
            total_subscribers=25_000,
            total_angels=200,
            tasks_per_month=500_000,
            monthly_dex_volume_usd=50_000,
            monthly_exits_usd=10_000,
            monthly_creations_usd=5_000,
        )

        # ROC-first gate
        assert metrics.roc_ratio == pytest.approx(0.60, rel=0.01)
        assert metrics.is_compute_positive is True

        # ROI-path gate
        assert metrics.combined_ratio > 1.0
        assert metrics.is_roi_sustainable is True

        # Combined
        assert metrics.is_sustainable is True
        assert metrics.sustainability_margin_usd > 0

    def test_low_volume_scenario_still_roc_positive(self) -> None:
        """Low task volume: fewer tasks, but ROC ratio preserved (60% margin)."""
        calc = UnifiedSustainabilityCalculator()
        metrics = calc.calculate_sustainability(
            total_subscribers=5_000,
            total_angels=50,
            tasks_per_month=50_000,  # 10x fewer tasks
            monthly_dex_volume_usd=5_000,
        )

        # ROC ratio is margin/spend, independent of volume
        # (assuming same agent mix → same 60% margin)
        assert metrics.roc_ratio == pytest.approx(0.60, rel=0.01)
        assert metrics.is_compute_positive is True

        # But ROI gate may fail at low volume
        # (depends on whether subscription revenue covers burn)

    def test_high_volume_scenario_roc_unchanged(self) -> None:
        """High task volume: more tasks, ROC ratio still 60%."""
        calc = UnifiedSustainabilityCalculator()
        metrics = calc.calculate_sustainability(
            total_subscribers=100_000,
            total_angels=1_000,
            tasks_per_month=5_000_000,  # 10x more tasks
            monthly_dex_volume_usd=500_000,
        )

        # ROC ratio preserved (60% margin per agent cost structure)
        assert metrics.roc_ratio == pytest.approx(0.60, rel=0.01)
        assert metrics.is_compute_positive is True
        assert metrics.is_roi_sustainable is True
        assert metrics.is_sustainable is True

    def test_zero_compute_fails_roc_gate(self) -> None:
        """Zero compute activity fails ROC-first gate (no productivity)."""
        calc = UnifiedSustainabilityCalculator()
        metrics = calc.calculate_sustainability(
            total_subscribers=25_000,
            total_angels=200,
            tasks_per_month=0,  # No compute
            monthly_dex_volume_usd=50_000,
        )

        # ROC = 0 when no compute spend
        assert metrics.roc_ratio == 0.0
        assert metrics.is_compute_positive is False

        # ROI gate may still pass (subscription revenue)
        assert metrics.is_roi_sustainable is True

        # But combined gate fails (ROC-first requirement)
        assert metrics.is_sustainable is False
