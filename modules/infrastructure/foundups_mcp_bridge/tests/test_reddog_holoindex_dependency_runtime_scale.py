"""Opt-in production-shape soak for the dependency-runtime materializer."""

from __future__ import annotations

import json
import os
import threading
import time
from pathlib import Path

import pytest

from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_dependency_runtime_contract import (
    DependencyRuntimeLimits,
)
from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_dependency_runtime_materializer import (
    materialize_dependency_runtime,
)


pytestmark = pytest.mark.skipif(
    os.environ.get("REDDOG_RUN_DEPENDENCY_RUNTIME_SCALE_SOAK") != "1",
    reason="explicit production-shape soak only",
)


def _build_tree(root: Path, *, files: int, directories: int) -> None:
    root.mkdir(parents=True)
    targets = []
    for index in range(directories):
        target = root / f"d{index:05d}"
        target.mkdir()
        targets.append(target)
    for index in range(files):
        (targets[index % directories] / f"f{index:05d}.py").write_bytes(b"")


def _sample_process(stop, samples, process) -> None:
    while not stop.wait(0.01):
        samples.append((process.num_handles(), process.memory_info().rss))


def _exercise_materializer(
    repo: Path, canonical: Path, source: Path, runtime: Path,
) -> dict[str, object]:
    limits = DependencyRuntimeLimits()
    psutil = pytest.importorskip("psutil")
    process = psutil.Process(os.getpid())
    baseline_handles = process.num_handles()
    baseline_rss = process.memory_info().rss
    samples: list[tuple[int, int]] = []
    stop = threading.Event()
    monitor = threading.Thread(
        target=_sample_process, args=(stop, samples, process), daemon=True
    )
    monitor.start()
    started = time.monotonic()
    try:
        first = materialize_dependency_runtime(
            source_site_packages=source, runtime_store_root=runtime,
            canonical_store=canonical, repo_roots=(repo,), limits=limits,
        )
    finally:
        stop.set()
        monitor.join(timeout=5.0)
    first_elapsed = time.monotonic() - started
    generation_count = len(tuple(
        entry for entry in runtime.iterdir()
        if entry.is_dir() and not entry.name.startswith(".")
    ))
    second_started = time.monotonic()
    second = materialize_dependency_runtime(
        source_site_packages=source, runtime_store_root=runtime,
        canonical_store=canonical, repo_roots=(repo,), limits=limits,
    )
    second_elapsed = time.monotonic() - second_started
    return {
        "first": first, "second": second,
        "generation_count": generation_count,
        "first_elapsed": first_elapsed, "second_elapsed": second_elapsed,
        "peak_handle_delta": max(row[0] for row in samples) - baseline_handles,
        "peak_rss_delta": max(row[1] for row in samples) - baseline_rss,
    }


def test_actual_file_and_directory_shape_has_bounded_resources(tmp_path: Path) -> None:
    repo, canonical = tmp_path / "repo", tmp_path / "canonical"
    source, runtime = repo / "site-packages", tmp_path / "runtime"
    (repo / ".git").mkdir(parents=True)
    canonical.mkdir()
    _build_tree(source, files=72_261, directories=11_639)
    evidence = _exercise_materializer(repo, canonical, source, runtime)
    first, second = evidence["first"], evidence["second"]

    assert first.binding.file_count == 72_261
    assert first.binding.directory_count == 11_639
    assert second.reused_existing_generation is True
    assert second.binding == first.binding
    assert evidence["generation_count"] == 1
    assert not (runtime / ".dependency-runtime-orphans").exists()
    assert evidence["peak_handle_delta"] < 128
    assert evidence["peak_rss_delta"] < 768 * 1024 * 1024
    assert evidence["first_elapsed"] < 30 * 60
    assert evidence["second_elapsed"] < evidence["first_elapsed"]
    print("DEPENDENCY_RUNTIME_SCALE_EVIDENCE=" + json.dumps({
        "file_count": first.binding.file_count,
        "directory_count": first.binding.directory_count,
        "generation_id": first.binding.generation_id,
        "first_elapsed_seconds": round(evidence["first_elapsed"], 3),
        "reuse_elapsed_seconds": round(evidence["second_elapsed"], 3),
        "peak_handle_delta": evidence["peak_handle_delta"],
        "peak_rss_delta_bytes": evidence["peak_rss_delta"],
    }, sort_keys=True, separators=(",", ":")))
