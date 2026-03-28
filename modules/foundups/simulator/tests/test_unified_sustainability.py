"""Tests for unified sustainability calculator."""

from __future__ import annotations

import pytest

from modules.foundups.simulator.economics.unified_sustainability import (
    UnifiedSustainabilityCalculator,
    ComputeBackingState,
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
