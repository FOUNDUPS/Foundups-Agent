"""Unauthenticated collection-mode pytest reporter for one registry shard."""

from __future__ import annotations

import json
from importlib.machinery import PathFinder
import os
from pathlib import Path
import sys
import tempfile
from typing import Any, Sequence

import pytest

SCHEMA_VERSION = "wre_pytest_collection_report.v3"
MAX_COLLECTED_IDS = 100_000


class _ArchiveImportGuard:
    __slots__ = ("allowed", "blocked")

    def __init__(self) -> None:
        self.allowed = tuple(Path(value).resolve() for value in {
            str(Path.cwd()), sys.base_prefix, sys.prefix,
        })
        self.blocked: set[str] = set()

    def find_spec(self, fullname: str, path: Any = None, target: Any = None):
        spec = PathFinder.find_spec(fullname, path, target)
        origin = getattr(spec, "origin", None)
        if spec is None or origin in {None, "built-in", "frozen"}:
            return spec
        resolved = Path(origin).resolve(strict=False)
        if any(resolved == root or root in resolved.parents for root in self.allowed):
            return spec
        self.blocked.add(str(resolved))
        raise ImportError(f"archive_import_root_rejected:{fullname}")


class _CollectionPlugin:
    __slots__ = ("collected", "errors", "guard")

    def __init__(self, guard: _ArchiveImportGuard) -> None:
        self.collected: set[str] = set()
        self.errors: list[dict[str, str]] = []
        self.guard = guard

    @pytest.hookimpl(wrapper=True, tryfirst=True)
    def pytest_collection_modifyitems(self, items: list[Any]):
        self.collected.update(str(item.nodeid) for item in items)
        yield
        self.collected.update(str(item.nodeid) for item in items)

    def pytest_collectreport(self, report: Any) -> None:
        if report.failed:
            self.errors.append({
                "nodeid": str(report.nodeid),
                "detail": str(report.longrepr).replace("\x00", "")[:4096],
            })

def main(argv: Sequence[str] | None = None) -> int:
    try:
        output, paths = _parse(list(sys.argv[1:] if argv is None else argv))
        guard = _ArchiveImportGuard()
        plugin = _CollectionPlugin(guard)
        trusted_builder = _build_report
        exit_code = _run(paths, plugin)
        if _build_report is not trusted_builder:
            raise ValueError("collector_report_builder_mutated")
        report = trusted_builder(plugin, exit_code)
        _atomic_write(output, report)
        return 0 if report["collection_reported_complete"] else 1
    except (OSError, ValueError) as exc:
        print(f"wre_pytest_collection_error:{exc}", file=sys.stderr)
        return 2


def _parse(argv: Sequence[str]) -> tuple[Path, tuple[str, ...]]:
    if len(argv) < 4 or argv[0] != "--output" or argv[2] != "--":
        raise ValueError("usage: --output ABSOLUTE_PATH -- TEST_PATHS")
    invoked = Path(sys.argv[0])
    if not invoked.is_absolute() or invoked.resolve() != Path(__file__).resolve():
        raise ValueError("collector_requires_absolute_trusted_script_path")
    output = Path(argv[1])
    paths = tuple(argv[3:])
    if not output.is_absolute() or not paths:
        raise ValueError("collector_arguments_invalid")
    if any(not _relative_test_path(value) for value in paths):
        raise ValueError("collector_test_path_invalid")
    parent = output.parent.resolve(strict=True)
    repo = Path(__file__).resolve().parents[4]
    if parent == repo or repo in parent.parents:
        raise ValueError("output_path_must_be_outside_repository")
    return parent / output.name, paths


def _relative_test_path(value: str) -> bool:
    if not isinstance(value, str) or not value or "\\" in value:
        return False
    path = Path(value)
    return bool(
        not path.is_absolute() and ".." not in path.parts
        and path.name.startswith("test_") and path.suffix == ".py"
    )


def _run(paths: Sequence[str], plugin: _CollectionPlugin) -> int:
    old_path = list(sys.path)
    old_meta_path = list(sys.meta_path)
    old_addopts = os.environ.pop("PYTEST_ADDOPTS", None)
    old_autoload = os.environ.get("PYTEST_DISABLE_PLUGIN_AUTOLOAD")
    os.environ["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    sys.path.insert(0, str(Path.cwd()))
    sys.meta_path.insert(0, plugin.guard)
    try:
        exit_code = int(pytest.main([
            "-p", "no:cacheprovider", "-o", "addopts=", "--collect-only",
            "--quiet", *paths,
        ], plugins=[plugin]))
        if not sys.meta_path or sys.meta_path[0] is not plugin.guard:
            raise ValueError("archive_import_guard_removed")
        return exit_code
    finally:
        sys.path[:] = old_path
        sys.meta_path[:] = old_meta_path
        _restore("PYTEST_ADDOPTS", old_addopts)
        _restore("PYTEST_DISABLE_PLUGIN_AUTOLOAD", old_autoload)


def _build_report(plugin: _CollectionPlugin, exit_code: int) -> dict[str, Any]:
    if len(plugin.collected) > MAX_COLLECTED_IDS:
        plugin.errors.append({
            "nodeid": "collection", "detail": "collected_id_limit_exceeded",
        })
    return {
        "schema_version": SCHEMA_VERSION,
        "collection_reported_complete": not plugin.errors
        and bool(plugin.collected) and exit_code == 0,
        "pytest_exit_code": exit_code,
        "collection_errors": sorted(
            plugin.errors, key=lambda item: (item["nodeid"], item["detail"])
        ),
        "collected_ids": sorted(plugin.collected),
        "test_body_execution_absence_verified": False,
        "ordinary_import_guard_reported_passed": not plugin.guard.blocked,
        "blocked_import_origins": sorted(plugin.guard.blocked),
        "collector_integrity_verified": False,
    }


def _restore(name: str, value: str | None) -> None:
    if value is None:
        os.environ.pop(name, None)
    else:
        os.environ[name] = value


def _atomic_write(output: Path, report: dict[str, Any]) -> None:
    data = (json.dumps(
        report, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ) + "\n").encode("ascii")
    temporary = ""
    try:
        with tempfile.NamedTemporaryFile(
            dir=output.parent, prefix=".wre-collection-", suffix=".tmp",
            delete=False,
        ) as handle:
            temporary = handle.name
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, output)
    finally:
        if temporary and os.path.exists(temporary):
            os.unlink(temporary)


if __name__ == "__main__":
    raise SystemExit(main())
