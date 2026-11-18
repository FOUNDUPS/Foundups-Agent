"""Fail-closed package-path regressions for the root script test alias."""

from __future__ import annotations

import importlib.util
from pathlib import Path


PACKAGE_INIT = Path(__file__).resolve().parents[1] / "scripts" / "__init__.py"
REPO_SCRIPTS = Path(__file__).resolve().parents[4] / "scripts"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(
        name,
        PACKAGE_INIT,
        submodule_search_locations=[str(PACKAGE_INIT.parent)],
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_normal_package_import_does_not_extend_runtime_namespace() -> None:
    module = _load("modules.communication.moltbot_bridge.scripts_probe")
    assert list(module.__path__) == [str(PACKAGE_INIT.parent)]


def test_pytest_top_level_alias_adds_only_exact_repo_scripts(
    tmp_path: Path, monkeypatch,
) -> None:
    foreign = tmp_path / "scripts"
    foreign.mkdir()
    monkeypatch.syspath_prepend(str(tmp_path))

    module = _load("scripts")

    assert list(module.__path__) == [
        str(PACKAGE_INIT.parent),
        str(REPO_SCRIPTS),
    ]
    assert str(foreign) not in module.__path__
