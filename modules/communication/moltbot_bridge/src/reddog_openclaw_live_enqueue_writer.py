"""Concrete OpenClaw live enqueue writer for RedDog.

Slice: REDDOG_OPENCLAW_LIVE_ENQUEUE_WRITER_ADAPTER_PHASE1

This adapter implements the writer protocol consumed by
`perform_reddog_openclaw_live_enqueue`. It writes only the queue/task intake record:

- `foundup_job` -> append a typed FoundUpJob to OpenClaw's in-memory queue.
- `autonomous_task` -> call AgentDB.create_autonomous_task().

It does NOT execute queued tasks, dispatch Hermes/WRE, create worktrees, edit files,
create PRs, push, merge, or settle rewards.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, Mapping, Optional

from modules.communication.moltbot_bridge.src.foundup_job_contract import FoundUpJob
from modules.communication.moltbot_bridge.src.openclaw_foundup_orchestrator import get_job_queue


def _safe_str(value: Any, default: str = "") -> str:
    text = str(value or "").strip()
    return text or default


def _payload(intake: Mapping[str, Any], receipt: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "source": "reddog_openclaw_live_enqueue",
        "proposed_intake": dict(intake),
        "live_enqueue_receipt": dict(receipt),
        "no_execution_performed": True,
        "no_reward_settlement_performed": True,
    }


class OpenClawLiveEnqueueWriter:
    """Concrete queue writer. Construction is side-effect free.

    `agent_db_factory` is injectable so tests can avoid touching the real DB while the
    production adapter can construct AgentDB lazily only when autonomous_task is used.
    """

    def __init__(self, agent_db_factory: Optional[Callable[[], Any]] = None) -> None:
        self._agent_db_factory = agent_db_factory

    def enqueue_foundup_job(self, intake: Mapping[str, Any], receipt: Mapping[str, Any]) -> Mapping[str, Any]:
        job_id = _safe_str(intake.get("proposed_job_id"))
        if not job_id:
            return {"ok": False, "reason": "missing_proposed_job_id"}

        job = FoundUpJob(
            job_id=job_id,
            tenant_id="reddog",
            foundup_id=None,
            intent_id=_safe_str(intake.get("work_order_id"), default=job_id),
            requested_action=_safe_str(intake.get("requested_action"), default="validate_foundup"),
            payload=_payload(intake, receipt),
        )
        job.status_reason_human = "RedDog live enqueue created FoundUpJob; execution not started."
        job.evidence_refs = list(intake.get("evidence_refs") or [])
        get_job_queue().append(job)
        return {"ok": True, "openclaw_queue_item_id": job.job_id, "agentdb_task_id": None}

    def enqueue_autonomous_task(self, intake: Mapping[str, Any], receipt: Mapping[str, Any]) -> Mapping[str, Any]:
        task_id = _safe_str(intake.get("proposed_task_id"))
        if not task_id:
            return {"ok": False, "reason": "missing_proposed_task_id"}

        factory = self._agent_db_factory
        if factory is None:
            from modules.infrastructure.database.src.agent_db import AgentDB

            factory = AgentDB

        db = factory()
        ok = db.create_autonomous_task(
            task_id=task_id,
            description=f"RedDog live enqueue for {_safe_str(intake.get('work_order_id'), default=task_id)}",
            required_skills=["reddog_work_order"],
            estimated_complexity=0.5,
            priority_score=1.0,
            context=_payload(intake, receipt),
            origin_continuity_id=_safe_str(intake.get("work_order_id")) or None,
        )
        return {
            "ok": bool(ok),
            "openclaw_queue_item_id": None,
            "agentdb_task_id": task_id if ok else None,
        }


__all__ = ["OpenClawLiveEnqueueWriter"]
