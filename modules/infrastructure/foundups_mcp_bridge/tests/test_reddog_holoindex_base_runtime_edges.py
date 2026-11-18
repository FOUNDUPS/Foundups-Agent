"""Path, projection, and binding falsifiers for inert base runtimes."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from modules.infrastructure.foundups_mcp_bridge.src import (
    reddog_holoindex_acceptance_windows as acceptance_windows,
)

from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_base_runtime_contract import (
    INVENTORY_NAME,
    BaseRuntimeLimits,
)
from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_base_runtime_descriptor import (
    BaseRuntimeDescriptorError,
    verify_base_runtime_generation,
)
from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_base_runtime_materializer import (
    BaseRuntimeMaterializationError,
    materialize_base_runtime,
)
from modules.infrastructure.foundups_mcp_bridge.tests.reddog_holoindex_test_fs_support import (
    create_directory_alias_or_skip,
)


LIMITS = BaseRuntimeLimits(
    max_files=50, max_directories=50, max_directory_depth=8,
    max_path_bytes=256, max_total_path_bytes=4096,
    max_file_bytes=1024 * 1024, max_total_bytes=8 * 1024 * 1024,
    max_inventory_bytes=64 * 1024, max_descriptor_bytes=16 * 1024,
)


def _fixture(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    repo = tmp_path / "repo"
    canonical = tmp_path / "canonical"
    source = repo / "Python312"
    runtime = tmp_path / "runtime"
    (repo / ".git").mkdir(parents=True)
    canonical.mkdir()
    (source / "DLLs").mkdir(parents=True)
    (source / "Lib" / "site-packages").mkdir(parents=True)
    (source / "tcl").mkdir()
    (source / "python.exe").write_bytes(b"exe")
    (source / "python312.dll").write_bytes(b"dll")
    (source / "DLLs" / "_ssl.pyd").write_bytes(b"pyd")
    (source / "Lib" / "os.py").write_bytes(b"stdlib")
    (source / "tcl" / "init.tcl").write_bytes(b"tcl")
    return repo, canonical, source, runtime


def _materialized(tmp_path: Path):
    repo, canonical, source, runtime = _fixture(tmp_path)
    result = materialize_base_runtime(
        source_base_prefix=source, runtime_store_root=runtime,
        canonical_store=canonical, repo_roots=(repo,), limits=LIMITS,
    )
    return repo, canonical, source, runtime, result


def test_missing_required_runtime_directory_fails_closed(tmp_path: Path) -> None:
    repo, canonical, source, runtime = _fixture(tmp_path)
    (source / "tcl" / "init.tcl").unlink()
    (source / "tcl").rmdir()

    with pytest.raises(
        BaseRuntimeMaterializationError, match="BASE_RUNTIME_REQUIRED_ROOT_MISSING",
    ):
        materialize_base_runtime(
            source_base_prefix=source, runtime_store_root=runtime,
            canonical_store=canonical, repo_roots=(repo,), limits=LIMITS,
        )


def test_source_directory_lease_does_not_require_delete_authority(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    observed: dict[str, int] = {}

    def open_handle(_path: Path, **kwargs: int) -> int:
        observed.update(kwargs)
        return 41

    monkeypatch.setattr(acceptance_windows, "_open_handle", open_handle)
    monkeypatch.setattr(acceptance_windows, "_require_handle_path", lambda *_a, **_k: None)
    monkeypatch.setattr(acceptance_windows, "_identity_from_handle", lambda _handle: (1, 2, 0, 0, 0))
    monkeypatch.setattr(acceptance_windows, "_close_handle", lambda _handle: None)

    lease = acceptance_windows.open_windows_directory_lease(
        tmp_path, expected_identity=(1, 2), require_delete_authority=False
    )
    lease.close()

    assert observed["desired_access"] & acceptance_windows._DELETE == 0
    assert observed["share_mode"] == acceptance_windows._FILE_SHARE_READ


def test_missing_required_runtime_role_fails_closed(tmp_path: Path) -> None:
    repo, canonical, source, runtime = _fixture(tmp_path)
    (source / "DLLs" / "_ssl.pyd").unlink()

    with pytest.raises(
        BaseRuntimeMaterializationError, match="BASE_RUNTIME_ROLE_COVERAGE_INVALID",
    ):
        materialize_base_runtime(
            source_base_prefix=source, runtime_store_root=runtime,
            canonical_store=canonical, repo_roots=(repo,), limits=LIMITS,
        )


def test_wrong_expected_generation_fails_before_payload_admission(tmp_path: Path) -> None:
    repo, canonical, _source, runtime, result = _materialized(tmp_path)

    with pytest.raises(
        BaseRuntimeDescriptorError, match="BASE_RUNTIME_DESCRIPTOR_BINDING_INVALID",
    ):
        verify_base_runtime_generation(
            runtime_store_root=runtime,
            generation_root=result.binding.generation_root,
            expected_generation_id="sha256:" + ("f" * 64),
            canonical_store=canonical, repo_roots=(repo,), limits=LIMITS,
        )


def test_generation_root_alias_is_rejected(tmp_path: Path) -> None:
    repo, canonical, _source, runtime, result = _materialized(tmp_path)
    target = result.binding.generation_root
    real = runtime / ".preserved-real-generation"
    os.rename(target, real)
    create_directory_alias_or_skip(target, real)

    with pytest.raises((BaseRuntimeDescriptorError, ValueError)):
        verify_base_runtime_generation(
            runtime_store_root=runtime, generation_root=target,
            expected_generation_id=result.binding.generation_id,
            canonical_store=canonical, repo_roots=(repo,), limits=LIMITS,
        )


def test_runtime_store_alias_is_rejected(tmp_path: Path) -> None:
    repo, canonical, source, runtime, _result = _materialized(tmp_path)
    linked = tmp_path / "linked-runtime"
    create_directory_alias_or_skip(linked, runtime)

    with pytest.raises(BaseRuntimeMaterializationError):
        materialize_base_runtime(
            source_base_prefix=source, runtime_store_root=linked,
            canonical_store=canonical, repo_roots=(repo,), limits=LIMITS,
        )


def test_path_budget_applies_to_projected_tree(tmp_path: Path) -> None:
    repo, canonical, source, runtime = _fixture(tmp_path)
    for index in range(4):
        (source / "Lib" / f"long_standard_library_name_{index}.py").write_bytes(b"x")
    bounded = BaseRuntimeLimits(
        max_files=50, max_directories=50, max_directory_depth=8,
        max_path_bytes=256, max_total_path_bytes=90,
        max_file_bytes=1024, max_total_bytes=4096,
        max_inventory_bytes=64 * 1024, max_descriptor_bytes=16 * 1024,
    )

    with pytest.raises(
        BaseRuntimeMaterializationError,
        match="DEPENDENCY_RUNTIME_SOURCE_TOTAL_PATH_BOUND",
    ):
        materialize_base_runtime(
            source_base_prefix=source, runtime_store_root=runtime,
            canonical_store=canonical, repo_roots=(repo,), limits=bounded,
        )


def test_inventory_tampering_fails_canonical_binding(tmp_path: Path) -> None:
    repo, canonical, _source, runtime, result = _materialized(tmp_path)
    inventory = result.binding.generation_root / INVENTORY_NAME
    inventory.write_bytes(inventory.read_bytes().replace(b"python.exe", b"pythonw.exe"))

    with pytest.raises(BaseRuntimeDescriptorError, match="BASE_RUNTIME_"):
        verify_base_runtime_generation(
            runtime_store_root=runtime,
            generation_root=result.binding.generation_root,
            canonical_store=canonical, repo_roots=(repo,), limits=LIMITS,
        )


@pytest.mark.skipif(os.name != "nt", reason="Windows alternate data streams")
def test_published_payload_ads_is_rejected(tmp_path: Path) -> None:
    repo, canonical, _source, runtime, result = _materialized(tmp_path)
    target = result.binding.base_prefix_root / "python.exe"
    Path(str(target) + ":reddog_audit").write_bytes(b"alternate")

    with pytest.raises(
        BaseRuntimeDescriptorError,
        match="runtime_artifact_alternate_stream_rejected",
    ):
        verify_base_runtime_generation(
            runtime_store_root=runtime,
            generation_root=result.binding.generation_root,
            canonical_store=canonical, repo_roots=(repo,), limits=LIMITS,
        )
