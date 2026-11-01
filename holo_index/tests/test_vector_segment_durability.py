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
    collection_uses_durable_hnsw_policy,
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


def test_live_collection_policy_requires_complete_schema(tmp_path: Path) -> None:
    durable_ssd = tmp_path / "live-durable" / "ssd"
    legacy_ssd = tmp_path / "live-legacy" / "ssd"
    _build_generation(durable_ssd, durable=True)
    _build_generation(legacy_ssd, durable=False)
    durable_client = _client(durable_ssd / "vectors", validate_only=True)
    try:
        assert collection_uses_durable_hnsw_policy(
            durable_client.get_collection("navigation_code")
        )
    finally:
        finalize_chroma_client(durable_client)
    legacy_client = _client(legacy_ssd / "vectors", validate_only=True)
    try:
        assert not collection_uses_durable_hnsw_policy(
            legacy_client.get_collection("navigation_code")
        )
    finally:
        finalize_chroma_client(legacy_client)


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


from holo_index import vector_segment_durability as policy
ERROR = "^HOLOINDEX_UNSAFE_COLLECTION_SETTINGS$"

class _Raw:
    def __init__(self, configuration, schema=None):
        self._model = SimpleNamespace(configuration_json=configuration, serialized_schema=schema)
        self.metadata, self.reads = {}, []

    def forbidden(self):
        self.reads.append("executable getter")
        raise AssertionError("executable getter accessed")

    configuration = property(forbidden)
    schema = property(forbidden)

class _Dict(dict):
    calls = 0

    def forbidden(self, *args, **kwargs):
        _Dict.calls += 1
        raise AssertionError("custom JSON hook accessed")

    items = get = __iter__ = __len__ = forbidden

    def __repr__(self):
        return "<unsupported mapping>"

def _config(metric="l2"):
    return {"hnsw": {"space": metric}}

def _with_ef(location, spec):
    config, schema = _config(), {}
    if location == "config":
        config["embedding_function"] = spec
    else:
        sparse = "sparse" in location
        index = {"enabled": False, "config": {"embedding_function": spec}}
        shape = {"sparse_vector": {"sparse_vector_index": index}} if sparse else {"float_list": {"vector_index": index}}
        schema = {"defaults": shape} if location.startswith("default") else {"keys": {"notes": shape}}
    return _Raw(config, schema)

def _call(collection):
    model = collection._model
    before = repr([model.configuration_json, model.serialized_schema])
    try:
        return getattr(policy, "validate_collection_raw_settings")(collection)
    finally:
        assert repr([model.configuration_json, model.serialized_schema]) == before
        assert collection.reads == []

def _deny(collection):
    with pytest.raises(ValueError, match=ERROR) as raised:
        _call(collection)
    assert type(raised.value) is getattr(policy, "UnsafeCollectionSettingsError")

@pytest.mark.parametrize("metric", ["l2", "cosine", "ip"])
@pytest.mark.parametrize("profile", ["absent", "config-none", "config-legacy", "dense-legacy", "dense-default", "sparse-legacy"])
def test_raw_accepted_profiles_never_use_executable_getters(metric, profile):
    collection = _Raw(_config(metric))
    if profile.startswith("config-"):
        collection._model.configuration_json["embedding_function"] = None if profile == "config-none" else {"type": "legacy"}
    elif profile != "absent":
        spec = {"type": "known", "name": "default", "config": {}} if profile == "dense-default" else {"type": "legacy"}
        collection = _with_ef("default-sparse" if profile == "sparse-legacy" else "key-dense", spec)
        collection._model.configuration_json["hnsw"]["space"] = metric
    assert _call(collection) == metric

@pytest.mark.parametrize("location", ["config", "default-dense", "key-dense", "default-sparse", "key-sparse"])
@pytest.mark.parametrize("spec", [{"type": "unknown"}, {"type": "legacy", "extra": 1},
    {"type": "unknown", "extra": 0},
    {"type": "known", "name": "default", "config": {"trust_remote_code": False}},
    {"type": "known", "name": "default", "config": {}, "extra": False}])
def test_all_dense_sparse_defaults_and_disabled_named_ef_paths_enforce_policy(location, spec):
    if location in ("default-sparse", "key-sparse") and spec == {"type": "unknown"}:
        assert _call(_with_ef(location, spec)) == "l2"
    else:
        _deny(_with_ef(location, spec))

@pytest.mark.parametrize("location", ["default-dense", "key-dense", "default-sparse", "key-sparse"])
def test_present_schema_ef_none_is_not_whole_schema_absence(location):
    _deny(_with_ef(location, None))

@pytest.mark.parametrize("location", ["default-sparse", "key-sparse"])
def test_sparse_does_not_inherit_known_dense_default_allowance(location):
    _deny(_with_ef(location, {"type": "known", "name": "default", "config": {}}))

@pytest.mark.parametrize("kind", ["configuration-none", "hnsw-list", "metric-unknown", "schema-list", "defaults-list", "keys-list", "key-none", "dense-config-none"])
def test_malformed_recognized_shapes_have_fixed_refusal(kind):
    collection = _Raw(_config(), {})
    if kind == "configuration-none": collection._model.configuration_json = None
    elif kind == "hnsw-list": collection._model.configuration_json["hnsw"] = []
    elif kind == "metric-unknown": collection._model.configuration_json["hnsw"]["space"] = "private-sentinel"
    else:
        collection._model.serialized_schema = {"schema-list": [], "defaults-list": {"defaults": []},
            "keys-list": {"keys": []}, "key-none": {"keys": {"notes": None}},
            "dense-config-none": {"defaults": {"float_list": {"vector_index": {"config": None}}}}}[kind]
    _deny(collection)

@pytest.mark.parametrize("kind", ["mapping", "nan", "infinity", "unsupported"])
def test_non_json_data_rejects_without_custom_container_hooks(kind):
    collection = _Raw(_config())
    collection._model.configuration_json["padding"] = {"mapping": _Dict(), "nan": float("nan"),
        "infinity": float("inf"), "unsupported": object()}[kind]
    _Dict.calls = 0
    _deny(collection)
    assert _Dict.calls == 0

@pytest.mark.parametrize("bound", ["nodes", "depth", "bytes", "bits"])
@pytest.mark.parametrize("excess", [0, 1])
def test_literal_resource_limits_are_inclusive_without_semantic_shape_confounds(bound, excess):
    config = _config()
    if bound == "nodes": value = [None] * (4088 + excess)
    elif bound == "bytes": value = "A" * (255960 + excess)
    elif bound == "bits": value = 1 << (2047 + excess)
    else:
        value = None
        for _ in range(15 + excess): value = [value]
    config["padding"] = value
    collection = _Raw(config)
    if excess: _deny(collection)
    else: assert _call(collection) == "l2"

@pytest.mark.parametrize("excess", [0, 1])
def test_raw_string_prepass_precedes_bounded_serialization(excess, monkeypatch):
    config = _config(); config["padding"] = "A" * (255982 + excess)
    calls, original = [], json.dumps
    def observed(*args, **kwargs):
        calls.append(True)
        return original(*args, **kwargs)
    monkeypatch.setattr(policy.json, "dumps", observed)
    _deny(_Raw(config))
    assert bool(calls) is (excess == 0)

@pytest.mark.parametrize("kind", ["cycle", "shared-over-limit", "shared-within-limit"])
def test_cycles_reject_and_shared_aliases_count_per_occurrence(kind):
    value = []
    if kind == "cycle": value.append(value)
    else: value = [value] * (4088 if kind == "shared-within-limit" else 4089)
    config = _config(); config["padding"] = value
    if kind == "shared-within-limit": assert _call(_Raw(config)) == "l2"
    else: _deny(_Raw(config))
