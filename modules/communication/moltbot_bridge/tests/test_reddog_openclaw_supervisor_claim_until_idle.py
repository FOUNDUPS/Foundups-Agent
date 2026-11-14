"""Focused integration case extracted from the inherited matrix."""

from __future__ import annotations

from modules.communication.moltbot_bridge.tests.test_reddog_signed_worker_dispatch_task_executor import (
    AgentDB,
    OpenClawSupervisor,
    Path,
    SIGNED_WORKER_OPENCLAW_CLAIM_LOOP_ACCEPT,
    _FakeRunner,
    _publish_agentdb_task,
    isolated_agent_db,  # noqa: F401
)


def test_openclaw_supervisor_instance_claims_signed_worker_tasks_until_idle(
    tmp_path: Path,
) -> None:
    task_id = _publish_agentdb_task(
        intent_id="worker_dispatch_intent_openclaw_candidate_1"
    )
    supervisor = OpenClawSupervisor(repo_root=tmp_path)

    result = supervisor.claim_reddog_signed_worker_dispatch_tasks_until_idle(
        signed_worker_runner=_FakeRunner(),
        max_claims=2,
    )

    assert result["accepted"] is True
    assert result["status"] == SIGNED_WORKER_OPENCLAW_CLAIM_LOOP_ACCEPT
    assert result["completed_task_ids"] == (task_id,)
    assert result["idle"] is True
    assert AgentDB().get_autonomous_task_by_id(task_id)["status"] == "completed"
