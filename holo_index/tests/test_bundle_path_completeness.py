"""Complete-or-empty bounds for repository-local bundle discovery."""

from __future__ import annotations

import ast
import inspect
import os
from pathlib import Path

import pytest

from holo_index.cli import bundle_path_confinement as confinement
from holo_index.cli.commands import bundle_json


@pytest.mark.parametrize("match_name", ["a_match.py", "z_match.py"])
def test_module_walk_entry_overflow_fails_empty_regardless_of_match_order(
    tmp_path: Path,
    monkeypatch,
    match_name: str,
) -> None:
    repo_root = tmp_path / "repo"
    module_dir = repo_root / "modules" / "communication" / "example"
    module_dir.mkdir(parents=True)
    for name in (match_name, "m_other.py", "n_other.py"):
        (module_dir / name).write_text("VALUE = 1\n", encoding="utf-8")
    monkeypatch.setattr(confinement, "LEXICAL_MODULE_MAX_ENTRIES", 2)

    assert confinement._bounded_module_files(repo_root, module_dir) == ()


def test_module_walk_result_is_independent_of_scandir_order(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo_root = tmp_path / "repo"
    module_dir = repo_root / "modules" / "communication" / "example"
    module_dir.mkdir(parents=True)
    for name in ("z.py", "a.py", "m.py"):
        (module_dir / name).write_text("VALUE = 1\n", encoding="utf-8")
    expected = confinement._bounded_module_files(repo_root, module_dir)
    real_scandir = os.scandir

    class ReverseEntries:
        def __init__(self, path) -> None:
            with real_scandir(path) as entries:
                self.entries = list(reversed(list(entries)))

        def __enter__(self):
            return iter(self.entries)

        def __exit__(self, *_args) -> None:
            return None

    monkeypatch.setattr(os, "scandir", ReverseEntries)
    assert confinement._bounded_module_files(repo_root, module_dir) == expected


def test_module_walk_depth_overflow_fails_empty_not_partial(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo_root = tmp_path / "repo"
    module_dir = repo_root / "modules" / "communication" / "example"
    nested = module_dir / "one" / "two"
    nested.mkdir(parents=True)
    (module_dir / "partial.py").write_text("VALUE = 1\n", encoding="utf-8")
    (nested / "deep.py").write_text("VALUE = 2\n", encoding="utf-8")
    monkeypatch.setattr(confinement, "LEXICAL_MODULE_MAX_DEPTH", 1)

    assert confinement._bounded_module_files(repo_root, module_dir) == ()


def test_module_walk_scandir_error_fails_empty_not_partial(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo_root = tmp_path / "repo"
    module_dir = repo_root / "modules" / "communication" / "example"
    nested = module_dir / "nested"
    nested.mkdir(parents=True)
    (module_dir / "partial.py").write_text("VALUE = 1\n", encoding="utf-8")
    real_scandir = os.scandir

    def error_on_nested(path):
        if Path(path) == nested:
            raise OSError("simulated scan failure")
        return real_scandir(path)

    monkeypatch.setattr(os, "scandir", error_on_nested)
    assert confinement._bounded_module_files(repo_root, module_dir) == ()


def test_bundle_handler_meets_wsp62_function_threshold() -> None:
    function = ast.parse(inspect.getsource(bundle_json.handle_bundle_json)).body[0]

    assert function.end_lineno - function.lineno + 1 <= 50
