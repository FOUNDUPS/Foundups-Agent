"""Canonical YUMORI / eSingularity Phase-1 financial model.

The repository is the source of truth for equations. Spreadsheet/PDF/web
surfaces are projections of this model, not independent calculation authority.

WSP: 3, 50, 84, 97. Public-facing values remain scenario outputs until their
underlying assumptions are independently validated.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Dict, List, Mapping, Sequence, Tuple

HOURS_PER_YEAR = 8_760


@dataclass(frozen=True)
class RevenueTier:
    key: str
    name: str
    gpu_count: int
    price_jpy_per_gpu_hour: float
    status: str = "LEGACY SCENARIO / VALIDATE"
    source: str = "FIN_YUMORI preset workbook"


@dataclass(frozen=True)
class DebtFacility:
    key: str
    name: str
    principal_jpy: float
    annual_rate: float
    term_years: int
    status: str = "LEGACY SCENARIO / FINANCING NOT COMMITTED"
    source: str = "FIN_YUMORI preset workbook"


@dataclass(frozen=True)
class ModelAssumptions:
    model_name: str
    years: Tuple[int, ...]
    utilization: Tuple[float, ...]
    total_gpus: int
    tiers: Tuple[RevenueTier, ...]
    total_site_power_kw: float
    it_power_kw: float
    pue: float
    electricity_tariff_jpy_per_kwh: float
    thermal_revenue_jpy: Tuple[float, ...]
    coolant_maintenance_jpy: Tuple[float, ...]
    network_backhaul_jpy: Tuple[float, ...]
    noc_labor_jpy: Tuple[float, ...]
    management_admin_jpy: Tuple[float, ...]
    academic_liaison_marketing_jpy: Tuple[float, ...]
    insurance_security_jpy: Tuple[float, ...]
    property_lease_jpy: Tuple[float, ...]
    community_benefit_jpy: Tuple[float, ...]
    working_capital_change_jpy: Tuple[float, ...]
    maintenance_capex_jpy: Tuple[float, ...]
    facility_capex_jpy: float
    compute_capex_jpy: float
    grants_jpy: float
    sponsor_equity_jpy: float
    compute_useful_life_years: int
    infrastructure_useful_life_years: int
    corporate_tax_rate: float
    debts: Tuple[DebtFacility, ...]
    discount_rate: float
    visitor_spend_low_jpy: float
    visitor_spend_high_jpy: float
    historical_facility_uses: int
    demolition_preparation_budget_jpy: float
    demolition_estimate_jpy: float
    academic_compute_benefit_jpy: float
    usable_heat_offset_jpy: float
    direct_high_tech_fte_low: int
    direct_high_tech_fte_high: int
    initial_local_contracts_low_jpy: float
    initial_local_contracts_high_jpy: float
    market_h100_dok_jpy_per_gpu_hour: float


@dataclass(frozen=True)
class DebtYear:
    year: int
    beginning_balance_jpy: float
    principal_repayment_jpy: float
    interest_jpy: float
    ending_balance_jpy: float
    total_debt_service_jpy: float


@dataclass(frozen=True)
class YearResult:
    year: int
    utilization: float
    billable_gpu_hours: float
    tier_revenue_jpy: Mapping[str, float]
    compute_revenue_jpy: float
    thermal_revenue_jpy: float
    gross_revenue_jpy: float
    power_cost_jpy: float
    total_cogs_jpy: float
    gross_profit_jpy: float
    total_sga_jpy: float
    ebitda_jpy: float
    compute_depreciation_jpy: float
    infrastructure_depreciation_jpy: float
    total_depreciation_jpy: float
    ebit_jpy: float
    interest_expense_jpy: float
    ebt_jpy: float
    income_tax_jpy: float
    net_income_jpy: float
    working_capital_change_jpy: float
    cash_flow_from_operations_jpy: float
    maintenance_capex_jpy: float
    debt_principal_repayment_jpy: float
    fcfe_jpy: float
    debt_service_jpy: float
    dscr: float | None


@dataclass(frozen=True)
class ModelResult:
    assumptions: ModelAssumptions
    years: Tuple[YearResult, ...]
    debt_schedules: Mapping[str, Tuple[DebtYear, ...]]
    initial_equity_jpy: float
    equity_cash_flows_jpy: Tuple[float, ...]
    equity_irr: float | None
    equity_npv_jpy: float
    five_year_revenue_jpy: float
    five_year_ebitda_jpy: float
    five_year_fcfe_jpy: float
    visitor_spend_30y_low_jpy: float
    visitor_spend_30y_high_jpy: float
    validation: Mapping[str, bool]

    def as_dict(self) -> Dict[str, object]:
        return asdict(self)


def default_assumptions() -> ModelAssumptions:
    """Return the reconciled Phase-1 base case.

    Legacy figures are preserved as assumptions where they are actual scenario
    inputs. Known arithmetic contradictions are not preserved as outputs.
    """
    return ModelAssumptions(
        model_name="YUMORI Phase-1 reconciled base case",
        years=(1, 2, 3, 4, 5),
        utilization=(0.65, 0.85, 0.92, 0.95, 0.95),
        total_gpus=384,
        tiers=(
            RevenueTier("tier_a", "Enterprise dedicated", 192, 420.0),
            RevenueTier("tier_b", "Regional SME / neocloud burst", 115, 380.0),
            RevenueTier("tier_c", "Academic consortium", 77, 220.0),
        ),
        total_site_power_kw=1_000.0,
        it_power_kw=850.0,
        pue=1.115,
        electricity_tariff_jpy_per_kwh=19.50,
        thermal_revenue_jpy=(4e6, 6e6, 6e6, 6e6, 6e6),
        coolant_maintenance_jpy=(8.5e6, 11e6, 12.5e6, 13.5e6, 14e6),
        network_backhaul_jpy=(18e6, 18e6, 18e6, 18e6, 18e6),
        noc_labor_jpy=(32e6, 34e6, 36e6, 38e6, 40e6),
        management_admin_jpy=(18e6, 19e6, 20e6, 21e6, 22e6),
        academic_liaison_marketing_jpy=(8e6, 8.5e6, 9e6, 9.5e6, 10e6),
        insurance_security_jpy=(9e6, 10e6, 11e6, 11.5e6, 12e6),
        property_lease_jpy=(0, 0, 0, 0, 0),
        community_benefit_jpy=(10e6, 11e6, 12e6, 13e6, 12e6),
        working_capital_change_jpy=(11e6, 5e6, 3e6, 7.5e6, 15e6),
        maintenance_capex_jpy=(5e6, 5e6, 6e6, 6e6, 7e6),
        facility_capex_jpy=285e6,
        compute_capex_jpy=1_800e6,
        grants_jpy=160e6,
        sponsor_equity_jpy=390e6,
        compute_useful_life_years=4,
        infrastructure_useful_life_years=10,
        corporate_tax_rate=0.30,
        debts=(
            DebtFacility("compute_debt", "Compute asset-backed debt", 1_440e6, 0.065, 4),
            DebtFacility("green_loan", "Fukui Bank / DBJ green loan", 95e6, 0.018, 10),
        ),
        discount_rate=0.12,
        visitor_spend_low_jpy=129_649_000.0,
        visitor_spend_high_jpy=719_033_354.0,
        historical_facility_uses=129_649,
        demolition_preparation_budget_jpy=12_720_000.0,
        demolition_estimate_jpy=1_580_000_000.0,
        academic_compute_benefit_jpy=94_187_520.0,
        usable_heat_offset_jpy=6_000_000.0,
        direct_high_tech_fte_low=4,
        direct_high_tech_fte_high=6,
        initial_local_contracts_low_jpy=77_000_000.0,
        initial_local_contracts_high_jpy=113_000_000.0,
        market_h100_dok_jpy_per_gpu_hour=373.5,
    )


def _require_horizon(name: str, values: Sequence[float], horizon: int) -> None:
    if len(values) != horizon:
        raise ValueError(f"{name} must contain {horizon} annual values; got {len(values)}")


def annuity_payment(principal_jpy: float, annual_rate: float, term_years: int) -> float:
    if principal_jpy < 0 or annual_rate < 0 or term_years <= 0:
        raise ValueError("Debt principal/rate/term must be non-negative with positive term")
    if principal_jpy == 0:
        return 0.0
    if annual_rate == 0:
        return principal_jpy / term_years
    return principal_jpy * annual_rate / (1.0 - (1.0 + annual_rate) ** (-term_years))


def build_debt_schedule(facility: DebtFacility, horizon: int) -> Tuple[DebtYear, ...]:
    payment = annuity_payment(facility.principal_jpy, facility.annual_rate, facility.term_years)
    balance = facility.principal_jpy
    rows: List[DebtYear] = []
    for year in range(1, horizon + 1):
        beginning = balance
        if beginning <= 1e-6:
            principal = interest = ending = service = 0.0
        else:
            interest = beginning * facility.annual_rate
            principal = min(beginning, max(0.0, payment - interest))
            ending = max(0.0, beginning - principal)
            service = principal + interest
        rows.append(DebtYear(year, beginning, principal, interest, ending, service))
        balance = ending
    return tuple(rows)


def npv(rate: float, cash_flows: Sequence[float]) -> float:
    if rate <= -1.0:
        raise ValueError("NPV rate must be greater than -100%")
    return sum(cf / ((1.0 + rate) ** period) for period, cf in enumerate(cash_flows))


def irr(cash_flows: Sequence[float], *, tolerance: float = 1e-10) -> float | None:
    """Solve periodic IRR with bounded bisection; returns None when no sign change exists."""
    if not cash_flows or not any(cf < 0 for cf in cash_flows) or not any(cf > 0 for cf in cash_flows):
        return None
    low, high = -0.999999, 1.0
    f_low, f_high = npv(low, cash_flows), npv(high, cash_flows)
    while f_low * f_high > 0 and high < 1_000_000:
        high *= 2.0
        f_high = npv(high, cash_flows)
    if f_low * f_high > 0:
        return None
    for _ in range(300):
        mid = (low + high) / 2.0
        f_mid = npv(mid, cash_flows)
        if abs(f_mid) <= tolerance:
            return mid
        if f_low * f_mid <= 0:
            high, f_high = mid, f_mid
        else:
            low, f_low = mid, f_mid
    return (low + high) / 2.0


def calculate_model(assumptions: ModelAssumptions | None = None) -> ModelResult:
    a = assumptions or default_assumptions()
    horizon = len(a.years)
    if horizon == 0:
        raise ValueError("Model horizon cannot be empty")
    if sum(t.gpu_count for t in a.tiers) != a.total_gpus:
        raise ValueError("Tier GPU allocations must sum to total_gpus")
    for name in (
        "utilization", "thermal_revenue_jpy", "coolant_maintenance_jpy",
        "network_backhaul_jpy", "noc_labor_jpy", "management_admin_jpy",
        "academic_liaison_marketing_jpy", "insurance_security_jpy",
        "property_lease_jpy", "community_benefit_jpy",
        "working_capital_change_jpy", "maintenance_capex_jpy",
    ):
        _require_horizon(name, getattr(a, name), horizon)
    if a.it_power_kw * a.pue > a.total_site_power_kw + 1e-9:
        raise ValueError("IT load x PUE exceeds total site power envelope")

    debt_schedules = {d.key: build_debt_schedule(d, horizon) for d in a.debts}
    facility_depreciable_basis = max(0.0, a.facility_capex_jpy - a.grants_jpy)
    infra_dep = facility_depreciable_basis / a.infrastructure_useful_life_years
    compute_dep = a.compute_capex_jpy / a.compute_useful_life_years

    years: List[YearResult] = []
    for idx, year in enumerate(a.years):
        util = a.utilization[idx]
        if not 0 <= util <= 1:
            raise ValueError(f"Utilization must be within 0-1; year {year}={util}")
        tier_revenue = {
            tier.key: tier.gpu_count * HOURS_PER_YEAR * util * tier.price_jpy_per_gpu_hour
            for tier in a.tiers
        }
        compute_revenue = sum(tier_revenue.values())
        thermal_revenue = a.thermal_revenue_jpy[idx]
        gross_revenue = compute_revenue + thermal_revenue
        power_cost = a.it_power_kw * util * a.pue * HOURS_PER_YEAR * a.electricity_tariff_jpy_per_kwh
        total_cogs = (
            power_cost + a.coolant_maintenance_jpy[idx] + a.network_backhaul_jpy[idx]
            + a.noc_labor_jpy[idx]
        )
        gross_profit = gross_revenue - total_cogs
        total_sga = (
            a.management_admin_jpy[idx] + a.academic_liaison_marketing_jpy[idx]
            + a.insurance_security_jpy[idx] + a.property_lease_jpy[idx]
            + a.community_benefit_jpy[idx]
        )
        ebitda = gross_profit - total_sga
        compute_depreciation = compute_dep if year <= a.compute_useful_life_years else 0.0
        infrastructure_depreciation = infra_dep if year <= a.infrastructure_useful_life_years else 0.0
        total_depreciation = compute_depreciation + infrastructure_depreciation
        ebit = ebitda - total_depreciation
        interest = sum(schedule[idx].interest_jpy for schedule in debt_schedules.values())
        principal = sum(schedule[idx].principal_repayment_jpy for schedule in debt_schedules.values())
        debt_service = sum(schedule[idx].total_debt_service_jpy for schedule in debt_schedules.values())
        ebt = ebit - interest
        income_tax = max(0.0, ebt * a.corporate_tax_rate)
        net_income = ebt - income_tax
        wc = a.working_capital_change_jpy[idx]
        cfo = net_income + total_depreciation - wc
        maintenance = a.maintenance_capex_jpy[idx]
        fcfe = cfo - maintenance - principal
        dscr = ebitda / debt_service if debt_service > 0 else None
        years.append(YearResult(
            year=year, utilization=util,
            billable_gpu_hours=a.total_gpus * HOURS_PER_YEAR * util,
            tier_revenue_jpy=tier_revenue,
            compute_revenue_jpy=compute_revenue,
            thermal_revenue_jpy=thermal_revenue,
            gross_revenue_jpy=gross_revenue,
            power_cost_jpy=power_cost,
            total_cogs_jpy=total_cogs,
            gross_profit_jpy=gross_profit,
            total_sga_jpy=total_sga,
            ebitda_jpy=ebitda,
            compute_depreciation_jpy=compute_depreciation,
            infrastructure_depreciation_jpy=infrastructure_depreciation,
            total_depreciation_jpy=total_depreciation,
            ebit_jpy=ebit,
            interest_expense_jpy=interest,
            ebt_jpy=ebt,
            income_tax_jpy=income_tax,
            net_income_jpy=net_income,
            working_capital_change_jpy=wc,
            cash_flow_from_operations_jpy=cfo,
            maintenance_capex_jpy=maintenance,
            debt_principal_repayment_jpy=principal,
            fcfe_jpy=fcfe,
            debt_service_jpy=debt_service,
            dscr=dscr,
        ))

    equity_cash_flows = (-a.sponsor_equity_jpy,) + tuple(y.fcfe_jpy for y in years)
    validation = validate_model(a, years, debt_schedules)
    return ModelResult(
        assumptions=a,
        years=tuple(years),
        debt_schedules={k: tuple(v) for k, v in debt_schedules.items()},
        initial_equity_jpy=a.sponsor_equity_jpy,
        equity_cash_flows_jpy=equity_cash_flows,
        equity_irr=irr(equity_cash_flows),
        equity_npv_jpy=npv(a.discount_rate, equity_cash_flows),
        five_year_revenue_jpy=sum(y.gross_revenue_jpy for y in years),
        five_year_ebitda_jpy=sum(y.ebitda_jpy for y in years),
        five_year_fcfe_jpy=sum(y.fcfe_jpy for y in years),
        visitor_spend_30y_low_jpy=a.visitor_spend_low_jpy * 30,
        visitor_spend_30y_high_jpy=a.visitor_spend_high_jpy * 30,
        validation=validation,
    )


def validate_model(
    a: ModelAssumptions,
    years: Sequence[YearResult],
    debt_schedules: Mapping[str, Sequence[DebtYear]],
) -> Dict[str, bool]:
    source_total = a.grants_jpy + sum(d.principal_jpy for d in a.debts) + a.sponsor_equity_jpy
    use_total = a.facility_capex_jpy + a.compute_capex_jpy
    compute_debt = next((d for d in a.debts if d.key == "compute_debt"), None)
    compute_schedule = debt_schedules.get("compute_debt", ())
    return {
        "capital_sources_equal_uses": abs(source_total - use_total) < 0.5,
        "tier_gpu_sum_matches_total": sum(t.gpu_count for t in a.tiers) == a.total_gpus,
        "power_envelope_respected": a.it_power_kw * a.pue <= a.total_site_power_kw + 1e-9,
        "compute_depreciation_stops_after_life": all(
            (y.compute_depreciation_jpy > 0) == (y.year <= a.compute_useful_life_years) for y in years
        ),
        "compute_debt_amortizes_by_term": (
            compute_debt is None
            or len(compute_schedule) < compute_debt.term_years
            or abs(compute_schedule[compute_debt.term_years - 1].ending_balance_jpy) < 0.5
        ),
        "visitor_spend_not_in_project_revenue": all(
            abs(y.gross_revenue_jpy - (y.compute_revenue_jpy + y.thermal_revenue_jpy)) < 0.5 for y in years
        ),
        "fcfe_reconciles": all(
            abs(y.fcfe_jpy - (y.cash_flow_from_operations_jpy - y.maintenance_capex_jpy - y.debt_principal_repayment_jpy)) < 0.5
            for y in years
        ),
    }


LEGACY_DISPLAYED_EQUITY_IRR = 0.684
LEGACY_SHOWN_FCFE_JPY = (161_810_153.0, 310_038_357.0, 359_762_827.0, 357_472_092.0, 755_264_092.0)
LEGACY_POWER_COST_JPY = (93_267_720.0, 121_965_480.0, 132_010_944.0, 136_314_360.0, 136_314_360.0)
LEGACY_COMPUTE_DEPRECIATION_JPY = (450e6, 450e6, 450e6, 450e6, 450e6)
LEGACY_COMPUTE_DEBT_BEGINNING_JPY = (1_440e6, 1_115e6, 768e6, 398e6, 0.0)
LEGACY_COMPUTE_DEBT_INTEREST_JPY = (84e6, 62e6, 39e6, 14e6, 0.0)


def audit_legacy_model(assumptions: ModelAssumptions | None = None) -> Dict[str, object]:
    """Return deterministic reconciliation findings for the preset workbook."""
    a = assumptions or default_assumptions()
    legacy_cash_flows = (-a.sponsor_equity_jpy,) + LEGACY_SHOWN_FCFE_JPY
    solved_legacy_irr = irr(legacy_cash_flows)
    implied_power_kw = []
    for cost, util in zip(LEGACY_POWER_COST_JPY, a.utilization):
        denom = a.electricity_tariff_jpy_per_kwh * HOURS_PER_YEAR * util
        implied_power_kw.append(cost / denom if denom else 0.0)
    interest_should_be = tuple(bal * 0.065 for bal in LEGACY_COMPUTE_DEBT_BEGINNING_JPY)
    return {
        "displayed_equity_irr": LEGACY_DISPLAYED_EQUITY_IRR,
        "solved_equity_irr_from_shown_fcfe": solved_legacy_irr,
        "irr_gap_percentage_points": (
            (LEGACY_DISPLAYED_EQUITY_IRR - solved_legacy_irr) * 100 if solved_legacy_irr is not None else None
        ),
        "implied_power_kw_by_year": tuple(implied_power_kw),
        "stated_it_power_kw": a.it_power_kw,
        "legacy_compute_depreciation_year5_jpy": LEGACY_COMPUTE_DEPRECIATION_JPY[-1],
        "expected_compute_depreciation_year5_jpy": 0.0,
        "legacy_compute_interest_jpy": LEGACY_COMPUTE_DEBT_INTEREST_JPY,
        "rate_implied_interest_jpy": interest_should_be,
        "findings": (
            "Displayed IRR does not equal IRR solved from displayed sponsor equity and FCFE.",
            "Legacy electricity expense implies approximately 840 kW before PUE, while operating assumptions state 850 kW IT load and PUE 1.11-1.12.",
            "Legacy Year-5 compute depreciation continues after a stated four-year useful life.",
            "Legacy compute-debt interest is below beginning balance x 6.5%; financing schedule is not formula-reconciled.",
            "Legacy tier revenue contains small hard-coded drift from GPU count x 8,760 x utilization x price.",
        ),
    }
