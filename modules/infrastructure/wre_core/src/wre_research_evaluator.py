# -*- coding: utf-8 -*-
"""
WRE ROC Auto-Researcher Evaluator (WSP 48)

Read-only simulator harness that executes the sustainability model using the
agent mixtures and premium multipliers defined in wre_research_target.py.
"""

import sys
import json
import ast
import math
from collections.abc import Mapping
from inspect import signature
from pathlib import Path
from types import MappingProxyType

# Add repo root to sys.path if not present
REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from modules.foundups.simulator.economics.unified_sustainability import (
    UnifiedSustainabilityCalculator,
)
from modules.foundups.simulator.economics.agent_compute_costs import (
    AGENT_INFRASTRUCTURE_COSTS,
)
from modules.foundups.simulator.economics import unified_sustainability as economics


class ResearchSustainabilityCalculator(UnifiedSustainabilityCalculator):
    """
    Subclass of UnifiedSustainabilityCalculator that incorporates
    premium pricing multipliers and demand elasticity.
    """

    def __init__(self, multipliers, agent_allocation, *args, cost_catalog=None, **kwargs):
        self.cost_catalog = snapshot_cost_catalog(cost_catalog)
        super().__init__(*args, **kwargs)
        self.multipliers = multipliers
        self.agent_allocation = agent_allocation

    def calculate_compute_revenue(self, tasks_per_month, agent_mix=None):
        """
        Calculate compute cost and margin adjusting for premium multipliers
        and demand elasticity.
        """
        total_cost = 0.0
        total_revenue = 0.0

        # Normalize allocation
        alloc_sum = sum(self.agent_allocation.values())
        normalized_alloc = (
            {k: v / alloc_sum for k, v in self.agent_allocation.items()}
            if alloc_sum > 0
            else self.agent_allocation
        )

        for agent_name, fraction in normalized_alloc.items():
            m = self.multipliers.get(agent_name, 1.0)
            # Demand elasticity: task volume drops as multiplier increases
            # At 1.0 multiplier, factor is 1.0. At 5.0 multiplier, factor is 0.12.
            elasticity_factor = max(0.1, 1.0 - 0.22 * (m - 1.0))
            task_count = int(tasks_per_month * fraction * elasticity_factor)

            unit_cost = self.cost_catalog.get(agent_name)
            if unit_cost is not None:
                cost = task_count * unit_cost
                revenue = cost * m
                total_cost += cost
                total_revenue += revenue

                # Record in parent compute backing state
                self.compute_backing.record_task(
                    agent_name=agent_name,
                    cost_usd=cost,
                    fi_earned=task_count * 0.01,
                    task_count=task_count,
                )

        margin = total_revenue - total_cost
        return total_cost, margin


def load_target_config_from_source(source: str) -> tuple[dict[str, float], dict[str, float]]:
    """Extract target constants without executing target code."""

    tree = ast.parse(source)
    values: dict[str, object] = {}
    for node in tree.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if not isinstance(target, ast.Name):
            continue
        if target.id not in {"AGENT_ALLOCATION", "AGENT_PREMIUM_MULTIPLIERS"}:
            continue
        values[target.id] = ast.literal_eval(node.value)

    allocation = _coerce_metric_map(values.get("AGENT_ALLOCATION"))
    multipliers = _coerce_metric_map(values.get("AGENT_PREMIUM_MULTIPLIERS"))
    return allocation, multipliers


def load_target_config(target_path: Path) -> tuple[dict[str, float], dict[str, float]]:
    """Read and parse target constants without importing the file."""

    return load_target_config_from_source(target_path.read_text(encoding="utf-8"))


def _coerce_metric_map(value: object) -> dict[str, float]:
    if not isinstance(value, Mapping):
        return {}
    result: dict[str, float] = {}
    for key, item in value.items():
        if not isinstance(key, str):
            return {}
        if isinstance(item, bool) or not isinstance(item, (int, float)):
            return {}
        try:
            number = float(item)
        except (OverflowError, ValueError):
            return {}
        if not math.isfinite(number):
            return {}
        result[key] = number
    return result


def snapshot_cost_catalog(cost_catalog=None) -> Mapping:
    """Copy finite nonnegative unit totals; never retain mutable cost objects."""
    if cost_catalog is None:
        cost_catalog = {name: cost.total_usd for name, cost in AGENT_INFRASTRUCTURE_COSTS.items()}
    if not isinstance(cost_catalog, Mapping) or not cost_catalog:
        raise ValueError("cost catalog must be a nonempty mapping")
    captured = {}
    for name, value in cost_catalog.items():
        if not isinstance(name, str) or isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("cost catalog requires string names and numeric totals")
        try:
            total = float(value)
        except (OverflowError, ValueError) as error:
            raise ValueError("cost catalog totals must be finite and nonnegative") from error
        if not math.isfinite(total) or total < 0:
            raise ValueError("cost catalog totals must be finite and nonnegative")
        captured[name] = total
    return MappingProxyType(captured)


def _profile_number(value):
    """Keep primitive numeric values without losing integer precision."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("comparison basis requires numeric profile values")
    try:
        finite = math.isfinite(value)
    except (OverflowError, ValueError):
        finite = False
    if not finite:
        raise ValueError("comparison basis requires finite profile values")
    return value


def _profile_tiers(distribution):
    """Preserve consumed iteration order and distinguish absent tiers from zero."""
    if not isinstance(distribution, Mapping):
        raise ValueError("comparison basis requires a tier distribution mapping")
    rows = []
    for name, fraction in distribution.items():
        if not isinstance(name, str):
            raise ValueError("comparison basis requires string tier names")
        tier = economics.TIERS.get(name)
        rows.append([name, _profile_number(fraction),
                     _profile_number(tier.price_usd) if tier else None])
    return rows


def snapshot_comparison_basis() -> str:
    """Copy consumed ambient inputs for drift checks, not immutable execution.

    Costs have a separate frozen catalog. Definition-bound defaults are read from
    the actual methods; overridden or unused defaults are deliberately excluded.
    The JSON value is neither an authenticated oracle identity nor a receipt.
    """
    try:
        defaults = signature(UnifiedSustainabilityCalculator.calculate_sustainability).parameters
        constructor = signature(UnifiedSustainabilityCalculator.__init__).parameters
        angel = signature(UnifiedSustainabilityCalculator.calculate_angel_revenue).parameters
        distribution = defaults["tier_distribution"].default or economics.TIER_DISTRIBUTION
        values = {
            "schema": "wre_roc_comparison_v1",
            "tiers": _profile_tiers(distribution),
            "subscription_margin": _profile_number(economics.SUBSCRIPTION_GROSS_MARGIN),
            "angel": [_profile_number(getattr(economics.ANGEL_TIER, name))
                      for name in ("price_usd", "max_angels_per_opo", "opo_treasury_fee")],
            "angel_stake": _profile_number(angel["avg_opo_stake_usd"].default),
            "dex_fee": _profile_number(economics.FEE_RATES[economics.FeeType.DEX_TRADE]),
            "burn": _profile_number(constructor["monthly_burn_usd"].default),
            "sats_per_usd": _profile_number(economics.SATS_PER_USD),
            "activity": [_profile_number(defaults[name].default) for name in (
                "monthly_dex_volume_usd", "monthly_exits_usd", "monthly_creations_usd", "monthly_opos")],
        }
        return json.dumps(values, allow_nan=False, separators=(",", ":"))
    except (AttributeError, KeyError, TypeError) as error:
        raise ValueError("comparison basis cannot capture current profile") from error


def _check_comparison_basis(expected):
    if not isinstance(expected, str) or not expected:
        raise ValueError("comparison basis must be a nonempty captured string")
    if expected != snapshot_comparison_basis():
        raise ValueError("comparison basis drifted during this invocation")


def evaluate_target(target_path: Path, *, cost_catalog=None, comparison_basis=None) -> dict:
    """Optionally reject persistent profile drift before returning any metrics.

    Only None opts out for direct callers. Before/after sampling does not protect
    concurrent mutation or a transient change restored before the second check.
    """
    if comparison_basis is not None:
        _check_comparison_basis(comparison_basis)
    metrics = _evaluate_target(target_path, cost_catalog=cost_catalog)
    if comparison_basis is not None:
        _check_comparison_basis(comparison_basis)
    return metrics


def _evaluate_target(target_path: Path, *, cost_catalog=None) -> dict:
    """
    Parse target constants from target_path and evaluate fitness.

    The target file is never imported or executed. This keeps the Phase 1
    dry-run research loop from turning a generated proposal into live code.
    """
    allocation, multipliers = load_target_config(target_path)
    cost_catalog = snapshot_cost_catalog(cost_catalog)

    # Validation guards
    if not allocation or not multipliers:
        return {
            "roc_ratio": 0.0,
            "is_roi_sustainable": False,
            "is_compute_positive": False,
            "fitness": -100.0,
            "error": "Missing AGENT_ALLOCATION or AGENT_PREMIUM_MULTIPLIERS",
        }

    # Reject impossible mixtures before the simulator can reward negative costs.
    unknown_agents = (set(allocation) | set(multipliers)) - set(cost_catalog)
    invalid_fractions = any(value < 0.0 or value > 1.0 for value in allocation.values())
    if unknown_agents or invalid_fractions:
        return {
            "roc_ratio": 0.0,
            "is_roi_sustainable": False,
            "is_compute_positive": False,
            "fitness": -100.0,
            "error": (
                f"Unknown agent types: {', '.join(sorted(unknown_agents))}"
                if unknown_agents
                else "Allocation fractions must be in range [0.0, 1.0]"
            ),
        }

    # Sum of allocation check
    sum_alloc = sum(allocation.values())
    if not math.isclose(sum_alloc, 1.0, rel_tol=0.0, abs_tol=1e-9):
        # Penalize invalid configuration
        return {
            "roc_ratio": 0.0,
            "is_roi_sustainable": False,
            "is_compute_positive": False,
            "fitness": -50.0 - abs(sum_alloc - 1.0) * 100,
            "error": f"Allocation sum is {sum_alloc}, must be 1.0",
        }

    # Range check for multipliers
    for k, v in multipliers.items():
        if v < 1.0 or v > 5.0:
            return {
                "roc_ratio": 0.0,
                "is_roi_sustainable": False,
                "is_compute_positive": False,
                "fitness": -150.0,
                "error": f"Multiplier {k}={v} is out of bounds [1.0, 5.0]",
            }

    return _evaluate_config(allocation, multipliers, cost_catalog)


def _evaluate_config(allocation, multipliers, cost_catalog) -> dict:
    """Score a valid literal configuration against explicit captured unit costs."""
    calc = ResearchSustainabilityCalculator(
        multipliers=multipliers,
        agent_allocation=allocation,
        cost_catalog=cost_catalog,
    )

    # Calculate overall metrics using standard parameters
    metrics = calc.calculate_sustainability(
        total_subscribers=25_000,
        total_angels=200,
        tasks_per_month=500_000,
    )

    roc_ratio = metrics.roc_ratio
    is_roi = metrics.is_roi_sustainable
    is_compute = metrics.is_compute_positive

    # Calculate overall fitness score
    # Primary goal is to maximize ROC.
    # Secondary constraint: Must maintain ROI sustainability.
    fitness = roc_ratio
    if not is_roi:
        # Heavily penalize ROI failure to keep the agent in bounds
        fitness -= 5.0

    return {
        "roc_ratio": roc_ratio,
        "is_roi_sustainable": is_roi,
        "is_compute_positive": is_compute,
        "fitness": fitness,
        "monthly_margin_usd": metrics.sustainability_margin_usd,
        "total_revenue_usd": metrics.revenue.total_revenue_usd,
        "compute_cost_usd": metrics.revenue.compute_spend_usd,
        "compute_margin_usd": metrics.revenue.compute_margin_usd,
    }


if __name__ == "__main__":
    target_file = Path(__file__).parent / "wre_research_target.py"
    if not target_file.exists():
        print(json.dumps({"error": "wre_research_target.py not found"}, indent=2))
        sys.exit(1)
    
    try:
        results = evaluate_target(target_file)
        print(json.dumps(results, indent=2))
    except Exception as e:
        print(json.dumps({"error": str(e)}, indent=2))
        sys.exit(1)
