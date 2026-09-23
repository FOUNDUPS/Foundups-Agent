"""Qualify effective evaluator inputs using fixed synthetic local costs."""

import csv
import hashlib
import json
from pathlib import Path

import pytest

from modules.infrastructure.wre_core.src import wre_research_evaluator as evaluator
from modules.foundups.simulator.economics import agent_compute_costs as costs
from modules.infrastructure.wre_core.src import wre_auto_researcher as researcher_module


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


def _assert_fixed_metrics(metrics, changed):
    """Independent arithmetic for the fixed workload, including the ROI gate."""
    expected = (2060, 1560, 78 / 103, 252047.5, 225047.5) if changed else (
        1280, 780, 39 / 64, 251267.5, 224267.5
    )
    fields = ("compute_cost_usd", "compute_margin_usd", "roc_ratio",
              "total_revenue_usd", "monthly_margin_usd")
    assert tuple(metrics[k] for k in fields) == pytest.approx(expected)
    assert metrics["is_roi_sustainable"] is True
    assert metrics["is_compute_positive"] is True
    assert metrics["fitness"] == pytest.approx(expected[2])  # No ROI penalty.


def _assert_comparison_artifacts(researcher, report, source, changed):
    outcome = "accepted" if changed else "rejected"
    digest = hashlib.sha256(source.encode("utf-8")).hexdigest()
    assert report["baseline_input_sha256"] == digest
    assert report["proposal_inputs"] == [{"iteration": 1, "proposal_input_sha256": digest}]
    assert (report["status"], report["stop_reason"], report["cleanup"]) == (
        "completed", "attempt_limit", "restored")
    assert report["failure"] is None and report["cleanup_failure"] is None
    assert [report[k] for k in ("attempts_requested", "attempts_started",
                               "attempts_finished", "baseline_evaluations",
                               "candidate_evaluations")] == [1] * 5
    _assert_fixed_metrics(report["baseline"], False)
    _assert_fixed_metrics(report["optimized"], changed)
    assert report["improvement"] == pytest.approx(975 / 6592 if changed else 0)
    assert report["history"] == [{"iteration": 1, "status": outcome,
                                  "fitness": report["optimized"]["fitness"],
                                  "roc_ratio": report["optimized"]["roc_ratio"]}]
    assert report["outcome_counts"][outcome] == sum(report["outcome_counts"].values()) == 1
    assert all(report[k] is None for k in (
        "independently_verified", "retained_improvements", "resource_usage"))
    assert report["program_inputs"] == []  # Deterministic callback, no backend call.
    assert json.loads(Path(report["report_path"]).read_text(encoding="utf-8")) == report
    with researcher.results_path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    assert [r["status"] for r in rows] == ["baseline", outcome]
    assert [r["iteration"] for r in rows] == ["0", "1"]
    assert [float(r["fitness"]) for r in rows] == pytest.approx(
        [39 / 64, 78 / 103 if changed else 39 / 64], abs=1e-6)
    assert [float(r["roc_ratio"]) for r in rows] == pytest.approx(
        [39 / 64, 78 / 103 if changed else 39 / 64], abs=1e-6)
    assert [float(r["monthly_margin"]) for r in rows] == pytest.approx(
        [224267.5, 225047.5 if changed else 224267.5])
    operations = researcher.runner.planned_operations
    assert [op["operation"] for op in operations] == (
        ["commit", "restore"] if changed else ["restore", "restore"])
    assert all(op["no_execution_performed"] is True for op in operations)
    assert all(op["path_digest"] == digest for op in operations)
    assert researcher.working_target_path.read_text(encoding="utf-8") == source


@pytest.mark.parametrize("changed", [False, True], ids=["stable_cost", "changed_cost"])
def test_actual_loop_identical_candidate_comparison_observation(tmp_path, monkeypatch, changed):
    """Characterize current comparison; acceptance is not retained improvement."""
    source = (
        "AGENT_ALLOCATION = {'basic_search': 0.5, 'openclaw': 0.5}\n"
        "AGENT_PREMIUM_MULTIPLIERS = {'basic_search': 1.0, 'openclaw': 2.0}\n"
    )
    target, program = tmp_path / "target.py", tmp_path / "program.md"
    target.write_bytes(source.encode("utf-8"))
    program.write_bytes(b"Fixed synthetic comparison; no provider.\n")
    table, original = evaluator.AGENT_INFRASTRUCTURE_COSTS, dict(evaluator.AGENT_INFRASTRUCTURE_COSTS)
    with monkeypatch.context() as fixture:
        fixture.setattr(researcher_module, "get_qwen_engine", lambda: None)
        fixture.setitem(table, "basic_search", costs.InfrastructureCost(0.002, 0, 0, 0, 0))
        fixture.setitem(table, "openclaw", costs.InfrastructureCost(0.004, 0, 0, 0, 0))
        researcher = researcher_module.WREAutoResearcher(
            target, program, max_iterations=1, dry_run=True, results_dir=tmp_path / "results")
        calls = []

        def forbid_live_commit(*args, **kwargs):
            calls.append("forbidden_live_commit")
            raise AssertionError("Dry-run must never delegate runner.commit")

        fixture.setattr(researcher.runner, "commit", forbid_live_commit)

        def propose(code, metrics, history):
            assert code == source and history == []
            _assert_fixed_metrics(metrics, False)
            calls.append(code)
            if changed:
                fixture.setitem(table, "openclaw", costs.InfrastructureCost(0.008, 0, 0, 0, 0))
            return code

        fixture.setattr(researcher, "_propose_change", propose)
        report = researcher.run()
        assert calls == [source]
        _assert_comparison_artifacts(researcher, report, source, changed)
        assert target.read_bytes() == source.encode("utf-8")
        assert program.read_bytes() == b"Fixed synthetic comparison; no provider.\n"
    assert table.keys() == original.keys()
    assert all(table[key] is value for key, value in original.items())
    assert table is costs.AGENT_INFRASTRUCTURE_COSTS
