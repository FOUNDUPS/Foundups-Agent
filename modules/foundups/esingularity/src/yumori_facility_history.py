"""Verified municipal-history read model for Sukatto Land Kuzuryu.

This module keeps City-published operating history, designated-management
finance, City fiscal burden, and closed-building carrying-cost evidence separate
from YUMORI project economics. It contains no project forecast equations.

WSP: 3, 15, 22, 50, 84, 97.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Dict, Tuple

HISTORY_SCHEMA_VERSION = "yumori.facility_history.v1"
_DEFAULT_PATH = Path(__file__).resolve().parents[1] / "data" / "finance" / "facility_history_v1.json"


@dataclass(frozen=True)
class OperatingHistoryRow:
    period: str
    period_label: str
    users: int
    lodging_users: int
    day_users: int
    user_fee_revenue_jpy: float
    evidence_status: str
    scope: str
    source_url: str


@dataclass(frozen=True)
class UsageOnlyRow:
    period: str
    period_label: str
    users: int
    lodging_users: int
    day_users: int
    user_fee_revenue_jpy: float | None
    evidence_status: str
    scope: str
    source_url: str


@dataclass(frozen=True)
class ManagementFinanceRow:
    period: str
    management_fee_jpy: float
    payment_to_city_jpy: float
    evidence_status: str
    scope: str
    source_url: str


@dataclass(frozen=True)
class CityFiscalRow:
    period: str
    city_revenue_jpy: float
    city_expenditure_jpy: float
    city_net_cost_jpy: float
    combined_users: int
    cost_per_user_jpy: float
    scope: str
    evidence_status: str
    source_url: str


@dataclass(frozen=True)
class FacilityHistory:
    schema_version: str
    facility: str
    as_of: str
    truth_boundary: str
    operating_history: Tuple[OperatingHistoryRow, ...]
    usage_only_history: Tuple[UsageOnlyRow, ...]
    management_finance_history: Tuple[ManagementFinanceRow, ...]
    city_fiscal_history: Tuple[CityFiscalRow, ...]
    current_carrying_cost: Dict[str, object]
    operator_cost_evidence: Dict[str, object]

    def as_dict(self) -> Dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "facility": self.facility,
            "as_of": self.as_of,
            "truth_boundary": self.truth_boundary,
            "operating_history": [row.__dict__ for row in self.operating_history],
            "usage_only_history": [row.__dict__ for row in self.usage_only_history],
            "management_finance_history": [row.__dict__ for row in self.management_finance_history],
            "city_fiscal_history": [row.__dict__ for row in self.city_fiscal_history],
            "current_carrying_cost": self.current_carrying_cost,
            "operator_cost_evidence": self.operator_cost_evidence,
        }


def load_facility_history(path: str | Path | None = None) -> FacilityHistory:
    source = Path(path) if path else _DEFAULT_PATH
    raw = json.loads(source.read_text(encoding="utf-8"))
    if raw.get("schema_version") != HISTORY_SCHEMA_VERSION:
        raise ValueError(f"Unsupported facility history schema: {raw.get('schema_version')}")

    operating = tuple(OperatingHistoryRow(**row) for row in raw["operating_history"])
    usage_only = tuple(UsageOnlyRow(**row) for row in raw.get("usage_only_history", ()))
    management = tuple(ManagementFinanceRow(**row) for row in raw.get("management_finance_history", ()))
    fiscal = tuple(CityFiscalRow(**row) for row in raw["city_fiscal_history"])

    if not operating or not fiscal:
        raise ValueError("Facility history requires operating and city-fiscal evidence")
    if any(row.user_fee_revenue_jpy < 0 or row.users < 0 for row in operating):
        raise ValueError("Operating history cannot contain negative users or revenue")
    if any(row.users < 0 for row in usage_only):
        raise ValueError("Usage-only history cannot contain negative users")
    if any(row.management_fee_jpy < 0 or row.payment_to_city_jpy < 0 for row in management):
        raise ValueError("Management finance history cannot contain negative values")
    for row in fiscal:
        expected = row.city_expenditure_jpy - row.city_revenue_jpy
        if abs(expected - row.city_net_cost_jpy) > 0.5:
            raise ValueError(f"City fiscal row does not reconcile: {row.period}")

    carrying = dict(raw["current_carrying_cost"])
    component_total = sum(float(v) for v in carrying["components"].values())
    if abs(component_total - float(carrying["known_annual_cost_jpy"])) > 0.5:
        raise ValueError("Current carrying-cost components do not reconcile")

    return FacilityHistory(
        schema_version=raw["schema_version"],
        facility=raw["facility"],
        as_of=raw["as_of"],
        truth_boundary=raw["truth_boundary"],
        operating_history=operating,
        usage_only_history=usage_only,
        management_finance_history=management,
        city_fiscal_history=fiscal,
        current_carrying_cost=carrying,
        operator_cost_evidence=dict(raw["operator_cost_evidence"]),
    )


def build_public_facility_history() -> Dict[str, object]:
    """Return the bounded public history block used by API/web projections."""
    history = load_facility_history()
    data = history.as_dict()
    data["accounting_rules"] = {
        "user_fee_revenue": "Historical facility customer revenue; not YUMORI forecast revenue.",
        "usage_only": "A published user count with no recovered fee-revenue figure remains usage-only; revenue is not interpolated.",
        "management_finance": "Designated-management fee/payment-to-City history is a funding/governance arrangement, not customer revenue or operator expense.",
        "city_net_cost": "City-side fiscal burden for Sukatto Land Kuzuryu + Sukoyaka Dome; not full operator OPEX.",
        "carrying_cost": "Dormant/closed-facility carrying-cost floor; excludes active-use staffing, repairs, and program operations.",
        "operator_opex_gap": "Do not infer reopened onsen OPEX until complete operating-expense evidence or a new operating budget is available."
    }
    return data
