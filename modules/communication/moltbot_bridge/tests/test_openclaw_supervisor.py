import json
import os
from unittest.mock import MagicMock, patch

import pytest

from modules.communication.moltbot_bridge.src.openclaw_supervisor import (
    OpenClawSupervisor,
    SupervisorState,
)
from modules.communication.moltbot_bridge.src.reddog_wsp15_allocation_receipt import (
    allocate_reddog_wsp15_receipt,
)
from modules.infrastructure.database.src.db_manager import DatabaseManager


@pytest.fixture(autouse=True)
def isolated_agent_db(tmp_path, monkeypatch):
    monkeypatch.setenv("FOUNDUPS_DB_PATH", str(tmp_path / "foundups.db"))
    DatabaseManager.reset_for_tests()
    yield
    DatabaseManager.reset_for_tests()


def _queue_wsp15_allocation_receipt() -> dict[str, object]:
    return allocate_reddog_wsp15_receipt(
        requested_operation="create_foundup",
        prompt_text="RedDog resident queue runtime authority worktree execution",
        changed_paths=("modules/communication/moltbot_bridge/src/openclaw_supervisor.py",),
        allowed_read_targets=("modules/communication/moltbot_bridge/src/openclaw_supervisor.py",),
    ).to_dict()


def _queue_snapshot() -> dict[str, object]:
    allocation = _queue_wsp15_allocation_receipt()
    return {
        "schema_version": "reddog_authoritative_work_state.v1",
        "freshness_receipts": [{"receipt_id": "fresh-1", "fresh": True}],
        "worker_claims": [
            {
                "claim_id": "claim-1",
                "slice_id": "REDDOG_TEST_SLICE_PHASE1",
                "worker_id": "reddog-0102",
                "status": "ACTIVE",
                "expires_at": "2026-07-14T01:00:00+00:00",
                "freshness_receipt_id": "fresh-1",
            }
        ],
        "wre_queue_items": [
            {
                "queue_item_id": "queue-1",
                "slice_id": "REDDOG_TEST_SLICE_PHASE1",
                "claim_id": "claim-1",
                "worker_id": "reddog-0102",
                "status": "QUEUED",
                "evidence_refs": [
                    "claim:claim-1",
                    "freshness:fresh-1",
                    f"wsp15_allocation:{allocation['receipt_id']}",
                ],
                "wsp15_allocation_receipt": allocation,
                "no_execution_performed": True,
            }
        ],
    }


def _accepted_results_through(stage_key: str) -> dict[str, dict[str, object]]:
    values = {
        "authority_request": {"status": "QUEUE_AUTHORITY_REQUEST_DRYRUN_ACCEPT"},
        "authority_runtime": {"decision": "QUEUE_AUTHORITY_RUNTIME_INVOKE_ACCEPT"},
        "authority_verification": {"decision": "QUEUE_AUTHORITY_VERIFICATION_INVOKE_ACCEPT"},
        "worker_dispatch_dryrun": {
            "decision": "SIGNED_AUTHORITY_WORKER_DISPATCH_DRYRUN_ACCEPT"
        },
        "worker_dispatch_runtime": {
            "decision": "SIGNED_AUTHORITY_WORKER_DISPATCH_RUNTIME_ACCEPT"
        },
        "work_order_invocation": {
            "decision": "QUEUE_VERIFIED_AUTHORITY_WORK_ORDER_INVOKE_ACCEPT"
        },
        "executor_plan": {"decision": "QUEUE_AUTHORIZED_EXECUTOR_PLAN_DRYRUN_ACCEPT"},
        "execution_valve": {"decision": "QUEUE_AUTHORIZED_EXECUTION_VALVE_INVOKE_ACCEPT"},
        "worktree_create": {"decision": "QUEUE_AUTHORIZED_WORKTREE_CREATE_INVOKE_ACCEPT"},
        "bounded_worker_pilot": {
            "decision": "QUEUE_AUTHORIZED_BOUNDED_WORKER_PILOT_INVOKE_ACCEPT"
        },
    }
    ordered: dict[str, dict[str, object]] = {}
    for key, value in values.items():
        ordered[key] = value
        if key == stage_key:
            break
    return ordered


def _write_runtime_queue_state(
    runtime_root,
    *,
    accepted_through: str,
) -> None:
    runtime_root.mkdir(parents=True, exist_ok=True)
    (runtime_root / "authoritative_work_state.json").write_text(
        json.dumps(_queue_snapshot(), sort_keys=True),
        encoding="utf-8",
    )
    (runtime_root / "resident_queue_chain_results.json").write_text(
        json.dumps(
            {
                "schema_version": "reddog_resident_queue_chain_results.v1",
                "stage_results": _accepted_results_through(accepted_through),
            },
            sort_keys=True,
        ),
        encoding="utf-8",
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


def test_run_cycle_claims_signed_worker_tasks_when_enabled(tmp_path):
    from modules.communication.moltbot_bridge.src.reddog_openclaw_hermes_0102_worker_dispatch_runtime import (
        SIGNED_WORKER_DISPATCH_TASK_SOURCE,
    )

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
        "next_cursor": 10,
        "latest_sequence_id": 10,
    }

    events = []
    supervisor = OpenClawSupervisor(
        repo_root=tmp_path,
        broker=broker,
        observer=observer,
        action_reporter=lambda action, result, details: events.append((action, result, details)),
        self_audit_factory=lambda repo_root: MagicMock(scan_once=MagicMock(return_value=0)),
    )
    supervisor._bootstrapped = True
    supervisor.claim_reddog_signed_worker_dispatch_tasks_until_idle = MagicMock(
        return_value={
            "accepted": True,
            "status": "SIGNED_WORKER_OPENCLAW_CLAIM_LOOP_ACCEPT",
            "claimed_count": 2,
            "completed_task_ids": ("task-1", "task-2"),
            "requeued_task_ids": (),
            "failed_task_ids": (),
            "receipt_ids": (
                "signed_worker_task_execution_alpha",
                "signed_worker_task_execution_beta",
            ),
            "rejection_reasons": (),
        }
    )
    pending_task = {
        "task_id": "signed-task-1",
        "discovered_by": SIGNED_WORKER_DISPATCH_TASK_SOURCE,
        "context": {
            "source": SIGNED_WORKER_DISPATCH_TASK_SOURCE,
            "worker_runtime": "openclaw",
            "capability": "candidate_queue_review",
        },
    }

    with patch.dict(
        os.environ,
        {
            "OPENCLAW_SIGNED_WORKER_TASKS_ENABLED": "1",
            "OPENCLAW_SIGNED_WORKER_TASK_MAX_CLAIMS": "2",
            "OPENCLAW_AUTO_TASKS_ENABLED": "1",
        },
    ), patch("modules.infrastructure.database.src.agent_db.AgentDB") as mock_db:
        mock_db.return_value.get_autonomous_tasks.return_value = [pending_task]
        result = supervisor.run_cycle()

    assert result["plan"]["action"] == "claim_signed_worker_tasks_until_idle"
    assert result["plan"]["max_claims"] == 2
    supervisor.claim_reddog_signed_worker_dispatch_tasks_until_idle.assert_called_once_with(
        max_claims=2
    )
    assert result["action_result"]["ok"] is True
    assert result["action_result"]["claimed_count"] == 2
    assert result["action_result"]["receipt_ids"] == (
        "signed_worker_task_execution_alpha",
        "signed_worker_task_execution_beta",
    )
    assert result["verify"]["ok"] is True
    assert result["verify"]["completed_task_ids"] == ("task-1", "task-2")
    assert result["verify"]["receipt_ids"] == (
        "signed_worker_task_execution_alpha",
        "signed_worker_task_execution_beta",
    )
    assert any(event[0] == "supervisor_execute" for event in events)


def test_run_cycle_claims_signed_worker_tasks_when_profile_enables_supervisor_loop(tmp_path):
    from modules.communication.moltbot_bridge.src.reddog_openclaw_hermes_0102_worker_dispatch_runtime import (
        SIGNED_WORKER_DISPATCH_TASK_SOURCE,
    )

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
        "next_cursor": 10,
        "latest_sequence_id": 10,
    }
    supervisor = OpenClawSupervisor(
        repo_root=tmp_path,
        broker=broker,
        observer=observer,
        action_reporter=lambda action, result, details: None,
        self_audit_factory=lambda repo_root: MagicMock(scan_once=MagicMock(return_value=0)),
    )
    supervisor._bootstrapped = True
    supervisor.claim_reddog_signed_worker_dispatch_tasks_until_idle = MagicMock(
        return_value={
            "accepted": True,
            "status": "SIGNED_WORKER_OPENCLAW_CLAIM_LOOP_ACCEPT",
            "claimed_count": 1,
            "completed_task_ids": ("task-profile",),
            "failed_task_ids": (),
            "rejection_reasons": (),
        }
    )
    pending_task = {
        "task_id": "task-profile",
        "discovered_by": SIGNED_WORKER_DISPATCH_TASK_SOURCE,
        "context": {
            "source": SIGNED_WORKER_DISPATCH_TASK_SOURCE,
            "worker_runtime": "openclaw",
            "capability": "candidate_queue_review",
        },
    }

    with patch.dict(
        os.environ,
        {
            "REDDOG_RESIDENT_QUEUE_BINDING_PROFILE": "signed_0102_bounded_code_fusion_worktree_draft_pr",
            "OPENCLAW_SIGNED_WORKER_TASK_MAX_CLAIMS": "3",
        },
    ), patch("modules.infrastructure.database.src.agent_db.AgentDB") as mock_db:
        mock_db.return_value.get_autonomous_tasks.return_value = [pending_task]
        result = supervisor.run_cycle()

    assert result["plan"]["action"] == "claim_signed_worker_tasks_until_idle"
    assert result["plan"]["max_claims"] == 3
    supervisor.claim_reddog_signed_worker_dispatch_tasks_until_idle.assert_called_once_with(
        max_claims=3
    )
    assert result["verify"]["ok"] is True


def test_run_cycle_claims_signed_0102_bounded_code_task_with_profile_runtime_paths(tmp_path):
    from modules.communication.moltbot_bridge.src.reddog_openclaw_hermes_0102_worker_dispatch_runtime import (
        SIGNED_WORKER_DISPATCH_TASK_SOURCE,
    )

    repo = tmp_path / "repo"
    repo.mkdir()
    runtime_root = tmp_path / "resident-runtime"
    _write_runtime_queue_state(runtime_root, accepted_through="worktree_create")
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
        "next_cursor": 12,
        "latest_sequence_id": 12,
    }
    supervisor = OpenClawSupervisor(
        repo_root=repo,
        broker=broker,
        observer=observer,
        action_reporter=lambda action, result, details: None,
        self_audit_factory=lambda repo_root: MagicMock(scan_once=MagicMock(return_value=0)),
    )
    supervisor._bootstrapped = True
    supervisor.claim_reddog_signed_worker_dispatch_tasks_until_idle = MagicMock(
        return_value={
            "accepted": True,
            "status": "SIGNED_WORKER_OPENCLAW_CLAIM_LOOP_ACCEPT",
            "claimed_count": 1,
            "completed_task_ids": ("task-code",),
            "failed_task_ids": (),
            "rejection_reasons": (),
        }
    )
    pending_task = {
        "task_id": "task-code",
        "discovered_by": SIGNED_WORKER_DISPATCH_TASK_SOURCE,
        "context": {
            "source": SIGNED_WORKER_DISPATCH_TASK_SOURCE,
            "worker_runtime": "0102",
            "capability": "bounded_code_change",
            "queue_item_id": "queue-1",
        },
    }

    with patch.dict(
        os.environ,
        {
            "REDDOG_RESIDENT_QUEUE_BINDING_PROFILE": "signed_0102_bounded_code_fusion",
            "REDDOG_RESIDENT_RUNTIME_ROOT": str(runtime_root),
            "REDDOG_RESIDENT_QUEUE_NOW_ISO": "2026-07-14T00:00:00+00:00",
        },
    ), patch("modules.infrastructure.database.src.agent_db.AgentDB") as mock_db:
        mock_db.return_value.get_autonomous_tasks.return_value = [pending_task]
        result = supervisor.run_cycle()

    assert result["plan"]["action"] == "claim_signed_worker_tasks_until_idle"
    supervisor.claim_reddog_signed_worker_dispatch_tasks_until_idle.assert_called_once_with(
        max_claims=1
    )
    assert result["verify"]["completed_task_ids"] == ("task-code",)


def test_run_cycle_claims_queue_stage_progress_task_with_profile_runtime_paths(tmp_path):
    from modules.communication.moltbot_bridge.src.reddog_openclaw_hermes_0102_worker_dispatch_runtime import (
        SIGNED_WORKER_DISPATCH_TASK_SOURCE,
    )

    repo = tmp_path / "repo"
    repo.mkdir()
    runtime_root = tmp_path / "resident-runtime"
    _write_runtime_queue_state(runtime_root, accepted_through="bounded_worker_pilot")
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
        "next_cursor": 13,
        "latest_sequence_id": 13,
    }
    supervisor = OpenClawSupervisor(
        repo_root=repo,
        broker=broker,
        observer=observer,
        action_reporter=lambda action, result, details: None,
        self_audit_factory=lambda repo_root: MagicMock(scan_once=MagicMock(return_value=0)),
    )
    supervisor._bootstrapped = True
    supervisor.claim_reddog_signed_worker_dispatch_tasks_until_idle = MagicMock(
        return_value={
            "accepted": True,
            "status": "SIGNED_WORKER_OPENCLAW_CLAIM_LOOP_ACCEPT",
            "claimed_count": 1,
            "completed_task_ids": ("task-stage",),
            "failed_task_ids": (),
            "rejection_reasons": (),
        }
    )
    pending_task = {
        "task_id": "task-stage",
        "discovered_by": SIGNED_WORKER_DISPATCH_TASK_SOURCE,
        "context": {
            "source": SIGNED_WORKER_DISPATCH_TASK_SOURCE,
            "worker_runtime": "openclaw",
            "capability": "queue_stage_progress",
            "queue_item_id": "queue-1",
        },
    }

    with patch.dict(
        os.environ,
        {
            "REDDOG_RESIDENT_QUEUE_BINDING_PROFILE": "signed_0102_bounded_code_fusion_worktree_draft_pr",
            "REDDOG_RESIDENT_RUNTIME_ROOT": str(runtime_root),
            "REDDOG_RESIDENT_QUEUE_NOW_ISO": "2026-07-14T00:00:00+00:00",
        },
    ), patch("modules.infrastructure.database.src.agent_db.AgentDB") as mock_db:
        mock_db.return_value.get_autonomous_tasks.return_value = [pending_task]
        result = supervisor.run_cycle()

    assert result["plan"]["action"] == "claim_signed_worker_tasks_until_idle"
    supervisor.claim_reddog_signed_worker_dispatch_tasks_until_idle.assert_called_once_with(
        max_claims=1
    )
    assert result["verify"]["completed_task_ids"] == ("task-stage",)


def test_run_cycle_does_not_claim_queue_stage_task_when_profile_runtime_files_missing(tmp_path):
    from modules.communication.moltbot_bridge.src.reddog_openclaw_hermes_0102_worker_dispatch_runtime import (
        SIGNED_WORKER_DISPATCH_TASK_SOURCE,
    )

    repo = tmp_path / "repo"
    repo.mkdir()
    runtime_root = tmp_path / "resident-runtime"
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
        "next_cursor": 14,
        "latest_sequence_id": 14,
    }
    supervisor = OpenClawSupervisor(
        repo_root=repo,
        broker=broker,
        observer=observer,
        action_reporter=lambda action, result, details: None,
        self_audit_factory=lambda repo_root: MagicMock(scan_once=MagicMock(return_value=0)),
    )
    supervisor._bootstrapped = True
    supervisor.claim_reddog_signed_worker_dispatch_tasks_until_idle = MagicMock()
    pending_task = {
        "task_id": "task-stage-missing",
        "discovered_by": SIGNED_WORKER_DISPATCH_TASK_SOURCE,
        "context": {
            "source": SIGNED_WORKER_DISPATCH_TASK_SOURCE,
            "worker_runtime": "openclaw",
            "capability": "queue_stage_progress",
            "queue_item_id": "queue-1",
        },
    }

    with patch.dict(
        os.environ,
        {
            "REDDOG_RESIDENT_QUEUE_BINDING_PROFILE": "signed_0102_bounded_code_fusion_worktree_draft_pr",
            "REDDOG_RESIDENT_RUNTIME_ROOT": str(runtime_root),
            "REDDOG_RESIDENT_QUEUE_NOW_ISO": "2026-07-14T00:00:00+00:00",
            "OPENCLAW_AUTO_TASKS_ENABLED": "0",
        },
    ), patch("modules.infrastructure.database.src.agent_db.AgentDB") as mock_db:
        mock_db.return_value.get_autonomous_tasks.return_value = [pending_task]
        result = supervisor.run_cycle()

    assert result["triage"]["kind"] == "idle"
    supervisor.claim_reddog_signed_worker_dispatch_tasks_until_idle.assert_not_called()


def test_run_cycle_explicit_zero_disables_profile_signed_worker_loop(tmp_path):
    from modules.communication.moltbot_bridge.src.reddog_openclaw_hermes_0102_worker_dispatch_runtime import (
        SIGNED_WORKER_DISPATCH_TASK_SOURCE,
    )

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
        "next_cursor": 10,
        "latest_sequence_id": 10,
    }
    supervisor = OpenClawSupervisor(
        repo_root=tmp_path,
        broker=broker,
        observer=observer,
        action_reporter=lambda action, result, details: None,
        self_audit_factory=lambda repo_root: MagicMock(scan_once=MagicMock(return_value=0)),
    )
    supervisor._bootstrapped = True
    supervisor.claim_reddog_signed_worker_dispatch_tasks_until_idle = MagicMock()
    pending_task = {
        "task_id": "task-profile-disabled",
        "discovered_by": SIGNED_WORKER_DISPATCH_TASK_SOURCE,
        "context": {
            "source": SIGNED_WORKER_DISPATCH_TASK_SOURCE,
            "worker_runtime": "openclaw",
            "capability": "candidate_queue_review",
        },
    }

    with patch.dict(
        os.environ,
        {
            "REDDOG_RESIDENT_QUEUE_BINDING_PROFILE": "signed_0102_bounded_code_fusion_worktree_draft_pr",
            "OPENCLAW_SIGNED_WORKER_TASKS_ENABLED": "0",
            "OPENCLAW_AUTO_TASKS_ENABLED": "0",
        },
    ), patch("modules.infrastructure.database.src.agent_db.AgentDB") as mock_db:
        mock_db.return_value.get_autonomous_tasks.return_value = [pending_task]
        result = supervisor.run_cycle()

    assert result["triage"]["kind"] == "idle"
    supervisor.claim_reddog_signed_worker_dispatch_tasks_until_idle.assert_not_called()


def test_run_cycle_claims_signed_0102_readonly_tasks_when_readonly_gate_enabled(tmp_path):
    from modules.communication.moltbot_bridge.src.reddog_openclaw_hermes_0102_worker_dispatch_runtime import (
        SIGNED_WORKER_DISPATCH_TASK_SOURCE,
    )

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
        "next_cursor": 11,
        "latest_sequence_id": 11,
    }

    supervisor = OpenClawSupervisor(
        repo_root=tmp_path,
        broker=broker,
        observer=observer,
        action_reporter=lambda action, result, details: None,
        self_audit_factory=lambda repo_root: MagicMock(scan_once=MagicMock(return_value=0)),
    )
    supervisor._bootstrapped = True
    supervisor.claim_reddog_signed_worker_dispatch_tasks_until_idle = MagicMock(
        return_value={
            "accepted": True,
            "status": "SIGNED_WORKER_OPENCLAW_CLAIM_LOOP_ACCEPT",
            "claimed_count": 1,
            "completed_task_ids": ("task-0102",),
            "failed_task_ids": (),
            "rejection_reasons": (),
        }
    )
    pending_task = {
        "task_id": "task-0102",
        "discovered_by": SIGNED_WORKER_DISPATCH_TASK_SOURCE,
        "context": {
            "source": SIGNED_WORKER_DISPATCH_TASK_SOURCE,
            "worker_runtime": "0102",
            "capability": "architect_review",
        },
    }

    with patch.dict(
        os.environ,
        {
            "OPENCLAW_SIGNED_WORKER_TASKS_ENABLED": "1",
            "OPENCLAW_SIGNED_0102_READONLY_TASKS_ENABLED": "1",
            "OPENCLAW_SIGNED_WORKER_TASK_MAX_CLAIMS": "1",
        },
    ), patch("modules.infrastructure.database.src.agent_db.AgentDB") as mock_db:
        mock_db.return_value.get_autonomous_tasks.return_value = [pending_task]
        result = supervisor.run_cycle()

    assert result["plan"]["action"] == "claim_signed_worker_tasks_until_idle"
    assert result["plan"]["max_claims"] == 1
    supervisor.claim_reddog_signed_worker_dispatch_tasks_until_idle.assert_called_once_with(
        max_claims=1
    )
    assert result["verify"]["ok"] is True
    assert result["verify"]["completed_task_ids"] == ("task-0102",)


def test_run_cycle_signed_worker_loop_rejects_invalid_max_claims(tmp_path):
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
        "next_cursor": 11,
        "latest_sequence_id": 11,
    }

    supervisor = OpenClawSupervisor(
        repo_root=tmp_path,
        broker=broker,
        observer=observer,
        action_reporter=lambda action, result, details: None,
        self_audit_factory=lambda repo_root: MagicMock(scan_once=MagicMock(return_value=0)),
    )
    supervisor._bootstrapped = True
    supervisor.claim_reddog_signed_worker_dispatch_tasks_until_idle = MagicMock()

    with patch.dict(
        os.environ,
        {
            "OPENCLAW_SIGNED_WORKER_TASKS_ENABLED": "1",
            "OPENCLAW_SIGNED_WORKER_TASK_MAX_CLAIMS": "0",
        },
    ):
        result = supervisor.run_cycle()

    assert result["triage"]["kind"] == "escalate"
    assert result["triage"]["reason"] == "REJECT_REDDOG_SIGNED_WORKER_CLAIM_LOOP_MAX_CLAIMS_INVALID"
    assert result["verify"]["ok"] is False
    supervisor.claim_reddog_signed_worker_dispatch_tasks_until_idle.assert_not_called()


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


# --------------------------------------------------------------------------- #
#  AI Overseer analysis tests (P1 closure)                                     #
# --------------------------------------------------------------------------- #


def test_plan_ai_analysis_normal_shape(tmp_path):
    """Normal analysis shape with classification.complexity populates ai_analysis."""
    from unittest.mock import patch

    broker = MagicMock()
    broker.get_runtime_status.return_value = {
        "registered": True, "running": True, "state": "running", "last_error": "", "enabled": True,
    }
    observer = MagicMock()
    observer.get_live_status.return_value = {"registered": True}
    observer.follow_events.return_value = {"events": [], "next_cursor": 0, "latest_sequence_id": 0}

    # Mock AI Overseer with normal shape BEFORE supervisor init
    mock_overseer = MagicMock()
    mock_overseer.analyze_mission_requirements.return_value = {
        "method": "gemma_fast_classification",
        "classification": {"complexity": 4, "category": "refactoring"},
        "patterns_detected": ["wsp_violation", "test_gap"],
        "recommended_team": {"lead": "qwen", "support": ["gemma"]},
    }

    supervisor = OpenClawSupervisor(
        repo_root=tmp_path,
        broker=broker,
        observer=observer,
        action_reporter=lambda a, r, d: None,
        self_audit_factory=lambda repo_root: MagicMock(),
    )
    # Skip bootstrap to prevent _init_unified_components from overwriting mock
    supervisor._bootstrapped = True
    supervisor._ai_overseer = mock_overseer

    # Provide a pending task to trigger PLAN state (not idle)
    # Enable auto-tasks circuit breaker for test
    pending_task = {"task_id": "test_001", "prompt": "test", "status": "pending"}
    with patch.dict(os.environ, {"OPENCLAW_AUTO_TASKS_ENABLED": "1"}), \
         patch("modules.infrastructure.database.src.agent_db.AgentDB") as mock_db:
        mock_db.return_value.get_autonomous_tasks.return_value = [pending_task]
        mock_db.return_value.assign_autonomous_task.return_value = True
        result = supervisor.run_cycle()

    ai_analysis = result["plan"].get("ai_analysis", {})
    assert ai_analysis.get("complexity") == 4
    assert ai_analysis.get("patterns") == ["wsp_violation", "test_gap"]
    assert ai_analysis.get("recommended_team") == {"lead": "qwen", "support": ["gemma"]}
    assert ai_analysis.get("method") == "gemma_fast_classification"
    assert "error" not in ai_analysis


def test_plan_ai_analysis_fallback_shape(tmp_path):
    """Fallback shape with top-level complexity populates nonzero ai_analysis.complexity."""
    from unittest.mock import patch

    broker = MagicMock()
    broker.get_runtime_status.return_value = {
        "registered": True, "running": True, "state": "running", "last_error": "", "enabled": True,
    }
    observer = MagicMock()
    observer.get_live_status.return_value = {"registered": True}
    observer.follow_events.return_value = {"events": [], "next_cursor": 0, "latest_sequence_id": 0}

    # Mock AI Overseer with fallback shape (no classification object)
    mock_overseer = MagicMock()
    mock_overseer.analyze_mission_requirements.return_value = {
        "method": "fallback",
        "mission_type": "custom",
        "complexity": 3,  # top-level, not nested
        "requires_coordination": True,
    }

    supervisor = OpenClawSupervisor(
        repo_root=tmp_path,
        broker=broker,
        observer=observer,
        action_reporter=lambda a, r, d: None,
        self_audit_factory=lambda repo_root: MagicMock(),
    )
    # Skip bootstrap to prevent _init_unified_components from overwriting mock
    supervisor._bootstrapped = True
    supervisor._ai_overseer = mock_overseer

    # Provide a pending task to trigger PLAN state (not idle)
    # Enable auto-tasks circuit breaker for test
    pending_task = {"task_id": "test_002", "prompt": "test", "status": "pending"}
    with patch.dict(os.environ, {"OPENCLAW_AUTO_TASKS_ENABLED": "1"}), \
         patch("modules.infrastructure.database.src.agent_db.AgentDB") as mock_db:
        mock_db.return_value.get_autonomous_tasks.return_value = [pending_task]
        mock_db.return_value.assign_autonomous_task.return_value = True
        result = supervisor.run_cycle()

    ai_analysis = result["plan"].get("ai_analysis", {})
    assert ai_analysis.get("complexity") == 3, "Fallback complexity=3 must not degrade to 0"
    assert ai_analysis.get("requires_coordination") is True
    assert ai_analysis.get("method") == "fallback"
    assert "error" not in ai_analysis


def test_plan_ai_analysis_exception_stores_error(tmp_path):
    """Exception in AI Overseer stores error in ai_analysis, plan still succeeds."""
    from unittest.mock import patch

    broker = MagicMock()
    broker.get_runtime_status.return_value = {
        "registered": True, "running": True, "state": "running", "last_error": "", "enabled": True,
    }
    observer = MagicMock()
    observer.get_live_status.return_value = {"registered": True}
    observer.follow_events.return_value = {"events": [], "next_cursor": 0, "latest_sequence_id": 0}

    # Mock AI Overseer that raises
    mock_overseer = MagicMock()
    mock_overseer.analyze_mission_requirements.side_effect = RuntimeError("Holo unavailable")

    supervisor = OpenClawSupervisor(
        repo_root=tmp_path,
        broker=broker,
        observer=observer,
        action_reporter=lambda a, r, d: None,
        self_audit_factory=lambda repo_root: MagicMock(),
    )
    # Skip bootstrap to prevent _init_unified_components from overwriting mock
    supervisor._bootstrapped = True
    supervisor._ai_overseer = mock_overseer

    # Provide a pending task to trigger PLAN state (not idle)
    # Enable auto-tasks circuit breaker for test
    pending_task = {"task_id": "test_003", "prompt": "test", "status": "pending"}
    with patch.dict(os.environ, {"OPENCLAW_AUTO_TASKS_ENABLED": "1"}), \
         patch("modules.infrastructure.database.src.agent_db.AgentDB") as mock_db:
        mock_db.return_value.get_autonomous_tasks.return_value = [pending_task]
        mock_db.return_value.assign_autonomous_task.return_value = True
        result = supervisor.run_cycle()

    ai_analysis = result["plan"].get("ai_analysis", {})
    assert "error" in ai_analysis
    assert "Holo unavailable" in ai_analysis["error"]
    # Plan should still complete even with AI analysis error
    assert result["plan"]["action"] == "execute_autonomous_task"


# --------------------------------------------------------------------------- #
#  Supervisor Memory Nudge Tests                                               #
# --------------------------------------------------------------------------- #


def test_verify_failure_emits_nudge(tmp_path):
    """Verify failure emits a memory nudge with breadcrumb recording."""
    nudge_calls = []

    class MockNudgeEngine:
        def __init__(self, repo_root=None, **kwargs):
            self.repo_root = repo_root

        def emit_nudges(self, events, record_breadcrumbs=False):
            nudge_calls.append({
                "events": events,
                "record_breadcrumbs": record_breadcrumbs,
            })
            # Simulate note creation
            return [tmp_path / "mock_note.md"]

    broker = MagicMock()
    # Always return stopped to force start attempt, then verify failure
    broker.get_runtime_status.return_value = {
        "registered": True,
        "running": False,
        "state": "stopped",
        "last_error": "still down",
        "enabled": True,
    }
    broker.start_dae.return_value = {"status": "starting"}

    observer = MagicMock()
    observer.get_live_status.return_value = {"registered": True}
    observer.follow_events.return_value = {
        "events": [],
        "next_cursor": 0,
        "latest_sequence_id": 0,
    }

    supervisor = OpenClawSupervisor(
        repo_root=tmp_path,
        broker=broker,
        observer=observer,
        action_reporter=lambda a, r, d: None,
        self_audit_factory=lambda repo_root: MagicMock(),
    )

    with patch(
        "modules.communication.moltbot_bridge.src.memory_nudge_engine.MemoryNudgeEngine",
        MockNudgeEngine,
    ):
        result = supervisor.run_cycle()

        # Verify failure should have occurred
        assert result["verify"]["ok"] is False
        assert supervisor.current_state == SupervisorState.ESCALATE

        # Should have emitted a nudge
        assert len(nudge_calls) == 1
        assert nudge_calls[0]["record_breadcrumbs"] is True
        event = nudge_calls[0]["events"][0]
        assert event.trigger_type == "supervisor_verify_failure"
        assert "verify failed" in event.title.lower()
        assert event.priority == "P1"


def test_escalate_budget_exhausted_emits_nudge(tmp_path, monkeypatch):
    """Restart budget exhausted escalation emits a P0 nudge."""
    monkeypatch.setenv("OPENCLAW_SUPERVISOR_MAX_RESTARTS", "2")
    monkeypatch.setenv("OPENCLAW_SUPERVISOR_RESTART_WINDOW_SEC", "600")

    nudge_calls = []

    class MockNudgeEngine:
        def __init__(self, repo_root=None, **kwargs):
            pass

        def emit_nudges(self, events, record_breadcrumbs=False):
            nudge_calls.append({
                "events": events,
                "record_breadcrumbs": record_breadcrumbs,
            })
            return [tmp_path / "mock_note.md"]

    broker = MagicMock()
    broker.get_runtime_status.return_value = {
        "registered": True,
        "running": False,
        "state": "stopped",
        "last_error": "crashed",
        "enabled": True,
    }
    observer = MagicMock()
    observer.get_live_status.return_value = {"registered": True}
    observer.follow_events.return_value = {
        "events": [],
        "next_cursor": 0,
        "latest_sequence_id": 0,
    }

    supervisor = OpenClawSupervisor(
        repo_root=tmp_path,
        broker=broker,
        observer=observer,
        action_reporter=lambda a, r, d: None,
        self_audit_factory=lambda repo_root: MagicMock(),
    )
    # Exhaust restart budget
    supervisor._restart_attempts.extend([100.0, 200.0])

    with patch(
        "modules.communication.moltbot_bridge.src.openclaw_supervisor.time.time",
        return_value=250.0,
    ), patch(
        "modules.communication.moltbot_bridge.src.memory_nudge_engine.MemoryNudgeEngine",
        MockNudgeEngine,
    ):
        result = supervisor.run_cycle()

        assert result["verify"]["error"] == "resident_openclaw_restart_budget_exhausted"
        assert supervisor.current_state == SupervisorState.ESCALATE

        # Should have emitted a P0 nudge
        assert len(nudge_calls) == 1
        event = nudge_calls[0]["events"][0]
        assert event.trigger_type == "supervisor_escalation"
        assert "budget_exhausted" in event.title
        assert event.priority == "P0"


def test_escalate_broker_unavailable_emits_nudge(tmp_path):
    """Broker unavailable escalation emits a P1 nudge."""
    nudge_calls = []

    class MockNudgeEngine:
        def __init__(self, repo_root=None, **kwargs):
            pass

        def emit_nudges(self, events, record_breadcrumbs=False):
            nudge_calls.append({
                "events": events,
                "record_breadcrumbs": record_breadcrumbs,
            })
            return [tmp_path / "mock_note.md"]

    supervisor = OpenClawSupervisor(
        repo_root=tmp_path,
        broker=MagicMock(),  # Will be overridden
        observer=MagicMock(),
        action_reporter=lambda a, r, d: None,
        self_audit_factory=lambda repo_root: MagicMock(),
    )
    # Skip normal broker initialization and force broker/observer to None
    supervisor._bootstrapped = True
    supervisor._broker = None
    supervisor._observer = None

    # Mock _get_broker and _get_observer to return None (prevents lazy init)
    supervisor._get_broker = lambda: None
    supervisor._get_observer = lambda: None

    with patch(
        "modules.communication.moltbot_bridge.src.memory_nudge_engine.MemoryNudgeEngine",
        MockNudgeEngine,
    ):
        result = supervisor.run_cycle()

        assert result["verify"]["error"] == "broker_or_observer_unavailable"
        assert supervisor.current_state == SupervisorState.ESCALATE

        # Should have emitted a P1 nudge
        assert len(nudge_calls) == 1
        event = nudge_calls[0]["events"][0]
        assert event.trigger_type == "supervisor_escalation"
        assert "broker_or_observer" in event.title
        assert event.priority == "P1"


def test_identical_escalation_dedupes(tmp_path):
    """Repeated identical escalations are deduplicated by nudge engine."""
    nudge_calls = []
    seen_signatures = set()

    class MockNudgeEngine:
        def __init__(self, repo_root=None, **kwargs):
            pass

        def emit_nudges(self, events, record_breadcrumbs=False):
            created = []
            for event in events:
                if event.signature not in seen_signatures:
                    seen_signatures.add(event.signature)
                    created.append(tmp_path / f"note_{event.signature}.md")
            nudge_calls.append({
                "events": events,
                "created": created,
            })
            return created

    supervisor = OpenClawSupervisor(
        repo_root=tmp_path,
        broker=MagicMock(),
        observer=MagicMock(),
        action_reporter=lambda a, r, d: None,
        self_audit_factory=lambda repo_root: MagicMock(),
    )
    supervisor._bootstrapped = True
    # Force broker/observer unavailable escalation
    supervisor._get_broker = lambda: None
    supervisor._get_observer = lambda: None

    with patch(
        "modules.communication.moltbot_bridge.src.memory_nudge_engine.MemoryNudgeEngine",
        MockNudgeEngine,
    ):
        # Run multiple cycles with same escalation
        supervisor.run_cycle()
        supervisor.run_cycle()
        supervisor.run_cycle()

        # Should have called emit_nudges 3 times, but only first creates note
        assert len(nudge_calls) == 3
        assert len(nudge_calls[0]["created"]) == 1  # First creates
        assert len(nudge_calls[1]["created"]) == 0  # Second dedups
        assert len(nudge_calls[2]["created"]) == 0  # Third dedups


def test_different_task_failures_produce_different_signatures(tmp_path):
    """Different task failures produce different nudge signatures (not over-deduplicated)."""
    emitted_events = []

    class MockNudgeEngine:
        def __init__(self, repo_root=None, **kwargs):
            pass

        def emit_nudges(self, events, record_breadcrumbs=False):
            emitted_events.extend(events)
            return [tmp_path / f"note_{len(emitted_events)}.md"]

    broker = MagicMock()
    broker.get_runtime_status.return_value = {
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

    supervisor = OpenClawSupervisor(
        repo_root=tmp_path,
        broker=broker,
        observer=observer,
        action_reporter=lambda a, r, d: None,
        self_audit_factory=lambda repo_root: MagicMock(),
    )
    supervisor._bootstrapped = True

    # Create two different task failures
    task1 = {"task_id": "grant_watchlist_review", "description": "Review grants"}
    task2 = {"task_id": "pqn_watchlist_review", "description": "Review PQN"}

    # Enable auto-tasks circuit breaker for test
    with patch.dict(os.environ, {"OPENCLAW_AUTO_TASKS_ENABLED": "1"}), \
         patch(
        "modules.communication.moltbot_bridge.src.memory_nudge_engine.MemoryNudgeEngine",
        MockNudgeEngine,
    ), patch("modules.infrastructure.database.src.agent_db.AgentDB") as mock_db:
        # First cycle: task1 fails
        mock_db.return_value.get_autonomous_tasks.side_effect = [
            [task1],  # pending
            [],  # completed (task not there = failure)
        ]
        mock_db.return_value.assign_autonomous_task.return_value = True

        # Mock execute_task to return failure
        with patch(
            "modules.communication.moltbot_bridge.scripts.run_task.execute_task",
            return_value={"ok": False, "error": "task_failed"},
        ):
            supervisor.run_cycle()

        # Second cycle: task2 fails with different error
        mock_db.return_value.get_autonomous_tasks.side_effect = [
            [task2],  # pending
            [],  # completed (task not there = failure)
        ]

        with patch(
            "modules.communication.moltbot_bridge.scripts.run_task.execute_task",
            return_value={"ok": False, "error": "timeout"},
        ):
            supervisor.run_cycle()

        # Both failures should have emitted events
        assert len(emitted_events) == 2

        # Signatures should be DIFFERENT (task_id and error in title)
        sig1 = emitted_events[0].signature
        sig2 = emitted_events[1].signature
        assert sig1 != sig2, (
            f"Different task failures should have different signatures: "
            f"{emitted_events[0].title} vs {emitted_events[1].title}"
        )

        # Titles should include task_id
        assert "grant_watchlist_review" in emitted_events[0].title
        assert "pqn_watchlist_review" in emitted_events[1].title


def test_successful_cycle_does_not_emit_nudge(tmp_path):
    """Successful execution cycle does not emit any nudge."""
    nudge_calls = []

    class MockNudgeEngine:
        def __init__(self, repo_root=None, **kwargs):
            pass

        def emit_nudges(self, events, record_breadcrumbs=False):
            nudge_calls.append(events)
            return []

    broker = MagicMock()
    broker.get_runtime_status.return_value = {
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

    supervisor = OpenClawSupervisor(
        repo_root=tmp_path,
        broker=broker,
        observer=observer,
        action_reporter=lambda a, r, d: None,
        self_audit_factory=lambda repo_root: MagicMock(),
    )

    with patch(
        "modules.communication.moltbot_bridge.src.memory_nudge_engine.MemoryNudgeEngine",
        MockNudgeEngine,
    ), patch("modules.infrastructure.database.src.agent_db.AgentDB") as mock_db:
        mock_db.return_value.get_autonomous_tasks.return_value = []
        result = supervisor.run_cycle()

        # Should be idle (healthy runtime, no pending tasks)
        assert result["triage"]["kind"] == "idle"
        assert supervisor.current_state == SupervisorState.IDLE_WATCH

        # Should NOT have emitted any nudge
        assert len(nudge_calls) == 0


def test_breadcrumb_recording_invoked_on_nudge(tmp_path):
    """Breadcrumb recording is invoked when nudge is emitted."""
    breadcrumb_recorded = []

    class MockNudgeEngine:
        def __init__(self, repo_root=None, **kwargs):
            pass

        def emit_nudges(self, events, record_breadcrumbs=False):
            if record_breadcrumbs:
                breadcrumb_recorded.append(True)
            return [tmp_path / "note.md"]

    supervisor = OpenClawSupervisor(
        repo_root=tmp_path,
        broker=MagicMock(),
        observer=MagicMock(),
        action_reporter=lambda a, r, d: None,
        self_audit_factory=lambda repo_root: MagicMock(),
    )
    supervisor._bootstrapped = True
    # Force broker/observer unavailable escalation
    supervisor._get_broker = lambda: None
    supervisor._get_observer = lambda: None

    with patch(
        "modules.communication.moltbot_bridge.src.memory_nudge_engine.MemoryNudgeEngine",
        MockNudgeEngine,
    ):
        supervisor.run_cycle()

        # Should have recorded breadcrumb
        assert len(breadcrumb_recorded) == 1
        assert breadcrumb_recorded[0] is True


# --------------------------------------------------------------------------- #
#  Self-Audit Triage Path Tests                                                #
# --------------------------------------------------------------------------- #


def test_self_audit_triage_returns_execute_action(tmp_path):
    """Self-audit event from JSONL triggers execute_self_audit_fix action."""
    import json

    broker = MagicMock()
    broker.get_runtime_status.return_value = {
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

    # Create a mock self-audit loop with a JSONL file containing pending events
    audit_loop = MagicMock()
    audit_loop.allowed_fixes = {"start_ironclaw_gateway", "diagnose_microphone_device"}
    audit_loop.scan_once.return_value = 0  # No new events in this scan
    audit_loop._apply_policy_fix.return_value = (True, "start_command_dispatched")

    # Create JSONL with a pending event that has an allowed fix
    task_log = tmp_path / "daemon_self_audit_tasks.jsonl"
    event = {
        "timestamp": 1700000000,
        "source_file": "/logs/test.log",
        "signature": "ironclaw runtime is unavailable",
        "line": "[ERROR] IronClaw runtime is unavailable",
        "recommended_fix": "start_ironclaw_gateway",
        "auto_fix_attempted": False,
        "auto_fix_result": "not_attempted",
    }
    task_log.write_text(json.dumps(event) + "\n", encoding="utf-8")
    audit_loop.task_log_path = task_log

    supervisor = OpenClawSupervisor(
        repo_root=tmp_path,
        broker=broker,
        observer=observer,
        action_reporter=lambda a, r, d: None,
        self_audit_factory=lambda repo_root: audit_loop,
    )

    with patch.dict(os.environ, {"OPENCLAW_SELF_AUDIT_ENABLED": "1"}), \
         patch("modules.infrastructure.database.src.agent_db.AgentDB") as mock_db:
        mock_db.return_value.get_autonomous_tasks.return_value = []
        result = supervisor.run_cycle()

    # Should have triggered execute_self_audit_fix action
    # When action is taken, result has "plan" instead of "triage"
    assert "plan" in result
    assert result["plan"]["action"] == "execute_self_audit_fix"
    assert result["plan"]["recommended_fix"] == "start_ironclaw_gateway"
    assert "ironclaw" in result["plan"]["event_signature"]
    # Verify the execution happened
    assert result["action_result"]["ok"] is True


def test_self_audit_triage_skips_already_attempted(tmp_path):
    """Self-audit events that were already attempted are skipped."""
    import json

    broker = MagicMock()
    broker.get_runtime_status.return_value = {
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

    audit_loop = MagicMock()
    audit_loop.allowed_fixes = {"start_ironclaw_gateway"}
    audit_loop.scan_once.return_value = 0

    # Create JSONL with an already-attempted event
    task_log = tmp_path / "daemon_self_audit_tasks.jsonl"
    event = {
        "timestamp": 1700000000,
        "source_file": "/logs/test.log",
        "signature": "ironclaw runtime is unavailable",
        "line": "[ERROR] IronClaw runtime is unavailable",
        "recommended_fix": "start_ironclaw_gateway",
        "auto_fix_attempted": True,  # Already attempted
        "auto_fix_result": "start_command_dispatched",
    }
    task_log.write_text(json.dumps(event) + "\n", encoding="utf-8")
    audit_loop.task_log_path = task_log

    supervisor = OpenClawSupervisor(
        repo_root=tmp_path,
        broker=broker,
        observer=observer,
        action_reporter=lambda a, r, d: None,
        self_audit_factory=lambda repo_root: audit_loop,
    )

    with patch.dict(os.environ, {"OPENCLAW_SELF_AUDIT_ENABLED": "1"}), \
         patch("modules.infrastructure.database.src.agent_db.AgentDB") as mock_db:
        mock_db.return_value.get_autonomous_tasks.return_value = []
        result = supervisor.run_cycle()

    # Should idle because all events were already attempted
    assert result["triage"]["kind"] == "idle"


def test_self_audit_triage_ignores_non_allowed_fixes(tmp_path):
    """Self-audit events with non-allowed fixes are ignored."""
    import json

    broker = MagicMock()
    broker.get_runtime_status.return_value = {
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

    audit_loop = MagicMock()
    audit_loop.allowed_fixes = {"start_ironclaw_gateway"}  # inspect_log not allowed
    audit_loop.scan_once.return_value = 0

    # Create JSONL with an event that recommends a non-allowed fix
    task_log = tmp_path / "daemon_self_audit_tasks.jsonl"
    event = {
        "timestamp": 1700000000,
        "source_file": "/logs/test.log",
        "signature": "random error pattern",
        "line": "[ERROR] Something went wrong",
        "recommended_fix": "inspect_log_and_create_patch_task",  # Not in allowed_fixes
        "auto_fix_attempted": False,
        "auto_fix_result": "not_attempted",
    }
    task_log.write_text(json.dumps(event) + "\n", encoding="utf-8")
    audit_loop.task_log_path = task_log

    supervisor = OpenClawSupervisor(
        repo_root=tmp_path,
        broker=broker,
        observer=observer,
        action_reporter=lambda a, r, d: None,
        self_audit_factory=lambda repo_root: audit_loop,
    )

    with patch.dict(os.environ, {"OPENCLAW_SELF_AUDIT_ENABLED": "1"}), \
         patch("modules.infrastructure.database.src.agent_db.AgentDB") as mock_db:
        mock_db.return_value.get_autonomous_tasks.return_value = []
        result = supervisor.run_cycle()

    # Should idle because the fix is not in allowed_fixes
    assert result["triage"]["kind"] == "idle"


# --------------------------------------------------------------------------- #
#  End-to-End Maintenance Loop Tests                                           #
# --------------------------------------------------------------------------- #


def test_maintenance_loop_e2e_self_audit_via_agentdb(tmp_path, monkeypatch):
    """End-to-end: AgentDB task with source=self_audit flows through run_task.py."""
    import uuid

    # Set up test environment
    monkeypatch.setenv("OPENCLAW_MAINTENANCE_ENABLED", "1")
    monkeypatch.setenv("OPENCLAW_SELF_AUDIT_ENABLED", "0")  # Disable JSONL path for this test

    broker = MagicMock()
    broker.get_runtime_status.return_value = {
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

    # Create a real AgentDB task with source=self_audit
    task_id = f"e2e-test-{uuid.uuid4().hex[:8]}"
    pending_task = {
        "task_id": task_id,
        "description": "Apply policy fix for IronClaw gateway",
        "status": "pending",
        "required_skills": [],
        "context": {
            "source": "self_audit",
            "context": {"recommended_fix": "start_ironclaw_gateway"},
        },
    }

    # Mock the supervisor's components
    supervisor = OpenClawSupervisor(
        repo_root=tmp_path,
        broker=broker,
        observer=observer,
        action_reporter=lambda a, r, d: None,
        self_audit_factory=lambda repo_root: MagicMock(scan_once=MagicMock(return_value=0)),
    )

    # Mock AgentDB to return our task
    with patch("modules.infrastructure.database.src.agent_db.AgentDB") as mock_db_class:
        mock_db = MagicMock()
        mock_db_class.return_value = mock_db

        # First call returns pending task, subsequent calls return empty
        call_count = [0]

        def get_tasks_side_effect(status=None, limit=None):
            call_count[0] += 1
            if status == "pending" and call_count[0] == 1:
                return [pending_task]
            if status == "assigned":
                # run_task.py looks for assigned tasks
                return [dict(pending_task, status="assigned")]
            return []

        mock_db.get_autonomous_tasks.side_effect = get_tasks_side_effect
        mock_db.assign_autonomous_task.return_value = True
        mock_db.complete_autonomous_task.return_value = True

        # Mock the DaemonSelfAuditLoop for run_task.py dispatch
        with patch(
            "modules.infrastructure.wre_core.src.daemon_self_audit_loop.DaemonSelfAuditLoop"
        ) as mock_audit_loop:
            mock_loop_instance = MagicMock()
            mock_loop_instance._apply_policy_fix.return_value = (True, "start_command_dispatched")
            mock_audit_loop.return_value = mock_loop_instance

            result = supervisor.run_cycle()

    # Verify the maintenance task was selected and executed
    assert "plan" in result
    assert result["plan"]["action"] == "execute_maintenance_task"
    assert result["plan"]["task"]["family"] == "self_audit_fix"
    assert result["action_result"]["ok"] is True
    assert "self_audit" in result["action_result"]["executor"]


def test_supervisor_action_reporter_recursively_redacts_nested_secrets(tmp_path):
    reports = []
    supervisor = OpenClawSupervisor(
        tmp_path,
        action_reporter=lambda action, result, details: reports.append(
            (action, result, details)
        ),
    )
    secrets = (
        "openrouter-secret-value",
        "bearer-secret-value",
        "query-secret-value",
        "opaque-token-value",
    )

    supervisor._action_reporter(
        "supervisor_test",
        "Authorization: Bearer bearer-secret-value",
        {
            "OPENROUTER_API_KEY": secrets[0],
            "nested": {
                "header": "Authorization: Bearer bearer-secret-value",
                "url": "https://example.test/?token=query-secret-value",
                "token": "opaque-token-value",
            },
        },
    )

    serialized = json.dumps(reports, default=str)
    for secret in secrets:
        assert secret not in serialized
    assert "[REDACTED]" in serialized


def test_supervisor_pattern_memory_receives_redacted_context_only(tmp_path):
    class _Memory:
        def __init__(self):
            self.outcomes = []

        def store_outcome(self, outcome):
            self.outcomes.append(outcome)

    supervisor = OpenClawSupervisor(tmp_path, action_reporter=lambda *_: None)
    memory = _Memory()
    supervisor._pattern_memory = memory
    with patch.object(supervisor, "_record_continuity_breadcrumb"):
        supervisor._remember(
            {},
            {"action": "test", "detail": "AWS_SECRET_ACCESS_KEY=aws-secret-value"},
            {
                "ok": True,
                "detail": "Cookie: session=second-cookie-secret",
                "token": "pattern-memory-token",
            },
            {"ok": True, "fidelity": 1.0},
        )

    assert len(memory.outcomes) == 1
    serialized = json.dumps(memory.outcomes[0].__dict__, default=str)
    assert "aws-secret-value" not in serialized
    assert "second-cookie-secret" not in serialized
    assert "pattern-memory-token" not in serialized
    assert "[REDACTED]" in serialized
