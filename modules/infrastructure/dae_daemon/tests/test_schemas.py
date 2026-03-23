"""Layer 0 Tests: Schema serialization round-trips."""

import json
import time
import pytest

from modules.infrastructure.dae_daemon.src.schemas import (
    DAEState,
    DAEEventType,
    SecuritySeverity,
    DAERegistration,
    DAEEvent,
    KillswitchReport,
)


class TestDAEState:
    def test_all_states_exist(self):
        expected = {"registered", "starting", "running", "degraded",
                    "stopping", "stopped", "detached", "crashed"}
        assert {s.value for s in DAEState} == expected

    def test_round_trip(self):
        for state in DAEState:
            assert DAEState(state.value) is state


class TestDAEEventType:
    def test_lifecycle_events(self):
        lifecycle = {"dae_registered", "dae_started", "dae_stopped",
                     "dae_heartbeat", "dae_state_changed", "dae_detached"}
        actual = {e.value for e in DAEEventType
                  if e.value.startswith("dae_")}
        assert lifecycle == actual

    def test_cardiovascular_events(self):
        cardio = {"message_in", "message_out", "action_performed"}
        actual = {e.value for e in DAEEventType
                  if e.value in cardio}
        assert cardio == actual

    def test_security_events(self):
        assert DAEEventType.SECURITY_VIOLATION.value == "security_violation"
        assert DAEEventType.KILLSWITCH_TRIGGERED.value == "killswitch_triggered"


class TestDAERegistration:
    def test_defaults(self):
        reg = DAERegistration(dae_id="fam", dae_name="FAM", domain="foundups")
        assert reg.enabled is True
        assert reg.state == DAEState.REGISTERED
        assert reg.pid is None
        assert reg.heartbeat_interval_sec == 60.0

    def test_round_trip(self):
        reg = DAERegistration(
            dae_id="yt_livechat",
            dae_name="YouTube LiveChat",
            domain="communication",
            enabled=False,
            state=DAEState.RUNNING,
            pid=12345,
            heartbeat_interval_sec=30.0,
            last_heartbeat=time.time(),
            metadata={"channel_id": "abc"},
        )
        d = reg.to_dict()
        restored = DAERegistration.from_dict(d)
        assert restored.dae_id == reg.dae_id
        assert restored.state == DAEState.RUNNING
        assert restored.pid == 12345
        assert restored.metadata == {"channel_id": "abc"}

    def test_to_dict_state_is_string(self):
        reg = DAERegistration(dae_id="x", dae_name="X", domain="d")
        d = reg.to_dict()
        assert isinstance(d["state"], str)
        assert d["state"] == "registered"


class TestDAEEvent:
    def test_auto_fields(self):
        ev = DAEEvent(event_type=DAEEventType.DAE_STARTED, dae_id="fam")
        assert ev.timestamp > 0
        assert len(ev.event_id) == 16
        assert ev.dedupe_key == ev.event_id

    def test_deterministic_id(self):
        ts = 1700000000.0
        ev1 = DAEEvent(
            event_type=DAEEventType.DAE_HEARTBEAT,
            dae_id="fam",
            payload={"cpu": 0.5},
            timestamp=ts,
        )
        ev2 = DAEEvent(
            event_type=DAEEventType.DAE_HEARTBEAT,
            dae_id="fam",
            payload={"cpu": 0.5},
            timestamp=ts,
        )
        assert ev1.event_id == ev2.event_id

    def test_different_payload_different_id(self):
        ts = 1700000000.0
        ev1 = DAEEvent(
            event_type=DAEEventType.DAE_HEARTBEAT,
            dae_id="fam",
            payload={"cpu": 0.5},
            timestamp=ts,
        )
        ev2 = DAEEvent(
            event_type=DAEEventType.DAE_HEARTBEAT,
            dae_id="fam",
            payload={"cpu": 0.9},
            timestamp=ts,
        )
        assert ev1.event_id != ev2.event_id

    def test_round_trip(self):
        ev = DAEEvent(
            event_type=DAEEventType.MESSAGE_IN,
            dae_id="openclaw",
            payload={"source": "voice_repl", "length": 42},
            actor_id="012",
        )
        d = ev.to_dict()
        assert isinstance(d["event_type"], str)

        restored = DAEEvent.from_dict(d)
        assert restored.event_type == DAEEventType.MESSAGE_IN
        assert restored.dae_id == "openclaw"
        assert restored.payload["source"] == "voice_repl"

    def test_json_serializable(self):
        ev = DAEEvent(
            event_type=DAEEventType.ACTION_PERFORMED,
            dae_id="sim",
            payload={"action": "step", "tick": 100},
        )
        # Must not raise
        json_str = json.dumps(ev.to_dict())
        assert "action_performed" in json_str


class TestKillswitchReport:
    def test_defaults(self):
        report = KillswitchReport(dae_id="bad_dae")
        assert report.severity == SecuritySeverity.CRITICAL
        assert report.timestamp > 0
        assert report.pid_kill_success is False

    def test_round_trip(self):
        report = KillswitchReport(
            dae_id="openclaw",
            dae_name="OpenClaw DAE",
            reason="Unauthorized API call to external service",
            severity=SecuritySeverity.HIGH,
            triggering_event_ids=["abc123", "def456"],
            pid_terminated=9999,
            pid_kill_success=True,
            metadata={"investigation": "pending"},
        )
        d = report.to_dict()
        assert d["severity"] == "high"

        restored = KillswitchReport.from_dict(d)
        assert restored.severity == SecuritySeverity.HIGH
        assert restored.pid_terminated == 9999
        assert len(restored.triggering_event_ids) == 2
