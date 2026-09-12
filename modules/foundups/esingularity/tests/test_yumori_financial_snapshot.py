from dataclasses import replace

import pytest

from modules.foundups.esingularity.src.yumori_feasibility_finance import (
    CustomerOfftake,
    EvidenceStatus,
    FeasibilityFundingInputs,
)
from modules.foundups.esingularity.src.yumori_financial_model import default_assumptions
from modules.foundups.esingularity.src.yumori_financial_snapshot import (
    SNAPSHOT_SCHEMA_VERSION,
    build_finance_snapshot,
)


def test_snapshot_combines_model_history_catalog_and_capacity_without_inventing_funding():
    snapshot = build_finance_snapshot()
    assert snapshot["schema_version"] == SNAPSHOT_SCHEMA_VERSION
    assert snapshot["foundup_id"] == "esingularity_001"
    assert len(snapshot["capacity_planning"]) == 5
    assert snapshot["capacity_planning"][0]["gpus"] == 384
    assert snapshot["capacity_planning"][-1]["gpus"] == 1920
    assert len(snapshot["capacity_economics"]) == 5
    assert snapshot["capacity_economics"][0]["mw"] == 1
    assert snapshot["capacity_economics"][-1]["mw"] == 5
    assert snapshot["facility_history"]["operating_history"][-1]["users"] == 129_649
    assert snapshot["facility_history"]["operating_history"][-1]["user_fee_revenue_jpy"] == 124_886_000
    assert snapshot["facility_history"]["city_fiscal_history"][-1]["city_net_cost_jpy"] == 19_615_602
    assert snapshot["facility_history"]["current_carrying_cost"]["known_annual_cost_jpy"] == 7_892_646
    assert snapshot["capacity_allocation"]["total_gpu_capacity"] == 384
    assert snapshot["capacity_allocation"]["committed_reserved_gpus"] == 0
    assert snapshot["capacity_allocation"]["committed_headroom_gpus"] == 384
    assert snapshot["catalog"]["counts"]["products"] == 14
    assert snapshot["catalog"]["counts"]["market_benchmarks"] == 16
    assert snapshot["price_reconciliation"]["targets"]
    assert snapshot["feasibility"]["status"] == "NOT_RUN"
    assert "does not infer commitments" in snapshot["feasibility"]["reason"]


def test_snapshot_preserves_canonical_operating_model_outputs():
    snapshot = build_finance_snapshot()
    summary = snapshot["operating_model"]["summary"]
    assert round(summary["five_year_revenue_jpy"]) == 5_374_487_296
    assert round(summary["five_year_fcfe_jpy"]) == 1_691_425_157
    assert 0.59 < summary["equity_irr"] < 0.61
    assert all(snapshot["operating_model"]["validation"].values())


def test_capacity_economics_follow_active_scenario_assumptions():
    base = default_assumptions()
    base_snapshot = build_finance_snapshot(base)
    richer_tiers = tuple(
        replace(tier, price_jpy_per_gpu_hour=tier.price_jpy_per_gpu_hour * 1.10)
        for tier in base.tiers
    )
    changed = replace(base, tiers=richer_tiers)
    changed_snapshot = build_finance_snapshot(changed)
    assert changed_snapshot["capacity_economics"][0]["year1_revenue_jpy"] > base_snapshot["capacity_economics"][0]["year1_revenue_jpy"]


def test_explicit_feasibility_inputs_keep_contract_value_cash_and_capacity_separate():
    customer = CustomerOfftake(
        organization="Example University",
        customer_type="university",
        product="gpu_academic",
        requested_gpus=32,
        reserved_capacity_gpus=32,
        annual_contract_value_jpy=100_000_000,
        nominal_multiyear_contract_value_jpy=400_000_000,
        take_or_pay_minimum_jpy=80_000_000,
        actual_upfront_cash_jpy=20_000_000,
        evidence_status=EvidenceStatus.COMMITTED,
    )
    funding_inputs = FeasibilityFundingInputs(
        phase1_total_project_cost_jpy=2_085_000_000,
        city_cash_committed_jpy=0,
        prefecture_cash_committed_jpy=0,
        national_awarded_support_jpy=0,
        private_quiet_phase_capital_committed_jpy=400_000_000,
        public_campaign_capital_committed_jpy=0,
        cash_flow_available_for_debt_service_jpy=250_000_000,
        dscr_requirement=1.5,
        debt_interest_rate=0.06,
        debt_term_years=10,
    )
    snapshot = build_finance_snapshot(
        customer_offtake=[customer],
        funding_inputs=funding_inputs,
    )
    feasibility = snapshot["feasibility"]
    capacity = snapshot["capacity_allocation"]
    assert capacity["committed_reserved_gpus"] == 32
    assert capacity["committed_headroom_gpus"] == 352
    assert feasibility["status"] == "CALCULATED FROM EXPLICIT INPUTS"
    assert feasibility["offtake"]["annual_committed_revenue_jpy"] == 100_000_000
    assert feasibility["offtake"]["nominal_committed_contract_value_jpy"] == 400_000_000
    assert feasibility["offtake"]["verified_upfront_cash_jpy"] == 20_000_000
    assert feasibility["funding_result"]["pre_debt_cash_funding_jpy"] == 420_000_000
    assert feasibility["funding_result"]["actual_debt_deployed_jpy"] <= feasibility["funding_result"]["remaining_funding_gap_jpy"]


def test_feasibility_snapshot_fails_closed_when_committed_reservations_exceed_gpu_pool():
    records = [
        CustomerOfftake(
            organization="Enterprise A",
            customer_type="enterprise",
            product="gpu_reserved",
            reserved_capacity_gpus=256,
            evidence_status=EvidenceStatus.COMMITTED,
        ),
        CustomerOfftake(
            organization="University A",
            customer_type="university",
            product="gpu_academic",
            reserved_capacity_gpus=160,
            evidence_status=EvidenceStatus.VERIFIED,
        ),
    ]
    funding_inputs = FeasibilityFundingInputs(
        phase1_total_project_cost_jpy=2_085_000_000,
        cash_flow_available_for_debt_service_jpy=250_000_000,
        dscr_requirement=1.5,
        debt_interest_rate=0.06,
        debt_term_years=10,
    )
    with pytest.raises(ValueError, match="exceed physical capacity by 32 GPUs"):
        build_finance_snapshot(
            customer_offtake=records,
            funding_inputs=funding_inputs,
        )
