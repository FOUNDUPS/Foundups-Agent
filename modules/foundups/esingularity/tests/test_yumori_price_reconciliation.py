import pytest

from modules.foundups.esingularity.src.yumori_price_reconciliation import (
    build_price_reconciliation,
)


def test_enterprise_target_compares_directly_to_sakura_without_fx():
    result = build_price_reconciliation()
    enterprise = next(
        row for row in result["targets"] if row["target"]["product_id"] == "gpu_reserved"
    )
    sakura = next(
        comparison
        for comparison in enterprise["comparisons"]
        if comparison["benchmark"]["id"] == "sakura_dok_h100_8gpu_2026-09-12"
    )
    assert sakura["comparison_status"] == "DIRECT_PRICE_RATIO_ONLY"
    assert sakura["benchmark_gpu_hour_basis"] == 373.5
    assert sakura["absolute_delta"] == pytest.approx(46.5)
    assert sakura["delta_pct"] == pytest.approx(420 / 373.5 - 1)


def test_cross_currency_gpu_benchmarks_require_dated_fx_instead_of_hidden_conversion():
    result = build_price_reconciliation()
    enterprise = next(
        row for row in result["targets"] if row["target"]["product_id"] == "gpu_reserved"
    )
    aws = next(
        comparison
        for comparison in enterprise["comparisons"]
        if comparison["benchmark"]["id"] == "aws_capacity_blocks_h100_tokyo_2026-09-12"
    )
    assert aws["comparison_status"] == "FX_REQUIRED"
    assert aws["target_currency"] == "JPY"
    assert aws["benchmark"]["currency"] == "USD"
    assert "delta_pct" not in aws


def test_burst_target_is_lower_than_sakura_single_gpu_public_price_but_scope_warning_remains():
    result = build_price_reconciliation()
    burst = next(
        row for row in result["targets"] if row["target"]["product_id"] == "gpu_burst"
    )
    sakura = next(
        comparison
        for comparison in burst["comparisons"]
        if comparison["benchmark"]["id"] == "sakura_dok_h100_1gpu_2026-09-12"
    )
    assert sakura["comparison_status"] == "DIRECT_PRICE_RATIO_ONLY"
    assert sakura["delta_pct"] < 0
    assert "Hardware configuration" in sakura["scope_warning"]


def test_academic_target_has_no_fake_market_comparison_when_no_matching_product_exists():
    result = build_price_reconciliation()
    academic = next(
        row for row in result["targets"] if row["target"]["product_id"] == "gpu_academic"
    )
    assert academic["comparisons"] == []
    assert academic["direct_comparison_count"] == 0
    assert academic["fx_required_count"] == 0
