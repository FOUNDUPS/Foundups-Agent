"""Repo-canonical YUMORI financial model.

WSP 97 truth boundary:
- This module calculates modelled outputs from explicit assumptions.
- It does not convert assumptions into commitments or forecasts.
- Regional/public-value references stay separate from project-company revenue.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import math
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple


ASSUMPTIONS_PATH = (
    Path(__file__).resolve().parent
    / "assumptions"
    / "yumori_legacy_reconciled.json"
)


@dataclass(frozen=True)
class DebtYear:
    year: int
    beginning_principal_jpy: float
    principal_repayment_jpy: float
    interest_jpy: float
    ending_principal_jpy: float
    total_debt_service_jpy: float


@dataclass(frozen=True)
class ModelYear:
    year: int
    utilization: float
    tier_a_revenue_jpy: float
    tier_b_revenue_jpy: float
    tier_c_revenue_jpy: float
    compute_revenue_jpy: float
    thermal_revenue_jpy: float
    gross_revenue_jpy: float
    electricity_jpy: float
    cogs_jpy: float
    gross_profit_jpy: float
    sga_jpy: float
    ebitda_jpy: float
    depreciation_jpy: float
    ebit_jpy: float
    interest_jpy: float
    ebt_jpy: float
    tax_jpy: float
    net_income_jpy: float
    operating_cash_flow_jpy: float
    maintenance_capex_jpy: float
    debt_principal_jpy: float
    fcfe_jpy: float
    cumulative_fcfe_jpy: float
    dscr: float


@dataclass(frozen=True)
class ModelResult:
    scenario: str
    status: str
    assumptions: Mapping[str, Any]
    compute_debt: Tuple[DebtYear, ...]
    green_debt: Tuple[DebtYear, ...]
    years: Tuple[ModelYear, ...]
    equity_cash_flows_jpy: Tuple[float, ...]
    equity_irr: float
    equity_npv_jpy: float
    validation_messages: Tuple[str, ...]


def load_assumptions(path: Path | str = ASSUMPTIONS_PATH) -> Dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _annuity_payment(principal: float, annual_rate: float, term_years: int) -> float:
    if principal < 0 or term_years <= 0 or annual_rate < 0:
        raise ValueError("Invalid debt terms")
    if principal == 0:
        return 0.0
    if annual_rate == 0:
        return principal / term_years
    return principal * annual_rate / (1.0 - (1.0 + annual_rate) ** (-term_years))


def debt_schedule(
    principal_jpy: float,
    annual_rate: float,
    term_years: int,
    horizon_years: int,
) -> Tuple[DebtYear, ...]:
    """Standard fully-amortizing annual-payment debt schedule."""
    payment = _annuity_payment(principal_jpy, annual_rate, term_years)
    balance = float(principal_jpy)
    rows: List[DebtYear] = []
    for year in range(1, horizon_years + 1):
        beginning = balance
        if beginning <= 1e-9:
            rows.append(DebtYear(year, 0.0, 0.0, 0.0, 0.0, 0.0))
            continue
        interest = beginning * annual_rate
        total_payment = min(payment, beginning + interest)
        principal_payment = max(0.0, total_payment - interest)
        ending = max(0.0, beginning - principal_payment)
        rows.append(
            DebtYear(
                year=year,
                beginning_principal_jpy=beginning,
                principal_repayment_jpy=principal_payment,
                interest_jpy=interest,
                ending_principal_jpy=ending,
                total_debt_service_jpy=total_payment,
            )
        )
        balance = ending
    return tuple(rows)


def npv(rate: float, cash_flows: Sequence[float]) -> float:
    if rate <= -1.0:
        raise ValueError("rate must be greater than -100%")
    return sum(value / ((1.0 + rate) ** index) for index, value in enumerate(cash_flows))


def irr(cash_flows: Sequence[float], *, lower: float = -0.9999, upper: float = 10.0) -> float:
    """Dependency-free IRR using bracket expansion + bisection."""
    if not cash_flows or not (any(x < 0 for x in cash_flows) and any(x > 0 for x in cash_flows)):
        raise ValueError("IRR requires at least one negative and one positive cash flow")

    def f(rate: float) -> float:
        return npv(rate, cash_flows)

    lo, hi = lower, upper
    flo, fhi = f(lo), f(hi)
    attempts = 0
    while flo * fhi > 0 and attempts < 12:
        hi *= 2.0
        fhi = f(hi)
        attempts += 1
    if flo * fhi > 0:
        raise ValueError("Unable to bracket IRR")

    for _ in range(250):
        mid = (lo + hi) / 2.0
        fmid = f(mid)
        if abs(fmid) < 0.01:
            return mid
        if flo * fmid <= 0:
            hi, fhi = mid, fmid
        else:
            lo, flo = mid, fmid
    return (lo + hi) / 2.0


def _straight_line_depreciation(
    basis_jpy: float,
    useful_life_years: int,
    horizon_years: int,
) -> Tuple[float, ...]:
    if useful_life_years <= 0:
        raise ValueError("useful life must be positive")
    annual = basis_jpy / useful_life_years
    return tuple(annual if year <= useful_life_years else 0.0 for year in range(1, horizon_years + 1))


def _vector(mapping: Mapping[str, Any], key: str, horizon: int) -> Tuple[float, ...]:
    values = tuple(float(x) for x in mapping[key])
    if len(values) != horizon:
        raise ValueError(f"{key} expected {horizon} values, got {len(values)}")
    return values


def build_model(assumptions: Mapping[str, Any] | None = None) -> ModelResult:
    a: Mapping[str, Any] = assumptions or load_assumptions()
    years = tuple(int(x) for x in a["years"])
    horizon = len(years)
    util = _vector(a, "utilization", horizon)
    hours = float(a["hours_per_year"])

    gpu = a["gpus"]
    price = a["gpu_hour_price_jpy"]
    gpu_total = int(gpu["total"])
    tier_counts = (int(gpu["tier_a"]), int(gpu["tier_b"]), int(gpu["tier_c"]))
    if sum(tier_counts) != gpu_total:
        raise ValueError("GPU tier counts must sum to total GPUs")

    thermal = _vector(a, "thermal_revenue_jpy", horizon)
    cogs_a = a["cogs_jpy"]
    coolant = _vector(cogs_a, "coolant_pumps_filters", horizon)
    network = _vector(cogs_a, "network_backhaul", horizon)
    noc_labor = _vector(cogs_a, "noc_hpc_labor", horizon)

    sga_a = a["sga_jpy"]
    management = _vector(sga_a, "management_admin", horizon)
    academic_marketing = _vector(sga_a, "academic_marketing", horizon)
    insurance = _vector(sga_a, "insurance_security", horizon)
    property_lease = _vector(sga_a, "property_lease", horizon)
    community = _vector(sga_a, "community_benefit", horizon)

    wc_change = _vector(a, "working_capital_change_jpy", horizon)
    maintenance_capex = _vector(a, "maintenance_capex_jpy", horizon)

    power = a["power"]
    cost_power_kw = float(power["legacy_cost_model_full_load_kw"])
    tariff = float(power["tariff_jpy_per_kwh"])

    depreciation_a = a["depreciation"]
    capital = a["capital_jpy"]
    hardware_dep = _straight_line_depreciation(
        float(capital["compute_hardware_capex"]),
        int(depreciation_a["compute_hardware_life_years"]),
        horizon,
    )
    infra_dep = _straight_line_depreciation(
        float(depreciation_a["infrastructure_basis_net_of_grants_jpy"]),
        int(depreciation_a["infrastructure_life_years"]),
        horizon,
    )

    debt_a = a["debt"]
    compute_debt = debt_schedule(
        float(debt_a["compute"]["principal_jpy"]),
        float(debt_a["compute"]["annual_rate"]),
        int(debt_a["compute"]["term_years"]),
        horizon,
    )
    green_debt = debt_schedule(
        float(debt_a["green"]["principal_jpy"]),
        float(debt_a["green"]["annual_rate"]),
        int(debt_a["green"]["term_years"]),
        horizon,
    )

    tax_rate = float(a["tax_rate"])
    cumulative_fcfe = 0.0
    rows: List[ModelYear] = []

    for idx, year in enumerate(years):
        u = util[idx]
        tier_a = tier_counts[0] * hours * u * float(price["tier_a"])
        tier_b = tier_counts[1] * hours * u * float(price["tier_b"])
        tier_c = tier_counts[2] * hours * u * float(price["tier_c"])
        compute_revenue = tier_a + tier_b + tier_c
        gross_revenue = compute_revenue + thermal[idx]

        # Legacy reconciliation: prior electricity row = 840 kW × 8,760 × utilization × tariff.
        # 840 kW is explicitly labelled legacy/inferred in the assumptions file.
        electricity = cost_power_kw * hours * u * tariff
        cogs = electricity + coolant[idx] + network[idx] + noc_labor[idx]
        gross_profit = gross_revenue - cogs
        sga = (
            management[idx]
            + academic_marketing[idx]
            + insurance[idx]
            + property_lease[idx]
            + community[idx]
        )
        ebitda = gross_profit - sga
        depreciation = hardware_dep[idx] + infra_dep[idx]
        ebit = ebitda - depreciation
        interest = compute_debt[idx].interest_jpy + green_debt[idx].interest_jpy
        ebt = ebit - interest
        tax = max(0.0, ebt * tax_rate)
        net_income = ebt - tax
        operating_cash_flow = net_income + depreciation - wc_change[idx]
        debt_principal = (
            compute_debt[idx].principal_repayment_jpy
            + green_debt[idx].principal_repayment_jpy
        )
        fcfe = operating_cash_flow - maintenance_capex[idx] - debt_principal
        cumulative_fcfe += fcfe
        debt_service = (
            compute_debt[idx].total_debt_service_jpy
            + green_debt[idx].total_debt_service_jpy
        )
        dscr = ebitda / debt_service if debt_service else math.inf

        rows.append(
            ModelYear(
                year=year,
                utilization=u,
                tier_a_revenue_jpy=tier_a,
                tier_b_revenue_jpy=tier_b,
                tier_c_revenue_jpy=tier_c,
                compute_revenue_jpy=compute_revenue,
                thermal_revenue_jpy=thermal[idx],
                gross_revenue_jpy=gross_revenue,
                electricity_jpy=electricity,
                cogs_jpy=cogs,
                gross_profit_jpy=gross_profit,
                sga_jpy=sga,
                ebitda_jpy=ebitda,
                depreciation_jpy=depreciation,
                ebit_jpy=ebit,
                interest_jpy=interest,
                ebt_jpy=ebt,
                tax_jpy=tax,
                net_income_jpy=net_income,
                operating_cash_flow_jpy=operating_cash_flow,
                maintenance_capex_jpy=maintenance_capex[idx],
                debt_principal_jpy=debt_principal,
                fcfe_jpy=fcfe,
                cumulative_fcfe_jpy=cumulative_fcfe,
                dscr=dscr,
            )
        )

    equity = float(capital["sponsor_equity"])
    equity_cash_flows = (-equity,) + tuple(row.fcfe_jpy for row in rows)
    equity_irr = irr(equity_cash_flows)
    discount_rate = float(a["equity_discount_rate"])
    equity_npv = npv(discount_rate, equity_cash_flows)
    result = ModelResult(
        scenario=str(a["scenario"]),
        status=str(a["status"]),
        assumptions=a,
        compute_debt=compute_debt,
        green_debt=green_debt,
        years=tuple(rows),
        equity_cash_flows_jpy=equity_cash_flows,
        equity_irr=equity_irr,
        equity_npv_jpy=equity_npv,
        validation_messages=(),
    )
    messages = validate_model(result)
    return ModelResult(**{**result.__dict__, "validation_messages": tuple(messages)})


def validate_model(result: ModelResult, tolerance_jpy: float = 1.0) -> List[str]:
    a = result.assumptions
    messages: List[str] = []
    capital = a["capital_jpy"]
    grants = sum(float(v) for v in capital["grants"].values())
    sources = (
        grants
        + float(capital["sponsor_equity"])
        + float(capital["compute_debt"])
        + float(capital["green_loan"])
    )
    uses = float(capital["facility_infrastructure_capex"]) + float(capital["compute_hardware_capex"])
    if abs(sources - uses) > tolerance_jpy:
        raise AssertionError(f"Sources != uses: {sources} vs {uses}")
    messages.append("sources_equal_uses")

    for row in result.years:
        tier_sum = row.tier_a_revenue_jpy + row.tier_b_revenue_jpy + row.tier_c_revenue_jpy
        if abs(tier_sum - row.compute_revenue_jpy) > tolerance_jpy:
            raise AssertionError(f"Year {row.year}: compute revenue does not reconcile")
        if abs(row.compute_revenue_jpy + row.thermal_revenue_jpy - row.gross_revenue_jpy) > tolerance_jpy:
            raise AssertionError(f"Year {row.year}: gross revenue does not reconcile")
        if abs(row.gross_revenue_jpy - row.cogs_jpy - row.sga_jpy - row.ebitda_jpy) > tolerance_jpy:
            raise AssertionError(f"Year {row.year}: EBITDA does not reconcile")
        if abs(row.ebt_jpy - row.tax_jpy - row.net_income_jpy) > tolerance_jpy:
            raise AssertionError(f"Year {row.year}: net income does not reconcile")
    messages.append("annual_statements_reconcile")

    compute_end = result.compute_debt[-1].ending_principal_jpy
    if compute_end > tolerance_jpy:
        raise AssertionError("4-year compute debt is not fully amortized")
    messages.append("compute_debt_fully_amortized")

    hardware_life = int(a["depreciation"]["compute_hardware_life_years"])
    if len(result.years) > hardware_life:
        year_after_life = result.years[hardware_life]
        infra_annual = float(a["depreciation"]["infrastructure_basis_net_of_grants_jpy"]) / float(
            a["depreciation"]["infrastructure_life_years"]
        )
        if abs(year_after_life.depreciation_jpy - infra_annual) > tolerance_jpy:
            raise AssertionError("Hardware depreciation continues beyond stated useful life")
    messages.append("depreciation_respects_useful_life")

    if not math.isfinite(result.equity_irr):
        raise AssertionError("Equity IRR is not finite")
    messages.append("irr_calculated_from_cash_flows")
    return messages


def result_as_dict(result: ModelResult) -> Dict[str, Any]:
    """Stable JSON-ready projection for exporters/tests/RedDog."""
    return {
        "scenario": result.scenario,
        "status": result.status,
        "equity_irr": result.equity_irr,
        "equity_npv_jpy": result.equity_npv_jpy,
        "equity_cash_flows_jpy": list(result.equity_cash_flows_jpy),
        "years": [row.__dict__ for row in result.years],
        "compute_debt": [row.__dict__ for row in result.compute_debt],
        "green_debt": [row.__dict__ for row in result.green_debt],
        "validation_messages": list(result.validation_messages),
        "regional_reference": result.assumptions["regional_reference"],
        "city_fiscal_reference": result.assumptions["city_fiscal_reference"],
    }


if __name__ == "__main__":
    print(json.dumps(result_as_dict(build_model()), indent=2, ensure_ascii=False))
