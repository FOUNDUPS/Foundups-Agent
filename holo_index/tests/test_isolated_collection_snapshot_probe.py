"""Tests for isolated persisted-state collection snapshot verification."""

from __future__ import annotations

import json
import sys
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

import holo_index.isolated_collection_snapshot_probe as probe_module
from holo_index.freshness_receipt import (
    ALL_COLLECTIONS,
    BASELINE_QUERY_COLLECTIONS,
    build_freshness_receipt,
)
from holo_index.isolated_collection_snapshot_probe import (
    IsolatedSnapshotProbeError,
    open_persisted_collection_view,
    probe_collection_snapshots,
    verify_collection_snapshots_isolated,
)


FINGERPRINT = "sha256:" + ("1" * 64)


class _Collection:
    def __init__(self, name: str, count: int = 2) -> None:
        self.name = name
        self._count = count
        self.metadata = {
            "embedding_backend": "test-embedding",
            "embedding_model": "test-model",
            "embedding_space_fingerprint": FINGERPRINT,
        }

    def count(self) -> int:
        return self._count

    def get(self, include=None):
        return {
            "ids": [f"{self.name}:{index}" for index in range(self._count)],
            "documents": [
                f"document:{self.name}:{index}" for index in range(self._count)
            ],
            "metadatas": [
                {"path": f"{self.name}/item_{index}.txt"}
                for index in range(self._count)
            ],
            "embeddings": [[float(index)] for index in range(self._count)],
        }


def test_default_client_uses_canonical_vector_store(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    opened: list[str] = []
    client = SimpleNamespace()
    monkeypatch.setitem(
        sys.modules,
        "chromadb",
        SimpleNamespace(
            PersistentClient=lambda *, path: opened.append(path) or client
        ),
    )

    result = probe_module._default_client_factory(tmp_path / "ssd")

    assert result is client
    assert opened == [str(tmp_path / "ssd" / "vectors")]


def _fixture(tmp_path: Path):
    attr_map = {
        "navigation_code": "code_collection",
        "navigation_wsp": "wsp_collection",
        "navigation_tests": "test_collection",
        "navigation_skills": "skill_collection",
        "navigation_symbols": "symbol_collection",
        "navigation_docs": "docs_collection",
        "navigation_knowledge": "knowledge_collection",
        "navigation_work_ledger": "work_ledger_collection",
        "navigation_vocabulary": "vocabulary_collection",
    }
    collections = {name: _Collection(name) for name in ALL_COLLECTIONS}
    holo = SimpleNamespace(
        **{attr: collections[name] for name, attr in attr_map.items()},
        index_embedding_backend="test-embedding",
        index_embedding_model_id="test-model",
        index_embedding_space_fingerprint=FINGERPRINT,
    )
    receipt = build_freshness_receipt(
        holo,
        ssd_path=tmp_path / "ssd",
        repo_root=tmp_path / "repo",
        source="manual_index",
        generated_at="2026-07-19T00:00:00+00:00",
        repo_head_sha="a" * 40,
    )
    client = SimpleNamespace(
        get_collection=lambda name, **_kwargs: collections[name]
    )
    return receipt, collections, client


def test_isolated_probe_accepts_exact_persisted_collections(tmp_path: Path) -> None:
    receipt, collections, _client = _fixture(tmp_path)
    calls: list[tuple[str, object]] = []

    def get_collection(name: str, *, embedding_function):
        calls.append((name, embedding_function))
        return collections[name]

    client = SimpleNamespace(get_collection=get_collection)

    result = probe_collection_snapshots(
        receipt,
        ssd_path=tmp_path / "ssd",
        client_factory=lambda _path: client,
    )

    assert result.ok is True
    assert result.mismatched_collections == ()
    assert calls
    assert all(embedding_function is None for _name, embedding_function in calls)


def test_isolated_probe_rejects_one_persisted_mismatch(tmp_path: Path) -> None:
    receipt, collections, client = _fixture(tmp_path)
    collections["navigation_skills"].get = lambda include=None: {
        "ids": ["navigation_skills:0", "navigation_skills:1"],
        "documents": ["mutated", "mutated"],
        "metadatas": [{"path": "a"}, {"path": "b"}],
        "embeddings": [[0.0], [1.0]],
    }

    result = probe_collection_snapshots(
        receipt,
        ssd_path=tmp_path / "ssd",
        client_factory=lambda _path: client,
    )

    assert result.ok is False
    assert result.mismatched_collections == ("navigation_skills",)
    assert result.error == "COLLECTION_SNAPSHOT_MISMATCH"


def test_isolated_probe_rejects_tampered_receipt(tmp_path: Path) -> None:
    receipt, _collections, client = _fixture(tmp_path)
    tampered = replace(receipt, repo_head_sha="b" * 40)

    result = probe_collection_snapshots(
        tampered,
        ssd_path=tmp_path / "ssd",
        client_factory=lambda _path: client,
    )

    assert result.ok is False
    assert result.error == "INVALID_RECEIPT_INTEGRITY"


def test_isolated_probe_requires_all_baseline_collections(tmp_path: Path) -> None:
    receipt, _collections, client = _fixture(tmp_path)
    incomplete = replace(
        receipt,
        collections=[
            entry
            for entry in receipt.collections
            if entry.name not in BASELINE_QUERY_COLLECTIONS
            or entry.name != "navigation_code"
        ],
    )

    result = probe_collection_snapshots(
        incomplete,
        ssd_path=tmp_path / "ssd",
        client_factory=lambda _path: client,
    )

    assert result.ok is False
    assert result.error == "INVALID_RECEIPT_INTEGRITY"


def test_persisted_view_reopens_all_collections_without_encoder(tmp_path: Path) -> None:
    _receipt, collections, _client = _fixture(tmp_path)
    calls: list[tuple[str, object]] = []

    def get_collection(name: str, *, embedding_function):
        calls.append((name, embedding_function))
        return collections[name]

    client = SimpleNamespace(get_collection=get_collection)

    view = open_persisted_collection_view(
        tmp_path / "ssd",
        client_factory=lambda _path: client,
    )

    assert view.client is client
    assert view.code_collection is collections["navigation_code"]
    assert view.wsp_collection is collections["navigation_wsp"]
    assert view.skill_collection is collections["navigation_skills"]
    assert view.index_embedding_backend == "test-embedding"
    assert view.index_embedding_model_id == "test-model"
    assert view.index_embedding_space_fingerprint == FINGERPRINT
    assert calls
    assert all(embedding_function is None for _name, embedding_function in calls)


def test_persisted_view_marks_unavailable_collection_missing(tmp_path: Path) -> None:
    _receipt, collections, _client = _fixture(tmp_path)

    def get_collection(name: str, *, embedding_function):
        assert embedding_function is None
        if name == "navigation_docs":
            raise RuntimeError("missing")
        return collections[name]

    view = open_persisted_collection_view(
        tmp_path / "ssd",
        client_factory=lambda _path: SimpleNamespace(get_collection=get_collection),
    )

    assert view.docs_collection is None
    assert view.code_collection is collections["navigation_code"]


def test_parent_accepts_generation_bound_isolated_success(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    receipt, _collections, _client = _fixture(tmp_path)
    response = {
        "schema_version": "holoindex_isolated_snapshot_probe.v1",
        "ok": True,
        "generation_id": receipt.generation_id,
        "mismatched_collections": [],
        "error": "",
    }
    monkeypatch.setattr(
        "holo_index.isolated_collection_snapshot_probe.subprocess.run",
        lambda *args, **kwargs: SimpleNamespace(
            returncode=0,
            stdout=json.dumps(response),
            stderr="",
        ),
    )

    failures = verify_collection_snapshots_isolated(
        receipt,
        ssd_path=tmp_path / "ssd",
        repo_root=tmp_path / "repo",
    )

    assert failures == []


@pytest.mark.parametrize(
    "response",
    (
        "not-json",
        json.dumps(
            {
                "schema_version": "holoindex_isolated_snapshot_probe.v1",
                "ok": True,
                "generation_id": "wrong-generation",
                "mismatched_collections": [],
                "error": "",
            }
        ),
        json.dumps(
            {
                "schema_version": "holoindex_isolated_snapshot_probe.v1",
                "ok": True,
                "generation_id": "GENERATION_PLACEHOLDER",
                "mismatched_collections": ["untrusted_collection"],
                "error": "",
            }
        ),
    ),
)
def test_parent_rejects_malformed_or_unbound_probe_response(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    response: str,
) -> None:
    receipt, _collections, _client = _fixture(tmp_path)
    rendered = response.replace("GENERATION_PLACEHOLDER", receipt.generation_id)
    monkeypatch.setattr(
        "holo_index.isolated_collection_snapshot_probe.subprocess.run",
        lambda *args, **kwargs: SimpleNamespace(
            returncode=0,
            stdout=rendered,
            stderr="",
        ),
    )

    with pytest.raises(
        IsolatedSnapshotProbeError,
        match="ISOLATED_PROBE_RESPONSE_INVALID",
    ):
        verify_collection_snapshots_isolated(
            receipt,
            ssd_path=tmp_path / "ssd",
            repo_root=tmp_path / "repo",
        )
