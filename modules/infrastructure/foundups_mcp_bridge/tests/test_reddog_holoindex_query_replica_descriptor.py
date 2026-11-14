"""Synthetic contracts for active query-replica descriptor admission."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
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


def _fixture_with_query_snapshots(tmp_path: Path):
    return _fixture(tmp_path)


def _revalidate(fixture, admitted, **overrides):
    from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_query_replica_descriptor import (
        _revalidate_admitted_query_replica_for_test,
    )

    canonical, repo, _replica, proof, _binding, _manifests = fixture
    return _revalidate_admitted_query_replica_for_test(
        admitted_binding=admitted,
        replica_root_proof=proof,
        canonical_repo_root=repo,
        canonical_ssd_path=canonical,
        dependencies=overrides.pop("dependencies", _dependencies()),
        **overrides,
    )


def _descriptor_entry(path: Path, generation: Path) -> dict[str, object]:
    digest = "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
    return {
        "path": path.relative_to(generation).as_posix(),
        "size": path.stat().st_size,
        "sha256": digest,
        "source_before_sha256": digest,
        "source_after_sha256": digest,
    }


def _rewrite_as_legacy_full_descriptor(fixture, *, retain_snapshots: bool = False):
    result = _materialize(fixture)
    snapshots = result.generation_directory / "vectors" / "query_snapshots"
    if not retain_snapshots:
        shutil.rmtree(snapshots)
    sqlite = result.generation_directory / "vectors" / "chroma.sqlite3"
    sqlite.write_bytes(b"historical-legacy-vector-database")
    segment = result.generation_directory / "vectors" / "legacy-segment"
    segment.mkdir()
    for name in (
        "data_level0.bin", "header.bin", "length.bin", "link_lists.bin",
    ):
        (segment / name).write_bytes(name.encode("ascii"))
    payload = json.loads(result.active_descriptor.read_text(encoding="utf-8"))
    retained = [
        entry for entry in payload["files"]
        if entry["path"].startswith("models/")
        or (retain_snapshots and entry["path"].startswith("vectors/query_snapshots/"))
    ]
    payload["files"] = retained + [
        _descriptor_entry(path, result.generation_directory)
        for path in (sqlite, *sorted(segment.iterdir()))
    ]
    payload["files"].sort(key=lambda entry: entry["path"])
    result.active_descriptor.write_text(
        json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    return result


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
    target = result.generation_directory / "vectors" / "query_snapshots" / "snapshot_set.json"
    target.write_bytes(b"changed-generation")

    with pytest.raises(RuntimeError, match="ARTIFACT_DIGEST_MISMATCH"):
        _verify(fixture)


def test_historical_full_descriptor_remains_verifiable_for_audit(
    tmp_path: Path,
) -> None:
    fixture = _fixture(tmp_path)
    result = _rewrite_as_legacy_full_descriptor(fixture)
    admitted = _verify(fixture)

    assert "vectors/chroma.sqlite3" in {
        artifact.relative_path for artifact in admitted.artifacts
    }
    assert not (result.generation_directory / "vectors" / "query_snapshots").exists()


def test_sqlite_only_historical_descriptor_is_rejected(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    result = _rewrite_as_legacy_full_descriptor(fixture)
    shutil.rmtree(result.generation_directory / "models")
    vectors = result.generation_directory / "vectors"
    for path in tuple(vectors.iterdir()):
        if path.name != "chroma.sqlite3":
            shutil.rmtree(path) if path.is_dir() else path.unlink()
    payload = json.loads(result.active_descriptor.read_text(encoding="utf-8"))
    payload["files"] = [
        entry for entry in payload["files"]
        if entry["path"] == "vectors/chroma.sqlite3"
    ]
    result.active_descriptor.write_text(
        json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError, match="RUNTIME_ARTIFACT_SET_INCOMPLETE"):
        _verify(fixture)


def test_modern_snapshot_descriptor_mixed_with_sqlite_is_rejected(
    tmp_path: Path,
) -> None:
    fixture = _fixture(tmp_path)
    result = _materialize(fixture)
    sqlite = result.generation_directory / "vectors" / "chroma.sqlite3"
    sqlite.write_bytes(b"mixed-legacy-payload")
    payload = json.loads(result.active_descriptor.read_text(encoding="utf-8"))
    payload["files"].append(
        _descriptor_entry(sqlite, result.generation_directory)
    )
    payload["files"].sort(key=lambda entry: entry["path"])
    result.active_descriptor.write_text(
        json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError, match="RUNTIME_ARTIFACT_SET_INCOMPLETE"):
        _verify(fixture)


def test_historical_full_descriptor_with_snapshots_is_audit_only(
    tmp_path: Path,
) -> None:
    fixture = _fixture(tmp_path)
    _rewrite_as_legacy_full_descriptor(fixture, retain_snapshots=True)
    admitted = _verify(fixture)

    with pytest.raises(RuntimeError, match="RUNTIME_ARTIFACT_SET_INCOMPLETE"):
        _revalidate(fixture, admitted)


def test_descriptor_rejects_case_variant_nested_model_marker(
    tmp_path: Path,
) -> None:
    fixture = _fixture(tmp_path)
    result = _materialize(fixture)
    marker = (
        result.generation_directory / "models" / "sentence_transformers"
        / "all-MiniLM-L6-v2" / "nested" / "MODULES.JSON"
    )
    marker.parent.mkdir()
    marker.write_bytes(b"[]")
    payload = json.loads(result.active_descriptor.read_text(encoding="utf-8"))
    payload["files"].append(
        _descriptor_entry(marker, result.generation_directory)
    )
    payload["files"].sort(key=lambda entry: entry["path"])
    result.active_descriptor.write_text(
        json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError, match="RUNTIME_ARTIFACT_SET_INCOMPLETE"):
        _verify(fixture)


def test_admitted_binding_revalidation_rejects_runtime_artifact_surface_drift(
    tmp_path: Path,
) -> None:
    relatives = (
        Path("vectors/query_snapshots/navigation_code.rows.jsonl"),
        Path("models/sentence_transformers/all-MiniLM-L6-v2/model.safetensors"),
    )
    for index, relative in enumerate(relatives):
        case = tmp_path / f"mutation-{index}"
        case.mkdir()
        fixture = _fixture_with_query_snapshots(case)
        result = _materialize(fixture)
        admitted = _verify(fixture)
        assert _revalidate(fixture, admitted) == admitted
        (result.generation_directory / relative).write_bytes(b"changed-runtime")
        with pytest.raises(RuntimeError, match="RUNTIME_ARTIFACT_CHANGED"):
            _revalidate(fixture, admitted)

    extra_case = tmp_path / "extra"
    extra_case.mkdir()
    fixture = _fixture_with_query_snapshots(extra_case)
    result = _materialize(fixture)
    admitted = _verify(fixture)
    extra = result.generation_directory / "models" / "unlisted-runtime.bin"
    extra.write_bytes(b"unlisted")
    with pytest.raises(RuntimeError, match="RUNTIME_ARTIFACT_SET_CHANGED"):
        _revalidate(fixture, admitted)


def test_admitted_binding_revalidation_rejects_descriptor_swap(
    tmp_path: Path,
) -> None:
    fixture = _fixture_with_query_snapshots(tmp_path)
    result = _materialize(fixture)
    admitted = _verify(fixture)
    payload = json.loads(result.active_descriptor.read_text(encoding="utf-8"))
    payload["created_at"] = "2026-08-18T00:00:00+00:00"
    result.active_descriptor.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(RuntimeError, match="BINDING_CHANGED"):
        _revalidate(fixture, admitted)


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
    source = result.generation_directory / "vectors" / "query_snapshots" / "snapshot_set.json"
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
