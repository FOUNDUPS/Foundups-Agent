# -*- coding: utf-8 -*-
"""
WRE ROC Auto-Researcher Evaluator (WSP 48)

Read-only simulator harness that executes the sustainability model using the
agent mixtures and premium multipliers defined in wre_research_target.py.
"""

import sys
import json
import ast
from collections.abc import Mapping
from pathlib import Path

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


class ResearchSustainabilityCalculator(UnifiedSustainabilityCalculator):
    """
    Subclass of UnifiedSustainabilityCalculator that incorporates
    premium pricing multipliers and demand elasticity.
    """

    def __init__(self, multipliers, agent_allocation, *args, **kwargs):
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

            infra = AGENT_INFRASTRUCTURE_COSTS.get(agent_name)
            if infra:
                cost = task_count * infra.total_usd
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
        if not isinstance(item, (int, float)):
            return {}
        result[key] = float(item)
    return result


def evaluate_target(target_path: Path) -> dict:
    """
    Parse target constants from target_path and evaluate fitness.

    The target file is never imported or executed. This keeps the Phase 1
    dry-run research loop from turning a generated proposal into live code.
    """
    allocation, multipliers = load_target_config(target_path)

    # Validation guards
    if not allocation or not multipliers:
        return {
            "roc_ratio": 0.0,
            "is_roi_sustainable": False,
            "is_compute_positive": False,
            "fitness": -100.0,
            "error": "Missing AGENT_ALLOCATION or AGENT_PREMIUM_MULTIPLIERS",
        }

    # Sum of allocation check
    sum_alloc = sum(allocation.values())
    if abs(sum_alloc - 1.0) > 0.05:
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

    # Run simulation
    calc = ResearchSustainabilityCalculator(
        multipliers=multipliers,
        agent_allocation=allocation,
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
