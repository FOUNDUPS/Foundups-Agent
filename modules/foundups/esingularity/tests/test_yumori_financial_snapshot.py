from modules.foundups.esingularity.src.yumori_feasibility_finance import (
    CustomerOfftake,
    EvidenceStatus,
    FeasibilityFundingInputs,
)
from modules.foundups.esingularity.src.yumori_financial_snapshot import (
    SNAPSHOT_SCHEMA_VERSION,
    build_finance_snapshot,
)


def test_snapshot_combines_model_catalog_and_capacity_without_inventing_funding():
    snapshot = build_finance_snapshot()
    assert snapshot["schema_version"] == SNAPSHOT_SCHEMA_VERSION
    assert snapshot["foundup_id"] == "esingularity_001"
    assert len(snapshot["capacity_planning"]) == 5
    assert snapshot["capacity_planning"][0]["gpus"] == 384
    assert snapshot["capacity_planning"][-1]["gpus"] == 1920
    assert snapshot["catalog"]["counts"]["products"] == 14
    assert snapshot["feasibility"]["status"] == "NOT_RUN"
    assert "does not infer commitments" in snapshot["feasibility"]["reason"]


def test_snapshot_preserves_canonical_operating_model_outputs():
    snapshot = build_finance_snapshot()
    summary = snapshot["operating_model"]["summary"]
    assert round(summary["five_year_revenue_jpy"]) == 5_374_487_296
    assert round(summary["five_year_fcfe_jpy"]) == 1_691_425_157
    assert 0.59 < summary["equity_irr"] < 0.61
    assert all(snapshot["operating_model"]["validation"].values())


def test_explicit_feasibility_inputs_keep_contract_value_and_cash_separate():
    customer = CustomerOfftake(
        organization="Example University",
        customer_type="university",
        product="reserved_gpu_capacity",
        requested_gpus=32,
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
    assert feasibility["status"] == "CALCULATED FROM EXPLICIT INPUTS"
    assert feasibility["offtake"]["annual_committed_revenue_jpy"] == 100_000_000
    assert feasibility["offtake"]["nominal_committed_contract_value_jpy"] == 400_000_000
    assert feasibility["offtake"]["verified_upfront_cash_jpy"] == 20_000_000
    assert feasibility["funding_result"]["pre_debt_cash_funding_jpy"] == 420_000_000
    assert feasibility["funding_result"]["actual_debt_deployed_jpy"] <= feasibility["funding_result"]["remaining_funding_gap_jpy"]
