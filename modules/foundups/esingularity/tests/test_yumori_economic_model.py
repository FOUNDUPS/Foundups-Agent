from modules.foundups.esingularity.src.yumori_economic_model import (
    DEFAULT_SERVICE_CATALOG,
    DemandLine,
    DemandSizingInputs,
    calculate_demand_led_node_sizing,
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
