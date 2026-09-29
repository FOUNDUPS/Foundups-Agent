"""Canonical YUMORI/eSingularity economic and demand-led node sizing model.

Repository truth:
- the workbook is a projection / sensitivity surface;
- site capacity is not selected by arbitrary MW labels;
- customer/service demand, unit economics, financing burden, and verified utility
  capacity determine feasible node size;
- no utility-confirmed capacity is claimed for Sukatto, Shimousaka, or Hanyu.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from math import inf
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

# Portfolio allocation is bounded separately; legacy parity and sizing stay intact.
from modules.foundups.esingularity.src.yumori_portfolio_model import (
    AnnualCashInputs, GrantAllocation, PortfolioInputs, PortfolioResult,
    SiteCost, SiteFinancialInputs, default_portfolio_sites, run_portfolio_model,
)

MODEL_YEARS = 5
HOURS_PER_YEAR = 8_760.0
METHODOLOGY_URL = "https://ai-circular-economy.com/"
PAPER_STATUS_WEIGHTS: Mapping[str, float] = {
    "completed": 0.0,
    "operating": 0.0,
    "signed": 0.5,
    "loi": 1.0,
    "paused": 1.0,
}


@dataclass(frozen=True)
class ServiceOffer:
    service_id: str
    name: str
    primary_buyer: str
    resource_family: str
    billing_unit: str
    consumes_gpu_pool: bool
    base_price_jpy_per_unit: float = 0.0
    pricing_status: str = "TBD"
    gpu_hours_per_unit: float = 0.0
    source_url: str = ""
    contract_form: str = ""
    note: str = ""


DEFAULT_SERVICE_CATALOG: tuple[ServiceOffer, ...] = (
    ServiceOffer("S01", "Burst / on-demand GPU compute", "SME / startup / research", "GPU", "JPY / GPUh", True, 380.0, "VERIFY", 1.0, "https://ai.sakura.ad.jp/gpu/koukaryoku-dok/", "Usage / monthly reservation", "Inherited scenario; validate like-for-like."),
    ServiceOffer("S02", "Enterprise reserved GPU capacity", "Large enterprise / anchor", "GPU", "JPY / GPUh", True, 420.0, "VERIFY", 1.0, "https://ai.sakura.ad.jp/gpu/koukaryoku-dok/", "6–60 month minimum-use / take-or-pay", "Internal target until customer evidence."),
    ServiceOffer("S03", "Academic research GPU capacity", "University / research institution", "GPU", "JPY / GPUh", True, 220.0, "VERIFY / SUBSIDIZED", 1.0, "https://ai.sakura.ad.jp/gpu/koukaryoku-dok/", "Annual / multi-year minimum purchase", "Discount must be funded by project economics, sponsor, or public support."),
    ServiceOffer("S04", "Private / sovereign 8-GPU node", "Enterprise / finance / public sector", "GPU", "JPY / 8GPU-month", True, 2_452_800.0, "VERIFY", 8.0 * 730.0, "https://ai.sakura.ad.jp/gpu/koukaryoku-dok/", "Dedicated node / cluster reservation", "Legacy scenario; dedicated tenancy / locality / private networking."),
    ServiceOffer("S05", "Dedicated multi-node cluster reservation", "Enterprise / research consortium", "GPU", "JPY / cluster-month", True, contract_form="Reserved cluster / minimum-use", note="Configure node count and GPU-hours before pricing."),
    ServiceOffer("S06", "Batch inference compute", "Enterprise / SME / research", "GPU", "JPY / GPUh", True, gpu_hours_per_unit=1.0, contract_form="Usage / reservation"),
    ServiceOffer("S07", "Real-time inference endpoint", "Enterprise / public sector / startup", "GPU", "GPUh + request/token fee", True, gpu_hours_per_unit=1.0, contract_form="Reserved serving + SLA"),
    ServiceOffer("S08", "Managed open-source model hosting", "Enterprise / university / startup", "GPU", "GPUh + managed fee", True, gpu_hours_per_unit=1.0, contract_form="Reserved serving + SLA"),
    ServiceOffer("S09", "Managed training / fine-tuning jobs", "Enterprise / university", "GPU", "GPUh + engineering fee", True, gpu_hours_per_unit=1.0, contract_form="Project SOW + reserved capacity"),
    ServiceOffer("S10", "Model evaluation / benchmarking", "Enterprise / university / developer", "GPU", "GPUh + project fee", True, gpu_hours_per_unit=1.0, contract_form="Project SOW"),
    ServiceOffer("S11", "Managed AI-agent runtime", "Enterprise / municipality / startup", "GPU", "GPUh + managed fee", True, gpu_hours_per_unit=1.0, contract_form="Monthly / reserved"),
    ServiceOffer("S12", "CPU / HPC compute", "Engineering / research / enterprise", "CPU", "JPY / CPUh", False, contract_form="Usage / reservation"),
    ServiceOffer("S13", "Private Kubernetes / AI platform", "Enterprise / consortium", "Managed platform", "JPY / month", False, contract_form="Monthly / annual"),
    ServiceOffer("S14", "Secure storage / data vault", "All compute customers", "Storage", "JPY / TB-month", False, contract_form="Monthly / annual"),
    ServiceOffer("S15", "Backup / archive / checkpoint retention", "All compute customers", "Storage", "JPY / TB-month", False, contract_form="Monthly / annual"),
    ServiceOffer("S16", "Dataset staging / preprocessing", "Enterprise / university / startup", "Data service", "JPY / TB or project", False, contract_form="Project / usage"),
    ServiceOffer("S17", "Private network / dedicated circuit", "Enterprise / university / public sector", "Network", "JPY / circuit-month", False, contract_form="Monthly / annual"),
    ServiceOffer("S18", "High-speed data transfer / egress", "All compute customers", "Network", "JPY / TB", False, contract_form="Usage"),
    ServiceOffer("S19", "Colocation / private rack or cage", "Enterprise / infrastructure partner", "Facility", "JPY / rack-kW-month", False, contract_form="Monthly / annual"),
    ServiceOffer("S20", "Disaster recovery / warm standby", "Enterprise / public sector", "Resilience", "JPY / month", False, contract_form="Annual / multi-year"),
    ServiceOffer("S21", "MLOps / monitoring / managed operations", "Enterprise / university / startup", "Managed service", "JPY / month or SOW", False, contract_form="Monthly / project"),
    ServiceOffer("S22", "Physical-AI / robotics simulation compute", "Manufacturing / robotics / university", "GPU", "JPY / GPUh + project fee", True, gpu_hours_per_unit=1.0, contract_form="Project / reservation"),
    ServiceOffer("S23", "Sponsored education / community compute block", "Municipality / sponsor / university", "GPU", "JPY / GPUh or block", True, gpu_hours_per_unit=1.0, contract_form="Annual sponsored block", note="End user may pay zero; sponsor/public buyer funds capacity."),
    ServiceOffer("S24", "Thermal offtake / heat reuse", "Onsen / greenhouse / local facility", "Heat", "JPY / MWh-th or savings share", False, pricing_status="ENGINEERING FS", source_url="https://www.metro.tokyo.lg.jp/information/press/2026/07/2026071607", contract_form="Heat purchase / savings share", note="Value only useful delivered heat; never double-count heat sale and avoided fuel."),
)


@dataclass(frozen=True)
class DemandLine:
    customer: str
    service_id: str
    annual_units: float
    price_override_jpy_per_unit: float | None = None
    prepay_fraction: float = 0.0
    contract_term_years: float = 1.0
    commitment_status: str = "INTERVIEW"

    def validate(self) -> None:
        if self.annual_units < 0:
            raise ValueError("annual units cannot be negative")
        if self.price_override_jpy_per_unit is not None and self.price_override_jpy_per_unit < 0:
            raise ValueError("price override cannot be negative")
        if not 0.0 <= self.prepay_fraction <= 1.0:
            raise ValueError("prepay fraction must be between zero and one")
        if self.contract_term_years <= 0:
            raise ValueError("contract term must be positive")


@dataclass(frozen=True)
class DemandSizingInputs:
    demand_lines: tuple[DemandLine, ...] = ()
    service_catalog: tuple[ServiceOffer, ...] = DEFAULT_SERVICE_CATALOG
    target_utilization: float = 0.65
    hours_per_year: float = HOURS_PER_YEAR
    # Legacy workbook proxy only: 850 kW IT / 384 GPUs.
    it_kw_per_gpu: float = 850.0 / 384.0
    pue: float = 1.12
    electricity_tariff_jpy_per_kwh: float = 19.5
    grid_confirmed_facility_kw: float | None = None
    fixed_non_electric_cash_opex_jpy: float = 103_500_000.0
    annual_debt_service_jpy: float = 464_810_000.0
    target_dscr: float = 1.25
    fallback_revenue_jpy_per_gpu_hour: float = 368.0

    def validate(self) -> None:
        if not 0 < self.target_utilization <= 1:
            raise ValueError("target utilization must be in (0, 1]")
        if self.hours_per_year <= 0 or self.it_kw_per_gpu <= 0 or self.pue < 1:
            raise ValueError("hours, kW/GPU, and PUE must be positive")
        if self.electricity_tariff_jpy_per_kwh < 0:
            raise ValueError("electricity tariff cannot be negative")
        if self.grid_confirmed_facility_kw is not None and self.grid_confirmed_facility_kw < 0:
            raise ValueError("grid capacity cannot be negative")
        if self.fixed_non_electric_cash_opex_jpy < 0 or self.annual_debt_service_jpy < 0:
            raise ValueError("cash Opex and debt service cannot be negative")
        if self.target_dscr < 0 or self.fallback_revenue_jpy_per_gpu_hour < 0:
            raise ValueError("DSCR and fallback revenue cannot be negative")
        ids = [offer.service_id for offer in self.service_catalog]
        if len(ids) != len(set(ids)):
            raise ValueError("service IDs must be unique")
        for line in self.demand_lines:
            line.validate()


@dataclass(frozen=True)
class DemandSizingResult:
    annual_contract_revenue_jpy: float
    annual_gpu_hours: float
    demand_backed_average_gpus: float
    demand_backed_it_kw: float
    demand_backed_facility_kw: float
    upfront_cash_jpy: float
    nominal_multiyear_contract_value_jpy: float
    blended_revenue_jpy_per_gpu_hour: float
    energy_cost_jpy_per_gpu_hour: float
    contribution_jpy_per_gpu_hour: float
    required_annual_contribution_jpy: float
    financial_floor_gpu_hours: float
    financial_floor_average_gpus: float
    financial_floor_it_kw: float
    financial_floor_facility_kw: float
    required_gross_revenue_floor_jpy: float
    demand_revenue_coverage: float
    grid_fit: str
    commercial_readiness: str
    active_unpriced_service_ids: tuple[str, ...]
    truth_boundary: Mapping[str, str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def calculate_demand_led_node_sizing(inputs: DemandSizingInputs | None = None) -> DemandSizingResult:
    """Translate entered customer/service demand into capacity and viability checks.

    Demand-backed capacity is the only capacity supported by current order inputs.
    Financial-floor capacity is an equivalent sold-capacity requirement under
    the current pricing/Opex/debt scenario. It is a warning metric, not a build target.
    Utility-confirmed capacity is a hard external constraint and stays UNVERIFIED
    until an actual operator response exists.
    """

    model = inputs or DemandSizingInputs()
    model.validate()
    catalog = {offer.service_id: offer for offer in model.service_catalog}

    revenue = 0.0
    gpu_hours = 0.0
    upfront = 0.0
    nominal_contract_value = 0.0
    unpriced: set[str] = set()

    for line in model.demand_lines:
        if line.annual_units == 0:
            continue
        if line.service_id not in catalog:
            raise ValueError(f"unknown service ID: {line.service_id}")
        offer = catalog[line.service_id]
        price = (
            line.price_override_jpy_per_unit
            if line.price_override_jpy_per_unit is not None
            else offer.base_price_jpy_per_unit
        )
        if price <= 0:
            unpriced.add(line.service_id)
        line_revenue = line.annual_units * price
        line_gpu_hours = line.annual_units * offer.gpu_hours_per_unit
        revenue += line_revenue
        gpu_hours += line_gpu_hours
        upfront += line_revenue * line.prepay_fraction
        nominal_contract_value += line_revenue * line.contract_term_years

    demand_gpus = gpu_hours / (model.hours_per_year * model.target_utilization)
    demand_it_kw = demand_gpus * model.it_kw_per_gpu
    demand_facility_kw = demand_it_kw * model.pue

    blended_revenue = (
        revenue / gpu_hours
        if gpu_hours > 0 and revenue > 0
        else model.fallback_revenue_jpy_per_gpu_hour
    )
    energy_cost = model.it_kw_per_gpu * model.pue * model.electricity_tariff_jpy_per_kwh
    contribution = blended_revenue - energy_cost
    required_contribution = (
        model.fixed_non_electric_cash_opex_jpy
        + model.target_dscr * model.annual_debt_service_jpy
    )
    floor_gpu_hours = required_contribution / contribution if contribution > 0 else inf
    floor_gpus = floor_gpu_hours / (model.hours_per_year * model.target_utilization) if floor_gpu_hours != inf else inf
    floor_it_kw = floor_gpus * model.it_kw_per_gpu if floor_gpus != inf else inf
    floor_facility_kw = floor_it_kw * model.pue if floor_it_kw != inf else inf
    revenue_floor = floor_gpu_hours * blended_revenue if floor_gpu_hours != inf else inf
    coverage = revenue / revenue_floor if revenue_floor not in (0, inf) else 0.0

    if model.grid_confirmed_facility_kw is None:
        grid_fit = "UNVERIFIED"
    elif demand_facility_kw <= model.grid_confirmed_facility_kw:
        grid_fit = "PASS"
    else:
        grid_fit = "FAIL"

    if unpriced:
        readiness = "PRICE ACTIVE DEMAND"
    elif revenue <= 0:
        readiness = "NO CONTRACTED DEMAND"
    elif coverage < 1:
        readiness = "BUILD MORE DEMAND"
    elif grid_fit == "FAIL":
        readiness = "GRID FAIL"
    elif grid_fit == "UNVERIFIED":
        readiness = "VERIFY GRID"
    else:
        readiness = "READY FOR ENGINEERING"

    return DemandSizingResult(
        annual_contract_revenue_jpy=revenue,
        annual_gpu_hours=gpu_hours,
        demand_backed_average_gpus=demand_gpus,
        demand_backed_it_kw=demand_it_kw,
        demand_backed_facility_kw=demand_facility_kw,
        upfront_cash_jpy=upfront,
        nominal_multiyear_contract_value_jpy=nominal_contract_value,
        blended_revenue_jpy_per_gpu_hour=blended_revenue,
        energy_cost_jpy_per_gpu_hour=energy_cost,
        contribution_jpy_per_gpu_hour=contribution,
        required_annual_contribution_jpy=required_contribution,
        financial_floor_gpu_hours=floor_gpu_hours,
        financial_floor_average_gpus=floor_gpus,
        financial_floor_it_kw=floor_it_kw,
        financial_floor_facility_kw=floor_facility_kw,
        required_gross_revenue_floor_jpy=revenue_floor,
        demand_revenue_coverage=coverage,
        grid_fit=grid_fit,
        commercial_readiness=readiness,
        active_unpriced_service_ids=tuple(sorted(unpriced)),
        truth_boundary={
            "capacity": "No school or Sukatto kW/MW capacity is confirmed until a utility response exists.",
            "demand": "Interviews and LOIs are evidence stages; only binding orders/live usage support bankable demand.",
            "financial_floor": "Equivalent sold capacity under scenario pricing/Opex/debt; never a speculative build target.",
            "pricing": "Unverified service prices remain VERIFY/TBD and must be replaced with customer/market evidence.",
        },
    )


@dataclass(frozen=True)
class RevenueTier:
    name: str
    share: float
    price_jpy_per_gpu_hour: float
    status: str = "VERIFY"


@dataclass(frozen=True)
class CapitalItem:
    name: str
    amount_jpy: float
    status: str = "MODEL ONLY"


@dataclass(frozen=True)
class DebtTerms:
    principal_jpy: float
    annual_interest_rate: float
    term_years: int
    status: str = "MODEL ONLY"


@dataclass(frozen=True)
class YumoriEconomicInputs:
    """Legacy five-year workbook-parity scenario.

    This exists for audit continuity. It is not the node sizing authority.
    Use calculate_demand_led_node_sizing() to derive current site capacity.
    """

    gpu_count: int = 384
    it_load_capacity_kw: float = 850.0
    pue: float = 1.12
    hours_per_year: float = HOURS_PER_YEAR
    idle_it_load_fraction: float = 0.0
    electricity_tariff_jpy_per_kwh: float = 19.5
    electricity_escalation: float = 0.02
    utilization: tuple[float, ...] = (0.65, 0.85, 0.92, 0.95, 0.95)
    revenue_tiers: tuple[RevenueTier, ...] = (
        RevenueTier("enterprise", 0.50, 420.0),
        RevenueTier("regional_sme", 0.30, 380.0),
        RevenueTier("academic", 0.20, 220.0),
    )
    gpu_price_escalation: float = 0.0
    heat_value_jpy: tuple[float, ...] = (4_000_000.0, 6_000_000.0, 6_000_000.0, 6_000_000.0, 6_000_000.0)
    coolant_maintenance_y1_jpy: float = 8_500_000.0
    coolant_escalation: float = 0.05
    fiber_network_y1_jpy: float = 18_000_000.0
    fiber_escalation: float = 0.0
    direct_labor_y1_jpy: float = 32_000_000.0
    direct_labor_escalation: float = 0.05
    management_y1_jpy: float = 18_000_000.0
    management_escalation: float = 0.05
    liaison_y1_jpy: float = 8_000_000.0
    liaison_escalation: float = 0.05
    insurance_y1_jpy: float = 9_000_000.0
    insurance_escalation: float = 0.05
    community_benefit_y1_jpy: float = 10_000_000.0
    community_benefit_escalation: float = 0.05
    maintenance_capex_share_of_revenue: float = 0.006
    working_capital_share_of_revenue: float = 0.015
    effective_tax_rate: float = 0.30
    infrastructure_items: tuple[CapitalItem, ...] = (
        CapitalItem("site_preparation_civil", 22_000_000.0),
        CapitalItem("substation_switchgear", 65_000_000.0),
        CapitalItem("modular_container_chassis", 32_000_000.0),
        CapitalItem("immersion_cooling_heat_exchangers", 48_000_000.0),
        CapitalItem("bess", 85_000_000.0),
        CapitalItem("thermal_piping_headers", 18_000_000.0),
        CapitalItem("legal_permitting_engineering_contingency", 15_000_000.0),
    )
    compute_hardware_capex_jpy: float = 1_800_000_000.0
    committed_awarded_grants_jpy: float = 0.0
    potential_grants_scenario_jpy: float = 0.0
    compute_debt: DebtTerms = DebtTerms(1_440_000_000.0, 0.065, 4)
    infrastructure_debt: DebtTerms = DebtTerms(95_000_000.0, 0.018, 10)
    compute_useful_life_years: int = 4
    infrastructure_useful_life_years: int = 10
    equity_discount_rate: float = 0.12

    def validate(self) -> None:
        if self.gpu_count <= 0 or self.it_load_capacity_kw <= 0:
            raise ValueError("GPU count and IT load must be positive")
        if self.pue < 1.0:
            raise ValueError("PUE cannot be below 1.0")
        if len(self.utilization) != MODEL_YEARS or len(self.heat_value_jpy) != MODEL_YEARS:
            raise ValueError("utilization and heat values must contain five years")
        if any(not 0 <= value <= 1 for value in self.utilization):
            raise ValueError("utilization must stay between zero and one")
        if abs(sum(tier.share for tier in self.revenue_tiers) - 1.0) > 1e-9:
            raise ValueError("revenue tier shares must sum to 1.0")


@dataclass(frozen=True)
class ModelYear:
    year: int
    utilization: float
    billable_gpu_hours: float
    compute_revenue_jpy: float
    heat_value_jpy: float
    gross_revenue_jpy: float
    electricity_consumption_kwh: float
    electricity_cost_jpy: float
    cogs_jpy: float
    gross_profit_jpy: float
    sga_jpy: float
    ebitda_jpy: float
    compute_depreciation_jpy: float
    infrastructure_depreciation_jpy: float
    ebit_jpy: float
    interest_jpy: float
    earnings_before_tax_jpy: float
    cash_taxes_jpy: float
    net_income_jpy: float
    debt_principal_jpy: float
    debt_service_jpy: float
    dscr: float
    working_capital_jpy: float
    change_in_working_capital_jpy: float
    maintenance_capex_jpy: float
    fcfe_jpy: float


@dataclass(frozen=True)
class YumoriEconomicResult:
    total_infrastructure_capex_jpy: float
    total_project_capex_jpy: float
    equity_required_jpy: float
    potential_grants_excluded_jpy: float
    years: tuple[ModelYear, ...]
    cumulative_fcfe_jpy: float
    equity_irr: float | None
    equity_npv_jpy: float
    equity_multiple_5y: float | None
    payback_years: float | None
    minimum_dscr: float
    checks: Mapping[str, bool]
    truth_boundary: Mapping[str, str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _debt_schedule(terms: DebtTerms, years: int = MODEL_YEARS):
    annual_principal = terms.principal_jpy / terms.term_years
    opening = terms.principal_jpy
    out = []
    for _ in range(years):
        principal = min(opening, annual_principal)
        interest = opening * terms.annual_interest_rate
        ending = max(0.0, opening - principal)
        out.append((opening, principal, interest, ending))
        opening = ending
    return tuple(out)


def _npv(rate: float, cash_flows: Sequence[float]) -> float:
    return sum(cash / ((1 + rate) ** period) for period, cash in enumerate(cash_flows))


def calculate_irr(cash_flows: Sequence[float]) -> float | None:
    if len(cash_flows) < 2 or not (any(v < 0 for v in cash_flows) and any(v > 0 for v in cash_flows)):
        return None
    low, high = -0.999999, 10.0
    lv, hv = _npv(low, cash_flows), _npv(high, cash_flows)
    if lv * hv > 0:
        return None
    for _ in range(200):
        mid = (low + high) / 2
        mv = _npv(mid, cash_flows)
        if abs(mv) < 1e-7:
            return mid
        if lv * mv > 0:
            low, lv = mid, mv
        else:
            high = mid
    return (low + high) / 2


def _payback_years(initial_equity: float, annual_fcfe: Sequence[float]) -> float | None:
    running = -initial_equity
    for year, cash in enumerate(annual_fcfe, start=1):
        prior = running
        running += cash
        if running >= 0 and cash > 0:
            return (year - 1) + (-prior / cash)
    return None


def run_yumori_economic_model(inputs: YumoriEconomicInputs | None = None) -> YumoriEconomicResult:
    """Reproduce the current functional workbook's legacy five-year base scenario."""

    model = inputs or YumoriEconomicInputs()
    model.validate()
    infrastructure_capex = sum(x.amount_jpy for x in model.infrastructure_items)
    total_capex = infrastructure_capex + model.compute_hardware_capex_jpy
    equity_required = max(
        0.0,
        total_capex
        - model.committed_awarded_grants_jpy
        - model.compute_debt.principal_jpy
        - model.infrastructure_debt.principal_jpy,
    )
    compute_debt = _debt_schedule(model.compute_debt)
    infra_debt = _debt_schedule(model.infrastructure_debt)
    infra_dep = max(infrastructure_capex - model.committed_awarded_grants_jpy, 0.0) / model.infrastructure_useful_life_years

    years = []
    prior_wc = 0.0
    for idx in range(MODEL_YEARS):
        year = idx + 1
        util = model.utilization[idx]
        gpu_hours = model.gpu_count * model.hours_per_year * util
        compute_rev = sum(
            model.gpu_count * tier.share * model.hours_per_year * util
            * tier.price_jpy_per_gpu_hour * ((1 + model.gpu_price_escalation) ** idx)
            for tier in model.revenue_tiers
        )
        gross_rev = compute_rev + model.heat_value_jpy[idx]
        effective_load = model.idle_it_load_fraction + (1 - model.idle_it_load_fraction) * util
        kwh = model.it_load_capacity_kw * model.pue * model.hours_per_year * effective_load
        tariff = model.electricity_tariff_jpy_per_kwh * ((1 + model.electricity_escalation) ** idx)
        electricity = kwh * tariff
        cogs = (
            electricity
            + model.coolant_maintenance_y1_jpy * ((1 + model.coolant_escalation) ** idx)
            + model.fiber_network_y1_jpy * ((1 + model.fiber_escalation) ** idx)
            + model.direct_labor_y1_jpy * ((1 + model.direct_labor_escalation) ** idx)
        )
        gross_profit = gross_rev - cogs
        sga = (
            model.management_y1_jpy * ((1 + model.management_escalation) ** idx)
            + model.liaison_y1_jpy * ((1 + model.liaison_escalation) ** idx)
            + model.insurance_y1_jpy * ((1 + model.insurance_escalation) ** idx)
            + model.community_benefit_y1_jpy * ((1 + model.community_benefit_escalation) ** idx)
        )
        ebitda = gross_profit - sga
        compute_dep = model.compute_hardware_capex_jpy / model.compute_useful_life_years if year <= model.compute_useful_life_years else 0.0
        dep = compute_dep + infra_dep
        ebit = ebitda - dep
        interest = compute_debt[idx][2] + infra_debt[idx][2]
        ebt = ebit - interest
        taxes = max(0.0, ebt * model.effective_tax_rate)
        net_income = ebt - taxes
        principal = compute_debt[idx][1] + infra_debt[idx][1]
        debt_service = principal + interest
        dscr = ebitda / debt_service if debt_service else 0.0
        wc = gross_rev * model.working_capital_share_of_revenue
        delta_wc = wc - prior_wc
        prior_wc = wc
        maint = gross_rev * model.maintenance_capex_share_of_revenue
        fcfe = net_income + dep - delta_wc - maint - principal
        years.append(ModelYear(year, util, gpu_hours, compute_rev, model.heat_value_jpy[idx], gross_rev, kwh, electricity, cogs, gross_profit, sga, ebitda, compute_dep, infra_dep, ebit, interest, ebt, taxes, net_income, principal, debt_service, dscr, wc, delta_wc, maint, fcfe))

    annual_fcfe = tuple(y.fcfe_jpy for y in years)
    cash_flows = (-equity_required, *annual_fcfe)
    cumulative = sum(annual_fcfe)
    sources_less_uses = (
        model.committed_awarded_grants_jpy
        + model.compute_debt.principal_jpy
        + model.infrastructure_debt.principal_jpy
        + equity_required - total_capex
    )
    return YumoriEconomicResult(
        infrastructure_capex,
        total_capex,
        equity_required,
        model.potential_grants_scenario_jpy,
        tuple(years),
        cumulative,
        calculate_irr(cash_flows) if equity_required else None,
        _npv(model.equity_discount_rate, cash_flows),
        cumulative / equity_required if equity_required else None,
        _payback_years(equity_required, annual_fcfe) if equity_required else 0.0,
        min((y.dscr for y in years), default=inf),
        {
            "revenue_shares_sum_to_one": abs(sum(t.share for t in model.revenue_tiers) - 1.0) <= 1e-9,
            "base_sources_equal_uses": abs(sources_less_uses) <= 0.01,
            "potential_grants_excluded_from_base": model.potential_grants_scenario_jpy >= 0,
            "compute_depreciation_stops_after_useful_life": years[-1].compute_depreciation_jpy == 0.0,
        },
        {
            "calculation_authority": "YUMORI/eSingularity repository model",
            "legacy_base_case": "Five-year defaults preserve the functional FIN workbook for audit continuity; they do not size the node.",
            "sizing": "Use calculate_demand_led_node_sizing; do not choose MW first.",
            "commercial_inputs": "Tariff, utilization, service pricing, demand, debt, CapEx, and heat value remain VERIFY/MODEL until evidenced.",
        },
    )


@dataclass(frozen=True)
class HeatRecoveryInputs:
    it_load_kw: float
    load_fraction: float
    recovery_fraction: float
    delivery_efficiency: float
    thermal_demand_kw: float
    annual_availability: float
    value_jpy_per_thermal_kwh: float
    grid_heat_kg_co2_per_kwh: float = 0.0
    hours_per_year: float = HOURS_PER_YEAR

    def validate(self) -> None:
        if self.it_load_kw < 0 or self.thermal_demand_kw < 0:
            raise ValueError("heat loads and demand cannot be negative")
        if self.value_jpy_per_thermal_kwh < 0:
            raise ValueError("heat value cannot be negative")
        for value in (
            self.load_fraction,
            self.recovery_fraction,
            self.delivery_efficiency,
            self.annual_availability,
        ):
            if not 0.0 <= value <= 1.0:
                raise ValueError("heat fractions must stay between zero and one")


@dataclass(frozen=True)
class HeatRecoveryResult:
    source_heat_kw: float
    recovered_heat_kw: float
    delivered_heat_kw: float
    usable_heat_kw: float
    annual_usable_thermal_kwh: float
    annual_value_jpy: float
    avoided_kg_co2: float


def calculate_heat_recovery(inputs: HeatRecoveryInputs) -> HeatRecoveryResult:
    """Value only heat that can be recovered, delivered, and actually used."""

    inputs.validate()
    source = inputs.it_load_kw * inputs.load_fraction
    recovered = source * inputs.recovery_fraction
    delivered = recovered * inputs.delivery_efficiency
    usable = min(delivered, inputs.thermal_demand_kw)
    annual_kwh = usable * inputs.hours_per_year * inputs.annual_availability
    return HeatRecoveryResult(
        source_heat_kw=source,
        recovered_heat_kw=recovered,
        delivered_heat_kw=delivered,
        usable_heat_kw=usable,
        annual_usable_thermal_kwh=annual_kwh,
        annual_value_jpy=annual_kwh * inputs.value_jpy_per_thermal_kwh,
        avoided_kg_co2=annual_kwh * inputs.grid_heat_kg_co2_per_kwh,
    )


@dataclass(frozen=True)
class InfrastructureFlow:
    flow_id: str
    source: str
    target: str
    flow_type: str
    status: str
    source_url: str
    evidence_class: str = "OFFICIAL"
    announced_at: str = ""
    amount_jpy: float | None = None
    amount_status: str = "UNDISCLOSED"
    note: str = ""

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "InfrastructureFlow":
        return cls(
            **{
                field_name: value[field_name]
                for field_name in cls.__dataclass_fields__
                if field_name in value
            }
        )


@dataclass(frozen=True)
class DependencyAnalysis:
    edge_count: int
    participant_count: int
    reciprocal_directed_edges: int
    reciprocal_share: float
    reciprocal_pairs: int
    directed_three_party_cycles: int
    paper_share: float
    paper_and_circular_edges: int
    endpoint_hhi: float
    effective_participants: float
    concentration_raw: float
    circularity_score: float
    announced_vs_paid_score: float
    counterparty_concentration_score: float
    computed_component_score: float
    computed_weight_coverage: float
    known_amount_jpy: float
    known_amount_edges: int
    undisclosed_amount_edges: int
    truth_boundary: str


def _bounded_scale(value: float, low: float, high: float) -> float:
    if high <= low:
        raise ValueError("scale high must exceed low")
    return max(0.0, min(1.0, (value - low) / (high - low))) * 100.0


def _directed_three_cycles(pairs: set[tuple[str, str]]) -> int:
    cycles: set[tuple[str, str, str]] = set()
    for first, second in pairs:
        for middle, third in pairs:
            if middle != second:
                continue
            if len({first, second, third}) != 3 or (third, first) not in pairs:
                continue
            rotations = (
                (first, second, third),
                (second, third, first),
                (third, first, second),
            )
            cycles.add(min(rotations))
    return len(cycles)


def analyze_infrastructure_flows(
    flows: Iterable[InfrastructureFlow],
) -> DependencyAnalysis:
    """Return only reproducible network indicators; never a market forecast."""

    records = tuple(
        flow for flow in flows if flow.source.strip() and flow.target.strip()
    )
    if not records:
        return DependencyAnalysis(
            0,
            0,
            0,
            0.0,
            0,
            0,
            0.0,
            0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.50,
            0.0,
            0,
            0,
            "Empty ledger; no market inference is available.",
        )

    pairs = {(flow.source.strip(), flow.target.strip()) for flow in records}
    reciprocal_edges = sum(
        (target, source) in pairs
        for source, target in (
            (flow.source.strip(), flow.target.strip()) for flow in records
        )
    )
    reciprocal_share = reciprocal_edges / len(records)
    reciprocal_pairs = len(
        {
            frozenset((source, target))
            for source, target in pairs
            if (target, source) in pairs
        }
    )
    paper_weights = [
        PAPER_STATUS_WEIGHTS.get(flow.status.strip().lower(), 0.5)
        for flow in records
    ]
    paper_share = sum(paper_weights) / len(paper_weights)
    paper_and_circular = sum(
        weight >= 1.0 and (flow.target.strip(), flow.source.strip()) in pairs
        for flow, weight in zip(records, paper_weights)
    )

    degree: dict[str, int] = {}
    for flow in records:
        degree[flow.source.strip()] = degree.get(flow.source.strip(), 0) + 1
        degree[flow.target.strip()] = degree.get(flow.target.strip(), 0) + 1
    total_endpoints = len(records) * 2
    endpoint_hhi = sum(
        (count / total_endpoints) ** 2 for count in degree.values()
    )
    effective_participants = 1.0 / endpoint_hhi if endpoint_hhi else 0.0
    participant_count = len(degree)
    concentration = (
        max(0.0, 1.0 - (effective_participants / participant_count))
        if participant_count
        else 0.0
    )

    circularity_score = _bounded_scale(reciprocal_share, 0.10, 0.60)
    paper_score = _bounded_scale(paper_share, 0.15, 0.70)
    concentration_score = _bounded_scale(concentration, 0.25, 0.70)
    component_score = (
        circularity_score * 0.25
        + paper_score * 0.15
        + concentration_score * 0.10
    ) / 0.50
    known_amounts = [
        flow.amount_jpy for flow in records if flow.amount_jpy is not None
    ]

    return DependencyAnalysis(
        edge_count=len(records),
        participant_count=participant_count,
        reciprocal_directed_edges=reciprocal_edges,
        reciprocal_share=reciprocal_share,
        reciprocal_pairs=reciprocal_pairs,
        directed_three_party_cycles=_directed_three_cycles(pairs),
        paper_share=paper_share,
        paper_and_circular_edges=paper_and_circular,
        endpoint_hhi=endpoint_hhi,
        effective_participants=effective_participants,
        concentration_raw=concentration,
        circularity_score=circularity_score,
        announced_vs_paid_score=paper_score,
        counterparty_concentration_score=concentration_score,
        computed_component_score=component_score,
        computed_weight_coverage=0.50,
        known_amount_jpy=sum(known_amounts),
        known_amount_edges=len(known_amounts),
        undisclosed_amount_edges=len(records) - len(known_amounts),
        truth_boundary=(
            "Partial dependency diagnostic only: reproducible indicators cover "
            "50% of the referenced methodology. Revenue-gap, financing-quality, "
            "and market-behavior judgements are omitted."
        ),
    )


def load_japan_infrastructure_flows(
    path: str | Path | None = None,
) -> tuple[InfrastructureFlow, ...]:
    ledger_path = (
        Path(path)
        if path
        else Path(__file__).resolve().parents[1]
        / "jhr"
        / "data"
        / "japan_ai_infrastructure_flows.json"
    )
    payload = json.loads(ledger_path.read_text(encoding="utf-8"))
    return tuple(
        InfrastructureFlow.from_mapping(item) for item in payload["flows"]
    )
