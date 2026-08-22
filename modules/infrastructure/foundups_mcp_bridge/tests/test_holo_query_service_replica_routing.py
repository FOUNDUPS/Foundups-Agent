"""Exact dual-path routing contracts for the resident Holo owner."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_query_replica_descriptor import (
    ActiveQueryReplicaBinding,
    QueryReplicaDescriptorError,
)
from modules.infrastructure.foundups_mcp_bridge.src.holo_query_service_replica import (
    QueryReplicaRuntime,
    prepare_query_backend,
)
from modules.infrastructure.foundups_mcp_bridge.tests.holo_query_service_fixtures import (
    _Backend,
)
from modules.infrastructure.foundups_mcp_bridge.tests.test_holo_query_service import (
    _query,
    _service,
)


def _binding(tmp_path: Path, *, digest: str = "1") -> ActiveQueryReplicaBinding:
    canonical = tmp_path / "canonical"
    generation = tmp_path / "replica" / "generations" / ("b" * 64)
    generation.mkdir(parents=True, exist_ok=True)
    return ActiveQueryReplicaBinding(
        descriptor_path=tmp_path / "replica" / "holoindex_query_replica.active.json",
        descriptor_digest="sha256:" + digest * 64,
        descriptor_identity=(1, 2, 3, 4, 1),
        generation_id="sha256:" + "b" * 64,
        generation_directory=generation,
        replica_id="sha256:" + "c" * 64,
        path_identity_digest="sha256:" + "d" * 64,
        canonical_repo_head_sha="a" * 40,
        canonical_repo_root_digest="sha256:" + "e" * 64,
        canonical_receipt_path=canonical / "indexes" / "receipt.json",
        canonical_receipt_digest="sha256:" + "f" * 64,
        canonical_storage_identity=str(canonical),
        query_storage_identity=str(tmp_path / "replica"),
        artifacts=(),
    )


def test_backend_factory_receives_only_query_generation_and_freshness_stays_canonical(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    binding = _binding(tmp_path)
    opened: list[Path] = []
    receipt_reads: list[Path] = []

    def factory(path: Path):
        opened.append(path)
        if path == tmp_path / "holo-store":
            raise AssertionError("canonical vectors opened by backend")
        backend = _Backend()
        backend.ssd_path = path
        return backend

    owner = _service(
        tmp_path, monkeypatch,
        backend_factory=factory,
        receipt_loader=lambda path: receipt_reads.append(path) or None,
        _replica_verifier_for_test=lambda: binding,
    )
    # Restore the canonical synthetic receipt loader used by the fixture.
    owner._freshness._loader = lambda path: (
        receipt_reads.append(path)
        or __import__(
            "modules.infrastructure.foundups_mcp_bridge.tests.test_holo_query_service",
            fromlist=["_receipt"],
        )._receipt(repo_root=tmp_path, ssd_path=tmp_path / "holo-store")
    )
    try:
        result = _query(owner)
    finally:
        owner.close()
    assert result["ok"] is True
    assert opened == [binding.generation_directory]
    assert receipt_reads and set(receipt_reads) == {tmp_path / "holo-store" / "indexes" / "holoindex_freshness_receipt.json"}
    assert result["query_replica_descriptor_digest"] == binding.descriptor_digest
    assert str(tmp_path / "replica") not in json.dumps(result)
    assert result["freshness_receipt_path"] == ""


def test_active_descriptor_swap_during_backend_construction_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    first, second = _binding(tmp_path, digest="1"), _binding(tmp_path, digest="2")
    calls = 0

    def verifier() -> ActiveQueryReplicaBinding:
        nonlocal calls
        calls += 1
        return first if calls < 3 else second

    owner = _service(
        tmp_path, monkeypatch,
        backend_factory=lambda path: _Backend(),
        _replica_verifier_for_test=verifier,
    )
    try:
        result = _query(owner)
    finally:
        owner.close()
    assert result["ok"] is False
    assert result["error"] in {"QUERY_REPLICA_INVALID", "SEMANTIC_BACKEND_UNAVAILABLE"}


def test_backend_reporting_canonical_storage_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    binding = _binding(tmp_path)

    def factory(_path: Path):
        backend = _Backend()
        backend.ssd_path = tmp_path / "holo-store"
        return backend

    owner = _service(
        tmp_path, monkeypatch,
        backend_factory=factory,
        _replica_verifier_for_test=lambda: binding,
    )
    try:
        result = _query(owner)
    finally:
        owner.close()
    assert result["ok"] is False
    assert result["error"] == "SEMANTIC_BACKEND_UNAVAILABLE"


def test_production_backend_requires_exact_snapshot_generation(tmp_path: Path) -> None:
    binding = _binding(tmp_path)
    runtime = QueryReplicaRuntime(
        tmp_path / "canonical", lambda: binding, binding,
        require_snapshot_generation=True,
    )
    backend = _Backend()
    backend.ssd_path = binding.generation_directory
    backend.query_snapshot_generation_id = "sha256:" + "9" * 64

    with pytest.raises(
        QueryReplicaDescriptorError,
        match="QUERY_REPLICA_SNAPSHOT_GENERATION_MISMATCH",
    ):
        prepare_query_backend(runtime, lambda _path: backend)
