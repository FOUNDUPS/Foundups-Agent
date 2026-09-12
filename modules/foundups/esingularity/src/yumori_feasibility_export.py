"""Reusable XLSX projection helpers for YUMORI feasibility funding/offtake.

This module writes *adjacent* feasibility sheets into an xlsxwriter Workbook.
It does not own the financial equations and does not mutate the canonical
Phase-1 operating/P&L model.  Calculation authority remains Python:
``yumori_feasibility_finance.py`` for these evidence/capital gates and
``yumori_financial_model.py`` for the operating model.

WSP: 3, 50, 84, 95, 97, 109.
"""
from __future__ import annotations

from dataclasses import asdict
from typing import Dict, Iterable, Sequence, Tuple

from .yumori_feasibility_finance import (
    CustomerOfftake,
    FeasibilityFundingInputs,
    FeasibilityFundingResult,
    OfftakeSummary,
    calculate_feasibility_funding,
    capacity_plan,
    summarize_offtake,
)

NCDS_SHEET = "14. NCDS Feasibility Funding"
OFFTAKE_SHEET = "15. 1–5 MW Pricing & Offtake"
FEASIBILITY_SHEET_NAMES = (NCDS_SHEET, OFFTAKE_SHEET)


def feasibility_workbook_contract(
    records: Iterable[CustomerOfftake],
    funding_inputs: FeasibilityFundingInputs,
) -> Dict[str, object]:
    records = tuple(records)
    offtake = summarize_offtake(records)
    funding = calculate_feasibility_funding(funding_inputs, offtake)
    return {
        "sheets": FEASIBILITY_SHEET_NAMES,
        "source_of_truth": "modules/foundups/esingularity/src/yumori_feasibility_finance.py",
        "customer_record_count": offtake.record_count,
        "offtake_summary": asdict(offtake),
        "funding_result": asdict(funding),
        "capacity_plans": [asdict(capacity_plan(mw)) for mw in range(1, 6)],
        "accounting_rules": {
            "annual_contract_value": "operating revenue / underwriting evidence",
            "nominal_multiyear_contract_value": "not construction cash",
            "take_or_pay_minimum": "bankability evidence; not automatically cash",
            "actual_upfront_cash": "construction cash only for VERIFIED/COMMITTED records",
            "city_in_kind_support": "reported separately; excluded from pre-debt cash",
            "potential_public_support": "scenario only; excluded until committed/awarded",
            "deployed_debt": "MIN(remaining funding gap, DSCR-supported amortizing debt capacity)",
        },
    }


def _formats(workbook):
    navy = "#0B1F3A"
    blue = "#D9EAF7"
    yellow = "#FFF2CC"
    green = "#E2F0D9"
    return {
        "title": workbook.add_format({"bold": True, "font_size": 16, "font_color": "#FFFFFF", "bg_color": navy}),
        "header": workbook.add_format({"bold": True, "font_color": "#FFFFFF", "bg_color": navy, "border": 1, "text_wrap": True}),
        "section": workbook.add_format({"bold": True, "font_color": "#FFFFFF", "bg_color": navy}),
        "jpy": workbook.add_format({"num_format": "¥#,##0;[Red](¥#,##0);-"}),
        "pct": workbook.add_format({"num_format": "0.0%;[Red](0.0%);-"}),
        "multiple": workbook.add_format({"num_format": "0.00x;[Red](0.00x);-"}),
        "num": workbook.add_format({"num_format": "#,##0;[Red](#,##0);-"}),
        "model": workbook.add_format({"bg_color": yellow, "num_format": "¥#,##0;[Red](¥#,##0);-"}),
        "committed": workbook.add_format({"bg_color": green, "num_format": "¥#,##0;[Red](¥#,##0);-"}),
        "potential": workbook.add_format({"bg_color": yellow, "num_format": "¥#,##0;[Red](¥#,##0);-"}),
        "note": workbook.add_format({"font_color": "#666666", "italic": True, "text_wrap": True, "valign": "top"}),
        "text": workbook.add_format({"text_wrap": True, "valign": "top"}),
        "subtle": workbook.add_format({"bg_color": blue, "text_wrap": True}),
    }


def write_feasibility_sheets(
    workbook,
    records: Sequence[CustomerOfftake],
    funding_inputs: FeasibilityFundingInputs,
) -> Tuple[OfftakeSummary, FeasibilityFundingResult]:
    """Append both feasibility sheets to an open xlsxwriter Workbook."""
    records = tuple(records)
    summary = summarize_offtake(records)
    funding = calculate_feasibility_funding(funding_inputs, summary)
    f = _formats(workbook)
    _write_ndcs_sheet(workbook, funding_inputs, summary, funding, f)
    _write_offtake_sheet(workbook, records, summary, f)
    return summary, funding


def _write_ndcs_sheet(workbook, inputs, summary, result, f) -> None:
    ws = workbook.add_worksheet(NCDS_SHEET)
    ws.hide_gridlines(2)
    ws.freeze_panes(4, 1)
    ws.set_column("A:A", 43)
    ws.set_column("B:B", 18)
    ws.set_column("C:C", 20)
    ws.set_column("D:D", 54)
    ws.merge_range("A1:D1", "NCDS FEASIBILITY FUNDING / 資金調達フィージビリティ", f["title"])
    ws.merge_range(
        "A2:D2",
        "Evidence/capital gate only. Ordinary customer revenue and nominal contract value are NOT construction cash. Python remains authority.",
        f["note"],
    )
    ws.write_row("A4", ["Funding / underwriting metric", "JPY / Value", "Classification", "Accounting treatment"], f["header"])

    lines = [
        ("Phase-1 total project cost", inputs.phase1_total_project_cost_jpy, "MODEL INPUT", "Total funding requirement; validate vendor/engineering CapEx."),
        ("City committed cash support", inputs.city_cash_committed_jpy, "COMMITTED CASH", "Counts in pre-debt cash only when actually committed."),
        ("City in-kind support", inputs.city_in_kind_support_jpy, "IN-KIND / SEPARATE", "Does not reduce cash funding gap unless monetized and documented."),
        ("Prefecture committed cash", inputs.prefecture_cash_committed_jpy, "COMMITTED CASH", "Counts only when committed."),
        ("National awarded support", inputs.national_awarded_support_jpy, "AWARDED CASH", "Candidate grants remain outside this line."),
        ("Customer actual upfront cash", summary.verified_upfront_cash_jpy, "VERIFIED/COMMITTED CASH", "Deposits/prepayments/advance capacity cash only."),
        ("Private quiet-phase capital commitments", inputs.private_quiet_phase_capital_committed_jpy, "COMMITTED CASH", "Anchor/private capital actually committed."),
        ("Public campaign capital commitments", inputs.public_campaign_capital_committed_jpy, "COMMITTED CASH", "Committed public campaign capital only."),
        ("Potential/candidate public support", inputs.potential_public_support_jpy, "POTENTIAL / SEPARATE", "Excluded from pre-debt cash until awarded/committed."),
        ("PRE-DEBT CASH FUNDING", result.pre_debt_cash_funding_jpy, "CALCULATED", "Committed cash sources only."),
        ("Pre-debt funding %", result.pre_debt_funding_pct, "CALCULATED", "Pre-debt cash ÷ project cost."),
        ("Pre-debt target", result.pre_debt_target_jpy, "MODEL TARGET", f"Project cost × {inputs.pre_debt_target_pct:.0%}."),
        ("Pre-debt target shortfall", result.pre_debt_target_shortfall_jpy, "CALCULATED", "Shortfall to adjustable pre-debt target."),
        ("Remaining funding gap before debt", result.remaining_funding_gap_jpy, "CALCULATED", "Project cost − pre-debt cash."),
        ("Year-1 EBITDA evidence", result.year1_ebitda_jpy, "MODEL / EVIDENCE", "Displayed separately; not automatically CFADS."),
        ("CFADS used for debt sizing", result.cash_flow_available_for_debt_service_jpy, "UNDERWRITING INPUT", "Cash flow available for debt service; must be defined/validated."),
        ("Required DSCR", inputs.dscr_requirement, "UNDERWRITING INPUT", "Lender covenant assumption; not a commitment."),
        ("Debt interest rate", inputs.debt_interest_rate, "UNDERWRITING INPUT", "Financing assumption."),
        ("Debt term (years)", inputs.debt_term_years, "UNDERWRITING INPUT", "Financing assumption."),
        ("Maximum annual debt service", result.max_annual_debt_service_jpy, "CALCULATED", "CFADS ÷ required DSCR."),
        ("DSCR-supported debt capacity", result.dscr_supported_debt_capacity_jpy, "CALCULATED", "Amortizing principal supported by max debt service/rate/term."),
        ("ACTUAL DEBT DEPLOYED", result.actual_debt_deployed_jpy, "CALCULATED", "MIN(remaining funding gap, supportable debt capacity)."),
        ("REMAINING UNFUNDED GAP AFTER DEBT", result.remaining_unfunded_gap_after_debt_jpy, "GO/NO-GO GATE", "If positive: add capital/prepayments, reduce/resize CapEx, restructure, or stop."),
    ]
    for row, (label, value, status, treatment) in enumerate(lines, start=5):
        ws.write(row - 1, 0, label)
        if "%" in label or "DSCR" in label and label == "Required DSCR":
            fmt = f["pct"] if "%" in label else f["multiple"]
        elif label == "Debt interest rate":
            fmt = f["pct"]
        elif label == "Debt term (years)":
            fmt = f["num"]
        else:
            fmt = f["jpy"]
        ws.write(row - 1, 1, value, fmt)
        ws.write(row - 1, 2, status, f["text"])
        ws.write(row - 1, 3, treatment, f["text"])

    ws.write(29, 0, "Customer annual committed revenue", f["subtle"])
    ws.write(29, 1, summary.annual_committed_revenue_jpy, f["jpy"])
    ws.write(29, 2, "OPERATING REVENUE / UNDERWRITING", f["subtle"])
    ws.write(29, 3, "Shown for bankability evidence. It is not added to construction cash.", f["subtle"])
    ws.write(30, 0, "Customer nominal committed multi-year value", f["subtle"])
    ws.write(30, 1, summary.nominal_committed_contract_value_jpy, f["jpy"])
    ws.write(30, 2, "NOMINAL CONTRACT VALUE", f["subtle"])
    ws.write(30, 3, "Not construction cash; do not add to funding stack.", f["subtle"])


def _write_offtake_sheet(workbook, records, summary, f) -> None:
    ws = workbook.add_worksheet(OFFTAKE_SHEET)
    ws.hide_gridlines(2)
    ws.freeze_panes(10, 3)
    ws.set_column("A:A", 5)
    ws.set_column("B:C", 24)
    ws.set_column("D:D", 28)
    ws.set_column("E:J", 16)
    ws.set_column("K:Q", 18)
    ws.set_column("R:S", 28)
    ws.merge_range("A1:S1", "1–5 MW PRICING & OFFTAKE / 需要・価格・オフテイク", f["title"])
    ws.merge_range(
        "A2:S2",
        "The same physical GPU pool may support multiple products. Do not double-count capacity. Contract value, revenue, and actual upfront cash remain separate.",
        f["note"],
    )

    ws.write_row("A4", ["MW", "GPUs", "8-GPU nodes", "Status"], f["header"])
    for row, mw in enumerate(range(1, 6), start=5):
        plan = capacity_plan(mw)
        ws.write(row - 1, 0, plan.mw)
        ws.write(row - 1, 1, plan.gpus, f["num"])
        ws.write(row - 1, 2, plan.eight_gpu_nodes, f["num"])
        ws.write(row - 1, 3, "PLANNING RELATIONSHIP / NOT GRID OR PROCUREMENT COMMITMENT", f["text"])

    headers = [
        "#", "Organization", "Customer type", "Product", "Requested GPUs", "Requested nodes",
        "Hours/month", "Reserved GPUs", "Start date", "Term months", "Current provider",
        "Current price / GPU-h", "YUMORI price / GPU-h", "Annual contract value",
        "Nominal multi-year value", "Take-or-pay minimum", "Deposit/prepay %",
        "Actual upfront cash", "Evidence / procurement / source",
    ]
    ws.write_row("A10", headers, f["header"])
    for idx, record in enumerate(records, start=1):
        row = 10 + idx
        evidence = " | ".join(
            part for part in (
                record.evidence_status.value,
                record.procurement_constraints,
                record.evidence_source,
            ) if part
        )
        values = [
            idx, record.organization, record.customer_type, record.product,
            record.requested_gpus, record.requested_nodes, record.hours_per_month,
            record.reserved_capacity_gpus, record.start_date, record.contract_term_months,
            record.market_current_provider, record.current_price_jpy_per_gpu_hour,
            record.proposed_price_jpy_per_gpu_hour, record.annual_contract_value_jpy,
            record.nominal_multiyear_contract_value_jpy, record.take_or_pay_minimum_jpy,
            record.deposit_prepayment_pct, record.actual_upfront_cash_jpy, evidence,
        ]
        for col, value in enumerate(values):
            if col in (11, 12, 13, 14, 15, 17):
                fmt = f["jpy"]
            elif col == 16:
                fmt = f["pct"]
            elif col in (4, 5, 6, 7, 9):
                fmt = f["num"]
            else:
                fmt = f["text"]
            ws.write(row - 1, col, value, fmt)

    summary_row = 12 + len(records)
    ws.merge_range(summary_row - 1, 0, summary_row - 1, 3, "OFFTAKE SUMMARY — DO NOT COMBINE THESE COLUMNS", f["section"])
    summary_lines = [
        ("Annual committed operating revenue", summary.annual_committed_revenue_jpy, "Operating revenue / underwriting evidence"),
        ("Nominal committed multi-year value", summary.nominal_committed_contract_value_jpy, "Nominal contract value; not cash"),
        ("Committed take-or-pay minimum", summary.committed_take_or_pay_minimum_jpy, "Bankability evidence; not automatically cash"),
        ("Verified/committed actual upfront cash", summary.verified_upfront_cash_jpy, "May enter pre-debt construction funding"),
        ("Potential annual revenue", summary.potential_annual_revenue_jpy, "Pipeline only; not committed"),
        ("Potential nominal contract value", summary.potential_nominal_contract_value_jpy, "Pipeline only; not committed cash"),
    ]
    for offset, (label, value, treatment) in enumerate(summary_lines, start=1):
        rr = summary_row + offset
        ws.write(rr - 1, 0, label)
        ws.write(rr - 1, 1, value, f["jpy"])
        ws.merge_range(rr - 1, 2, rr - 1, 5, treatment, f["text"])
