from dataclasses import replace
from math import isclose

from modules.foundups.esingularity.src.yumori_economic_model import (
    HeatRecoveryInputs,
    InfrastructureFlow,
    YumoriEconomicInputs,
    analyze_infrastructure_flows,
    calculate_heat_recovery,
    load_japan_infrastructure_flows,
    run_yumori_economic_model,
)


def test_default_scenario_reproduces_fin_yumori_workbook():
    result = run_yumori_economic_model()

    assert result.total_infrastructure_capex_jpy == 285_000_000
    assert result.total_project_capex_jpy == 2_085_000_000
    assert result.equity_required_jpy == 550_000_000
    assert isclose(result.years[0].gross_revenue_jpy, 808_630_528, abs_tol=0.01)
    assert isclose(result.years[0].ebitda_jpy, 599_427_112, abs_tol=0.01)
    assert isclose(result.years[0].dscr, 1.289617504, rel_tol=1e-9)
    assert isclose(result.cumulative_fcfe_jpy, 1_732_492_960, abs_tol=1.0)
    assert isclose(result.equity_irr or 0.0, 0.4092639067, rel_tol=1e-8)
    assert result.years[4].compute_depreciation_jpy == 0
    assert all(result.checks.values())


def test_unawarded_grant_scenario_never_reduces_base_equity():
    scenario_only = run_yumori_economic_model(
        replace(YumoriEconomicInputs(), potential_grants_scenario_jpy=160_000_000)
    )
    awarded = run_yumori_economic_model(
        replace(YumoriEconomicInputs(), committed_awarded_grants_jpy=160_000_000)
    )

    assert scenario_only.equity_required_jpy == 550_000_000
    assert scenario_only.potential_grants_excluded_jpy == 160_000_000
    assert awarded.equity_required_jpy == 390_000_000


def test_revenue_shares_fail_closed_when_they_do_not_sum_to_one():
    bad_tiers = tuple(replace(tier, share=tier.share / 2) for tier in YumoriEconomicInputs().revenue_tiers)

    try:
        run_yumori_economic_model(replace(YumoriEconomicInputs(), revenue_tiers=bad_tiers))
    except ValueError as error:
        assert "sum to 1.0" in str(error)
    else:
        raise AssertionError("invalid revenue shares should fail closed")


def test_heat_recovery_caps_value_at_real_thermal_demand():
    result = calculate_heat_recovery(
        HeatRecoveryInputs(
            it_load_kw=850,
            load_fraction=0.65,
            recovery_fraction=0.80,
            delivery_efficiency=0.90,
            thermal_demand_kw=300,
            annual_availability=0.90,
            value_jpy_per_thermal_kwh=10,
            grid_heat_kg_co2_per_kwh=0.2,
        )
    )

    assert isclose(result.delivered_heat_kw, 397.8)
    assert result.usable_heat_kw == 300
    assert result.annual_usable_thermal_kwh == 2_365_200
    assert result.annual_value_jpy == 23_652_000
    assert result.avoided_kg_co2 == 473_040


def test_dependency_math_keeps_partial_score_truth_boundary():
    flows = (
        InfrastructureFlow("1", "A", "B", "compute", "completed", "https://example.com/1"),
        InfrastructureFlow("2", "B", "A", "equity", "signed", "https://example.com/2"),
        InfrastructureFlow("3", "B", "C", "compute", "loi", "https://example.com/3"),
        InfrastructureFlow("4", "C", "A", "partnership", "paused", "https://example.com/4"),
    )

    result = analyze_infrastructure_flows(flows)

    assert result.edge_count == 4
    assert result.reciprocal_directed_edges == 2
    assert result.reciprocal_share == 0.5
    assert result.reciprocal_pairs == 1
    assert result.directed_three_party_cycles == 1
    assert result.paper_share == 0.625
    assert result.circularity_score == 80.0
    assert result.computed_weight_coverage == 0.5
    assert "not" in result.truth_boundary.lower() or "only" in result.truth_boundary.lower()


def test_official_japan_seed_is_sourced_and_does_not_invent_amounts():
    flows = load_japan_infrastructure_flows()
    result = analyze_infrastructure_flows(flows)

    assert len(flows) >= 10
    assert all(flow.source_url.startswith("https://") for flow in flows)
    assert all(flow.evidence_class == "OFFICIAL" for flow in flows)
    assert result.known_amount_edges == 0
    assert result.undisclosed_amount_edges == len(flows)
