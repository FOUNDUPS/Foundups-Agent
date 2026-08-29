"""Opt-in physical reviewed-wheel repeatability and resource integration gate."""

from __future__ import annotations

import gc
import hashlib
import os
from pathlib import Path
import time

import psutil
import pytest

from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_query_runtime_builder_packaging_wheel import (
    PACKAGING_26_WHEEL_SHA256,
    PACKAGING_26_WHEEL_SIZE,
    admit_pinned_builder_packaging_wheel,
)


pytestmark = pytest.mark.integration
_REPEAT_ADMISSIONS = 200


def test_opt_in_real_reviewed_packaging_wheel_repeatability_and_resources() -> None:
    if os.environ.get("REDDOG_RUN_PACKAGING_26_REAL_WHEEL") != "1":
        pytest.skip("set REDDOG_RUN_PACKAGING_26_REAL_WHEEL=1 for the physical gate")
    raw = os.environ.get("REDDOG_PACKAGING_26_WHEEL", "")
    assert raw, "REDDOG_PACKAGING_26_WHEEL is required once the gate is enabled"
    path = Path(raw)
    assert path.is_absolute() and path.drive.rstrip(":").upper() in {"O", "E"}
    before_digest = hashlib.sha256(path.read_bytes()).hexdigest()
    process = psutil.Process()
    before_handles = process.num_handles()
    before_rss = process.memory_info().rss
    started = time.perf_counter()
    results = tuple(
        admit_pinned_builder_packaging_wheel(
            wheel_path=path, wheel_store_root=path.parent,
        )
        for _index in range(_REPEAT_ADMISSIONS)
    )
    elapsed = time.perf_counter() - started
    gc.collect()
    first = results[0]
    assert all(result == first for result in results)
    assert first.wheel_sha256 == "sha256:" + PACKAGING_26_WHEEL_SHA256
    assert first.wheel_size == PACKAGING_26_WHEEL_SIZE
    assert first.member_count == 24
    assert first.expanded_bytes == 276_911
    assert process.num_handles() - before_handles < 4
    assert process.memory_info().rss - before_rss < 16 * 1024 * 1024
    assert hashlib.sha256(path.read_bytes()).hexdigest() == before_digest
    assert elapsed < 30.0
