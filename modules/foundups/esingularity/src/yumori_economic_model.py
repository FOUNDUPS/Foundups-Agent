"""Calculation authority for the YUMORI adaptive-reuse economic model.

This is project economics for YUMORI/eSingularity.  It is deliberately separate
from the generic FoundUps token/ROC simulator.  Defaults reproduce the current
FIN YUMORI Phase 1 workbook while retaining its MODEL/VERIFY truth labels.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from math import inf
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


MODEL_YEARS = 5
METHODOLOGY_URL = "https://ai-circular-economy.com/"

# Will Francis's status weights. "operating" is the completed equivalent used
# by the Japan infrastructure ledger; an unrecognized status stays neutral.
PAPER_STATUS_WEIGHTS: Mapping[str, float] = {
    "completed": 0.0,
    "operating": 0.0,
    "signed": 0.5,
    "loi": 1.0,
    "paused": 1.0,
}


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
    """Five-year scenario inputs matching the current functional workbook.

    These defaults are not verified bids, customer contracts, utility tariffs,
    debt terms, grants, or forecasts.  Callers should replace them only with a
    sourced scenario and retain the status/provenance outside the calculation.
    """

    gpu_count: int = 384
    it_load_capacity_kw: float = 850.0
    pue: float = 1.12
    hours_per_year: float = 8_760.0
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
    # Workbook-parity placeholders. Use calculate_heat_recovery() to replace
    # them after an engineering heat balance and an offtake value exist.
    heat_value_jpy: tuple[float, ...] = (
        4_000_000.0,
        6_000_000.0,
        6_000_000.0,
        6_000_000.0,
        6_000_000.0,
    )
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
        if any(not 0.0 <= value <= 1.0 for value in self.utilization):
            raise ValueError("utilization must stay between zero and one")
        if not 0.0 <= self.idle_it_load_fraction <= 1.0:
            raise ValueError("idle IT load fraction must stay between zero and one")
        if abs(sum(tier.share for tier in self.revenue_tiers) - 1.0) > 1e-9:
            raise ValueError("revenue tier shares must sum to 1.0")
        if any(tier.share < 0 or tier.price_jpy_per_gpu_hour < 0 for tier in self.revenue_tiers):
            raise ValueError("revenue shares and prices cannot be negative")
        for rate in (
            self.electricity_escalation,
            self.gpu_price_escalation,
            self.effective_tax_rate,
            self.maintenance_capex_share_of_revenue,
            self.working_capital_share_of_revenue,
            self.equity_discount_rate,
        ):
            if rate < 0:
                raise ValueError("rates cannot be negative")
        for debt in (self.compute_debt, self.infrastructure_debt):
            if debt.principal_jpy < 0 or debt.annual_interest_rate < 0 or debt.term_years <= 0:
                raise ValueError("debt terms must be non-negative with a positive term")
        if self.committed_awarded_grants_jpy < 0 or self.potential_grants_scenario_jpy < 0:
            raise ValueError("grant amounts cannot be negative")


@dataclass(frozen=True)
class DebtYear:
    opening_jpy: float
    principal_jpy: float
    interest_jpy: float
    ending_jpy: float


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


def _debt_schedule(terms: DebtTerms, years: int = MODEL_YEARS) -> tuple[DebtYear, ...]:
    annual_principal = terms.principal_jpy / terms.term_years
    opening = terms.principal_jpy
    schedule: list[DebtYear] = []
    for _ in range(years):
        principal = min(opening, annual_principal)
        interest = opening * terms.annual_interest_rate
        ending = max(0.0, opening - principal)
        schedule.append(DebtYear(opening, principal, interest, ending))
        opening = ending
    return tuple(schedule)


def _npv(rate: float, cash_flows: Sequence[float]) -> float:
    return sum(cash_flow / ((1.0 + rate) ** period) for period, cash_flow in enumerate(cash_flows))


def calculate_irr(cash_flows: Sequence[float]) -> float | None:
    """Return a conventional annual IRR using a dependency-free bisection."""

    if len(cash_flows) < 2 or not (any(v < 0 for v in cash_flows) and any(v > 0 for v in cash_flows)):
        return None
    lower = -0.999999
    upper = 10.0
    low_value = _npv(lower, cash_flows)
    high_value = _npv(upper, cash_flows)
    if low_value == 0:
        return lower
    if high_value == 0:
        return upper
    if low_value * high_value > 0:
        return None
    for _ in range(200):
        middle = (lower + upper) / 2.0
        value = _npv(middle, cash_flows)
        if abs(value) < 1e-7:
            return middle
        if low_value * value > 0:
            lower, low_value = middle, value
        else:
            upper = middle
    return (lower + upper) / 2.0


def _payback_years(initial_equity: float, annual_fcfe: Sequence[float]) -> float | None:
    running = -initial_equity
    for year, cash_flow in enumerate(annual_fcfe, start=1):
        prior = running
        running += cash_flow
        if running >= 0 and cash_flow > 0:
            return (year - 1) + (-prior / cash_flow)
    return None


def run_yumori_economic_model(inputs: YumoriEconomicInputs | None = None) -> YumoriEconomicResult:
    """Calculate the YUMORI five-year project scenario.

    Potential grants never reduce the base financing need. Only the explicitly
    committed/awarded grant field is deducted.
    """

    model = inputs or YumoriEconomicInputs()
    model.validate()
    infrastructure_capex = sum(item.amount_jpy for item in model.infrastructure_items)
    total_capex = infrastructure_capex + model.compute_hardware_capex_jpy
    equity_required = max(
        0.0,
        total_capex
        - model.committed_awarded_grants_jpy
        - model.compute_debt.principal_jpy
        - model.infrastructure_debt.principal_jpy,
    )
    compute_debt = _debt_schedule(model.compute_debt)
    infrastructure_debt = _debt_schedule(model.infrastructure_debt)
    infrastructure_depreciation = max(
        infrastructure_capex - model.committed_awarded_grants_jpy, 0.0
    ) / model.infrastructure_useful_life_years

    results: list[ModelYear] = []
    prior_working_capital = 0.0
    for index in range(MODEL_YEARS):
        year = index + 1
        utilization = model.utilization[index]
        billable_gpu_hours = model.gpu_count * model.hours_per_year * utilization
        compute_revenue = sum(
            model.gpu_count
            * tier.share
            * model.hours_per_year
            * utilization
            * tier.price_jpy_per_gpu_hour
            * ((1.0 + model.gpu_price_escalation) ** index)
            for tier in model.revenue_tiers
        )
        heat_value = model.heat_value_jpy[index]
        gross_revenue = compute_revenue + heat_value

        effective_load_fraction = model.idle_it_load_fraction + (
            (1.0 - model.idle_it_load_fraction) * utilization
        )
        electricity_consumption = (
            model.it_load_capacity_kw * model.pue * model.hours_per_year * effective_load_fraction
        )
        tariff = model.electricity_tariff_jpy_per_kwh * (
            (1.0 + model.electricity_escalation) ** index
        )
        electricity_cost = electricity_consumption * tariff
        cogs = sum(
            (
                electricity_cost,
                model.coolant_maintenance_y1_jpy * ((1.0 + model.coolant_escalation) ** index),
                model.fiber_network_y1_jpy * ((1.0 + model.fiber_escalation) ** index),
                model.direct_labor_y1_jpy * ((1.0 + model.direct_labor_escalation) ** index),
            )
        )
        gross_profit = gross_revenue - cogs
        sga = sum(
            (
                model.management_y1_jpy * ((1.0 + model.management_escalation) ** index),
                model.liaison_y1_jpy * ((1.0 + model.liaison_escalation) ** index),
                model.insurance_y1_jpy * ((1.0 + model.insurance_escalation) ** index),
                model.community_benefit_y1_jpy
                * ((1.0 + model.community_benefit_escalation) ** index),
            )
        )
        ebitda = gross_profit - sga
        compute_depreciation = (
            model.compute_hardware_capex_jpy / model.compute_useful_life_years
            if year <= model.compute_useful_life_years
            else 0.0
        )
        depreciation = compute_depreciation + infrastructure_depreciation
        ebit = ebitda - depreciation
        interest = compute_debt[index].interest_jpy + infrastructure_debt[index].interest_jpy
        earnings_before_tax = ebit - interest
        cash_taxes = max(0.0, earnings_before_tax * model.effective_tax_rate)
        net_income = earnings_before_tax - cash_taxes
        principal = compute_debt[index].principal_jpy + infrastructure_debt[index].principal_jpy
        debt_service = principal + interest
        dscr = ebitda / debt_service if debt_service else 0.0
        working_capital = gross_revenue * model.working_capital_share_of_revenue
        working_capital_change = working_capital - prior_working_capital
        prior_working_capital = working_capital
        maintenance_capex = gross_revenue * model.maintenance_capex_share_of_revenue
        fcfe = net_income + depreciation - working_capital_change - maintenance_capex - principal
        results.append(
            ModelYear(
                year=year,
                utilization=utilization,
                billable_gpu_hours=billable_gpu_hours,
                compute_revenue_jpy=compute_revenue,
                heat_value_jpy=heat_value,
                gross_revenue_jpy=gross_revenue,
                electricity_consumption_kwh=electricity_consumption,
                electricity_cost_jpy=electricity_cost,
                cogs_jpy=cogs,
                gross_profit_jpy=gross_profit,
                sga_jpy=sga,
                ebitda_jpy=ebitda,
                compute_depreciation_jpy=compute_depreciation,
                infrastructure_depreciation_jpy=infrastructure_depreciation,
                ebit_jpy=ebit,
                interest_jpy=interest,
                earnings_before_tax_jpy=earnings_before_tax,
                cash_taxes_jpy=cash_taxes,
                net_income_jpy=net_income,
                debt_principal_jpy=principal,
                debt_service_jpy=debt_service,
                dscr=dscr,
                working_capital_jpy=working_capital,
                change_in_working_capital_jpy=working_capital_change,
                maintenance_capex_jpy=maintenance_capex,
                fcfe_jpy=fcfe,
            )
        )

    annual_fcfe = tuple(year.fcfe_jpy for year in results)
    equity_cash_flows = (-equity_required, *annual_fcfe)
    cumulative_fcfe = sum(annual_fcfe)
    sources_less_uses = (
        model.committed_awarded_grants_jpy
        + model.compute_debt.principal_jpy
        + model.infrastructure_debt.principal_jpy
        + equity_required
        - total_capex
    )
    equity_multiple = cumulative_fcfe / equity_required if equity_required else None
    truth_boundary = {
        "calculation_authority": "YUMORI/eSingularity FoundUp Python model",
        "not_roc": "No FoundUps token, ROC, CABR, or payout economics are calculated here.",
        "base_case": "Defaults reproduce the FIN YUMORI functional workbook; they are not a forecast.",
        "funding": "Only committed/awarded grants reduce base financing; debt remains MODEL ONLY.",
        "commercial_inputs": "Tariff, utilization, GPU pricing, demand, and heat value remain VERIFY.",
    }
    return YumoriEconomicResult(
        total_infrastructure_capex_jpy=infrastructure_capex,
        total_project_capex_jpy=total_capex,
        equity_required_jpy=equity_required,
        potential_grants_excluded_jpy=model.potential_grants_scenario_jpy,
        years=tuple(results),
        cumulative_fcfe_jpy=cumulative_fcfe,
        equity_irr=calculate_irr(equity_cash_flows) if equity_required else None,
        equity_npv_jpy=_npv(model.equity_discount_rate, equity_cash_flows),
        equity_multiple_5y=equity_multiple,
        payback_years=_payback_years(equity_required, annual_fcfe) if equity_required else 0.0,
        minimum_dscr=min((year.dscr for year in results), default=inf),
        checks={
            "revenue_shares_sum_to_one": abs(sum(t.share for t in model.revenue_tiers) - 1.0) <= 1e-9,
            "base_sources_equal_uses": abs(sources_less_uses) <= 0.01,
            "potential_grants_excluded_from_base": model.potential_grants_scenario_jpy >= 0.0,
            "compute_depreciation_stops_after_useful_life": results[-1].compute_depreciation_jpy == 0.0,
        },
        truth_boundary=truth_boundary,
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
    hours_per_year: float = 8_760.0

    def validate(self) -> None:
        if self.it_load_kw < 0 or self.thermal_demand_kw < 0 or self.value_jpy_per_thermal_kwh < 0:
            raise ValueError("heat loads, demand, and value cannot be negative")
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
    """Calculate usable onsen heat without counting rejected heat as value."""

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
        return cls(**{field_name: value[field_name] for field_name in cls.__dataclass_fields__ if field_name in value})


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
            if middle != second or len({first, second, third}) != 3 or (third, first) not in pairs:
                continue
            rotations = (
                (first, second, third),
                (second, third, first),
                (third, first, second),
            )
            cycles.add(min(rotations))
    return len(cycles)


def analyze_infrastructure_flows(flows: Iterable[InfrastructureFlow]) -> DependencyAnalysis:
    """Analyze sourced Japan infrastructure flows using the map's computed math.

    Only the three reproducible network indicators are calculated. The original
    site's three manually judged market indicators are intentionally omitted, so
    this result is not labelled a bubble index or an investment conclusion.
    """

    records = tuple(flow for flow in flows if flow.source.strip() and flow.target.strip())
    if not records:
        return DependencyAnalysis(
            edge_count=0,
            participant_count=0,
            reciprocal_directed_edges=0,
            reciprocal_share=0.0,
            reciprocal_pairs=0,
            directed_three_party_cycles=0,
            paper_share=0.0,
            paper_and_circular_edges=0,
            endpoint_hhi=0.0,
            effective_participants=0.0,
            concentration_raw=0.0,
            circularity_score=0.0,
            announced_vs_paid_score=0.0,
            counterparty_concentration_score=0.0,
            computed_component_score=0.0,
            computed_weight_coverage=0.5,
            known_amount_jpy=0.0,
            known_amount_edges=0,
            undisclosed_amount_edges=0,
            truth_boundary="Empty ledger; no market inference is available.",
        )
    pairs = {(flow.source.strip(), flow.target.strip()) for flow in records}
    reciprocal_edges = sum((target, source) in pairs for source, target in ((f.source.strip(), f.target.strip()) for f in records))
    reciprocal_share = reciprocal_edges / len(records)
    reciprocal_pairs = len({frozenset((source, target)) for source, target in pairs if (target, source) in pairs})

    paper_weights = [PAPER_STATUS_WEIGHTS.get(flow.status.strip().lower(), 0.5) for flow in records]
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
    hhi = sum((count / total_endpoints) ** 2 for count in degree.values())
    effective_participants = 1.0 / hhi if hhi else 0.0
    participant_count = len(degree)
    concentration = max(0.0, 1.0 - (effective_participants / participant_count)) if participant_count else 0.0

    circularity_score = _bounded_scale(reciprocal_share, 0.10, 0.60)
    paper_score = _bounded_scale(paper_share, 0.15, 0.70)
    concentration_score = _bounded_scale(concentration, 0.25, 0.70)
    computed_component_score = (
        circularity_score * 0.25 + paper_score * 0.15 + concentration_score * 0.10
    ) / 0.50
    known_amounts = [flow.amount_jpy for flow in records if flow.amount_jpy is not None]
    return DependencyAnalysis(
        edge_count=len(records),
        participant_count=participant_count,
        reciprocal_directed_edges=reciprocal_edges,
        reciprocal_share=reciprocal_share,
        reciprocal_pairs=reciprocal_pairs,
        directed_three_party_cycles=_directed_three_cycles(pairs),
        paper_share=paper_share,
        paper_and_circular_edges=paper_and_circular,
        endpoint_hhi=hhi,
        effective_participants=effective_participants,
        concentration_raw=concentration,
        circularity_score=circularity_score,
        announced_vs_paid_score=paper_score,
        counterparty_concentration_score=concentration_score,
        computed_component_score=computed_component_score,
        computed_weight_coverage=0.50,
        known_amount_jpy=sum(known_amounts),
        known_amount_edges=len(known_amounts),
        undisclosed_amount_edges=len(records) - len(known_amounts),
        truth_boundary=(
            "Partial dependency diagnostic only: three computed indicators cover 50% of the source "
            "methodology. Revenue-gap, financing-quality, and market-behavior judgements are omitted."
        ),
    )


def load_japan_infrastructure_flows(path: str | Path | None = None) -> tuple[InfrastructureFlow, ...]:
    ledger_path = Path(path) if path else Path(__file__).resolve().parents[1] / "jhr" / "data" / "japan_ai_infrastructure_flows.json"
    payload = json.loads(ledger_path.read_text(encoding="utf-8"))
    return tuple(InfrastructureFlow.from_mapping(item) for item in payload["flows"])
