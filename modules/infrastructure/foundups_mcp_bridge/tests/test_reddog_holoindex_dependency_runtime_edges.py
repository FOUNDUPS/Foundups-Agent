"""Additional path and binding falsifiers for inert dependency runtimes."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from modules.infrastructure.foundups_mcp_bridge.tests.reddog_holoindex_test_fs_support import (
    create_directory_alias_or_skip,
)

from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_dependency_runtime_contract import (
    INVENTORY_NAME,
    DependencyRuntimeLimits,
)
from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_dependency_runtime_descriptor import (
    DependencyRuntimeDescriptorError,
    verify_dependency_runtime_generation,
)
from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_dependency_runtime_materializer import (
    DependencyRuntimeMaterializationError,
    materialize_dependency_runtime,
)


LIMITS = DependencyRuntimeLimits(
    max_files=20,
    max_directories=20,
    max_directory_depth=8,
    max_path_bytes=256,
    max_total_path_bytes=2048,
    max_file_bytes=1024 * 1024,
    max_total_bytes=4 * 1024 * 1024,
    max_inventory_bytes=64 * 1024,
    max_descriptor_bytes=16 * 1024,
)


def _materialized(tmp_path: Path):
    repo = tmp_path / "repo"
    canonical = tmp_path / "canonical"
    source = repo / ".venv" / "Lib" / "site-packages"
    runtime = tmp_path / "runtime"
    (repo / ".git").mkdir(parents=True)
    canonical.mkdir()
    source.mkdir(parents=True)
    (source / "payload.py").write_text("VALUE = 1\n", encoding="ascii")
    result = materialize_dependency_runtime(
        source_site_packages=source, runtime_store_root=runtime,
        canonical_store=canonical, repo_roots=(repo,), limits=LIMITS,
    )
    return repo, canonical, source, runtime, result


def test_generation_root_link_alias_is_rejected_before_content_use(
    tmp_path: Path,
) -> None:
    repo, canonical, _source, runtime, result = _materialized(tmp_path)
    target = result.binding.generation_root
    real = runtime / ".preserved-real-generation"
    os.rename(target, real)
    create_directory_alias_or_skip(target, real)

    with pytest.raises((DependencyRuntimeDescriptorError, ValueError)):
        verify_dependency_runtime_generation(
            runtime_store_root=runtime, generation_root=target,
            expected_generation_id=result.binding.generation_id,
            canonical_store=canonical, repo_roots=(repo,), limits=LIMITS,
        )


def test_wrong_expected_generation_fails_before_payload_admission(
    tmp_path: Path,
) -> None:
    repo, canonical, _source, runtime, result = _materialized(tmp_path)
    wrong = "sha256:" + ("f" * 64)

    with pytest.raises(
        DependencyRuntimeDescriptorError,
        match="DEPENDENCY_RUNTIME_DESCRIPTOR_BINDING_INVALID",
    ):
        verify_dependency_runtime_generation(
            runtime_store_root=runtime,
            generation_root=result.binding.generation_root,
            expected_generation_id=wrong, canonical_store=canonical,
            repo_roots=(repo,), limits=LIMITS,
        )


def test_runtime_store_link_is_not_resolved_into_valid_store(tmp_path: Path) -> None:
    repo, canonical, source, runtime, _result = _materialized(tmp_path)
    linked = tmp_path / "linked-runtime"
    create_directory_alias_or_skip(linked, runtime)

    with pytest.raises(DependencyRuntimeMaterializationError):
        materialize_dependency_runtime(
            source_site_packages=source, runtime_store_root=linked,
            canonical_store=canonical, repo_roots=(repo,), limits=LIMITS,
        )


def test_aggregate_path_bound_rejects_before_runtime_copy(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    canonical = tmp_path / "canonical"
    source = repo / "site-packages"
    runtime = tmp_path / "runtime"
    (repo / ".git").mkdir(parents=True)
    canonical.mkdir()
    source.mkdir()
    for index in range(4):
        (source / f"long_payload_name_{index}.py").write_text("X=1\n", encoding="ascii")
    bounded = DependencyRuntimeLimits(
        max_files=20, max_directories=20, max_directory_depth=8,
        max_path_bytes=256, max_total_path_bytes=32,
        max_file_bytes=1024, max_total_bytes=4096,
        max_inventory_bytes=64 * 1024, max_descriptor_bytes=16 * 1024,
    )

    with pytest.raises(
        DependencyRuntimeMaterializationError,
        match="DEPENDENCY_RUNTIME_SOURCE_TOTAL_PATH_BOUND",
    ):
        materialize_dependency_runtime(
            source_site_packages=source, runtime_store_root=runtime,
            canonical_store=canonical, repo_roots=(repo,), limits=bounded,
        )


@pytest.mark.skipif(os.name != "nt", reason="Windows alternate data streams")
@pytest.mark.parametrize("directory", (False, True))
def test_preexisting_source_ads_is_rejected(
    tmp_path: Path, directory: bool,
) -> None:
    repo = tmp_path / "repo"
    canonical = tmp_path / "canonical"
    source = repo / "site-packages"
    runtime = tmp_path / "runtime"
    (repo / ".git").mkdir(parents=True)
    canonical.mkdir()
    source.mkdir()
    payload = source / "payload.py"
    payload.write_text("VALUE = 1\n", encoding="ascii")
    target = source if directory else payload
    Path(str(target) + ":reddog_audit").write_bytes(b"alternate")

    with pytest.raises(
        DependencyRuntimeMaterializationError,
        match="runtime_artifact_alternate_stream_rejected",
    ):
        materialize_dependency_runtime(
            source_site_packages=source, runtime_store_root=runtime,
            canonical_store=canonical, repo_roots=(repo,), limits=LIMITS,
        )


@pytest.mark.skipif(os.name != "nt", reason="Windows alternate data streams")
@pytest.mark.parametrize("directory", (False, True))
def test_postpublication_ads_is_rejected_by_full_reverification(
    tmp_path: Path, directory: bool,
) -> None:
    repo, canonical, _source, runtime, result = _materialized(tmp_path)
    payload = result.binding.site_packages_root / "payload.py"
    target = result.binding.site_packages_root if directory else payload
    Path(str(target) + ":reddog_audit").write_bytes(b"alternate")

    with pytest.raises(
        DependencyRuntimeDescriptorError,
        match="runtime_artifact_alternate_stream_rejected",
    ):
        verify_dependency_runtime_generation(
            runtime_store_root=runtime,
            generation_root=result.binding.generation_root,
            expected_generation_id=result.binding.generation_id,
            canonical_store=canonical, repo_roots=(repo,), limits=LIMITS,
        )


@pytest.mark.skipif(os.name != "nt", reason="Windows alternate data streams")
@pytest.mark.parametrize(
    "target_name", ("generation", "descriptor", "inventory", "orphans"),
)
def test_generation_contract_ads_is_rejected(
    tmp_path: Path, target_name: str,
) -> None:
    repo, canonical, _source, runtime, result = _materialized(tmp_path)
    targets = {
        "generation": result.binding.generation_root,
        "descriptor": result.binding.descriptor_path,
        "inventory": result.binding.generation_root / INVENTORY_NAME,
        "orphans": result.binding.generation_root
        / ".dependency-runtime-publication-orphans",
    }
    Path(str(targets[target_name]) + ":reddog_audit").write_bytes(b"alternate")

    with pytest.raises(
        DependencyRuntimeDescriptorError,
        match="runtime_artifact_alternate_stream_rejected",
    ):
        verify_dependency_runtime_generation(
            runtime_store_root=runtime,
            generation_root=result.binding.generation_root,
            expected_generation_id=result.binding.generation_id,
            canonical_store=canonical, repo_roots=(repo,), limits=LIMITS,
        )
