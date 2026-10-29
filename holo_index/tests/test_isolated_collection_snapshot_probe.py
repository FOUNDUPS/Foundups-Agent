"""Tests for isolated persisted-state collection snapshot verification."""

from __future__ import annotations

import json
import sqlite3
import sys
import uuid
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
from holo_index.vector_segment_durability import HNSW_ARTIFACTS, HNSW_SEGMENT_TYPE


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

    def get(self, include=None, limit=None, offset=None):
        start = int(offset or 0)
        stop = start + int(limit) if limit is not None else self._count
        return {
            "ids": [f"{self.name}:{index}" for index in range(start, min(stop, self._count))],
            "documents": [
                f"document:{self.name}:{index}" for index in range(start, min(stop, self._count))
            ],
            "metadatas": [
                {"path": f"{self.name}/item_{index}.txt"}
                for index in range(start, min(stop, self._count))
            ],
            "embeddings": [[float(index)] for index in range(start, min(stop, self._count))],
        }

    def query(self, *, query_embeddings, n_results, include):
        assert len(query_embeddings) == 1
        assert n_results == 1
        assert include == ["distances"]
        return {"ids": [[f"{self.name}:0"]], "distances": [[0.0]]}


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
            __version__="1.5.5",
            PersistentClient=lambda *, path, settings: opened.append(
                (path, settings.migrations)
            ) or client
        ),
    )
    monkeypatch.setitem(
        sys.modules,
        "chromadb.config",
        SimpleNamespace(Settings=lambda **kwargs: SimpleNamespace(**kwargs)),
    )

    result = probe_module._default_client_factory(tmp_path / "ssd")

    assert result is client
    assert opened == [(str(tmp_path / "ssd" / "vectors"), "validate")]


def test_default_client_rejects_unsupported_chromadb_version(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(
        sys.modules,
        "chromadb",
        SimpleNamespace(__version__="9.9.9", PersistentClient=lambda **_kwargs: None),
    )
    monkeypatch.setitem(
        sys.modules,
        "chromadb.config",
        SimpleNamespace(Settings=lambda **kwargs: SimpleNamespace(**kwargs)),
    )

    with pytest.raises(ValueError, match="UNSUPPORTED_CHROMADB_VERSION"):
        probe_module._default_client_factory(tmp_path / "ssd")


def _write_durable_segment_fixture(ssd_path: Path, names: tuple[str, ...]) -> None:
    vectors = ssd_path / "vectors"
    vectors.mkdir(parents=True)
    schema = json.dumps(
        {
            "keys": {
                "#embedding": {
                    "float_list": {
                        "vector_index": {
                            "config": {
                                "hnsw": {"batch_size": 2, "sync_threshold": 3}
                            }
                        }
                    }
                }
            }
        },
        separators=(",", ":"),
        sort_keys=True,
    )
    database = sqlite3.connect(vectors / "chroma.sqlite3")
    database.execute("CREATE TABLE collections (id TEXT, name TEXT, schema_str TEXT)")
    database.execute(
        "CREATE TABLE segments (id TEXT, type TEXT, scope TEXT, collection TEXT)"
    )
    for name in names:
        collection_id = str(uuid.uuid4())
        segment_id = str(uuid.uuid4())
        database.execute(
            "INSERT INTO collections VALUES (?, ?, ?)",
            (collection_id, name, schema),
        )
        database.execute(
            "INSERT INTO segments VALUES (?, ?, ?, ?)",
            (segment_id, HNSW_SEGMENT_TYPE, "VECTOR", collection_id),
        )
        segment = vectors / segment_id
        segment.mkdir()
        for filename in HNSW_ARTIFACTS:
            (segment / filename).write_bytes(b"durable")
    database.commit()
    database.close()


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
    _write_durable_segment_fixture(tmp_path / "ssd", tuple(collections))
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


def _probe_response(receipt, ok: bool, mismatches: list[str], error: str) -> str:
    return json.dumps(
        {
            "schema_version": "holoindex_isolated_snapshot_probe.v1",
            "ok": ok,
            "generation_id": receipt.generation_id,
            "mismatched_collections": mismatches,
            "error": error,
        }
    )


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


def test_isolated_probe_rejects_unqueryable_vector_segment(tmp_path: Path) -> None:
    receipt, collections, client = _fixture(tmp_path)

    def unavailable_vector_segment(**_kwargs):
        raise RuntimeError("Nothing found on disk")

    collections["navigation_code"].query = unavailable_vector_segment

    result = probe_collection_snapshots(
        receipt,
        ssd_path=tmp_path / "ssd",
        client_factory=lambda _path: client,
    )

    assert result.ok is False
    assert result.mismatched_collections == ("navigation_code",)
    assert result.error == "VECTOR_SEGMENT_UNAVAILABLE"


def test_isolated_probe_rejects_query_result_for_different_record(
    tmp_path: Path,
) -> None:
    receipt, collections, client = _fixture(tmp_path)
    collections["navigation_code"].query = lambda **_kwargs: {
        "ids": [["forged-id"]],
        "distances": [[0.0]],
    }

    result = probe_collection_snapshots(
        receipt,
        ssd_path=tmp_path / "ssd",
        client_factory=lambda _path: client,
    )

    assert result.ok is False
    assert result.mismatched_collections == ("navigation_code",)
    assert result.error == "VECTOR_SEGMENT_UNAVAILABLE"


def test_isolated_probe_rejects_unbounded_sample_fallback(tmp_path: Path) -> None:
    receipt, collections, client = _fixture(tmp_path)

    def reject_bounded_get(*, include, limit=None, offset=None):
        if limit is not None or offset is not None:
            raise TypeError("legacy unbounded client")
        return collections["navigation_code"].get(include=include)

    collections["navigation_code"].get = reject_bounded_get

    result = probe_collection_snapshots(
        receipt,
        ssd_path=tmp_path / "ssd",
        client_factory=lambda _path: client,
    )

    assert result.ok is False
    assert result.mismatched_collections == ("navigation_code",)


def test_chroma_finalization_clears_cache_even_when_stop_fails() -> None:
    calls: list[str] = []

    class Client:
        _system = SimpleNamespace(
            stop=lambda: (_ for _ in ()).throw(RuntimeError("stop failed"))
        )

        @staticmethod
        def clear_system_cache() -> None:
            calls.append("clear")

    with pytest.raises(RuntimeError, match="stop failed"):
        probe_module.finalize_chroma_client(Client())

    assert calls == ["clear"]


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
    assert view.models_path == (tmp_path / "ssd" / "models").resolve(strict=False)
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


def test_parent_rejects_persistently_unqueryable_vector_segment(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    receipt, _collections, _client = _fixture(tmp_path)
    response = {
        "schema_version": "holoindex_isolated_snapshot_probe.v1",
        "ok": False,
        "generation_id": receipt.generation_id,
        "mismatched_collections": ["navigation_code"],
        "error": "VECTOR_SEGMENT_UNAVAILABLE",
    }
    monkeypatch.setattr(
        "holo_index.isolated_collection_snapshot_probe.subprocess.run",
        lambda *args, **kwargs: SimpleNamespace(
            returncode=0,
            stdout=json.dumps(response),
            stderr="",
        ),
    )
    with pytest.raises(IsolatedSnapshotProbeError, match="VECTOR_SEGMENT_UNAVAILABLE"):
        verify_collection_snapshots_isolated(
            receipt,
            ssd_path=tmp_path / "ssd",
            repo_root=tmp_path / "repo",
        )


def test_parent_rejects_transient_successes_after_vector_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    receipt, _collections, _client = _fixture(tmp_path)
    responses = [
        _probe_response(receipt, False, ["navigation_code"], "VECTOR_SEGMENT_UNAVAILABLE")
    ]
    calls = []
    timeouts = []
    moments = iter((100.0, 101.0))
    monkeypatch.setattr(probe_module.time, "monotonic", lambda: next(moments))

    def run_probe(*_args, **kwargs):
        calls.append(kwargs["input"])
        timeouts.append(kwargs["timeout"])
        return SimpleNamespace(returncode=0, stdout=responses.pop(0), stderr="")

    monkeypatch.setattr(
        "holo_index.isolated_collection_snapshot_probe.subprocess.run",
        run_probe,
    )

    with pytest.raises(IsolatedSnapshotProbeError, match="VECTOR_SEGMENT_UNAVAILABLE"):
        verify_collection_snapshots_isolated(
            receipt,
            ssd_path=tmp_path / "ssd",
            repo_root=tmp_path / "repo",
            timeout_seconds=10.0,
        )

    assert len(calls) == 1
    assert timeouts == [9.0]


def test_parent_does_not_retry_collection_snapshot_mismatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    receipt, _collections, _client = _fixture(tmp_path)
    calls = []
    response = _probe_response(
        receipt, False, ["navigation_code"], "COLLECTION_SNAPSHOT_MISMATCH"
    )
    monkeypatch.setattr(
        "holo_index.isolated_collection_snapshot_probe.subprocess.run",
        lambda *args, **kwargs: calls.append(kwargs["input"])
        or SimpleNamespace(returncode=0, stdout=response, stderr=""),
    )

    failures = verify_collection_snapshots_isolated(
        receipt,
        ssd_path=tmp_path / "ssd",
        repo_root=tmp_path / "repo",
    )

    assert failures == ["navigation_code"]
    assert len(calls) == 1


def test_parent_does_not_retry_vector_failure_for_later_snapshot_result(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    receipt, _collections, _client = _fixture(tmp_path)
    responses = [
        _probe_response(receipt, False, ["navigation_code"], "VECTOR_SEGMENT_UNAVAILABLE"),
        _probe_response(receipt, False, ["navigation_code"], "COLLECTION_SNAPSHOT_MISMATCH"),
    ]
    calls = []
    monkeypatch.setattr(
        "holo_index.isolated_collection_snapshot_probe.subprocess.run",
        lambda *args, **kwargs: calls.append(kwargs["input"])
        or SimpleNamespace(returncode=0, stdout=responses.pop(0), stderr=""),
    )

    with pytest.raises(IsolatedSnapshotProbeError, match="VECTOR_SEGMENT_UNAVAILABLE"):
        verify_collection_snapshots_isolated(
            receipt,
            ssd_path=tmp_path / "ssd",
            repo_root=tmp_path / "repo",
        )

    assert len(calls) == 1


def test_parent_rejects_interrupted_vector_convergence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    receipt, _collections, _client = _fixture(tmp_path)
    responses = [
        _probe_response(receipt, False, ["navigation_code"], "VECTOR_SEGMENT_UNAVAILABLE"),
        _probe_response(receipt, True, [], ""),
        _probe_response(receipt, False, ["navigation_code"], "VECTOR_SEGMENT_UNAVAILABLE"),
    ]
    monkeypatch.setattr(
        "holo_index.isolated_collection_snapshot_probe.subprocess.run",
        lambda *args, **kwargs: SimpleNamespace(
            returncode=0, stdout=responses.pop(0), stderr=""
        ),
    )

    with pytest.raises(IsolatedSnapshotProbeError, match="VECTOR_SEGMENT_UNAVAILABLE"):
        verify_collection_snapshots_isolated(
            receipt,
            ssd_path=tmp_path / "ssd",
            repo_root=tmp_path / "repo",
        )


@pytest.mark.parametrize("timeout", (None, "bad", 0, float("nan")))
def test_parent_rejects_invalid_total_timeout_before_child_process(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    timeout,
) -> None:
    receipt, _collections, _client = _fixture(tmp_path)
    monkeypatch.setattr(
        "holo_index.isolated_collection_snapshot_probe.subprocess.run",
        lambda *_args, **_kwargs: pytest.fail("child process must not start"),
    )

    with pytest.raises(IsolatedSnapshotProbeError, match="ISOLATED_PROBE_TIMEOUT_INVALID"):
        verify_collection_snapshots_isolated(
            receipt,
            ssd_path=tmp_path / "ssd",
            repo_root=tmp_path / "repo",
            timeout_seconds=timeout,
        )


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
                "mismatched_collections": [],
                "error": "",
                "unexpected": True,
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


def test_parent_rejects_oversized_child_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    receipt, _collections, _client = _fixture(tmp_path)
    monkeypatch.setattr(
        "holo_index.isolated_collection_snapshot_probe.subprocess.run",
        lambda *args, **kwargs: SimpleNamespace(
            returncode=0,
            stdout="x" * (probe_module.MAX_PROCESS_OUTPUT_BYTES + 1),
        ),
    )

    with pytest.raises(IsolatedSnapshotProbeError, match="ISOLATED_PROBE_OUTPUT_LIMIT"):
        verify_collection_snapshots_isolated(
            receipt,
            ssd_path=tmp_path / "ssd",
            repo_root=tmp_path / "repo",
        )


def test_parent_rejects_oversized_child_error_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    receipt, _collections, _client = _fixture(tmp_path)
    monkeypatch.setattr(
        "holo_index.isolated_collection_snapshot_probe.subprocess.run",
        lambda *args, **kwargs: SimpleNamespace(
            returncode=0,
            stdout="{}",
            stderr="x" * (probe_module.MAX_PROCESS_OUTPUT_BYTES + 1),
        ),
    )

    with pytest.raises(IsolatedSnapshotProbeError, match="ISOLATED_PROBE_OUTPUT_LIMIT"):
        verify_collection_snapshots_isolated(
            receipt,
            ssd_path=tmp_path / "ssd",
            repo_root=tmp_path / "repo",
        )
