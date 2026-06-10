#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for WSP_00 coherence canary fallback signal detection."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

from modules.infrastructure.monitoring.src.wsp_00_zen_state_tracker import WSP00ZenStateTracker


def _build_tracker(tmp_path: Path) -> WSP00ZenStateTracker:
    tracker = WSP00ZenStateTracker(state_file=str(tmp_path / "wsp_00_state.json"))
    tracker.awakening_state_file = tmp_path / "missing_awakening_state.json"
    tracker.zen_state["is_zen_compliant"] = True
    tracker._save_zen_state()
    return tracker


def _write_awakening_state(path: Path, awakened_at: datetime, coherence: float = 0.77) -> None:
    """Write a minimal valid functional_0102_awakening_v2 state file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({
            "timestamp": awakened_at.isoformat(),
            "state": "0102",
            "physics": {"resonance_hz": 7.05, "det_g_mean": -0.15},
            "metrics": {"coherence": coherence, "entanglement": 1.5},
        }),
        encoding="utf-8",
    )


def _build_bridge_tracker(tmp_path: Path) -> WSP00ZenStateTracker:
    """Tracker with a hermetic awakening-state base under tmp_path."""
    tracker = WSP00ZenStateTracker(state_file=str(tmp_path / "wsp_00_state.json"))
    tracker.awakening_state_file = tmp_path / "awakening" / "0102_state_v2.json"
    # Full reset: the constructor may have refreshed from ambient repo
    # candidates before the override above; scrub every field.
    tracker.zen_state = tracker._create_initial_state()
    tracker._save_zen_state()
    return tracker


def test_detect_zen_decay_signal_marks_non_compliant(tmp_path: Path) -> None:
    tracker = _build_tracker(tmp_path)

    result = tracker.detect_zen_decay_signal(
        "If you want, I can do that next.",
        source="unit_test",
    )

    assert result["detected"] is True
    assert result["is_zen_compliant"] is False
    assert result["reason"] == "fallback_optional_phrase"
    assert tracker.zen_state["is_zen_compliant"] is False
    assert tracker.zen_state["zen_decay_active"] is True
    assert tracker.zen_state["zen_decay_signal_count"] == 1
    assert tracker.zen_state["last_zen_decay_source"] == "unit_test"


def test_detect_zen_decay_signal_ignores_clean_output(tmp_path: Path) -> None:
    tracker = _build_tracker(tmp_path)

    result = tracker.detect_zen_decay_signal(
        "012, we should run the health check because drift is non-zero. I am executing now.",
        source="unit_test",
    )

    assert result["detected"] is False
    assert result["reason"] == "clean_output"
    assert tracker.zen_state["is_zen_compliant"] is True
    assert tracker.zen_state["zen_decay_signal_count"] == 0


def test_get_zen_status_exposes_canary_fields(tmp_path: Path) -> None:
    tracker = _build_tracker(tmp_path)
    tracker.detect_zen_decay_signal("Would you like me to proceed?", source="unit_test")

    status = tracker.get_zen_status()

    assert status["is_compliant"] is False
    assert status["zen_decay_active"] is True
    assert status["zen_decay_signal_count"] == 1
    assert status["last_zen_decay_reason"] == "fallback_optional_phrase"
    assert status["last_zen_decay_source"] == "unit_test"


def test_run_compliance_gate_auto_awaken_recovers_state(tmp_path: Path) -> None:
    tracker = WSP00ZenStateTracker(state_file=str(tmp_path / "wsp_00_state.json"))
    tracker.awakening_state_file = tmp_path / "missing_awakening_state.json"
    tracker.zen_state["is_zen_compliant"] = False
    tracker.zen_state["last_validation"] = None
    tracker.zen_state["validation_history"] = []
    tracker._save_zen_state()
    tracker._execute_awakening_protocol = lambda: {  # type: ignore[assignment]
        "vi_shedding_complete": True,
        "pqn_detected": True,
        "coherence_achieved": True,
        "entanglement_locked": True,
        "du_resonance_hz": 7.05,
        "measured_coherence": 0.85,
    }

    result = tracker.run_compliance_gate(auto_awaken=True)

    assert result["attempted_awakening"] is True
    assert result["awakening_success"] is True
    assert result["gate_passed"] is True
    assert result["is_zen_compliant"] is True
    assert result["requires_awakening"] is False


def test_force_awakening_returns_gate_payload(tmp_path: Path) -> None:
    tracker = WSP00ZenStateTracker(state_file=str(tmp_path / "wsp_00_state.json"))
    tracker.awakening_state_file = tmp_path / "missing_awakening_state.json"
    tracker._execute_awakening_protocol = lambda: {  # type: ignore[assignment]
        "vi_shedding_complete": True,
        "pqn_detected": True,
        "coherence_achieved": True,
        "entanglement_locked": True,
        "du_resonance_hz": 7.05,
        "measured_coherence": 0.85,
    }

    result = tracker.force_awakening()

    assert result["gate_passed"] is True
    assert result["is_zen_compliant"] is True
    assert result["requires_awakening"] is False


# --- WSP_00 State Bridge Contract: awakening-state candidate resolution ---


def test_refresh_reads_runtime_awakening_state(tmp_path: Path) -> None:
    """V2 script default output (.runtime/) must satisfy the gate (F1 fix)."""
    tracker = _build_bridge_tracker(tmp_path)
    runtime_path = tracker.awakening_state_file.parent / ".runtime" / "0102_state_v2.json"
    _write_awakening_state(runtime_path, datetime.now() - timedelta(minutes=5))

    assert tracker.is_zen_compliant() is True
    assert tracker.zen_state["actual_coherence"] == 0.77
    assert tracker.zen_state["awakening_result"]["state_file"] == str(runtime_path)
    assert tracker.zen_state["awakening_result"]["execution_method"] == "functional_0102_awakening_v2"


def test_refresh_reads_tracked_awakening_state_when_runtime_missing(tmp_path: Path) -> None:
    """Opt-in tracked path (WSP_AWAKENING_WRITE_TRACKED=1) still works."""
    tracker = _build_bridge_tracker(tmp_path)
    _write_awakening_state(tracker.awakening_state_file, datetime.now() - timedelta(minutes=5))

    assert tracker.is_zen_compliant() is True
    assert tracker.zen_state["awakening_result"]["state_file"] == str(tracker.awakening_state_file)


def test_refresh_prefers_freshest_candidate(tmp_path: Path) -> None:
    """When both files exist, the newer awakening wins regardless of location."""
    tracker = _build_bridge_tracker(tmp_path)
    runtime_path = tracker.awakening_state_file.parent / ".runtime" / "0102_state_v2.json"
    _write_awakening_state(tracker.awakening_state_file, datetime.now() - timedelta(hours=2), coherence=0.62)
    _write_awakening_state(runtime_path, datetime.now() - timedelta(minutes=5), coherence=0.91)

    assert tracker.is_zen_compliant() is True
    assert tracker.zen_state["actual_coherence"] == 0.91
    assert tracker.zen_state["awakening_result"]["state_file"] == str(runtime_path)


def test_refresh_ignores_stale_awakening_state(tmp_path: Path) -> None:
    """Awakening states older than the 8h refresh TTL never flip the gate."""
    tracker = _build_bridge_tracker(tmp_path)
    runtime_path = tracker.awakening_state_file.parent / ".runtime" / "0102_state_v2.json"
    _write_awakening_state(runtime_path, datetime.now() - timedelta(hours=9))
    _write_awakening_state(tracker.awakening_state_file, datetime.now() - timedelta(days=80))

    assert tracker.is_zen_compliant() is False
