from modules.foundups.esingularity.src.yumori_financial_export import (
    SHEET_NAMES,
    workbook_contract,
)


def test_workbook_contract_has_live_model_tabs():
    contract = workbook_contract()
    assert contract["sheets"] == SHEET_NAMES
    assert len(SHEET_NAMES) == 14
    assert SHEET_NAMES[0] == "0. Model Inputs"
    assert SHEET_NAMES[-1] == "13. Audit Checks"


def test_workbook_contract_points_to_repo_model_authority():
    contract = workbook_contract()
    assert contract["source_of_truth"].endswith("src/yumori_financial_model.py")
    assert contract["formula_contract"]["power_cost"] == (
        "it_power_kw * utilization * pue * 8760 * tariff_jpy_per_kwh"
    )
    assert contract["formula_contract"]["equity_irr"].startswith("IRR(")


def test_workbook_contract_exposes_passing_engine_validation():
    contract = workbook_contract()
    assert contract["validation"]
    assert all(contract["validation"].values())


def test_workbook_contract_carries_legacy_reconciliation_findings():
    audit = workbook_contract()["legacy_audit"]
    assert audit["displayed_equity_irr"] == 0.684
    assert 0.66 < audit["solved_equity_irr_from_shown_fcfe"] < 0.68
    assert all(abs(v - 840.0) < 0.02 for v in audit["implied_power_kw_by_year"])
