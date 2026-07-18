"""Embedding-space and generation-pinning owner-service regressions."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

import pytest

from modules.infrastructure.foundups_mcp_bridge.tests.test_holo_query_service import (
    BASELINE_COLLECTIONS,
    _Backend,
    _query,
    _raw_result,
    _receipt,
    _service,
)


def test_runtime_embedding_space_mismatch_never_claims_current(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    backend = _Backend()
    backend.collection_embedding_space_map = {
        name: ("sha256:" + ("2" * 64))
        for name in BASELINE_COLLECTIONS
    }
    raw = dict(_raw_result())
    metadata = dict(raw["metadata"])
    metadata["collection_embedding_space_map"] = dict(
        backend.collection_embedding_space_map
    )
    raw["metadata"] = metadata
    backend.result = raw
    owner = _service(tmp_path, monkeypatch, backend=backend)
    try:
        result = _query(owner)
        assert result["ok"] is False
        assert result["freshness"] == "STALE"
        assert result["error"] == "EMBEDDING_SPACE_MISMATCH"
        assert any(
            reason.startswith("embedding_space_mismatch:")
            for reason in result["stale_reasons"]
        )
    finally:
        owner.close()


def test_backend_space_change_during_search_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    changed = "sha256:" + ("3" * 64)

    class ChangingBackend(_Backend):
        def search(
            self, query: str, *, limit: int, doc_type_filter: str
        ) -> Mapping[str, Any]:
            self.collection_embedding_space_map = {
                name: changed for name in BASELINE_COLLECTIONS
            }
            raw = dict(self.result)
            metadata = dict(raw["metadata"])
            metadata["collection_embedding_space_map"] = dict(
                self.collection_embedding_space_map
            )
            raw["metadata"] = metadata
            return raw

    owner = _service(tmp_path, monkeypatch, backend=ChangingBackend())
    try:
        result = _query(owner)
        assert result["ok"] is False
        assert result["error"] == "EMBEDDING_SPACE_MISMATCH"
        assert result["freshness"] == "STALE"
    finally:
        owner.close()


def test_generation_unbound_backend_cache_is_disabled(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    stale = _raw_result()
    stale["code_hits"][0]["path"] = "modules/stale_generation.py"

    class CachedBackend(_Backend):
        def __init__(self) -> None:
            super().__init__()
            self.search_cache = object()

        def search(
            self, query: str, *, limit: int, doc_type_filter: str
        ) -> Mapping[str, Any]:
            return stale if self.search_cache is not None else self.result

    backend = CachedBackend()
    owner = _service(tmp_path, monkeypatch, backend=backend)
    try:
        result = _query(owner)
        assert result["ok"] is True
        assert backend.search_cache is None
        assert result["raw_result"] == _raw_result()
    finally:
        owner.close()


def test_resident_backend_is_pinned_to_first_proven_generation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    generation = {"value": "generation-1"}
    backend = _Backend()
    owner = _service(
        tmp_path,
        monkeypatch,
        backend=backend,
        receipt_loader=lambda _path: _receipt(generation=generation["value"]),
    )
    try:
        assert _query(owner)["ok"] is True
        generation["value"] = "generation-2"
        result = _query(owner)
        assert result["ok"] is False
        assert result["error"] == "QUERY_OWNER_POISONED"
        assert result["stale_reasons"] == ["owner_backend_generation_changed"]
        assert backend.search_calls == 1
    finally:
        owner.close()


def test_generation_change_during_query_fails_closed_with_raw_result(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    receipts = iter([_receipt(generation="generation-1"), _receipt(generation="generation-2")])
    raw = _raw_result()
    owner = _service(
        tmp_path,
        monkeypatch,
        backend=_Backend(raw),
        receipt_loader=lambda _path: next(receipts),
    )
    try:
        result = _query(owner)
        assert result["error"] == "GENERATION_CHANGED_DURING_QUERY"
        assert result["freshness"] == "STALE"
        assert "freshness_generation_changed_during_query" in result["stale_reasons"]
        assert "freshness_receipt_digest_changed_during_query" in result["stale_reasons"]
        assert result["raw_result"] == raw
    finally:
        owner.close()
