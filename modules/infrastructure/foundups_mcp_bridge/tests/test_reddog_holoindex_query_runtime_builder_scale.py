"""Opt-in upper-shape resource soak for the inert builder proof algorithms."""

from __future__ import annotations

import base64
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
import threading
import time

import pytest

from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_dependency_runtime_contract import (
    digest_bytes,
    validate_inventory,
)
from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_query_runtime_builder_contract import (
    _packaging_authority_capability,
    _process_authority_capability,
    _source_authority_capability,
    builder_authority_receipt,
)
from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_query_runtime_builder_git import (
    PinnedGitAuthority,
    _committed_file_rows,
)
from modules.infrastructure.foundups_mcp_bridge.src import (
    reddog_holoindex_query_runtime_builder_git as builder_git_module,
)
from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_query_runtime_builder_packaging import (
    _parse_record,
    _record_ownership_index,
)
from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_query_runtime_builder_source import (
    QueryRuntimeBuilderSourceError,
    _observed_source_rows,
)


pytestmark = pytest.mark.skipif(
    os.environ.get("REDDOG_RUN_BUILDER_SCALE") != "1",
    reason="set REDDOG_RUN_BUILDER_SCALE=1 for the upper-shape builder soak",
)

_PACKAGING_ROWS = 72_261
_SOURCE_ROWS = 1_500


def _d(char: str) -> str:
    return "sha256:" + char * 64


def _record_hash(payload: bytes) -> str:
    encoded = base64.urlsafe_b64encode(hashlib.sha256(payload).digest())
    return encoded.rstrip(b"=").decode("ascii")


def _record_bytes(paths: tuple[str, ...], record_path: str) -> bytes:
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, lineterminator="\n")
    empty_hash = _record_hash(b"")
    for path in paths:
        writer.writerow((path, "", "") if path == record_path else (
            path, f"sha256={empty_hash}", 0,
        ))
    return buffer.getvalue().encode("utf-8")


def _exercise_packaging_rows(count: int) -> tuple[int, int]:
    record_path = "packaging-26.0.dist-info/RECORD"
    paths = tuple(sorted((
        *(f"packaging/f{index:05d}.py" for index in range(count - 1)),
        record_path,
    ), key=str.casefold))
    record = _record_bytes(paths, record_path)
    empty_digest = digest_bytes(b"")
    rows = [{
        "path": path,
        "size": len(record) if path == record_path else 0,
        "sha256": digest_bytes(record) if path == record_path else empty_digest,
        "role": "dependency_payload",
    } for path in paths]
    inventory = validate_inventory({
        "schema_version": "holoindex_dependency_payload_inventory.v1",
        "directories": ["packaging", "packaging-26.0.dist-info"],
        "files": rows,
    })
    parsed = _parse_record(record, record_path)
    expected = tuple((row["path"], row["size"], row["sha256"]) for row in inventory["files"])
    assert parsed == expected
    assert len(_record_ownership_index(expected, parsed)) == count
    return len(parsed), len(record)


def _source_fixture(root: Path, count: int):
    origins, expected, committed = {}, {}, []
    for index in range(count):
        relative = f"builder_sources/s{index:04d}.py"
        payload = f"VALUE = {index:04d}\n".encode("ascii")
        target = root.joinpath(*relative.split("/"))
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
        origins[relative] = f"scale.s{index:04d}"
        expected[relative] = hashlib.sha256(payload).hexdigest()
        committed.append((relative, len(payload), digest_bytes(payload)))
    git = PinnedGitAuthority(
        root, "a" * 40, _d("e"), _d("f"),
        frozenset(origins), tuple(committed),
    )
    return origins, expected, git


def _exercise_git_batch(count: int, monkeypatch) -> tuple[int, int]:
    paths = tuple(f"builder_sources/s{index:04d}.py" for index in range(count))
    payloads = {path: f"VALUE = {index:04d}\n".encode("ascii") for index, path in enumerate(paths)}
    object_ids, batch_parts, tree_parts = {}, [], []
    for path in paths:
        payload = payloads[path]
        framed = f"blob {len(payload)}\0".encode("ascii") + payload
        object_id = hashlib.sha1(framed).hexdigest()
        object_ids[path] = object_id
        tree_parts.append(f"100644 blob {object_id}\t{path}".encode("utf-8") + b"\0")
        batch_parts.append(
            f"{object_id} blob {len(payload)}\n".encode("ascii") + payload + b"\n"
        )
    calls = []

    def fake_git(prefix, root, environment, *arguments, limit, stdin_bytes=None):
        calls.append((arguments, stdin_bytes))
        return b"".join(tree_parts) if arguments[0] == "ls-tree" else b"".join(batch_parts)

    monkeypatch.setattr(builder_git_module, "_git", fake_git)
    rows = _committed_file_rows(("git",), Path("O:/repo"), {}, "a" * 40, paths)
    request = b"".join(object_ids[path].encode("ascii") + b"\n" for path in paths)
    assert calls == [
        (("ls-tree", "-r", "-z", "--full-tree", "a" * 40), None),
        (("cat-file", "--batch"), request),
    ]
    assert tuple(row[0] for row in rows) == paths
    return len(rows), sum(row[1] for row in rows)


def _exercise_source_rows(count: int) -> tuple[int, int]:
    Path("O:/tmp").mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="reddog-builder-scale-", dir="O:/tmp") as name:
        root = Path(name)
        origins, expected, git = _source_fixture(root, count)
        first = _observed_source_rows(root, origins, expected, git)
        final_path = root.joinpath(*first[-1]["relative_path"].split("/"))
        original = final_path.read_bytes()
        final_path.write_bytes(original.replace(b"1499", b"FAIL"))
        with pytest.raises(QueryRuntimeBuilderSourceError, match="MANIFEST_DIGEST_MISMATCH"):
            _observed_source_rows(root, origins, expected, git)
        final_path.write_bytes(original)
        second = _observed_source_rows(root, origins, expected, git)
        assert second == first
        return len(first), sum(row["size"] for row in first)


def _receipt(packaging_count: int, packaging_bytes: int, source_count: int, source_bytes: int):
    process = _process_authority_capability({
        "runtime_composition_generation_id": _d("1"),
        "runtime_composition_descriptor_digest": _d("2"),
        "builder_source_root_digest": _d("a"),
        "dependency_runtime_inventory_digest": _d("6"),
        "process_image_content_digest": _d("3"), "process_image_size": 42,
        "launch_state_digest": _d("4"), "sys_path_digest": _d("5"),
        "actual_process_image_verified": True, "isolation_verified": True,
        "native_loaded_image_closure_verified": False,
    })
    packaging = _packaging_authority_capability({
        "distribution_name": "packaging", "distribution_version": "26.0",
        "dependency_inventory_digest": _d("6"), "record_digest": _d("7"),
        "owned_files_digest": _d("8"), "owned_file_count": packaging_count,
        "owned_file_bytes": packaging_bytes, "loaded_origins_digest": _d("9"),
        "loaded_module_count": 6, "record_ownership_verified": True,
        "source_only_topology_verified": True, "bytecode_cache_absent": True,
        "loaded_origin_metadata_verified": True,
    })
    source = _source_authority_capability({
        "repo_head_sha": "a" * 40, "repo_root_digest": _d("a"),
        "backend_manifest_digest": _d("b"), "observed_source_manifest_digest": _d("c"),
        "observed_loaded_sources_digest": _d("d"), "loaded_source_count": source_count,
        "loaded_source_bytes": source_bytes, "git_executable_content_digest": _d("e"),
        "repository_state_digest": _d("f"), "manifest_bytes_verified": True,
        "observed_loaded_source_metadata_verified": True,
        "pinned_git_executable_verified": True,
        "repository_topology_snapshot_verified": True, "git_environment_sanitized": True,
    })
    return builder_authority_receipt(
        process_authority=process, packaging_authority=packaging,
        source_authority=source,
    )


def _sample_process(stop: threading.Event, samples: list[tuple[int, int]], process) -> None:
    while not stop.wait(0.01):
        samples.append((process.num_handles(), process.memory_info().rss))


def test_builder_upper_shape_is_deterministic_and_resource_bounded(monkeypatch) -> None:
    psutil = pytest.importorskip("psutil")
    process = psutil.Process(os.getpid())
    baseline = (process.num_handles(), process.memory_info().rss)
    samples = [baseline]
    stop = threading.Event()
    monitor = threading.Thread(
        target=_sample_process, args=(stop, samples, process),
        daemon=True, name="reddog-builder-scale-monitor",
    )
    started = time.monotonic()
    monitor.start()
    try:
        packaging_count, packaging_bytes = _exercise_packaging_rows(_PACKAGING_ROWS)
        git_count, git_bytes = _exercise_git_batch(_SOURCE_ROWS, monkeypatch)
        source_count, source_bytes = _exercise_source_rows(_SOURCE_ROWS)
        first = _receipt(packaging_count, packaging_bytes, source_count, source_bytes)
        second = _receipt(packaging_count, packaging_bytes, source_count, source_bytes)
    finally:
        stop.set()
        monitor.join(timeout=5)
    elapsed = time.monotonic() - started
    evidence = {
        "packaging_rows": packaging_count, "git_batch_rows": git_count,
        "git_batch_bytes": git_bytes, "source_rows": source_count,
        "elapsed_seconds": round(elapsed, 3),
        "peak_handle_delta": max(row[0] for row in samples) - baseline[0],
        "peak_rss_delta_bytes": max(row[1] for row in samples) - baseline[1],
    }
    assert first == second
    assert packaging_count == _PACKAGING_ROWS
    assert git_count == _SOURCE_ROWS
    assert source_count == _SOURCE_ROWS
    assert evidence["peak_handle_delta"] < 128
    assert evidence["peak_rss_delta_bytes"] < 768 * 1024 * 1024
    assert elapsed < 120
    print("BUILDER_SCALE_EVIDENCE=" + json.dumps(evidence, sort_keys=True, separators=(",", ":")))
