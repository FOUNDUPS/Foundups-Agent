"""Three-site capital allocation; missing inputs never become zero-cost projects.

This bounded extension does not size compute or import legacy Sukatto economics.
Cash scenarios are hypotheses. Deployment requires independently evidenced gates.
Amounts are nominal JPY; payback is undiscounted and limited to supplied years.
"""

from dataclasses import asdict, dataclass, fields
from math import isfinite


SCHOOL_COSTS = (
    "survey_engineering", "building_retrofit", "electrical_receiving",
    "transformer_switchgear", "utility_contribution", "modular_dc",
    "compute_hardware", "cooling_cdu_heat_rejection", "ups", "bess",
    "fiber_network", "fire_suppression", "security", "seismic_building",
    "mechanical", "contingency", "design_permitting", "education_community",
    "site_use_rights",
)
SUKATTO_COSTS = (
    "lawful_acquisition_lease_use", "building_rehabilitation", "asbestos",
    "mep_renewal", "onsen_restoration", "thermal_loop_heat_reuse",
    "public_community", "education_innovation", "optional_compute",
    "design_permitting", "contingency", "survey_engineering",
)
EVIDENCE_CLASSES = {"SOURCED", "VENDOR QUOTE", "ENGINEERING ESTIMATE", "MODEL ONLY", "TBD"}
GRANT_STATUSES = {"VERIFIED PROGRAM", "ELIGIBILITY INQUIRY", "ELIGIBLE", "APPLICATION", "SELECTED", "AWARDED"}
GATE_NAMES = ("utility", "fiber", "building", "demand", "capex", "financing", "legal_use")
SITE_NAMES = {"Site 1": "Sukatto", "Site 2": "Shimousaka", "Site 3": "Hanyu"}


def _amount(value: float | None, label: str) -> None:
    if value is not None and (isinstance(value, bool) or not isfinite(value) or value < 0):
        raise ValueError(f"{label} must be finite, nonnegative or None")


@dataclass(frozen=True)
class SiteCost:
    category: str
    amount_jpy: float | None = None
    evidence: str = "TBD"
    source: str = ""

    def validate(self) -> None:
        _amount(self.amount_jpy, self.category)
        if not self.category or self.evidence not in EVIDENCE_CLASSES:
            raise ValueError("Invalid cost category/evidence")
        if self.amount_jpy is not None and self.evidence == "TBD":
            raise ValueError("A numeric cost needs an explicit evidence class")
        if self.evidence not in {"TBD", "MODEL ONLY"} and not self.source:
            raise ValueError("Evidence-backed costs require a source")


@dataclass(frozen=True)
class GrantAllocation:
    allocation_id: str
    site_id: str
    amount_jpy: float
    status: str
    award_reference: str = ""

    def validate(self) -> None:
        _amount(self.amount_jpy, "grant")
        if self.amount_jpy is None:
            raise ValueError("Grant allocations require an explicit amount")
        if not self.allocation_id or self.status not in GRANT_STATUSES:
            raise ValueError("Invalid grant allocation/status")
        if self.status == "AWARDED" and not self.award_reference:
            raise ValueError("AWARDED requires an award reference")


@dataclass(frozen=True)
class SiteFinancialInputs:
    site_id: str
    priority: int
    costs: tuple[SiteCost, ...]
    included: bool = True
    committed_debt_jpy: float = 0.0
    committed_equity_jpy: float = 0.0
    gates: tuple[str, ...] = ("UNVERIFIED",) * 7
    utility_confirmed_kw: float | None = None
    demand_facility_kw: float | None = None
    # Independent cash estimates for site/phase payback, never copied from Hanyu.
    unlevered_cash_flows_jpy: tuple[float, ...] | None = None

    def validate(self) -> None:
        if self.site_id not in SITE_NAMES or self.priority not in (1, 2, 3):
            raise ValueError("Unknown canonical site or priority")
        if not self.costs or len({c.category for c in self.costs}) != len(self.costs):
            raise ValueError("Site cost categories must be nonempty and unique")
        for cost in self.costs:
            cost.validate()
        for key in ("committed_debt_jpy", "committed_equity_jpy", "utility_confirmed_kw", "demand_facility_kw"):
            _amount(getattr(self, key), key)
        if self.committed_debt_jpy is None or self.committed_equity_jpy is None:
            raise ValueError("Committed sources require explicit amounts; use zero for none recorded")
        if len(self.gates) != len(GATE_NAMES) or any(g not in {"PASS", "UNVERIFIED", "FAIL"} for g in self.gates):
            raise ValueError("Each named gate requires PASS, UNVERIFIED or FAIL")
        if self.unlevered_cash_flows_jpy is not None and any(not isfinite(v) for v in self.unlevered_cash_flows_jpy):
            raise ValueError("Cash flows must be finite")

    @property
    def deployable(self) -> bool:
        return (
            self.included and all(g == "PASS" for g in self.gates)
            and all(c.amount_jpy is not None for c in self.costs)
            and self.utility_confirmed_kw is not None
            and self.demand_facility_kw is not None
            and 0 < self.demand_facility_kw <= self.utility_confirmed_kw
        )


def default_portfolio_sites() -> tuple[SiteFinancialInputs, ...]:
    return tuple(
        SiteFinancialInputs(site, priority, tuple(SiteCost(c) for c in categories))
        for site, priority, categories in (
            ("Site 3", 1, SCHOOL_COSTS), ("Site 2", 2, SCHOOL_COSTS), ("Site 1", 3, SUKATTO_COSTS)
        )
    )


@dataclass(frozen=True)
class AnnualCashInputs:
    revenue_jpy: float | None = None
    electricity_jpy: float | None = None
    operations_jpy: float | None = None  # includes network, staff, insurance
    maintenance_jpy: float | None = None
    cash_tax_jpy: float | None = None
    working_capital_increase_jpy: float | None = None
    renewal_capex_jpy: float | None = None
    debt_service_jpy: float | None = None  # interest + principal, quoted or MODEL ONLY
    reserve_contribution_jpy: float | None = None
    investor_due_jpy: float | None = None  # agreed distribution/repayment assumption
    community_benefit_jpy: float | None = None  # cash commitment, not wider impact


@dataclass(frozen=True)
class PortfolioInputs:
    sites: tuple[SiteFinancialInputs, ...] = ()
    hanyu_cash: tuple[AnnualCashInputs, ...] = (AnnualCashInputs(),) * 5
    hanyu_expansion_capex_jpy: float | None = None
    expansion_gate_passed: bool = False
    grants: tuple[GrantAllocation, ...] = ()
    scenario: str = "base"
    investor_equity_jpy: float | None = None  # scenario paid-in equity, not committed source


@dataclass(frozen=True)
class CashYear:
    ebitda_jpy: float
    unlevered_cash_jpy: float
    debt_service_jpy: float
    free_cash_after_debt_jpy: float
    investor_distribution_jpy: float
    investor_arrears_jpy: float
    retained_cash_balance_jpy: float
    dscr: float | None


@dataclass(frozen=True)
class PortfolioResult:
    scenario: str
    site_capex_jpy: dict[str, float | None]
    entered_cost_subtotal_jpy: float
    total_portfolio_capex_jpy: float | None
    committed_sources_jpy: float
    unawarded_grants_excluded_jpy: float
    initial_hanyu_funding_gap_jpy: float | None
    gross_external_capital_gap_jpy: float | None
    residual_financing_gap_jpy: float | None
    later_phase_requirement_jpy: float | None
    reinvestable_cash_jpy: float | None
    peak_cash_bridge_jpy: float | None
    self_funding_result: str
    missing_inputs: tuple[str, ...]
    years: tuple[CashYear, ...]
    affordable_allocations_jpy: dict[str, float]
    deployable_allocations_jpy: dict[str, float]
    deployment_gates: dict[str, bool]
    site_payback_years: dict[str, float | None]
    phase_payback_years: dict[int, float | None]
    portfolio_payback_years: float | None
    investor_payback_years: float | None

    def to_dict(self) -> dict:
        return asdict(self)


def _payback(cost: float | None, cash: tuple[float, ...] | None) -> float | None:
    if cost is None or cash is None:
        return None
    if cost == 0:
        return 0.0
    running = -cost
    for year, value in enumerate(cash):
        prior, running = running, running + value
        if running >= 0 and value > 0:
            return year - prior / value
    return None  # no recovery within the supplied horizon; never extrapolate


def run_portfolio_model(inputs: PortfolioInputs | None = None) -> PortfolioResult:
    model = inputs or PortfolioInputs()
    sites = model.sites or default_portfolio_sites()
    for site in sites:
        site.validate()
    if len({s.site_id for s in sites}) != len(sites) or len({s.priority for s in sites}) != len(sites):
        raise ValueError("Duplicate site identity or priority")
    included = tuple(sorted((s for s in sites if s.included), key=lambda s: s.priority))
    if not included or included[0].site_id != "Site 3" or included[0].priority != 1:
        raise ValueError("This self-funding test requires Hanyu as Priority 1")
    if not model.hanyu_cash:
        raise ValueError("At least one cash-flow year is required")
    _amount(model.hanyu_expansion_capex_jpy, "Hanyu expansion")
    _amount(model.investor_equity_jpy, "investor equity")
    if len({g.allocation_id for g in model.grants}) != len(model.grants):
        raise ValueError("Grant allocation counted more than once")
    awarded = {s.site_id: 0.0 for s in included}
    excluded_grants = 0.0
    for grant in model.grants:
        grant.validate()
        if grant.site_id not in {s.site_id for s in sites}:
            raise ValueError("Grant references an unknown site")
        if grant.site_id not in awarded:
            continue  # an excluded site's restricted grant cannot finance another site
        if grant.status == "AWARDED":
            awarded[grant.site_id] += grant.amount_jpy
        else:
            excluded_grants += grant.amount_jpy

    missing, capex = [], {}
    entered = 0.0
    for site in included:
        entered += sum(c.amount_jpy for c in site.costs if c.amount_jpy is not None)
        absent = [f"{site.site_id}.{c.category}" for c in site.costs if c.amount_jpy is None]
        missing.extend(absent)
        capex[site.site_id] = None if absent else sum(c.amount_jpy for c in site.costs)
    if model.hanyu_expansion_capex_jpy is None:
        missing.append("Hanyu expansion CapEx (enter 0 only if explicitly excluded)")
    else:
        entered += model.hanyu_expansion_capex_jpy
    total = None if missing else entered
    site_sources = {s.site_id: s.committed_debt_jpy + s.committed_equity_jpy + awarded[s.site_id] for s in included}
    # Restricted site funding never covers another site's shortfall implicitly.
    gaps = {s.site_id: None if capex[s.site_id] is None else max(0.0, capex[s.site_id] - site_sources[s.site_id]) for s in included}
    gross_gap = None if total is None else sum(gaps.values()) + model.hanyu_expansion_capex_jpy
    later = None if total is None else total - capex["Site 3"]

    cash_missing = []
    for year, cash in enumerate(model.hanyu_cash, 1):
        for f in fields(cash):
            value = getattr(cash, f.name)
            _amount(value, f.name)
            if value is None:
                cash_missing.append(f"{model.scenario}.Y{year}.{f.name}")
    missing.extend(cash_missing)
    years, balance, arrears, peak_bridge = [], 0.0, 0.0, 0.0
    if not cash_missing:
        for c in model.hanyu_cash:
            ebitda = c.revenue_jpy - c.electricity_jpy - c.operations_jpy - c.maintenance_jpy - c.community_benefit_jpy
            unlevered = ebitda - c.cash_tax_jpy - c.working_capital_increase_jpy - c.renewal_capex_jpy
            free_cash = unlevered - c.debt_service_jpy
            balance += free_cash - c.reserve_contribution_jpy
            due = arrears + c.investor_due_jpy
            distribution = min(max(0.0, balance), due)
            arrears = due - distribution
            balance -= distribution
            peak_bridge = max(peak_bridge, -balance)
            years.append(CashYear(ebitda, unlevered, c.debt_service_jpy, free_cash,
                                  distribution, arrears, balance,
                                  unlevered / c.debt_service_jpy if c.debt_service_jpy else None))
    reinvestable = None if cash_missing else max(0.0, balance)
    if missing:
        verdict = "INSUFFICIENT EVIDENCE"
    elif peak_bridge > 0 or arrears > 0:
        verdict = "NO — ADDITIONAL CAPITAL REQUIRED"
    elif reinvestable >= later:
        verdict = "YES UNDER CURRENT MODEL ASSUMPTIONS"
    elif reinvestable > 0:
        verdict = "PARTIAL SELF-FUNDING"
    else:
        verdict = "NO — ADDITIONAL CAPITAL REQUIRED"

    gates = {s.site_id: s.deployable for s in included}
    affordable, deployable = {}, {}
    pool = reinvestable or 0.0
    if total is not None and reinvestable is not None and not arrears and not peak_bridge:
        targets = [("Hanyu expansion", model.hanyu_expansion_capex_jpy,
                    gates["Site 3"] and model.expansion_gate_passed)]
        prior_gate = gates["Site 3"]
        for site in included[1:]:
            prior_gate = prior_gate and gates[site.site_id]
            targets.append((site.site_id, capex[site.site_id], prior_gate))
        for name, need, gate in targets:
            allocated = min(pool, need)
            affordable[name] = allocated
            # Hold partial phases: staged tranches require an explicit smaller cost plan.
            deployable[name] = allocated if gate and allocated == need else 0.0
            pool -= allocated

    residual = None
    if gross_gap is not None and reinvestable is not None:
        future_gap = gross_gap - gaps["Site 3"]
        residual = gaps["Site 3"] + max(0.0, future_gap - reinvestable) + peak_bridge + arrears
    site_cash = {s.site_id: s.unlevered_cash_flows_jpy for s in included}
    site_cash["Site 3"] = tuple(y.unlevered_cash_jpy for y in years) if years else None
    paybacks = {key: _payback(capex[key], cash) for key, cash in site_cash.items()}
    portfolio_cash = None
    # Expansion's cash is not forecast here: no full-portfolio payback when it is included.
    if model.hanyu_expansion_capex_jpy == 0 and all(v is not None and len(v) == len(model.hanyu_cash) for v in site_cash.values()):
        portfolio_cash = tuple(sum(v[i] for v in site_cash.values()) for i in range(len(model.hanyu_cash)))
    return PortfolioResult(
        model.scenario, capex, entered, total, sum(site_sources.values()), excluded_grants,
        gaps["Site 3"], gross_gap, residual, later, reinvestable,
        None if cash_missing else peak_bridge, verdict, tuple(missing), tuple(years),
        affordable, deployable, gates, paybacks,
        {s.priority: paybacks[s.site_id] for s in included},
        _payback(total, portfolio_cash),
        _payback(model.investor_equity_jpy, tuple(y.investor_distribution_jpy for y in years) if years else None),
    )
