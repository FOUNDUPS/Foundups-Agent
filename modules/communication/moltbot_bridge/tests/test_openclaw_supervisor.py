from unittest.mock import MagicMock

from modules.communication.moltbot_bridge.src.openclaw_supervisor import (
    OpenClawSupervisor,
    SupervisorState,
)


def test_run_cycle_starts_openclaw_when_resident_runtime_is_down(tmp_path):
    broker = MagicMock()

    def status_for(dae_id):
        if dae_id == "openclaw":
            if not getattr(status_for, "seen_openclaw", False):
                status_for.seen_openclaw = True
                return {"registered": True, "running": False, "state": "stopped", "last_error": "", "enabled": True}
            return {"registered": True, "running": True, "state": "starting", "last_error": "", "enabled": True}
        return {"registered": True, "running": True, "state": "running", "last_error": "", "enabled": True}

    broker.get_runtime_status.side_effect = status_for
    broker.start_dae.return_value = {"status": "starting"}

    observer = MagicMock()
    observer.get_live_status.return_value = {"registered": True, "recent_events": []}

    events = []
    audit_loop = MagicMock()

    supervisor = OpenClawSupervisor(
        repo_root=tmp_path,
        broker=broker,
        observer=observer,
        action_reporter=lambda action, result, details: events.append((action, result, details)),
        self_audit_factory=lambda repo_root: audit_loop,
    )

    result = supervisor.run_cycle()

    broker.start_dae.assert_called_once_with("openclaw", actor_id="0102")
    audit_loop.start.assert_called_once()
    assert result["verify"]["ok"] is True
    assert supervisor.current_state == SupervisorState.IDLE_WATCH
    assert any(action == "supervisor_execute" for action, _, _ in events)


def test_run_cycle_idles_when_resident_runtime_is_healthy(tmp_path):
    broker = MagicMock()
    broker.get_runtime_status.side_effect = lambda dae_id: {
        "registered": True,
        "running": True,
        "state": "running",
        "last_error": "",
        "enabled": True,
    }
    observer = MagicMock()
    observer.get_live_status.return_value = {"registered": True, "recent_events": []}

    events = []
    supervisor = OpenClawSupervisor(
        repo_root=tmp_path,
        broker=broker,
        observer=observer,
        action_reporter=lambda action, result, details: events.append((action, result, details)),
        self_audit_factory=lambda repo_root: MagicMock(),
    )

    result = supervisor.run_cycle()

    broker.start_dae.assert_not_called()
    assert result["triage"]["kind"] == "idle"
    assert supervisor.current_state == SupervisorState.IDLE_WATCH
    assert any(action == "supervisor_cycle" for action, _, _ in events)
