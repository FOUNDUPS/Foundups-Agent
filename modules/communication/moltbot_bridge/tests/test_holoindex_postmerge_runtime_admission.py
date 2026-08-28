"""Controller admission, exact-task acknowledgment, and fail-fast regressions."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

from modules.communication.moltbot_bridge.src import (
    holoindex_postmerge_runtime_controller as controller,
)


HEAD = "a" * 40
TASK_ID = "holoindex_postmerge_refresh:" + HEAD
AUTHORITY_DIGEST = "sha256:" + ("b" * 64)


def _live_broker() -> MagicMock:
    broker = MagicMock()
    broker.get_runtime_status.return_value = {
        "registered": True, "running": True, "thread_alive": True,
        "state": "running", "last_error": "",
    }
    return broker


def _pending_database() -> MagicMock:
    database = MagicMock()
    database.get_autonomous_task_by_id.return_value = {
        "task_id": TASK_ID, "status": "pending", "assigned_to": "",
        "required_skills": ["holo-search"],
        "context": {
            "schema_version": "holoindex_postmerge_coordination_v1",
            "source": "holoindex_postmerge_coordinator",
            "target_repo_head_sha": HEAD,
            "authority_root_digest": AUTHORITY_DIGEST,
            "request_event_id": "holoindex_postmerge_requested:" + HEAD,
        },
    }
    return database


class _Clock:
    def __init__(self) -> None:
        self.value = 0.0

    def __call__(self) -> float:
        return self.value

    def sleep(self, seconds: float) -> None:
        self.value += seconds


def _git(argv, _root):
    args = tuple(argv[1:])
    if args[0] == "status":
        return SimpleNamespace(returncode=0, stdout="")
    if args[0] == "rev-parse":
        return SimpleNamespace(returncode=0, stdout=HEAD + "\n")
    raise AssertionError(args)


def test_missing_runtime_dependencies_reject_before_task_coordination(
    monkeypatch, tmp_path: Path,
) -> None:
    coordinator = MagicMock()
    monkeypatch.setattr(
        controller, "classify_verified_owner_result",
        lambda *_args, **_kwargs: "INVALID",
    )
    head, task_id, authority_digest, terminal = controller._admit_or_coordinate(
        root=tmp_path, query="runtime closure", git_runner=_git,
        query_runner=lambda *_args, **_kwargs: {"ok": False},
        select_authority=lambda root: SimpleNamespace(accepted=True),
        coordinator=coordinator, runtime_preflight=lambda: False,
    )
    assert head == HEAD and task_id == "" and authority_digest == ""
    assert terminal is not None
    assert terminal.rejection_reasons == ("runtime_dependencies_unavailable",)
    coordinator.assert_not_called()


def test_supervisor_binding_waits_for_readiness_then_acknowledges_exact_task(
    tmp_path: Path,
) -> None:
    clock = _Clock()
    statuses = iter(("not_ready", "bound"))
    calls: list[str] = []

    def binder(task_id: str, root: Path) -> str:
        calls.append(task_id)
        assert root == tmp_path
        return next(statuses)

    reason = controller._wait_for_supervisor_binding(
        binder, TASK_ID, tmp_path, broker=_live_broker(),
        database=_pending_database(), expected_head=HEAD,
        expected_authority_root_digest=AUTHORITY_DIGEST, deadline=10.0,
        clock=clock, sleeper=clock.sleep, interval=0.1,
    )
    assert reason == ""
    assert calls == [TASK_ID, TASK_ID]


def test_completion_wait_surfaces_runtime_failure_without_sleeping(
    monkeypatch, tmp_path: Path,
) -> None:
    clock = _Clock()
    monkeypatch.setattr(
        controller, "validate_supervisor_holoindex_postmerge_completion",
        lambda *_args: None,
    )
    monkeypatch.setattr(
        controller, "holoindex_postmerge_runtime_inspection",
        lambda *_args, **_kwargs: ("openclaw_not_live", "", 0.0),
    )
    owner, reason = controller._wait_for_completion(
        database=object(), task_id=TASK_ID, query="runtime closure",
        root=tmp_path, deadline=10.0, clock=clock, sleeper=clock.sleep,
        interval=1.0, query_runner=lambda *_args, **_kwargs: {},
        select_authority=lambda root: None, git_runner=_git,
        expected_head=HEAD, expected_authority_root_digest=AUTHORITY_DIGEST,
        broker=object(),
    )
    assert owner is None and reason == "openclaw_not_live"
    assert clock.value == 0.0


def test_binding_wait_surfaces_runtime_crash_before_ack_timeout(tmp_path: Path) -> None:
    clock = _Clock()
    broker = _live_broker()
    broker.get_runtime_status.side_effect = [
        {"registered": True, "running": True, "thread_alive": True,
         "state": "running", "last_error": ""},
        {"registered": True, "running": False, "thread_alive": False,
         "state": "crashed", "last_error": "constructor_failed"},
    ]
    reason = controller._wait_for_supervisor_binding(
        lambda *_args: "not_ready", TASK_ID, tmp_path, broker=broker,
        database=_pending_database(), expected_head=HEAD,
        expected_authority_root_digest=AUTHORITY_DIGEST, deadline=14_400.0,
        clock=clock, sleeper=clock.sleep, interval=1.0,
    )
    assert reason == "openclaw_supervisor_runtime_error"
    assert clock.value == 0.0


def test_completion_wait_bounds_live_but_stalled_task_progress(
    monkeypatch, tmp_path: Path,
) -> None:
    clock = _Clock()
    monkeypatch.setattr(
        controller, "validate_supervisor_holoindex_postmerge_completion",
        lambda *_args: None,
    )
    monkeypatch.setattr(
        controller, "holoindex_postmerge_runtime_inspection",
        lambda *_args, **_kwargs: ("", "sha256:" + ("a" * 64), 60.0),
    )
    owner, reason = controller._wait_for_completion(
        database=object(), task_id=TASK_ID, query="runtime closure",
        root=tmp_path, deadline=14_400.0, clock=clock, sleeper=clock.sleep,
        interval=10.0, query_runner=lambda *_args, **_kwargs: {},
        select_authority=lambda root: None, git_runner=_git,
        expected_head=HEAD, expected_authority_root_digest=AUTHORITY_DIGEST,
        broker=object(),
    )
    assert owner is None and reason == "postmerge_task_progress_timeout"
    assert clock.value == 60.0


def test_healthy_long_execution_uses_integrity_bound_assignment_lease(
    monkeypatch, tmp_path: Path,
) -> None:
    clock = _Clock()
    completion = {
        "generation_id": "sha256:" + ("c" * 64),
        "freshness_receipt_digest": "sha256:" + ("d" * 64),
    }
    monkeypatch.setattr(
        controller, "validate_supervisor_holoindex_postmerge_completion",
        lambda *_args: completion if clock.value >= 2_400.0 else None,
    )
    monkeypatch.setattr(
        controller, "holoindex_postmerge_runtime_inspection",
        lambda *_args, **_kwargs: ("", "sha256:" + ("e" * 64), 7_500.0),
    )
    monkeypatch.setattr(
        controller, "_prove_completion_owner",
        lambda **_kwargs: ({"freshness_generation_id": completion["generation_id"]}, ""),
    )
    owner, reason = controller._wait_for_completion(
        database=object(), task_id=TASK_ID, query="runtime closure",
        root=tmp_path, deadline=14_400.0, clock=clock, sleeper=clock.sleep,
        interval=300.0, query_runner=lambda *_args, **_kwargs: {},
        select_authority=lambda root: None, git_runner=_git,
        expected_head=HEAD, expected_authority_root_digest=AUTHORITY_DIGEST,
        broker=object(),
    )
    assert reason == "" and owner is not None
    assert clock.value == 2_400.0
