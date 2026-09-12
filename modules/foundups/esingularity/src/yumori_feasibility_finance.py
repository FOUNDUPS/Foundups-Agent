"""YUMORI / eSingularity feasibility funding and customer-offtake evidence.

This module is intentionally adjacent to, not a replacement for,
``yumori_financial_model.py``.  It models evidence and capital-feasibility gates
without changing the canonical Phase-1 P&L/debt outputs yet.

Accounting boundary:
- ordinary customer contract value is operating revenue / underwriting evidence;
- nominal multi-year contract value is not construction cash;
- only actual verified/committed upfront cash reduces the construction funding gap;
- candidate grants/support remain potential until awarded/committed.

WSP: 3, 50, 84, 95, 97, 109.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable, Tuple

GPUS_PER_MW_PLANNING = 384
GPUS_PER_NODE = 8


class EvidenceStatus(str, Enum):
    VERIFIED = "VERIFIED"
    COMMITTED = "COMMITTED"
    POTENTIAL = "POTENTIAL"
    MODEL_ONLY = "MODEL ONLY"


@dataclass(frozen=True)
class CapacityPlan:
    mw: float
    gpus: int
    eight_gpu_nodes: int


@dataclass(frozen=True)
class CustomerOfftake:
    organization: str
    customer_type: str
    product: str
    requested_gpus: int = 0
    requested_nodes: int = 0
    hours_per_month: float = 0.0
    reserved_capacity_gpus: int = 0
    start_date: str = ""
    contract_term_months: int = 0
    market_current_provider: str = ""
    current_price_jpy_per_gpu_hour: float = 0.0
    proposed_price_jpy_per_gpu_hour: float = 0.0
    annual_contract_value_jpy: float = 0.0
    nominal_multiyear_contract_value_jpy: float = 0.0
    take_or_pay_minimum_jpy: float = 0.0
    deposit_prepayment_pct: float = 0.0
    actual_upfront_cash_jpy: float = 0.0
    procurement_constraints: str = ""
    evidence_status: EvidenceStatus = EvidenceStatus.POTENTIAL
    evidence_source: str = ""

    def __post_init__(self) -> None:
        numeric_nonnegative = {
            "requested_gpus": self.requested_gpus,
            "requested_nodes": self.requested_nodes,
            "hours_per_month": self.hours_per_month,
            "reserved_capacity_gpus": self.reserved_capacity_gpus,
            "contract_term_months": self.contract_term_months,
            "current_price_jpy_per_gpu_hour": self.current_price_jpy_per_gpu_hour,
            "proposed_price_jpy_per_gpu_hour": self.proposed_price_jpy_per_gpu_hour,
            "annual_contract_value_jpy": self.annual_contract_value_jpy,
            "nominal_multiyear_contract_value_jpy": self.nominal_multiyear_contract_value_jpy,
            "take_or_pay_minimum_jpy": self.take_or_pay_minimum_jpy,
            "actual_upfront_cash_jpy": self.actual_upfront_cash_jpy,
        }
        for name, value in numeric_nonnegative.items():
            if value < 0:
                raise ValueError(f"{name} cannot be negative")
        if not 0.0 <= self.deposit_prepayment_pct <= 1.0:
            raise ValueError("deposit_prepayment_pct must be within 0-1")


@dataclass(frozen=True)
class OfftakeSummary:
    annual_committed_revenue_jpy: float
    nominal_committed_contract_value_jpy: float
    committed_take_or_pay_minimum_jpy: float
    verified_upfront_cash_jpy: float
    potential_annual_revenue_jpy: float
    potential_nominal_contract_value_jpy: float
    record_count: int


@dataclass(frozen=True)
class FeasibilityFundingInputs:
    phase1_total_project_cost_jpy: float
    city_cash_committed_jpy: float = 0.0
    city_in_kind_support_jpy: float = 0.0
    prefecture_cash_committed_jpy: float = 0.0
    national_awarded_support_jpy: float = 0.0
    private_quiet_phase_capital_committed_jpy: float = 0.0
    public_campaign_capital_committed_jpy: float = 0.0
    potential_public_support_jpy: float = 0.0
    pre_debt_target_pct: float = 0.80
    year1_ebitda_jpy: float = 0.0
    cash_flow_available_for_debt_service_jpy: float = 0.0
    dscr_requirement: float = 1.0
    debt_interest_rate: float = 0.0
    debt_term_years: int = 1

    def __post_init__(self) -> None:
        if self.phase1_total_project_cost_jpy <= 0:
            raise ValueError("phase1_total_project_cost_jpy must be positive")
        if not 0.0 <= self.pre_debt_target_pct <= 1.0:
            raise ValueError("pre_debt_target_pct must be within 0-1")
        if self.dscr_requirement <= 0:
            raise ValueError("dscr_requirement must be positive")
        if self.debt_interest_rate < 0:
            raise ValueError("debt_interest_rate cannot be negative")
        if self.debt_term_years <= 0:
            raise ValueError("debt_term_years must be positive")
        for name in (
            "city_cash_committed_jpy",
            "city_in_kind_support_jpy",
            "prefecture_cash_committed_jpy",
            "national_awarded_support_jpy",
            "private_quiet_phase_capital_committed_jpy",
            "public_campaign_capital_committed_jpy",
            "potential_public_support_jpy",
            "year1_ebitda_jpy",
            "cash_flow_available_for_debt_service_jpy",
        ):
            if getattr(self, name) < 0:
                raise ValueError(f"{name} cannot be negative")


@dataclass(frozen=True)
class FeasibilityFundingResult:
    pre_debt_cash_funding_jpy: float
    pre_debt_funding_pct: float
    pre_debt_target_jpy: float
    pre_debt_target_shortfall_jpy: float
    remaining_funding_gap_jpy: float
    max_annual_debt_service_jpy: float
    dscr_supported_debt_capacity_jpy: float
    actual_debt_deployed_jpy: float
    remaining_unfunded_gap_after_debt_jpy: float
    city_in_kind_support_jpy: float
    potential_public_support_jpy: float
    year1_ebitda_jpy: float
    cash_flow_available_for_debt_service_jpy: float


def capacity_plan(mw: float) -> CapacityPlan:
    """Planning relationship only: 1 MW ~= 384 GPUs ~= 48 eight-GPU nodes."""
    if mw <= 0:
        raise ValueError("mw must be positive")
    gpus_float = mw * GPUS_PER_MW_PLANNING
    gpus = round(gpus_float)
    if abs(gpus_float - gpus) > 1e-9:
        raise ValueError("mw must map to a whole GPU count under the 384-GPU/MW planning relationship")
    if gpus % GPUS_PER_NODE:
        raise ValueError("GPU count must map to whole 8-GPU nodes")
    return CapacityPlan(mw=mw, gpus=gpus, eight_gpu_nodes=gpus // GPUS_PER_NODE)


def summarize_offtake(records: Iterable[CustomerOfftake]) -> OfftakeSummary:
    annual_committed = nominal_committed = take_or_pay = verified_upfront = 0.0
    potential_annual = potential_nominal = 0.0
    count = 0
    committed_statuses = {EvidenceStatus.VERIFIED, EvidenceStatus.COMMITTED}
    for record in records:
        count += 1
        if record.evidence_status in committed_statuses:
            annual_committed += record.annual_contract_value_jpy
            nominal_committed += record.nominal_multiyear_contract_value_jpy
            take_or_pay += record.take_or_pay_minimum_jpy
            # Upfront cash reduces construction funding only when the record is
            # verified/committed and an actual cash amount is explicitly present.
            verified_upfront += record.actual_upfront_cash_jpy
        else:
            potential_annual += record.annual_contract_value_jpy
            potential_nominal += record.nominal_multiyear_contract_value_jpy
    return OfftakeSummary(
        annual_committed_revenue_jpy=annual_committed,
        nominal_committed_contract_value_jpy=nominal_committed,
        committed_take_or_pay_minimum_jpy=take_or_pay,
        verified_upfront_cash_jpy=verified_upfront,
        potential_annual_revenue_jpy=potential_annual,
        potential_nominal_contract_value_jpy=potential_nominal,
        record_count=count,
    )


def debt_capacity_from_cfads(
    cash_flow_available_for_debt_service_jpy: float,
    dscr_requirement: float,
    annual_interest_rate: float,
    term_years: int,
) -> Tuple[float, float]:
    """Return (max annual debt service, amortizing principal capacity)."""
    if cash_flow_available_for_debt_service_jpy < 0:
        raise ValueError("cash_flow_available_for_debt_service_jpy cannot be negative")
    if dscr_requirement <= 0:
        raise ValueError("dscr_requirement must be positive")
    if annual_interest_rate < 0 or term_years <= 0:
        raise ValueError("invalid debt rate/term")
    max_debt_service = cash_flow_available_for_debt_service_jpy / dscr_requirement
    if max_debt_service == 0:
        return 0.0, 0.0
    if annual_interest_rate == 0:
        return max_debt_service, max_debt_service * term_years
    annuity_factor = annual_interest_rate / (1.0 - (1.0 + annual_interest_rate) ** (-term_years))
    return max_debt_service, max_debt_service / annuity_factor


def calculate_feasibility_funding(
    inputs: FeasibilityFundingInputs,
    offtake: OfftakeSummary,
) -> FeasibilityFundingResult:
    """Calculate the NCDS-style pre-debt funding and debt-capacity waterfall.

    City in-kind support and potential public support are reported but excluded
    from cash funding.  Customer nominal contract value and ordinary operating
    revenue are also excluded. Only explicit actual upfront cash from
    verified/committed customer records enters pre-debt construction funding.
    """
    pre_debt_cash = (
        inputs.city_cash_committed_jpy
        + inputs.prefecture_cash_committed_jpy
        + inputs.national_awarded_support_jpy
        + offtake.verified_upfront_cash_jpy
        + inputs.private_quiet_phase_capital_committed_jpy
        + inputs.public_campaign_capital_committed_jpy
    )
    project_cost = inputs.phase1_total_project_cost_jpy
    pre_debt_pct = pre_debt_cash / project_cost
    pre_debt_target = project_cost * inputs.pre_debt_target_pct
    pre_debt_target_shortfall = max(0.0, pre_debt_target - pre_debt_cash)
    remaining_gap = max(0.0, project_cost - pre_debt_cash)
    max_service, supportable_debt = debt_capacity_from_cfads(
        inputs.cash_flow_available_for_debt_service_jpy,
        inputs.dscr_requirement,
        inputs.debt_interest_rate,
        inputs.debt_term_years,
    )
    actual_debt = min(remaining_gap, supportable_debt)
    remaining_after_debt = max(0.0, remaining_gap - actual_debt)
    return FeasibilityFundingResult(
        pre_debt_cash_funding_jpy=pre_debt_cash,
        pre_debt_funding_pct=pre_debt_pct,
        pre_debt_target_jpy=pre_debt_target,
        pre_debt_target_shortfall_jpy=pre_debt_target_shortfall,
        remaining_funding_gap_jpy=remaining_gap,
        max_annual_debt_service_jpy=max_service,
        dscr_supported_debt_capacity_jpy=supportable_debt,
        actual_debt_deployed_jpy=actual_debt,
        remaining_unfunded_gap_after_debt_jpy=remaining_after_debt,
        city_in_kind_support_jpy=inputs.city_in_kind_support_jpy,
        potential_public_support_jpy=inputs.potential_public_support_jpy,
        year1_ebitda_jpy=inputs.year1_ebitda_jpy,
        cash_flow_available_for_debt_service_jpy=inputs.cash_flow_available_for_debt_service_jpy,
    )
