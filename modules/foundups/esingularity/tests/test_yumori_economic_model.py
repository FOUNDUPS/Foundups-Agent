from modules.foundups.esingularity.src.yumori_economic_model import (
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
