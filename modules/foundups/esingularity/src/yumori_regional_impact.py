"""Regional Impact calculation owner; never part of project/investor cash flow.

Projects may use these arithmetic screens for feasibility, not as forecasts,
appraisals, measured GDP, or an NCDS-endorsed ROI formula. The existing Google
FIN Regional Impact tab is a working projection of this module.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from math import isfinite
from typing import Any

MODEL_VERSION = "regional-impact/1.0.0"
SOURCES = {
    "attendance": "https://www.city.fukui.lg.jp/fukusi/kfukusi/ikigai/p015196_d/fil/monitoring-30sukatto.pdf",
    "fy2019_reference": "https://www.city.fukui.lg.jp/sisei/gikai/shigikaishikumi/p022677_d/fil/aramasi2.pdf",
    "tourism_2025": "https://www.pref.fukui.lg.jp/doc/kankou/fukuiken-kankoukyakusu_d/fil/024.pdf",
    "io_method": "https://www.pref.fukui.lg.jp/doc/toukei-jouhou/hakyukouka.html",
    "property_reference": "https://www.city.fukui.lg.jp/sisei/plan/reform/p071776_d/fil/SUKATTO.pdf",
    "asset_admission": "modules/foundups/esingularity/frontend/audit/SOURCE_OF_TRUTH.md",
}
# (fiscal period, overnight uses/year, day uses/year, years, published average?)
HISTORICAL_PERIODS = (
    ("FY2005", 19213, 123271, 1, False),
    ("FY2006-2010", 16227, 133960, 5, True),
    ("FY2011-2015", 15159, 117855, 5, True),
    ("FY2016", 13597, 122185, 1, False),
    ("FY2017", 15382, 118039, 1, False),
    ("FY2018", 15621, 114028, 1, False),
)
FY2019_REFERENCE_USES = 124561  # retained; archived source recheck required
FY2018_USER_FEES_JPY = 124886000  # monitoring p.1, 124,886 thousand JPY


def _number(name: str, value: float, minimum: float = 0.0) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a finite number")
    if not isfinite(value) or value < minimum:
        raise ValueError(f"{name} must be finite and >= {minimum}")


def _fraction(name: str, value: float) -> None:
    _number(name, value)
    if value > 1:
        raise ValueError(f"{name} must be <= 1")


def _years(value: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 100:
        raise ValueError("years must be an integer in [1, 100]")


def annual_present_value(amount_jpy: float, rate: float, years: int) -> float:
    """End-of-year, constant nominal stream; zero rate is valid."""
    _number("amount_jpy", amount_jpy)
    _fraction("discount_rate", rate)
    _years(years)
    return sum(amount_jpy / (1 + rate) ** year for year in range(1, years + 1))


@dataclass(frozen=True)
class VisitorScenario:
    name: str = "100k provincial-benchmark screen"
    annual_visits: float = 100000
    spend_per_visit_jpy: float = 5546
    local_capture: float = 0.5
    additionality: float = 0.5
    discount_rate: float = 0.03
    years: int = 30

    def calculate(self) -> dict[str, Any]:
        for name in ("annual_visits", "spend_per_visit_jpy"):
            _number(name, getattr(self, name))
        for name in ("local_capture", "additionality", "discount_rate"):
            _fraction(name, getattr(self, name))
        _years(self.years)
        gross = self.annual_visits * self.spend_per_visit_jpy
        incremental = gross * self.local_capture * self.additionality
        return {
            "inputs": asdict(self),
            "gross_spend_jpy": gross,
            "incremental_local_spend_jpy": incremental,
            "gross_spend_10y_jpy": gross * 10,
            "gross_spend_horizon_jpy": gross * self.years,
            "gross_spend_pv_jpy": annual_present_value(gross, self.discount_rate, self.years),
            "incremental_spend_pv_jpy": annual_present_value(incremental, self.discount_rate, self.years),
            "horizon_visits": self.annual_visits * self.years,
            "io_total_output_jpy": None,
            "io_indirect_induced_jpy": None,
            "status": "SCENARIO; NOT PROJECT REVENUE OR GDP; I-O NOT CALCULATED",
        }


@dataclass(frozen=True)
class AssetScenario:
    historical_build_jpy: float = 4680000000
    demolition_estimate_jpy: float = 1580000000
    preparation_budget_jpy: float = 12720000
    historic_cost_index: float = 83.7
    current_cost_index: float = 121.6
    property_floor_m2: float = 8099.56
    site_m2: float = 33717.36
    annual_land_jpy_per_m2: float = 454.86
    listed_maintenance_jpy: float = 7892646
    discount_rate: float = 0.03
    demolition_escalation: float = 0.0
    years: int = 30
    annual_visits: float = 100000

    def calculate(self) -> dict[str, Any]:
        for name, value in asdict(self).items():
            _number(name, value)
        if self.historic_cost_index == 0 or self.property_floor_m2 == 0:
            raise ValueError("cost index and floor area must be positive")
        _fraction("discount_rate", self.discount_rate)
        _fraction("demolition_escalation", self.demolition_escalation)
        _years(self.years)
        indexed = self.historical_build_jpy * self.current_cost_index / self.historic_cost_index
        deferred = self.demolition_estimate_jpy * ((1 + self.demolition_escalation) / (1 + self.discount_rate)) ** self.years
        land = self.site_m2 * self.annual_land_jpy_per_m2
        hurdle = land + self.listed_maintenance_jpy
        return {
            "inputs": asdict(self),
            "indexed_construction_reference_jpy": indexed,
            "demolition_to_indexed_ratio": self.demolition_estimate_jpy / indexed if indexed else None,
            "indexed_reference_per_m2_jpy": indexed / self.property_floor_m2,
            "deferred_demolition_pv_jpy": deferred,
            "timing_only_difference_jpy": self.demolition_estimate_jpy - deferred,
            "land_burden_jpy": land,
            "listed_operating_hurdle_jpy": hurdle,
            "hurdle_per_visit_jpy": hurdle / self.annual_visits if self.annual_visits else None,
            "market_value_jpy": None,
            "actual_demolition_contract_jpy": None,
            "net_reuse_benefit_jpy": None,
            "status": "REFERENCE / SCENARIO; NOT APPRAISAL, CONTRACT PRICE OR FULL OPEX",
        }


def innovation_payroll(firms: float, fte_per_firm: float = 2, payroll_per_fte_jpy: float = 4000000) -> dict[str, Any]:
    for name, value in (("firms", firms), ("fte_per_firm", fte_per_firm), ("payroll_per_fte_jpy", payroll_per_fte_jpy)):
        _number(name, value)
    fte = firms * fte_per_firm
    payroll = fte * payroll_per_fte_jpy
    return {"firms": firms, "fte": fte, "annual_payroll_jpy": payroll,
            "payroll_10y_jpy": payroll * 10, "payroll_30y_jpy": payroll * 30,
            "status": "GROSS SCENARIO; NOT VERIFIED OR NET-NEW EMPLOYMENT"}


def calculate_regional_impact() -> dict[str, Any]:
    """Reproduce the separate regional workbook layer without cash injection."""
    history = [
        {"period": p, "overnight": o, "day": d, "years": y,
         "published_average": average, "period_uses": (o + d) * y}
        for p, o, d, y, average in HISTORICAL_PERIODS
    ]
    subtotal = sum(p["period_uses"] for p in history)
    visitors = [VisitorScenario(name, visits, spend).calculate() for name, visits, spend in (
        ("Lower-use sensitivity", 75000, 1000),
        ("100k planning sensitivity", 100000, 2500),
        ("100k provincial-benchmark screen", 100000, 5546),
        ("125k historical-use sensitivity", 125000, 5546),
    )]
    return {
        "model_version": MODEL_VERSION,
        "sources": SOURCES,
        "history": history,
        "source_derived_uses_fy2005_fy2018": subtotal,
        "history_precision": "SUM USING PUBLISHED FIVE-YEAR AVERAGES; NOT UNIQUE PEOPLE",
        "fy2019_reference_uses": FY2019_REFERENCE_USES,
        "expanded_reference_total_fy2005_fy2019": subtotal + FY2019_REFERENCE_USES,
        "fy2019_reference_status": "SOURCE RECHECK: ORIGINAL URL RETURNED 404 ON 2026-09-29",
        "lifetime_uses": None,
        "fy2018_user_fees_jpy": FY2018_USER_FEES_JPY,
        "user_fees_boundary": "RECORDED USER FEES; NOT LODGING-ONLY REVENUE, TOTAL REVENUE OR PROFIT",
        "tourism_benchmark": {"day_jpy": 5546, "overnight_jpy": 30221,
                              "day_retail_jpy": 1786, "day_other_jpy": 3760,
                              "fy2018_mix_equivalent_jpy": 114028 * 5546 + 15621 * 30221,
                              "boundary": "2025 TRIP AVERAGES, NOT FACILITY ACTUALS; OTHER INCLUDES FOOD/LOCAL TRANSPORT"},
        "visitors": visitors,
        "innovation": [innovation_payroll(n) for n in (20, 30, 60)],
        "asset": AssetScenario().calculate(),
        "aggregate_community_roi": None,
        "lodging_conversion": "NO AUTOMATIC CARRYOVER OF FORMER STAYS; EXTERNAL HOTEL DEMAND REQUIRES EVIDENCE",
        "cash_boundary": "NO LINK INTO PROJECT REVENUE, CFADS, DSCR, INVESTOR RETURN OR REINVESTABLE CASH",
    }


def regional_projection_values() -> dict[str, float]:
    """Expected numerical values at existing Regional Impact cell addresses.

    Recompute for a parity receipt; this does not read/write Drive or confer
    authority to overwrite current human assumptions.
    """
    result = calculate_regional_impact()
    asset = result["asset"]
    cells = {"B6": result["source_derived_uses_fy2005_fy2018"],
             "B18": result["tourism_benchmark"]["fy2018_mix_equivalent_jpy"],
             "B50": asset["deferred_demolition_pv_jpy"],
             "B51": asset["timing_only_difference_jpy"],
             "B54": asset["indexed_construction_reference_jpy"],
             "B59": asset["land_burden_jpy"],
             "B60": asset["listed_operating_hurdle_jpy"],
             "B61": asset["hurdle_per_visit_jpy"]}
    for col, scenario in zip("BCDE", result["visitors"]):
        for row, key in ((23, "gross_spend_jpy"), (26, "incremental_local_spend_jpy"),
                         (29, "gross_spend_10y_jpy"), (30, "gross_spend_horizon_jpy"),
                         (32, "gross_spend_pv_jpy"), (33, "horizon_visits")):
            cells[f"{col}{row}"] = scenario[key]
    for col, scenario in zip("BCD", result["innovation"]):
        cells[f"{col}39"] = scenario["annual_payroll_jpy"]
        cells[f"{col}40"] = scenario["payroll_10y_jpy"]
        cells[f"{col}41"] = scenario["payroll_30y_jpy"]
    return cells
