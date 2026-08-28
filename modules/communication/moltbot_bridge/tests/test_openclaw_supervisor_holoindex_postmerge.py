"""Focused OpenClaw supervisor contracts for exact-SHA HoloIndex maintenance."""

from unittest.mock import MagicMock, patch

import pytest

from modules.communication.moltbot_bridge.src import (
    openclaw_supervisor as supervisor_module,
)
from modules.communication.moltbot_bridge.src.openclaw_supervisor import (
    OpenClawSupervisor,
)
from modules.communication.moltbot_bridge.src.holoindex_postmerge_supervisor_policy import (
    HOLOINDEX_POSTMERGE_ONLY_MODE,
    HOLOINDEX_POSTMERGE_SOURCE,
    HoloIndexPostmergePoller,
    holoindex_postmerge_only_execution_rejection,
    validate_supervisor_holoindex_postmerge_completion,
)


def test_bound_poller_never_schedules_an_independent_coordinator(
    tmp_path, monkeypatch,
):
    task_id = "holoindex_postmerge_refresh:" + ("a" * 40)
    poller = HoloIndexPostmergePoller(tmp_path, enabled=True, task_id=task_id)
    schedule = MagicMock()
    monkeypatch.setattr(poller, "_schedule", schedule)

    assert poller.poll() == {
        "accepted": True, "status": "TASK_BOUND", "rejection_reasons": [],
    }
    assert poller.task_id == task_id
    assert poller.future is None
    schedule.assert_not_called()


def test_poller_binding_is_idempotent_and_rejects_replacement(tmp_path):
    first = "holoindex_postmerge_refresh:" + ("a" * 40)
    second = "holoindex_postmerge_refresh:" + ("b" * 40)
    poller = HoloIndexPostmergePoller(tmp_path, enabled=True)

    assert poller.bind_task(first) is True
    assert poller.bind_task(first) is True
    assert poller.bind_task(second) is False
    assert poller.bind_task("not-a-task") is False
    assert poller.task_id == first


def test_poller_exact_release_allows_the_next_controller_task(tmp_path):
    first = "holoindex_postmerge_refresh:" + ("a" * 40)
    second = "holoindex_postmerge_refresh:" + ("b" * 40)
    poller = HoloIndexPostmergePoller(tmp_path, enabled=True, task_id=first)

    assert poller.release_task(second) is False
    assert poller.release_task(first) is True
    assert poller.task_id == ""
    assert poller.bind_task(second) is True


def test_supervisor_constructor_and_registration_preserve_exact_task(tmp_path):
    task_id = "holoindex_postmerge_refresh:" + ("a" * 40)
    supervisor = OpenClawSupervisor(
        repo_root=tmp_path, runtime_mode=HOLOINDEX_POSTMERGE_ONLY_MODE,
        postmerge_task_id=task_id,
    )
    assert supervisor.register_holoindex_postmerge_task(task_id) is True
    assert supervisor._holoindex_postmerge_poller.task_id == task_id
    assert supervisor.release_holoindex_postmerge_task(task_id) is True


def test_postmerge_completion_policy_requires_exact_atomic_receipt(monkeypatch):
    target_sha = "a" * 40
    task_id = "holoindex_postmerge_refresh:" + target_sha
    authority_digest = "sha256:" + ("b" * 64)
    database = MagicMock()
    database.get_autonomous_task_by_id.return_value = {
        "task_id": task_id,
        "status": "completed",
        "context": {
            "source": "holoindex_postmerge_coordinator",
            "target_repo_head_sha": target_sha,
            "authority_root_digest": authority_digest,
        },
    }
    validator = MagicMock(return_value={"status": "COMPLETED"})
    monkeypatch.setattr(
        "modules.infrastructure.idle_automation.src.holoindex_postmerge_contract."
        "validate_holoindex_postmerge_completion",
        validator,
    )

    result = validate_supervisor_holoindex_postmerge_completion(database, task_id)

    assert result == {"status": "COMPLETED"}
    validator.assert_called_once_with(
        database,
        task_id=task_id,
        target_repo_head_sha=target_sha,
        authority_root_digest=authority_digest,
    )


@pytest.mark.parametrize(
    ("task_id", "context"),
    [
        ("holoindex_postmerge_refresh:not-a-sha", {}),
        (
            "holoindex_postmerge_refresh:" + ("a" * 40),
            {
                "source": "holoindex_postmerge_coordinator",
                "target_repo_head_sha": "c" * 40,
                "authority_root_digest": "sha256:" + ("b" * 64),
            },
        ),
    ],
)
def test_postmerge_completion_policy_rejects_malformed_binding(task_id, context):
    database = MagicMock()
    database.get_autonomous_task_by_id.return_value = {"context": context}

    assert validate_supervisor_holoindex_postmerge_completion(database, task_id) is None


def test_supervisor_postmerge_verify_rejects_generic_completed_row(tmp_path):
    target_sha = "a" * 40
    task_id = "holoindex_postmerge_refresh:" + target_sha
    supervisor = OpenClawSupervisor(
        repo_root=tmp_path,
        broker=MagicMock(),
        observer=MagicMock(),
        action_reporter=lambda *_args: None,
    )
    plan = {
        "action": "execute_maintenance_task",
        "task": {"task_id": task_id, "family": "holoindex_postmerge"},
    }

    with (
        patch("modules.infrastructure.database.src.agent_db.AgentDB") as db_class,
        patch.object(
            supervisor_module,
            "verified_maintenance_task_status",
            return_value=None,
        ) as validate_status,
    ):
        db_class.return_value.get_autonomous_tasks.return_value = [
            {"task_id": task_id, "status": "completed"}
        ]
        result = supervisor._verify(plan, {"ok": True})

    assert result["ok"] is False
    assert result["task_status"] is None
    assert result["error"] == "maintenance_task_not_completed"
    validate_status.assert_called_once_with(
        db_class.return_value, task_id, "holoindex_postmerge"
    )
    db_class.return_value.get_autonomous_tasks.assert_not_called()


def test_supervisor_postmerge_verify_accepts_exact_completion_receipt(tmp_path):
    task_id = "holoindex_postmerge_refresh:" + ("a" * 40)
    supervisor = OpenClawSupervisor(
        repo_root=tmp_path,
        broker=MagicMock(),
        observer=MagicMock(),
        action_reporter=lambda *_args: None,
    )
    plan = {
        "action": "execute_maintenance_task",
        "task": {"task_id": task_id, "family": "holoindex_postmerge"},
    }

    with (
        patch("modules.infrastructure.database.src.agent_db.AgentDB"),
        patch.object(
            supervisor_module,
            "verified_maintenance_task_status",
            return_value="completed",
        ),
    ):
        result = supervisor._verify(plan, {"ok": True})

    assert result["ok"] is True
    assert result["task_status"] == "completed"
    assert result["error"] == ""


def test_holoindex_postmerge_only_mode_ignores_all_other_task_families(
    tmp_path, monkeypatch,
):
    for name in (
        "OPENCLAW_AUTO_TASKS_ENABLED",
        "OPENCLAW_MAINTENANCE_ENABLED",
        "OPENCLAW_SELF_AUDIT_ENABLED",
        "OPENCLAW_SKILL_EVOLUTION_ENABLED",
        "OPENCLAW_MUTATION_SURFACE_ENABLED",
    ):
        monkeypatch.setenv(name, "1")
    monkeypatch.setenv("HOLOINDEX_POSTMERGE_COORDINATOR_ENABLED", "0")
    signed_enabled = MagicMock(return_value=True)
    monkeypatch.setattr(
        supervisor_module, "_signed_worker_tasks_enabled_from_env", signed_enabled
    )
    task_id = "holoindex_postmerge_refresh:" + ("a" * 40)
    db = MagicMock()
    db.get_autonomous_task_by_id.return_value = {
        "task_id": task_id,
        "status": "pending",
        "description": "Refresh exact-SHA HoloIndex authority",
        "context": {
            "schema_version": "holoindex_postmerge_coordination_v1",
            "source": "holoindex_postmerge_coordinator",
        },
        "required_skills": ["holo-search"],
    }
    monkeypatch.setattr(
        "modules.infrastructure.database.src.agent_db.AgentDB", lambda: db
    )
    audit_factory = MagicMock()
    supervisor = OpenClawSupervisor(
        repo_root=tmp_path, self_audit_factory=audit_factory,
        runtime_mode=HOLOINDEX_POSTMERGE_ONLY_MODE,
    )
    supervisor._holoindex_postmerge_poller._task_id = task_id

    supervisor._start_self_audit()
    result = supervisor._triage(
        {"openclaw_runtime": {"registered": True, "running": True}}
    )

    assert supervisor.restart_enabled is False
    assert supervisor.self_audit_enabled is False
    audit_factory.assert_not_called()
    signed_enabled.assert_not_called()
    db.get_autonomous_tasks.assert_not_called()
    assert result["action"] == "execute_maintenance_task"
    assert result["task"]["family"] == "holoindex_postmerge"

    supervisor._holoindex_postmerge_poller._task_id = ""
    db.get_autonomous_task_by_id.reset_mock()
    idle = supervisor._triage(
        {"openclaw_runtime": {"registered": True, "running": True}}
    )
    assert idle == {"kind": "idle", "reason": "holoindex_postmerge_only_idle"}
    db.get_autonomous_tasks.assert_not_called()


@pytest.mark.parametrize(
    "plan",
    [
        None,
        [],
        "bad",
        7,
        {"action": "start_openclaw"},
        {"action": "claim_signed_worker_tasks_until_idle"},
        {"action": "execute_autonomous_task", "task": {"task_id": "other"}},
        {
            "action": "execute_maintenance_task",
            "task": {"task_id": "other", "family": "self_audit_fix"},
        },
        {"action": "execute_self_audit_fix", "recommended_fix": "restart"},
        {"action": "execute_maintenance_task", "task": None},
        {"action": "execute_maintenance_task", "task": []},
        {"action": "execute_maintenance_task", "task": "bad"},
        {"action": "execute_maintenance_task", "task": 7},
        {
            "action": "execute_maintenance_task",
            "task": {
                "task_id": "holoindex_postmerge_refresh:" + ("a" * 40),
                "family": "holoindex_postmerge",
                "source": "hostile",
                "context": {"source": "hostile"},
            },
        },
    ],
)
def test_holoindex_postmerge_only_execute_gate_rejects_non_holo_plans(
    tmp_path, plan,
):
    broker = MagicMock()
    supervisor = OpenClawSupervisor(
        repo_root=tmp_path, broker=broker,
        runtime_mode=HOLOINDEX_POSTMERGE_ONLY_MODE,
    )
    supervisor.claim_reddog_signed_worker_dispatch_tasks_until_idle = MagicMock()
    supervisor._self_audit_loop = MagicMock()
    supervisor._start_execution_emitter = MagicMock()

    result = supervisor._execute(plan)

    assert result == {
        "ok": False,
        "status": "rejected",
        "error": "holoindex_postmerge_only_plan_rejected",
    }
    broker.start_dae.assert_not_called()
    supervisor.claim_reddog_signed_worker_dispatch_tasks_until_idle.assert_not_called()
    supervisor._self_audit_loop._apply_policy_fix.assert_not_called()
    supervisor._start_execution_emitter.assert_not_called()


def test_holoindex_postmerge_only_execute_gate_admits_exact_family_shape(tmp_path):
    supervisor = OpenClawSupervisor(
        repo_root=tmp_path, runtime_mode=HOLOINDEX_POSTMERGE_ONLY_MODE
    )
    plan = {
        "action": "execute_maintenance_task",
        "task": {
            "task_id": "holoindex_postmerge_refresh:" + ("a" * 40),
            "family": "holoindex_postmerge",
            "source": HOLOINDEX_POSTMERGE_SOURCE,
            "context": {"source": HOLOINDEX_POSTMERGE_SOURCE},
        },
    }

    assert holoindex_postmerge_only_execution_rejection(
        enabled=True, plan=plan
    ) is None
