import pytest

from modules.foundups.esingularity.src.yumori_financial_service import (
    apply_scenario_overrides,
    calculate_scenario,
    scenario_input_contract,
)


def test_empty_scenario_preserves_canonical_outputs():
    snapshot = calculate_scenario({})
    summary = snapshot["operating_model"]["summary"]
    assert round(summary["five_year_revenue_jpy"]) == 5_374_487_296
    assert round(summary["five_year_fcfe_jpy"]) == 1_691_425_157
    assert 0.59 < summary["equity_irr"] < 0.61
    assert snapshot["scenario"]["overrides"] == {}


def test_enterprise_price_override_recalculates_revenue_through_python_engine():
    base = calculate_scenario({})
    higher = calculate_scenario({"tier_prices": {"tier_a": 500.0}})
    base_y1 = base["operating_model"]["years"][0]["gross_revenue_jpy"]
    higher_y1 = higher["operating_model"]["years"][0]["gross_revenue_jpy"]
    expected_delta = 192 * 8760 * 0.65 * (500.0 - 420.0)
    assert higher_y1 - base_y1 == pytest.approx(expected_delta)


def test_power_inputs_recalculate_power_cost_through_python_engine():
    base = calculate_scenario({})
    efficient = calculate_scenario({"pue": 1.05})
    expensive_power = calculate_scenario({"electricity_tariff_jpy_per_kwh": 30.0})
    base_cost = base["operating_model"]["years"][0]["power_cost_jpy"]
    efficient_cost = efficient["operating_model"]["years"][0]["power_cost_jpy"]
    expensive_cost = expensive_power["operating_model"]["years"][0]["power_cost_jpy"]
    assert efficient_cost < base_cost
    assert expensive_cost > base_cost


def test_tier_gpu_counts_can_resize_pool_and_auto_update_total_gpus():
    assumptions = apply_scenario_overrides(
        {
            "tier_gpu_counts": {
                "tier_a": 384,
                "tier_b": 230,
                "tier_c": 154,
            }
        }
    )
    assert assumptions.total_gpus == 768
    assert sum(tier.gpu_count for tier in assumptions.tiers) == 768
    snapshot = calculate_scenario(
        {
            "tier_gpu_counts": {
                "tier_a": 384,
                "tier_b": 230,
                "tier_c": 154,
            },
            "it_power_kw": 1700.0,
            "total_site_power_kw": 2000.0,
        }
    )
    assert snapshot["scenario"]["resolved_assumptions"]["total_gpus"] == 768


def test_unknown_scenario_field_fails_closed():
    with pytest.raises(ValueError, match="Unsupported scenario fields"):
        calculate_scenario({"magic_revenue_multiplier": 2.0})


def test_invalid_utilization_fails_in_canonical_calculator():
    with pytest.raises(ValueError, match="Utilization must be within 0-1"):
        calculate_scenario({"utilization": [1.2, 0.85, 0.92, 0.95, 0.95]})


def test_unknown_debt_key_and_field_fail_closed():
    with pytest.raises(ValueError, match="Unknown debt facility keys"):
        calculate_scenario({"debts": {"mystery_loan": {"principal_jpy": 1}}})
    with pytest.raises(ValueError, match="Unsupported debt fields"):
        calculate_scenario({"debts": {"green_loan": {"balloon_payment": 1}}})


def test_input_contract_exposes_only_bounded_dynamic_fields():
    contract = scenario_input_contract()
    assert contract["status"] == "MODEL ONLY / SCENARIO INPUTS"
    assert "pue" in contract["scalar_fields"]
    assert "utilization" in contract["schedule_fields"]
    assert "tier_prices" in contract["structured_fields"]
    assert "grants_jpy" in contract["scalar_fields"]
    assert "magic_revenue_multiplier" not in contract["scalar_fields"]
