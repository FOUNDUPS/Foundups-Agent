# -*- coding: utf-8 -*-
"""
WRE ROC Auto-Researcher Tests (WSP 48)
Slice Name: WRE_AUTORESEARCH_GIT_RUNNER_CONTRACT_PHASE1

Verifies the Auto-Researcher contract loop, AST denylist violations,
dry-run safety, path write protection, and fail-closed SPECIFIED_NOT_IMPLEMENTED behavior.
"""

import ast
import os
import sys
import shutil
import pytest
import tempfile
import time
from pathlib import Path

# Add repo root to sys.path
REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from modules.infrastructure.wre_core.src.wre_research_evaluator import evaluate_target
from modules.infrastructure.wre_core.src.wre_auto_researcher import WREAutoResearcher, DryRunGitRunner


@pytest.fixture
def temp_research_env(tmp_path):
    """Fixture to create temporary target and program files."""
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
    working_file = results_dir / target_path.name
    assert working_file.exists()


def test_repo_source_isolation_block(temp_research_env):
    """Verify WSP_97 path protection block when target_path resolves under REPO_ROOT."""
    target_path, program_path = temp_research_env

    # Point results_dir to be under REPO_ROOT to trigger PermissionError
    repo_results_dir = Path(REPO_ROOT) / "modules" / "infrastructure" / "wre_core" / "src" / "sandbox_test"

    with pytest.raises(PermissionError) as exc_info:
        WREAutoResearcher(
            target_path=target_path,
            program_path=program_path,
            max_iterations=1,
            dry_run=True,
            results_dir=repo_results_dir,
        )

    assert "strictly prohibited" in str(exc_info.value)


def test_results_tsv_path_isolation(temp_research_env, tmp_path):
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

    # Check results file created under results_dir
    expected_file = results_dir / "results.tsv"
    assert expected_file.exists()
    assert "timestamp" in expected_file.read_text(encoding="utf-8")

    # Ensure no results.tsv was written to repo source folder
    source_results = Path(REPO_ROOT) / "modules" / "infrastructure" / "wre_core" / "src" / "results.tsv"
    assert not source_results.exists()


def test_commit_mode_fail_closed(temp_research_env, tmp_path):
    """Verify commit/live mode is fail-closed, raising SPECIFIED_NOT_IMPLEMENTED."""
    target_path, program_path = temp_research_env
    results_dir = tmp_path / "runs"

    # Direct initialization of WREAutoResearcher with dry_run=False should raise error
    with pytest.raises(NotImplementedError) as exc_info:
        WREAutoResearcher(
            target_path=target_path,
            program_path=program_path,
            max_iterations=1,
            dry_run=False,
            runner=DryRunGitRunner(),
            results_dir=results_dir,
        )
    
    assert "SPECIFIED_NOT_IMPLEMENTED" in str(exc_info.value)
