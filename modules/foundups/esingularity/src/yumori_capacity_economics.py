"""Simple 1-5 MW planning projection for the public finance interface.

This is intentionally a *planning linearization*, not a replacement for the
canonical project model or a bankable engineering forecast. It answers the
simple public question: if the current 1 MW scenario were repeated at 1-5 MW,
what order of magnitude of revenue, operating cost, EBITDA, and capital would
that imply?

All financial equations still originate from ``yumori_financial_model.py``.
Historical facility comparison values originate from ``yumori_facility_history``.

WSP: 3, 15, 22, 50, 84, 97.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Dict, Tuple

from .yumori_facility_history import load_facility_history
from .yumori_financial_model import calculate_model, default_assumptions
from .yumori_feasibility_finance import capacity_plan


@dataclass(frozen=True)
class CapacityEconomics:
    mw: int
    gpus: int
    eight_gpu_nodes: int
    estimated_project_cost_jpy: float
    year1_revenue_jpy: float
    year1_operating_cost_jpy: float
    year1_ebitda_jpy: float
    historic_fy2018_user_fee_revenue_coverage_x: float
    historic_fy2018_city_net_cost_coverage_x: float
    current_dormant_carrying_cost_coverage_x: float
    status: str
    scaling_rule: str

    def as_dict(self) -> Dict[str, object]:
        return asdict(self)


def capacity_economics(mw: int) -> CapacityEconomics:
    if mw not in range(1, 6):
        raise ValueError("Public planning capacity must be an integer from 1 to 5 MW")

    assumptions = default_assumptions()
    base = calculate_model(assumptions)
    y1 = base.years[0]
    plan = capacity_plan(float(mw))
    history = load_facility_history()
    fy2018 = next(row for row in history.operating_history if row.period == "FY2018")
    fy2018_city = next(row for row in history.city_fiscal_history if row.period == "FY2018")
    carrying = float(history.current_carrying_cost["known_annual_cost_jpy"])

    # Simple public-planning linearization. This deliberately does not imply
    # stepped utility upgrades, bulk-purchase savings, staffing economies, or a
    # proportional increase in usable recovered heat.
    revenue = y1.gross_revenue_jpy * mw
    operating_cost = (y1.total_cogs_jpy + y1.total_sga_jpy) * mw
    ebitda = revenue - operating_cost

    # Facility reuse/repair basis stays fixed; compute hardware scales linearly.
    # This is a model-only order-of-magnitude capital indicator.
    estimated_project_cost = assumptions.facility_capex_jpy + assumptions.compute_capex_jpy * mw

    return CapacityEconomics(
        mw=mw,
        gpus=plan.gpus,
        eight_gpu_nodes=plan.eight_gpu_nodes,
        estimated_project_cost_jpy=estimated_project_cost,
        year1_revenue_jpy=revenue,
        year1_operating_cost_jpy=operating_cost,
        year1_ebitda_jpy=ebitda,
        historic_fy2018_user_fee_revenue_coverage_x=(ebitda / fy2018.user_fee_revenue_jpy),
        historic_fy2018_city_net_cost_coverage_x=(ebitda / fy2018_city.city_net_cost_jpy),
        current_dormant_carrying_cost_coverage_x=(ebitda / carrying),
        status="MODEL ONLY / SIMPLE 1MW LINEARIZATION",
        scaling_rule=(
            "Revenue and modeled operating cost are linearly scaled from the current "
            "1 MW Year-1 scenario. Facility CapEx remains fixed while compute CapEx "
            "scales linearly. This does not model stepped grid/fiber/cooling upgrades, "
            "staffing economies, financing, or full reopened-onsen OPEX."
        ),
    )


def capacity_economics_table() -> Tuple[CapacityEconomics, ...]:
    return tuple(capacity_economics(mw) for mw in range(1, 6))
