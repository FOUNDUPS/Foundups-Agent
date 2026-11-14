"""Opt-in production-shape scale soak for the positive distribution graph."""

from __future__ import annotations

import base64
import hashlib
import os
import threading
import time

import pytest

from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_dependency_runtime_contract import (
    digest_bytes,
)
from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_query_distribution_graph import (
    derive_distribution_projection,
)
from modules.infrastructure.foundups_mcp_bridge.tests.test_reddog_holoindex_query_distribution_graph import (
    TARGET,
)


pytestmark = pytest.mark.skipif(
    os.environ.get("REDDOG_RUN_QUERY_CANDIDATE_SCALE_SOAK") != "1",
    reason="explicit production-shape query-candidate soak only",
)


def _record_hash(payload: bytes) -> str:
    encoded = base64.urlsafe_b64encode(hashlib.sha256(payload).digest())
    return encoded.rstrip(b"=").decode("ascii")


def _distribution(index: int, count: int, files_per_distribution: int) -> dict[str, bytes]:
    name = f"scale-{index:03d}"
    package = name.replace("-", "_")
    stem = f"{package}-1.0.dist-info"
    requirement = f"Requires-Dist: scale-{index + 1:03d}==1.0\n" if index + 1 < count else ""
    metadata = (
        f"Metadata-Version: 2.1\nName: {name}\nVersion: 1.0\n{requirement}\n"
    ).encode()
    wheel = (
        b"Wheel-Version: 1.0\nRoot-Is-Purelib: true\nTag: py3-none-any\n"
    )
    payloads = {
        f"{package}/f{item:04d}.py": b"VALUE=1\n"
        for item in range(files_per_distribution)
    }
    payloads[f"{stem}/METADATA"] = metadata
    payloads[f"{stem}/WHEEL"] = wheel
    record_path = f"{stem}/RECORD"
    record = "".join(
        f"{path},sha256={_record_hash(payload)},{len(payload)}\n"
        for path, payload in sorted(payloads.items(), key=lambda row: row[0].casefold())
    )
    payloads[record_path] = (record + f"{record_path},,\n").encode()
    return payloads


def _sample_rss(stop: threading.Event, samples: list[int], process) -> None:
    while not stop.wait(0.01):
        samples.append(process.memory_info().rss)


def test_distribution_graph_production_shape_is_bounded() -> None:
    psutil = pytest.importorskip("psutil")
    distribution_count, files_per_distribution = 150, 300
    payloads: dict[str, bytes] = {}
    for index in range(distribution_count):
        payloads.update(_distribution(index, distribution_count, files_per_distribution))
    rows = [{
        "path": path, "size": len(payload), "sha256": digest_bytes(payload),
        "role": "dependency_payload",
    } for path, payload in sorted(payloads.items(), key=lambda row: row[0].casefold())]
    process = psutil.Process(os.getpid())
    baseline = process.memory_info().rss
    samples = [baseline]
    stop = threading.Event()
    monitor = threading.Thread(target=_sample_rss, args=(stop, samples, process), daemon=True)
    monitor.start()
    started = time.monotonic()
    try:
        result = derive_distribution_projection(
            inventory_rows=rows, read_bytes=payloads.__getitem__,
            root_requirements=[{"name": "scale-000", "version": "1.0", "extras": []}],
            module_origins=[
                "scale_000/f0000.py", f"scale_{distribution_count - 1:03d}/f0299.py",
            ],
            marker_environment=TARGET,
        )
    finally:
        stop.set()
        monitor.join(timeout=5)
    elapsed = time.monotonic() - started
    peak_rss_delta = max(samples) - baseline

    assert len(result.distributions) == distribution_count
    assert len(result.files) == distribution_count * (files_per_distribution + 3)
    assert elapsed < 120
    assert peak_rss_delta < 768 * 1024 * 1024
