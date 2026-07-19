"""Regression tests for complete, bounded HoloIndex source indexing."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from holo_index.core.indexing_engine import index_skillz_entries
from holo_index.symbol_indexer import index_symbol_entries


class _Collection:
    def __init__(self) -> None:
        self.add_calls: list[dict[str, Any]] = []

    def add(self, **kwargs: Any) -> None:
        self.add_calls.append(kwargs)


class _BatchModel:
    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    def encode(self, values: list[str], **_kwargs: Any) -> list[list[float]]:
        self.calls.append(list(values))
        return [[float(index), 1.0] for index, _value in enumerate(values)]


class _Holo:
    def __init__(self, project_root: Path, *, model: Any | None = None) -> None:
        self.project_root = project_root
        self.model = model
        self.symbol_collection = _Collection()
        self.skill_collection = _Collection()
        self.logged: list[tuple[str, str]] = []

    def _reset_collection(self, name: str) -> _Collection:
        collection = _Collection()
        if name == "navigation_symbols":
            self.symbol_collection = collection
        elif name == "navigation_skills":
            self.skill_collection = collection
        return collection

    def _get_embedding(self, _text: str) -> list[float]:
        return [0.1, 0.2]

    def _log_agent_action(self, message: str, level: str) -> None:
        self.logged.append((level, message))


def _symbol_metadata(holo: _Holo) -> list[dict[str, Any]]:
    return [
        metadata
        for call in holo.symbol_collection.add_calls
        for metadata in call["metadatas"]
    ]


def test_unparseable_source_is_accounted_without_invented_symbol(tmp_path: Path) -> None:
    source = tmp_path / "broken.py"
    source.write_text("def broken(:\n    pass\n", encoding="utf-8")
    model = _BatchModel()
    holo = _Holo(tmp_path, model=model)

    result = index_symbol_entries(holo, roots=[tmp_path])

    assert result.discovered_count == 1
    assert result.processed_count == 1
    assert result.failed_count == 0
    assert result.fallback_count == 1
    assert result.complete is True
    assert result.indexed_count == 1
    metadata = _symbol_metadata(holo)[0]
    assert metadata["type"] == "unparsed_source"
    assert metadata["symbol"] == ""
    assert metadata["parse_status"] == "SyntaxError"
    assert model.calls and "def broken" not in model.calls[0][0]


def test_utf8_bom_source_is_parsed_as_python(tmp_path: Path) -> None:
    source = tmp_path / "bom.py"
    source.write_bytes(b"\xef\xbb\xbfdef bom_symbol():\n    return True\n")
    holo = _Holo(tmp_path, model=_BatchModel())

    result = index_symbol_entries(holo, roots=[tmp_path])

    assert result.complete is True
    assert result.fallback_count == 0
    metadata = _symbol_metadata(holo)[0]
    assert metadata["type"] == "symbol"
    assert metadata["symbol"].startswith("bom_symbol(")


def test_unparseable_and_valid_sources_are_both_in_collection(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("def valid():\n    pass\n", encoding="utf-8")
    (tmp_path / "b.py").write_text("class Broken(\n", encoding="utf-8")
    holo = _Holo(tmp_path, model=_BatchModel())

    result = index_symbol_entries(holo, roots=[tmp_path])

    assert result.discovered_count == result.processed_count == 2
    assert result.indexed_count == 2
    assert result.fallback_count == 1
    assert result.complete is True
    assert {item["type"] for item in _symbol_metadata(holo)} == {
        "symbol",
        "unparsed_source",
    }


def test_symbol_embeddings_are_bounded_into_collection_batches(tmp_path: Path) -> None:
    source = tmp_path / "many.py"
    source.write_text(
        "\n".join(f"def symbol_{index}(): pass" for index in range(5001)),
        encoding="utf-8",
    )
    model = _BatchModel()
    holo = _Holo(tmp_path, model=model)

    result = index_symbol_entries(holo, roots=[tmp_path])

    assert result.complete is True
    assert result.indexed_count == 5001
    assert [len(call) for call in model.calls] == [5000, 1]
    assert [len(call["ids"]) for call in holo.symbol_collection.add_calls] == [5000, 1]


def test_true_source_io_failure_remains_incomplete(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "source.py"
    source.write_text("def present(): pass\n", encoding="utf-8")
    import holo_index.symbol_indexer as module

    def _raise(_path: Path):
        raise OSError("simulated read failure")

    monkeypatch.setattr(module.tokenize, "open", _raise)
    result = index_symbol_entries(_Holo(tmp_path), roots=[tmp_path])

    assert result.failed_count == 1
    assert result.fallback_count == 0
    assert result.complete is False


def test_skillz_agent_identifiers_accept_mixed_scalar_values(tmp_path: Path) -> None:
    skill = tmp_path / "holo_index" / "skillz" / "mixed_agents" / "SKILLz.md"
    skill.parent.mkdir(parents=True)
    skill.write_text(
        "---\n"
        "name: mixed_agents\n"
        "description: Mixed identifiers\n"
        "agents: [97, 0102, worker]\n"
        "primary_agent: worker\n"
        "---\n"
        "# Mixed agents\n",
        encoding="utf-8",
    )
    holo = _Holo(tmp_path)

    result = index_skillz_entries(holo)

    assert result.complete is True
    assert result.failed_count == 0
    metadata = holo.skill_collection.add_calls[0]["metadatas"][0]
    assert metadata["agents"] == "97,66,worker"
