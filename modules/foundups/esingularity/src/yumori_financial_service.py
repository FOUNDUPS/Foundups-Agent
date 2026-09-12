"""Governed dynamic scenario service for the YUMORI financial model.

This is a transport-independent application layer for the future eSingularity
financial interface. Frontends may collect assumptions, but all accepted
scenario changes are applied to the canonical Python dataclasses and recalculated
through ``yumori_financial_model.calculate_model``.

No financial formula is reimplemented here. Unknown or structurally unsafe
fields fail closed.

WSP: 3, 15, 22, 50, 84, 95, 97, 109.
"""
from __future__ import annotations

from dataclasses import asdict, replace
from typing import Dict, Mapping, Sequence

from .yumori_financial_model import (
    DebtFacility,
    ModelAssumptions,
    RevenueTier,
    default_assumptions,
)
from .yumori_financial_snapshot import build_finance_snapshot

_ALLOWED_SCALAR_OVERRIDES = {
    "total_gpus",
    "it_power_kw",
    "total_site_power_kw",
    "pue",
    "electricity_tariff_jpy_per_kwh",
    "facility_capex_jpy",
    "compute_capex_jpy",
    "grants_jpy",
    "sponsor_equity_jpy",
    "compute_useful_life_years",
    "infrastructure_useful_life_years",
    "corporate_tax_rate",
    "discount_rate",
}
_ALLOWED_SCHEDULE_OVERRIDES = {
    "utilization",
    "thermal_revenue_jpy",
    "coolant_maintenance_jpy",
    "network_backhaul_jpy",
    "noc_labor_jpy",
    "management_admin_jpy",
    "academic_liaison_marketing_jpy",
    "insurance_security_jpy",
    "property_lease_jpy",
    "community_benefit_jpy",
    "working_capital_change_jpy",
    "maintenance_capex_jpy",
}
_ALLOWED_STRUCTURED_OVERRIDES = {"tier_prices", "tier_gpu_counts", "debts"}
_ALLOWED_OVERRIDES = (
    _ALLOWED_SCALAR_OVERRIDES
    | _ALLOWED_SCHEDULE_OVERRIDES
    | _ALLOWED_STRUCTURED_OVERRIDES
)


def scenario_input_contract() -> Dict[str, object]:
    """Describe the bounded fields accepted by ``calculate_scenario``."""
    return {
        "status": "MODEL ONLY / SCENARIO INPUTS",
        "scalar_fields": sorted(_ALLOWED_SCALAR_OVERRIDES),
        "schedule_fields": sorted(_ALLOWED_SCHEDULE_OVERRIDES),
        "structured_fields": {
            "tier_prices": "mapping[tier_key] -> JPY/GPU-hour",
            "tier_gpu_counts": "mapping[tier_key] -> integer GPUs",
            "debts": (
                "mapping[debt_key] -> optional principal_jpy, annual_rate, "
                "term_years overrides"
            ),
        },
        "truth_boundary": (
            "Changing a scenario input recalculates a model; it does not validate "
            "customer demand, vendor pricing, grid capacity, financing, or grants."
        ),
    }


def _as_numeric_tuple(name: str, values: object, horizon: int) -> tuple[float, ...]:
    if not isinstance(values, Sequence) or isinstance(values, (str, bytes)):
        raise ValueError(f"{name} must be a sequence of {horizon} numeric values")
    converted = tuple(float(value) for value in values)
    if len(converted) != horizon:
        raise ValueError(f"{name} must contain {horizon} values; got {len(converted)}")
    return converted


def _override_tiers(
    tiers: tuple[RevenueTier, ...],
    prices: object | None,
    gpu_counts: object | None,
) -> tuple[RevenueTier, ...]:
    price_map = {} if prices is None else prices
    gpu_map = {} if gpu_counts is None else gpu_counts
    if not isinstance(price_map, Mapping) or not isinstance(gpu_map, Mapping):
        raise ValueError("tier_prices and tier_gpu_counts must be mappings")
    known = {tier.key for tier in tiers}
    unknown = (set(price_map) | set(gpu_map)) - known
    if unknown:
        raise ValueError(f"Unknown revenue tier keys: {sorted(unknown)}")
    updated = []
    for tier in tiers:
        price = float(price_map.get(tier.key, tier.price_jpy_per_gpu_hour))
        gpu_count = int(gpu_map.get(tier.key, tier.gpu_count))
        if price < 0 or gpu_count < 0:
            raise ValueError(f"Tier {tier.key} price/GPU count cannot be negative")
        updated.append(
            replace(
                tier,
                price_jpy_per_gpu_hour=price,
                gpu_count=gpu_count,
                status="MODEL ONLY / SCENARIO OVERRIDE",
                source="dynamic scenario input",
            )
        )
    return tuple(updated)


def _override_debts(
    debts: tuple[DebtFacility, ...], overrides: object | None
) -> tuple[DebtFacility, ...]:
    override_map = {} if overrides is None else overrides
    if not isinstance(override_map, Mapping):
        raise ValueError("debts must be a mapping keyed by debt facility key")
    known = {debt.key for debt in debts}
    unknown = set(override_map) - known
    if unknown:
        raise ValueError(f"Unknown debt facility keys: {sorted(unknown)}")

    updated = []
    for debt in debts:
        change = override_map.get(debt.key, {})
        if not isinstance(change, Mapping):
            raise ValueError(f"Debt override for {debt.key} must be a mapping")
        allowed = {"principal_jpy", "annual_rate", "term_years"}
        unexpected = set(change) - allowed
        if unexpected:
            raise ValueError(
                f"Unsupported debt fields for {debt.key}: {sorted(unexpected)}"
            )
        principal = float(change.get("principal_jpy", debt.principal_jpy))
        rate = float(change.get("annual_rate", debt.annual_rate))
        term = int(change.get("term_years", debt.term_years))
        if principal < 0 or rate < 0 or term <= 0:
            raise ValueError(f"Invalid debt override for {debt.key}")
        updated.append(
            replace(
                debt,
                principal_jpy=principal,
                annual_rate=rate,
                term_years=term,
                status="MODEL ONLY / SCENARIO OVERRIDE",
                source="dynamic scenario input",
            )
        )
    return tuple(updated)


def apply_scenario_overrides(
    overrides: Mapping[str, object],
    base: ModelAssumptions | None = None,
) -> ModelAssumptions:
    """Apply a whitelisted set of scenario changes to canonical assumptions."""
    unknown = set(overrides) - _ALLOWED_OVERRIDES
    if unknown:
        raise ValueError(f"Unsupported scenario fields: {sorted(unknown)}")

    a = base or default_assumptions()
    horizon = len(a.years)
    changes: Dict[str, object] = {}

    for field in _ALLOWED_SCALAR_OVERRIDES:
        if field not in overrides:
            continue
        raw = overrides[field]
        if field in {"total_gpus", "compute_useful_life_years", "infrastructure_useful_life_years"}:
            value: object = int(raw)  # type: ignore[arg-type]
        else:
            value = float(raw)  # type: ignore[arg-type]
        changes[field] = value

    for field in _ALLOWED_SCHEDULE_OVERRIDES:
        if field in overrides:
            changes[field] = _as_numeric_tuple(field, overrides[field], horizon)

    tiers = _override_tiers(
        a.tiers,
        overrides.get("tier_prices"),
        overrides.get("tier_gpu_counts"),
    )
    if "tier_prices" in overrides or "tier_gpu_counts" in overrides:
        changes["tiers"] = tiers
        if "tier_gpu_counts" in overrides and "total_gpus" not in overrides:
            changes["total_gpus"] = sum(tier.gpu_count for tier in tiers)

    if "debts" in overrides:
        changes["debts"] = _override_debts(a.debts, overrides["debts"])

    updated = replace(a, **changes)
    # The canonical calculator performs the final fail-closed reconciliation
    # (GPU allocation sums, utilization bounds, site power envelope, horizons).
    return updated


def calculate_scenario(
    overrides: Mapping[str, object],
    base: ModelAssumptions | None = None,
) -> Dict[str, object]:
    """Return a website/API-ready snapshot calculated by canonical Python math."""
    assumptions = apply_scenario_overrides(overrides, base)
    snapshot = build_finance_snapshot(assumptions)
    snapshot["scenario"] = {
        "status": "MODEL ONLY / DYNAMIC SCENARIO",
        "overrides": dict(overrides),
        "input_contract": scenario_input_contract(),
        "resolved_assumptions": asdict(assumptions),
    }
    return snapshot
