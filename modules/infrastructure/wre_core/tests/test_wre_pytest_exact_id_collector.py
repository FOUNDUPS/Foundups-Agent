from __future__ import annotations

import ast
import json
from pathlib import Path
import subprocess
import sys

import pytest

from modules.infrastructure.wre_core.src import wre_pytest_exact_id_collector as collector


ROOT = Path(__file__).resolve().parents[4]
COLLECTOR = ROOT / "modules/infrastructure/wre_core/src/wre_pytest_exact_id_collector.py"
OUTCOME_FIELDS = (
    "passed_ids", "failed_ids", "error_ids", "skipped_ids",
    "xfailed_ids", "xpassed_ids", "deselected_ids",
)


def _run(project: Path, *args: str, output: Path | None = None):
    destination = output or project.parent / "evidence" / "report.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        [sys.executable, str(COLLECTOR.resolve()), "--output", str(destination), "--", *args],
        cwd=project, capture_output=True, text=True, timeout=30, check=False,
    )
    report = json.loads(destination.read_text(encoding="utf-8")) if destination.exists() else None
    return result, report, destination


def _write(project: Path, name: str, source: str) -> None:
    (project / name).write_text(source, encoding="utf-8")


def test_collects_exact_terminal_node_ids(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    _write(project, "test_outcomes.py", """
import pytest

def test_pass(): pass
def test_fail(): assert False
@pytest.mark.skip(reason="skip")
def test_skip(): pass
@pytest.mark.xfail(reason="known")
def test_xfail(): assert False
@pytest.mark.xfail(reason="unexpected")
def test_xpass(): pass
@pytest.mark.xfail(reason="strict", strict=True)
def test_xpass_strict(): pass
def test_deselected(): pass
""".lstrip())
    result, report, destination = _run(project, "-q", "-k", "not deselected")
    assert result.returncode == 0, result.stderr
    assert report["schema_version"] == "wre_pytest_exact_id_report.v1"
    assert report["pytest_exit_code"] == 1
    assert report["collection_complete"] is True
    assert report["passed_ids"] == ["test_outcomes.py::test_pass"]
    assert report["failed_ids"] == ["test_outcomes.py::test_fail"]
    assert report["skipped_ids"] == ["test_outcomes.py::test_skip"]
    assert report["xfailed_ids"] == ["test_outcomes.py::test_xfail"]
    assert report["xpassed_ids"] == [
        "test_outcomes.py::test_xpass", "test_outcomes.py::test_xpass_strict",
    ]
    assert report["deselected_ids"] == ["test_outcomes.py::test_deselected"]
    assert report["error_ids"] == []
    assert report["collected_ids"] == sorted(set().union(*(set(report[name]) for name in OUTCOME_FIELDS)))
    assert not list(destination.parent.glob(".wre-pytest-*.tmp"))


def test_setup_and_teardown_failures_are_errors(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    _write(project, "test_errors.py", """
import pytest

@pytest.fixture
def setup_error():
    raise RuntimeError("setup")

@pytest.fixture
def teardown_error():
    yield
    raise RuntimeError("teardown")

def test_setup(setup_error): pass
def test_teardown(teardown_error): pass
""".lstrip())
    result, report, _ = _run(project, "-q")
    assert result.returncode == 0
    assert report["collection_complete"] is True
    assert report["error_ids"] == ["test_errors.py::test_setup", "test_errors.py::test_teardown"]
    assert all(not report[name] for name in OUTCOME_FIELDS if name != "error_ids")


def test_collection_error_writes_incomplete_report_and_fails(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    _write(project, "test_bad.py", "def test_bad(:\n")
    result, report, _ = _run(project, "-q")
    assert result.returncode != 0
    assert report["collection_complete"] is False
    assert report["pytest_exit_code"] not in {0, 1}
    assert report["collection_errors"]


def test_no_tests_is_fail_closed(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    result, report, _ = _run(project, "-q")
    assert result.returncode != 0
    assert report["pytest_exit_code"] == 5
    assert report["collected_ids"] == []


def test_early_stop_with_unexecuted_collected_ids_is_fail_closed(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    _write(project, "test_stop.py", """
def test_first(): assert False
def test_never_runs(): pass
""".lstrip())
    result, report, _ = _run(project, "-q", "--maxfail=1")
    assert result.returncode != 0
    assert report["pytest_exit_code"] == 1
    assert report["collection_complete"] is False
    assert report["collected_ids"] == ["test_stop.py::test_first", "test_stop.py::test_never_runs"]
    assert report["failed_ids"] == ["test_stop.py::test_first"]


def test_silent_item_removal_by_candidate_hook_is_incomplete(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    _write(project, "conftest.py", "def pytest_collection_modifyitems(items):\n    items[:] = items[:1]\n")
    _write(project, "test_items.py", "def test_one(): pass\ndef test_two(): pass\n")
    result, report, _ = _run(project, "-q")
    assert result.returncode != 0
    assert report["collection_complete"] is False
    assert report["collected_ids"] == ["test_items.py::test_one", "test_items.py::test_two"]
    assert report["passed_ids"] == ["test_items.py::test_one"]


@pytest.mark.parametrize("args", [
    ("-p", "example"), ("-pexample",), ("--junitxml=stolen.xml",),
    ("--json-report",), ("--collect-only",),
])
def test_candidate_cannot_select_plugins_or_reporters(tmp_path: Path, args: tuple[str, ...]) -> None:
    project = tmp_path / "project"
    project.mkdir()
    _write(project, "test_ok.py", "def test_ok(): pass\n")
    result, report, _ = _run(project, *args)
    assert result.returncode == 2
    assert report is None
    assert "pytest_argument_forbidden" in result.stderr


def test_relative_output_path_is_rejected_without_write(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    result = subprocess.run(
        [sys.executable, str(COLLECTOR.resolve()), "--output", "report.json", "--", "-q"],
        cwd=project, capture_output=True, text=True, timeout=30, check=False,
    )
    assert result.returncode == 2
    assert not (project / "report.json").exists()


def test_repository_output_path_is_rejected() -> None:
    with pytest.raises(ValueError, match="outside_repository"):
        collector._validated_output(ROOT / "forbidden-report.json")


def test_candidate_config_cannot_enable_an_output_reporter(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    _write(project, "pytest.ini", "[pytest]\naddopts = --junitxml=attacker.xml\n")
    _write(project, "test_ok.py", "def test_ok(): pass\n")
    result, report, _ = _run(project, "-q")
    assert result.returncode == 0
    assert report["passed_ids"] == ["test_ok.py::test_ok"]
    assert not (project / "attacker.xml").exists()


def test_candidate_closing_console_stream_fails_closed(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    _write(project, "test_close.py", "import sys\nsys.stdout.close()\n\ndef test_ok(): pass\n")
    result, report, _ = _run(project, "-q")
    assert result.returncode != 0
    assert report is None


def test_candidate_cannot_replace_terminal_classifier_global(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    _write(project, "test_forge.py", """
import __main__

def test_forge():
    __main__._terminal_outcome = lambda _reports: "passed_ids"
    assert False
""".lstrip())
    result, report, _ = _run(project, "-q")
    assert result.returncode == 0
    assert report["failed_ids"] == ["test_forge.py::test_forge"]
    assert report["passed_ids"] == []


def test_source_has_no_subprocess_and_respects_size_limits() -> None:
    source = COLLECTOR.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported = {
        alias.name.split(".", 1)[0]
        for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    assert "subprocess" not in imported
    assert len(source.splitlines()) <= 200
    assert source.isascii()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            assert node.end_lineno is not None
            assert node.end_lineno - node.lineno + 1 <= 50, node.name
