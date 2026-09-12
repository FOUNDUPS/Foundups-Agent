import math
import pytest

from modules.foundups.esingularity.src.yumori_feasibility_finance import (
    CustomerOfftake,
    EvidenceStatus,
    FeasibilityFundingInputs,
    calculate_feasibility_funding,
    capacity_plan,
    debt_capacity_from_cfads,
    summarize_offtake,
)


def test_capacity_plan_scales_1mw_and_5mw_without_double_counting():
    one = capacity_plan(1)
    five = capacity_plan(5)
    assert (one.gpus, one.eight_gpu_nodes) == (384, 48)
    assert (five.gpus, five.eight_gpu_nodes) == (1920, 240)


def test_committed_contract_value_revenue_and_upfront_cash_remain_distinct():
    record = CustomerOfftake(
        organization="Example University",
        customer_type="university",
        product="reserved_gpu_capacity",
        requested_gpus=32,
        annual_contract_value_jpy=100_000_000,
        nominal_multiyear_contract_value_jpy=300_000_000,
        take_or_pay_minimum_jpy=80_000_000,
        deposit_prepayment_pct=0.10,
        actual_upfront_cash_jpy=30_000_000,
        evidence_status=EvidenceStatus.COMMITTED,
        evidence_source="signed example term sheet",
    )
    summary = summarize_offtake([record])
    assert summary.annual_committed_revenue_jpy == 100_000_000
    assert summary.nominal_committed_contract_value_jpy == 300_000_000
    assert summary.committed_take_or_pay_minimum_jpy == 80_000_000
    assert summary.verified_upfront_cash_jpy == 30_000_000


def test_prepayment_percentage_does_not_create_cash_when_no_cash_received():
    record = CustomerOfftake(
        organization="Example Enterprise",
        customer_type="enterprise",
        product="dedicated_nodes",
        annual_contract_value_jpy=120_000_000,
        nominal_multiyear_contract_value_jpy=360_000_000,
        deposit_prepayment_pct=0.25,
        actual_upfront_cash_jpy=0,
        evidence_status=EvidenceStatus.COMMITTED,
    )
    summary = summarize_offtake([record])
    assert summary.annual_committed_revenue_jpy == 120_000_000
    assert summary.nominal_committed_contract_value_jpy == 360_000_000
    assert summary.verified_upfront_cash_jpy == 0


def test_potential_and_model_only_demand_do_not_enter_committed_funding():
    potential = CustomerOfftake(
        organization="Potential Buyer",
        customer_type="enterprise",
        product="burst_compute",
        annual_contract_value_jpy=50_000_000,
        nominal_multiyear_contract_value_jpy=100_000_000,
        actual_upfront_cash_jpy=10_000_000,
        evidence_status=EvidenceStatus.POTENTIAL,
    )
    model_only = CustomerOfftake(
        organization="Scenario Buyer",
        customer_type="model",
        product="academic_compute",
        annual_contract_value_jpy=20_000_000,
        nominal_multiyear_contract_value_jpy=60_000_000,
        actual_upfront_cash_jpy=5_000_000,
        evidence_status=EvidenceStatus.MODEL_ONLY,
    )
    summary = summarize_offtake([potential, model_only])
    assert summary.annual_committed_revenue_jpy == 0
    assert summary.nominal_committed_contract_value_jpy == 0
    assert summary.verified_upfront_cash_jpy == 0
    assert summary.potential_annual_revenue_jpy == 70_000_000
    assert summary.potential_nominal_contract_value_jpy == 160_000_000


def test_city_in_kind_and_potential_grants_do_not_reduce_construction_cash_gap():
    offtake = summarize_offtake([
        CustomerOfftake(
            organization="Committed Customer",
            customer_type="enterprise",
            product="reserved_gpu_capacity",
            actual_upfront_cash_jpy=100_000_000,
            evidence_status=EvidenceStatus.VERIFIED,
        )
    ])
    inputs = FeasibilityFundingInputs(
        phase1_total_project_cost_jpy=2_000_000_000,
        city_cash_committed_jpy=200_000_000,
        city_in_kind_support_jpy=300_000_000,
        prefecture_cash_committed_jpy=100_000_000,
        national_awarded_support_jpy=150_000_000,
        potential_public_support_jpy=500_000_000,
        private_quiet_phase_capital_committed_jpy=250_000_000,
        public_campaign_capital_committed_jpy=50_000_000,
        cash_flow_available_for_debt_service_jpy=300_000_000,
        dscr_requirement=1.5,
        debt_interest_rate=0.06,
        debt_term_years=10,
    )
    result = calculate_feasibility_funding(inputs, offtake)
    assert result.pre_debt_cash_funding_jpy == 850_000_000
    assert math.isclose(result.pre_debt_funding_pct, 0.425)
    assert result.city_in_kind_support_jpy == 300_000_000
    assert result.potential_public_support_jpy == 500_000_000
    assert result.remaining_funding_gap_jpy == 1_150_000_000


def test_pre_debt_target_defaults_to_eighty_percent():
    result = calculate_feasibility_funding(
        FeasibilityFundingInputs(
            phase1_total_project_cost_jpy=2_000_000_000,
            city_cash_committed_jpy=500_000_000,
            cash_flow_available_for_debt_service_jpy=0,
            dscr_requirement=1.5,
            debt_interest_rate=0.06,
            debt_term_years=10,
        ),
        summarize_offtake([]),
    )
    assert result.pre_debt_target_jpy == 1_600_000_000
    assert result.pre_debt_target_shortfall_jpy == 1_100_000_000


def test_debt_deployed_is_lesser_of_gap_and_supportable_capacity():
    max_service, supportable = debt_capacity_from_cfads(
        cash_flow_available_for_debt_service_jpy=300_000_000,
        dscr_requirement=1.5,
        annual_interest_rate=0.06,
        term_years=10,
    )
    assert max_service == 200_000_000
    assert supportable > 1_000_000_000

    # Gap smaller than capacity: debt is capped at gap.
    gap_capped = calculate_feasibility_funding(
        FeasibilityFundingInputs(
            phase1_total_project_cost_jpy=1_000_000_000,
            city_cash_committed_jpy=800_000_000,
            cash_flow_available_for_debt_service_jpy=300_000_000,
            dscr_requirement=1.5,
            debt_interest_rate=0.06,
            debt_term_years=10,
        ),
        summarize_offtake([]),
    )
    assert gap_capped.actual_debt_deployed_jpy == 200_000_000
    assert gap_capped.remaining_unfunded_gap_after_debt_jpy == 0

    # Capacity smaller than gap: residual gap remains.
    capacity_capped = calculate_feasibility_funding(
        FeasibilityFundingInputs(
            phase1_total_project_cost_jpy=2_000_000_000,
            city_cash_committed_jpy=100_000_000,
            cash_flow_available_for_debt_service_jpy=60_000_000,
            dscr_requirement=1.5,
            debt_interest_rate=0.06,
            debt_term_years=10,
        ),
        summarize_offtake([]),
    )
    assert capacity_capped.actual_debt_deployed_jpy < capacity_capped.remaining_funding_gap_jpy
    assert capacity_capped.remaining_unfunded_gap_after_debt_jpy > 0


def test_invalid_inputs_fail_closed():
    with pytest.raises(ValueError):
        CustomerOfftake(
            organization="Bad",
            customer_type="enterprise",
            product="reserved",
            deposit_prepayment_pct=1.5,
        )
    with pytest.raises(ValueError):
        FeasibilityFundingInputs(
            phase1_total_project_cost_jpy=-1,
        )
    with pytest.raises(ValueError):
        capacity_plan(0)
