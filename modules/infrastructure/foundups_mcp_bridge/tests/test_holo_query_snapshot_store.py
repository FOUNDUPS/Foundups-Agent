"""Generation-bound immutable query snapshot store contracts."""

from __future__ import annotations

import hashlib
from pathlib import Path
from types import SimpleNamespace

import pytest

from holo_index.embedding_space import (
    CANONICAL_INDEX_BACKEND,
    SENTENCE_TRANSFORMER_MODEL_ID,
    embedding_artifact_digest,
    embedding_space_fingerprint,
    SENTENCE_TRANSFORMER_CONTRACT,
)
from holo_index.freshness_receipt import (
    BASELINE_QUERY_COLLECTIONS,
    COLLECTION_ATTRS,
    CollectionFreshness,
    HoloIndexFreshnessReceipt,
)
from holo_index.vector_segment_durability import durable_hnsw_configuration
from modules.infrastructure.foundups_mcp_bridge.src.holo_query_snapshot_store import (
    QuerySnapshotStoreError,
    open_query_snapshot_client,
    publish_query_snapshot_set,
)


class _Collection:
    configuration = {"hnsw": {"space": "l2"}}

    def __init__(self, metadata: dict[str, str]) -> None:
        self.metadata = metadata
        self._values = {
            "ids": ["row_1", "row_2"],
            "documents": ["first", "second"],
            "metadatas": [{"path": "first.py"}, {"path": "second.py"}],
            "embeddings": [
                [1.0] + [0.0] * 383,
                [0.0, 1.0] + [0.0] * 382,
            ],
        }

    def get(self, *, include, limit, offset):
        end = offset + limit
        return {
            "ids": self._values["ids"][offset:end],
            **{key: self._values[key][offset:end] for key in include},
        }


def _model(models: Path) -> tuple[str, str]:
    snapshot = models / "sentence_transformers" / "all-MiniLM-L6-v2"
    snapshot.mkdir(parents=True)
    for name in ("modules.json", "config.json", "model.safetensors", "tokenizer.json"):
        (snapshot / name).write_bytes(name.encode("ascii"))
    artifact = embedding_artifact_digest(snapshot)
    fingerprint = embedding_space_fingerprint(
        backend=CANONICAL_INDEX_BACKEND,
        model_id=SENTENCE_TRANSFORMER_MODEL_ID,
        artifact_digest=artifact,
        encoder_contract=SENTENCE_TRANSFORMER_CONTRACT,
    )
    return artifact, fingerprint


def _fixture(tmp_path: Path):
    ssd = tmp_path / "ssd"
    (ssd / "vectors").mkdir(parents=True)
    models = ssd / "models"
    _artifact, fingerprint = _model(models)
    metadata = {
        "embedding_backend": CANONICAL_INDEX_BACKEND,
        "embedding_model": SENTENCE_TRANSFORMER_MODEL_ID,
        "embedding_space_fingerprint": fingerprint,
    }
    holo = SimpleNamespace(models_path=models)
    entries = []
    for name in sorted(BASELINE_QUERY_COLLECTIONS):
        setattr(holo, COLLECTION_ATTRS[name], _Collection(metadata))
        entries.append(CollectionFreshness(
            name=name, count=2, status="current", source="test",
            repo_head_sha="a" * 40, last_indexed_at="2026-08-22T00:00:00Z",
            embedding_backend=CANONICAL_INDEX_BACKEND,
            embedding_model=SENTENCE_TRANSFORMER_MODEL_ID,
            embedding_space_fingerprint=fingerprint, verification="PASS",
        ))
    receipt = HoloIndexFreshnessReceipt(
        schema_version="holoindex_freshness_receipt.v2",
        generated_at="2026-08-22T00:00:00Z", repo_root=str(tmp_path),
        repo_head_sha="a" * 40, ssd_path=str(ssd), source="test",
        generation_id="sha256:" + "b" * 64, collections=entries,
    )
    return ssd, holo, receipt


def _tree_hashes(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in root.rglob("*") if path.is_file()
    }


def test_snapshot_round_trip_queries_without_mutating_generation(tmp_path: Path) -> None:
    ssd, holo, receipt = _fixture(tmp_path)
    root = publish_query_snapshot_set(holo, receipt, ssd_path=ssd)
    before = _tree_hashes(root)

    client = open_query_snapshot_client(ssd / "vectors")
    result = client.get_collection("navigation_code").query(
        query_embeddings=[[1.0] + [0.0] * 383], n_results=1
    )
    assert result["ids"] == [["row_1"]]
    assert client.generation_id == receipt.generation_id
    assert client.get_collection("navigation_work_ledger").count() == 0
    assert _tree_hashes(root) == before
    client.close()


def test_snapshot_artifact_change_fails_closed(tmp_path: Path) -> None:
    ssd, holo, receipt = _fixture(tmp_path)
    root = publish_query_snapshot_set(holo, receipt, ssd_path=ssd)
    target = root / "navigation_code.rows.jsonl"
    target.write_bytes(target.read_bytes() + b" ")

    with pytest.raises(QuerySnapshotStoreError, match="ARTIFACT_BINDING_MISMATCH"):
        open_query_snapshot_client(ssd / "vectors")


def test_snapshot_export_normalizes_persisted_unicode_to_nfc(tmp_path: Path) -> None:
    ssd, holo, receipt = _fixture(tmp_path)
    knowledge = getattr(holo, COLLECTION_ATTRS["navigation_knowledge"])
    knowledge._values["documents"][0] = "Cafe\u0301"
    knowledge._values["metadatas"][0]["section"] = "Re\u0301sume\u0301"

    publish_query_snapshot_set(holo, receipt, ssd_path=ssd)
    collection = open_query_snapshot_client(ssd / "vectors").get_collection(
        "navigation_knowledge"
    )
    row = collection.get(ids=["row_1"])

    assert row["documents"] == ["Caf\u00e9"]
    assert row["metadatas"] == [
        {"path": "first.py", "section": "R\u00e9sum\u00e9"}
    ]


def test_snapshot_export_rejects_nfc_key_collision(tmp_path: Path) -> None:
    ssd, holo, receipt = _fixture(tmp_path)
    knowledge = getattr(holo, COLLECTION_ATTRS["navigation_knowledge"])
    knowledge._values["metadatas"][0] = {"\u00e9": 1, "e\u0301": 2}

    with pytest.raises(QuerySnapshotStoreError, match="NORMALIZATION_COLLISION"):
        publish_query_snapshot_set(holo, receipt, ssd_path=ssd)


def test_real_chroma_export_is_queryable_without_chroma_reopen(tmp_path: Path) -> None:
    import chromadb

    ssd, fixture_holo, receipt = _fixture(tmp_path)
    writer = chromadb.PersistentClient(path=str(ssd / "vectors"))
    proof_holo = SimpleNamespace(models_path=fixture_holo.models_path)
    try:
        for name in sorted(BASELINE_QUERY_COLLECTIONS):
            source = getattr(fixture_holo, COLLECTION_ATTRS[name])
            collection = writer.create_collection(
                name,
                metadata=source.metadata,
                configuration=durable_hnsw_configuration(),
            )
            collection.add(
                ids=source._values["ids"],
                documents=source._values["documents"],
                metadatas=source._values["metadatas"],
                embeddings=source._values["embeddings"],
            )
            setattr(proof_holo, COLLECTION_ATTRS[name], collection)
        publish_query_snapshot_set(proof_holo, receipt, ssd_path=ssd)
    finally:
        writer.close()

    client = open_query_snapshot_client(ssd / "vectors")
    assert client.get_collection("navigation_symbols").count() == 2
    client.close()


def test_snapshot_set_total_size_fails_before_publication(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    import modules.infrastructure.foundups_mcp_bridge.src.holo_query_snapshot_store as store

    ssd, holo, receipt = _fixture(tmp_path)
    monkeypatch.setattr(store, "MAX_SNAPSHOT_SET_BYTES", 1)
    with pytest.raises(QuerySnapshotStoreError, match="TOTAL_SIZE_BOUND"):
        publish_query_snapshot_set(holo, receipt, ssd_path=ssd)
    assert not (ssd / "vectors" / "query_snapshots").exists()
