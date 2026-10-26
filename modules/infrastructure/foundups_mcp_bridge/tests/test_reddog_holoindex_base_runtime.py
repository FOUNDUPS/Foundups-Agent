"""Adversarial tests for inert HoloIndex Python base-runtime generations."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_base_runtime_contract import (
    DESCRIPTOR_NAME,
    INVENTORY_NAME,
    BaseRuntimeLimits,
)
from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_base_runtime_descriptor import (
    BaseRuntimeDescriptorError,
    verify_base_runtime_generation,
)
from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_base_runtime_materializer import (
    BaseRuntimeMaterializationError,
    _MaterializerDependencies,
    _materialize_base_runtime_for_test,
    materialize_base_runtime,
)


LIMITS = BaseRuntimeLimits(
    max_files=50,
    max_directories=50,
    max_directory_depth=8,
    max_path_bytes=256,
    max_total_path_bytes=4096,
    max_file_bytes=1024 * 1024,
    max_total_bytes=8 * 1024 * 1024,
    max_inventory_bytes=64 * 1024,
    max_descriptor_bytes=16 * 1024,
)


def _fixture(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    repo = tmp_path / "repo"
    canonical = tmp_path / "canonical"
    source = repo / "Python312"
    runtime = tmp_path / "base-runtimes"
    (repo / ".git").mkdir(parents=True)
    canonical.mkdir()
    (source / "DLLs").mkdir(parents=True)
    (source / "Lib" / "encodings").mkdir(parents=True)
    (source / "Lib" / "site-packages").mkdir()
    (source / "tcl" / "tcl8.6").mkdir(parents=True)
    (source / "python.exe").write_bytes(b"python-executable")
    (source / "python312.dll").write_bytes(b"python-runtime-library")
    (source / "vcruntime140.dll").write_bytes(b"admitted-loader-runtime")
    (source / "DLLs" / "_hashlib.pyd").write_bytes(b"native-extension")
    (source / "Lib" / "encodings" / "__init__.py").write_bytes(b"stdlib")
    (source / "Lib" / "site-packages" / "ambient.py").write_bytes(b"excluded")
    (source / "tcl" / "tcl8.6" / "init.tcl").write_bytes(b"runtime-data")
    (source / "NEWS.txt").write_bytes(b"excluded-documentation")
    return repo, canonical, source, runtime


def _materialize(tmp_path: Path):
    repo, canonical, source, runtime = _fixture(tmp_path)
    result = materialize_base_runtime(
        source_base_prefix=source,
        runtime_store_root=runtime,
        canonical_store=canonical,
        repo_roots=(repo,),
        limits=LIMITS,
    )
    return repo, canonical, source, runtime, result


def _verify(repo: Path, canonical: Path, runtime: Path, generation: Path):
    return verify_base_runtime_generation(
        runtime_store_root=runtime,
        generation_root=generation,
        canonical_store=canonical,
        repo_roots=(repo,),
        limits=LIMITS,
    )


def test_materialization_is_exact_inert_path_free_and_runnable_shape(
    tmp_path: Path,
) -> None:
    repo, canonical, source, runtime, result = _materialize(tmp_path)
    binding = result.binding

    assert result.reused_existing_generation is False
    assert binding.generation_root.name == binding.generation_id.removeprefix("sha256:")
    assert (binding.base_prefix_root / "python.exe").is_file()
    assert (binding.base_prefix_root / "Lib" / "encodings" / "__init__.py").is_file()
    assert not (binding.base_prefix_root / "Lib" / "site-packages").exists()
    assert not (binding.base_prefix_root / "NEWS.txt").exists()
    assert binding.artifact_bytes_verified_at_publication is True
    assert binding.native_loader_closure_verified is False
    assert binding.deterministic_effects_verified is False
    assert binding.signature_verified is False
    assert binding.write_denial_verified is False
    assert binding.activation_eligible is False
    assert binding.exact_runtime_closure_verified is False
    assert _verify(repo, canonical, runtime, binding.generation_root) == binding

    descriptor = json.loads((binding.generation_root / DESCRIPTOR_NAME).read_text("ascii"))
    inventory = json.loads((binding.generation_root / INVENTORY_NAME).read_text("ascii"))
    serialized = json.dumps({"descriptor": descriptor, "inventory": inventory})
    assert str(repo) not in serialized
    assert str(runtime) not in serialized
    assert str(source) not in serialized
    assert descriptor["activation_eligible"] is False


def test_second_identical_materialization_reuses_without_copy(tmp_path: Path) -> None:
    repo, canonical, source, runtime, first = _materialize(tmp_path)

    def forbidden_copy(*_args, **_kwargs):
        raise AssertionError("copy must not run for exact reuse")

    second = _materialize_base_runtime_for_test(
        source_base_prefix=source,
        runtime_store_root=runtime,
        canonical_store=canonical,
        repo_roots=(repo,),
        limits=LIMITS,
        dependencies=_MaterializerDependencies(copy_tree=forbidden_copy),
    )

    assert second.reused_existing_generation is True
    assert second.binding == first.binding
    assert not (runtime / ".base-runtime-orphans").exists()


def test_source_change_creates_new_generation_without_mutating_old(
    tmp_path: Path,
) -> None:
    repo, canonical, source, runtime, first = _materialize(tmp_path)
    old_payload = first.binding.base_prefix_root / "Lib" / "encodings" / "__init__.py"
    old_bytes = old_payload.read_bytes()
    (source / "Lib" / "encodings" / "__init__.py").write_bytes(b"stdlib-v2")

    second = materialize_base_runtime(
        source_base_prefix=source, runtime_store_root=runtime,
        canonical_store=canonical, repo_roots=(repo,), limits=LIMITS,
    )

    assert second.binding.generation_id != first.binding.generation_id
    assert old_payload.read_bytes() == old_bytes
    assert _verify(repo, canonical, runtime, first.binding.generation_root) == first.binding


def test_published_payload_mutation_fails_reverification(tmp_path: Path) -> None:
    repo, canonical, _source, runtime, result = _materialize(tmp_path)
    target = result.binding.base_prefix_root / "python.exe"
    target.write_bytes(b"mutated")

    with pytest.raises(
        BaseRuntimeDescriptorError, match="BASE_RUNTIME_(INVENTORY_MISMATCH|PAYLOAD_DIGEST_MISMATCH)",
    ):
        _verify(repo, canonical, runtime, result.binding.generation_root)


def test_unlisted_payload_fails_reverification(tmp_path: Path) -> None:
    repo, canonical, _source, runtime, result = _materialize(tmp_path)
    (result.binding.base_prefix_root / "ambient.dll").write_bytes(b"ambient")

    with pytest.raises(BaseRuntimeDescriptorError, match="BASE_RUNTIME_INVENTORY_MISMATCH"):
        _verify(repo, canonical, runtime, result.binding.generation_root)


def test_unpublished_staging_is_verified_before_publish(tmp_path: Path) -> None:
    repo, canonical, source, runtime = _fixture(tmp_path)
    published = False

    def corrupt(staging: Path) -> None:
        (staging / "python-runtime" / "python.exe").write_bytes(b"corrupt")

    def forbidden_publish(_source: Path, _target: Path) -> None:
        nonlocal published
        published = True

    dependencies = _MaterializerDependencies(
        after_contracts=corrupt, publish_directory=forbidden_publish
    )
    with pytest.raises(BaseRuntimeMaterializationError, match="BASE_RUNTIME_"):
        _materialize_base_runtime_for_test(
            source_base_prefix=source, runtime_store_root=runtime,
            canonical_store=canonical, repo_roots=(repo,), limits=LIMITS,
            dependencies=dependencies,
        )

    assert published is False
    assert not tuple(runtime.glob(".base-runtime-stage-*"))


def test_corrupt_existing_generation_is_never_replaced(tmp_path: Path) -> None:
    repo, canonical, source, runtime, first = _materialize(tmp_path)
    (first.binding.base_prefix_root / "python.exe").write_bytes(b"corrupt")

    def forbidden_copy(*_args, **_kwargs):
        raise AssertionError("existing digest root must not be replaced")

    with pytest.raises(BaseRuntimeMaterializationError, match="BASE_RUNTIME_"):
        _materialize_base_runtime_for_test(
            source_base_prefix=source, runtime_store_root=runtime,
            canonical_store=canonical, repo_roots=(repo,), limits=LIMITS,
            dependencies=_MaterializerDependencies(copy_tree=forbidden_copy),
        )
