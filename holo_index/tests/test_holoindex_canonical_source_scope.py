"""Regressions for canonical HoloIndex source-set identities."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from holo_index.core.indexing_engine import index_wsp_entries
from holo_index.source_scope import canonical_source_scope_id
from holo_index.symbol_indexer import index_symbol_entries


class _Collection:
    def __init__(self) -> None:
        self.add_calls: list[dict[str, Any]] = []

    def add(self, **kwargs: Any) -> None:
        self.add_calls.append(kwargs)


class _Holo:
    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root
        self.symbol_collection = _Collection()
        self.wsp_collection = _Collection()
        self.wsp_summary: dict[str, Any] = {}
        self.wsp_summary_file = project_root / "wsp_summary.json"

    def _reset_collection(self, _name: str) -> _Collection:
        return _Collection()

    def _get_embedding(self, _text: str) -> list[float]:
        return [0.1]

    def _infer_cube_tag(self, *_values: Any) -> None:
        return None

    def _log_agent_action(self, *_values: Any) -> None:
        return None


def _write_python(root: Path, relative: str) -> None:
    target = root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("def indexed_symbol():\n    return True\n", encoding="utf-8")


def test_default_symbol_scope_covers_all_three_canonical_roots(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_python(tmp_path, "modules/example.py")
    _write_python(tmp_path, "scripts/tool.py")
    _write_python(tmp_path, "holo_index/helper.py")
    monkeypatch.delenv("HOLO_SYMBOL_ROOTS", raising=False)
    monkeypatch.setenv("HOLO_SYMBOL_MAX_FILES", "0")
    monkeypatch.setenv("HOLO_SYMBOL_MAX_ENTRIES", "0")

    result = index_symbol_entries(_Holo(tmp_path))

    assert result.discovered_count == 3
    assert result.processed_count == 3
    assert result.complete is True
    assert result.source_scope_id == canonical_source_scope_id(
        "navigation_symbols"
    )


def test_narrowed_symbol_roots_never_claim_canonical_scope(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_python(tmp_path, "modules/example.py")
    _write_python(tmp_path, "scripts/tool.py")
    monkeypatch.setenv("HOLO_SYMBOL_ROOTS", "modules")
    monkeypatch.setenv("HOLO_SYMBOL_MAX_FILES", "0")
    monkeypatch.setenv("HOLO_SYMBOL_MAX_ENTRIES", "0")

    result = index_symbol_entries(_Holo(tmp_path))

    assert result.discovered_count == 1
    assert result.complete is True
    assert result.source_scope_id == ""


def test_symbol_cap_makes_canonical_refresh_incomplete(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_python(tmp_path, "modules/a.py")
    _write_python(tmp_path, "modules/b.py")
    monkeypatch.delenv("HOLO_SYMBOL_ROOTS", raising=False)
    monkeypatch.setenv("HOLO_SYMBOL_MAX_FILES", "1")
    monkeypatch.setenv("HOLO_SYMBOL_MAX_ENTRIES", "0")

    result = index_symbol_entries(_Holo(tmp_path))

    assert result.discovered_count == 2
    assert result.processed_count == 1
    assert result.complete is False
    assert "cap truncated" in (result.warning or "")


def test_wsp_custom_path_never_claims_framework_scope(tmp_path: Path) -> None:
    custom = tmp_path / "custom"
    custom.mkdir()
    (custom / "WSP_999_Custom.md").write_text(
        "# WSP 999\nCustom protocol.\n",
        encoding="utf-8",
    )

    result = index_wsp_entries(_Holo(tmp_path), paths=[custom])

    assert result.complete is True
    assert result.source_scope_id == ""


def test_default_wsp_path_claims_framework_scope(tmp_path: Path) -> None:
    framework = tmp_path / "WSP_framework" / "src"
    framework.mkdir(parents=True)
    (framework / "WSP_00_Test.md").write_text(
        "# WSP 00\nCanonical protocol.\n",
        encoding="utf-8",
    )

    result = index_wsp_entries(_Holo(tmp_path))

    assert result.complete is True
    assert result.source_scope_id == canonical_source_scope_id("navigation_wsp")
