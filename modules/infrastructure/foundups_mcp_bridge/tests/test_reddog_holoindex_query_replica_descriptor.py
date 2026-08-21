"""Synthetic contracts for active query-replica descriptor admission."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from modules.infrastructure.foundups_mcp_bridge.tests.test_reddog_holoindex_query_replica import (
    SHA,
    _ReceiptProof,
    _fixture,
    _materialize,
)


def _dependencies(*, lock_probe=None):
    from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_query_replica_descriptor import (
        _DescriptorDependencies,
    )

    return _DescriptorDependencies(
        state_reader=lambda _root: SimpleNamespace(
            proven_clean=True, head_sha=SHA, error=""
        ),
        lock_probe=lock_probe or (
            lambda _path: SimpleNamespace(clear=True, held=False, status="clear")
        ),
        receipt_opener=lambda **_kwargs: _ReceiptProof(),
    )


def _verify(fixture, **overrides):
    from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_query_replica_descriptor import (
        _verify_active_query_replica_for_test,
    )

    canonical, repo, _replica, proof, _binding, _manifests = fixture
    return _verify_active_query_replica_for_test(
        replica_root_proof=proof,
        canonical_repo_root=repo,
        canonical_ssd_path=canonical,
        dependencies=overrides.pop("dependencies", _dependencies()),
        **overrides,
    )


def test_materialized_descriptor_routes_to_exact_generation_without_path_leak(
    tmp_path: Path,
) -> None:
    fixture = _fixture(tmp_path)
    result = _materialize(fixture)
    binding = _verify(fixture)

    assert binding.descriptor_digest == result.descriptor_digest
    assert binding.generation_directory == result.generation_directory
    assert binding.generation_id == fixture[4].generation_id
    assert set(binding.public_binding) == {
        "query_replica_descriptor_digest",
        "query_replica_generation_id",
        "query_replica_id",
        "query_replica_path_identity_digest",
    }
    assert str(fixture[2]) not in json.dumps(binding.public_binding)


def test_replica_artifact_mutation_is_rejected(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    result = _materialize(fixture)
    target = result.generation_directory / "vectors" / "chroma.sqlite3"
    target.write_bytes(b"changed-generation")

    with pytest.raises(RuntimeError, match="ARTIFACT_DIGEST_MISMATCH"):
        _verify(fixture)


def test_active_descriptor_schema_and_generation_path_fail_closed(
    tmp_path: Path,
) -> None:
    fixture = _fixture(tmp_path)
    result = _materialize(fixture)
    payload = json.loads(result.active_descriptor.read_text(encoding="utf-8"))
    payload["schema_version"] = "holoindex_query_replica.v999"
    result.active_descriptor.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(RuntimeError, match="DESCRIPTOR_SCHEMA_INVALID"):
        _verify(fixture)


def test_authority_or_maintenance_lease_transition_is_rejected(
    tmp_path: Path,
) -> None:
    fixture = _fixture(tmp_path)
    _materialize(fixture)
    calls = 0

    def changing_probe(_path: Path):
        nonlocal calls
        calls += 1
        held = calls >= 3
        return SimpleNamespace(clear=not held, held=held, status="held" if held else "clear")

    with pytest.raises(RuntimeError, match="LEASE_ACTIVE"):
        _verify(fixture, dependencies=_dependencies(lock_probe=changing_probe))


def test_unlisted_generation_file_and_hardlink_are_rejected(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    result = _materialize(fixture)
    source = result.generation_directory / "vectors" / "chroma.sqlite3"
    extra = result.generation_directory / "vectors" / "unlisted.bin"
    extra.write_bytes(b"unlisted")
    with pytest.raises(RuntimeError, match="MANIFEST_MISMATCH"):
        _verify(fixture)
    extra.unlink()
    try:
        source_link = result.generation_directory / "vectors" / "hardlink.sqlite3"
        source_link.hardlink_to(source)
    except OSError:
        pytest.skip("filesystem does not permit hardlinks")
    with pytest.raises(RuntimeError, match="FILE_NOT_PRIVATE_REGULAR"):
        _verify(fixture)
