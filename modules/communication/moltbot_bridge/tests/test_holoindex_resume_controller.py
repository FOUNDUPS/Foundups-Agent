"""Additive resume lifecycle controls; fake runtime ports, real resume validator."""
from contextlib import contextmanager
from dataclasses import replace
from datetime import timedelta
import inspect
from unittest.mock import Mock

import pytest

from modules.communication.moltbot_bridge.src import holoindex_postmerge_runtime_controller as controller
from modules.communication.moltbot_bridge.src.reddog_holoindex_incident_repair_contract import seal_receipt
from modules.communication.moltbot_bridge.tests.holoindex_resume_test_support import (
    HEAD, NOW, make_case, resume,
)
from modules.communication.moltbot_bridge.tests.test_holoindex_postmerge_runtime_controller import (
    FakeBroker, FakeClock, _git_runner, _repair_receipt, GENERATION, FRESHNESS,
)
from modules.infrastructure.idle_automation.tests.test_holoindex_postmerge_coordinator import roots


def _api():
    value = controller._run_holoindex_postmerge_runtime_for_test
    for function in (value, controller.run_holoindex_postmerge_runtime_once):
        parameter = inspect.signature(function).parameters.get("resume_incident_id")
        assert parameter is not None and parameter.default is None, "controller_resume_pointer_api_missing"
    return value


@contextmanager
def _lease(trace):
    trace.append("lease_enter")
    try:
        yield
    finally:
        trace.append("lease_exit")


def _wire(monkeypatch, case, phase, trace):
    def inside():
        assert trace[0] == "lease_enter" and "lease_exit" not in trace
    def preflight():
        inside()
        trace.append("preflight")
        return True
    def resume_bound(**kwargs):
        inside()
        assert "preflight" in trace and kwargs["db"] is case.db
        assert kwargs["repo_root"] == case.root
        trace.append("resume")
        return resume(case, resume_incident_id=kwargs["resume_incident_id"])
    def completion(_database, task_id):
        inside()
        assert _database is case.db and task_id == case.task_id
        if phase == "interrupt":
            raise KeyboardInterrupt()
        return {"generation_id": GENERATION, "freshness_receipt_digest": FRESHNESS}
    monkeypatch.setattr(controller, "resume_holoindex_incident_repair", resume_bound, raising=False)
    monkeypatch.setattr(controller, "classify_verified_owner_result", lambda *_a, **_k: "INVALID")
    monkeypatch.setattr(controller, "validate_supervisor_holoindex_postmerge_completion", completion)
    monkeypatch.setattr(controller, "query_and_classify_owner_result", lambda **kw: (
        controller.CURRENT, {"freshness_generation_id": GENERATION,
        "freshness_receipt_digest": FRESHNESS,
        "owner_acquisition_cycle": kw["query_runner"].keywords["acquisition_cycle"]}))
    return preflight


def _invoke(monkeypatch, roots, phase):
    value = _api()
    case = make_case(monkeypatch, roots, "retry_wait" if phase == "retry_wait" else "pending")
    if phase == "retry_wait":
        due = (NOW + timedelta(seconds=1)).isoformat()
        case.db.tasks[case.task_id].update(retry_not_before=due)
        case.db.tasks[case.task_id]["context"]["retry_not_before"] = due
    broker, clock, trace = FakeBroker(stop_works=phase != "cleanup_failure"), FakeClock(), []
    preflight = _wire(monkeypatch, case, phase, trace)
    initial = seal_receipt(replace(_repair_receipt(), authority_root_digest=case.digest, receipt_id=""))
    coordinator = Mock(return_value=initial)
    bootstrap = Mock()
    result = value(repo_root=case.root, query="runtime closure", timeout_seconds=10.0,
        poll_interval_seconds=0.1, git_runner=_git_runner(),
        query_runner=lambda *_a, **_k: {"ok": False, "error": "STALE_INDEX"},
        select_authority=case.select, coordinator=coordinator,
        bootstrap=bootstrap, broker_provider=lambda: broker, database_provider=lambda: case.db,
        clock=clock, sleeper=clock.sleep, lease_factory=lambda: _lease(trace),
        runtime_preflight=preflight,
        resume_incident_id=None if phase == "initial" else case.pointer)
    return result, case, broker, trace, coordinator, bootstrap


@pytest.mark.parametrize("phase", ["initial", "resume", "retry_wait", "interrupt", "cleanup_failure"])
def test_validated_incident_survives_controller_lifecycle(monkeypatch, roots, phase):
    result, case, broker, trace, coordinator, bootstrap = _invoke(monkeypatch, roots, phase)
    assert result.incident_id == case.pointer
    assert result.task_id == case.task_id and result.target_repo_head_sha == HEAD
    assert trace[0] == "lease_enter" and trace[-1] == "lease_exit"
    if phase == "initial":
        coordinator.assert_called_once()
        assert "resume" not in trace
    else:
        coordinator.assert_not_called()
        assert trace.index("preflight") < trace.index("resume")
    if phase == "retry_wait":
        assert result.accepted is False
        assert broker.started == [] and broker.stopped == []
        bootstrap.assert_not_called()
    else:
        assert broker.started == ["openclaw", "openclaw_supervisor"]
        assert broker.stopped == ["openclaw_supervisor", "openclaw"]
        assert broker.start_launch_kwargs[1] == {
            "runtime_mode": "holoindex_postmerge_only", "postmerge_task_id": case.task_id}
        assert result.accepted is (phase in {"initial", "resume"})
        if phase != "cleanup_failure":
            assert result.stopped_runtime_ids == ("openclaw_supervisor", "openclaw")


def test_malformed_controller_pointer_cannot_reach_query_or_database(roots):
    value = _api()
    query, database, coordinator, bootstrap = Mock(), Mock(), Mock(), Mock()
    clock = FakeClock()
    result = value(repo_root=roots[0], query="runtime closure", timeout_seconds=10.0,
        poll_interval_seconds=0.1, git_runner=_git_runner(), query_runner=query,
        select_authority=Mock(), coordinator=coordinator, bootstrap=bootstrap,
        broker_provider=Mock(), database_provider=database, clock=clock,
        sleeper=clock.sleep, resume_incident_id=True)
    assert result.accepted is False and result.incident_id == ""
    query.assert_not_called()
    database.assert_not_called()
    coordinator.assert_not_called()
    bootstrap.assert_not_called()
