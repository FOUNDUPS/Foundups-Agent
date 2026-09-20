# -*- coding: utf-8 -*-
"""
WRE ROC Auto-Researcher Tests (WSP 48)
Slice Name: WRE_AUTORESEARCH_GIT_RUNNER_CONTRACT_PHASE1

Verifies the Auto-Researcher contract loop, AST denylist violations,
dry-run safety, path write protection, and fail-closed SPECIFIED_NOT_IMPLEMENTED behavior.
"""

import ast
import csv
import hashlib
import json
import math
import os
import sys
import shutil
import pytest
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier

# Add repo root to sys.path
REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from modules.infrastructure.wre_core.src.wre_research_evaluator import evaluate_target
from modules.infrastructure.wre_core.src import wre_auto_researcher as researcher_module
from modules.infrastructure.wre_core.src.wre_auto_researcher import WREAutoResearcher, DryRunGitRunner


@pytest.fixture
def temp_research_env(tmp_path, monkeypatch):
    """Fixture to create temporary target and program files."""
    # Disable model construction before initialization, not after it has occurred.
    monkeypatch.setattr(
        "modules.infrastructure.wre_core.src.wre_auto_researcher.get_qwen_engine",
        lambda: None,
    )
    target_src = Path(REPO_ROOT) / "modules" / "infrastructure" / "wre_core" / "src" / "wre_research_target.py"
    program_src = Path(REPO_ROOT) / "modules" / "infrastructure" / "wre_core" / "src" / "wre_research_program.md"

    temp_target = tmp_path / "wre_research_target.py"
    temp_program = tmp_path / "wre_research_program.md"

    # Copy files to temp directory
    shutil.copy(target_src, temp_target)
    shutil.copy(program_src, temp_program)

    return temp_target, temp_program


def test_ast_denylist_for_execution():
    """
    AST denylist: the researcher and evaluator do not import shell helpers,
    execute target code, or call direct shell command APIs.
    """
    src_files = [
        Path(REPO_ROOT) / "modules" / "infrastructure" / "wre_core" / "src" / "wre_auto_researcher.py",
        Path(REPO_ROOT) / "modules" / "infrastructure" / "wre_core" / "src" / "wre_research_evaluator.py",
    ]

    banned_imports = {"subprocess", "importlib"}
    banned_direct_calls = {"system", "popen", "Popen", "call", "check_output", "check_call", "eval", "exec"}
    banned_module_methods = {"run", "Popen", "call", "check_output", "check_call", "system", "popen"}

    for src_file in src_files:
        tree = ast.parse(src_file.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for name in node.names:
                    assert name.name not in banned_imports, f"Banned import '{name.name}' found in {src_file.name}."

            if isinstance(node, ast.ImportFrom):
                assert node.module not in banned_imports, f"Banned import from '{node.module}' found in {src_file.name}."

            if isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Name):
                    assert func.id not in banned_direct_calls, f"Banned direct call to '{func.id}' found."
                elif isinstance(func, ast.Attribute):
                    if src_file.name == "wre_auto_researcher.py":
                        assert func.attr != "commit", "Phase 1 must not delegate a live commit."
                    if isinstance(func.value, ast.Name) and func.value.id in {"subprocess", "os"}:
                        message = f"Banned method call to '{func.value.id}.{func.attr}' found."
                        assert func.attr not in banned_module_methods, message


def test_evaluator_valid_target(temp_research_env):
    """Verify the evaluator correctly computes metrics on a valid target."""
    target_path, _ = temp_research_env
    metrics = evaluate_target(target_path)

    assert "roc_ratio" in metrics
    assert "is_roi_sustainable" in metrics
    assert "fitness" in metrics
    assert "error" not in metrics
    assert metrics["roc_ratio"] > 0.0


@pytest.mark.parametrize("allocation,multipliers", [
    ("{'basic_search': -0.5, 'openclaw': 1.5}", "{'basic_search': 1.0, 'openclaw': 5.0}"),
    ("{'basic_search': 1.025}", "{'basic_search': 2.0}"),
    ("{'basic_search': 0.52, 'openclaw': 0.52}", "{'basic_search': 2.0}"),
    ("{'basic_search': 0.48, 'openclaw': 0.48}", "{'basic_search': 2.0}"),
    ("{'basic_search': True}", "{'basic_search': 2.0}"),
    ("{'basic_search': '1.0'}", "{'basic_search': 2.0}"),
    ("{'basic_search': 1e309}", "{'basic_search': 2.0}"),
    ("{'basic_search': -1e309}", "{'basic_search': 2.0}"),
    ("{'basic_search': " + "1" + "0" * 350 + "}", "{'basic_search': 2.0}"),
    ("{'unregistered_agent': 1.0}", "{'unregistered_agent': 2.0}"),
    ("{'basic_search': 1.0}", "{'basic_search': True}"),
    ("{'basic_search': 1.0}", "{'basic_search': '2.0'}"),
    ("{'basic_search': 1.0}", "{'basic_search': 1e309}"),
    ("{'basic_search': 1.0}", "{'basic_search': -1.0}"),
    ("{'basic_search': 1.0}", "{'basic_search': 5.1}"),
    ("{'basic_search': 1.0}", "{'unregistered_agent': 2.0}"),
])
def test_evaluator_rejects_invalid_input_before_simulation(
    tmp_path, monkeypatch, allocation, multipliers
):
    target = tmp_path / "invalid_target.py"
    target.write_text(
        f"AGENT_ALLOCATION = {allocation}\nAGENT_PREMIUM_MULTIPLIERS = {multipliers}\n",
        encoding="utf-8",
    )

    def unexpected_simulation(*args, **kwargs):
        pytest.fail("Invalid candidate reached the simulator")

    monkeypatch.setattr(
        "modules.infrastructure.wre_core.src.wre_research_evaluator.ResearchSustainabilityCalculator",
        unexpected_simulation,
    )
    metrics = evaluate_target(target)
    assert "error" in metrics
    assert math.isfinite(metrics["fitness"]) and metrics["fitness"] < 0
    assert metrics["is_compute_positive"] is False
    assert metrics["is_roi_sustainable"] is False


@pytest.mark.parametrize("multiplier,expected_roc", [(1, 0.0), (5.0, 4.0)])
def test_evaluator_keeps_valid_numeric_boundaries(tmp_path, multiplier, expected_roc):
    target = tmp_path / "valid_target.py"
    target.write_text(
        "AGENT_ALLOCATION = {'basic_search': 1, 'openclaw': 0.0}\n"
        f"AGENT_PREMIUM_MULTIPLIERS = {{'basic_search': {multiplier!r}}}\n",
        encoding="utf-8",
    )
    metrics = evaluate_target(target)
    assert "error" not in metrics
    assert metrics["roc_ratio"] == pytest.approx(expected_roc)
    assert math.isfinite(metrics["fitness"])


def test_auto_researcher_rejects_impossible_allocation(temp_research_env, tmp_path, monkeypatch):
    target_path, program_path = temp_research_env
    original_code = target_path.read_text(encoding="utf-8")
    runner = DryRunGitRunner()
    researcher = WREAutoResearcher(
        target_path, program_path, max_iterations=1,
        runner=runner, results_dir=tmp_path / "invalid_candidate_run",
    )
    # This candidate previously scored 4.116 versus the valid baseline's 1.043.
    monkeypatch.setattr(
        researcher, "_propose_change",
        lambda *args: (
            "AGENT_ALLOCATION = {'basic_search': -0.5, 'openclaw': 1.5}\n"
            "AGENT_PREMIUM_MULTIPLIERS = {'basic_search': 1.0, 'openclaw': 5.0}\n"
        ),
    )
    result = researcher.run()
    assert result["history"][0]["status"] == "failed_validation"
    assert result["optimized"] == result["baseline"]
    assert result["improvement"] == 0.0
    assert not any(op["operation"] == "commit" for op in runner.planned_operations)
    assert target_path.read_text(encoding="utf-8") == original_code
    assert researcher.working_target_path.read_text(encoding="utf-8") == original_code


def test_evaluator_does_not_execute_target_code(tmp_path):
    """Target parsing is literal-only; import side effects must not run."""
    marker = tmp_path / "side_effect.txt"
    target = tmp_path / "malicious_target.py"
    target.write_text(
        f"""# -*- coding: utf-8 -*-
from pathlib import Path
Path({str(marker)!r}).write_text("executed", encoding="utf-8")

AGENT_ALLOCATION = {{
    "basic_search": 0.30,
    "openclaw_lite": 0.25,
    "openclaw": 0.25,
    "gotjunk_browse": 0.10,
    "gotjunk": 0.05,
    "cabr_validator": 0.05,
}}

AGENT_PREMIUM_MULTIPLIERS = {{
    "basic_search": 1.5,
    "openclaw_lite": 1.8,
    "openclaw": 2.0,
    "gotjunk_browse": 1.2,
    "gotjunk": 2.2,
    "cabr_validator": 2.5,
}}
""",
        encoding="utf-8",
    )

    metrics = evaluate_target(target)

    assert "error" not in metrics
    assert marker.exists() is False


def test_auto_researcher_dry_run_contract(temp_research_env, tmp_path):
    """Verify that in dry-run mode, DryRunGitRunner records structured operations and no live mutation occurs."""
    target_path, program_path = temp_research_env
    
    # Store initial modification time of template target
    initial_mtime = target_path.stat().st_mtime
    original_code = target_path.read_text(encoding="utf-8")

    runner = DryRunGitRunner()
    results_dir = tmp_path / "runs"

    researcher = WREAutoResearcher(
        target_path=target_path,
        program_path=program_path,
        max_iterations=2,
        dry_run=True,
        runner=runner,
        results_dir=results_dir,
    )
    # Use heuristic fallback
    researcher.llm = None
    results = researcher.run()

    # Verify no mutation on original file and structured operations recorded
    assert results["dry_run"] is True
    assert len(runner.planned_operations) > 0
    
    # Assert commands are structured operations dictionaries
    for op in runner.planned_operations:
        assert isinstance(op, dict)
        assert "operation" in op
        assert "relative_path" in op
        assert "path_digest" in op
        assert op["no_execution_performed"] is True

    # Ensure source template file was NEVER written to (mtime untouched and content unchanged)
    assert target_path.stat().st_mtime == initial_mtime
    assert target_path.read_text(encoding="utf-8") == original_code

    # Check that the modified files only exist in the sandboxed runs folder
    working_file = researcher.working_target_path
    assert researcher.results_dir.parent == results_dir.resolve()
    assert working_file.parent.parent == researcher.results_dir
    assert working_file.exists()


def test_repo_source_isolation_block(temp_research_env, tmp_path, monkeypatch):
    """Verify WSP_97 path protection block when target_path resolves under REPO_ROOT."""
    target_path, program_path = temp_research_env

    # Point results_dir to be under REPO_ROOT to trigger PermissionError
    isolated_repo = tmp_path / "repo"
    isolated_repo.mkdir()
    monkeypatch.setattr(researcher_module, "REPO_ROOT", isolated_repo)
    repo_results_dir = isolated_repo / "sandbox_test"

    with pytest.raises(PermissionError) as exc_info:
        WREAutoResearcher(
            target_path=target_path,
            program_path=program_path,
            max_iterations=1,
            dry_run=True,
            results_dir=repo_results_dir,
        )

    assert "strictly prohibited" in str(exc_info.value)
    assert not repo_results_dir.exists()


def test_results_tsv_path_isolation(temp_research_env, tmp_path, capsys):
    """Verify results.tsv is written inside the custom directory, not in repo source."""
    target_path, program_path = temp_research_env
    results_dir = tmp_path / "sandbox_runs"

    researcher = WREAutoResearcher(
        target_path=target_path,
        program_path=program_path,
        max_iterations=1,
        dry_run=True,
        results_dir=results_dir,
    )
    researcher.llm = None
    researcher.run()

    # The requested directory is a parent; this invocation owns a unique run.
    expected_file = researcher.results_path
    assert researcher.results_dir.parent == results_dir.resolve()
    assert expected_file.parent == researcher.results_dir
    assert expected_file.exists()
    assert "timestamp" in expected_file.read_text(encoding="utf-8")
    assert str(expected_file) in capsys.readouterr().out

    # Ensure no results.tsv was written to repo source folder
    source_results = Path(REPO_ROOT) / "modules" / "infrastructure" / "wre_core" / "src" / "results.tsv"
    assert not source_results.exists()


def _assert_interrupted_report(researcher, phase, error_type):
    report = json.loads(next(researcher.results_dir.glob("invocation-*/report.json")).read_text())
    completed = phase == "evaluation" and error_type is RuntimeError
    assert report["status"] == ("completed" if completed else "aborted")
    assert report["cleanup"] == "restored"
    assert report["attempts_started"] == (2 if phase == "later_proposal" else int(phase != "baseline"))
    assert report["attempts_finished"] == int(completed or phase == "later_proposal")
    assert report["outcome_counts"]["no_proposal"] == int(phase == "later_proposal")
    assert report["baseline_evaluations"] == 1
    assert report["candidate_evaluations"] == int(phase == "evaluation")


@pytest.mark.parametrize("phase", ["baseline", "proposal", "diff", "evaluation", "later_proposal"])
@pytest.mark.parametrize("error_type", [RuntimeError, KeyboardInterrupt])
def test_dry_run_restores_after_diff_interruption(temp_research_env, tmp_path, monkeypatch, error_type, phase):
    target_path, program_path = temp_research_env
    original_code = target_path.read_text(encoding="utf-8")
    runner = DryRunGitRunner()
    researcher = WREAutoResearcher(
        target_path, program_path, max_iterations=2 if phase == "later_proposal" else 1,
        runner=runner, results_dir=tmp_path / "interrupted_run",
    )
    monkeypatch.setattr(researcher, "_propose_change", lambda *args: original_code + "\n# candidate\n")

    proposals = []
    def interrupted_diff(*args):
        if phase == "later_proposal" and not proposals:
            proposals.append(None)
            return None
        raise error_type("interrupted diff")

    if phase in ("baseline", "evaluation"):
        actual_evaluate = researcher_module.evaluate_target
        calls = []
        def evaluate(path):
            calls.append(path)
            if phase == "baseline" or len(calls) > 1:
                interrupted_diff()
            return actual_evaluate(path)
        monkeypatch.setattr(researcher_module, "evaluate_target", evaluate)
    else:
        monkeypatch.setattr(runner if phase == "diff" else researcher,
                            "diff" if phase == "diff" else "_propose_change", interrupted_diff)
    # Ordinary evaluator exceptions are handled as crashed outcomes, not aborts.
    if phase == "evaluation" and error_type is RuntimeError:
        result = researcher.run()
        assert result["outcome_counts"]["crashed"] == 1
    else:
        with pytest.raises(error_type, match="interrupted diff"):
            researcher.run()
    _assert_interrupted_report(researcher, phase, error_type)
    assert researcher.working_target_path.read_text(encoding="utf-8") == original_code
    assert target_path.read_text(encoding="utf-8") == original_code
    assert not any(op["operation"] == "commit" for op in runner.planned_operations)


@pytest.mark.parametrize("cleanup_fault", ["runner", "output"])
def test_dry_run_restores_local_copy_when_cleanup_dependencies_fail(
    temp_research_env, tmp_path, monkeypatch, cleanup_fault
):
    target_path, program_path = temp_research_env
    original_code = target_path.read_text(encoding="utf-8")
    runner = DryRunGitRunner()
    researcher = WREAutoResearcher(
        target_path, program_path, max_iterations=1,
        runner=runner, results_dir=tmp_path / "failed_restore_run",
    )
    monkeypatch.setattr(researcher, "_propose_change", lambda *args: original_code + "\n# candidate\n")

    def interrupted_diff(*args):
        raise RuntimeError("interrupted diff")

    def failed_restore(*args):
        raise RuntimeError("runner restore failed")

    monkeypatch.setattr(runner, "diff", interrupted_diff)
    if cleanup_fault == "runner":
        monkeypatch.setattr(runner, "restore", failed_restore)
        error_type, message = RuntimeError, "runner restore failed"
    else:
        import builtins
        original_print = builtins.print

        def failed_cleanup_output(*args, **kwargs):
            if args and str(args[0]).startswith("\n[SAFETY]"):
                raise BrokenPipeError("cleanup output failed")
            return original_print(*args, **kwargs)

        monkeypatch.setattr(builtins, "print", failed_cleanup_output)
        error_type, message = BrokenPipeError, "cleanup output failed"
    with pytest.raises(error_type, match=message) as caught:
        researcher.run()
    assert "interrupted diff" in str(caught.value.__context__)
    assert researcher.working_target_path.read_text(encoding="utf-8") == original_code
    assert target_path.read_text(encoding="utf-8") == original_code
    report = json.loads(next(researcher.results_dir.glob("invocation-*/report.json")).read_text())
    assert report["status"] == "aborted" and report["failure"]["type"] == "RuntimeError"
    assert report["cleanup"] == ("failed" if cleanup_fault == "runner" else "restored")
    assert report["cleanup_failure"]["type"] == error_type.__name__


def test_invalid_baseline_stops_before_proposal(temp_research_env, tmp_path, monkeypatch):
    target_path, program_path = temp_research_env
    invalid_source = (
        "AGENT_ALLOCATION = {'basic_search': -0.5, 'openclaw': 1.5}\n"
        "AGENT_PREMIUM_MULTIPLIERS = {'basic_search': 1.0, 'openclaw': 5.0}\n"
    )
    target_path.write_text(invalid_source, encoding="utf-8")
    researcher = WREAutoResearcher(
        target_path, program_path, max_iterations=1,
        results_dir=tmp_path / "invalid_baseline_run",
    )

    def unexpected_proposal(*args):
        pytest.fail("Invalid baseline reached proposal generation")

    monkeypatch.setattr(researcher, "_propose_change", unexpected_proposal)
    with pytest.raises(ValueError, match="Baseline validation failed"):
        researcher.run()
    assert researcher.working_target_path.read_text(encoding="utf-8") == invalid_source
    assert not any(op["operation"] == "commit" for op in researcher.runner.planned_operations)
    report = json.loads(next(researcher.results_dir.glob("invocation-*/report.json")).read_text())
    assert report["status"] == "aborted" and report["attempts_started"] == 0
    assert report["improvement"] is None and report["optimized"] is None


@pytest.mark.parametrize("mode", [False, None, 0, 1, "true", [], {}])
def test_commit_mode_fail_closed(temp_research_env, tmp_path, mode):
    """Verify commit/live mode is fail-closed, raising SPECIFIED_NOT_IMPLEMENTED."""
    target_path, program_path = temp_research_env
    results_dir = tmp_path / "runs"

    # Only the literal dry-run mode is implemented; truthy values cannot admit it.
    with pytest.raises(NotImplementedError) as exc_info:
        WREAutoResearcher(
            target_path=target_path,
            program_path=program_path,
            max_iterations=1,
            dry_run=mode,
            runner=DryRunGitRunner(),
            results_dir=results_dir,
        )
    
    assert "SPECIFIED_NOT_IMPLEMENTED" in str(exc_info.value)
    assert not results_dir.exists()


@pytest.mark.parametrize("use_default", [False, True], ids=["explicit-parent", "default-parent"])
def test_overlapping_research_runs_preserve_each_others_files(temp_research_env, tmp_path, monkeypatch, use_default):
    target, program = temp_research_env
    original = target.read_text(encoding="utf-8")
    original_mtime = target.stat().st_mtime_ns
    monkeypatch.setattr(researcher_module.tempfile, "gettempdir", lambda: str(tmp_path / "default-temp"))
    options = {} if use_default else {"results_dir": tmp_path / "runs"}
    first = WREAutoResearcher(target, program, max_iterations=0, **options)
    first_proposal = "# first proposal\n" + original
    first.working_target_path.write_text(first_proposal, encoding="utf-8")
    first._log_to_tsv(7, "first_only", {}, "first")
    first_log = first.results_path.read_bytes()
    second = WREAutoResearcher(target, program, max_iterations=0, **options)
    assert first.working_target_path.read_text(encoding="utf-8") == first_proposal
    assert first.results_path.read_bytes() == first_log
    assert first.results_dir != second.results_dir
    assert first.results_dir.parent == second.results_dir.parent
    second_proposal = "# second proposal\n" + original
    second.working_target_path.write_text(second_proposal, encoding="utf-8")
    second._log_to_tsv(8, "second_only", {}, "second")
    second_log = second.results_path.read_bytes()
    first.run()
    assert second.working_target_path.read_text(encoding="utf-8") == second_proposal
    assert second.results_path.read_bytes() == second_log
    assert "second_only" not in first.results_path.read_text(encoding="utf-8")
    assert "first_only" not in second.results_path.read_text(encoding="utf-8")
    second.run()
    assert first.working_target_path.read_text(encoding="utf-8") == original
    assert second.working_target_path.read_text(encoding="utf-8") == original
    assert target.read_text(encoding="utf-8") == original
    assert target.stat().st_mtime_ns == original_mtime


def test_research_target_named_like_log_keeps_separate_artifacts(temp_research_env, tmp_path):
    target, program = temp_research_env
    original = target.read_bytes()
    named_like_log = tmp_path / "results.tsv"
    named_like_log.write_bytes(original)
    researcher = WREAutoResearcher(named_like_log, program, max_iterations=0, results_dir=tmp_path / "runs")
    researcher.run()
    assert researcher.results_path != researcher.working_target_path
    assert researcher.results_path.read_text(encoding="utf-8").startswith("timestamp\titeration\t")
    assert researcher.working_target_path.read_text(encoding="utf-8") == named_like_log.read_text(encoding="utf-8")
    assert named_like_log.read_bytes() == original


def test_concurrent_research_construction_owns_distinct_directories(temp_research_env, tmp_path):
    target, program = temp_research_env
    barrier = Barrier(2)
    def construct(_index):
        barrier.wait(timeout=10)
        return WREAutoResearcher(target, program, max_iterations=0, results_dir=tmp_path / "runs")
    with ThreadPoolExecutor(max_workers=2) as workers:
        researchers = list(workers.map(construct, range(2)))
    assert len({r.results_dir for r in researchers}) == 2
    assert len({r.working_target_path for r in researchers}) == 2
    assert len({r.results_path for r in researchers}) == 2
    for researcher in researchers:
        assert researcher.working_target_path.read_bytes() == target.read_bytes()
        assert researcher.results_path.read_text(encoding="utf-8").startswith("timestamp\titeration\t")


@pytest.mark.parametrize("drift", ["construction", "between_calls", "baseline", "proposal", "interrupted"])
@pytest.mark.parametrize("newline", ["\n", "\r\n"], ids=["lf", "crlf"])
def test_invocation_uses_one_baseline_snapshot(temp_research_env, tmp_path, monkeypatch, drift, newline):
    target, program = temp_research_env
    original = target.read_text(encoding="utf-8")
    target.write_bytes(original.replace("\n", newline).encode("utf-8"))
    changed = original + "\n# changed outside this invocation\n"
    read_text = Path.read_text
    def read(path, *args, **kwargs):
        if path == program and drift == "construction":
            target.write_text(changed, encoding="utf-8")
        return read_text(path, *args, **kwargs)
    monkeypatch.setattr(Path, "read_text", read)
    researcher = WREAutoResearcher(target, program, max_iterations=1, results_dir=tmp_path / "runs")
    assert researcher.working_target_path.read_text(encoding="utf-8") == original
    source_bytes = target.read_bytes()
    evaluated, proposed = [], []
    def evaluate(path):
        evaluated.append(path.read_text(encoding="utf-8"))
        if drift == "baseline":
            researcher.original_code = changed
        return evaluate_target(path)
    def propose(code, *args):
        proposed.append(code)
        if drift in ("proposal", "interrupted"):
            researcher.original_code = changed
        if drift == "interrupted":
            raise KeyboardInterrupt("proposal interrupted")
        return None
    monkeypatch.setattr(researcher, "_propose_change", propose)
    if drift == "between_calls":
        researcher.run()
        proposed.clear()
        researcher.working_target_path.write_text(changed, encoding="utf-8")
    monkeypatch.setattr(researcher_module, "evaluate_target", evaluate)
    if drift == "interrupted":
        with pytest.raises(KeyboardInterrupt, match="proposal interrupted"):
            researcher.run()
        report = json.loads(next(researcher.results_dir.glob("invocation-*/report.json")).read_text())
    else:
        report = researcher.run()
    assert evaluated == proposed == [original]
    assert researcher.working_target_path.read_text(encoding="utf-8") == original
    assert target.read_bytes() == source_bytes
    assert report["baseline_input_sha256"] == hashlib.sha256(original.encode("utf-8")).hexdigest()
    assert report["cleanup"] == "restored"
    assert report["status"] == ("aborted" if drift == "interrupted" else "completed")
    assert json.loads(Path(report["report_path"]).read_text()) == report


@pytest.mark.parametrize("outcomes", [
    [], ["no_proposal"] * 3, ["rejected"] * 3, ["failed_validation"] * 3,
    ["crashed"] * 3, ["accepted"] * 3,
    ["no_proposal", "rejected", "failed_validation", "crashed", "accepted"],
])
def test_completed_run_accounts_for_every_attempt(temp_research_env, tmp_path, monkeypatch, outcomes):
    target, program = temp_research_env
    original = target.read_bytes()
    researcher = WREAutoResearcher(target, program, max_iterations=len(outcomes), results_dir=tmp_path / "runs")
    active, calls = [], []

    def propose(*args):
        state = outcomes[len(active)]
        active.append(state)
        return None if state == "no_proposal" else original.decode("utf-8") + "\n# candidate\n"

    def evaluate(path):
        calls.append(path)
        metrics = dict(fitness=0.0, roc_ratio=1.0, monthly_margin_usd=0.0, is_roi_sustainable=False)
        if active:
            if active[-1] == "crashed":
                raise RuntimeError("evaluation interrupted")
            if active[-1] == "failed_validation":
                metrics["error"] = "invalid candidate"
            if active[-1] == "accepted":
                metrics["fitness"] = float(len(calls))
        return metrics

    monkeypatch.setattr(researcher, "_propose_change", propose)
    monkeypatch.setattr(researcher_module, "evaluate_target", evaluate)
    result = researcher.run()
    assert json.loads(Path(result["report_path"]).read_text()) == result
    counts = {state: outcomes.count(state) for state in ("no_proposal", "accepted", "rejected", "failed_validation", "crashed")}
    assert result["attempts_requested"] == result["attempts_started"] == result["iterations_run"] == len(outcomes)
    assert result["baseline_evaluations"] == 1
    assert result["candidate_evaluations"] == len(calls) - 1 == len(outcomes) - counts["no_proposal"]
    assert result["outcome_counts"] == counts
    assert result["independently_verified"] is None and result["retained_improvements"] is None
    assert result["resource_usage"] is None
    assert [row["status"] for row in result["history"]] == outcomes
    with researcher.results_path.open(encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream, delimiter="\t"))
    assert [row["status"] for row in rows] == ["baseline"] + outcomes
    assert [int(row["iteration"]) for row in rows] == list(range(len(outcomes) + 1))
    previous_fitness = 0.0
    for row in rows:
        if row["status"] == "accepted":
            assert row["info"] == f"Improved from {previous_fitness:.4f}"
            previous_fitness = float(row["fitness"])
        if row["status"] in ("no_proposal", "crashed"):
            assert all(row[key] == "" for key in ("fitness", "roc_ratio", "monthly_margin"))
    assert target.read_bytes() == researcher.working_target_path.read_bytes() == original


@pytest.mark.parametrize("cap", [-1, True, False, 1.5, "2", None])
def test_invalid_attempt_cap_rejects_before_output(temp_research_env, tmp_path, monkeypatch, cap):
    target, program = temp_research_env
    output = tmp_path / "must_not_exist"
    monkeypatch.setattr(researcher_module, "get_qwen_engine", lambda: pytest.fail("invalid cap initialized model"))
    with pytest.raises(ValueError, match="max_iterations"):
        WREAutoResearcher(target, program, max_iterations=cap, results_dir=output)
    assert not output.exists()
    monkeypatch.setattr(researcher_module, "get_qwen_engine", lambda: None)
    researcher = WREAutoResearcher(target, program, max_iterations=0, results_dir=tmp_path / "valid")
    researcher.max_iterations = cap
    monkeypatch.setattr(researcher_module, "evaluate_target", lambda path: pytest.fail("invalid cap evaluated baseline"))
    with pytest.raises(ValueError, match="max_iterations"):
        researcher.run()


@pytest.mark.parametrize("failure", ["commit", "accepted_log"])
def test_failed_acceptance_preserves_reported_best(temp_research_env, tmp_path, monkeypatch, failure):
    target, program = temp_research_env
    original = target.read_text(encoding="utf-8")
    baseline = evaluate_target(target)
    candidate = dict(baseline, fitness=baseline["fitness"] + 1)
    metrics = iter([baseline, candidate])
    researcher = WREAutoResearcher(target, program, max_iterations=1, results_dir=tmp_path / "runs")
    monkeypatch.setattr(researcher, "_propose_change", lambda *args: original + "\n# candidate\n")
    monkeypatch.setattr(researcher_module, "evaluate_target", lambda path: next(metrics))
    log = researcher._log_to_tsv

    def fail(*args):
        raise RuntimeError("acceptance recording failed")

    def fail_accepted(iteration, status, values, info=""):
        return fail() if status == "accepted" else log(iteration, status, values, info)

    monkeypatch.setattr(researcher, "_commit" if failure == "commit" else "_log_to_tsv",
                        fail if failure == "commit" else fail_accepted)
    result = researcher.run()
    assert result["optimized"] == result["baseline"] == baseline
    assert result["improvement"] == 0
    assert [row["status"] for row in result["history"]] == ["crashed"]
    assert researcher.working_target_path.read_text(encoding="utf-8") == original


def test_report_keeps_invocation_attempt_cap(temp_research_env, tmp_path, monkeypatch):
    target, program = temp_research_env
    researcher = WREAutoResearcher(target, program, max_iterations=2, results_dir=tmp_path / "runs")

    def propose(*args):
        researcher.max_iterations = 99
        return None

    monkeypatch.setattr(researcher, "_propose_change", propose)
    result = researcher.run()
    assert result["attempts_requested"] == result["attempts_started"] == result["iterations_run"] == 2


def _assert_reports_preserved(researcher, first, first_bytes, fault):
    reports = [json.loads(p.read_text()) for p in researcher.results_dir.glob("invocation-*/report.json")]
    assert len(reports) == (2 if fault in ("none", "cleanup", "local_write") else 1)
    assert sum(r["status"] == "completed" for r in reports) == (2 if fault == "none" else 1)
    assert Path(first["report_path"]).read_bytes() == first_bytes
    restored = researcher.working_target_path.read_bytes() == researcher.target_path.read_bytes()
    assert restored is (fault != "local_write")


def _assert_mode_denied(researcher, original, commits, timing):
    assert not commits
    assert researcher.target_path.read_text(encoding="utf-8") == original
    assert researcher.working_target_path.read_text(encoding="utf-8") == original
    if timing != "direct_commit":
        report = json.loads(next(researcher.results_dir.glob("invocation-*/report.json")).read_text())
        assert report["status"] == "aborted" and report["cleanup"] == "restored"
        assert report["failure"]["type"] == "NotImplementedError"
        assert report["dry_run"] is (timing != "before_run")
        assert report["attempts_started"] == int(timing != "before_run")
        assert report["candidate_evaluations"] == int(timing in ("diff", "evaluation", "after_loop"))


@pytest.mark.parametrize("mode", [False, 1])
@pytest.mark.parametrize("timing", ["before_run", "proposal", "missing_proposal", "diff", "evaluation", "after_loop", "direct_commit"])
def test_mode_drift_cannot_delegate_commit_or_skip_cleanup(temp_research_env, tmp_path, monkeypatch, mode, timing):
    target, program = temp_research_env
    original = target.read_text(encoding="utf-8")
    researcher = WREAutoResearcher(target, program, max_iterations=1, results_dir=tmp_path / "runs")
    commits, evaluated = [], []
    baseline = evaluate_target(target)
    improved = dict(baseline, fitness=baseline["fitness"] + 1)
    monkeypatch.setattr(researcher.runner, "commit", lambda *args: commits.append(args))
    def propose(*args):
        if timing in ("proposal", "missing_proposal"):
            researcher.dry_run = mode
        return None if timing == "missing_proposal" else original + "\n# proposed\n"
    def diff(*args):
        researcher.dry_run = mode
        return ""
    def evaluate(path):
        evaluated.append(path)
        if timing == "evaluation" and len(evaluated) > 1:
            researcher.dry_run = mode
        return baseline if len(evaluated) == 1 else improved
    loop = researcher._run_loop
    def run_loop(report, baseline_code):
        loop(report, baseline_code)
        researcher.dry_run = mode
    monkeypatch.setattr(researcher, "_propose_change", propose)
    monkeypatch.setattr(researcher_module, "evaluate_target", evaluate)
    if timing == "diff":
        monkeypatch.setattr(researcher.runner, "diff", diff)
    if timing == "after_loop":
        monkeypatch.setattr(researcher, "_run_loop", run_loop)
    if timing in ("before_run", "direct_commit"):
        researcher.dry_run = mode
    if timing == "before_run":
        researcher.working_target_path.write_text("# stale scratch\n" + original, encoding="utf-8")
    with pytest.raises(NotImplementedError, match="SPECIFIED_NOT_IMPLEMENTED"):
        if timing == "direct_commit":
            researcher._commit(1, improved)
        else:
            researcher.run()
    _assert_mode_denied(researcher, original, commits, timing)


@pytest.mark.parametrize("fault", ["none", "publish", "write", "cleanup", "publish_abort", "allocate", "local_write"])
def test_terminal_reports_preserve_prior_invocations(temp_research_env, tmp_path, monkeypatch, fault):
    target, program = temp_research_env
    researcher = WREAutoResearcher(target, program, max_iterations=0, results_dir=tmp_path / "runs")
    first = researcher.run()
    first_path = Path(first["report_path"])
    first_bytes = first_path.read_bytes()
    researcher.working_target_path.write_text("# stale scratch\n" + target.read_text(), encoding="utf-8")
    original_replace = Path.replace
    original_write = Path.write_text
    def replace(path, destination):
        assert (researcher.working_target_path.read_bytes() == target.read_bytes()) is (fault != "local_write")
        if fault.startswith("publish"):
            raise OSError("publication failed")
        return original_replace(path, destination)
    def write(path, *args, **kwargs):
        if fault == "write" and path.name == "report.tmp":
            raise OSError("publication failed")
        if fault == "local_write" and path == researcher.working_target_path:
            raise OSError("restoration failed")
        return original_write(path, *args, **kwargs)
    def restore(*args, **kwargs):
        raise OSError("restoration failed")
    monkeypatch.setattr(Path, "replace", replace)
    monkeypatch.setattr(Path, "write_text", write)
    if fault == "cleanup":
        monkeypatch.setattr(researcher.runner, "restore", restore)
    if fault == "allocate":
        monkeypatch.setattr(researcher_module.tempfile, "mkdtemp", restore)
    if fault == "publish_abort":
        researcher.max_iterations = -1
    if fault == "none":
        second = researcher.run()
        assert second["invocation_id"] != first["invocation_id"]
        assert json.loads(Path(second["report_path"]).read_text()) == second
        assert second["attempts_started"] == 0 and second["baseline_evaluations"] == 1
    else:
        with pytest.raises(OSError, match="restoration failed" if fault in ("cleanup", "local_write", "allocate") else "publication failed") as caught:
            researcher.run()
        if fault == "publish_abort":
            assert isinstance(caught.value.__context__, ValueError)
        if fault == "local_write":
            failed = json.loads(next(p for p in researcher.results_dir.glob("invocation-*/report.json") if p != first_path).read_text())
            assert failed["failure"] == {"type": "OSError", "phase": "baseline_preparation"}
            assert failed["baseline_evaluations"] == failed["attempts_started"] == 0
    _assert_reports_preserved(researcher, first, first_bytes, fault)


@pytest.mark.parametrize("newline", ["\n", "\r\n"])
def test_proposal_inputs_distinguish_equal_outcomes(temp_research_env, tmp_path, monkeypatch, newline):
    target, program = temp_research_env
    researcher = WREAutoResearcher(target, program, max_iterations=3, results_dir=tmp_path / "runs")
    original = target.read_text(encoding="utf-8")
    first_bytes = None
    for label in ("first", "second"):
        proposals = [original + f"# {label} café\n", None, original + f"# {label} 東京\n"]
        proposals = [p.replace("\n", newline) if p else p for p in proposals]
        pending = iter(proposals)
        monkeypatch.setattr(researcher, "_propose_change", lambda code, metrics, history: next(pending))
        result = researcher.run()
        assert result["proposal_inputs"] == [
            {"iteration": i, "proposal_input_sha256": hashlib.sha256(p.encode("utf-8")).hexdigest()}
            for i, p in enumerate(proposals, 1) if p
        ]
        assert [row["status"] for row in result["history"]] == ["rejected", "no_proposal", "rejected"]
        assert result["candidate_evaluations"] == 2 and result["attempts_started"] == 3
        assert json.loads(Path(result["report_path"]).read_text()) == result
        assert researcher.working_target_path.read_text(encoding="utf-8") == original
        assert target.read_text(encoding="utf-8") == original
        if first_bytes is None:
            first_path, first_inputs = Path(result["report_path"]), result["proposal_inputs"]
            first_bytes = first_path.read_bytes()
        else:
            assert result["proposal_inputs"] != first_inputs
            assert first_path.read_bytes() == first_bytes


@pytest.mark.parametrize("fault", ["write", "diff", "evaluation"])
def test_aborted_proposal_keeps_input_identity(temp_research_env, tmp_path, monkeypatch, fault):
    target, program = temp_research_env
    researcher = WREAutoResearcher(target, program, max_iterations=1, results_dir=tmp_path / "runs")
    original = target.read_text(encoding="utf-8")
    proposed = original + "# interrupted proposal\n"
    monkeypatch.setattr(researcher, "_propose_change", lambda *args: proposed)
    write_text, evaluator = Path.write_text, researcher_module.evaluate_target
    evaluated = []
    def write(path, data, *args, **kwargs):
        if fault == "write" and path == researcher.working_target_path and data is proposed:
            raise OSError("candidate write failed")
        return write_text(path, data, *args, **kwargs)
    def diff(*args):
        if fault == "diff":
            raise RuntimeError("diff failed")
        return ""
    def evaluate(path):
        evaluated.append(path)
        if fault == "evaluation" and len(evaluated) == 2:
            raise KeyboardInterrupt()
        return evaluator(path)
    monkeypatch.setattr(Path, "write_text", write)
    monkeypatch.setattr(researcher.runner, "diff", diff)
    monkeypatch.setattr(researcher_module, "evaluate_target", evaluate)
    with pytest.raises({"write": OSError, "diff": RuntimeError, "evaluation": KeyboardInterrupt}[fault]):
        researcher.run()
    report = json.loads(next(researcher.results_dir.glob("invocation-*/report.json")).read_text())
    assert report["proposal_inputs"] == [{"iteration": 1, "proposal_input_sha256": hashlib.sha256(proposed.encode("utf-8")).hexdigest()}]
    assert report["status"] == "aborted" and report["cleanup"] == "restored"
    assert report["attempts_started"] == 1 and report["attempts_finished"] == 0
    assert report["candidate_evaluations"] == int(fault == "evaluation")
    assert researcher.working_target_path.read_text(encoding="utf-8") == original
    assert target.read_text(encoding="utf-8") == original


@pytest.mark.parametrize("proposal", [None, "", {}, False, {"code": "bad"}, b"bad", 1])
def test_missing_or_nontext_proposal_has_no_text_identity(temp_research_env, tmp_path, monkeypatch, proposal):
    target, program = temp_research_env
    researcher = WREAutoResearcher(target, program, max_iterations=1, results_dir=tmp_path / "runs")
    monkeypatch.setattr(researcher, "_propose_change", lambda *args: proposal)
    diff_calls = []
    monkeypatch.setattr(researcher.runner, "diff", lambda *args: diff_calls.append(args))
    if proposal:
        with pytest.raises(TypeError):
            researcher.run()
    else:
        researcher.run()
    report = json.loads(next(researcher.results_dir.glob("invocation-*/report.json")).read_text())
    assert report["proposal_inputs"] == [] and not diff_calls
    assert report["candidate_evaluations"] == 0 and report["cleanup"] == "restored"
    if proposal:
        assert report["failure"] == {"type": "TypeError", "phase": "candidate_preparation"}
    else:
        assert report["status"] == "completed" and report["outcome_counts"]["no_proposal"] == 1


def test_proposal_text_subclass_uses_underlying_unicode(temp_research_env, tmp_path, monkeypatch):
    class EncodedOverride(str):
        def encode(self, *args, **kwargs):
            raise AssertionError("override must not define text identity")
    target, program = temp_research_env
    researcher = WREAutoResearcher(target, program, max_iterations=1, results_dir=tmp_path / "runs")
    plain = target.read_text(encoding="utf-8") + "# subclass café\n"
    monkeypatch.setattr(researcher, "_propose_change", lambda *args: EncodedOverride(plain))
    result = researcher.run()
    assert result["proposal_inputs"] == [{"iteration": 1, "proposal_input_sha256": hashlib.sha256(plain.encode("utf-8")).hexdigest()}]
    assert result["history"][0]["status"] == "rejected"


_RESEARCH_EXIT_CHILD = r'''
import json, os, sys, types
from pathlib import Path
repo, case, mode = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve(), sys.argv[3]
owner = "modules.infrastructure.wre_core.src"
readable = {repo / p for p in ("modules/__init__.py", "modules/infrastructure/wre_core/__init__.py", "modules/infrastructure/wre_core/src/__init__.py", "modules/infrastructure/wre_core/src/wre_auto_researcher.py")}
def deny():
    (case / "guard-denied").write_text("forbidden effect")
    raise AssertionError("forbidden effect")
def guard(event, args):
    if event.startswith(("subprocess.", "socket.", "sqlite3.", "os.exec", "os.spawn", "os.fork", "os.system", "os.posix_spawn", "os.startfile", "os.kill", "ctypes.")):
        deny()
    if event == "open" and not isinstance(args[0], int):
        path = Path(os.fsdecode(args[0])).resolve()
        writing = args[2] & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND)
        allowed = path.is_relative_to(case) or (not writing and (path in readable or path.is_relative_to(Path(sys.base_prefix))))
        if not allowed or path.name.startswith(".env") or path.suffix in (".db", ".sqlite", ".gguf", ".pem", ".key"):
            deny()
    if event in ("os.mkdir", "os.remove", "os.rmdir", "os.rename"):
        for raw in args[:2] if event == "os.rename" else args[:1]:
            if not Path(raw).resolve().is_relative_to(case):
                deny()
    if event in ("os.chdir", "os.symlink", "os.link", "os.chmod", "os.truncate", "os.utime", "os.chown", "os.putenv", "os.unsetenv"):
        deny()
sys.addaudithook(guard)
def unused(*args):
    raise AssertionError("unused loader")
for name, values in (("modules.infrastructure.shared_utilities.ai_engine_singletons", {"get_qwen_engine": lambda: None}), (owner + ".wre_research_evaluator", {"evaluate_target": lambda path: {"fitness": 1.0, "roc_ratio": 1.0, "monthly_margin_usd": 1.0}, "load_target_config_from_source": unused})):
    module = types.ModuleType(name)
    module.__dict__.update(values)
    sys.modules[name] = module
sys.path.insert(0, str(repo))
from modules.infrastructure.wre_core.src import wre_auto_researcher as subject
assert not any(name.startswith(("modules.foundups.simulator", "holo_index", "modules.infrastructure.shared_utilities.local_llm_resolver")) for name in sys.modules)
researcher = subject.WREAutoResearcher(case / "target.py", case / "program.md", max_iterations=1, results_dir=case / "runs")
researcher._propose_change = lambda *args: "# proposal"
allocate, replace, paths = subject._new_run_report, Path.replace, {}
def reserve(*args):
    report = allocate(*args)
    paths.update(run=str(researcher.results_dir), scratch=str(researcher.working_target_path), report=report["report_path"])
    (case / "paths.json").write_text(json.dumps(paths))
    return report
def stop(phase, code):
    (case / "phase").write_text(phase)
    os._exit(code)
def publish(path, destination):
    assert path == Path(paths["report"]).with_suffix(".tmp") and destination == Path(paths["report"])
    if mode == "temporary":
        stop("temporary", 72)
    return replace(path, destination)
subject._new_run_report, Path.replace = reserve, publish
researcher.runner.diff = lambda *args: stop("proposal", 71) if mode == "proposal" else ""
(case / "ack.json").write_text(json.dumps(researcher.run()))
'''


@pytest.mark.parametrize("mode,expected_exit", [("normal", 0), ("proposal", 71), ("temporary", 72)])
def test_abrupt_exit_preserves_unknown_report_state(tmp_path, mode, expected_exit):
    import subprocess
    case = (tmp_path / mode).resolve()
    assert not case.is_relative_to(REPO_ROOT.resolve())
    case.mkdir()
    inputs = {case / "target.py": b"# baseline", case / "program.md": b"fixture", case / "runs/run-prior/invocation-prior/report.json": b"prior-fixture"}
    for path, content in inputs.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    environment = {key: os.environ[key] for key in ("SystemRoot", "WINDIR") if key in os.environ}
    environment.update(TMP=str(case), TEMP=str(case), HOME=str(case), USERPROFILE=str(case))
    command = [sys.executable, "-I", "-S", "-B", "-X", f"pycache_prefix={case / 'pycache'}", "-c", _RESEARCH_EXIT_CHILD, str(REPO_ROOT), str(case), mode]
    child = subprocess.Popen(command, cwd=case, env=environment, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        code = child.wait(timeout=20)
    finally:
        if child.poll() is None:
            child.kill()
            child.wait(timeout=5)
    assert code == expected_exit and not (case / "guard-denied").exists()
    paths = json.loads((case / "paths.json").read_text())
    assert set(paths) == {"run", "scratch", "report"}
    run, scratch, report = (Path(paths[key]).resolve() for key in ("run", "scratch", "report"))
    assert run.parent == case / "runs" and run.name.startswith("run-") and run.name != "run-prior"
    assert scratch == run / "target/target.py" and report.parent.parent == run
    assert report.name == "report.json" and report.parent.name.startswith("invocation-")
    assert scratch.read_bytes() == (b"# proposal" if mode == "proposal" else b"# baseline")
    assert all(path.read_bytes() == content for path, content in inputs.items())
    assert report.exists() is (mode == "normal")
    assert report.with_suffix(".tmp").exists() is (mode == "temporary")
    assert (case / "ack.json").exists() is (mode == "normal")
    if mode != "normal":
        assert (case / "phase").read_text() == mode
    if mode in ("normal", "temporary"):
        result = json.loads((report if mode == "normal" else report.with_suffix(".tmp")).read_text())
        assert result["invocation_id"] == report.parent.name and Path(result["report_path"]).resolve() == report
        assert result["status"] == "completed" and result["cleanup"] == "restored"
        assert result["baseline_input_sha256"] == hashlib.sha256(b"# baseline").hexdigest()
        assert result["proposal_inputs"] == [{"iteration": 1, "proposal_input_sha256": hashlib.sha256(b"# proposal").hexdigest()}]
        if mode == "normal":
            assert json.loads((case / "ack.json").read_text()) == result
