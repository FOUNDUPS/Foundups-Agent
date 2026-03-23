from unittest.mock import MagicMock

import pytest

from modules.communication.moltbot_bridge.src.openclaw_supervisor import (
    OpenClawSupervisor,
    SupervisorState,
)
from modules.infrastructure.database.src.db_manager import DatabaseManager


@pytest.fixture(autouse=True)
def isolated_agent_db(tmp_path, monkeypatch):
    monkeypatch.setenv("FOUNDUPS_DB_PATH", str(tmp_path / "foundups.db"))
    DatabaseManager.reset_for_tests()
    yield
    DatabaseManager.reset_for_tests()


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
    observer.follow_events.return_value = {
        "events": [],
        "next_cursor": 4,
        "latest_sequence_id": 4,
    }

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
    assert supervisor._event_cursor == 4
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
    observer.follow_events.return_value = {
        "events": [],
        "next_cursor": 9,
        "latest_sequence_id": 9,
    }

    events = []
    supervisor = OpenClawSupervisor(
        repo_root=tmp_path,
        broker=broker,
        observer=observer,
        action_reporter=lambda action, result, details: events.append((action, result, details)),
        self_audit_factory=lambda repo_root: MagicMock(),
    )

    from unittest.mock import patch
    with patch("modules.infrastructure.database.src.agent_db.AgentDB") as mock_db:
        mock_db.return_value.get_autonomous_tasks.return_value = []
        result = supervisor.run_cycle()

    broker.start_dae.assert_not_called()
    assert result["triage"]["kind"] == "idle"
    assert supervisor.current_state == SupervisorState.IDLE_WATCH
    assert supervisor._event_cursor == 9
    assert any(action == "supervisor_cycle" for action, _, _ in events)


def test_run_cycle_escalates_when_restart_budget_is_exhausted(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENCLAW_SUPERVISOR_MAX_RESTARTS", "2")
    monkeypatch.setenv("OPENCLAW_SUPERVISOR_RESTART_WINDOW_SEC", "600")

    broker = MagicMock()
    broker.get_runtime_status.side_effect = lambda dae_id: {
        "registered": True,
        "running": False,
        "state": "stopped",
        "last_error": "crashed",
        "enabled": True,
    }
    observer = MagicMock()
    observer.get_live_status.return_value = {"registered": True, "recent_events": []}
    observer.follow_events.return_value = {
        "events": [{"sequence_id": 12, "payload": {"action_type": "launch_failed"}}],
        "next_cursor": 12,
        "latest_sequence_id": 12,
    }

    events = []
    supervisor = OpenClawSupervisor(
        repo_root=tmp_path,
        broker=broker,
        observer=observer,
        action_reporter=lambda action, result, details: events.append((action, result, details)),
        self_audit_factory=lambda repo_root: MagicMock(),
    )
    supervisor._restart_attempts.extend([100.0, 200.0])

    from unittest.mock import patch

    with patch("modules.communication.moltbot_bridge.src.openclaw_supervisor.time.time", return_value=250.0):
        result = supervisor.run_cycle()

    broker.start_dae.assert_not_called()
    assert result["verify"]["ok"] is False
    assert result["verify"]["error"] == "resident_openclaw_restart_budget_exhausted"
    assert supervisor.current_state == SupervisorState.ESCALATE
    assert supervisor._event_cursor == 12
    assert any(result == "ESCALATE" for action, result, _ in events if action == "supervisor_state")


def test_run_cycle_records_failed_verify_and_advances_cursor(tmp_path):
    broker = MagicMock()

    def status_for(dae_id):
        if dae_id == "openclaw":
            return {"registered": True, "running": False, "state": "stopped", "last_error": "still down", "enabled": True}
        return {"registered": True, "running": True, "state": "running", "last_error": "", "enabled": True}

    broker.get_runtime_status.side_effect = status_for
    broker.start_dae.return_value = {"status": "starting"}

    observer = MagicMock()
    observer.get_live_status.return_value = {"registered": True, "recent_events": []}
    observer.follow_events.return_value = {
        "events": [{"sequence_id": 21, "payload": {"action_type": "launch_failed"}}],
        "next_cursor": 21,
        "latest_sequence_id": 21,
    }

    events = []
    supervisor = OpenClawSupervisor(
        repo_root=tmp_path,
        broker=broker,
        observer=observer,
        action_reporter=lambda action, result, details: events.append((action, result, details)),
        self_audit_factory=lambda repo_root: MagicMock(),
    )

    result = supervisor.run_cycle()

    assert result["verify"]["ok"] is False
    assert supervisor.current_state == SupervisorState.ESCALATE
    assert supervisor._event_cursor == 21
    assert any(action == "supervisor_cycle" for action, _, _ in events)
