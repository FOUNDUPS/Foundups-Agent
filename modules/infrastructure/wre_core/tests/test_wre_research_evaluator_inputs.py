"""Qualify effective evaluator inputs using fixed synthetic local costs."""

import csv
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from modules.infrastructure.wre_core.src import wre_research_evaluator as evaluator
from modules.foundups.simulator.economics import agent_compute_costs as costs
from modules.foundups.simulator.economics import unified_sustainability as economics
from modules.foundups.simulator.economics import subscription_tiers as subscriptions
from modules.foundups.simulator.economics import fee_revenue_tracker as fees
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


@pytest.mark.parametrize("change", ["stable", "replace", "mutate", "remove"])
def test_actual_loop_identical_candidate_uses_frozen_costs(tmp_path, monkeypatch, change):
    """Same candidate must not benefit from dependency-only cost changes."""
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
            if change == "replace":
                fixture.setitem(table, "openclaw", costs.InfrastructureCost(0.008, 0, 0, 0, 0))
            elif change == "mutate":
                fixture.setattr(table["openclaw"], "compute_usd", 0.008)
            elif change == "remove":
                fixture.delitem(table, "openclaw")
            return code

        fixture.setattr(researcher, "_propose_change", propose)
        report = researcher.run()
        assert calls == [source]
        _assert_comparison_artifacts(researcher, report, source, False)
        assert target.read_bytes() == source.encode("utf-8")
        assert program.read_bytes() == b"Fixed synthetic comparison; no provider.\n"
    assert table.keys() == original.keys()
    assert all(table[key] is value for key, value in original.items())
    assert table is costs.AGENT_INFRASTRUCTURE_COSTS


def _fixed_researcher(tmp_path, monkeypatch, iterations=1):
    target, program = tmp_path / "target.py", tmp_path / "program.md"
    target.write_text("AGENT_ALLOCATION = {'basic_search': 0.5, 'openclaw': 0.5}\n"
                      "AGENT_PREMIUM_MULTIPLIERS = {'basic_search': 1.0, 'openclaw': 2.0}\n")
    program.write_text("Fixed fixture")
    monkeypatch.setattr(researcher_module, "get_qwen_engine", lambda: None)
    monkeypatch.setitem(evaluator.AGENT_INFRASTRUCTURE_COSTS, "basic_search",
                        costs.InfrastructureCost(0.002, 0, 0, 0, 0))
    monkeypatch.setitem(evaluator.AGENT_INFRASTRUCTURE_COSTS, "openclaw",
                        costs.InfrastructureCost(0.004, 0, 0, 0, 0))
    return researcher_module.WREAutoResearcher(
        target, program, max_iterations=iterations, results_dir=tmp_path / "runs")


def test_cost_snapshot_copies_values_and_drives_real_evaluator(tmp_path, monkeypatch):
    researcher = _fixed_researcher(tmp_path, monkeypatch)
    source = {"basic_search": 0.002, "openclaw": 0.004}
    snapshot = evaluator.snapshot_cost_catalog(source)
    source["openclaw"] = 0.008
    with pytest.raises(TypeError):
        snapshot["openclaw"] = 0.1
    monkeypatch.setattr(evaluator.AGENT_INFRASTRUCTURE_COSTS["openclaw"], "compute_usd", 0.008)
    _assert_fixed_metrics(evaluator.evaluate_target(researcher.target_path, cost_catalog=snapshot), False)
    _assert_fixed_metrics(evaluator.evaluate_target(researcher.target_path), True)
    assert dict(snapshot) == {"basic_search": 0.002, "openclaw": 0.004}


@pytest.mark.parametrize("catalog", [False, [], {}, {1: 0.1}, {"openclaw": True},
                                     {"openclaw": "0.1"}, {"openclaw": -1},
                                     {"openclaw": float("nan")}, {"openclaw": float("inf")}])
def test_invalid_cost_catalog_cannot_fall_back_to_live_values(tmp_path, monkeypatch, catalog):
    researcher = _fixed_researcher(tmp_path, monkeypatch)
    with pytest.raises(ValueError, match="cost catalog"):
        evaluator.snapshot_cost_catalog(catalog)
    with pytest.raises(ValueError, match="cost catalog"):
        evaluator.evaluate_target(researcher.target_path, cost_catalog=catalog)


@pytest.mark.parametrize("bad_total", [True, -1, float("nan"), float("inf")])
def test_invalid_global_cost_aborts_with_report_and_cleanup(tmp_path, monkeypatch, bad_total):
    researcher = _fixed_researcher(tmp_path, monkeypatch)
    monkeypatch.setitem(evaluator.AGENT_INFRASTRUCTURE_COSTS, "openclaw",
                        SimpleNamespace(total_usd=bad_total))
    monkeypatch.setattr(researcher, "_propose_change", lambda *args: pytest.fail("proposal entered"))
    with pytest.raises(ValueError, match="cost catalog"):
        researcher.run()
    report = json.loads(next(researcher.results_dir.glob("invocation-*/report.json")).read_text())
    assert report["failure"] == {"type": "ValueError", "phase": "cost_capture"}
    assert report["status"] == "aborted" and report["cleanup"] == "restored"
    assert report["baseline_evaluations"] == report["candidate_evaluations"] == 0
    assert report["history"] == [] and report["optimized"] is None
    assert researcher.working_target_path.read_text() == researcher.original_code


def test_catalog_addition_does_not_enter_current_invocation(tmp_path, monkeypatch):
    researcher = _fixed_researcher(tmp_path, monkeypatch)
    def propose(code, *args):
        monkeypatch.setitem(evaluator.AGENT_INFRASTRUCTURE_COSTS, "new_agent",
                            costs.InfrastructureCost(0.004, 0, 0, 0, 0))
        return code.replace("openclaw", "new_agent")
    monkeypatch.setattr(researcher, "_propose_change", propose)
    report = researcher.run()
    assert report["history"] == [{"iteration": 1, "status": "failed_validation",
                                  "error": "Unknown agent types: new_agent"}]
    assert report["improvement"] == 0 and report["cleanup"] == "restored"


def test_later_invocations_refresh_costs_without_mutating_earlier_metrics(tmp_path, monkeypatch):
    first = _fixed_researcher(tmp_path, monkeypatch)
    second = researcher_module.WREAutoResearcher(
        first.target_path, first.program_path, max_iterations=0, results_dir=tmp_path / "runs")
    inner_reports = []
    def propose(code, *args):
        monkeypatch.setattr(evaluator.AGENT_INFRASTRUCTURE_COSTS["openclaw"], "compute_usd", 0.008)
        inner_reports.append(second.run())
        return code
    monkeypatch.setattr(first, "_propose_change", propose)
    initial = first.run()
    _assert_fixed_metrics(initial["baseline"], False)
    _assert_fixed_metrics(initial["optimized"], False)
    _assert_fixed_metrics(inner_reports[0]["baseline"], True)
    monkeypatch.setattr(first, "_propose_change", lambda code, *args: code)
    refreshed = first.run()
    _assert_fixed_metrics(refreshed["baseline"], True)
    assert initial["improvement"] == refreshed["improvement"] == 0
    assert initial["invocation_id"] != refreshed["invocation_id"]
    assert first.working_target_path.read_text() == first.original_code


def test_zero_cost_still_records_work_in_compute_backing():
    calc = evaluator.ResearchSustainabilityCalculator(
        {"basic_search": 1.0}, {"basic_search": 1.0}, cost_catalog={"basic_search": 0.0})
    assert calc.calculate_compute_revenue(10) == (0.0, 0.0)
    assert calc.compute_backing.total_tasks_executed == 10
    assert calc.compute_backing.total_fi_mined == pytest.approx(0.1)


# Fixed controls for persistent comparison-profile drift; ABA remains unguarded.
def _profile_researcher(tmp_path, monkeypatch):
    researcher = _fixed_researcher(tmp_path, monkeypatch)
    tiers = {"basic": SimpleNamespace(price_usd=1.0), "pro": SimpleNamespace(price_usd=2.0)}
    angel = SimpleNamespace(price_usd=10.0, max_angels_per_opo=2, opo_treasury_fee=0.1)
    rates = {fees.FeeType.DEX_TRADE: 0.01}
    for module in (economics, subscriptions):
        monkeypatch.setattr(module, "TIERS", tiers)
        monkeypatch.setattr(module, "ANGEL_TIER", angel)
    for module in (economics, fees):
        monkeypatch.setattr(module, "FEE_RATES", rates)
    monkeypatch.setattr(economics, "TIER_DISTRIBUTION", {"basic": 1.0, "pro": 0.0})
    monkeypatch.setattr(economics, "SUBSCRIPTION_GROSS_MARGIN", 0.5)
    monkeypatch.setattr(researcher.runner, "commit", lambda *a, **k: pytest.fail("live commit"))
    return researcher


def _assert_profile_metrics(metrics, revenue):
    assert set(metrics) == {"compute_cost_usd", "compute_margin_usd", "roc_ratio",
                            "total_revenue_usd", "monthly_margin_usd", "fitness",
                            "is_compute_positive", "is_roi_sustainable"}
    roi = revenue >= 27000
    fields = ("compute_cost_usd", "compute_margin_usd", "roc_ratio",
              "total_revenue_usd", "monthly_margin_usd", "fitness")
    assert tuple(metrics[k] for k in fields) == pytest.approx(
        (1280, 780, 39 / 64, revenue, revenue - 27000, 39 / 64 - (0 if roi else 5)))
    assert metrics["is_compute_positive"] is True
    assert metrics["is_roi_sustainable"] is roi


def _change_profile(monkeypatch, change):
    if change in ("price", "combined"):
        monkeypatch.setattr(economics.TIERS["basic"], "price_usd", 1.2)
    if change == "distribution":
        monkeypatch.setitem(economics.TIER_DISTRIBUTION, "basic", 0.98)
        monkeypatch.setitem(economics.TIER_DISTRIBUTION, "pro", 0.02)
    if change in ("margin", "combined", "downward"):
        monkeypatch.setattr(economics, "SUBSCRIPTION_GROSS_MARGIN", 0.5 if change == "downward" else 0.6)
    if change == "angel_price":
        monkeypatch.setattr(economics.ANGEL_TIER, "price_usd", 11.0)
    if change == "angel_limit":
        monkeypatch.setattr(economics.ANGEL_TIER, "max_angels_per_opo", 3)
    if change == "opo_fee":
        monkeypatch.setattr(economics.ANGEL_TIER, "opo_treasury_fee", 0.11)
    if change in ("dex_fee", "combined"):
        monkeypatch.setitem(economics.FEE_RATES, fees.FeeType.DEX_TRADE, 0.02)
    if change == "membership":
        monkeypatch.delitem(economics.TIERS, "basic")
    if change == "export_tiers":
        monkeypatch.setattr(subscriptions, "TIERS", {})
    if change == "export_angel":
        monkeypatch.setattr(subscriptions, "ANGEL_TIER", None)
    if change == "export_fees":
        monkeypatch.setattr(fees, "FEE_RATES", {})
    if change in ("bound_burn", "bound_btc", "unused_compute", "finite_sats"):
        attribute = {"bound_burn": "F0_MONTHLY_BURN_USD", "bound_btc": "BTC_PRICE_USD",
                     "unused_compute": "COMPUTE_GROSS_MARGIN", "finite_sats": "SATS_PER_USD"}[change]
        monkeypatch.setattr(economics, attribute, 1.0)


def _assert_profile_receipts(researcher, report, observed, baseline, candidate, drift):
    outcome = "crashed" if drift else "rejected"
    _assert_profile_metrics(report["baseline"], baseline)
    assert report["optimized"] == report["baseline"] and report["improvement"] == 0
    assert len(observed) == (1 if drift else 2)
    _assert_profile_metrics(observed[0], baseline)
    if drift:
        assert report["history"][0]["status"] == "crashed"
        assert "comparison basis" in report["history"][0]["error"]
    else:
        _assert_profile_metrics(observed[1], candidate)
        assert report["history"] == [{"iteration": 1, "status": outcome,
                                      "fitness": observed[1]["fitness"], "roc_ratio": 39 / 64}]
    assert report["outcome_counts"][outcome] == sum(report["outcome_counts"].values()) == 1
    assert [report[k] for k in ("attempts_requested", "attempts_started", "attempts_finished",
                               "baseline_evaluations", "candidate_evaluations")] == [1] * 5
    assert (report["status"], report["stop_reason"], report["cleanup"]) == (
        "completed", "attempt_limit", "restored")
    assert report["failure"] is report["cleanup_failure"] is None
    with researcher.results_path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    assert [r["status"] for r in rows] == ["baseline", outcome]
    assert float(rows[0]["fitness"]) == pytest.approx(observed[0]["fitness"], abs=1e-6)
    assert float(rows[0]["monthly_margin"]) == pytest.approx(baseline - 27000)
    if drift:
        assert all(rows[1][k] == "" for k in ("fitness", "roc_ratio", "monthly_margin"))
    else:
        assert float(rows[1]["fitness"]) == pytest.approx(observed[1]["fitness"], abs=1e-6)
        assert float(rows[1]["monthly_margin"]) == pytest.approx(candidate - 27000)
    _assert_profile_artifacts(researcher, report)


def _assert_profile_artifacts(researcher, report):
    digest = hashlib.sha256(researcher.original_code.encode()).hexdigest()
    assert report["baseline_input_sha256"] == digest
    assert report["proposal_inputs"] == [{"iteration": 1, "proposal_input_sha256": digest}]
    assert report["program_inputs"] == []
    assert researcher.program_path.read_text() == "Fixed fixture"
    assert all(report[k] is None for k in ("independently_verified", "retained_improvements", "resource_usage"))
    assert json.loads(Path(report["report_path"]).read_text(encoding="utf-8")) == report
    operations = researcher.runner.planned_operations
    assert [op["operation"] for op in operations] == ["restore", "restore"]
    assert all(op["no_execution_performed"] is True and op["path_digest"] == digest for op in operations)
    assert researcher.target_path.read_text() == researcher.working_target_path.read_text() == researcher.original_code


@pytest.mark.parametrize("change,baseline,candidate", [
    ("stable", 26830, 26830), ("price", 26830, 29330), ("distribution", 26830, 27080),
    ("margin", 26830, 29330), ("angel_price", 26830, 27030), ("angel_limit", 26830, 31830),
    ("opo_fee", 26830, 27830), ("dex_fee", 26830, 27330), ("combined", 26830, 32830),
    ("downward", 29330, 26830), ("membership", 26830, 14330),
    ("export_tiers", 26830, 26830), ("export_angel", 26830, 26830), ("export_fees", 26830, 26830),
    ("bound_burn", 26830, 26830), ("bound_btc", 26830, 26830),
    ("unused_compute", 26830, 26830), ("finite_sats", 26830, 26830),
])
def test_actual_loop_remaining_profile_changes_with_identical_text(tmp_path, monkeypatch, change, baseline, candidate):
    original = _profile_globals()
    with monkeypatch.context() as fixture:
        _run_profile_case(tmp_path, fixture, change, baseline, candidate)
    assert all(before is after for before, after in zip(original, _profile_globals()))


def _profile_globals():
    return tuple(getattr(module, name) for module, names in (
        (economics, ("TIERS", "ANGEL_TIER", "FEE_RATES", "TIER_DISTRIBUTION",
                     "SUBSCRIPTION_GROSS_MARGIN", "F0_MONTHLY_BURN_USD", "BTC_PRICE_USD",
                     "COMPUTE_GROSS_MARGIN", "SATS_PER_USD")),
        (subscriptions, ("TIERS", "ANGEL_TIER")), (fees, ("FEE_RATES",)),
    ) for name in names)


def _run_profile_case(tmp_path, monkeypatch, change, baseline, candidate):
    researcher = _profile_researcher(tmp_path, monkeypatch)
    if change == "downward":
        monkeypatch.setattr(economics, "SUBSCRIPTION_GROSS_MARGIN", 0.6)
    actual_evaluate, observed = researcher_module.evaluate_target, []
    def evaluate(path, **context):
        result = actual_evaluate(path, **context)
        observed.append(dict(result))
        return result
    def propose(code, metrics, history):
        assert code == researcher.original_code and history == []
        _assert_profile_metrics(metrics, baseline)
        _change_profile(monkeypatch, change)
        return code
    monkeypatch.setattr(researcher_module, "evaluate_target", evaluate)
    monkeypatch.setattr(researcher, "_propose_change", propose)
    report = researcher.run()
    drift = change not in {"stable", "export_tiers", "export_angel", "export_fees",
                           "bound_burn", "bound_btc", "unused_compute"}
    _assert_profile_receipts(researcher, report, observed, baseline, candidate, drift)

def test_empty_distribution_uses_live_fallback(tmp_path, monkeypatch):
    researcher = _profile_researcher(tmp_path, monkeypatch)
    calculator = evaluator.ResearchSustainabilityCalculator(
        {"basic_search": 1.0}, {"basic_search": 1.0})
    assert calculator.calculate_subscription_revenue(25000, {}) == (25000, 12500, 25000)
    monkeypatch.setattr(economics.TIERS["basic"], "price_usd", 1.2)
    assert calculator.calculate_subscription_revenue(25000, {}) == (30000, 15000, 25000)
    assert researcher.target_path.read_text() == researcher.original_code


@pytest.mark.parametrize("stage", ["baseline", "candidate"])
def test_invalid_sats_affects_failure_path_without_changing_target(tmp_path, monkeypatch, stage):
    researcher = _profile_researcher(tmp_path, monkeypatch)
    def propose(code, *args):
        monkeypatch.setattr(economics, "SATS_PER_USD", float("nan"))
        return code
    monkeypatch.setattr(researcher, "_propose_change", propose)
    if stage == "baseline":
        monkeypatch.setattr(economics, "SATS_PER_USD", float("nan"))
        with pytest.raises(ValueError, match="comparison basis"):
            researcher.run()
        report = json.loads(next(researcher.results_dir.glob("invocation-*/report.json")).read_text())
        assert report["status"] == "aborted" and report["history"] == []
        assert report["failure"] == {"type": "ValueError", "phase": "comparison_capture"}
        assert report["baseline_evaluations"] == report["candidate_evaluations"] == 0
    else:
        report = researcher.run()
        assert report["status"] == "completed" and report["failure"] is None
        assert report["history"][0]["status"] == "crashed"
        assert "comparison basis" in report["history"][0]["error"]
        assert report["outcome_counts"]["crashed"] == 1 and report["improvement"] == 0
        _assert_profile_metrics(report["baseline"], 26830)
        assert report["optimized"] == report["baseline"]
        assert report["baseline_evaluations"] == report["candidate_evaluations"] == 1
    assert report["cleanup"] == "restored" and report["cleanup_failure"] is None
    assert researcher.target_path.read_text() == researcher.working_target_path.read_text() == researcher.original_code



def test_stable_profile_accepts_real_candidate_improvement(tmp_path, monkeypatch):
    researcher = _profile_researcher(tmp_path, monkeypatch)
    candidate = researcher.original_code.replace("'openclaw': 2.0", "'openclaw': 3.0")
    assert candidate != researcher.original_code
    monkeypatch.setattr(researcher, "_propose_change", lambda *args: candidate)
    report = researcher.run()
    _assert_profile_metrics(report["baseline"], 26830)
    fields = ("compute_cost_usd", "compute_margin_usd", "roc_ratio", "total_revenue_usd",
              "monthly_margin_usd", "fitness")
    assert tuple(report["optimized"][k] for k in fields) == pytest.approx(
        (1060, 1120, 56 / 53, 27170, 170, 56 / 53))
    assert report["optimized"]["is_roi_sustainable"] is report["optimized"]["is_compute_positive"] is True
    assert report["improvement"] == pytest.approx(18477 / 3392)
    assert report["history"] == [{"iteration": 1, "status": "accepted", "fitness": 56 / 53, "roc_ratio": 56 / 53}]
    candidate_digest = hashlib.sha256(candidate.encode()).hexdigest()
    assert report["proposal_inputs"] == [{"iteration": 1, "proposal_input_sha256": candidate_digest}]
    assert report["baseline_input_sha256"] != candidate_digest
    operations = researcher.runner.planned_operations
    assert [op["operation"] for op in operations] == ["commit", "restore"]
    assert operations[0]["path_digest"] == candidate_digest
    assert all(op["no_execution_performed"] is True for op in operations)
    assert report["cleanup"] == "restored" and report["failure"] is None
    assert json.loads(Path(report["report_path"]).read_text(encoding="utf-8")) == report
    assert researcher.target_path.read_text() == researcher.working_target_path.read_text() == researcher.original_code


def test_basis_copies_ordered_profile_and_distinguishes_absence(tmp_path, monkeypatch):
    researcher = _profile_researcher(tmp_path, monkeypatch)
    basis = evaluator.snapshot_comparison_basis()
    assert isinstance(basis, str) and json.loads(basis)
    monkeypatch.setattr(economics, "TIER_DISTRIBUTION", {"pro": 0.0, "basic": 1.0})
    reordered = evaluator.snapshot_comparison_basis()
    assert reordered != basis
    monkeypatch.setattr(economics.TIERS["basic"], "price_usd", 0)
    zero = evaluator.snapshot_comparison_basis()
    monkeypatch.delitem(economics.TIERS, "basic")
    absent = evaluator.snapshot_comparison_basis()
    assert len({basis, reordered, zero, absent}) == 4
    with pytest.raises(ValueError, match="comparison basis"):
        evaluator.evaluate_target(researcher.target_path, comparison_basis=basis)


@pytest.mark.parametrize("basis", ["", False, {}, [], 0, "bogus"])
def test_explicit_invalid_basis_never_disables_guard(tmp_path, monkeypatch, basis):
    researcher = _profile_researcher(tmp_path, monkeypatch)
    with pytest.raises(ValueError, match="comparison basis"):
        evaluator.evaluate_target(researcher.target_path, comparison_basis=basis)


@pytest.mark.parametrize("restore_inside", [False, True])
def test_after_evaluation_check_and_explicit_aba_limit(tmp_path, monkeypatch, restore_inside):
    researcher = _profile_researcher(tmp_path, monkeypatch)
    actual, calls = evaluator._evaluate_config, []
    def evaluate(*args):
        calls.append(1)
        if len(calls) == 2:
            monkeypatch.setattr(economics, "SUBSCRIPTION_GROSS_MARGIN", 0.6)
        result = actual(*args)
        if restore_inside:
            monkeypatch.setattr(economics, "SUBSCRIPTION_GROSS_MARGIN", 0.5)
        return result
    monkeypatch.setattr(evaluator, "_evaluate_config", evaluate)
    monkeypatch.setattr(researcher, "_propose_change", lambda code, *args: code)
    report = researcher.run()
    assert len(calls) == 2
    assert report["history"][0]["status"] == ("accepted" if restore_inside else "crashed")
    assert report["improvement"] == (5 if restore_inside else 0)
    if not restore_inside:
        assert "comparison basis" in report["history"][0]["error"]
    # A transient change-and-restore escapes before/after sampling; never claim atomicity.
    assert report["cleanup"] == "restored" and report["failure"] is None
    assert researcher.target_path.read_text() == researcher.working_target_path.read_text() == researcher.original_code


def test_nested_and_later_invocations_refresh_profile_independently(tmp_path, monkeypatch):
    outer = _profile_researcher(tmp_path, monkeypatch)
    inner = researcher_module.WREAutoResearcher(
        outer.target_path, outer.program_path, max_iterations=0, results_dir=tmp_path / "inner")
    nested = []
    def propose(code, *args):
        monkeypatch.setattr(economics, "SUBSCRIPTION_GROSS_MARGIN", 0.6)
        nested.append(inner.run())
        return code
    monkeypatch.setattr(outer, "_propose_change", propose)
    initial = outer.run()
    _assert_profile_metrics(nested[0]["baseline"], 29330)
    _assert_profile_metrics(initial["baseline"], 26830)
    assert initial["history"][0]["status"] == "crashed" and initial["improvement"] == 0
    monkeypatch.setattr(outer, "_propose_change", lambda code, *args: code)
    later = outer.run()
    _assert_profile_metrics(later["baseline"], 29330)
    assert later["history"][0]["status"] == "rejected" and later["improvement"] == 0
    assert len({initial["invocation_id"], nested[0]["invocation_id"], later["invocation_id"]}) == 3
    assert all(r["cleanup"] == "restored" for r in (initial, nested[0], later))
    assert outer.working_target_path.read_text() == outer.original_code


@pytest.mark.parametrize("name", ["burn", "distribution", "dex", "exits", "creations", "opos", "stake"])
def test_consumed_definition_bound_defaults_are_guarded(tmp_path, monkeypatch, name):
    researcher = _profile_researcher(tmp_path, monkeypatch)
    cls = economics.UnifiedSustainabilityCalculator
    method = {"burn": cls.__init__, "stake": cls.calculate_angel_revenue}.get(
        name, cls.calculate_sustainability)
    basis = evaluator.snapshot_comparison_basis()
    values = list(method.__defaults__)
    index, value = {"burn": (0, 29000), "distribution": (-2, {"pro": 1.0}),
                    "dex": (3, 51000), "exits": (4, 11000), "creations": (5, 6000),
                    "opos": (6, 6), "stake": (1, 11000)}[name]
    values[index] = value
    monkeypatch.setattr(method, "__defaults__", tuple(values))
    assert evaluator.snapshot_comparison_basis() != basis
    with pytest.raises(ValueError, match="comparison basis"):
        evaluator.evaluate_target(researcher.target_path, comparison_basis=basis)
    # Omitting the guard retains the direct-call API and reads current effective defaults.
    assert "error" not in evaluator.evaluate_target(researcher.target_path)


def test_effective_distribution_precedence_and_empty_default_fallback(tmp_path, monkeypatch):
    researcher = _profile_researcher(tmp_path, monkeypatch)
    method = economics.UnifiedSustainabilityCalculator.calculate_sustainability
    defaults = list(method.__defaults__)
    defaults[-2] = {"pro": 1.0}
    monkeypatch.setattr(method, "__defaults__", tuple(defaults))
    basis = evaluator.snapshot_comparison_basis()
    metrics = evaluator.evaluate_target(researcher.target_path, comparison_basis=basis)
    monkeypatch.setattr(economics, "TIER_DISTRIBUTION", {"basic": 0.5})
    assert evaluator.snapshot_comparison_basis() == basis
    assert evaluator.evaluate_target(researcher.target_path, comparison_basis=basis) == metrics
    defaults[-2] = {}
    monkeypatch.setattr(method, "__defaults__", tuple(defaults))
    fallback = evaluator.snapshot_comparison_basis()
    assert fallback != basis
    monkeypatch.setitem(economics.TIER_DISTRIBUTION, "basic", 0.6)
    assert evaluator.snapshot_comparison_basis() != fallback


@pytest.mark.parametrize("value", [float("nan"), float("inf"), True, "0.5"])
def test_invalid_profile_capture_never_enters_evaluator(tmp_path, monkeypatch, value):
    researcher = _profile_researcher(tmp_path, monkeypatch)
    monkeypatch.setattr(economics, "SUBSCRIPTION_GROSS_MARGIN", value)
    with pytest.raises(ValueError, match="comparison basis"):
        researcher.run()
    report = json.loads(next(researcher.results_dir.glob("invocation-*/report.json")).read_text())
    assert report["failure"] == {"type": "ValueError", "phase": "comparison_capture"}
    assert report["baseline_evaluations"] == report["candidate_evaluations"] == 0
    assert report["history"] == [] and report["optimized"] is None
    assert report["status"] == "aborted" and report["cleanup"] == "restored"
    assert researcher.working_target_path.read_text() == researcher.original_code
