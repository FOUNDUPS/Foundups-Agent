"""Chroma-shaped read-adapter compatibility for immutable snapshots."""

from __future__ import annotations

import json
from dataclasses import replace

import numpy as np
import pytest

from modules.infrastructure.foundups_mcp_bridge.tests.test_holo_query_snapshot_codec import (
    _fixture,
)


def _collection(metric: str = "l2"):
    from modules.infrastructure.foundups_mcp_bridge.src.holo_query_snapshot_codec import (
        load_collection_snapshot,
    )

    encoded = _fixture(metric=metric)
    return load_collection_snapshot(encoded.manifest, encoded.rows, encoded.vectors)


def test_adapter_surface_and_exact_get_shapes() -> None:
    collection = _collection()
    assert collection.name == "navigation_code"
    assert collection.metadata == {"nullable": None, "purpose": "synthetic"}
    assert collection.count() == 3
    assert collection.get(ids=["zeta", "alpha"], include=[]) == {
        "ids": ["zeta", "alpha"]
    }
    page = collection.get(include=["documents", "metadatas", "embeddings"], limit=1, offset=1)
    assert page["ids"] == ["middle"]
    assert page["documents"] == [None]
    assert page["metadatas"] == [None]
    assert page["embeddings"] == [[-1.0, 0.0]]
    exact = collection.get(where={"path": "a.py"}, include=["documents", "metadatas"])
    assert exact["ids"] == ["alpha"]
    assert exact["documents"] == ["alpha document"]
    assert exact["metadatas"][0]["enabled"] is True
    assert not any(hasattr(collection, name) for name in ("add", "upsert", "update", "delete"))


@pytest.mark.parametrize(
    ("metric", "query", "expected_ids", "expected_distances"),
    [
        ("l2", [1.0, 0.0], ["alpha", "zeta", "middle"], [0.0, 2.0, 4.0]),
        ("cosine", [1.0, 0.0], ["alpha", "zeta", "middle"], [0.0, 1.0, 2.0]),
        ("ip", [1.0, 0.0], ["alpha", "zeta", "middle"], [0.0, 1.0, 2.0]),
    ],
)
def test_query_metric_parity_and_nested_chroma_shapes(
    metric: str, query: list[float], expected_ids: list[str], expected_distances: list[float]
) -> None:
    result = _collection(metric).query(
        query_embeddings=[query], n_results=10,
        include=["documents", "metadatas", "distances", "embeddings"],
    )
    assert result["ids"] == [expected_ids]
    assert result["distances"][0] == pytest.approx(expected_distances, abs=1e-6)
    assert len(result["documents"]) == len(result["metadatas"]) == 1
    assert result["embeddings"][0][0] == [1.0, 0.0]


def test_query_is_deterministic_for_ties_and_multiple_queries() -> None:
    collection = _collection("l2")
    result = collection.query(
        query_embeddings=[[0.0, 0.0], [-1.0, 0.0]], n_results=2,
        include=["distances"],
    )
    assert result["ids"] == [["alpha", "middle"], ["middle", "zeta"]]
    assert result["distances"][0] == pytest.approx([1.0, 1.0])
    assert result["distances"][1] == pytest.approx([0.0, 2.0])


def test_get_omits_unknown_ids_without_mutating_internal_rows() -> None:
    collection = _collection()
    assert collection.get(ids=["missing"], include=[]) == {"ids": []}
    first = collection.get(ids="alpha", include=["metadatas", "documents"])
    first["metadatas"][0]["path"] = "mutated.py"
    first["documents"][0] = "mutated"
    second = collection.get(ids="alpha", include=["metadatas", "documents"])
    assert second["metadatas"][0]["path"] == "a.py"
    assert second["documents"][0] == "alpha document"


@pytest.mark.parametrize(
    "call",
    [
        lambda c: c.get(include=["uris"]),
        lambda c: c.get(ids=[7]),
        lambda c: c.get(limit=True),
        lambda c: c.get(offset=-1),
        lambda c: c.get(where={"other": "value"}),
        lambda c: c.query(query_embeddings=[], n_results=1),
        lambda c: c.query(query_embeddings=[[1.0]], n_results=1),
        lambda c: c.query(query_embeddings=[[float("nan"), 0.0]], n_results=1),
        lambda c: c.query(query_embeddings=[[1.0, 0.0]], n_results=0),
        lambda c: c.query(query_embeddings=[[1.0, 0.0]], n_results=1, include=["uris"]),
    ],
)
def test_adapter_rejects_unsupported_or_malformed_reads(call) -> None:
    from modules.infrastructure.foundups_mcp_bridge.src.holo_query_snapshot_codec import (
        SnapshotCodecError,
    )

    with pytest.raises(SnapshotCodecError):
        call(_collection())


def test_vector_math_is_chunk_bounded(monkeypatch: pytest.MonkeyPatch) -> None:
    collection = _collection("l2")
    collection._query_chunk_rows = 1
    observed: list[tuple[int, ...]] = []
    original = np.sum

    def recorded(value, *args, **kwargs):
        observed.append(value.shape)
        return original(value, *args, **kwargs)

    monkeypatch.setattr(np, "sum", recorded)
    result = collection.query(query_embeddings=[[1.0, 0.0]], n_results=2)
    assert result["ids"] == [["alpha", "zeta"]]
    assert observed and max(shape[0] for shape in observed) == 1


@pytest.mark.parametrize("scalar", [True, False, "1.0", "0", None])
def test_query_rejects_coercible_non_numeric_scalars(scalar: object) -> None:
    from modules.infrastructure.foundups_mcp_bridge.src.holo_query_snapshot_codec import (
        SnapshotCodecError,
    )

    with pytest.raises(SnapshotCodecError, match="QUERY_SCALAR_INVALID"):
        _collection().query(query_embeddings=[[scalar, 0.0]], n_results=1)


def test_cosine_tiny_identical_and_zero_vectors_are_unbiased_and_deterministic() -> None:
    from modules.infrastructure.foundups_mcp_bridge.src.holo_query_snapshot_codec import (
        encode_collection_snapshot,
        load_collection_snapshot,
    )
    from modules.infrastructure.foundups_mcp_bridge.tests.test_holo_query_snapshot_codec import (
        _identity,
    )

    encoded = encode_collection_snapshot(
        collection_name="navigation_code",
        rows=[
            {"id": "tiny", "document": "tiny", "metadata": None},
            {"id": "zero", "document": "zero", "metadata": None},
        ],
        embeddings=[[1e-30, 0.0], [0.0, 0.0]], metric="cosine",
        embedding_identity=_identity(),
    )
    collection = load_collection_snapshot(encoded.manifest, encoded.rows, encoded.vectors)
    tiny = collection.query(
        query_embeddings=[[1e-30, 0.0]], n_results=2, include=["distances"]
    )
    zero = collection.query(
        query_embeddings=[[0.0, 0.0]], n_results=2, include=["distances"]
    )
    assert tiny["ids"] == [["tiny", "zero"]]
    assert tiny["distances"][0] == pytest.approx([0.0, 1.0], abs=1e-12)
    assert zero["ids"] == [["tiny", "zero"]]
    assert zero["distances"][0] == pytest.approx([1.0, 1.0], abs=1e-12)


@pytest.mark.parametrize("metric", ["l2", "cosine", "ip"])
def test_extreme_admitted_float32_distance_math_remains_finite(metric: str) -> None:
    from modules.infrastructure.foundups_mcp_bridge.src.holo_query_snapshot_codec import (
        encode_collection_snapshot,
        load_collection_snapshot,
    )
    from modules.infrastructure.foundups_mcp_bridge.tests.test_holo_query_snapshot_codec import (
        _identity,
    )

    maximum = float(np.finfo(np.float32).max)
    encoded = encode_collection_snapshot(
        collection_name="navigation_code",
        rows=[
            {"id": "negative", "document": None, "metadata": None},
            {"id": "positive", "document": None, "metadata": None},
        ],
        embeddings=[[-maximum, maximum], [maximum, -maximum]], metric=metric,
        embedding_identity=_identity(),
    )
    collection = load_collection_snapshot(encoded.manifest, encoded.rows, encoded.vectors)
    result = collection.query(
        query_embeddings=[[maximum, -maximum]], n_results=2,
        include=["distances"],
    )
    assert np.isfinite(result["distances"]).all()


def test_workspace_ceiling_dynamically_reduces_chunk_rows() -> None:
    collection = _collection("l2")
    collection._query_chunk_rows = 10_000
    collection._limits = replace(collection._limits, max_query_workspace_bytes=248)
    observed: list[int] = []
    original = collection._distance_chunk

    def recorded(query, start, end):
        observed.append(end - start)
        return original(query, start, end)

    collection._distance_chunk = recorded
    collection.query(query_embeddings=[[1.0, 0.0]], n_results=2)
    assert observed == [1, 1, 1]


def test_query_validates_shape_and_workspace_before_numpy_conversion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from modules.infrastructure.foundups_mcp_bridge.src.holo_query_snapshot_codec import (
        SnapshotCodecError,
    )

    collection = _collection()
    calls = 0
    original = np.asarray

    def recorded(*args, **kwargs):
        nonlocal calls
        calls += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(np, "asarray", recorded)
    with pytest.raises(SnapshotCodecError, match="QUERY_DIMENSION_INVALID"):
        collection.query(query_embeddings=[[1.0]], n_results=1)
    assert calls == 0


def test_get_and_query_bounds_precede_result_allocation() -> None:
    from modules.infrastructure.foundups_mcp_bridge.src.holo_query_snapshot_codec import (
        SnapshotCodecError,
    )

    collection = _collection()
    with pytest.raises(SnapshotCodecError, match="GET_IDS_BOUND"):
        collection.get(ids=["a"] * (collection._limits.max_rows + 1))
    with pytest.raises(SnapshotCodecError, match="GET_ID_INVALID"):
        collection.get(ids=["x" * (collection._limits.max_id_bytes + 1)])
    with pytest.raises(SnapshotCodecError, match="QUERY_LIMIT_BOUND"):
        collection.query(
            query_embeddings=[[1.0, 0.0]],
            n_results=collection._limits.max_rows + 1,
        )


def test_public_metadata_and_embedding_identity_are_mutation_isolated() -> None:
    collection = _collection()
    metadata = collection.metadata
    identity = collection.embedding_identity
    metadata["purpose"] = "changed"
    identity["backend"] = "changed"
    assert collection.metadata["purpose"] == "synthetic"
    assert collection.embedding_identity["backend"] == "sentence_transformers"


@pytest.mark.parametrize(
    "path",
    ["x" * 4_097, "e\u0301.py", "bad\ud800.py"],
)
def test_where_path_uses_bounded_nfc_unicode_scalar_contract(path: str) -> None:
    from modules.infrastructure.foundups_mcp_bridge.src.holo_query_snapshot_codec import (
        SnapshotCodecError,
    )

    with pytest.raises(SnapshotCodecError, match="GET_WHERE_INVALID"):
        _collection().get(where={"path": path}, include=[])


def test_empty_include_does_not_touch_unrequested_payloads() -> None:
    collection = _collection()

    class BombValue:
        def __deepcopy__(self, _memo):
            raise AssertionError("unrequested value touched")

    class BombVectors:
        def __getitem__(self, _index):
            raise AssertionError("unrequested vectors touched")

    collection._rows[0]["document"] = BombValue()
    collection._rows[0]["metadata"] = BombValue()
    collection._vectors = BombVectors()
    assert collection.get(ids="alpha", include=[]) == {"ids": ["alpha"]}


def test_result_item_ceiling_precedes_deepcopy_and_vector_expansion() -> None:
    from modules.infrastructure.foundups_mcp_bridge.src.holo_query_snapshot_codec import (
        SnapshotCodecError,
    )

    collection = _collection()

    class BombValue:
        def __deepcopy__(self, _memo):
            raise AssertionError("deepcopy reached")

    class BombVector:
        def tolist(self):
            raise AssertionError("tolist reached")

    collection._rows[0]["document"] = BombValue()
    collection._vectors = [BombVector(), BombVector(), BombVector()]
    collection._limits = replace(collection._limits, max_result_items=1)
    with pytest.raises(SnapshotCodecError, match="RESULT_ITEM_BOUND"):
        collection.get(ids="alpha", include=["documents", "embeddings"])


def test_result_byte_ceiling_precedes_payload_expansion() -> None:
    from modules.infrastructure.foundups_mcp_bridge.src.holo_query_snapshot_codec import (
        SnapshotCodecError,
    )

    collection = _collection()
    collection._limits = replace(collection._limits, max_result_bytes=4)
    with pytest.raises(SnapshotCodecError, match="RESULT_WIRE_SIZE_BOUND"):
        collection.get(ids="alpha", include=[])


def test_workspace_ceiling_accounts_selection_arrays_before_allocation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from modules.infrastructure.foundups_mcp_bridge.src.holo_query_snapshot_codec import (
        SnapshotCodecError,
        encode_collection_snapshot,
        load_collection_snapshot,
    )
    from modules.infrastructure.foundups_mcp_bridge.tests.test_holo_query_snapshot_codec import (
        _identity,
    )

    encoded = encode_collection_snapshot(
        collection_name="navigation_code",
        rows=[{"id": f"row-{index:02d}", "document": None, "metadata": None}
              for index in range(11)],
        embeddings=[[float(index), 0.0] for index in range(11)], metric="l2",
        embedding_identity=_identity(),
    )
    collection = load_collection_snapshot(encoded.manifest, encoded.rows, encoded.vectors)
    collection._limits = replace(collection._limits, max_query_workspace_bytes=80)

    def forbidden(*_args, **_kwargs):
        raise AssertionError("selection allocation reached")

    monkeypatch.setattr(np, "concatenate", forbidden)
    monkeypatch.setattr(np, "lexsort", forbidden)
    with pytest.raises(SnapshotCodecError, match="QUERY_WORKSPACE_BOUND"):
        collection.query(query_embeddings=[[0.0, 0.0]], n_results=11, include=[])


def _compact_wire_bytes(value: object) -> int:
    return len(json.dumps(
        value, separators=(",", ":"), ensure_ascii=True, allow_nan=False,
    ).encode("ascii"))


def test_query_cardinality_preflight_precedes_nearest(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from modules.infrastructure.foundups_mcp_bridge.src.holo_query_snapshot_codec import (
        SnapshotCodecError,
    )

    collection = _collection()
    collection._limits = replace(collection._limits, max_result_items=1)

    def forbidden(*_args, **_kwargs):
        raise AssertionError("nearest reached")

    monkeypatch.setattr(collection, "_nearest", forbidden)
    with pytest.raises(SnapshotCodecError, match="RESULT_ITEM_BOUND"):
        collection.query(
            query_embeddings=[[1.0, 0.0], [0.0, 1.0]],
            n_results=2, include=[],
        )


def test_multiple_queries_account_retained_numpy_matches_in_workspace() -> None:
    from modules.infrastructure.foundups_mcp_bridge.src.holo_query_snapshot_codec import (
        SnapshotCodecError,
    )

    collection = _collection("l2")
    collection._limits = replace(
        collection._limits, max_query_workspace_bytes=270,
    )
    calls = 0
    original = collection._distance_chunk

    def recorded(query, start, end):
        nonlocal calls
        calls += 1
        return original(query, start, end)

    collection._distance_chunk = recorded
    with pytest.raises(SnapshotCodecError, match="QUERY_WORKSPACE_BOUND"):
        collection.query(
            query_embeddings=[[1.0, 0.0], [0.0, 1.0]],
            n_results=2, include=[],
        )
    assert calls == 3


def test_exact_wire_ceiling_counts_escaped_id_and_bound_equality() -> None:
    from modules.infrastructure.foundups_mcp_bridge.src.holo_query_snapshot_codec import (
        SnapshotCodecError,
        encode_collection_snapshot,
        load_collection_snapshot,
    )
    from modules.infrastructure.foundups_mcp_bridge.tests.test_holo_query_snapshot_codec import (
        _identity,
    )

    encoded = encode_collection_snapshot(
        collection_name="navigation_code",
        rows=[{"id": '"' * 100, "document": None, "metadata": None}],
        embeddings=[[1.0]], metric="l2", embedding_identity=_identity(),
    )
    collection = load_collection_snapshot(encoded.manifest, encoded.rows, encoded.vectors)
    expected = collection.get(include=[])
    exact = _compact_wire_bytes(expected)
    assert exact > 150
    collection._limits = replace(collection._limits, max_result_bytes=exact)
    assert collection.get(include=[]) == expected
    collection._limits = replace(collection._limits, max_result_bytes=exact - 1)
    with pytest.raises(SnapshotCodecError, match="RESULT_WIRE_SIZE_BOUND"):
        collection.get(include=[])


def test_exact_wire_ceiling_counts_nested_escaping_keys_and_empty_selection() -> None:
    from modules.infrastructure.foundups_mcp_bridge.src.holo_query_snapshot_codec import (
        SnapshotCodecError,
        encode_collection_snapshot,
        load_collection_snapshot,
    )
    from modules.infrastructure.foundups_mcp_bridge.tests.test_holo_query_snapshot_codec import (
        _identity,
    )

    encoded = encode_collection_snapshot(
        collection_name="navigation_code",
        rows=[{
            "id": "é\"\\\x01",
            "document": ["é", "\"", "\\", "\x02"],
            "metadata": {"ké\"\\\x03": "vé\"\\\x04"},
        }],
        embeddings=[[1.0]], metric="l2", embedding_identity=_identity(),
    )
    collection = load_collection_snapshot(encoded.manifest, encoded.rows, encoded.vectors)
    expected = collection.get(include=["documents", "metadatas"])
    exact = _compact_wire_bytes(expected)
    collection._limits = replace(collection._limits, max_result_bytes=exact)
    assert collection.get(include=["documents", "metadatas"]) == expected
    collection._limits = replace(collection._limits, max_result_bytes=exact - 1)
    with pytest.raises(SnapshotCodecError, match="RESULT_WIRE_SIZE_BOUND"):
        collection.get(include=["documents", "metadatas"])

    empty = collection.get(ids="missing", include=[])
    empty_exact = _compact_wire_bytes(empty)
    collection._limits = replace(collection._limits, max_result_bytes=empty_exact)
    assert collection.get(ids="missing", include=[]) == empty
    collection._limits = replace(collection._limits, max_result_bytes=empty_exact - 1)
    with pytest.raises(SnapshotCodecError, match="RESULT_WIRE_SIZE_BOUND"):
        collection.get(ids="missing", include=[])


@pytest.mark.parametrize("metric", ["l2", "cosine", "ip"])
def test_exact_nested_query_wire_ceiling_counts_extreme_float_rendering(metric: str) -> None:
    from modules.infrastructure.foundups_mcp_bridge.src.holo_query_snapshot_codec import (
        SnapshotCodecError,
        encode_collection_snapshot,
        load_collection_snapshot,
    )
    from modules.infrastructure.foundups_mcp_bridge.tests.test_holo_query_snapshot_codec import (
        _identity,
    )

    maximum = float(np.finfo(np.float32).max)
    encoded = encode_collection_snapshot(
        collection_name="navigation_code",
        rows=[{"id": "extreme", "document": None, "metadata": None}],
        embeddings=[[maximum, -maximum]], metric=metric,
        embedding_identity=_identity(),
    )
    collection = load_collection_snapshot(encoded.manifest, encoded.rows, encoded.vectors)
    kwargs = dict(
        query_embeddings=[[maximum, -maximum], [-maximum, maximum]],
        n_results=1, include=["embeddings", "distances"],
    )
    expected = collection.query(**kwargs)
    exact = _compact_wire_bytes(expected)
    assert exact > 20
    collection._limits = replace(collection._limits, max_result_bytes=exact)
    assert collection.query(**kwargs) == expected
    collection._limits = replace(collection._limits, max_result_bytes=exact - 1)
    with pytest.raises(SnapshotCodecError, match="RESULT_WIRE_SIZE_BOUND"):
        collection.query(**kwargs)


def test_high_dimension_cosine_workspace_rejects_before_distance_compute(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from modules.infrastructure.foundups_mcp_bridge.src.holo_query_snapshot_codec import (
        SnapshotCodecError,
        encode_collection_snapshot,
        load_collection_snapshot,
    )
    from modules.infrastructure.foundups_mcp_bridge.tests.test_holo_query_snapshot_codec import (
        _identity,
    )

    dimension = 4_096
    vector = [1.0] * dimension
    encoded = encode_collection_snapshot(
        collection_name="navigation_code",
        rows=[{"id": "wide", "document": None, "metadata": None}],
        embeddings=[vector], metric="cosine", embedding_identity=_identity(),
    )
    collection = load_collection_snapshot(encoded.manifest, encoded.rows, encoded.vectors)
    collection._limits = replace(
        collection._limits, max_query_workspace_bytes=83_000,
    )
    calls = 0

    def forbidden(*_args, **_kwargs):
        nonlocal calls
        calls += 1
        raise AssertionError("distance compute reached")

    monkeypatch.setattr(collection, "_distance_chunk", forbidden)
    with pytest.raises(SnapshotCodecError, match="QUERY_WORKSPACE_BOUND"):
        collection.query(
            query_embeddings=[vector], n_results=1, include=[],
        )
    assert calls == 0


def _chunks_for_workspace_limit(
    collection, kwargs: dict[str, object], observed: list[int], limit: int,
) -> list[int]:
    observed.clear()
    collection._limits = replace(
        collection._limits, max_query_workspace_bytes=limit,
    )
    collection.query(**kwargs)
    return list(observed)


@pytest.mark.parametrize(
    ("metric", "old_full_chunk_equality", "safe_full_chunk_equality"),
    [
        ("cosine", 78_336, 111_104),
        ("l2", 110_752, 143_616),
    ],
)
def test_multirow_reduction_workspace_and_threshold_boundaries(
    metric: str, old_full_chunk_equality: int,
    safe_full_chunk_equality: int,
) -> None:
    from modules.infrastructure.foundups_mcp_bridge.src.holo_query_snapshot_codec import (
        encode_collection_snapshot,
        load_collection_snapshot,
    )
    from modules.infrastructure.foundups_mcp_bridge.tests.test_holo_query_snapshot_codec import (
        _identity,
    )

    dimension = 1_024
    vector = [1.0] * dimension
    encoded = encode_collection_snapshot(
        collection_name="navigation_code",
        rows=[{"id": f"row-{index}", "document": None, "metadata": None}
              for index in range(4)],
        embeddings=[vector] * 4, metric=metric, embedding_identity=_identity(),
    )
    collection = load_collection_snapshot(encoded.manifest, encoded.rows, encoded.vectors)
    observed: list[int] = []
    original = collection._distance_chunk

    def recorded(query, start, end):
        observed.append(end - start)
        return original(query, start, end)

    collection._distance_chunk = recorded
    kwargs = dict(query_embeddings=[vector], n_results=2, include=[])

    assert _chunks_for_workspace_limit(
        collection, kwargs, observed, old_full_chunk_equality,
    ) == [2, 2]
    assert _chunks_for_workspace_limit(
        collection, kwargs, observed, safe_full_chunk_equality,
    ) == [4]
    assert _chunks_for_workspace_limit(
        collection, kwargs, observed, safe_full_chunk_equality - 1,
    ) == [3, 1]


def test_ip_workspace_threshold_equality_and_off_by_one() -> None:
    collection = _collection("ip")
    collection._query_chunk_rows = 10_000
    observed: list[int] = []
    original = collection._distance_chunk

    def recorded(query, start, end):
        observed.append(end - start)
        return original(query, start, end)

    collection._distance_chunk = recorded
    # fixed=8 query-f32 + 16 query-f64 + 128 selection; 3 rows * 40.
    equality = 272
    collection._limits = replace(
        collection._limits, max_query_workspace_bytes=equality,
    )
    collection.query(query_embeddings=[[1.0, 0.0]], n_results=2, include=[])
    assert observed == [3]

    observed.clear()
    collection._limits = replace(
        collection._limits, max_query_workspace_bytes=equality - 1,
    )
    collection.query(query_embeddings=[[1.0, 0.0]], n_results=2, include=[])
    assert observed == [2, 1]
