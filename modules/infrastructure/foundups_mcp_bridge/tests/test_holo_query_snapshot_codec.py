"""Synthetic contracts for the immutable Holo collection snapshot codec."""

from __future__ import annotations

import builtins
import hashlib
import json
from dataclasses import replace

import numpy as np
import pytest


def _api():
    from modules.infrastructure.foundups_mcp_bridge.src.holo_query_snapshot_codec import (
        SnapshotCodecError,
        SnapshotLimits,
        encode_collection_snapshot,
        load_collection_snapshot,
    )

    return SnapshotCodecError, SnapshotLimits, encode_collection_snapshot, load_collection_snapshot


def _identity() -> dict[str, object]:
    return {
        "backend": "sentence_transformers",
        "model_id": "sentence-transformers/all-MiniLM-L6-v2",
        "artifact_digest": "sha256:" + "a" * 64,
        "encoder_contract": "sentence_transformers.encode.v1",
        "space_fingerprint": "sha256:" + "b" * 64,
    }


def _fixture(*, metric: str = "l2"):
    _error, _limits, encode, _load = _api()
    rows = [
        {
            "id": "zeta",
            "document": {"nested": [None, True, False, 7, 2.5, "text"]},
            "metadata": {"path": "z.py", "priority": 2, "ratio": 0.5},
        },
        {
            "id": "alpha",
            "document": "alpha document",
            "metadata": {"path": "a.py", "enabled": True, "tags": ["a", "b"]},
        },
        {
            "id": "middle",
            "document": None,
            "metadata": None,
        },
    ]
    vectors = [[0.0, 1.0], [1.0, 0.0], [-1.0, 0.0]]
    return encode(
        collection_name="navigation_code",
        rows=rows,
        embeddings=vectors,
        metric=metric,
        embedding_identity=_identity(),
        collection_metadata={"purpose": "synthetic", "nullable": None},
    )


def test_encoding_is_canonical_deterministic_and_sorted_by_id() -> None:
    _error, _limits, encode, load = _api()
    first = _fixture()
    rows = [
        {"id": "middle", "document": None, "metadata": None},
        {"id": "alpha", "document": "alpha document", "metadata": {
            "tags": ["a", "b"], "enabled": True, "path": "a.py"}},
        {"id": "zeta", "document": {"nested": [None, True, False, 7, 2.5, "text"]},
         "metadata": {"ratio": 0.5, "priority": 2, "path": "z.py"}},
    ]
    second = encode(
        collection_name="navigation_code",
        rows=rows,
        embeddings=[[-1.0, 0.0], [1.0, 0.0], [0.0, 1.0]],
        metric="l2",
        embedding_identity=dict(reversed(tuple(_identity().items()))),
        collection_metadata={"nullable": None, "purpose": "synthetic"},
    )
    assert first == second
    assert first.manifest.endswith(b"\n")
    assert first.rows.splitlines()[0].startswith(b'{"document":"alpha document","id":"alpha"')
    manifest = json.loads(first.manifest)
    assert manifest["rows"] == {
        "bytes": len(first.rows),
        "sha256": "sha256:" + hashlib.sha256(first.rows).hexdigest(),
    }
    assert manifest["vectors"]["bytes"] == 3 * 2 * 4
    collection = load(first.manifest, first.rows, first.vectors)
    assert collection.get(include=["documents", "metadatas"])["ids"] == [
        "alpha", "middle", "zeta"
    ]


@pytest.mark.parametrize(
    ("mutator", "code"),
    [
        (lambda rows, vectors: (rows + [dict(rows[0])], vectors + [vectors[0]]), "DUPLICATE_ID"),
        (lambda rows, vectors: ([{**rows[0], "id": ""}], [vectors[0]]), "ID_INVALID"),
        (lambda rows, vectors: ([{**rows[0], "id": 7}], [vectors[0]]), "ID_INVALID"),
        (lambda rows, vectors: ([{**rows[0], "document": ("tuple",)}], [vectors[0]]), "ROW_VALUE_INVALID"),
        (lambda rows, vectors: ([{**rows[0], "metadata": {1: "bad"}}], [vectors[0]]), "ROW_VALUE_INVALID"),
        (lambda rows, vectors: ([{**rows[0], "metadata": {"bad": float("nan")}}], [vectors[0]]), "ROW_VALUE_INVALID"),
        (lambda rows, vectors: ([rows[0]], [[1.0, float("inf")]]), "EMBEDDING_NONFINITE"),
        (lambda rows, vectors: ([rows[0], rows[1]], [[1.0, 0.0], [1.0]]), "EMBEDDING_RAGGED"),
        (lambda rows, vectors: ([], []), "ROW_COUNT_BOUND"),
        (lambda rows, vectors: ([rows[0]], [[]]), "DIMENSION_BOUND"),
    ],
)
def test_encoder_rejects_noncanonical_or_unbounded_inputs(mutator, code: str) -> None:
    Error, _Limits, encode, _load = _api()
    rows = [
        {"id": "a", "document": "a", "metadata": {"path": "a.py"}},
        {"id": "b", "document": "b", "metadata": {"path": "b.py"}},
    ]
    changed_rows, changed_vectors = mutator(rows, [[1.0, 0.0], [0.0, 1.0]])
    with pytest.raises(Error, match=code):
        encode(
            collection_name="navigation_code",
            rows=changed_rows,
            embeddings=changed_vectors,
            metric="l2",
            embedding_identity=_identity(),
        )


def test_encoder_enforces_exact_count_dimension_and_byte_limits() -> None:
    Error, Limits, encode, _load = _api()
    base = Limits()
    kwargs = dict(
        collection_name="navigation_code",
        rows=[{"id": "a", "document": "payload", "metadata": None}],
        embeddings=[[1.0, 0.0]], metric="l2", embedding_identity=_identity(),
    )
    for limits, code in (
        (replace(base, max_rows=0), "LIMIT_INVALID"),
        (replace(base, max_rows=1, max_dimension=1), "DIMENSION_BOUND"),
        (replace(base, max_row_bytes=8), "ROW_SIZE_BOUND"),
        (replace(base, max_rows_bytes=8), "ROWS_SIZE_BOUND"),
        (replace(base, max_vector_bytes=4), "VECTOR_SIZE_BOUND"),
    ):
        with pytest.raises(Error, match=code):
            encode(**kwargs, limits=limits)


def _canonical_manifest(value: dict[str, object]) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii") + b"\n"


@pytest.mark.parametrize(
    "attack",
    [
        "unknown_key", "wrong_type", "bad_digest", "bad_length", "bad_dtype",
        "bad_metric", "trailing_json", "duplicate_key", "rows_trailing",
        "vectors_trailing", "row_order", "row_count", "dimension",
    ],
)
def test_loader_rejects_hostile_manifest_or_artifact_shapes(attack: str) -> None:
    Error, _Limits, _encode, load = _api()
    encoded = _fixture()
    manifest = json.loads(encoded.manifest)
    rows, vectors = encoded.rows, encoded.vectors
    if attack == "unknown_key":
        manifest["extra"] = True
    elif attack == "wrong_type":
        manifest["row_count"] = True
    elif attack == "bad_digest":
        manifest["rows"]["sha256"] = "sha256:" + "g" * 64
    elif attack == "bad_length":
        manifest["rows"]["bytes"] += 1
    elif attack == "bad_dtype":
        manifest["vectors"]["dtype"] = "float32"
    elif attack == "bad_metric":
        manifest["metric"] = "manhattan"
    elif attack == "trailing_json":
        with pytest.raises(Error, match="MANIFEST_NONCANONICAL"):
            load(encoded.manifest + b" ", rows, vectors)
        return
    elif attack == "duplicate_key":
        hostile = encoded.manifest[:-2] + b',"schema_version":"duplicate"}\n'
        with pytest.raises(Error, match="MANIFEST_INVALID"):
            load(hostile, rows, vectors)
        return
    elif attack == "rows_trailing":
        rows += b"\n"
        manifest["rows"]["bytes"] = len(rows)
        manifest["rows"]["sha256"] = "sha256:" + hashlib.sha256(rows).hexdigest()
    elif attack == "vectors_trailing":
        vectors += b"\x00\x00\x00\x00"
        manifest["vectors"]["bytes"] = len(vectors)
        manifest["vectors"]["sha256"] = "sha256:" + hashlib.sha256(vectors).hexdigest()
    elif attack == "row_order":
        lines = rows.splitlines(keepends=True)
        rows = b"".join(reversed(lines))
        manifest["rows"]["sha256"] = "sha256:" + hashlib.sha256(rows).hexdigest()
    elif attack == "row_count":
        manifest["row_count"] += 1
    elif attack == "dimension":
        manifest["dimension"] += 1
    candidate = _canonical_manifest(manifest)
    with pytest.raises(Error):
        load(candidate, rows, vectors)


def test_loader_copies_mutable_source_buffers_and_performs_no_filesystem_io(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _Error, _Limits, _encode, load = _api()
    encoded = _fixture()
    manifest = bytearray(encoded.manifest)
    rows = bytearray(encoded.rows)
    vectors = bytearray(encoded.vectors)
    calls: list[object] = []

    def forbidden(*args, **kwargs):
        calls.append((args, kwargs))
        raise AssertionError("filesystem access forbidden")

    monkeypatch.setattr(builtins, "open", forbidden)
    collection = load(manifest, rows, vectors)
    manifest[:] = b"X" * len(manifest)
    rows[:] = b"X" * len(rows)
    vectors[:] = b"X" * len(vectors)
    assert collection.get(ids="alpha", include=["documents"])["documents"] == [
        "alpha document"
    ]
    assert calls == []


def test_warm_queries_do_no_hashing_or_filesystem_io(monkeypatch: pytest.MonkeyPatch) -> None:
    _Error, _Limits, _encode, load = _api()
    encoded = _fixture(metric="cosine")
    collection = load(encoded.manifest, encoded.rows, encoded.vectors)
    calls = {"hash": 0, "open": 0}

    def forbidden_hash(*_args, **_kwargs):
        calls["hash"] += 1
        raise AssertionError("warm hashing forbidden")

    def forbidden_open(*_args, **_kwargs):
        calls["open"] += 1
        raise AssertionError("warm filesystem access forbidden")

    monkeypatch.setattr(hashlib, "sha256", forbidden_hash)
    monkeypatch.setattr(builtins, "open", forbidden_open)
    for _ in range(100):
        result = collection.query(query_embeddings=[[1.0, 0.0]], n_results=2)
        assert result["ids"] == [["alpha", "zeta"]]
    assert calls == {"hash": 0, "open": 0}


@pytest.mark.parametrize("scalar", [True, False, "1.25", "0", None])
def test_encoder_rejects_coercible_non_numeric_embedding_scalars(scalar: object) -> None:
    Error, _Limits, encode, _load = _api()
    with pytest.raises(Error, match="EMBEDDING_SCALAR_INVALID"):
        encode(
            collection_name="navigation_code",
            rows=[{"id": "a", "document": "a", "metadata": None}],
            embeddings=[[scalar, 0.0]], metric="l2",
            embedding_identity=_identity(),
        )


def test_encoder_rejects_finite_float_that_overflows_float32() -> None:
    Error, _Limits, encode, _load = _api()
    with pytest.raises(Error, match="EMBEDDING_NONFINITE"):
        encode(
            collection_name="navigation_code",
            rows=[{"id": "a", "document": "a", "metadata": None}],
            embeddings=[[1e100]], metric="l2", embedding_identity=_identity(),
        )


@pytest.mark.parametrize(
    ("field", "value", "code"),
    [
        ("id", "e\u0301", "ID_NON_NFC"),
        ("id", "bad\ud800", "ID_INVALID"),
        ("document", "bad\ud800", "ROW_VALUE_INVALID"),
        ("metadata", {"bad\ud800": "value"}, "ROW_VALUE_INVALID"),
        ("metadata", {"key": "bad\udfff"}, "ROW_VALUE_INVALID"),
    ],
)
def test_encoder_rejects_noncanonical_ids_and_non_scalar_unicode(
    field: str, value: object, code: str,
) -> None:
    Error, _Limits, encode, _load = _api()
    row = {"id": "a", "document": "a", "metadata": None}
    row[field] = value
    with pytest.raises(Error, match=code):
        encode(
            collection_name="navigation_code", rows=[row], embeddings=[[1.0]],
            metric="l2", embedding_identity=_identity(),
        )


def test_nfc_equivalent_id_aliases_fail_without_collapsing_rows() -> None:
    Error, _Limits, encode, _load = _api()
    rows = [
        {"id": "\u00e9", "document": "composed", "metadata": None},
        {"id": "e\u0301", "document": "decomposed", "metadata": None},
    ]
    with pytest.raises(Error, match="ID_NON_NFC"):
        encode(
            collection_name="navigation_code", rows=rows,
            embeddings=[[1.0], [2.0]], metric="l2",
            embedding_identity=_identity(),
        )


@pytest.mark.parametrize(
    "kwargs",
    [
        {"embedding_identity": None},
        {"embedding_identity": []},
        {"embedding_identity": {**_identity(), "backend": 7}},
        {"embedding_identity": {**_identity(), "backend": "bad\ud800"}},
        {"collection_metadata": {"bad\ud800": "value"}},
        {"collection_metadata": {"key": "bad\ud800"}},
    ],
)
def test_identity_and_collection_metadata_hostile_types_fail_stably(kwargs) -> None:
    Error, _Limits, encode, _load = _api()
    inputs = dict(
        collection_name="navigation_code",
        rows=[{"id": "a", "document": "a", "metadata": None}],
        embeddings=[[1.0]], metric="l2", embedding_identity=_identity(),
    )
    inputs.update(kwargs)
    with pytest.raises(Error):
        encode(**inputs)


@pytest.mark.parametrize(
    "selector",
    [
        lambda data: memoryview(data)[::2],
        lambda data: memoryview(data).cast("B", shape=[2, len(data) // 2]),
    ],
)
def test_loader_rejects_noncontiguous_or_multidimensional_buffers(selector) -> None:
    Error, _Limits, _encode, load = _api()
    encoded = _fixture()
    data = bytearray(encoded.vectors)
    if len(data) % 2:
        data.append(0)
    with pytest.raises(Error, match="BUFFER_INVALID"):
        load(encoded.manifest, encoded.rows, selector(data))


@pytest.mark.parametrize("buffer", ["bytes", 7, object(), [1, 2]])
def test_loader_rejects_non_buffer_types_before_conversion(buffer: object) -> None:
    Error, _Limits, _encode, load = _api()
    encoded = _fixture()
    with pytest.raises(Error, match="BUFFER_INVALID"):
        load(buffer, encoded.rows, encoded.vectors)


def test_loader_checks_declared_vector_length_before_numpy_conversion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    Error, _Limits, _encode, load = _api()
    encoded = _fixture()
    calls = 0

    def forbidden(*_args, **_kwargs):
        nonlocal calls
        calls += 1
        raise AssertionError("NumPy conversion reached")

    monkeypatch.setattr(np, "frombuffer", forbidden)
    with pytest.raises(Error, match="ARTIFACT_LENGTH_MISMATCH"):
        load(encoded.manifest, encoded.rows, encoded.vectors[:-4])
    assert calls == 0


def test_encoder_checks_vector_byte_ceiling_before_numpy_conversion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    Error, Limits, encode, _load = _api()
    calls = 0

    def forbidden(*_args, **_kwargs):
        nonlocal calls
        calls += 1
        raise AssertionError("NumPy conversion reached")

    monkeypatch.setattr(np, "asarray", forbidden)
    with pytest.raises(Error, match="VECTOR_SIZE_BOUND"):
        encode(
            collection_name="navigation_code",
            rows=[{"id": "a", "document": None, "metadata": None}],
            embeddings=[[1.0, 0.0]], metric="l2",
            embedding_identity=_identity(),
            limits=replace(Limits(), max_vector_bytes=4),
        )
    assert calls == 0


@pytest.mark.parametrize(
    "override",
    [
        {"rows": None},
        {"rows": 7},
        {"rows": "rows"},
        {"embeddings": None},
        {"embeddings": 7},
        {"embeddings": "vectors"},
    ],
)
def test_encoder_normalizes_hostile_public_container_types(override) -> None:
    Error, _Limits, encode, _load = _api()
    inputs = dict(
        collection_name="navigation_code",
        rows=[{"id": "a", "document": None, "metadata": None}],
        embeddings=[[1.0]], metric="l2", embedding_identity=_identity(),
    )
    inputs.update(override)
    with pytest.raises(Error):
        encode(**inputs)


@pytest.mark.parametrize(
    "override",
    [
        {"collection_name": "navigation_e\u0301"},
        {"embedding_identity": {**_identity(), "backend": "e\u0301"}},
        {"rows": [{"id": "a", "document": "e\u0301", "metadata": None}]},
        {"rows": [{"id": "a", "document": ["ok", ["e\u0301"]], "metadata": None}]},
        {"rows": [{"id": "a", "document": None, "metadata": {"e\u0301": "v"}}]},
        {"rows": [{"id": "a", "document": None, "metadata": {"k": "e\u0301"}}]},
    ],
)
def test_encoder_rejects_nfd_in_every_admitted_text_surface(override) -> None:
    Error, _Limits, encode, _load = _api()
    inputs = dict(
        collection_name="navigation_code",
        rows=[{"id": "a", "document": None, "metadata": None}],
        embeddings=[[1.0]], metric="l2", embedding_identity=_identity(),
    )
    inputs.update(override)
    with pytest.raises(Error):
        encode(**inputs)


@pytest.mark.parametrize("slot", ["manifest", "rows", "vectors"])
def test_loader_normalizes_released_memoryviews(slot: str) -> None:
    Error, _Limits, _encode, load = _api()
    encoded = _fixture()
    values = {
        "manifest": encoded.manifest,
        "rows": encoded.rows,
        "vectors": encoded.vectors,
    }
    released = memoryview(bytearray(values[slot]))
    released.release()
    values[slot] = released
    with pytest.raises(Error, match="BUFFER_INVALID"):
        load(values["manifest"], values["rows"], values["vectors"])
