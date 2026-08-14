"""Shared canonical fixtures for HoloIndex owner-service tests."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from holo_index.freshness_receipt import ALL_COLLECTIONS


TOKEN = "owner-service-test-token-with-strong-length"
SHA = "a" * 40
QUERY = "find the operational contract"
SPACE_FINGERPRINT = "sha256:" + ("1" * 64)


def _raw_result(*, mode: str = "semantic", error: str = "") -> Mapping[str, Any]:
    """Return a producer-shaped success or intentional producer error payload."""
    if error:
        return {"metadata": {"error": error}}
    code = [{
        "need": "example", "location": "modules/example/src/example.py:example()",
        "similarity": "91.0%", "cube": "example", "type": "code",
        "priority": 5.0, "preview": "example", "path": "modules/example/src/example.py",
    }]
    wsp = [{
        "wsp": "WSP_97", "title": "System Execution", "summary": "verified",
        "path": "WSP_framework/src/WSP_97_System_Execution_Prompting_Protocol.md",
        "similarity": "90.0%", "cube": "WSP", "type": "wsp", "priority": 5.0,
    }]
    docs = [{
        "title": "Example", "summary": "module", "path": "modules/example/README.md",
        "slice_id": None, "similarity": "80.0%", "type": "docs", "priority": 3.0,
    }]
    knowledge = [{
        "title": "Paper", "summary": "research",
        "path": "WSP_knowledge/docs/Papers/example.md", "slice_id": None,
        "similarity": "70.0%", "type": "knowledge", "priority": 3.0,
    }]
    empty: list[Mapping[str, Any]] = []
    backend_map = {name: "sentence_transformers" for name in ALL_COLLECTIONS}
    space_map = {name: SPACE_FINGERPRINT for name in ALL_COLLECTIONS}
    return {
        "code_hits": code, "wsp_hits": wsp, "test_hits": empty, "code": code,
        "wsps": wsp, "tests": empty, "skills": empty, "skill_hits": empty,
        "symbol_hits": empty, "docs_hits": docs, "knowledge_hits": knowledge,
        "docs": docs, "knowledge": knowledge, "work_ledger_hits": empty,
        "work_ledger": empty,
        "metadata": {
            "query": QUERY, "code_count": 1, "wsp_count": 1, "test_count": 0,
            "skill_count": 0, "symbol_count": 0, "docs_count": 1,
            "knowledge_count": 1, "work_ledger_count": 0,
            "timestamp": "2026-08-15T00:00:00+00:00", "cached": False,
            "retrieval_mode": mode,
            "embedding_backend": "sentence_transformers" if mode == "semantic" else "none",
            "backend_quality": "production", "quality_gate": "PASS",
            "routing_active": False, "collection_backend_map": backend_map,
            "collection_embedding_space_map": space_map,
        },
    }


class _Backend:
    def __init__(self, result: Mapping[str, Any] | None = None, *, mode: str = "semantic") -> None:
        self.result = result or _raw_result(mode=mode)
        self.retrieval_mode = mode
        self.collection_backend_map = {
            name: "sentence_transformers" for name in ALL_COLLECTIONS
        }
        self.collection_embedding_space_map = {
            name: SPACE_FINGERPRINT for name in ALL_COLLECTIONS
        }
        self.search_calls = 0
        self.index_calls = 0

    def search(self, query: str, *, limit: int, doc_type_filter: str) -> Mapping[str, Any]:
        self.search_calls += 1
        result = deepcopy(dict(self.result))
        metadata = result.get("metadata")
        if isinstance(metadata, Mapping) and "query" in metadata:
            result["metadata"] = {**metadata, "query": query}
        return result

    def index_code_entries(self) -> None:
        self.index_calls += 1
        raise AssertionError("query owner attempted indexing")

    def index_wsp_entries(self) -> None:
        self.index_calls += 1
        raise AssertionError("query owner attempted indexing")


__all__ = ["QUERY", "SHA", "SPACE_FINGERPRINT", "TOKEN", "_Backend", "_raw_result"]
