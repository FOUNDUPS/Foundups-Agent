from dataclasses import replace
import pytest

from modules.foundups.esingularity.src.yumori_economic_model import (
    AnnualCashInputs, GrantAllocation, PortfolioInputs, SiteCost,
    SiteFinancialInputs, default_portfolio_sites, run_portfolio_model,
    DEFAULT_SERVICE_CATALOG,
    DemandLine,
    DemandSizingInputs,
    HeatRecoveryInputs,
    InfrastructureFlow,
    analyze_infrastructure_flows,
    calculate_demand_led_node_sizing,
    calculate_heat_recovery,
    load_japan_infrastructure_flows,
    run_yumori_economic_model,
)


def test_legacy_functional_model_parity() -> None:
    result = run_yumori_economic_model()
    assert result.total_project_capex_jpy == 2_085_000_000
    assert result.equity_required_jpy == 550_000_000
    assert result.years[0].gross_revenue_jpy == 808_630_528
    assert result.years[0].ebitda_jpy == 599_427_112
    assert abs(result.minimum_dscr - 1.2896175039) < 1e-9
    assert abs(result.cumulative_fcfe_jpy - 1_732_492_960) < 1
    assert abs((result.equity_irr or 0) - 0.4092639067) < 1e-9


def test_service_catalog_has_24_unique_candidate_offers() -> None:
    ids = [offer.service_id for offer in DEFAULT_SERVICE_CATALOG]
    assert len(ids) == 24
    assert len(ids) == len(set(ids))


def test_no_demand_does_not_create_a_build_target() -> None:
    result = calculate_demand_led_node_sizing()
    assert result.annual_contract_revenue_jpy == 0
    assert result.demand_backed_facility_kw == 0
    assert result.grid_fit == "UNVERIFIED"
    assert result.commercial_readiness == "NO CONTRACTED DEMAND"
    assert abs(result.financial_floor_facility_kw - 932.36603475757) < 1e-6


def test_demand_is_translated_to_revenue_and_capacity() -> None:
    result = calculate_demand_led_node_sizing(
        DemandSizingInputs(
            demand_lines=(DemandLine("anchor", "S02", 100_000, prepay_fraction=0.1, contract_term_years=3),)
        )
    )
    assert result.annual_contract_revenue_jpy == 42_000_000
    assert abs(result.demand_backed_facility_kw - 43.5399836085) < 1e-6
    assert result.upfront_cash_jpy == 4_200_000
    assert result.nominal_multiyear_contract_value_jpy == 126_000_000
    assert result.commercial_readiness == "BUILD MORE DEMAND"


def test_unpriced_active_service_fails_closed() -> None:
    result = calculate_demand_led_node_sizing(
        DemandSizingInputs(demand_lines=(DemandLine("buyer", "S06", 1_000),))
    )
    assert result.active_unpriced_service_ids == ("S06",)
    assert result.commercial_readiness == "PRICE ACTIVE DEMAND"


def test_grid_gate_only_passes_after_confirmed_capacity() -> None:
    ready = calculate_demand_led_node_sizing(
        DemandSizingInputs(
            demand_lines=(DemandLine("anchor", "S02", 2_000_000),),
            grid_confirmed_facility_kw=1_000,
        )
    )
    assert ready.grid_fit == "PASS"
    assert ready.demand_revenue_coverage > 1
    assert ready.commercial_readiness == "READY FOR ENGINEERING"

    too_large = calculate_demand_led_node_sizing(
        DemandSizingInputs(
            demand_lines=(DemandLine("anchor", "S02", 2_500_000),),
            grid_confirmed_facility_kw=1_000,
        )
    )
    assert too_large.grid_fit == "FAIL"
    assert too_large.commercial_readiness == "GRID FAIL"


def test_heat_recovery_caps_value_at_real_demand() -> None:
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
    assert abs(result.delivered_heat_kw - 397.8) < 1e-9
    assert result.usable_heat_kw == 300
    assert result.annual_usable_thermal_kwh == 2_365_200
    assert result.annual_value_jpy == 23_652_000
    assert result.avoided_kg_co2 == 473_040


def test_dependency_math_stays_partial_and_non_predictive() -> None:
    flows = (
        InfrastructureFlow("1", "A", "B", "compute", "completed", "https://example.com/1"),
        InfrastructureFlow("2", "B", "A", "equity", "signed", "https://example.com/2"),
        InfrastructureFlow("3", "B", "C", "compute", "loi", "https://example.com/3"),
        InfrastructureFlow("4", "C", "A", "partnership", "paused", "https://example.com/4"),
    )
    result = analyze_infrastructure_flows(flows)
    assert result.edge_count == 4
    assert result.reciprocal_directed_edges == 2
    assert result.reciprocal_pairs == 1
    assert result.directed_three_party_cycles == 1
    assert result.computed_weight_coverage == 0.5
    assert "Partial dependency diagnostic" in result.truth_boundary


def test_japan_infrastructure_seed_is_sourced_without_invented_amounts() -> None:
    flows = load_japan_infrastructure_flows()
    result = analyze_infrastructure_flows(flows)
    assert len(flows) >= 10
    assert all(flow.source_url.startswith("https://") for flow in flows)
    assert all(flow.evidence_class == "OFFICIAL" for flow in flows)
    assert result.known_amount_edges == 0
    assert result.undisclosed_amount_edges == len(flows)


def portfolio_fixture(revenue=100.0, investor_due=10.0):
    sites = tuple(
        SiteFinancialInputs(s.site_id, s.priority, (SiteCost("independent_scope", cost, "MODEL ONLY"),))
        for s, cost in zip(default_portfolio_sites(), (100.0, 200.0, 300.0))
    )
    cash = AnnualCashInputs(revenue, 10, 10, 5, 5, 0, 5, 10, 5, investor_due, 0)
    return PortfolioInputs(sites=sites, hanyu_cash=(cash,) * 5, hanyu_expansion_capex_jpy=50,
                           investor_equity_jpy=100)


def test_portfolio_defaults_preserve_identity_and_unknowns():
    sites = default_portfolio_sites()
    assert [(s.site_id, s.priority) for s in sites] == [("Site 3", 1), ("Site 2", 2), ("Site 1", 3)]
    assert all(s.utility_confirmed_kw is None and not s.deployable for s in sites)
    assert sites[0].costs is not sites[1].costs
    result = run_portfolio_model()
    assert result.self_funding_result == "INSUFFICIENT EVIDENCE"
    assert result.total_portfolio_capex_jpy is None
    assert result.entered_cost_subtotal_jpy == 0
    assert len(result.missing_inputs) == 106  # 50 site costs + expansion + 55 cash inputs
    assert result.reinvestable_cash_jpy is None
    assert result.to_dict()["site_capex_jpy"] == {"Site 3": None, "Site 2": None, "Site 1": None}


@pytest.mark.parametrize("status", ["VERIFIED PROGRAM", "ELIGIBILITY INQUIRY", "ELIGIBLE", "APPLICATION", "SELECTED", "AWARDED"])
def test_portfolio_only_awarded_grants_reduce_committed_need(status):
    grant = GrantAllocation("F01/site3", "Site 3", 20, status, "award evidence" if status == "AWARDED" else "")
    result = run_portfolio_model(replace(portfolio_fixture(), grants=(grant,)))
    assert result.initial_hanyu_funding_gap_jpy == (80 if status == "AWARDED" else 100)
    assert result.unawarded_grants_excluded_jpy == (0 if status == "AWARDED" else 20)


def test_sukatto_exclusion_does_not_block_hanyu_operation():
    model = portfolio_fixture()
    failed = replace(model.sites[2], included=False, gates=("FAIL",) * 7)
    result = run_portfolio_model(replace(model, sites=(*model.sites[:2], failed)))
    assert result.site_capex_jpy == {"Site 3": 100, "Site 2": 200}
    assert len(result.years) == 5
    assert result.initial_hanyu_funding_gap_jpy == 100
    assert result.total_portfolio_capex_jpy == 350


def test_hanyu_scenarios_change_self_funding_without_double_counting():
    downside = run_portfolio_model(portfolio_fixture(50))
    base = run_portfolio_model(portfolio_fixture(100))
    upside = run_portfolio_model(portfolio_fixture(200))
    assert downside.self_funding_result == "NO — ADDITIONAL CAPITAL REQUIRED"
    assert base.self_funding_result == "PARTIAL SELF-FUNDING"
    assert upside.self_funding_result == "YES UNDER CURRENT MODEL ASSUMPTIONS"
    assert base.total_portfolio_capex_jpy == 650
    assert base.reinvestable_cash_jpy == 200
    assert base.residual_financing_gap_jpy == 450
    assert upside.residual_financing_gap_jpy == 100  # Hanyu start-up still needs capital
    assert sum(base.affordable_allocations_jpy.values()) == base.reinvestable_cash_jpy
    assert sum(y.investor_distribution_jpy for y in base.years) == 50
    assert sum(y.free_cash_after_debt_jpy for y in base.years) == 275
    assert base.reinvestable_cash_jpy + 50 + 25 == 275  # distributions + reserve deposits


def test_investor_obligations_and_cash_deficits_carry_forward():
    model = portfolio_fixture(200, investor_due=1000)
    result = run_portfolio_model(model)
    assert result.self_funding_result == "NO — ADDITIONAL CAPITAL REQUIRED"
    assert result.years[-1].investor_arrears_jpy == 4250
    assert result.reinvestable_cash_jpy == 0
    mixed = replace(portfolio_fixture(200), hanyu_cash=(portfolio_fixture(0).hanyu_cash[0],) + portfolio_fixture(200).hanyu_cash[1:])
    result = run_portfolio_model(mixed)
    assert result.peak_cash_bridge_jpy == 50
    assert result.years[1].investor_distribution_jpy == 20
    assert result.self_funding_result == "NO — ADDITIONAL CAPITAL REQUIRED"
    assert not result.affordable_allocations_jpy


def test_affordability_does_not_open_deployment_gates():
    model = portfolio_fixture(200)
    closed = run_portfolio_model(model)
    assert closed.affordable_allocations_jpy == {"Hanyu expansion": 50, "Site 2": 200, "Site 1": 300}
    assert all(v == 0 for v in closed.deployable_allocations_jpy.values())
    sites = tuple(replace(s, gates=("PASS",) * 7, utility_confirmed_kw=100, demand_facility_kw=80) for s in model.sites)
    ready = run_portfolio_model(replace(model, sites=sites, expansion_gate_passed=True))
    assert ready.deployable_allocations_jpy == ready.affordable_allocations_jpy
    no_grid = replace(sites[0], utility_confirmed_kw=None)
    assert not no_grid.deployable
    uncosted = replace(sites[0], costs=(SiteCost("survey"),))
    assert not uncosted.deployable
    too_small = replace(sites[0], utility_confirmed_kw=50)
    assert not too_small.deployable
    failed_sukatto = replace(sites[2], gates=("FAIL",) * 7)
    independent = run_portfolio_model(replace(model, sites=(*sites[:2], failed_sukatto)))
    assert independent.deployment_gates["Site 3"]
    assert independent.deployable_allocations_jpy["Site 2"] == 200
    assert independent.deployable_allocations_jpy["Site 1"] == 0


def test_project_payback_is_not_investor_or_portfolio_payback():
    result = run_portfolio_model(portfolio_fixture())
    assert abs(result.site_payback_years["Site 3"] - 100 / 65) < 1e-9
    assert result.phase_payback_years[1] == result.site_payback_years["Site 3"]
    assert result.site_payback_years["Site 1"] is None
    assert result.portfolio_payback_years is None
    assert result.investor_payback_years is None  # only 50 returned against 100 equity
    model = portfolio_fixture(200)
    sites = tuple(replace(s, unlevered_cash_flows_jpy=(100.0,) * 5) for s in model.sites)
    result = run_portfolio_model(replace(model, sites=sites, hanyu_expansion_capex_jpy=0))
    assert result.portfolio_payback_years is not None


def test_restricted_funding_cannot_cross_sites_or_duplicate_allocations():
    model = portfolio_fixture()
    grant = GrantAllocation("award1", "Site 1", 999, "AWARDED", "official award")
    result = run_portfolio_model(replace(model, grants=(grant,)))
    assert result.initial_hanyu_funding_gap_jpy == 100
    assert result.gross_external_capital_gap_jpy == 350  # surplus Sukatto award not transferable
    with pytest.raises(ValueError, match="more than once"):
        run_portfolio_model(replace(model, grants=(grant, grant)))
    with pytest.raises(ValueError, match="award reference"):
        run_portfolio_model(replace(model, grants=(replace(grant, award_reference=""),)))
    excluded = replace(model.sites[2], included=False)
    assert run_portfolio_model(replace(model, sites=(*model.sites[:2], excluded), grants=(grant,))).committed_sources_jpy == 0


@pytest.mark.parametrize("bad", [-1, float("nan"), float("inf"), True])
def test_invalid_portfolio_amounts_fail_closed(bad):
    with pytest.raises(ValueError):
        run_portfolio_model(replace(portfolio_fixture(), hanyu_expansion_capex_jpy=bad))


def test_missing_cash_does_not_masquerade_as_zero_and_partial_phases_stay_held():
    model = portfolio_fixture()
    result = run_portfolio_model(replace(model, hanyu_cash=(AnnualCashInputs(),)))
    assert result.self_funding_result == "INSUFFICIENT EVIDENCE"
    assert len(result.missing_inputs) == 11
    assert result.total_portfolio_capex_jpy == 650
    sites = tuple(replace(s, gates=("PASS",) * 7, utility_confirmed_kw=100, demand_facility_kw=80) for s in model.sites)
    result = run_portfolio_model(replace(model, sites=sites, expansion_gate_passed=True))
    assert result.affordable_allocations_jpy["Site 2"] == 150
    assert result.deployable_allocations_jpy["Site 2"] == 0


def test_portfolio_schema_rejects_ambiguous_identity_costs_and_evidence():
    model = portfolio_fixture()
    with pytest.raises(ValueError, match="Duplicate site"):
        run_portfolio_model(replace(model, sites=(model.sites[0], model.sites[0])))
    with pytest.raises(ValueError, match="Hanyu"):
        run_portfolio_model(replace(model, sites=model.sites[1:]))
    for costs in [(SiteCost("x", 1),), (SiteCost("x", 1, "SOURCED"),), (SiteCost("x"), SiteCost("x"))]:
        with pytest.raises(ValueError):
            run_portfolio_model(replace(model, sites=(replace(model.sites[0], costs=costs),)))
