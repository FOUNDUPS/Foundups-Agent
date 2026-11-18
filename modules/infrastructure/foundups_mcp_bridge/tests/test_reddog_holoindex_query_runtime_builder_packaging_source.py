"""Falsification tests for retained-wheel inert packaging-source generations."""

from __future__ import annotations

import base64
import concurrent.futures
import csv
from dataclasses import fields, replace
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import stat
import tempfile
import zipfile

import pytest

from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_query_replica_generation import (
    QueryReplicaGenerationError,
)
from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_query_runtime_builder_packaging_source_contract import (
    BUILDER_PACKAGING_SOURCE_DESCRIPTOR_NAME,
    BUILDER_PACKAGING_SOURCE_INVENTORY_NAME,
    BUILDER_PACKAGING_SOURCE_SITE_PACKAGES_DIRECTORY,
    BUILDER_PACKAGING_SOURCE_WHEEL_DIRECTORY,
    BuilderPackagingSourceLimits,
    canonical_json_bytes,
    derive_builder_packaging_source_generation_id,
    validate_builder_packaging_source_descriptor,
)
from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_query_runtime_builder_packaging_source_materializer import (
    BuilderPackagingSourceMaterializationError,
    _BuilderPackagingSourceDependencies,
    _materialize_builder_packaging_source_bytes_for_test,
    materialize_pinned_builder_packaging_source,
)
from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_query_runtime_builder_packaging_source_verifier import (
    BuilderPackagingSourceVerificationError,
    verify_builder_packaging_source_generation,
)
from modules.infrastructure.foundups_mcp_bridge.src import (
    reddog_holoindex_query_runtime_builder_packaging_wheel as wheel_module,
)


_FILENAME = "packaging-26.0-py3-none-any.whl"
_DIST_INFO = "packaging-26.0.dist-info"
_FALSE_CLAIMS = (
    "official_provenance_authenticated", "signature_verified",
    "network_performed", "download_performed", "installation_performed",
    "import_authority_verified", "child_execution_authorized",
    "builder_runtime_authenticated", "preimport_loader_authority_verified",
    "native_loader_closure_verified", "subprocess_closure_verified",
    "exact_runtime_closure_verified", "deterministic_effects_verified",
    "write_denial_verified", "activation_eligible", "a_grade_verified",
    "retrieval_rsi_verified",
)


def _record_hash(payload: bytes) -> str:
    digest = base64.urlsafe_b64encode(hashlib.sha256(payload).digest())
    return "sha256=" + digest.decode("ascii").rstrip("=")


def _record(files: list[tuple[str, bytes]]) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    for name, payload in files:
        writer.writerow((name, _record_hash(payload), len(payload)))
    writer.writerow((f"{_DIST_INFO}/RECORD", "", ""))
    return output.getvalue().encode("utf-8")


def _members() -> list[tuple[str, bytes]]:
    files = [
        ("packaging/__init__.py", b'__version__ = "26.0"\n'),
        ("packaging/version.py", b"class Version: pass\n"),
        (f"{_DIST_INFO}/METADATA", b"Name: packaging\nVersion: 26.0\n"),
        (f"{_DIST_INFO}/WHEEL", (
            b"Wheel-Version: 1.0\nRoot-Is-Purelib: true\nTag: py3-none-any\n"
        )),
    ]
    return [*files, (f"{_DIST_INFO}/RECORD", _record(files))]


def _wheel_bytes(members: list[tuple[str, bytes]] | None = None) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, payload in members or _members():
            info = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = (stat.S_IFREG | 0o644) << 16
            archive.writestr(info, payload)
    return output.getvalue()


@pytest.fixture
def o_root():
    parent = Path("O:/tmp").resolve()
    parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="reddog-source-", dir=parent) as raw:
        root = Path(raw).resolve()
        assert root.parent == parent and root.drive.upper() == "O:"
        yield root


def _layout(root: Path) -> tuple[Path, Path, Path, Path, bytes]:
    repo, canonical = root / "repo", root / "canonical"
    wheel_root, source_store = root / "wheel", root / "source-store"
    (repo / ".git").mkdir(parents=True)
    canonical.mkdir()
    wheel_root.mkdir()
    payload = _wheel_bytes()
    (wheel_root / _FILENAME).write_bytes(payload)
    return repo, canonical, wheel_root, source_store, payload


def _pin_synthetic(monkeypatch, payload: bytes) -> None:
    monkeypatch.setattr(wheel_module, "PACKAGING_26_WHEEL_SIZE", len(payload))
    monkeypatch.setattr(
        wheel_module, "PACKAGING_26_WHEEL_SHA256", hashlib.sha256(payload).hexdigest(),
    )


def _public(root: Path, monkeypatch):
    repo, canonical, wheel_root, source_store, payload = _layout(root)
    _pin_synthetic(monkeypatch, payload)
    result = materialize_pinned_builder_packaging_source(
        wheel_path=wheel_root / _FILENAME, wheel_store_root=wheel_root,
        source_store_root=source_store, canonical_store=canonical,
        repo_roots=(repo,),
    )
    return repo, canonical, wheel_root, source_store, payload, result


def _verify(repo: Path, canonical: Path, source_store: Path, generation: Path):
    return verify_builder_packaging_source_generation(
        source_store_root=source_store, generation_root=generation,
        canonical_store=canonical, repo_roots=(repo,),
    )


def _descriptor(result) -> dict[str, object]:
    return json.loads(result.binding.descriptor_path.read_text("ascii"))


def test_generation_id_binds_wheel_identity_even_for_same_tree() -> None:
    baseline = dict(
        wheel_filename=_FILENAME, wheel_size=10, wheel_sha256="sha256:" + "1" * 64,
        central_directory_digest="sha256:" + "2" * 64,
        member_set_digest="sha256:" + "3" * 64,
        metadata_digest="sha256:" + "4" * 64,
        wheel_metadata_digest="sha256:" + "5" * 64,
        record_digest="sha256:" + "6" * 64,
        owned_files_digest="sha256:" + "7" * 64,
        dependency_tree_digest_value="sha256:" + "8" * 64,
        member_count=2, directory_count=1, expanded_bytes=20,
    )
    first = derive_builder_packaging_source_generation_id(**baseline)
    baseline["central_directory_digest"] = "sha256:" + "9" * 64
    second = derive_builder_packaging_source_generation_id(**baseline)
    assert first != second


def test_materialization_persists_exact_wheel_and_tree_without_authority(
    o_root: Path, monkeypatch,
) -> None:
    repo, canonical, _wheel_root, source_store, payload, result = _public(
        o_root, monkeypatch,
    )
    binding = result.binding
    descriptor = _descriptor(result)
    assert result.reused_existing_generation is False
    assert binding.generation_root.name == binding.generation_id.removeprefix("sha256:")
    assert binding.wheel_path.read_bytes() == payload
    assert (binding.site_packages_root / "packaging/version.py").read_bytes() == b"class Version: pass\n"
    assert descriptor["reviewed_pin_match"] is True
    assert descriptor["source_lease_held_through_publication"] is False
    assert descriptor["extraction_performed"] is True
    assert descriptor["source_materialization_performed"] is True
    assert all(descriptor[name] is False for name in _FALSE_CLAIMS)
    public = binding.public_binding
    identity = ("descriptor_digest", "generation_id", "inventory_digest", "wheel_sha256", "member_set_digest", "dependency_tree_digest", "member_count", "directory_count", "expanded_bytes")
    truths = ("strict_archive_verified", "record_ownership_verified", "source_only_topology_verified", "source_materialization_performed", "extraction_performed", "publication_performed", "wheel_to_tree_verified", "artifact_bytes_verified_at_publication")
    authority = (
        "reviewed_pin_match", "source_lease_held_through_publication",
        "source_lease_held_through_current_verification",
    )
    expected = {f"builder_packaging_source_{name}" for name in (*identity, *truths, *authority, *_FALSE_CLAIMS)}
    assert set(public) == expected
    assert all(public[f"builder_packaging_source_{name}"] is True for name in truths + authority)
    assert all(public[f"builder_packaging_source_{name}"] is False for name in _FALSE_CLAIMS)
    assert all("path" not in str(key).casefold() and not isinstance(value, Path) for key, value in public.items())
    durable = _verify(repo, canonical, source_store, binding.generation_root)
    assert durable == replace(
        binding, source_lease_held_through_publication=False,
        source_lease_held_through_current_verification=False,
    )


def test_synthetic_byte_seam_claims_neither_pin_nor_lease(o_root: Path) -> None:
    repo, canonical, _wheel_root, source_store, payload = _layout(o_root)
    result = _materialize_builder_packaging_source_bytes_for_test(
        wheel_bytes=payload, source_store_root=source_store,
        canonical_store=canonical, repo_roots=(repo,),
    )
    descriptor = _descriptor(result)
    assert descriptor["reviewed_pin_match"] is False
    assert descriptor["source_lease_held_through_publication"] is False
    with pytest.raises(BuilderPackagingSourceVerificationError, match="AUTHORITY_REQUIRED"):
        _verify(repo, canonical, source_store, result.binding.generation_root)


def test_unsigned_descriptor_cannot_launder_live_source_authority(
    o_root: Path, monkeypatch,
) -> None:
    repo, canonical, wheel_root, source_store, payload = _layout(o_root)
    _pin_synthetic(monkeypatch, payload)
    private = _materialize_builder_packaging_source_bytes_for_test(
        wheel_bytes=payload, source_store_root=source_store,
        canonical_store=canonical, repo_roots=(repo,),
    )
    descriptor = _descriptor(private)
    descriptor["reviewed_pin_match"] = True
    descriptor["source_lease_held_through_publication"] = True
    private.binding.descriptor_path.write_bytes(canonical_json_bytes(descriptor))

    durable = _verify(repo, canonical, source_store, private.binding.generation_root)
    assert durable.reviewed_pin_match is True
    assert durable.source_lease_held_through_publication is False
    assert durable.source_lease_held_through_current_verification is False

    reused = materialize_pinned_builder_packaging_source(
        wheel_path=wheel_root / _FILENAME, wheel_store_root=wheel_root,
        source_store_root=source_store, canonical_store=canonical,
        repo_roots=(repo,),
    )
    assert reused.reused_existing_generation is True
    assert reused.binding.source_lease_held_through_publication is False
    assert reused.binding.source_lease_held_through_current_verification is True


def test_exact_reuse_never_writes_or_publishes(o_root: Path) -> None:
    repo, canonical, _wheel_root, source_store, payload = _layout(o_root)
    first = _materialize_builder_packaging_source_bytes_for_test(
        wheel_bytes=payload, source_store_root=source_store,
        canonical_store=canonical, repo_roots=(repo,),
    )
    descriptor_before = first.binding.descriptor_path.read_bytes()

    def forbidden(*_args, **_kwargs):
        raise AssertionError("reuse must not write or publish")

    second = _materialize_builder_packaging_source_bytes_for_test(
        wheel_bytes=payload, source_store_root=source_store,
        canonical_store=canonical, repo_roots=(repo,),
        dependencies=_BuilderPackagingSourceDependencies(
            write_source=forbidden, publish_directory=forbidden,
        ),
    )
    assert second.reused_existing_generation is True
    assert second.binding == first.binding
    assert second.binding.descriptor_path.read_bytes() == descriptor_before


@pytest.mark.parametrize(
    "target", ["descriptor", "inventory", "wheel", "member", "extra_file", "extra_directory"],
)
def test_any_persisted_tree_mutation_fails_full_reproof(
    o_root: Path, monkeypatch, target: str,
) -> None:
    repo, canonical, _wheel_root, source_store, _payload, result = _public(
        o_root, monkeypatch,
    )
    if target == "descriptor":
        result.binding.descriptor_path.write_bytes(b"{}\n")
    elif target == "inventory":
        (result.binding.generation_root / BUILDER_PACKAGING_SOURCE_INVENTORY_NAME).write_bytes(b"{}\n")
    elif target == "wheel":
        result.binding.wheel_path.write_bytes(b"corrupt")
    elif target == "member":
        (result.binding.site_packages_root / "packaging/version.py").write_bytes(b"corrupt")
    elif target == "extra_file":
        (result.binding.site_packages_root / "ambient.py").write_bytes(b"ambient")
    else:
        (result.binding.site_packages_root / "empty-ambient").mkdir()
    with pytest.raises(BuilderPackagingSourceVerificationError):
        _verify(repo, canonical, source_store, result.binding.generation_root)


def test_duplicate_key_and_nonclaim_escalation_reject(o_root: Path, monkeypatch) -> None:
    repo, canonical, _wheel_root, source_store, _payload, result = _public(
        o_root, monkeypatch,
    )
    descriptor_path = result.binding.descriptor_path
    original = descriptor_path.read_text("ascii")
    descriptor_path.write_text(
        original.replace("{", '{"status":"INERT_SOURCE",', 1), encoding="ascii",
    )
    with pytest.raises(BuilderPackagingSourceVerificationError, match="DUPLICATE_KEY"):
        _verify(repo, canonical, source_store, result.binding.generation_root)

    descriptor_path.write_text(original, encoding="ascii")
    value = json.loads(original)
    value["activation_eligible"] = True
    descriptor_path.write_bytes(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode("ascii") + b"\n"
    )
    with pytest.raises(BuilderPackagingSourceVerificationError, match="TRUTH_INVALID"):
        _verify(repo, canonical, source_store, result.binding.generation_root)


def test_prepublication_corruption_quarantines_only_staging(o_root: Path) -> None:
    repo, canonical, _wheel_root, source_store, payload = _layout(o_root)

    def corrupt(staging: Path) -> None:
        (staging / BUILDER_PACKAGING_SOURCE_SITE_PACKAGES_DIRECTORY / "packaging/version.py").write_bytes(b"bad")

    with pytest.raises(BuilderPackagingSourceMaterializationError):
        _materialize_builder_packaging_source_bytes_for_test(
            wheel_bytes=payload, source_store_root=source_store,
            canonical_store=canonical, repo_roots=(repo,),
            dependencies=_BuilderPackagingSourceDependencies(after_contracts=corrupt),
        )
    visible = tuple(path for path in source_store.iterdir() if not path.name.startswith("."))
    assert visible == ()
    assert len(tuple((source_store / ".builder-packaging-source-orphans").iterdir())) == 1


def test_postpublication_corruption_quarantines_owned_generation(o_root: Path) -> None:
    repo, canonical, _wheel_root, source_store, payload = _layout(o_root)

    def corrupt(target: Path) -> None:
        (target / BUILDER_PACKAGING_SOURCE_SITE_PACKAGES_DIRECTORY / "packaging/version.py").write_bytes(b"bad")

    with pytest.raises(BuilderPackagingSourceMaterializationError):
        _materialize_builder_packaging_source_bytes_for_test(
            wheel_bytes=payload, source_store_root=source_store,
            canonical_store=canonical, repo_roots=(repo,),
            dependencies=_BuilderPackagingSourceDependencies(after_publish=corrupt),
        )
    assert not tuple(path for path in source_store.iterdir() if not path.name.startswith("."))
    assert len(tuple((source_store / ".builder-packaging-source-orphans").iterdir())) == 1


@pytest.mark.parametrize("corrupt_winner", [False, True])
def test_no_replace_winner_is_verified_and_never_overwritten(
    o_root: Path, corrupt_winner: bool,
) -> None:
    repo, canonical, _wheel_root, source_store, payload = _layout(o_root)

    def competing_winner(staging: Path, target: Path) -> None:
        shutil.copytree(staging, target)
        if corrupt_winner:
            (target / BUILDER_PACKAGING_SOURCE_SITE_PACKAGES_DIRECTORY / "packaging/version.py").write_bytes(b"bad")
        raise QueryReplicaGenerationError("QUERY_REPLICA_GENERATION_EXISTS")

    if corrupt_winner:
        with pytest.raises(BuilderPackagingSourceMaterializationError):
            _materialize_builder_packaging_source_bytes_for_test(
                wheel_bytes=payload, source_store_root=source_store,
                canonical_store=canonical, repo_roots=(repo,),
                dependencies=_BuilderPackagingSourceDependencies(
                    publish_directory=competing_winner,
                ),
            )
        winner = tuple(path for path in source_store.iterdir() if not path.name.startswith("."))
        assert len(winner) == 1 and winner[0].is_dir()
    else:
        result = _materialize_builder_packaging_source_bytes_for_test(
            wheel_bytes=payload, source_store_root=source_store,
            canonical_store=canonical, repo_roots=(repo,),
            dependencies=_BuilderPackagingSourceDependencies(
                publish_directory=competing_winner,
            ),
        )
        assert result.reused_existing_generation is True


def test_same_store_concurrent_calls_converge_without_orphans(
    o_root: Path, monkeypatch,
) -> None:
    repo, canonical, wheel_root, source_store, payload = _layout(o_root)
    _pin_synthetic(monkeypatch, payload)

    def one_call():
        return materialize_pinned_builder_packaging_source(
            wheel_path=wheel_root / _FILENAME, wheel_store_root=wheel_root,
            source_store_root=source_store, canonical_store=canonical,
            repo_roots=(repo,),
        )

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        results = tuple(pool.map(lambda _index: one_call(), range(2)))
    assert sorted(result.reused_existing_generation for result in results) == [False, True]
    bindings = tuple(
        replace(result.binding, source_lease_held_through_publication=False)
        for result in results
    )
    assert bindings[0] == bindings[1]
    assert len(tuple(source_store.iterdir())) == 1


def test_retained_wheel_lease_spans_writer_and_publication(
    o_root: Path, monkeypatch,
) -> None:
    repo, canonical, wheel_root, source_store, payload = _layout(o_root)
    _pin_synthetic(monkeypatch, payload)
    attempts: list[str] = []

    def attempt(label: str) -> None:
        attempts.append(label)
        with pytest.raises(PermissionError):
            (wheel_root / _FILENAME).write_bytes(payload)

    with wheel_module._retain_pinned_builder_packaging_wheel(
        wheel_path=wheel_root / _FILENAME, wheel_store_root=wheel_root,
    ) as retained:
        dependencies = _BuilderPackagingSourceDependencies(
            after_contracts=lambda _path: attempt("contracts"),
            after_publish=lambda _path: attempt("publish"),
        )
        from modules.infrastructure.foundups_mcp_bridge.src import (
            reddog_holoindex_query_runtime_builder_packaging_source_materializer as module,
        )
        result = module._stable_materialize(
            payload=retained.payload, source_store_root=source_store,
            canonical_store=canonical, repo_roots=(repo,),
            limits=BuilderPackagingSourceLimits(), dependencies=dependencies,
            reviewed_pin_match=True, source_lease_held=True,
            source_reproof=retained.reprove_and_admit,
        )
    assert attempts == ["contracts", "publish"]
    assert result.binding.generation_root.is_dir()


def test_limits_reject_bool_zero_and_over_ceiling_before_store_mutation(
    o_root: Path,
) -> None:
    repo, canonical, _wheel_root, source_store, payload = _layout(o_root)
    baseline = BuilderPackagingSourceLimits()
    invalid = [replace(baseline, **{field.name: True}) for field in fields(baseline)]
    invalid.extend((replace(baseline, max_files=0), replace(baseline, max_files=129)))
    for limits in invalid:
        with pytest.raises(BuilderPackagingSourceMaterializationError, match="LIMIT_INVALID"):
            _materialize_builder_packaging_source_bytes_for_test(
                wheel_bytes=payload, source_store_root=source_store,
                canonical_store=canonical, repo_roots=(repo,), limits=limits,
            )
        assert not source_store.exists()


def test_store_inside_repo_is_rejected(o_root: Path) -> None:
    repo, canonical, _wheel_root, _source_store, payload = _layout(o_root)
    with pytest.raises(BuilderPackagingSourceMaterializationError):
        _materialize_builder_packaging_source_bytes_for_test(
            wheel_bytes=payload, source_store_root=repo / "source-store",
            canonical_store=canonical, repo_roots=(repo,),
        )


def test_token_injection_fails_before_staging_creation(o_root: Path) -> None:
    repo, canonical, _wheel_root, source_store, payload = _layout(o_root)
    with pytest.raises(BuilderPackagingSourceMaterializationError, match="TOKEN_INVALID"):
        _materialize_builder_packaging_source_bytes_for_test(
            wheel_bytes=payload, source_store_root=source_store,
            canonical_store=canonical, repo_roots=(repo,),
            dependencies=_BuilderPackagingSourceDependencies(token=lambda: "../escape"),
        )
    assert not source_store.exists()


def test_quarantine_failure_preserves_primary_as_cause(
    o_root: Path, monkeypatch,
) -> None:
    repo, canonical, _wheel_root, source_store, payload = _layout(o_root)
    from modules.infrastructure.foundups_mcp_bridge.src import (
        reddog_holoindex_query_runtime_builder_packaging_source_materializer as module,
    )
    monkeypatch.setattr(module, "quarantine_owned_staging", lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("fail")))

    def corrupt(staging: Path) -> None:
        (staging / BUILDER_PACKAGING_SOURCE_SITE_PACKAGES_DIRECTORY / "packaging/version.py").write_bytes(b"bad")

    with pytest.raises(BuilderPackagingSourceMaterializationError, match="QUARANTINE_FAILED") as captured:
        _materialize_builder_packaging_source_bytes_for_test(
            wheel_bytes=payload, source_store_root=source_store,
            canonical_store=canonical, repo_roots=(repo,),
            dependencies=_BuilderPackagingSourceDependencies(after_contracts=corrupt),
        )
    assert "MISMATCH" in str(captured.value.__cause__)


@pytest.mark.skipif(os.name != "nt", reason="Windows alternate data streams")
def test_member_ads_and_hardlink_fail_reverification(o_root: Path, monkeypatch) -> None:
    repo, canonical, _wheel_root, source_store, _payload, result = _public(
        o_root, monkeypatch,
    )
    member = result.binding.site_packages_root / "packaging/version.py"
    Path(str(member) + ":hidden").write_bytes(b"hidden")
    with pytest.raises(BuilderPackagingSourceVerificationError):
        _verify(repo, canonical, source_store, result.binding.generation_root)

    Path(str(member) + ":hidden").unlink()
    alias = result.binding.site_packages_root / "alias.py"
    os.link(member, alias)
    with pytest.raises(BuilderPackagingSourceVerificationError):
        _verify(repo, canonical, source_store, result.binding.generation_root)


def test_descriptor_validator_rejects_extra_and_missing_keys(o_root: Path, monkeypatch) -> None:
    _repo, _canonical, _wheel_root, _source_store, _payload, result = _public(
        o_root, monkeypatch,
    )
    descriptor = _descriptor(result)
    descriptor["attacker"] = True
    with pytest.raises(Exception, match="DESCRIPTOR_INVALID"):
        validate_builder_packaging_source_descriptor(descriptor)
    descriptor.pop("attacker")
    descriptor.pop("generation_id")
    with pytest.raises(Exception, match="DESCRIPTOR_INVALID"):
        validate_builder_packaging_source_descriptor(descriptor)


def test_contract_filenames_are_fixed_and_generation_has_no_dependency_runtime(
    o_root: Path, monkeypatch,
) -> None:
    _repo, _canonical, _wheel_root, _source_store, _payload, result = _public(
        o_root, monkeypatch,
    )
    root = result.binding.generation_root
    assert (root / BUILDER_PACKAGING_SOURCE_DESCRIPTOR_NAME).is_file()
    assert (root / BUILDER_PACKAGING_SOURCE_INVENTORY_NAME).is_file()
    assert (root / BUILDER_PACKAGING_SOURCE_WHEEL_DIRECTORY / _FILENAME).is_file()
    assert not (root / "dependency-runtime").exists()
