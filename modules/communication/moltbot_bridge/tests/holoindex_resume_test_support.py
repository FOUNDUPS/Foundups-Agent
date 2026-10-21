"""Synthetic resume fixtures; reuse existing in-memory DB and Git ports."""
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import Mock

from holo_index.authority_worktree import HoloIndexAuthoritySelection
from modules.communication.moltbot_bridge.src import reddog_holoindex_incident_repair_runtime as incident
from modules.infrastructure.idle_automation.src import holoindex_postmerge_contract as contract
from modules.infrastructure.idle_automation.src import holoindex_postmerge_coordinator as postmerge
from modules.infrastructure.idle_automation.tests.test_holoindex_postmerge_coordinator import (
    FakeDB, FakeGit, HEAD, _patch_state, _incident_binding,
)

NOW = datetime(2026, 10, 5, tzinfo=UTC)


def align_assignment_cleanup(db):
    """Align reused memory double with production task-namespace SQL cleanup."""
    for name in ("schedule_holoindex_postmerge_task_retry", "requeue_holoindex_postmerge_task"):
        original = getattr(db, name)
        def wrapped(task_id, _original=original, **kwargs):
            result = _original(task_id, **kwargs)
            if result:
                db.tasks[task_id].update(assigned_to=None, assigned_at=None)
                if db.tasks[task_id]["status"] == "pending":
                    db.tasks[task_id].update(retry_not_before=None, completed_at=None)
            return result
        setattr(db, name, wrapped)


def api():
    value = getattr(incident, "resume_holoindex_incident_repair", None)
    assert callable(value), "holoindex_persisted_resume_api_missing"
    return value


def make_case(monkeypatch, roots, status="pending", retry_count=1):
    workspace, authority = roots
    git, db = FakeGit(), FakeDB()
    align_assignment_cleanup(db)
    _patch_state(monkeypatch, authority, git)
    digest = contract.repository_root_digest(authority)
    binding = _incident_binding()
    task_id, request_id = contract.TASK_PREFIX + HEAD, contract.REQUEST_EVENT_PREFIX + HEAD
    context = dict(schema_version=contract.SCHEMA_VERSION, source=contract.SOURCE,
                   target_repo_head_sha=HEAD, authority_root_digest=digest,
                   request_event_id=request_id, retry_count=retry_count)
    db.tasks[task_id] = dict(task_id=task_id, status=status, context=context,
                            assigned_to=contract.CLAIM_AGENT_ID if status == "failed" else "",
                            required_skills=["holo-search"])
    db.create_coordination_event(request_id, "holoindex_postmerge_maintenance", "wre",
        [contract.CLAIM_AGENT_ID], contract._event_payload(
            target_repo_head_sha=HEAD, authority_root_digest=digest, status="REQUESTED"))
    incident_event = contract.incident_binding_event_id(binding)
    db.create_coordination_event(incident_event, contract.INCIDENT_EVENT_TYPE, "wre",
        [contract.CLAIM_AGENT_ID], contract.incident_binding_event_payload(
            incident_binding=binding, target_repo_head_sha=HEAD, authority_root_digest=digest))
    case = SimpleNamespace(root=workspace, authority=authority, db=db, git=git,
        digest=digest, binding=binding, task_id=task_id, request_id=request_id,
        incident_event=incident_event, pointer=binding["incident_id"], now=NOW)
    case.select = Mock(return_value=HoloIndexAuthoritySelection(
        True, authority, HEAD, HEAD, digest, True, "authority_worktree"))
    case.query = Mock(side_effect=AssertionError("resume must not query before completion"))
    def coordinate(**kwargs):
        assert kwargs["db"] is db and kwargs["incident_binding"] == binding
        return postmerge._coordinate_holoindex_postmerge_for_test(
            **kwargs, git_runner=git, now=lambda: case.now)
    case.coordinate = Mock(side_effect=coordinate)
    return case


def resume(case, **changes):
    kwargs = dict(repo_root=case.root, query="runtime closure",
        resume_incident_id=case.pointer, db=case.db,
        environment={contract.AUTHORITY_REPO_ROOT_ENV: str(case.authority)},
        select_authority=case.select, coordinator=case.coordinate, query_runner=case.query)
    kwargs.update(changes)
    return api()(**kwargs)


def corrupt(case, kind):
    event = case.db.events[case.incident_event]
    if kind == "missing_incident": del case.db.events[case.incident_event]
    elif kind == "missing_request": del case.db.events[case.request_id]
    elif kind == "missing_task": del case.db.tasks[case.task_id]
    elif kind == "incident_digest": event["payload"]["payload_digest"] = "sha256:" + "0" * 64
    elif kind == "incident_pointer": event["payload"]["incident_binding"]["incident_id"] = "sha256:" + "0" * 64
    elif kind == "incident_target": event["payload"]["target_repo_head_sha"] = "0" * 40
    elif kind == "incident_root": event["payload"]["authority_root_digest"] = "sha256:" + "0" * 64
    elif kind == "request_digest": case.db.events[case.request_id]["payload"]["payload_digest"] = "sha256:" + "0" * 64
    elif kind == "task_source": case.db.tasks[case.task_id]["context"]["source"] = "foreign"
    elif kind == "task_skills": case.db.tasks[case.task_id]["required_skills"] = ["foreign"]
    elif kind in {"executing", "completed"}:
        case.db.tasks[case.task_id].update(status=kind, assigned_to=contract.CLAIM_AGENT_ID)
    else: raise AssertionError(kind)
