"""Real Chroma regressions for durable HNSW generation publication."""

from __future__ import annotations

import json
import os
import sqlite3
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from holo_index.freshness_receipt import (
    ALL_COLLECTIONS,
    BASELINE_QUERY_COLLECTIONS,
    COLLECTION_ATTRS,
    build_freshness_receipt,
)
from holo_index.isolated_collection_snapshot_probe import (
    finalize_chroma_client,
    probe_collection_snapshots,
    verify_collection_snapshots_isolated,
)
from holo_index.vector_segment_durability import (
    HNSW_SEGMENT_TYPE,
    durable_hnsw_configuration,
    non_durable_vector_segments,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


def _chroma():
    chromadb = pytest.importorskip("chromadb")
    if str(chromadb.__version__) != "1.5.5":
        pytest.skip("real durability proof is pinned to chromadb 1.5.5")
    return chromadb


def _client(vector_path: Path, *, validate_only: bool):
    chromadb = _chroma()
    from chromadb.config import Settings

    settings = Settings(anonymized_telemetry=False)
    if validate_only:
        settings = Settings(anonymized_telemetry=False, migrations="validate")
    return chromadb.PersistentClient(
        path=str(vector_path),
        settings=settings,
    )


def _build_generation(ssd_path: Path, *, durable: bool, with_tail: bool = False):
    client = _client(ssd_path / "vectors", validate_only=False)
    collections = {}
    configuration = durable_hnsw_configuration() if durable else None
    for name in ALL_COLLECTIONS:
        kwargs = {"configuration": configuration} if configuration else {}
        collection = client.create_collection(name, **kwargs)
        collections[name] = collection
        if name in BASELINE_QUERY_COLLECTIONS:
            collection.add(
                ids=[f"{name}:{index}" for index in range(3)],
                embeddings=[[float(index), 0.0] for index in range(3)],
                documents=[f"document:{name}:{index}" for index in range(3)],
            )
            if with_tail:
                collection.add(
                    ids=[f"{name}:tail"],
                    embeddings=[[4.0, 0.0]],
                    documents=[f"document:{name}:tail"],
                )
    holo = SimpleNamespace(
        client=client,
        **{COLLECTION_ATTRS[name]: collections[name] for name in ALL_COLLECTIONS},
        index_embedding_backend="test-embedding",
        index_embedding_model_id="test-model",
        index_embedding_space_fingerprint="sha256:" + ("1" * 64),
    )
    receipt = build_freshness_receipt(
        holo,
        ssd_path=ssd_path,
        repo_root=REPO_ROOT,
        source="manual_index",
        generated_at="2026-08-11T00:00:00+00:00",
        repo_head_sha="a" * 40,
    )
    finalize_chroma_client(client)
    return receipt


def _probe_once(receipt, ssd_path: Path):
    client = _client(ssd_path / "vectors", validate_only=True)
    try:
        return probe_collection_snapshots(
            receipt,
            ssd_path=ssd_path,
            client_factory=lambda _path: client,
        )
    finally:
        finalize_chroma_client(client)


def test_legacy_subthreshold_generation_is_not_durable(tmp_path: Path) -> None:
    ssd = tmp_path / "legacy" / "ssd"
    _build_generation(ssd, durable=False)

    assert non_durable_vector_segments(
        ssd,
        collection_names=BASELINE_QUERY_COLLECTIONS,
    ) == tuple(sorted(BASELINE_QUERY_COLLECTIONS))


def test_durable_generation_survives_four_cleared_client_opens(
    tmp_path: Path,
) -> None:
    ssd = tmp_path / "durable" / "ssd"
    receipt = _build_generation(ssd, durable=True)

    for _attempt in range(4):
        result = _probe_once(receipt, ssd)
        assert result.ok is True
        assert result.mismatched_collections == ()


def test_checkpoint_plus_tail_survives_real_subprocess_probe(tmp_path: Path) -> None:
    ssd = tmp_path / "tail" / "ssd"
    receipt = _build_generation(ssd, durable=True, with_tail=True)

    assert verify_collection_snapshots_isolated(
        receipt,
        ssd_path=ssd,
        repo_root=REPO_ROOT,
    ) == []


def test_missing_persisted_metadata_rejects_named_collection(tmp_path: Path) -> None:
    ssd = tmp_path / "missing" / "ssd"
    receipt = _build_generation(ssd, durable=True)
    database = sqlite3.connect(ssd / "vectors" / "chroma.sqlite3")
    segment_id = database.execute(
        "SELECT s.id FROM segments AS s JOIN collections AS c "
        "ON c.id = s.collection WHERE c.name = ? AND s.type = ?",
        ("navigation_code", HNSW_SEGMENT_TYPE),
    ).fetchone()[0]
    database.close()
    (ssd / "vectors" / segment_id / "index_metadata.pickle").unlink()

    result = _probe_once(receipt, ssd)

    assert result.ok is False
    assert result.error == "VECTOR_SEGMENT_UNAVAILABLE"
    assert result.mismatched_collections == ("navigation_code",)


def test_changed_persistence_policy_rejects_named_collection(tmp_path: Path) -> None:
    ssd = tmp_path / "policy" / "ssd"
    _build_generation(ssd, durable=True)
    database = sqlite3.connect(ssd / "vectors" / "chroma.sqlite3")
    schema_text = database.execute(
        "SELECT schema_str FROM collections WHERE name = ?",
        ("navigation_code",),
    ).fetchone()[0]
    schema = json.loads(schema_text)
    schema["keys"]["#embedding"]["float_list"]["vector_index"]["config"][
        "hnsw"
    ]["sync_threshold"] = 1000
    database.execute(
        "UPDATE collections SET schema_str = ? WHERE name = ?",
        (json.dumps(schema), "navigation_code"),
    )
    database.commit()
    database.close()

    assert non_durable_vector_segments(
        ssd,
        collection_names=BASELINE_QUERY_COLLECTIONS,
    ) == ("navigation_code",)


@pytest.mark.skipif(os.name != "nt", reason="Windows junction regression")
def test_vectors_junction_to_external_store_is_rejected(tmp_path: Path) -> None:
    target_ssd = tmp_path / "external" / "ssd"
    _build_generation(target_ssd, durable=True)
    attacker_ssd = tmp_path / "attacker" / "ssd"
    attacker_ssd.mkdir(parents=True)
    junction = attacker_ssd / "vectors"
    completed = subprocess.run(
        [
            "cmd.exe",
            "/d",
            "/c",
            "mklink",
            "/J",
            str(junction),
            str(target_ssd / "vectors"),
        ],
        capture_output=True,
        check=False,
        shell=False,
        text=True,
    )
    if completed.returncode != 0:
        pytest.skip("junction creation unavailable")
    try:
        assert non_durable_vector_segments(
            attacker_ssd,
            collection_names=BASELINE_QUERY_COLLECTIONS,
        ) == tuple(sorted(BASELINE_QUERY_COLLECTIONS))
    finally:
        junction.rmdir()
