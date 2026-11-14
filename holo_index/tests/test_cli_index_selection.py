"""Tests for deterministic HoloIndex CLI collection selection."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

os.environ.setdefault("HOLO_SKIP_MODEL", "1")

from holo_index import _cli_main


REPO_ROOT = Path(__file__).resolve().parents[2]


def _args(**overrides):
    values = {flag: False for flag in _cli_main._INDEX_FLAG_ATTRS}
    values.update(overrides)
    return argparse.Namespace(**values)


def test_index_and_index_all_select_exact_same_baseline() -> None:
    alias = _cli_main._selected_index_collections(_args(index=True))
    explicit = _cli_main._selected_index_collections(_args(index_all=True))

    assert alias == explicit == set(_cli_main.BASELINE_INDEX_COLLECTIONS)
    assert alias == {
        "navigation_code",
        "navigation_symbols",
        "navigation_wsp",
        "navigation_tests",
        "navigation_skills",
        "navigation_docs",
        "navigation_knowledge",
    }


def test_test_only_selection_does_not_select_wsp_or_knowledge() -> None:
    selected = _cli_main._selected_index_collections(_args(index_tests=True))

    assert selected == {"navigation_tests"}
    assert "navigation_wsp" not in selected
    assert "navigation_knowledge" not in selected


def test_work_ledger_remains_targeted_and_outside_baseline() -> None:
    baseline = _cli_main._selected_index_collections(_args(index_all=True))
    targeted = _cli_main._selected_index_collections(_args(index_work_ledger=True))

    assert "navigation_work_ledger" not in baseline
    assert targeted == {"navigation_work_ledger"}


def test_code_plan_declares_implicit_symbol_mutation(monkeypatch) -> None:
    monkeypatch.setenv("HOLO_SYMBOL_AUTO", "1")
    selected = _cli_main._effective_index_collections(_args(index_code=True))

    assert selected == {"navigation_code", "navigation_symbols"}


def test_index_all_reports_cli_and_environment_scope_narrowing() -> None:
    args = _args(
        index_all=True,
        symbol_roots=["modules"],
        wsp_path=["custom"],
        module=None,
    )

    violations = _cli_main._baseline_source_scope_violations(
        args,
        {
            "HOLO_INDEX_WEB": "0",
            "HOLO_WEB_INDEX_MAX_FILES": "10",
            "HOLO_SYMBOL_ROOTS": "modules",
        },
    )

    assert violations == [
        "--symbol-roots",
        "--wsp-path",
        "HOLO_INDEX_WEB",
        "HOLO_SYMBOL_ROOTS",
        "HOLO_WEB_INDEX_MAX_FILES",
    ]


def test_cli_catalog_generation_is_not_part_of_index_all() -> None:
    source = (REPO_ROOT / "holo_index" / "_cli_main.py").read_text(encoding="utf-8")

    assert "index_cli = getattr(args, 'index_cli', False)" in source
    assert "index_cli = getattr(args, 'index_cli', False) or args.index_all" not in source


def test_cli_help_exposes_test_indexing_and_baseline_contract() -> None:
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env.setdefault("HOLO_SKIP_MODEL", "1")
    result = subprocess.run(
        [sys.executable, "-B", "holo_index.py", "--help"],
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        timeout=30,
        encoding="utf-8",
        errors="replace",
    )

    output = result.stdout + result.stderr
    normalized_output = " ".join(output.split())
    assert result.returncode == 0
    assert "--index-tests" in output
    assert "code, symbols, WSP, tests, skills, docs, and knowledge" in normalized_output
