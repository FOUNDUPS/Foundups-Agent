from unittest.mock import MagicMock
from pathlib import Path

from modules.communication.moltbot_bridge.src.openclaw_supervisor import OpenClawSupervisor
from modules.infrastructure.database.src.agent_db import AgentDB
from modules.infrastructure.database.src.db_manager import DatabaseManager


def test_run_cycle_executes_and_completes_pending_autonomous_task(tmp_path, monkeypatch):
    db_path = tmp_path / "foundups.db"
    monkeypatch.setenv("FOUNDUPS_DB_PATH", str(db_path))
    monkeypatch.setenv("OPENCLAW_AUTO_TASKS_ENABLED", "1")
    # Mock WRE to accept "test" skill and return success
    monkeypatch.setenv("WRE_MOCK_SKILLS", "test")
    DatabaseManager.reset_for_tests()

    # Mock WRE execute_skill to return success
    mock_wre = MagicMock()
    mock_wre.skills_loader = MagicMock()
    mock_wre.skills_loader.has_skill.return_value = True
    mock_wre.execute_skill.return_value = {"success": True, "output": "test completed"}
    monkeypatch.setattr(
        "modules.infrastructure.wre_core.wre_master_orchestrator.src.wre_master_orchestrator.WREMasterOrchestrator",
        lambda: mock_wre,
    )

    db = AgentDB()
    task_id = "test_task_p0_001"
    created = db.create_autonomous_task(
        task_id=task_id,
        description="Test P0 autonomous pipeline",
        required_skills=["test"],
        estimated_complexity=1.0,
        priority_score=99.0,
        context={"test": True},
    )
    assert created is True

    broker = MagicMock()
    broker.get_runtime_status.side_effect = lambda dae_id: {
        "registered": True,
        "running": True,
        "state": "running",
        "last_error": "",
        "enabled": True,
    }

    observer = MagicMock()
    observer.get_live_status.return_value = {"registered": True}
    observer.follow_events.return_value = {
        "events": [],
        "next_cursor": 0,
        "latest_sequence_id": 0,
    }

    events = []
    supervisor = OpenClawSupervisor(
        repo_root=Path(__file__).resolve().parents[4],
        broker=broker,
        observer=observer,
        action_reporter=lambda action, result, details: events.append((action, result, details)),
    )
    supervisor._bootstrapped = True

    result = supervisor.run_cycle()

    completed = db.get_autonomous_tasks(status="completed", limit=10)
    assert any(item["task_id"] == task_id for item in completed)
    assert result["plan"]["action"] == "execute_autonomous_task"
    assert result["verify"]["ok"] is True
    assert result["verify"]["task_status"] == "completed"
    assert any(action == "supervisor_execute" and outcome == "completed" for action, outcome, _ in events)

    DatabaseManager.reset_for_tests()
