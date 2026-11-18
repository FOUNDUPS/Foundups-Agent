"""Opt-in production-shape proof for the inert Python base runtime."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_base_runtime_descriptor import (
    verify_base_runtime_generation,
)
from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_base_runtime_materializer import (
    materialize_base_runtime,
)


@pytest.mark.skipif(
    os.environ.get("REDDOG_RUN_BASE_RUNTIME_SCALE") != "1",
    reason="opt-in production-shape base-runtime proof",
)
def test_current_python_base_runtime_materializes_and_reuses_exactly(
    tmp_path: Path,
) -> None:
    source = Path(os.environ.get("REDDOG_BASE_RUNTIME_SOURCE", sys.base_prefix))
    repo = tmp_path / "repo"
    canonical = tmp_path / "canonical"
    runtime = tmp_path / "base-runtimes"
    (repo / ".git").mkdir(parents=True)
    canonical.mkdir()

    first = materialize_base_runtime(
        source_base_prefix=source, runtime_store_root=runtime,
        canonical_store=canonical, repo_roots=(repo,),
    )
    second = materialize_base_runtime(
        source_base_prefix=source, runtime_store_root=runtime,
        canonical_store=canonical, repo_roots=(repo,),
    )
    verified = verify_base_runtime_generation(
        runtime_store_root=runtime,
        generation_root=first.binding.generation_root,
        canonical_store=canonical, repo_roots=(repo,),
    )

    assert first.reused_existing_generation is False
    assert second.reused_existing_generation is True
    assert second.binding == first.binding == verified
    assert first.binding.file_count > 1_000
    assert first.binding.total_bytes > 50 * 1024 * 1024
    assert first.binding.artifact_bytes_verified_at_publication is True
    assert first.binding.native_loader_closure_verified is False
    assert first.binding.activation_eligible is False
    assert first.binding.exact_runtime_closure_verified is False
