"""Windows retained-handle scaling proof for dependency-runtime copying."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_acceptance_guards import (
    create_isolated_store,
)
from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_dependency_runtime_contract import (
    DependencyRuntimeLimits,
)
from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_dependency_runtime_copy import (
    _copy_dependency_snapshot,
    plan_dependency_runtime_snapshot,
)
from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_dependency_runtime_materializer import (
    materialize_dependency_runtime,
)
from modules.infrastructure.shared_utilities.runtime_artifact_windows_streams import (
    windows_extended_path,
)


def _windows_long_relative(source: Path) -> Path:
    """Keep the source Win32-safe while forcing the staging copy past MAX_PATH."""

    remaining = max(80, 235 - len(str(source)) - len("payload.py") - 1)
    parts: list[str] = []
    while remaining > 0:
        width = min(48, remaining)
        parts.append("d" * width)
        remaining -= width + 1
    return Path(*parts) / "payload.py"


@pytest.mark.skipif(os.name != "nt", reason="Windows retained-handle contract")
def test_windows_copy_retains_handles_by_depth_not_file_count(tmp_path: Path) -> None:
    repo, canonical = tmp_path / "repo", tmp_path / "canonical"
    source, staging = repo / "site-packages", tmp_path / "staging"
    (repo / ".git").mkdir(parents=True)
    (source / "pkg" / "nested").mkdir(parents=True)
    canonical.mkdir()
    for index in range(700):
        (source / "pkg" / "nested" / f"f{index:04d}.py").write_text(
            f"VALUE = {index}\n", encoding="ascii"
        )
    limits = DependencyRuntimeLimits(
        max_files=1000, max_directories=20, max_directory_depth=8,
        max_path_bytes=256, max_total_path_bytes=64 * 1024,
        max_file_bytes=1024 * 1024, max_total_bytes=16 * 1024 * 1024,
        max_inventory_bytes=4 * 1024 * 1024,
        max_descriptor_bytes=16 * 1024,
    )
    store = create_isolated_store(
        staging, canonical_store=canonical, repo_roots=(repo,)
    )
    plan = plan_dependency_runtime_snapshot(source, limits=limits)

    proof, peak = _copy_dependency_snapshot(
        source, staging / "site-packages", store_proof=store,
        canonical_store=canonical, repo_roots=(repo,), limits=limits,
        expected_plan=plan,
    )

    assert proof.file_count == 700
    assert proof.destination_digest == plan.generation_id
    assert peak <= 16


@pytest.mark.skipif(os.name != "nt", reason="Windows extended-length path contract")
def test_windows_copy_supports_valid_paths_beyond_max_path(tmp_path: Path) -> None:
    repo, canonical = tmp_path / "repo", tmp_path / "canonical"
    source = repo / "site-packages"
    runtime = tmp_path / "runtime"
    relative = _windows_long_relative(source)
    empty_relative = relative.parent / "empty-leaf"
    source_file = source / relative
    destination_file = runtime / ("0" * 64) / "site-packages" / relative
    (repo / ".git").mkdir(parents=True)
    canonical.mkdir()
    source_file.parent.mkdir(parents=True)
    (source / empty_relative).mkdir()
    source_file.write_text("VALUE = 1\n", encoding="ascii")
    assert len(str(source_file)) < 260
    assert len(str(destination_file)) > 260
    assert len(str(destination_file.parent)) >= 248
    limits = DependencyRuntimeLimits(
        max_files=10, max_directories=20, max_directory_depth=16,
        max_path_bytes=512, max_total_path_bytes=4096,
        max_file_bytes=1024, max_total_bytes=4096,
        max_inventory_bytes=64 * 1024, max_descriptor_bytes=16 * 1024,
    )
    first = materialize_dependency_runtime(
        source_site_packages=source, runtime_store_root=runtime,
        canonical_store=canonical, repo_roots=(repo,), limits=limits,
    )
    second = materialize_dependency_runtime(
        source_site_packages=source, runtime_store_root=runtime,
        canonical_store=canonical, repo_roots=(repo,), limits=limits,
    )

    assert os.path.isfile(
        windows_extended_path(first.binding.site_packages_root / relative)
    )
    assert os.path.isdir(
        windows_extended_path(first.binding.site_packages_root / empty_relative)
    )
    assert second.reused_existing_generation is True
    assert second.binding == first.binding
