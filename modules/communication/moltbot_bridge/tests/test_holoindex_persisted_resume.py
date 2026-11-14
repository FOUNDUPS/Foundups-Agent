"""Frozen prior-admission resume tests; no live DB, Git, services or model."""
from copy import deepcopy
from dataclasses import replace
from datetime import timedelta
from unittest.mock import Mock

import pytest

from modules.communication.moltbot_bridge.tests.holoindex_resume_test_support import (
    HEAD, NOW, api, contract, corrupt, incident, make_case, resume,
)
from modules.infrastructure.idle_automation.tests.test_holoindex_postmerge_coordinator import roots


def test_pending_resume_reuses_real_durable_binding_and_coordinator(monkeypatch, roots):
    api()
    case = make_case(monkeypatch, roots)
    before = deepcopy((case.db.tasks, case.db.events))
    result = resume(case)
    assert result.accepted and result.status == "PENDING"
    assert result.incident_id == case.pointer and result.task_id == case.task_id
    assert result.target_repo_head_sha == HEAD and result.authority_root_digest == case.digest
    assert (case.db.tasks, case.db.events) == before
    assert case.coordinate.call_count == 1
    case.query.assert_not_called()


@pytest.mark.parametrize("kind", ["missing_incident", "missing_request", "missing_task",
    "incident_digest", "incident_pointer", "incident_target", "incident_root",
    "request_digest", "task_source", "task_skills", "executing", "completed"])
def test_invalid_persisted_binding_never_coordinates(monkeypatch, roots, kind):
    api()
    case = make_case(monkeypatch, roots)
    corrupt(case, kind)
    before = deepcopy((case.db.tasks, case.db.events))
    result = resume(case)
    assert result.accepted is False
    assert (case.db.tasks, case.db.events) == before
    case.coordinate.assert_not_called()
    case.query.assert_not_called()


@pytest.mark.parametrize("pointer", [None, "", True, 7, "sha256:" + "A" * 64,
    "sha256:" + "a" * 63, "sha256:" + "a" * 65], ids=["none", "empty", "bool", "int", "upper", "short", "long"])
def test_invalid_pointer_rejects_before_database_or_authority(roots, pointer):
    value = api()
    db, selection, coordinate, query = Mock(), Mock(), Mock(), Mock()
    result = value(repo_root=roots[0], query="runtime closure", resume_incident_id=pointer,
        db=db, select_authority=selection, coordinator=coordinate, query_runner=query)
    assert result.accepted is False
    assert not db.mock_calls
    selection.assert_not_called()
    coordinate.assert_not_called()
    query.assert_not_called()


@pytest.mark.parametrize("kind", ["unaccepted", "workspace_head", "authority_head", "root"])
def test_current_authority_must_match_prior_admission(monkeypatch, roots, kind):
    api()
    case = make_case(monkeypatch, roots)
    changes = {"unaccepted": {"accepted": False}, "workspace_head": {"workspace_head_sha": "0" * 40},
        "authority_head": {"authority_head_sha": "0" * 40}, "root": {"authority_root_digest": "sha256:" + "0" * 64}}
    case.select.return_value = replace(case.select.return_value, **changes[kind])
    assert resume(case).accepted is False
    case.coordinate.assert_not_called()


@pytest.mark.parametrize("phase", ["failed", "before_deadline", "at_deadline", "exhausted"])
def test_existing_retry_delay_and_budget_are_preserved(monkeypatch, roots, phase):
    api()
    status = "failed" if phase in {"failed", "exhausted"} else "retry_wait"
    case = make_case(monkeypatch, roots, status, 3 if phase == "exhausted" else 1)
    if status == "retry_wait":
        due = NOW if phase == "at_deadline" else NOW + timedelta(seconds=1)
        case.db.tasks[case.task_id]["context"]["retry_not_before"] = due.isoformat()
        case.db.tasks[case.task_id]["retry_not_before"] = due.isoformat()
    result = resume(case)
    if phase == "exhausted":
        assert result.accepted is False
        assert case.db.tasks[case.task_id]["status"] == "failed"
    else:
        assert result.accepted is True
        assert result.status == ("REQUEUED" if phase == "at_deadline" else "RETRY_WAIT")
        expected_count = 2 if phase == "failed" else 1
        assert case.db.tasks[case.task_id]["context"]["retry_count"] == expected_count
        assert not case.db.tasks[case.task_id].get("assigned_to")
        if phase == "failed":
            expected = (NOW + timedelta(seconds=300)).isoformat()
            assert case.db.tasks[case.task_id]["context"]["retry_not_before"] == expected
    assert case.coordinate.call_count == 1
    case.query.assert_not_called()


def test_generic_stale_index_remains_ineligible_without_pointer(monkeypatch, roots):
    case = make_case(monkeypatch, roots)
    result = incident.coordinate_holoindex_incident_repair(repo_root=case.root,
        query="runtime closure", owner_failure={"ok": False, "error": "STALE_INDEX",
            "index_gap_detected": True, "owner_attempts": 0, "no_holoindex_reindex_performed": True},
        db=case.db, select_authority=case.select, coordinator=case.coordinate, query_runner=case.query)
    assert result.accepted is False
    assert "STALE_INDEX" not in contract.HOLOINDEX_INCIDENT_KINDS
    case.coordinate.assert_not_called()
    case.query.assert_not_called()
