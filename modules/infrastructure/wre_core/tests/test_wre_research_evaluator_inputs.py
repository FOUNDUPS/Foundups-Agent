"""Qualify effective evaluator inputs using fixed synthetic local costs."""

import pytest

from modules.infrastructure.wre_core.src import wre_research_evaluator as evaluator
from modules.foundups.simulator.economics import agent_compute_costs as costs


def test_evaluator_consumes_cost_changes_with_identical_target(tmp_path, monkeypatch):
    target = tmp_path / "target.py"
    source = (
        b"AGENT_ALLOCATION = {'basic_search': 0.5, 'openclaw': 0.5}\n"
        b"AGENT_PREMIUM_MULTIPLIERS = {'basic_search': 1.0, 'openclaw': 2.0}\n"
    )
    target.write_bytes(source)
    table = evaluator.AGENT_INFRASTRUCTURE_COSTS
    assert table is costs.AGENT_INFRASTRUCTURE_COSTS
    original = dict(table)
    fields = ("compute_cost_usd", "compute_margin_usd", "roc_ratio")
    with monkeypatch.context() as fixture:
        fixture.setitem(table, "basic_search", costs.InfrastructureCost(0.002, 0, 0, 0, 0))
        fixture.setitem(table, "openclaw", costs.InfrastructureCost(0.004, 0, 0, 0, 0))
        baseline = evaluator.evaluate_target(target)
        # Fixed workload: 250,000 tasks at multiplier 1; 195,000 at multiplier 2.
        # Costs 500 + 780; only the latter produces margin, so ROC = 780 / 1280.
        assert tuple(baseline[k] for k in fields) == pytest.approx((1280, 780, 39 / 64))
        assert target.read_bytes() == source
        with monkeypatch.context() as changed:
            changed.setitem(table, "openclaw", costs.InfrastructureCost(0.008, 0, 0, 0, 0))
            alternate = evaluator.evaluate_target(target)
            # Only the second cost doubles: cost 500 + 1560, margin 1560.
            assert tuple(alternate[k] for k in fields) == pytest.approx((2060, 1560, 78 / 103))
            assert alternate["roc_ratio"] > baseline["roc_ratio"]
            assert target.read_bytes() == source
        assert evaluator.evaluate_target(target) == baseline
        assert target.read_bytes() == source
    assert table.keys() == original.keys()
    assert all(table[key] is value for key, value in original.items())
    assert table is costs.AGENT_INFRASTRUCTURE_COSTS
