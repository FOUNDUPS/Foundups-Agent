#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for the lightweight runtime event emitter.

Validates the event contract, JSONL persistence, and the
start/success/failure convenience helpers.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from modules.infrastructure.dae_daemon.src.runtime_emitter import (
    RuntimeEvent,
    emit,
    emit_failure,
    emit_start,
    emit_success,
    set_events_dir,
    reset_events_dir,
)


@pytest.fixture(autouse=True)
def _use_tmp_events_dir(tmp_path):
    """Redirect emitter output to a temp directory for every test."""
    set_events_dir(tmp_path)
    yield
    reset_events_dir()


def _read_events(tmp_path: Path) -> list[dict]:
    path = tmp_path / "runtime_events.jsonl"
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    return [json.loads(line) for line in lines]


# ---------------------------------------------------------------------------
# RuntimeEvent dataclass
# ---------------------------------------------------------------------------


class TestRuntimeEvent:

    def test_to_dict_strips_none(self):
        event = RuntimeEvent(
            surface="test", event_type="unit", status="success",
        )
        d = event.to_dict()
        assert "continuity_id" not in d
        assert "error" not in d
        assert d["surface"] == "test"
        assert d["status"] == "success"
        assert "timestamp" in d

    def test_to_dict_includes_non_none(self):
        event = RuntimeEvent(
            surface="x", event_type="y", status="failure",
            continuity_id="abc123", error="boom",
        )
        d = event.to_dict()
        assert d["continuity_id"] == "abc123"
        assert d["error"] == "boom"


# ---------------------------------------------------------------------------
# emit() — raw JSONL append
# ---------------------------------------------------------------------------


class TestEmit:

    def test_emit_writes_jsonl(self, tmp_path):
        event = RuntimeEvent(surface="s", event_type="e", status="started")
        emit(event)
        events = _read_events(tmp_path)
        assert len(events) == 1
        assert events[0]["surface"] == "s"
        assert events[0]["status"] == "started"

    def test_emit_appends(self, tmp_path):
        emit(RuntimeEvent(surface="a", event_type="t", status="started"))
        emit(RuntimeEvent(surface="b", event_type="t", status="success"))
        events = _read_events(tmp_path)
        assert len(events) == 2


# ---------------------------------------------------------------------------
# emit_start / emit_success / emit_failure helpers
# ---------------------------------------------------------------------------


class TestStartSuccessFailure:

    def test_start_returns_monotonic_time(self, tmp_path):
        before = time.monotonic()
        t = emit_start("surf", "evt")
        after = time.monotonic()
        assert before <= t <= after

        events = _read_events(tmp_path)
        assert len(events) == 1
        assert events[0]["status"] == "started"

    def test_success_computes_duration(self, tmp_path):
        t0 = emit_start("surf", "evt", task_id="task_1")
        time.sleep(0.05)  # 50ms to account for Windows timer resolution
        emit_success("surf", "evt", t0, task_id="task_1",
                     details={"key": "val"})

        events = _read_events(tmp_path)
        assert len(events) == 2
        success = events[1]
        assert success["status"] == "success"
        assert success["duration_ms"] >= 0  # monotonic, always non-negative
        assert success["task_id"] == "task_1"
        assert success["details"]["key"] == "val"

    def test_failure_includes_error(self, tmp_path):
        t0 = emit_start("surf", "evt")
        emit_failure("surf", "evt", t0, "something broke",
                     continuity_id="cont_abc")

        events = _read_events(tmp_path)
        failure = events[1]
        assert failure["status"] == "failure"
        assert failure["error"] == "something broke"
        assert failure["continuity_id"] == "cont_abc"

    def test_failure_truncates_long_error(self, tmp_path):
        t0 = emit_start("surf", "evt")
        long_error = "x" * 1000
        emit_failure("surf", "evt", t0, long_error)

        events = _read_events(tmp_path)
        assert len(events[1]["error"]) == 500

    def test_continuity_fields_propagated(self, tmp_path):
        t0 = emit_start(
            "surf", "evt",
            continuity_id="c1",
            parent_continuity_id="p1",
        )
        emit_success(
            "surf", "evt", t0,
            continuity_id="c1",
            parent_continuity_id="p1",
        )

        events = _read_events(tmp_path)
        for e in events:
            assert e["continuity_id"] == "c1"
            assert e["parent_continuity_id"] == "p1"


# ---------------------------------------------------------------------------
# Schema contract — mandatory fields present
# ---------------------------------------------------------------------------


class TestEventContract:

    def test_mandatory_fields_present(self, tmp_path):
        """Every emitted event must have surface, event_type, status, timestamp."""
        emit_start("my_surface", "my_event", task_id="t1")
        events = _read_events(tmp_path)
        e = events[0]
        assert "surface" in e
        assert "event_type" in e
        assert "status" in e
        assert "timestamp" in e

    def test_details_stays_compact(self, tmp_path):
        """Details dict should not contain giant payloads."""
        t0 = emit_start("s", "e", details={"a": "b"})
        emit_success("s", "e", t0, details={"x": 1, "y": 2})
        events = _read_events(tmp_path)
        for e in events:
            serialized = json.dumps(e.get("details", {}))
            assert len(serialized) < 2000, "Details should stay compact"
