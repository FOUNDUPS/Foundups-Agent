"""Costed hypotheses feeding the canonical portfolio engine, never commitments.

All money is nominal JPY excluding consumption tax. Years are operating years,
not promised construction dates. Numeric planning completeness is not evidence.
"""

import json
from dataclasses import replace
from math import ceil, isfinite
from pathlib import Path

from .yumori_portfolio_model import (
    AnnualCashInputs, PortfolioInputs, SiteCost, SiteFinancialInputs,
    SCHOOL_COSTS, SUKATTO_COSTS, run_portfolio_model,
)

ASSUMPTIONS_PATH = Path(__file__).resolve().parents[1] / "data/yumori_planning_assumptions.json"


def load_planning_assumptions(path: Path = ASSUMPTIONS_PATH) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def design_node(site: dict, data: dict) -> dict:
    """Hypothetical demand drives discrete server units; no utility fact inferred."""
    hours, utilization = site["design_peak_gpu_hours"], site["design_utilization"]
    if hours < 0 or not 0 < utilization <= data["availability"] <= 1:
        raise ValueError("Invalid design demand/utilization")
    nodes = ceil(hours / (data["hours_per_year"] * utilization * data["gpus_per_node"]))
    peak = (nodes * data["node_max_kw"] + site["other_it_kw"]) * site["pue"] if nodes else 0
    return dict(nodes=nodes, gpus=nodes * data["gpus_per_node"], facility_kw=peak,
                confirmed_utility_kw=None, contracted_gpu_hours=0)


def cost_site(site: dict, data: dict, cost_case: str) -> list[dict]:
    node = design_node(site, data)
    expected = SUKATTO_COSTS if site["site_id"] == "Site 1" else SCHOOL_COSTS
    rows = []
    if len({c["category"] for c in site["costs"]}) != len(site["costs"]):
        raise ValueError("Duplicate cost component")
    for c in site["costs"]:
        quantity = node["nodes"] if c["quantity"] == "demand_nodes" else c["quantity"]
        rates = [c["unit_cost_jpy"][k] for k in ("low", "base", "high")]
        if not all(isfinite(v) and v >= 0 for v in [quantity, *rates]) or rates != sorted(rates):
            raise ValueError("Invalid cost range")
        if c["evidence"] != "MODEL ONLY" or not c["scope"]:
            raise ValueError("Planning allowances must retain MODEL ONLY and scope")
        rows.append(dict(c, resolved_quantity=quantity,
                         amount_jpy=quantity * c["unit_cost_jpy"][cost_case]))
    basis = sum(c["amount_jpy"] for c in rows if c["category"] not in {"compute_hardware", "optional_compute"})
    rows.append(dict(category="contingency", resolved_quantity=basis,
                     unit="non-compute direct cost", unit_cost_jpy=site["contingency"],
                     amount_jpy=basis * site["contingency"][cost_case], evidence="MODEL ONLY",
                     scope="Percentage of all non-compute direct lines, including fees; no contingency on contingency"))
    if {c["category"] for c in rows} != set(expected):
        raise ValueError("Missing or unexpected site cost component")
    return sorted(rows, key=lambda c: expected.index(c["category"]))


def compute_electricity(site: dict, data: dict, sold: float, scenario: dict, year: int) -> float:
    node = design_node(site, data)
    hours = data["hours_per_year"]
    if not isfinite(sold) or sold < 0 or sold > node["gpus"] * hours * data["availability"]:
        raise ValueError("Sold GPU-hours exceed available physical capacity")
    utilization = sold / (node["gpus"] * hours) if node["gpus"] else 0
    average_it = (node["nodes"] * data["node_max_kw"] *
                  (data["idle_power_fraction"] + (1 - data["idle_power_fraction"]) * utilization)
                  + site["other_it_kw"])
    energy = average_it * site["pue"] * hours * scenario["energy_jpy_kwh"] * (1 + scenario["energy_escalation"]) ** year
    demand = ceil(node["facility_kw"]) * scenario["demand_charge_jpy_kw_month"] * 12
    return energy + demand


def run_planning_scenario(name: str = "base", data: dict | None = None) -> dict:
    data = data or load_planning_assumptions()
    s = data["scenarios"][name]
    if len(s["gpu_hours"]) != 5 or not 0 <= s["debt_share"] <= 1:
        raise ValueError("Expected five years and a valid debt share")
    if min(s["debt_term_years"], s["investor_repayment_years"], s["compute_life_years"], s["infrastructure_life_years"]) <= 0:
        raise ValueError("Financing and useful lives must be positive")
    sites, cost_tables = [], {}
    for site in data["sites"]:
        costs = cost_site(site, data, s["cost_case"])
        cost_tables[site["site_id"]] = costs
        sites.append(SiteFinancialInputs(site["site_id"], site["priority"], tuple(
            SiteCost(c["category"], c["amount_jpy"], c["evidence"], c["scope"]) for c in costs)))
    hanyu = next(x for x in data["sites"] if x["site_id"] == "Site 3")
    costs = cost_tables["Site 3"]
    capex = sum(c["amount_jpy"] for c in costs)
    compute = next(c["amount_jpy"] for c in costs if c["category"] == "compute_hardware")
    debt, equity = capex * s["debt_share"], capex * (1 - s["debt_share"])
    opening_debt, previous_wc, annual, detail = debt, 0.0, [], []
    for y, sold in enumerate(s["gpu_hours"]):
        revenue = sold * s["price_jpy_gpu_hour"] * (1 + s["price_escalation"]) ** y
        electricity = compute_electricity(hanyu, data, sold, s, y)
        ops = s["operations_y1_jpy"] * (1 + s["operations_escalation"]) ** y + revenue * s["variable_opex_share"]
        maintenance, community = capex * s["maintenance_share_capex"], s["community_y1_jpy"]
        interest = opening_debt * s["debt_rate"]
        principal = min(opening_debt, debt / s["debt_term_years"])
        depreciation = (compute / s["compute_life_years"] if y < s["compute_life_years"] else 0) + ((capex - compute) / s["infrastructure_life_years"] if y < s["infrastructure_life_years"] else 0)
        ebitda = revenue - electricity - ops - maintenance - community
        # Simplified positive-income tax; no loss carryforward or VAT recovery assumed.
        tax = max(0, ebitda - depreciation - interest) * s["tax_rate"]
        wc = revenue * s["working_capital_share"]
        wc_increase = max(0, wc - previous_wc)  # no cash-release credit in this screen
        previous_wc = max(previous_wc, wc)
        renewal = compute * s["renewal_fraction_year5"] if y == 4 else 0
        investor_due = equity * s["investor_return_rate"] + (equity / s["investor_repayment_years"] if y < s["investor_repayment_years"] else 0)
        cash = AnnualCashInputs(revenue, electricity, ops, maintenance, tax, wc_increase,
                                renewal, principal + interest, capex * s["reserve_share_capex"],
                                investor_due, community)
        annual.append(cash)
        detail.append(dict(sold_gpu_hours=sold, price_jpy_gpu_hour=revenue / sold if sold else s["price_jpy_gpu_hour"],
                           opening_debt_jpy=opening_debt, principal_jpy=principal, interest_jpy=interest,
                           depreciation_jpy=depreciation, cash=vars(cash)))
        opening_debt -= principal
    later_cash = {}
    for site in data["sites"]:
        sid = site["site_id"]
        if sid == "Site 3":
            continue
        terms = data["later_site_cash"][sid]
        capital = sum(c["amount_jpy"] for c in cost_tables[sid])
        hardware = sum(c["amount_jpy"] for c in cost_tables[sid] if c["category"] == "compute_hardware")
        cash_rows, wc_peak = [], 0.0
        for y in range(5):
            if sid == "Site 2":
                revenue = terms["gpu_hours"][y] * terms["price_jpy_gpu_hour"] * (1 + terms["price_escalation"]) ** y
                electricity = compute_electricity(site, data, terms["gpu_hours"][y], s, y)
                operating = terms["operations_y1_jpy"] * (1 + terms["operations_escalation"]) ** y + revenue * s["variable_opex_share"]
            else:
                revenue = terms["visits"][y] * terms["revenue_per_visit_jpy"]
                electricity = 0  # INCLUDED in explicitly combined onsen variable cash Opex
                operating = terms["fixed_opex_y1_jpy"] * (1 + terms["operations_escalation"]) ** y + revenue * terms["variable_opex_share"]
            maintenance = capital * s["maintenance_share_capex"]
            ebitda = revenue - electricity - operating - maintenance
            depreciation = hardware / s["compute_life_years"] + (capital - hardware) / s["infrastructure_life_years"]
            tax = max(0, ebitda - depreciation) * s["tax_rate"]
            wc = revenue * s["working_capital_share"]
            increase, wc_peak = max(0, wc - wc_peak), max(wc_peak, wc)
            renewal = hardware * s["renewal_fraction_year5"] if y == 4 else 0
            cash_rows.append(dict(revenue_jpy=revenue, electricity_jpy=electricity, operating_jpy=operating,
                                  maintenance_jpy=maintenance, tax_jpy=tax, wc_increase_jpy=increase,
                                  renewal_jpy=renewal, cfads_jpy=ebitda - tax - increase - renewal))
        later_cash[sid] = cash_rows
    sites = [replace(site, unlevered_cash_flows_jpy=tuple(r["cfads_jpy"] for r in later_cash[site.site_id]))
             if site.site_id in later_cash else site for site in sites]
    inputs = PortfolioInputs(sites=tuple(sites), hanyu_cash=tuple(annual), scenario=name,
                             hanyu_expansion_capex_jpy=data["expansion_capex_jpy"], investor_equity_jpy=equity)
    result = run_portfolio_model(inputs)
    return dict(scenario=name, cost_case=s["cost_case"], evidence_result="INSUFFICIENT EVIDENCE",
                planning_only=True, design=design_node(hanyu, data), costs=cost_tables,
                scenario_debt_jpy=debt, scenario_equity_jpy=equity, annual=detail, later_site_cash=later_cash,
                result=result.to_dict())
