"""Tests for truthful WSP Test Registry indexing."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

os.environ.setdefault("ANONYMIZED_TELEMETRY", "false")
os.environ.setdefault("HOLO_SKIP_MODEL", "1")

from holo_index.core.holo_index import HoloIndex
from holo_index.core.indexing_engine import index_test_registry


class FakeCollection:
    def __init__(self) -> None:
        self.add_calls: list[dict] = []

    def add(self, **kwargs) -> None:
        self.add_calls.append(kwargs)


class FakeHolo:
    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root
        self.test_collection = FakeCollection()
        self.reset_calls: list[str] = []
        self.logs: list[tuple[str, str]] = []

    def _log_agent_action(self, message: str, action_tag: str) -> None:
        self.logs.append((message, action_tag))

    def _get_embedding(self, text: str) -> list[float]:
        return [float(len(text))]

    def _reset_collection(self, name: str) -> FakeCollection:
        self.reset_calls.append(name)
        return FakeCollection()


def _write_registry(root: Path, payload) -> None:
    target = root / "WSP_knowledge" / "WSP_Test_Registry.json"
    target.parent.mkdir(parents=True)
    target.write_text(json.dumps(payload), encoding="utf-8")


def test_missing_registry_returns_empty_result_without_reset(tmp_path: Path) -> None:
    holo = FakeHolo(tmp_path)

    result = index_test_registry(holo)

    assert result.is_empty is True
    assert result.collection_name == "navigation_tests"
    assert holo.reset_calls == []


def test_canonical_registry_envelope_indexes_test_list(tmp_path: Path) -> None:
    _write_registry(
        tmp_path,
        {
            "version": "1.0",
            "tests": [
                {
                    "id": "test_one",
                    "path": "modules/example/tests/test_one.py",
                    "description": "first",
                    "capabilities": ["unit", "fast"],
                    "execution_type": "unit",
                    "owner": "modules/example/demo",
                    "suite_class": "unit",
                    "shard_id": "modules-example-demo-unit",
                    "collectable": True,
                    "quarantine_reasons": [],
                },
                {
                    "id": "test_two",
                    "path": "modules/example/tests/test_two.py",
                    "description": "second",
                    "capabilities": ["integration"],
                    "execution_type": "integration",
                },
            ],
        },
    )
    holo = FakeHolo(tmp_path)

    result = index_test_registry(holo)

    assert result.success is True
    assert result.complete is True
    assert result.discovered_count == 2
    assert result.indexed_count == 2
    assert holo.reset_calls == ["navigation_tests"]
    assert len(holo.test_collection.add_calls) == 1
    payload = holo.test_collection.add_calls[0]
    assert payload["metadatas"][0]["test_id"] == "test_one"
    assert payload["metadatas"][0]["capabilities"] == "unit, fast"
    assert payload["metadatas"][0]["owner"] == "modules/example/demo"
    assert payload["metadatas"][0]["suite_class"] == "unit"
    assert payload["metadatas"][0]["shard_id"] == "modules-example-demo-unit"
    assert payload["metadatas"][0]["collectable"] is True


def test_legacy_mapping_registry_remains_supported(tmp_path: Path) -> None:
    _write_registry(
        tmp_path,
        {
            "one": {
                "id": "test_one",
                "path": "test_one.py",
                "description": "legacy",
            }
        },
    )
    holo = FakeHolo(tmp_path)

    result = index_test_registry(holo)

    assert result.indexed_count == 1
    assert holo.reset_calls == ["navigation_tests"]


def test_invalid_registry_shape_does_not_reset_existing_collection(tmp_path: Path) -> None:
    _write_registry(tmp_path, {"version": "1.0", "tests": "not-a-list"})
    holo = FakeHolo(tmp_path)

    result = index_test_registry(holo)

    assert result.is_empty is True
    assert "1 malformed test entry" in (result.warning or "")
    assert result.failed_count == 1
    assert result.complete is False
    assert holo.reset_calls == []


def test_invalid_v2_registry_uses_strict_loader_before_reset(tmp_path: Path) -> None:
    _write_registry(tmp_path, {
        "schema_version": "wsp_test_registry.v2",
        "generation_policy": "git-tracked-python-tests.v1",
        "total_tests": 1, "quarantined_tests": 0,
        "tests": [{"path": "tests/test_missing.py"}],
    })
    holo = FakeHolo(tmp_path)
    result = index_test_registry(holo)
    assert result.indexed_count == 0
    assert "Failed to load test registry" in (result.warning or "")
    assert holo.reset_calls == []


def test_mixed_validity_registry_fails_before_collection_reset(tmp_path: Path) -> None:
    _write_registry(
        tmp_path,
        {
            "version": "1.0",
            "tests": [
                {
                    "id": "test_one",
                    "path": "modules/example/tests/test_one.py",
                    "description": "valid row",
                },
                "malformed-row",
            ],
        },
    )
    holo = FakeHolo(tmp_path)

    result = index_test_registry(holo)

    assert result.discovered_count == 2
    assert result.processed_count == 1
    assert result.indexed_count == 0
    assert result.failed_count == 1
    assert result.complete is False
    assert "1 malformed test entry" in (result.warning or "")
    assert holo.reset_calls == []


def test_real_chroma_indexes_canonical_registry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    registry_path = (
        Path(__file__).resolve().parents[2]
        / "WSP_knowledge"
        / "WSP_Test_Registry.json"
    )
    expected = len(json.loads(registry_path.read_text(encoding="utf-8"))["tests"])
    old_initialized = HoloIndex._initialized
    old_shared_state = HoloIndex._shared_state
    HoloIndex._initialized = False
    HoloIndex._shared_state = {}
    monkeypatch.delenv("HOLOINDEX_QUERY_READONLY", raising=False)
    monkeypatch.setenv("HOLO_SKIP_MODEL", "1")
    monkeypatch.setattr(HoloIndex, "_log_agent_action", lambda *args, **kwargs: None)

    try:
        index = HoloIndex(ssd_path=tmp_path / "ssd", quiet=True)
        result = index.index_test_registry()

        assert result.success is True
        assert result.indexed_count == expected
        assert index.test_collection.count() == expected
    finally:
        HoloIndex._initialized = old_initialized
        HoloIndex._shared_state = old_shared_state
