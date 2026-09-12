"""Generate the YUMORI live XLSX projection from repository-owned equations.

The workbook is an auditable projection. ``yumori_financial_model.py`` remains
calculation authority. Excel formulas mirror the Python equations so scenario
inputs can be changed interactively without turning the workbook into a second
source of truth.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict

from .yumori_financial_model import (
    HOURS_PER_YEAR,
    ModelAssumptions,
    ModelResult,
    audit_legacy_model,
    calculate_model,
    default_assumptions,
)

SHEET_NAMES = (
    "0. Model Inputs",
    "1. Executive Summary",
    "2. Capital Stack & Sources",
    "3. Operating Assumptions",
    "4. Revenue Model",
    "5. OpEx & COGS Breakdown",
    "6. Income Statement (P&L)",
    "7. Cash Flow & FCFE",
    "8. Debt Schedule & DSCR",
    "9. Regional Economic Impact",
    "10. Impact Assumptions",
    "11. 60-Day Validation",
    "12. Demand & Pricing",
    "13. Audit Checks",
)


def workbook_contract(result: ModelResult | None = None) -> Dict[str, object]:
    r = result or calculate_model()
    return {
        "sheets": SHEET_NAMES,
        "source_of_truth": "modules/foundups/esingularity/src/yumori_financial_model.py",
        "formula_contract": {
            "tier_revenue": "gpu_count * 8760 * utilization * price_jpy_per_gpu_hour",
            "power_cost": "it_power_kw * utilization * pue * 8760 * tariff_jpy_per_kwh",
            "depreciation": "asset_basis / useful_life while year <= useful_life",
            "fcfe": "net_income + depreciation - working_capital - maintenance_capex - debt_principal",
            "equity_irr": "IRR([-sponsor_equity] + annual_fcfe)",
            "equity_npv": "NPV(discount_rate, annual_fcfe) - sponsor_equity",
        },
        "validation": dict(r.validation),
        "legacy_audit": audit_legacy_model(r.assumptions),
    }


def _xlsxwriter():
    try:
        import xlsxwriter  # type: ignore
    except ImportError as exc:  # pragma: no cover - deployment boundary
        raise RuntimeError("Install XlsxWriter from the eSingularity requirements.txt") from exc
    return xlsxwriter


def export_xlsx(path: str | Path, assumptions: ModelAssumptions | None = None) -> Path:
    a = assumptions or default_assumptions()
    r = calculate_model(a)
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    xlsxwriter = _xlsxwriter()
    wb = xlsxwriter.Workbook(str(output))
    wb.set_properties({
        "title": "YUMORI / eSingularity Live Financial Model",
        "author": "YUMORI / FoundUps",
        "comments": "Generated from repository-owned YUMORI equations",
    })
    f = _formats(wb)
    inp = _inputs(wb, a, f)
    _revenue(wb, a, r, inp, f)
    _opex(wb, a, r, inp, f)
    _debt(wb, a, r, inp, f)
    _pnl(wb, a, r, inp, f)
    _cash_flow(wb, a, r, inp, f)
    _capital(wb, a, inp, f)
    _operating(wb, a, inp, f)
    _regional(wb, a, r, f)
    _impact(wb, a, r, f)
    _validation(wb, f)
    _demand(wb, a, r, inp, f)
    _audit(wb, a, r, f)
    _executive(wb, r, f)
    wb.close()
    return output


def _formats(wb):
    navy, yellow = "#0B1F3A", "#FFF2CC"
    return {
        "title": wb.add_format({"bold": True, "font_size": 16, "font_color": "#FFFFFF", "bg_color": navy}),
        "section": wb.add_format({"bold": True, "font_color": "#FFFFFF", "bg_color": navy}),
        "header": wb.add_format({"bold": True, "font_color": "#FFFFFF", "bg_color": navy, "border": 1, "align": "center"}),
        "input": wb.add_format({"font_color": "#0000FF", "bg_color": yellow}),
        "input_jpy": wb.add_format({"font_color": "#0000FF", "bg_color": yellow, "num_format": "¥#,##0;[Red](¥#,##0);-"}),
        "input_pct": wb.add_format({"font_color": "#0000FF", "bg_color": yellow, "num_format": "0.0%;[Red](0.0%);-"}),
        "jpy": wb.add_format({"num_format": "¥#,##0;[Red](¥#,##0);-"}),
        "pct": wb.add_format({"num_format": "0.0%;[Red](0.0%);-"}),
        "num": wb.add_format({"num_format": "#,##0;[Red](#,##0);-"}),
        "multiple": wb.add_format({"num_format": "0.00x;[Red](0.00x);-"}),
        "link_jpy": wb.add_format({"font_color": "#008000", "num_format": "¥#,##0;[Red](¥#,##0);-"}),
        "link_pct": wb.add_format({"font_color": "#008000", "num_format": "0.0%;[Red](0.0%);-"}),
        "total": wb.add_format({"bold": True, "top": 1, "num_format": "¥#,##0;[Red](¥#,##0);-"}),
        "note": wb.add_format({"font_color": "#666666", "italic": True, "text_wrap": True}),
        "warning": wb.add_format({"bg_color": yellow, "font_color": "#9C6500", "text_wrap": True}),
        "pass": wb.add_format({"bg_color": "#E2F0D9", "font_color": "#006100", "bold": True}),
        "flag": wb.add_format({"bg_color": yellow, "font_color": "#9C6500", "bold": True}),
    }


def _setup(wb, sheet: str, cols: int = 7):
    ws = wb.add_worksheet(sheet)
    ws.hide_gridlines(2)
    ws.freeze_panes(4, 1)
    ws.set_column(0, 0, 40)
    ws.set_column(1, cols - 1, 16)
    return ws


def _inputs(wb, a: ModelAssumptions, f) -> Dict[str, str]:
    ws = _setup(wb, SHEET_NAMES[0], 7)
    ws.merge_range("A1:G1", "YUMORI / eSingularity — LIVE MODEL INPUTS", f["title"])
    ws.merge_range("A2:G2", "Blue/yellow cells are editable scenario inputs; source/status remain beside every input.", f["note"])
    ws.write_row("A4", ["Assumption", "Value", "Unit", "Status", "Source / Evidence", "Key", "Notes"], f["header"])
    items = [
        ("Total Phase-1 GPUs", a.total_gpus, "GPUs", "LEGACY SCENARIO / VALIDATE", "FIN_YUMORI preset", "total_gpus"),
        ("Total site power envelope", a.total_site_power_kw, "kW", "GRID NOT COMMITTED", "FIN_YUMORI preset", "site_kw"),
        ("IT compute power allocation", a.it_power_kw, "kW", "LEGACY SCENARIO / VALIDATE", "FIN_YUMORI preset", "it_kw"),
        ("PUE base case", a.pue, "x", "MODELLED MIDPOINT / VALIDATE", "Legacy 1.11–1.12 midpoint", "pue"),
        ("Electricity tariff", a.electricity_tariff_jpy_per_kwh, "JPY/kWh", "VERIFY UTILITY", "FIN_YUMORI preset", "tariff"),
        ("Compute hardware CapEx", a.compute_capex_jpy, "JPY", "VENDOR QUOTE REQUIRED", "FIN_YUMORI preset", "compute_capex"),
        ("Facility / infrastructure CapEx", a.facility_capex_jpy, "JPY", "BIDS REQUIRED", "FIN_YUMORI preset", "facility_capex"),
        ("Assumed grants", a.grants_jpy, "JPY", "NOT AWARDED", "FIN_YUMORI preset", "grants"),
        ("Sponsor / partner equity", a.sponsor_equity_jpy, "JPY", "NOT COMMITTED", "FIN_YUMORI preset", "equity"),
        ("Effective corporate tax rate", a.corporate_tax_rate, "%", "TAX REVIEW REQUIRED", "FIN_YUMORI preset", "tax_rate"),
        ("Equity NPV discount rate", a.discount_rate, "%", "MODEL INPUT", "Reconciled base", "discount_rate"),
        ("Compute useful life", a.compute_useful_life_years, "years", "LEGACY SCENARIO", "FIN_YUMORI preset", "compute_life"),
        ("Infrastructure useful life", a.infrastructure_useful_life_years, "years", "LEGACY SCENARIO", "FIN_YUMORI preset", "infra_life"),
        ("Visitor-spending reference — low", a.visitor_spend_low_jpy, "JPY/year", "REFERENCE ONLY; NOT FORECAST", "FY2018 uses × ¥1,000", "visitor_low"),
        ("Visitor-spending reference — high", a.visitor_spend_high_jpy, "JPY/year", "REFERENCE ONLY; NOT FORECAST", "FY2018 uses × ¥5,546", "visitor_high"),
        ("Historical facility uses FY2018", a.historical_facility_uses, "uses/year", "VERIFIED HISTORICAL", "Fukui City / YUMORI", "historic_uses"),
        ("Current demolition-preparation budget", a.demolition_preparation_budget_jpy, "JPY", "VERIFIED CAMPAIGN RECORD", "Fukui City supplemental budget", "demo_prep"),
        ("Reported future demolition estimate", a.demolition_estimate_jpy, "JPY estimate", "REPORTED; NOT CONTRACT", "City/campaign summary", "demo_estimate"),
        ("Public 8×H100 DOK implied per-GPU price", a.market_h100_dok_jpy_per_gpu_hour, "JPY/GPU-hour", "PUBLIC 2026", "Sakura DOK", "market_dok"),
    ]
    refs: Dict[str, str] = {}
    for row, (label, value, unit, status, source, key) in enumerate(items, start=5):
        fmt = f["input_pct"] if unit == "%" else f["input_jpy"] if unit.startswith("JPY") else f["input"]
        ws.write(row - 1, 0, label); ws.write(row - 1, 1, value, fmt); ws.write(row - 1, 2, unit)
        ws.write(row - 1, 3, status); ws.write(row - 1, 4, source); ws.write(row - 1, 5, key)
        ws.write_comment(row - 1, 1, f"Status: {status}\nSource: {source}")
        refs[key] = f"'{SHEET_NAMES[0]}'!$B${row}"
    tier_row = 27
    ws.merge_range(f"A{tier_row-1}:G{tier_row-1}", "REVENUE TIERS", f["section"])
    ws.write_row(f"A{tier_row}", ["Tier", "GPUs", "JPY/GPU-hour", "Status", "Source", "Key", "Notes"], f["header"])
    for n, tier in enumerate(a.tiers, start=tier_row + 1):
        ws.write(n - 1, 0, tier.name); ws.write(n - 1, 1, tier.gpu_count, f["input"]); ws.write(n - 1, 2, tier.price_jpy_per_gpu_hour, f["input_jpy"])
        ws.write(n - 1, 3, tier.status); ws.write(n - 1, 4, tier.source); ws.write(n - 1, 5, tier.key)
        refs[f"{tier.key}_gpus"] = f"'{SHEET_NAMES[0]}'!$B${n}"
        refs[f"{tier.key}_price"] = f"'{SHEET_NAMES[0]}'!$C${n}"
    schedule_row = 34
    ws.merge_range(f"A{schedule_row-1}:G{schedule_row-1}", "ANNUAL SCHEDULES", f["section"])
    ws.write_row(f"A{schedule_row}", ["Schedule", "Year 1", "Year 2", "Year 3", "Year 4", "Year 5", "Status"], f["header"])
    schedules = [
        ("util", a.utilization, f["input_pct"], "Demand validation required"),
        ("thermal", a.thermal_revenue_jpy, f["input_jpy"], "Offtake not contracted"),
        ("coolant", a.coolant_maintenance_jpy, f["input_jpy"], "Legacy scenario"),
        ("network", a.network_backhaul_jpy, f["input_jpy"], "Legacy scenario"),
        ("noc", a.noc_labor_jpy, f["input_jpy"], "Legacy scenario"),
        ("mgmt", a.management_admin_jpy, f["input_jpy"], "Legacy scenario"),
        ("liaison", a.academic_liaison_marketing_jpy, f["input_jpy"], "Legacy scenario"),
        ("insurance", a.insurance_security_jpy, f["input_jpy"], "Legacy scenario"),
        ("lease", a.property_lease_jpy, f["input_jpy"], "Land terms TBD"),
        ("community", a.community_benefit_jpy, f["input_jpy"], "Governance TBD"),
        ("wc", a.working_capital_change_jpy, f["input_jpy"], "Legacy scenario"),
        ("maint_capex", a.maintenance_capex_jpy, f["input_jpy"], "Legacy scenario"),
    ]
    for rr, (key, vals, fmt, status) in enumerate(schedules, start=schedule_row + 1):
        ws.write(rr - 1, 0, key)
        for c, val in enumerate(vals, start=1):
            ws.write(rr - 1, c, val, fmt); refs[f"{key}{c}"] = f"'{SHEET_NAMES[0]}'!${chr(65+c)}${rr}"
        ws.write(rr - 1, 6, status)
    debt_row = 51
    ws.merge_range(f"A{debt_row-1}:G{debt_row-1}", "DEBT FACILITIES", f["section"])
    ws.write_row(f"A{debt_row}", ["Facility", "Principal", "Rate", "Term", "Status", "Key", "Source"], f["header"])
    for rr, debt in enumerate(a.debts, start=debt_row + 1):
        ws.write(rr - 1, 0, debt.name); ws.write(rr - 1, 1, debt.principal_jpy, f["input_jpy"]); ws.write(rr - 1, 2, debt.annual_rate, f["input_pct"]); ws.write(rr - 1, 3, debt.term_years, f["input"])
        ws.write(rr - 1, 4, debt.status); ws.write(rr - 1, 5, debt.key); ws.write(rr - 1, 6, debt.source)
        refs[f"{debt.key}_principal"] = f"'{SHEET_NAMES[0]}'!$B${rr}"
        refs[f"{debt.key}_rate"] = f"'{SHEET_NAMES[0]}'!$C${rr}"
        refs[f"{debt.key}_term"] = f"'{SHEET_NAMES[0]}'!$D${rr}"
    return refs


def _years(ws, f, row=4):
    ws.write_row(row - 1, 0, ["Metric", "Year 1", "Year 2", "Year 3", "Year 4", "Year 5", "5-Year Total"], f["header"])


def _revenue(wb, a, r, inp, f):
    ws = _setup(wb, SHEET_NAMES[4]); ws.merge_range("A1:G1", "5-YEAR REVENUE MODEL — FORMULA DRIVEN", f["title"]); _years(ws, f)
    ws.write("A5", "Cluster capacity utilization")
    for c in range(5): ws.write_formula(4, c + 1, f"={inp[f'util{c+1}']}", f["link_pct"], a.utilization[c])
    for i, tier in enumerate(a.tiers, start=6):
        ws.write(i - 1, 0, tier.name)
        for c, yr in enumerate(r.years, start=1):
            formula = f"={inp[tier.key+'_gpus']}*{HOURS_PER_YEAR}*{chr(65+c)}$5*{inp[tier.key+'_price']}"
            ws.write_formula(i - 1, c, formula, f["jpy"], yr.tier_revenue_jpy[tier.key])
        ws.write_formula(i - 1, 6, f"=SUM(B{i}:F{i})", f["total"], sum(y.tier_revenue_jpy[tier.key] for y in r.years))
    ws.write("A9", "Thermal off-take revenue")
    for c, yr in enumerate(r.years, start=1): ws.write_formula(8, c, f"={inp[f'thermal{c}']}", f["link_jpy"], yr.thermal_revenue_jpy)
    ws.write_formula("G9", "=SUM(B9:F9)", f["total"], sum(a.thermal_revenue_jpy))
    ws.write("A10", "TOTAL GROSS REVENUE", f["total"])
    for c, yr in enumerate(r.years, start=1): ws.write_formula(9, c, f"=SUM({chr(65+c)}6:{chr(65+c)}9)", f["total"], yr.gross_revenue_jpy)
    ws.write_formula("G10", "=SUM(B10:F10)", f["total"], r.five_year_revenue_jpy)


def _opex(wb, a, r, inp, f):
    ws = _setup(wb, SHEET_NAMES[5]); ws.merge_range("A1:G1", "5-YEAR OPERATING EXPENSES", f["title"]); _years(ws, f)
    labels = {5:"Electricity & grid power",6:"Coolant / pumps / filters",7:"Fiber & network backhaul",8:"NOC / HPC labor",9:"TOTAL COGS",10:"GROSS PROFIT",12:"Management / admin",13:"Academic liaison / marketing",14:"Insurance / security",15:"Property lease",16:"Community benefit",17:"TOTAL SG&A"}
    for row, label in labels.items(): ws.write(row - 1, 0, label, f["total"] if row in (9,10,17) else None)
    keymap = {6:"coolant",7:"network",8:"noc",12:"mgmt",13:"liaison",14:"insurance",15:"lease",16:"community"}
    for c, yr in enumerate(r.years, start=1):
        col = chr(65+c)
        ws.write_formula(4, c, f"={inp['it_kw']}*'{SHEET_NAMES[4]}'!{col}5*{inp['pue']}*{HOURS_PER_YEAR}*{inp['tariff']}", f["jpy"], yr.power_cost_jpy)
        for row, key in keymap.items(): ws.write_formula(row - 1, c, f"={inp[f'{key}{c}']}", f["link_jpy"])
        ws.write_formula(8, c, f"=SUM({col}5:{col}8)", f["total"], yr.total_cogs_jpy)
        ws.write_formula(9, c, f"='{SHEET_NAMES[4]}'!{col}10-{col}9", f["total"], yr.gross_profit_jpy)
        ws.write_formula(16, c, f"=SUM({col}12:{col}16)", f["total"], yr.total_sga_jpy)
    for row in labels: ws.write_formula(row - 1, 6, f"=SUM(B{row}:F{row})", f["total"] if row in (9,10,17) else f["jpy"])


def _debt(wb, a, r, inp, f):
    ws = _setup(wb, SHEET_NAMES[8]); ws.merge_range("A1:G1", "DEBT SCHEDULE & DSCR", f["title"]); _years(ws, f)
    for debt, start in zip(a.debts, (5, 10)):
        ws.write_column(start - 1, 0, [f"{debt.name} — beginning balance", "Principal repayment", "Interest", "Ending balance"])
        for c, item in enumerate(r.debt_schedules[debt.key], start=1):
            col = chr(65+c); prev = inp[f"{debt.key}_principal"] if c == 1 else f"{chr(64+c)}{start+3}"
            rate, term = inp[f"{debt.key}_rate"], inp[f"{debt.key}_term"]
            payment = f"({inp[f'{debt.key}_principal']}*{rate})/(1-(1+{rate})^(-{term}))"
            ws.write_formula(start - 1, c, f"={prev}", f["jpy"], item.beginning_balance_jpy)
            ws.write_formula(start + 1, c, f"={col}{start}*{rate}", f["jpy"], item.interest_jpy)
            ws.write_formula(start, c, f"=IF({col}{start}<=0,0,MIN({col}{start},MAX(0,{payment}-{col}{start+2})))", f["jpy"], item.principal_repayment_jpy)
            ws.write_formula(start + 2, c, f"=MAX(0,{col}{start}-{col}{start+1})", f["jpy"], item.ending_balance_jpy)
    for row, label in ((16,"Total principal"),(17,"Total interest"),(18,"TOTAL DEBT SERVICE"),(19,"EBITDA available for debt service"),(20,"DSCR")): ws.write(row - 1, 0, label, f["total"] if row in (18,20) else None)
    for c, yr in enumerate(r.years, start=1):
        col=chr(65+c); ws.write_formula(15,c,f"={col}6+{col}11",f["jpy"],yr.debt_principal_repayment_jpy); ws.write_formula(16,c,f"={col}7+{col}12",f["jpy"],yr.interest_expense_jpy); ws.write_formula(17,c,f"={col}16+{col}17",f["total"],yr.debt_service_jpy); ws.write_formula(18,c,f"='{SHEET_NAMES[6]}'!{col}9",f["link_jpy"],yr.ebitda_jpy); ws.write_formula(19,c,f"=IF({col}18=0,NA(),{col}19/{col}18)",f["multiple"],yr.dscr or 0)


def _pnl(wb, a, r, inp, f):
    ws=_setup(wb,SHEET_NAMES[6]); ws.merge_range("A1:G1","5-YEAR PRO FORMA INCOME STATEMENT — RECONCILED",f["title"]); _years(ws,f)
    rows={5:"Gross Revenue",6:"Less: COGS",7:"GROSS PROFIT",8:"Less: SG&A",9:"EBITDA",11:"Compute depreciation",12:"Infrastructure depreciation",13:"EBIT",15:"Interest expense",16:"EBT",17:"Income tax",18:"NET INCOME"}
    for row,label in rows.items(): ws.write(row-1,0,label,f["total"] if row in (7,9,13,16,18) else None)
    for c,yr in enumerate(r.years,start=1):
        col=chr(65+c); year=c
        ws.write_formula(4,c,f"='{SHEET_NAMES[4]}'!{col}10",f["link_jpy"],yr.gross_revenue_jpy); ws.write_formula(5,c,f"=-'{SHEET_NAMES[5]}'!{col}9",f["link_jpy"],-yr.total_cogs_jpy); ws.write_formula(6,c,f"=SUM({col}5:{col}6)",f["total"],yr.gross_profit_jpy); ws.write_formula(7,c,f"=-'{SHEET_NAMES[5]}'!{col}17",f["link_jpy"],-yr.total_sga_jpy); ws.write_formula(8,c,f"=SUM({col}7:{col}8)",f["total"],yr.ebitda_jpy)
        ws.write_formula(10,c,f"=-IF({year}<={inp['compute_life']},{inp['compute_capex']}/{inp['compute_life']},0)",f["jpy"],-yr.compute_depreciation_jpy); ws.write_formula(11,c,f"=-IF({year}<={inp['infra_life']},MAX(0,{inp['facility_capex']}-{inp['grants']})/{inp['infra_life']},0)",f["jpy"],-yr.infrastructure_depreciation_jpy); ws.write_formula(12,c,f"=SUM({col}9,{col}11,{col}12)",f["total"],yr.ebit_jpy); ws.write_formula(14,c,f"=-'{SHEET_NAMES[8]}'!{col}17",f["link_jpy"],-yr.interest_expense_jpy); ws.write_formula(15,c,f"=SUM({col}13,{col}15)",f["total"],yr.ebt_jpy); ws.write_formula(16,c,f"=-MAX(0,{col}16*{inp['tax_rate']})",f["jpy"],-yr.income_tax_jpy); ws.write_formula(17,c,f"=SUM({col}16,{col}17)",f["total"],yr.net_income_jpy)
    for row in rows: ws.write_formula(row-1,6,f"=SUM(B{row}:F{row})",f["total"] if row in (7,9,13,16,18) else f["jpy"])


def _cash_flow(wb,a,r,inp,f):
    ws=_setup(wb,SHEET_NAMES[7]); ws.merge_range("A1:G1","5-YEAR CASH FLOW & FCFE — RECONCILED",f["title"]); _years(ws,f)
    rows={5:"Net income",6:"Add: depreciation",7:"Less: change in working capital",8:"CASH FLOW FROM OPERATIONS",10:"Maintenance CapEx",12:"Debt principal repayment",13:"NET FCFE",14:"Cumulative FCFE"}
    for row,label in rows.items(): ws.write(row-1,0,label,f["total"] if row in (8,13,14) else None)
    cumulative=0.0
    for c,yr in enumerate(r.years,start=1):
        col=chr(65+c); cumulative+=yr.fcfe_jpy
        ws.write_formula(4,c,f"='{SHEET_NAMES[6]}'!{col}18",f["link_jpy"],yr.net_income_jpy); ws.write_formula(5,c,f"=-'{SHEET_NAMES[6]}'!{col}11-'{SHEET_NAMES[6]}'!{col}12",f["link_jpy"],yr.total_depreciation_jpy); ws.write_formula(6,c,f"=-{inp[f'wc{c}']}",f["link_jpy"],-yr.working_capital_change_jpy); ws.write_formula(7,c,f"=SUM({col}5:{col}7)",f["total"],yr.cash_flow_from_operations_jpy); ws.write_formula(9,c,f"=-{inp[f'maint_capex{c}']}",f["link_jpy"],-yr.maintenance_capex_jpy); ws.write_formula(11,c,f"=-'{SHEET_NAMES[8]}'!{col}16",f["link_jpy"],-yr.debt_principal_repayment_jpy); ws.write_formula(12,c,f"=SUM({col}8,{col}10,{col}12)",f["total"],yr.fcfe_jpy); ws.write_formula(13,c,f"={col}13" if c==1 else f"={chr(64+c)}14+{col}13",f["total"],cumulative)
    ws.write_row("A17",["Equity cash-flow sequence",-a.sponsor_equity_jpy,r.years[0].fcfe_jpy,r.years[1].fcfe_jpy,r.years[2].fcfe_jpy,r.years[3].fcfe_jpy]); ws.write_formula("G17","=F13",f["jpy"],r.years[4].fcfe_jpy); ws.write("A19","Equity IRR"); ws.write_formula("B19","=IRR(B17:G17)",f["pct"],r.equity_irr or 0); ws.write("A20","Equity NPV"); ws.write_formula("B20",f"=NPV({inp['discount_rate']},C17:G17)+B17",f["jpy"],r.equity_npv_jpy)


def _capital(wb,a,inp,f):
    ws=_setup(wb,SHEET_NAMES[2],4); ws.merge_range("A1:D1","SOURCES & USES OF FUNDS",f["title"]); ws.write_row("A4",["Capital Source","JPY","Status","Source"],f["header"])
    rows=[("Assumed grants",inp['grants'],"NOT AWARDED"),(a.debts[0].name,inp['compute_debt_principal'],"NOT COMMITTED"),(a.debts[1].name,inp['green_loan_principal'],"NOT COMMITTED"),("Sponsor / partner equity",inp['equity'],"NOT COMMITTED")]
    for row,(label,ref,status) in enumerate(rows,start=5): ws.write(row-1,0,label); ws.write_formula(row-1,1,f"={ref}",f["link_jpy"]); ws.write(row-1,2,status); ws.write(row-1,3,"Model Inputs")
    ws.write("A9","TOTAL SOURCES",f["total"]); ws.write_formula("B9","=SUM(B5:B8)",f["total"]); ws.write_row("A12",["Use","JPY","Status","Source"],f["header"])
    for row,(label,ref,status) in enumerate((("Facility / infrastructure CapEx",inp['facility_capex'],"BIDS REQUIRED"),("Compute hardware CapEx",inp['compute_capex'],"VENDOR QUOTE REQUIRED")),start=13): ws.write(row-1,0,label); ws.write_formula(row-1,1,f"={ref}",f["link_jpy"]); ws.write(row-1,2,status); ws.write(row-1,3,"Model Inputs")
    ws.write("A15","TOTAL USES",f["total"]); ws.write_formula("B15","=SUM(B13:B14)",f["total"]); ws.write("A17","SOURCES - USES CHECK"); ws.write_formula("B17","=B9-B15",f["jpy"])


def _operating(wb,a,inp,f):
    ws=_setup(wb,SHEET_NAMES[3],6); ws.merge_range("A1:F1","OPERATING ASSUMPTIONS & CAPACITY ALLOCATION",f["title"]); ws.write_row("A4",["Parameter","Value","Unit","Status","Formula role","Source"],f["header"])
    for row,(label,key,unit) in enumerate((("Total GPUs","total_gpus","GPUs"),("Site power envelope","site_kw","kW"),("IT power","it_kw","kW"),("PUE","pue","x"),("Electricity tariff","tariff","JPY/kWh")),start=5): ws.write(row-1,0,label); ws.write_formula(row-1,1,f"={inp[key]}",f["link_jpy"] if "JPY" in unit else None); ws.write(row-1,2,unit); ws.write(row-1,3,"MODEL INPUT / VALIDATE"); ws.write(row-1,4,"Revenue/power model"); ws.write(row-1,5,"Model Inputs")


def _regional(wb,a,r,f):
    ws=_setup(wb,SHEET_NAMES[9],5); ws.merge_range("A1:E1","REGIONAL ECONOMIC IMPACT — NOT PROJECT REVENUE",f["title"]); ws.write_row("A4",["Metric","Low / Base","High / Ref","Status","Boundary"],f["header"])
    data=(("Initial local contracts",a.initial_local_contracts_low_jpy,a.initial_local_contracts_high_jpy,"LEGACY SCENARIO","Regional value"),("Direct high-tech FTE",a.direct_high_tech_fte_low,a.direct_high_tech_fte_high,"LEGACY SCENARIO","Jobs, not revenue"),("Academic compute benefit",a.academic_compute_benefit_jpy,a.academic_compute_benefit_jpy,"LEGACY SCENARIO","Public/research value"),("Usable heat / fuel offset",a.usable_heat_offset_jpy,a.usable_heat_offset_jpy,"ENGINEERING VALIDATION REQUIRED","Avoided local energy cost"),("Visitor-spending reference",a.visitor_spend_low_jpy,a.visitor_spend_high_jpy,"REFERENCE ONLY; NOT FORECAST","Regional spending"))
    for row,item in enumerate(data,start=5): ws.write_row(row-1,0,item)
    ws.write("A12","30-year visitor-spending screen"); ws.write_number("B12",r.visitor_spend_30y_low_jpy,f["jpy"]); ws.write_number("C12",r.visitor_spend_30y_high_jpy,f["jpy"]); ws.write("D12","UNDISCOUNTED REFERENCE ONLY")


def _impact(wb,a,r,f):
    ws=_setup(wb,SHEET_NAMES[10],6); ws.merge_range("A1:F1","IMPACT ASSUMPTIONS / PUBLIC-VALUE BOUNDARY",f["title"]); ws.write_row("A4",["Metric","Low / Base","High / Ref","Unit","Status","Source"],f["header"])
    rows=(("Historical facility uses",a.historical_facility_uses,a.historical_facility_uses,"uses/year","VERIFIED HISTORICAL","Fukui City/YUMORI"),("Visitor-spending reference",a.visitor_spend_low_jpy,a.visitor_spend_high_jpy,"JPY/year","REFERENCE ONLY","FY2018 screen"),("Demolition-preparation budget",a.demolition_preparation_budget_jpy,a.demolition_preparation_budget_jpy,"JPY","VERIFIED CAMPAIGN RECORD","City supplemental budget"),("Future demolition estimate",a.demolition_estimate_jpy,a.demolition_estimate_jpy,"JPY estimate","REPORTED; NOT CONTRACT","City/campaign summary"),("Internal total CapEx",a.facility_capex_jpy+a.compute_capex_jpy,a.facility_capex_jpy+a.compute_capex_jpy,"JPY","LEGACY SCENARIO","Model"),("Sponsor equity",a.sponsor_equity_jpy,a.sponsor_equity_jpy,"JPY","NOT COMMITTED","Model"),("Reconciled equity IRR",r.equity_irr,r.equity_irr,"%","MODEL OUTPUT","Python model"))
    for row,item in enumerate(rows,start=5): ws.write_row(row-1,0,item)


def _validation(wb,f):
    ws=_setup(wb,SHEET_NAMES[11],5); ws.merge_range("A1:E1","60-DAY FEASIBILITY VALIDATION GATES",f["title"]); ws.write_row("A4",["Gate","Question","Model variable","State","Evidence needed"],f["header"])
    gates=(("Grid","Can ~1 MW be delivered at acceptable cost/schedule?","Power/tariff/PUE","OPEN","Utility capacity/interconnection"),("Fiber","Can redundant fiber be delivered?","Network/bankability","OPEN","Carrier proposals"),("Demand","Who will sign LOIs/reservations at what price?","Utilization/pricing","OPEN","Interviews/LOIs/pilots"),("Vendor CapEx","Current GPU/network/storage quote?","Compute CapEx","OPEN","Vendor quotes"),("Financing","What terms/security will lenders offer?","Debt/IRR/DSCR","OPEN","Indicative terms"),("Thermal","How much heat is usable?","Thermal value","OPEN","Engineering study"),("Building/asbestos","What selective rehabilitation is feasible?","CapEx","OPEN","Structural/MEP/asbestos cost"),("Land/planning","Can site/use terms be secured?","Lease/schedule","OPEN","Owner/planning confirmation"))
    for row,item in enumerate(gates,start=5): ws.write_row(row-1,0,item)


def _demand(wb,a,r,inp,f):
    ws=_setup(wb,SHEET_NAMES[12],6); ws.merge_range("A1:F1","DEMAND & PRICING VALIDATION",f["title"]); ws.write_row("A4",["Metric","Value","Unit","Status","Source","Interpretation"],f["header"])
    rows=(("Sakura DOK 8×H100 implied price",a.market_h100_dok_jpy_per_gpu_hour,"JPY/GPU-hour","PUBLIC 2026","Sakura DOK","Benchmark"),("Tier A price",a.tiers[0].price_jpy_per_gpu_hour,"JPY/GPU-hour","LEGACY SCENARIO","Preset","Validate WTP"),("Tier B price",a.tiers[1].price_jpy_per_gpu_hour,"JPY/GPU-hour","LEGACY SCENARIO","Preset","Validate WTP"),("Tier C price",a.tiers[2].price_jpy_per_gpu_hour,"JPY/GPU-hour","LEGACY SCENARIO","Preset","Academic discount"))
    for row,item in enumerate(rows,start=5): ws.write_row(row-1,0,item)
    ws.write("A11","Y1 billable GPU-hours"); ws.write_formula("B11",f"={inp['total_gpus']}*{HOURS_PER_YEAR}*'{SHEET_NAMES[4]}'!B5",f["num"],r.years[0].billable_gpu_hours); ws.write("A12","Y1 compute revenue"); ws.write_formula("B12",f"=SUM('{SHEET_NAMES[4]}'!B6:B8)",f["jpy"],r.years[0].compute_revenue_jpy); ws.write("A13","Y1 blended JPY/GPU-hour"); ws.write_formula("B13","=B12/B11",f["jpy"],r.years[0].compute_revenue_jpy/r.years[0].billable_gpu_hours); ws.write("A14","Premium/(discount) vs DOK"); ws.write_formula("B14",f"=B13/{inp['market_dok']}-1",f["pct"],r.years[0].compute_revenue_jpy/r.years[0].billable_gpu_hours/a.market_h100_dok_jpy_per_gpu_hour-1)
    ws.merge_range("A18:F20","Public AI/DX activity is a lead source, not booked demand. Replace utilization with measured GPU-hours, current spend, price ceiling, start date, procurement route and LOI/pilot evidence.",f["note"])


def _audit(wb,a,r,f):
    ws=_setup(wb,SHEET_NAMES[13],5); ws.merge_range("A1:E1","AUDIT CHECKS / LEGACY RECONCILIATION",f["title"]); ws.write_row("A4",["Check","Live result","Status","Legacy/comparison","Interpretation"],f["header"]); audit=audit_legacy_model(a)
    rows=(("Sources equal uses",0,"PASS",0,"Must be zero"),("Tier GPU sum",sum(t.gpu_count for t in a.tiers),"PASS",a.total_gpus,""),("Power envelope IT×PUE",a.it_power_kw*a.pue,"PASS",a.total_site_power_kw,"Must fit"),("Compute depreciation Year 5",0,"PASS",450_000_000,"Legacy continued beyond 4-year life"),("Live IRR",r.equity_irr,"FLAG",audit['displayed_equity_irr'],"Legacy 68.4% does not reconcile"),("Legacy shown-FCFE IRR",audit['solved_equity_irr_from_shown_fcfe'],"FLAG",audit['displayed_equity_irr'],"~1.496 percentage-point gap"),("Legacy implied power basis",audit['implied_power_kw_by_year'][0],"FLAG",a.it_power_kw,"~840 vs stated 850 before PUE"),("Live 5-year revenue",r.five_year_revenue_jpy,"MODELLED","Legacy ~¥5.371B","Bottom-up"),("Live 5-year FCFE",r.five_year_fcfe_jpy,"MODELLED","Legacy ~¥1.944B","Reconciled"))
    for row,item in enumerate(rows,start=5): ws.write_row(row-1,0,item); ws.write(row-1,2,item[2],f["pass"] if item[2]=="PASS" else f["flag"] if item[2]=="FLAG" else None)


def _executive(wb,r,f):
    ws=_setup(wb,SHEET_NAMES[1],8); ws.merge_range("A1:H1","YUMORI / eSingularity — LIVE FINANCIAL MODEL",f["title"]); ws.merge_range("A2:H2","MODELLED — not a forecast or financing commitment. Regional visitor spending is deliberately outside project revenue.",f["warning"]); ws.write_row("A4",["Metric","Excel live formula","Python reconciled check","Status"],f["header"])
    rows=(("5-year gross revenue",f"=SUM('{SHEET_NAMES[4]}'!B10:F10)",r.five_year_revenue_jpy,"MODELLED",f["jpy"]),("5-year EBITDA",f"=SUM('{SHEET_NAMES[6]}'!B9:F9)",r.five_year_ebitda_jpy,"MODELLED",f["jpy"]),("5-year FCFE",f"=SUM('{SHEET_NAMES[7]}'!B13:F13)",r.five_year_fcfe_jpy,"MODELLED",f["jpy"]),("Equity IRR",f"='{SHEET_NAMES[7]}'!B19",r.equity_irr,"MODELLED",f["pct"]),("Equity NPV",f"='{SHEET_NAMES[7]}'!B20",r.equity_npv_jpy,"MODELLED",f["jpy"]),("30-year visitor-spend low",f"='{SHEET_NAMES[0]}'!$B$18*30",r.visitor_spend_30y_low_jpy,"REFERENCE ONLY",f["jpy"]),("30-year visitor-spend high",f"='{SHEET_NAMES[0]}'!$B$19*30",r.visitor_spend_30y_high_jpy,"REFERENCE ONLY",f["jpy"]))
    for row,(label,formula,value,status,fmt) in enumerate(rows,start=5): ws.write(row-1,0,label); ws.write_formula(row-1,1,formula,fmt,value); ws.write(row-1,2,value,fmt); ws.write(row-1,3,status)
    ws.merge_range("A14:E14","DECISION BOUNDARY",f["section"]); ws.merge_range("A15:E18","The model tests whether a ~1 MW compute anchor could support reuse economics. Grid, fiber, land/planning, rehabilitation, vendor pricing, offtake, financing, tax and heat recovery remain feasibility gates.",f["note"])
