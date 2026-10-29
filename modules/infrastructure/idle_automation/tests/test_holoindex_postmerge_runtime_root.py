"""Dependency-runtime selection regressions for the post-merge executor."""

from __future__ import annotations

from pathlib import Path

import pytest

from modules.infrastructure.idle_automation.tests import (
    test_holoindex_postmerge_coordinator as support,
)


roots = support.roots


def _claimed_task(roots, monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    workspace, authority = roots
    database = support.FakeDB()
    git = support.FakeGit((support.HEAD, support.HEAD))
    support._patch_state(monkeypatch, authority, git)
    environment = {
        **support._environment(authority),
        "HOLOINDEX_SSD_PATH": str(tmp_path / "ssd"),
    }
    queued = support.coordinator._coordinate_holoindex_postmerge_for_test(
        repo_root=workspace,
        db=database,
        environment=environment,
        git_runner=git,
    )
    support._claim(database, queued.task_id)
    return workspace, authority, database, environment, queued.task_id


def _execute(workspace, database, environment, task_id, transaction):
    return support.executor._execute_holoindex_postmerge_task_for_test(
        repo_root=workspace,
        task_id=task_id,
        context=database.tasks[task_id]["context"],
        execution_claim=support._execution_claim(database, task_id),
        db=database,
        environment=environment,
        authority_transaction=transaction,
    )


def test_executor_resolves_primary_runtime_without_changing_authority(
    roots,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    workspace, authority, database, environment, task_id = _claimed_task(
        roots, monkeypatch, tmp_path
    )
    runtime_root = tmp_path / "canonical-runtime"
    runtime_root.mkdir()
    observed: dict[str, object] = {}
    monkeypatch.setattr(
        support.executor,
        "resolve_holoindex_runtime_root",
        lambda root: runtime_root if Path(root) == workspace else Path(root),
    )

    def transaction(**kwargs):
        observed.update(kwargs)
        return support._transaction_result()

    result = _execute(
        workspace, database, environment, task_id, transaction
    )

    assert result["ok"] is True
    assert observed["workspace_root"] == runtime_root
    assert observed["repo_root"] == authority


def test_runtime_root_failure_finalizes_task_without_authority_call(
    roots,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    workspace, _, database, environment, task_id = _claimed_task(
        roots, monkeypatch, tmp_path
    )
    effects: list[str] = []

    def reject_resolution(_root):
        raise RuntimeError("injected resolver fault")

    monkeypatch.setattr(
        support.executor, "resolve_holoindex_runtime_root", reject_resolution
    )
    result = _execute(
        workspace,
        database,
        environment,
        task_id,
        lambda **_kwargs: effects.append("authority"),
    )

    assert result["ok"] is False
    assert result["detail"] == "postmerge_runtime_root_resolution_failed"
    assert database.tasks[task_id]["status"] == "failed"
    assert effects == []


@pytest.mark.parametrize(
    "gate", ["persisted_context", "claim", "authority", "request", "start"]
)
def test_pre_transaction_gates_do_not_resolve_runtime_or_call_authority(
    gate: str,
    roots,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    workspace, _, database, environment, task_id = _claimed_task(
        roots, monkeypatch, tmp_path
    )
    context = database.tasks[task_id]["context"]
    execution_claim = support._execution_claim(database, task_id)
    effects: list[str] = []
    if gate == "persisted_context":
        context = {**context, "source": "tampered"}
    elif gate == "claim":
        execution_claim = {**execution_claim, "claim_id": "wrong"}
    elif gate == "authority":
        environment = {
            **environment,
            support.coordinator.AUTHORITY_REPO_ROOT_ENV: "relative-root",
        }
    elif gate == "request":
        database.events[support.coordinator.REQUEST_EVENT_PREFIX + support.HEAD][
            "payload"
        ]["status"] = "BROKEN"
    elif gate == "start":
        database.tasks[task_id]["status"] = "executing"
    monkeypatch.setattr(
        support.executor,
        "resolve_holoindex_runtime_root",
        lambda _root: effects.append("runtime"),
    )

    result = support.executor._execute_holoindex_postmerge_task_for_test(
        repo_root=workspace,
        task_id=task_id,
        context=context,
        execution_claim=execution_claim,
        db=database,
        environment=environment,
        authority_transaction=lambda **_kwargs: effects.append("authority"),
    )

    assert result["ok"] is False
    assert effects == []
