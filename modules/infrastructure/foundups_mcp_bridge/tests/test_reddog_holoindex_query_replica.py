"""Adversarial contracts for immutable per-generation Holo query replicas."""

from __future__ import annotations

import hashlib
import json
import os
import stat
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from holo_index.freshness_receipt import BASELINE_QUERY_COLLECTIONS, freshness_receipt_path
from holo_index.maintenance_lock import (
    acquire_authority_update_lease,
    acquire_maintenance_lease,
    authority_update_lock_path,
    maintenance_lock_path,
)
from holo_index.repository_state import repository_root_digest
from holo_index.storage_contract import storage_path_identity


SHA = "a" * 40
GENERATION = "sha256:" + "b" * 64
RECEIPT_DIGEST = "sha256:" + "c" * 64


class _ReceiptProof:
    def __init__(self, fail_at: int = 0) -> None:
        self.calls = 0
        self.fail_at = fail_at

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        return None

    def revalidate(self) -> None:
        self.calls += 1
        if self.fail_at and self.calls >= self.fail_at:
            raise ValueError("receipt swapped")


def _digest(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _snapshot_tree(vectors: Path) -> Path:
    snapshots = vectors / "query_snapshots"
    snapshots.mkdir()
    collections = {}
    for collection in sorted(BASELINE_QUERY_COLLECTIONS):
        artifacts = {}
        for kind, suffix in (
            ("manifest", "manifest.json"),
            ("rows", "rows.jsonl"),
            ("vectors", "vectors.f32"),
        ):
            path = snapshots / f"{collection}.{suffix}"
            path.write_bytes(f"{collection}:{kind}".encode("ascii"))
            artifacts[kind] = {
                "path": path.name,
                "bytes": path.stat().st_size,
                "sha256": _digest(path),
            }
        collections[collection] = artifacts
    payload = {
        "schema_version": "holoindex_query_snapshot_set.v1",
        "generation_id": GENERATION,
        "collections": collections,
    }
    (snapshots / "snapshot_set.json").write_bytes(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("ascii") + b"\n"
    )
    return snapshots


def _tree_manifest(logical_name: str, source: Path, relative_root: str):
    from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_acceptance_guards import (
        ExpectedArtifactFile,
    )
    from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_artifact_manifest import (
        ModelCopyLimits,
        snapshot_artifact_files,
    )
    from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_query_replica import (
        ArtifactTreeManifest,
    )

    snapshot = snapshot_artifact_files(
        source,
        ModelCopyLimits(
            max_files=200_000,
            max_file_bytes=2_147_483_648,
            max_total_bytes=8_589_934_592,
        ),
    )
    files = tuple(
        ExpectedArtifactFile(
            relative_path=relative,
            size=metadata.st_size,
            sha256=_digest(file),
        )
        for relative, file, metadata in snapshot.files
    )
    return ArtifactTreeManifest(logical_name, source, relative_root, files)


def test_artifact_snapshot_order_matches_casefolded_manifest_order(
    tmp_path: Path,
) -> None:
    from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_artifact_manifest import (
        ExpectedArtifactFile,
        ModelCopyLimits,
        snapshot_artifact_files,
        validate_expected_manifest,
    )

    source = tmp_path / "model"
    source.mkdir()
    (source / "README.md").write_bytes(b"readme")
    (source / "config.json").write_bytes(b"{}")
    snapshot = snapshot_artifact_files(
        source,
        ModelCopyLimits(max_files=10, max_file_bytes=100, max_total_bytes=100),
    )
    manifest = tuple(
        ExpectedArtifactFile(relative, metadata.st_size, _digest(path))
        for relative, path, metadata in snapshot.files
    )

    assert tuple(item.relative_path for item in manifest) == (
        "config.json",
        "README.md",
    )
    assert validate_expected_manifest(snapshot.files, manifest)


def test_large_descriptor_secret_scan_is_complete_without_truncation() -> None:
    from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_acceptance_guards import (
        AcceptanceGuardError,
    )
    from modules.infrastructure.foundups_mcp_bridge.src.reddog_private_json_publication import (
        _encode_payload,
    )

    payload = {
        "schema_version": "holoindex_query_replica.v1",
        "files": [
            {"path": f"vectors/chunk-{index:04d}.bin"}
            for index in range(600)
        ],
    }

    encoded = _encode_payload(
        payload,
        2_097_152,
        expected_schema="holoindex_query_replica.v1",
        reject_absolute_paths=False,
    )
    assert json.loads(encoded) == payload

    payload["files"][-1]["token"] = "not-persistable"
    with pytest.raises(AcceptanceGuardError, match="RECEIPT_NOT_SECRET_FREE"):
        _encode_payload(
            payload,
            2_097_152,
            expected_schema="holoindex_query_replica.v1",
            reject_absolute_paths=False,
        )


def _canonical_fixture_paths(tmp_path: Path):
    canonical = tmp_path / "canonical"
    repo = tmp_path / "repo"
    canonical.mkdir()
    repo.mkdir()
    vectors = canonical / "vectors"
    vectors.mkdir()
    snapshots = _snapshot_tree(vectors)
    model_relative = Path("models") / "sentence_transformers" / "all-MiniLM-L6-v2"
    model = canonical / model_relative
    model.mkdir(parents=True)
    for name, payload in {
        "config.json": b"{}",
        "model.safetensors": b"model-generation",
        "modules.json": b"[]",
        "tokenizer.json": b"{}",
    }.items():
        (model / name).write_bytes(payload)
    receipt = freshness_receipt_path(canonical)
    receipt.parent.mkdir()
    receipt.write_bytes(b"canonical-receipt")
    with acquire_authority_update_lease(canonical):
        pass
    with acquire_maintenance_lease(maintenance_lock_path(canonical)):
        pass
    return canonical, repo, snapshots, model, model_relative, receipt


def _fixture(tmp_path: Path):
    from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_acceptance_guards import (
        create_isolated_store,
    )
    from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_query_replica import (
        CanonicalGenerationBinding,
    )

    canonical, repo, vectors, model, model_relative, receipt = (
        _canonical_fixture_paths(tmp_path)
    )
    replica = tmp_path / "replica"
    root_proof = create_isolated_store(
        replica, canonical_store=canonical, repo_roots=(repo,)
    )

    manifests = (
        _tree_manifest("model", model, model_relative.as_posix()),
        _tree_manifest("snapshots", vectors, "vectors/query_snapshots"),
    )
    binding = CanonicalGenerationBinding(
        repo_root=repo,
        repo_root_digest=repository_root_digest(repo),
        repo_head_sha=SHA,
        receipt_path=receipt,
        receipt_digest=RECEIPT_DIGEST,
        generation_id=GENERATION,
        canonical_storage_identity=storage_path_identity(canonical),
    )
    return canonical, repo, replica, root_proof, binding, manifests


def _deps(
    *, receipt=None, acquire_lease=None, copy_tree=None, publish_json=None,
    publish_directory=None, orphan_token=None,
):
    from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_query_replica import (
        _QueryReplicaTestDependencies,
    )

    kwargs = {
        "open_receipt": lambda **_kwargs: receipt or _ReceiptProof(),
        "now": lambda: datetime(2026, 8, 17, tzinfo=timezone.utc),
    }
    if acquire_lease is not None:
        kwargs["acquire_lease"] = acquire_lease
    if copy_tree is not None:
        kwargs["copy_tree"] = copy_tree
    if publish_json is not None:
        kwargs["publish_json"] = publish_json
    if publish_directory is not None:
        kwargs["publish_directory"] = publish_directory
    if orphan_token is not None:
        kwargs["orphan_token"] = orphan_token
    return _QueryReplicaTestDependencies(**kwargs)


def _materialize(fixture, **kwargs):
    from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_query_replica import (
        _materialize_query_replica_for_test,
    )

    canonical, _repo, _replica, root_proof, binding, manifests = fixture
    return _materialize_query_replica_for_test(
        canonical_store=canonical,
        replica_root_proof=root_proof,
        binding=binding,
        manifests=manifests,
        dependencies=kwargs.pop("dependencies", _deps()),
        **kwargs,
    )


def test_valid_materialization_is_deterministic_and_preserves_canonical_bytes(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    canonical = fixture[0]
    before = {path.relative_to(canonical).as_posix(): _digest(path) for path in canonical.rglob("*") if path.is_file()}
    result = _materialize(fixture)
    after = {path.relative_to(canonical).as_posix(): _digest(path) for path in canonical.rglob("*") if path.is_file()}
    descriptor = json.loads(result.active_descriptor.read_text(encoding="utf-8"))
    assert before == after
    assert result.file_count == 26
    assert descriptor["schema_version"] == "holoindex_query_replica.v1"
    assert descriptor["status"] == "CURRENT"
    paths = [entry["path"] for entry in descriptor["files"]]
    assert paths == sorted(paths)
    assert all(
        entry["sha256"] == entry["source_before_sha256"] == entry["source_after_sha256"]
        for entry in descriptor["files"]
    )
    assert list((fixture[2] / ".query-replica-orphans").iterdir()) == []


@pytest.mark.skipif(os.name != "nt", reason="Windows raw-handle scalability")
def test_windows_materializer_does_not_exhaust_crt_descriptors(
    tmp_path: Path,
) -> None:
    fixture = _fixture(tmp_path)
    canonical, repo, replica, root_proof = fixture[:4]
    vectors = fixture[5][1].source_root
    for index in range(600):
        (vectors / f"chunk-{index:04d}.bin").write_bytes(b"segment")
    manifest = _tree_manifest("vectors", vectors, "vectors")
    from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_acceptance_model_copy import (
        copy_model_snapshot,
    )
    from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_artifact_manifest import (
        ModelCopyLimits,
    )

    result = copy_model_snapshot(
        vectors,
        replica / "vectors-copy",
        store_proof=root_proof,
        canonical_store=canonical,
        repo_roots=(repo,),
        limits=ModelCopyLimits(
            max_files=1_000,
            max_file_bytes=1_000_000,
            max_total_bytes=10_000_000,
        ),
        expected_manifest=manifest.files,
    )

    assert result.file_count == 622


def test_source_mutation_during_copy_is_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from modules.infrastructure.foundups_mcp_bridge.src import (
        reddog_holoindex_acceptance_model_descriptors as descriptors,
    )
    from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_query_replica import QueryReplicaError

    fixture = _fixture(tmp_path)
    original = descriptors._descriptor_sha256
    calls = {"count": 0}

    def changed_after_first(descriptor: int) -> str:
        calls["count"] += 1
        digest = original(descriptor)
        return "sha256:" + "0" * 64 if calls["count"] == 2 else digest

    monkeypatch.setattr(descriptors, "_descriptor_sha256", changed_after_first)
    with pytest.raises(QueryReplicaError):
        _materialize(fixture)
    assert not (fixture[2] / "holoindex_query_replica.active.json").exists()


def test_receipt_generation_swap_is_rejected(tmp_path: Path) -> None:
    from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_query_replica import QueryReplicaError

    fixture = _fixture(tmp_path)
    with pytest.raises((QueryReplicaError, ValueError)):
        _materialize(fixture, dependencies=_deps(receipt=_ReceiptProof(fail_at=2)))
    assert not (fixture[2] / "holoindex_query_replica.active.json").exists()


def test_final_receipt_failure_quarantines_just_published_active(
    tmp_path: Path,
) -> None:
    from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_query_replica import QueryReplicaError

    fixture = _fixture(tmp_path)
    with pytest.raises(QueryReplicaError, match="ACTIVE_QUARANTINED") as raised:
        _materialize(
            fixture, dependencies=_deps(
                receipt=_ReceiptProof(fail_at=6), orphan_token=lambda: "fixed"
            )
        )
    assert not (fixture[2] / "holoindex_query_replica.active.json").exists()
    orphan = fixture[2] / raised.value.orphan_relative_path
    assert orphan.is_file()
    assert json.loads(orphan.read_text(encoding="utf-8"))["status"] == "CURRENT"
    assert (fixture[2] / "generations" / GENERATION.removeprefix("sha256:")).is_dir()
    for path in (
        authority_update_lock_path(fixture[0]), maintenance_lock_path(fixture[0]),
    ):
        with acquire_maintenance_lease(path):
            pass


def test_active_quarantine_preserves_same_name_replacement(tmp_path: Path) -> None:
    from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_query_replica import QueryReplicaError
    from modules.infrastructure.foundups_mcp_bridge.src.reddog_private_json_publication import (
        atomic_publish_private_json_proven,
    )

    fixture = _fixture(tmp_path)
    foreign = b"foreign-active-descriptor"

    def replace_after_publish(*args, **kwargs):
        proof = atomic_publish_private_json_proven(*args, **kwargs)
        proof.path.unlink()
        proof.path.write_bytes(foreign)
        return proof

    dependencies = _deps(publish_json=replace_after_publish, orphan_token=lambda: "fixed")
    with pytest.raises(QueryReplicaError, match="ACTIVE_QUARANTINED") as raised:
        _materialize(
            fixture, dependencies=dependencies
        )
    active = fixture[2] / "holoindex_query_replica.active.json"
    assert not active.exists()
    assert (fixture[2] / raised.value.orphan_relative_path).read_bytes() == foreign


def test_active_quarantine_preserves_same_inode_same_size_mutation(tmp_path: Path) -> None:
    from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_query_replica import QueryReplicaError
    from modules.infrastructure.foundups_mcp_bridge.src.reddog_private_json_publication import (
        atomic_publish_private_json_proven,
    )

    fixture = _fixture(tmp_path)
    mutated: dict[str, bytes] = {}

    def mutate_after_publish(*args, **kwargs):
        proof = atomic_publish_private_json_proven(*args, **kwargs)
        replacement = b"X" * proof.size
        with proof.path.open("r+b") as stream:
            stream.write(replacement)
            stream.flush()
        mutated["bytes"] = replacement
        return proof

    with pytest.raises(QueryReplicaError, match="ACTIVE_QUARANTINED") as raised:
        _materialize(
            fixture,
            dependencies=_deps(
                publish_json=mutate_after_publish, orphan_token=lambda: "fixed"
            ),
        )
    active = fixture[2] / "holoindex_query_replica.active.json"
    assert not active.exists()
    assert (fixture[2] / raised.value.orphan_relative_path).read_bytes() == mutated["bytes"]


def test_active_quarantine_failure_leaves_active_and_reports_relative_name(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    from modules.infrastructure.foundups_mcp_bridge.src import (
        reddog_holoindex_query_replica as query_replica,
    )
    from modules.infrastructure.foundups_mcp_bridge.src.reddog_private_json_publication import (
        atomic_publish_private_json_proven,
    )

    fixture = _fixture(tmp_path)

    def mutate_after_publish(*args, **kwargs):
        proof = atomic_publish_private_json_proven(*args, **kwargs)
        with proof.path.open("r+b") as stream:
            stream.write(b"X" * proof.size)
        return proof

    monkeypatch.setattr(
        query_replica, "quarantine_proven_private_json",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("rename denied")),
    )
    with pytest.raises(
        query_replica.QueryReplicaError, match="ACTIVE_QUARANTINE_FAILED"
    ) as raised:
        _materialize(fixture, dependencies=_deps(publish_json=mutate_after_publish))
    assert raised.value.unsafe_relative_path == "holoindex_query_replica.active.json"
    assert not Path(raised.value.unsafe_relative_path).is_absolute()
    assert (fixture[2] / raised.value.unsafe_relative_path).is_file()


def test_both_existing_leases_are_held_through_active_publish_and_released(
    tmp_path: Path,
) -> None:
    from holo_index.maintenance_lock import MaintenanceLeaseBusy
    from modules.infrastructure.foundups_mcp_bridge.src.reddog_private_json_publication import (
        atomic_publish_private_json_proven,
    )

    fixture = _fixture(tmp_path)
    canonical = fixture[0]
    lock_paths = (
        authority_update_lock_path(canonical), maintenance_lock_path(canonical),
    )
    before = {path: path.read_bytes() for path in lock_paths}

    def assert_locked_then_publish(*args, **kwargs):
        for path in lock_paths:
            with pytest.raises(MaintenanceLeaseBusy):
                acquire_maintenance_lease(path)
        return atomic_publish_private_json_proven(*args, **kwargs)

    _materialize(fixture, dependencies=_deps(publish_json=assert_locked_then_publish))

    assert {path: path.read_bytes() for path in lock_paths} == before
    for path in lock_paths:
        with acquire_maintenance_lease(path):
            pass


def test_source_destination_overlap_is_rejected(tmp_path: Path) -> None:
    from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_acceptance_guards import StoreProof
    from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_query_replica import QueryReplicaError

    fixture = _fixture(tmp_path)
    metadata = fixture[0].stat()
    forged = StoreProof(fixture[0], metadata.st_dev, metadata.st_ino, metadata.st_mode, 0)
    with pytest.raises((QueryReplicaError, Exception)):
        from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_query_replica import _materialize_query_replica_for_test
        _materialize_query_replica_for_test(
            canonical_store=fixture[0], replica_root_proof=forged,
            binding=fixture[4], manifests=fixture[5], dependencies=_deps(),
        )


@pytest.mark.parametrize("kind", ["symlink", "hardlink", "special"])
def test_link_hardlink_and_special_sources_are_rejected(tmp_path: Path, kind: str) -> None:
    from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_query_replica import QueryReplicaError

    fixture = _fixture(tmp_path)
    vectors = fixture[5][1].source_root
    source = vectors / "snapshot_set.json"
    if kind == "symlink":
        try:
            (vectors / "bad-link").symlink_to(source)
        except OSError:
            pytest.skip("symlink creation unavailable")
    elif kind == "hardlink":
        os.link(source, vectors / "bad-hardlink")
    else:
        if os.name == "nt":
            pytest.skip("portable special-file fixture unavailable on Windows")
        os.mkfifo(vectors / "bad-fifo")
    with pytest.raises(QueryReplicaError):
        _materialize(fixture)


@pytest.mark.parametrize("defect", ["reparse", "special"])
def test_injected_windows_reparse_and_special_sources_fail_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, defect: str
) -> None:
    from modules.infrastructure.foundups_mcp_bridge.src import (
        reddog_holoindex_artifact_manifest as artifact_manifest,
    )
    from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_query_replica import QueryReplicaError

    fixture = _fixture(tmp_path)
    target = fixture[0] / "models" / "sentence_transformers" / "all-MiniLM-L6-v2" / "config.json"
    if defect == "reparse":
        original = artifact_manifest._is_link_or_reparse
        monkeypatch.setattr(
            artifact_manifest,
            "_is_link_or_reparse",
            lambda path, metadata=None: Path(str(path).removeprefix("\\\\?\\")) == target or original(path, metadata),
        )
    else:
        original_lstat = artifact_manifest.os.lstat

        def special_lstat(path):
            value = original_lstat(path)
            if Path(str(path).removeprefix("\\\\?\\")) != target:
                return value
            return SimpleNamespace(
                st_mode=stat.S_IFIFO,
                st_dev=value.st_dev,
                st_ino=value.st_ino,
                st_size=value.st_size,
                st_mtime_ns=value.st_mtime_ns,
                st_nlink=1,
                st_file_attributes=0,
                st_reparse_tag=0,
            )

        monkeypatch.setattr(artifact_manifest.os, "lstat", special_lstat)
    with pytest.raises(QueryReplicaError):
        _materialize(fixture)


@pytest.mark.parametrize("bound", ["count", "bytes", "path", "descriptor"])
def test_resource_bounds_fail_closed(tmp_path: Path, bound: str) -> None:
    from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_query_replica import (
        QueryReplicaError,
        QueryReplicaLimits,
    )

    fixture = _fixture(tmp_path)
    limits = QueryReplicaLimits(
        max_files=1 if bound == "count" else 100,
        max_file_bytes=100_000,
        max_total_bytes=1 if bound == "bytes" else 1_000_000,
        max_path_bytes=2 if bound == "path" else 512,
        max_descriptor_bytes=1 if bound == "descriptor" else 4_194_304,
    )
    with pytest.raises(QueryReplicaError):
        _materialize(fixture, limits=limits)


@pytest.mark.parametrize("target", ["descriptor", "generation"])
def test_preexisting_publication_target_is_never_overwritten(tmp_path: Path, target: str) -> None:
    from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_query_replica import QueryReplicaError

    fixture = _fixture(tmp_path)
    replica = fixture[2]
    if target == "descriptor":
        path = replica / "holoindex_query_replica.active.json"
        path.write_bytes(b"foreign")
    else:
        path = replica / "generations" / GENERATION.removeprefix("sha256:")
        path.mkdir(parents=True)
    with pytest.raises(QueryReplicaError):
        _materialize(fixture)
    assert path.exists()


def test_copy_or_hash_failure_leaves_no_active_descriptor(tmp_path: Path) -> None:
    from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_query_replica import QueryReplicaError

    fixture = _fixture(tmp_path)

    def fail_copy(*_args, **_kwargs):
        raise OSError("copy failed")

    with pytest.raises(QueryReplicaError):
        _materialize(
            fixture,
            dependencies=_deps(copy_tree=fail_copy, orphan_token=lambda: "fixed"),
        )
    assert not (fixture[2] / "holoindex_query_replica.active.json").exists()
    assert not list(fixture[2].glob(".query-replica-stage-*"))
    staging_orphans = list((fixture[2] / ".query-replica-orphans").glob("staging-*") )
    assert len(staging_orphans) == 1
    assert staging_orphans[0].is_dir()


@pytest.mark.skipif(os.name != "nt", reason="Windows partial-copy preservation")
def test_windows_copy_failure_quarantines_staging_with_partial_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    from modules.infrastructure.foundups_mcp_bridge.src import (
        reddog_holoindex_acceptance_model_copy as model_copy,
    )
    from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_query_replica import QueryReplicaError

    fixture = _fixture(tmp_path)
    partial = b"partial-model-copy"

    def fail_after_write(_source_fd, target_fd, _expected, **_kwargs):
        os.write(target_fd, partial)
        os.fsync(target_fd)
        raise model_copy.AcceptanceGuardError("INJECTED_WINDOWS_COPY_FAILURE")

    monkeypatch.setattr(model_copy, "copy_descriptors", fail_after_write)
    with pytest.raises(QueryReplicaError):
        _materialize(
            fixture, dependencies=_deps(orphan_token=lambda: "fixed")
        )
    assert not (fixture[2] / "holoindex_query_replica.active.json").exists()
    orphans = list((fixture[2] / ".query-replica-orphans").glob("staging-*") )
    assert len(orphans) == 1
    assert partial in {path.read_bytes() for path in orphans[0].rglob("*") if path.is_file()}


def test_atomic_descriptor_failure_leaves_published_generation_inactive(tmp_path: Path) -> None:
    from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_query_replica import QueryReplicaError

    fixture = _fixture(tmp_path)

    def fail_publish(*_args, **_kwargs):
        raise OSError("descriptor publish failed")

    with pytest.raises(QueryReplicaError):
        _materialize(fixture, dependencies=_deps(publish_json=fail_publish))
    assert not (fixture[2] / "holoindex_query_replica.active.json").exists()
    assert (fixture[2] / "generations" / GENERATION.removeprefix("sha256:")).is_dir()


def test_cleanup_never_removes_replaced_foreign_staging(tmp_path: Path) -> None:
    from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_query_replica import QueryReplicaError

    fixture = _fixture(tmp_path)
    foreign: dict[str, Path] = {}

    def replace_then_fail(_source, destination, **_kwargs):
        staging = Path(destination).parents[2]
        moved = staging.with_name(staging.name + "-owned-moved")
        staging.rename(moved)
        staging.mkdir()
        (staging / "foreign.txt").write_text("foreign", encoding="utf-8")
        foreign["path"] = staging
        raise OSError("stop")

    with pytest.raises(QueryReplicaError):
        _materialize(fixture, dependencies=_deps(copy_tree=replace_then_fail))
    assert (foreign["path"] / "foreign.txt").read_text(encoding="utf-8") == "foreign"


def test_manifest_order_and_model_completeness_are_enforced(tmp_path: Path) -> None:
    from dataclasses import replace
    from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_query_replica import QueryReplicaError

    fixture = _fixture(tmp_path)
    with pytest.raises(QueryReplicaError, match="MANIFEST_ORDER"):
        _materialize((*fixture[:5], tuple(reversed(fixture[5]))))
    incomplete = replace(fixture[5][0], files=fixture[5][0].files[1:])
    with pytest.raises(QueryReplicaError):
        _materialize((*fixture[:5], (incomplete, fixture[5][1])))


def test_model_markers_nested_below_snapshot_root_are_rejected(
    tmp_path: Path,
) -> None:
    from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_query_replica import QueryReplicaError

    fixture = _fixture(tmp_path)
    model = fixture[5][0].source_root
    nested = model / "nested"
    nested.mkdir()
    (model / "config.json").rename(nested / "config.json")
    model_manifest = _tree_manifest(
        "model", model, fixture[5][0].replica_relative_root
    )

    with pytest.raises(QueryReplicaError, match="MODEL_SNAPSHOT_INCOMPLETE"):
        _materialize((*fixture[:5], (model_manifest, fixture[5][1])))


@pytest.mark.parametrize("size", [True, 1.0])
def test_manifest_sizes_require_exact_integers(tmp_path: Path, size: object) -> None:
    from dataclasses import replace
    from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_query_replica import QueryReplicaError

    fixture = _fixture(tmp_path)
    model = fixture[5][0]
    invalid = replace(model.files[0], size=size)
    changed = replace(model, files=(invalid, *model.files[1:]))
    with pytest.raises(QueryReplicaError):
        _materialize((*fixture[:5], (changed, fixture[5][1])))


@pytest.mark.parametrize("value", [True, 1.0])
def test_query_bounds_require_exact_integers(tmp_path: Path, value: object) -> None:
    from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_query_replica import (
        QueryReplicaError,
        QueryReplicaLimits,
    )

    fixture = _fixture(tmp_path)
    limits = QueryReplicaLimits(max_files=value)
    with pytest.raises(QueryReplicaError, match="LIMIT_INVALID"):
        _materialize(fixture, limits=limits)


@pytest.mark.parametrize(
    "aliases",
    [("Alias.bin", "alias.bin"), ("café.bin", "café.bin")],
)
def test_manifest_rejects_normalized_path_aliases(
    tmp_path: Path, aliases: tuple[str, str],
) -> None:
    from dataclasses import replace
    from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_query_replica import QueryReplicaError

    fixture = _fixture(tmp_path)
    model = fixture[5][0]
    first = replace(model.files[0], relative_path=aliases[0])
    second = replace(model.files[1], relative_path=aliases[1])
    changed = replace(model, files=(first, second, *model.files[2:]))
    with pytest.raises(QueryReplicaError):
        _materialize((*fixture[:5], (changed, fixture[5][1])))


def test_public_materializer_exposes_no_dependency_injection(tmp_path: Path) -> None:
    import inspect
    from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_query_replica import (
        materialize_query_replica,
    )

    assert "dependencies" not in inspect.signature(materialize_query_replica).parameters
    fixture = _fixture(tmp_path)
    with pytest.raises(TypeError):
        materialize_query_replica(
            canonical_store=fixture[0], replica_root_proof=fixture[3],
            binding=fixture[4], manifests=fixture[5], dependencies=_deps(),
        )
