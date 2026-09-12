from modules.foundups.esingularity.src.yumori_financial_model import (
    LEGACY_DISPLAYED_EQUITY_IRR,
    audit_legacy_model,
    calculate_model,
    default_assumptions,
)


def test_base_model_reconciles():
    result = calculate_model()
    assert all(result.validation.values())
    assert round(result.five_year_revenue_jpy) == 5_374_487_296
    assert round(result.five_year_fcfe_jpy) == 1_691_425_157
    assert result.equity_irr is not None
    assert 0.59 < result.equity_irr < 0.61


def test_revenue_is_bottom_up_from_gpu_counts_prices_and_utilization():
    a = default_assumptions()
    result = calculate_model(a)
    y1 = result.years[0]
    expected = sum(
        tier.gpu_count * 8760 * a.utilization[0] * tier.price_jpy_per_gpu_hour
        for tier in a.tiers
    )
    assert abs(y1.compute_revenue_jpy - expected) < 0.5
    assert abs(y1.gross_revenue_jpy - (expected + a.thermal_revenue_jpy[0])) < 0.5


def test_power_cost_uses_stated_it_load_pue_utilization_and_tariff():
    a = default_assumptions()
    result = calculate_model(a)
    y1 = result.years[0]
    expected = (
        a.it_power_kw
        * a.utilization[0]
        * a.pue
        * 8760
        * a.electricity_tariff_jpy_per_kwh
    )
    assert abs(y1.power_cost_jpy - expected) < 0.5


def test_compute_depreciation_stops_after_four_years():
    result = calculate_model()
    assert [y.compute_depreciation_jpy for y in result.years[:4]] == [450_000_000.0] * 4
    assert result.years[4].compute_depreciation_jpy == 0.0


def test_visitor_spend_is_not_project_revenue():
    a = default_assumptions()
    result = calculate_model(a)
    assert result.visitor_spend_30y_low_jpy == a.visitor_spend_low_jpy * 30
    assert result.visitor_spend_30y_high_jpy == a.visitor_spend_high_jpy * 30
    for year in result.years:
        assert year.gross_revenue_jpy == year.compute_revenue_jpy + year.thermal_revenue_jpy


def test_legacy_irr_display_does_not_reconcile():
    audit = audit_legacy_model()
    solved = audit["solved_equity_irr_from_shown_fcfe"]
    assert solved is not None
    assert abs(solved - LEGACY_DISPLAYED_EQUITY_IRR) > 0.01
    assert 1.4 < audit["irr_gap_percentage_points"] < 1.6


def test_legacy_power_cost_implies_840_kw_not_850_kw():
    audit = audit_legacy_model()
    assert all(abs(value - 840.0) < 0.02 for value in audit["implied_power_kw_by_year"])
    assert audit["stated_it_power_kw"] == 850.0
