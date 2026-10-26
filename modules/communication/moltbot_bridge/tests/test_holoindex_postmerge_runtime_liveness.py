"""Exact-task and resident-runtime liveness regressions."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import pytest

from modules.communication.moltbot_bridge.src.holoindex_postmerge_runtime_liveness import (
    holoindex_postmerge_runtime_rejection,
)
from modules.infrastructure.database.src.holoindex_postmerge_claim_contract import (
    build_holoindex_postmerge_claim_context,
)
from modules.infrastructure.idle_automation.src.holoindex_postmerge_contract import (
    CLAIM_AGENT_ID,
    SCHEMA_VERSION,
    SOURCE,
    REQUEST_EVENT_PREFIX,
    TASK_PREFIX,
)


HEAD = "a" * 40
TASK_ID = TASK_PREFIX + HEAD
AUTHORITY_DIGEST = "sha256:" + ("b" * 64)


class _Broker:
    def __init__(self) -> None:
        self.statuses = {
            runtime_id: {
                "registered": True, "running": True, "thread_alive": True,
                "state": "running", "last_error": "",
            }
            for runtime_id in ("openclaw", "openclaw_supervisor")
        }

    def get_runtime_status(self, runtime_id: str) -> dict[str, Any]:
        return dict(self.statuses[runtime_id])


class _Database:
    def __init__(self, task: dict[str, Any] | None) -> None:
        self.task = task

    def get_autonomous_task_by_id(self, task_id: str) -> dict[str, Any] | None:
        assert task_id == TASK_ID
        return self.task


def _task(
    status: str = "pending", *, issued_at: datetime | None = None,
    lease_seconds: int = 3600,
) -> dict[str, Any]:
    assigned = CLAIM_AGENT_ID if status in {
        "assigned", "executing", "completed", "failed", "superseded",
    } else ""
    context = {
        "schema_version": SCHEMA_VERSION,
        "source": SOURCE,
        "target_repo_head_sha": HEAD,
        "authority_root_digest": AUTHORITY_DIGEST,
        "request_event_id": REQUEST_EVENT_PREFIX + HEAD,
    }
    task = {
        "task_id": TASK_ID,
        "status": status,
        "assigned_to": assigned,
        "required_skills": ["holo-search"],
        "context": context,
    }
    if status in {"assigned", "executing"}:
        claimed = build_holoindex_postmerge_claim_context(
            task_id=TASK_ID,
            agent_id=CLAIM_AGENT_ID,
            base_context=context,
            claim_id="hpmc_" + ("c" * 32),
            issued_at=issued_at or datetime.now(timezone.utc),
            lease_seconds=lease_seconds,
        )
        assert claimed is not None
        task["assigned_at"] = claimed["claim_issued_at"]
        task["context"] = claimed
    return task


def test_exact_pending_task_and_both_live_runtimes_remain_admitted() -> None:
    assert holoindex_postmerge_runtime_rejection(
        _Broker(), _Database(_task()), task_id=TASK_ID, expected_head=HEAD,
        expected_authority_root_digest=AUTHORITY_DIGEST,
    ) == ""


def test_dead_runtime_rejects_before_the_controller_timeout() -> None:
    broker = _Broker()
    broker.statuses["openclaw"]["thread_alive"] = False
    assert holoindex_postmerge_runtime_rejection(
        broker, _Database(_task()), task_id=TASK_ID, expected_head=HEAD,
        expected_authority_root_digest=AUTHORITY_DIGEST,
    ) == "openclaw_not_live"


@pytest.mark.parametrize(
    ("status", "reason"),
    [
        ("failed", "postmerge_task_failed"),
        ("superseded", "postmerge_task_superseded"),
        ("retry_wait", "postmerge_task_retry_wait"),
        ("completed", "postmerge_completion_invalid"),
    ],
)
def test_nonprogressing_task_state_rejects_immediately(
    status: str, reason: str,
) -> None:
    assert holoindex_postmerge_runtime_rejection(
        _Broker(), _Database(_task(status)), task_id=TASK_ID, expected_head=HEAD,
        expected_authority_root_digest=AUTHORITY_DIGEST,
    ) == reason


def test_task_binding_drift_rejects_immediately() -> None:
    task = _task()
    task["context"]["target_repo_head_sha"] = "c" * 40
    assert holoindex_postmerge_runtime_rejection(
        _Broker(), _Database(task), task_id=TASK_ID, expected_head=HEAD,
        expected_authority_root_digest=AUTHORITY_DIGEST,
    ) == "postmerge_task_binding_invalid"


@pytest.mark.parametrize("drift", ["request_event_id", "incident_binding"])
def test_canonical_task_context_drift_rejects_immediately(drift: str) -> None:
    task = _task()
    if drift == "request_event_id":
        task["context"][drift] = "wrong"
    else:
        task["context"][drift] = {"incident_id": "untrusted"}
    assert holoindex_postmerge_runtime_rejection(
        _Broker(), _Database(task), task_id=TASK_ID, expected_head=HEAD,
        expected_authority_root_digest=AUTHORITY_DIGEST,
    ) == "postmerge_task_binding_invalid"


def test_expired_active_claim_rejects_immediately() -> None:
    task = _task(
        "executing",
        issued_at=datetime.now(timezone.utc) - timedelta(seconds=2),
        lease_seconds=1,
    )
    assert holoindex_postmerge_runtime_rejection(
        _Broker(), _Database(task), task_id=TASK_ID, expected_head=HEAD,
        expected_authority_root_digest=AUTHORITY_DIGEST,
    ) == "postmerge_task_claim_expired"


@pytest.mark.parametrize(
    "field",
    ["claim_id", "claim_issued_at", "claim_expires_at", "claim_binding_digest"],
)
def test_claim_context_tamper_rejects_immediately(field: str) -> None:
    task = _task("executing")
    task["context"][field] = "attacker"
    assert holoindex_postmerge_runtime_rejection(
        _Broker(), _Database(task), task_id=TASK_ID, expected_head=HEAD,
        expected_authority_root_digest=AUTHORITY_DIGEST,
    ) == "postmerge_task_claim_invalid"


def test_claim_assignment_time_drift_rejects_immediately() -> None:
    task = _task("executing")
    task["assigned_at"] = (
        datetime.now(timezone.utc) - timedelta(seconds=1)
    ).isoformat()
    assert holoindex_postmerge_runtime_rejection(
        _Broker(), _Database(task), task_id=TASK_ID, expected_head=HEAD,
        expected_authority_root_digest=AUTHORITY_DIGEST,
    ) == "postmerge_task_claim_invalid"


def test_wrong_assignee_rejects_immediately() -> None:
    task = _task("executing")
    task["assigned_to"] = "another_worker"
    assert holoindex_postmerge_runtime_rejection(
        _Broker(), _Database(task), task_id=TASK_ID, expected_head=HEAD,
        expected_authority_root_digest=AUTHORITY_DIGEST,
    ) == "postmerge_task_assignment_invalid"


def test_different_valid_authority_digest_rejects_immediately() -> None:
    task = _task()
    task["context"]["authority_root_digest"] = "sha256:" + ("f" * 64)
    assert holoindex_postmerge_runtime_rejection(
        _Broker(), _Database(task), task_id=TASK_ID, expected_head=HEAD,
        expected_authority_root_digest=AUTHORITY_DIGEST,
    ) == "postmerge_task_binding_invalid"
