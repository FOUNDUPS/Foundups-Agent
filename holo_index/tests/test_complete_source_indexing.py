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


class _StatefulCollection:
    def __init__(self, metadata: dict[str, str]) -> None:
        self.metadata = dict(metadata)
        self.records: dict[str, dict[str, Any]] = {}
        self.upsert_calls: list[list[str]] = []
        self.delete_calls: list[list[str]] = []

    def get(
        self,
        *,
        ids: list[str] | None = None,
        include: list[str] | None = None,
    ) -> dict[str, Any]:
        selected = (
            list(self.records)
            if ids is None
            else [value for value in ids if value in self.records]
        )
        return {
            "ids": selected,
            "documents": [self.records[value]["document"] for value in selected],
            "metadatas": [self.records[value]["metadata"] for value in selected],
        }

    def upsert(self, **kwargs: Any) -> None:
        self.upsert_calls.append(list(kwargs["ids"]))
        for item_id, document, metadata, embedding in zip(
            kwargs["ids"],
            kwargs["documents"],
            kwargs["metadatas"],
            kwargs["embeddings"],
        ):
            self.records[item_id] = {
                "document": document,
                "metadata": metadata,
                "embedding": embedding,
            }

    def add(self, **kwargs: Any) -> None:
        self.upsert(**kwargs)

    def update(self, *, ids: list[str], metadatas: list[dict[str, Any]]) -> None:
        for item_id, metadata in zip(ids, metadatas):
            self.records[item_id]["metadata"] = metadata

    def delete(self, *, ids: list[str]) -> None:
        self.delete_calls.append(list(ids))
        for item_id in ids:
            self.records.pop(item_id, None)

    def count(self) -> int:
        return len(self.records)


class _StatefulHolo:
    def __init__(self, project_root: Path, model: _BatchModel) -> None:
        self.project_root = project_root
        self.model = model
        self.index_embedding_backend = "sentence_transformers"
        self.index_embedding_model_id = "test-model"
        self.index_embedding_space_fingerprint = "sha256:" + ("a" * 64)
        self.symbol_collection = _StatefulCollection(self.embedding_metadata)
        self.reset_count = 0

    @property
    def embedding_metadata(self) -> dict[str, str]:
        return {
            "embedding_backend": self.index_embedding_backend,
            "embedding_model": self.index_embedding_model_id,
            "embedding_space_fingerprint": self.index_embedding_space_fingerprint,
        }

    def _reset_collection(self, _name: str) -> _StatefulCollection:
        self.reset_count += 1
        self.symbol_collection = _StatefulCollection(self.embedding_metadata)
        return self.symbol_collection

    def _get_embedding(self, _text: str) -> list[float]:
        return [0.1, 0.2]

    def _log_agent_action(self, _message: str, _level: str) -> None:
        return None


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


def test_unchanged_stable_records_reuse_exact_space_embeddings(tmp_path: Path) -> None:
    source = tmp_path / "source.py"
    source.write_text("def stable():\n    return True\n", encoding="utf-8")
    model = _BatchModel()
    holo = _StatefulHolo(tmp_path, model)

    first = index_symbol_entries(holo, roots=[tmp_path])
    first_id = next(iter(holo.symbol_collection.records))
    model.calls.clear()
    second = index_symbol_entries(holo, roots=[tmp_path])

    assert first.reused_count == 0
    assert second.reused_count == 1
    assert model.calls == []
    assert next(iter(holo.symbol_collection.records)) == first_id
    assert holo.reset_count == 0


def test_changed_document_reembeds_same_stable_symbol_id(tmp_path: Path) -> None:
    source = tmp_path / "source.py"
    source.write_text("def stable():\n    return True\n", encoding="utf-8")
    model = _BatchModel()
    holo = _StatefulHolo(tmp_path, model)
    index_symbol_entries(holo, roots=[tmp_path])
    first_id = next(iter(holo.symbol_collection.records))
    model.calls.clear()
    source.write_text(
        "def stable():\n    \"\"\"Changed evidence.\"\"\"\n    return True\n",
        encoding="utf-8",
    )

    result = index_symbol_entries(holo, roots=[tmp_path])

    assert result.reused_count == 0
    assert len(model.calls) == 1
    assert next(iter(holo.symbol_collection.records)) == first_id


def test_stale_stable_record_is_deleted_after_reconciliation(tmp_path: Path) -> None:
    source = tmp_path / "source.py"
    source.write_text("def removed():\n    return True\n", encoding="utf-8")
    holo = _StatefulHolo(tmp_path, _BatchModel())
    index_symbol_entries(holo, roots=[tmp_path])
    stale_id = next(iter(holo.symbol_collection.records))
    source.unlink()

    result = index_symbol_entries(holo, roots=[tmp_path])

    assert result.indexed_count == 0
    assert stale_id not in holo.symbol_collection.records
    assert holo.symbol_collection.delete_calls == [[stale_id]]


def test_embedding_space_mismatch_forces_reset_and_reembedding(tmp_path: Path) -> None:
    source = tmp_path / "source.py"
    source.write_text("def stable():\n    return True\n", encoding="utf-8")
    model = _BatchModel()
    holo = _StatefulHolo(tmp_path, model)
    index_symbol_entries(holo, roots=[tmp_path])
    model.calls.clear()
    holo.symbol_collection.metadata["embedding_space_fingerprint"] = (
        "sha256:" + ("b" * 64)
    )

    result = index_symbol_entries(holo, roots=[tmp_path])

    assert result.reused_count == 0
    assert len(model.calls) == 1
    assert holo.reset_count == 1


def test_stable_records_are_worktree_path_independent(tmp_path: Path) -> None:
    roots = [tmp_path / "one", tmp_path / "two"]
    payloads: list[dict[str, Any]] = []
    for root in roots:
        source = root / "modules" / "sample.py"
        source.parent.mkdir(parents=True)
        source.write_text("def stable():\n    return True\n", encoding="utf-8")
        holo = _Holo(root, model=_BatchModel())
        index_symbol_entries(holo, roots=[root / "modules"])
        payloads.append(holo.symbol_collection.add_calls[0])

    assert payloads[0]["ids"] == payloads[1]["ids"]
    assert payloads[0]["documents"] == payloads[1]["documents"]
    assert payloads[0]["metadatas"] == payloads[1]["metadatas"]


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
