"""Verifier-owned pytest node-ID evidence collector."""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import tempfile
from typing import Any, Sequence

import pytest
SCHEMA_VERSION = "wre_pytest_exact_id_report.v1"
MAX_COLLECTED_IDS = 100_000
_OUTCOME_NAMES = (
    "passed_ids", "failed_ids", "error_ids", "skipped_ids",
    "xfailed_ids", "xpassed_ids", "deselected_ids",
)
_BANNED_ARGS = (
    "-p", "--collect-only", "--co", "--junitxml", "--junit-xml",
    "--json-report", "--json-report-file", "--resultlog", "--trace-config",
)
class _ExactIdPlugin:
    __slots__ = (
        "collected", "deselected", "reports", "collection_errors",
        "_terminal_classifier",
    )
    def __init__(self) -> None:
        self.collected: set[str] = set()
        self.deselected: set[str] = set()
        self.reports: dict[str, list[tuple[str, str, str, str]]] = {}
        self.collection_errors: list[dict[str, str]] = []
        self._terminal_classifier = _terminal_outcome

    @pytest.hookimpl(wrapper=True, tryfirst=True)
    def pytest_collection_modifyitems(self, items: list[Any]):
        self.collected.update(item.nodeid for item in items)
        yield
        self.collected.update(item.nodeid for item in items)

    def pytest_deselected(self, items: list[Any]) -> None:
        ids = {item.nodeid for item in items}
        self.collected.update(ids)
        self.deselected.update(ids)

    def pytest_collectreport(self, report: Any) -> None:
        if report.failed:
            self.collection_errors.append({
                "nodeid": str(report.nodeid),
                "detail": _bounded_text(report.longrepr),
            })

    def pytest_runtest_logreport(self, report: Any) -> None:
        self.reports.setdefault(str(report.nodeid), []).append((
            str(report.when), str(report.outcome),
            str(getattr(report, "wasxfail", "")), _bounded_text(report.longrepr),
        ))

    def build(self, exit_code: int) -> dict[str, Any]:
        if len(self.collected) > MAX_COLLECTED_IDS:
            self.collection_errors.append({
                "nodeid": "collection", "detail": "collected_id_limit_exceeded",
            })
        outcomes = {name: set() for name in _OUTCOME_NAMES}
        outcomes["deselected_ids"].update(self.deselected)
        for nodeid in sorted(self.collected - self.deselected):
            outcome = self._terminal_classifier(self.reports.get(nodeid, []))
            if outcome:
                outcomes[outcome].add(nodeid)
        terminal = set().union(*outcomes.values())
        complete = not self.collection_errors and terminal == self.collected
        return _report(self, outcomes, exit_code, complete)


def _bounded_text(value: Any) -> str:
    return str(value).replace("\x00", "")[:4096]


def _terminal_outcome(reports: Sequence[tuple[str, str, str, str]]) -> str:
    if any(when in {"setup", "teardown"} and outcome == "failed" for when, outcome, _, _ in reports):
        return "error_ids"
    calls = [entry for entry in reports if entry[0] == "call"]
    if any(outcome == "passed" and wasxfail for _, outcome, wasxfail, _ in calls):
        return "xpassed_ids"
    if any(outcome == "failed" and detail.startswith("[XPASS(strict)]") for _, outcome, _, detail in calls):
        return "xpassed_ids"
    if any(outcome == "skipped" and wasxfail for _, outcome, wasxfail, _ in reports):
        return "xfailed_ids"
    if any(outcome == "failed" for _, outcome, _, _ in calls):
        return "failed_ids"
    if any(outcome == "skipped" for _, outcome, _, _ in reports):
        return "skipped_ids"
    if any(outcome == "passed" for _, outcome, _, _ in calls):
        return "passed_ids"
    return ""


def _report(plugin: _ExactIdPlugin, outcomes: dict[str, set[str]], exit_code: int, complete: bool) -> dict[str, Any]:
    result: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "collection_complete": complete,
        "pytest_exit_code": exit_code,
        "collection_errors": sorted(plugin.collection_errors, key=lambda item: (item["nodeid"], item["detail"])),
        "collected_ids": sorted(plugin.collected),
    }
    result.update({name: sorted(values) for name, values in outcomes.items()})
    return result


def _parse(argv: Sequence[str]) -> tuple[Path, list[str]]:
    invoked = Path(sys.argv[0])
    if not invoked.is_absolute() or invoked.resolve() != Path(__file__).resolve():
        raise ValueError("collector_requires_absolute_trusted_script_path")
    if len(argv) < 3 or argv[0] != "--output" or argv[2] != "--":
        raise ValueError("usage: --output ABSOLUTE_PATH -- PYTEST_ARGS")
    output = Path(argv[1])
    if not output.is_absolute():
        raise ValueError("output_path_must_be_absolute")
    _validate_pytest_args(argv[3:])
    return _validated_output(output), list(argv[3:])


def _validate_pytest_args(args: Sequence[str]) -> None:
    for arg in args:
        if any(arg == banned or arg.startswith(banned + "=") for banned in _BANNED_ARGS):
            raise ValueError(f"pytest_argument_forbidden:{arg.split('=', 1)[0]}")
        if arg.startswith("-p"):
            raise ValueError("pytest_argument_forbidden:-p")


def _validated_output(output: Path) -> Path:
    parent = output.parent.resolve(strict=True)
    repo = Path(__file__).resolve().parents[4]
    if output.exists() and output.is_symlink():
        raise ValueError("output_path_must_not_be_symlink")
    if parent == repo or repo in parent.parents:
        raise ValueError("output_path_must_be_outside_repository")
    return parent / output.name


def _atomic_write(output: Path, report: dict[str, Any]) -> None:
    data = (json.dumps(report, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode("utf-8")
    temporary = ""
    try:
        with tempfile.NamedTemporaryFile(dir=output.parent, prefix=".wre-pytest-", suffix=".tmp", delete=False) as handle:
            temporary = handle.name
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, output)
    finally:
        if temporary and os.path.exists(temporary):
            os.unlink(temporary)


def _run_pytest(args: Sequence[str], plugin: _ExactIdPlugin) -> int:
    old_argv = sys.argv
    old_path = list(sys.path)
    old_addopts = os.environ.pop("PYTEST_ADDOPTS", None)
    old_autoload = os.environ.get("PYTEST_DISABLE_PLUGIN_AUTOLOAD")
    os.environ["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    sys.argv = [str(Path(__file__).resolve()), *args]
    sys.path.insert(0, str(Path.cwd()))
    try:
        return int(pytest.main(["-p", "no:cacheprovider", "-o", "addopts=", *args], plugins=[plugin]))
    finally:
        sys.argv = old_argv
        sys.path[:] = old_path
        _restore_env("PYTEST_ADDOPTS", old_addopts)
        _restore_env("PYTEST_DISABLE_PLUGIN_AUTOLOAD", old_autoload)


def _restore_env(name: str, value: str | None) -> None:
    if value is None:
        os.environ.pop(name, None)
    else:
        os.environ[name] = value


def main(argv: Sequence[str] | None = None) -> int:
    try:
        output, args = _parse(list(sys.argv[1:] if argv is None else argv))
        plugin = _ExactIdPlugin()
        trusted_classifier = plugin._terminal_classifier
        exit_code = _run_pytest(args, plugin)
        if plugin._terminal_classifier is not trusted_classifier:
            raise ValueError("collector_classifier_mutated")
        report = plugin.build(exit_code)
        _atomic_write(output, report)
        return 0 if report["collection_complete"] and exit_code in {0, 1} else 1
    except (OSError, ValueError) as exc:
        print(f"wre_pytest_collector_error:{exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
