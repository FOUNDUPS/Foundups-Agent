"""Authority-lease, activation ordering, and supersession regressions."""

from __future__ import annotations

import inspect
from pathlib import Path
from types import SimpleNamespace
from typing import Sequence

import pytest

from modules.infrastructure.database.src.agent_db import AgentDB
from modules.infrastructure.database.src.db_manager import DatabaseManager
from modules.infrastructure.foundups_mcp_bridge.src import (
    reddog_holoindex_postmerge_replica as replica_composer,
)
from modules.infrastructure.idle_automation.tests import (
    test_holoindex_postmerge_coordinator as support,
)


roots = support.roots


@pytest.fixture()
def real_agent_db(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> AgentDB:
    monkeypatch.setenv("FOUNDUPS_DB_ENGINE", "sqlite")
    monkeypatch.setenv("FOUNDUPS_DB_PATH", str(tmp_path / "postmerge.db"))
    DatabaseManager.reset_for_tests()
    database = AgentDB()
    yield database
    DatabaseManager.reset_for_tests()


def _execution_claim(context) -> dict[str, str]:
    return {
        "claim_id": str(context["claim_id"]),
        "claim_binding_digest": str(context["claim_binding_digest"]),
    }


def test_production_authority_and_executor_apis_seal_dependency_injection() -> None:
    authority_parameters = inspect.signature(
        support.authority_transaction.advance_reddog_holoindex_authority
    ).parameters
    executor_parameters = inspect.signature(
        support.coordinator.execute_holoindex_postmerge_task
    ).parameters
    coordinator_parameters = inspect.signature(
        support.coordinator.coordinate_holoindex_postmerge
    ).parameters
    composer_parameters = inspect.signature(
        replica_composer.ensure_postmerge_query_replica_operational
    ).parameters

    assert "activate_replica" not in authority_parameters
    assert "ensure_current" not in authority_parameters
    assert "git_runner" not in authority_parameters
    assert "authority_transaction" not in executor_parameters
    assert "git_runner" not in coordinator_parameters
    assert "prove_operational" not in coordinator_parameters
    assert "now" not in coordinator_parameters
    assert "dependencies" not in composer_parameters


def test_authority_transaction_releases_lease_for_replica_activation(
    roots,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    workspace, authority = roots
    git = support.FakeGit((support.HEAD, support.HEAD))
    support._patch_state(monkeypatch, authority, git)
    effects: list[str] = []
    current_args: dict[str, object] = {}

    def ensure_current(**kwargs):
        current_args.update(kwargs)
        effects.append("refresh")
        return support._transaction_result()

    result = support.authority_transaction._advance_reddog_holoindex_authority_for_test(
        workspace_root=workspace,
        repo_root=authority,
        target_repo_head_sha=support.HEAD,
        expected_authority_root_digest=(
            support.authority_transaction.repository_root_digest(authority)
        ),
        environ={"HOLOINDEX_SSD_PATH": str(tmp_path / "ssd")},
        git_runner=git,
        cleanup_owner=lambda: effects.append("cleanup"),
        ensure_current=ensure_current,
        activate_replica=lambda **kwargs: (
            effects.append("activation") or kwargs["current"]
        ),
        lease_factory=lambda _path: support._Lease(effects),
    )

    assert result.ready is True
    assert effects == [
        "lease_enter", "cleanup", "refresh", "lease_exit",
        "activation", "lease_enter", "lease_exit",
    ]
    assert current_args["owner_runtime_root"] == workspace


def test_authority_transaction_rejects_non_forward_update(
    roots,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    workspace, authority = roots

    monkeypatch.setattr(
        support.authority_transaction,
        "read_repository_state",
        lambda _path: support._state(support.NEWER_HEAD),
    )

    class NonAncestorGit(support.FakeGit):
        def __call__(self, argv: Sequence[str], cwd: Path):
            if tuple(argv)[:3] == ("git", "merge-base", "--is-ancestor"):
                return SimpleNamespace(returncode=1, stdout="", stderr="")
            return super().__call__(argv, cwd)

    result = support.authority_transaction._advance_reddog_holoindex_authority_for_test(
        workspace_root=workspace,
        repo_root=authority,
        target_repo_head_sha=support.HEAD,
        expected_authority_root_digest=(
            support.authority_transaction.repository_root_digest(authority)
        ),
        environ={"HOLOINDEX_SSD_PATH": str(tmp_path / "ssd")},
        git_runner=NonAncestorGit(),
        ensure_current=lambda **_kwargs: pytest.fail("must not refresh"),
        cleanup_owner=lambda: pytest.fail("must not stop owner"),
        lease_factory=lambda _path: support._Lease([]),
    )

    assert result.ready is False
    assert result.error == "authority_non_forward_update_rejected"


def test_activation_failure_reacquires_authority_and_cleans_owner(
    roots,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    workspace, authority = roots
    git = support.FakeGit((support.HEAD, support.HEAD))
    support._patch_state(monkeypatch, authority, git)
    effects: list[str] = []

    def reject_activation(**_kwargs):
        effects.append("activation")
        return SimpleNamespace(
            ready=False, status="FAILED", refreshed=True,
            error="ACTIVATION_MATERIALIZATION_FAILED",
            repo_head_sha=support.HEAD,
            generation_id="sha256:" + ("1" * 64),
            freshness_receipt_digest="sha256:" + ("2" * 64),
        )

    result = support.authority_transaction._advance_reddog_holoindex_authority_for_test(
        workspace_root=workspace,
        repo_root=authority,
        target_repo_head_sha=support.HEAD,
        expected_authority_root_digest=(
            support.authority_transaction.repository_root_digest(authority)
        ),
        environ={"HOLOINDEX_SSD_PATH": str(tmp_path / "ssd")},
        git_runner=git,
        cleanup_owner=lambda: effects.append("cleanup"),
        ensure_current=lambda **_kwargs: support._transaction_result(),
        activate_replica=reject_activation,
        lease_factory=lambda _path: support._Lease(effects),
    )

    assert result.ready is False
    assert result.error == "ACTIVATION_MATERIALIZATION_FAILED"
    assert effects == [
        "lease_enter", "cleanup", "lease_exit", "activation",
        "lease_enter", "cleanup", "lease_exit",
    ]


def test_activation_failure_through_executor_never_completes_agentdb(
    roots,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    workspace, authority = roots
    db = support.FakeDB()
    git = support.FakeGit((support.HEAD, support.HEAD, support.HEAD))
    support._patch_state(monkeypatch, authority, git)
    environment = {
        **support._environment(authority),
        "HOLOINDEX_SSD_PATH": str(tmp_path / "ssd"),
    }
    queued = support.coordinator._coordinate_holoindex_postmerge_for_test(
        repo_root=workspace,
        db=db,
        environment=environment,
        git_runner=git,
    )
    support._claim(db, queued.task_id)

    def actual_failed_transaction(**kwargs):
        return support.authority_transaction._advance_reddog_holoindex_authority_for_test(
            **kwargs,
            git_runner=git,
            cleanup_owner=lambda: None,
            ensure_current=lambda **_kwargs: support._transaction_result(),
            activate_replica=lambda **_kwargs: SimpleNamespace(
                ready=False,
                status="FAILED",
                refreshed=True,
                error="ACTIVATION_ROUTE_STATE_INVALID",
                repo_head_sha=support.HEAD,
                generation_id="sha256:" + ("1" * 64),
                freshness_receipt_digest="sha256:" + ("2" * 64),
            ),
            lease_factory=lambda _path: support._Lease([]),
        )

    result = support.coordinator._execute_holoindex_postmerge_task_for_test(
        repo_root=workspace,
        task_id=queued.task_id,
        context=db.tasks[queued.task_id]["context"],
        execution_claim=support._execution_claim(db, queued.task_id),
        db=db,
        environment=environment,
        authority_transaction=actual_failed_transaction,
    )

    assert result["ok"] is False
    assert result["detail"] == "ACTIVATION_ROUTE_STATE_INVALID"
    assert db.tasks[queued.task_id]["status"] == "failed"
    assert (
        db.events[support.coordinator.REQUEST_EVENT_PREFIX + support.HEAD][
            "resolution_status"
        ]
        == "pending"
    )
    assert support.coordinator.COMPLETION_EVENT_PREFIX + support.HEAD not in db.events


def test_activation_failure_preserves_real_agentdb_request_truth(
    roots,
    real_agent_db: AgentDB,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    workspace, authority = roots
    git = support.FakeGit((support.HEAD, support.HEAD, support.HEAD))
    support._patch_state(monkeypatch, authority, git)
    environment = {
        **support._environment(authority),
        "HOLOINDEX_SSD_PATH": str(tmp_path / "ssd"),
    }
    queued = support.coordinator._coordinate_holoindex_postmerge_for_test(
        repo_root=workspace, db=real_agent_db,
        environment=environment, git_runner=git,
    )
    assert real_agent_db.claim_holoindex_postmerge_task(
        queued.task_id, support.executor.CLAIM_AGENT_ID,
        expected_source=support.coordinator.SOURCE,
        expected_schema_version=support.coordinator.SCHEMA_VERSION,
        expected_target_repo_head_sha=support.HEAD,
        expected_authority_root_digest=queued.authority_root_digest,
    )
    persisted = real_agent_db.get_autonomous_task_by_id(queued.task_id)
    context = persisted["context"]

    result = support.coordinator._execute_holoindex_postmerge_task_for_test(
        repo_root=workspace, task_id=queued.task_id, context=context,
        execution_claim=_execution_claim(context),
        db=real_agent_db, environment=environment,
        authority_transaction=lambda **kwargs: (
            support.authority_transaction._advance_reddog_holoindex_authority_for_test(
                **kwargs, git_runner=git, cleanup_owner=lambda: None,
                ensure_current=lambda **_kwargs: support._transaction_result(),
                activate_replica=lambda **_kwargs: SimpleNamespace(
                    ready=False, status="FAILED", refreshed=True,
                    error="ACTIVATION_ROUTE_STATE_INVALID",
                    observed_origin_main_sha=support.HEAD,
                ),
                lease_factory=lambda _path: support._Lease([]),
            )
        ),
    )

    assert result["detail"] == "ACTIVATION_ROUTE_STATE_INVALID"
    assert real_agent_db.get_autonomous_task_by_id(queued.task_id)["status"] == "failed"
    request = real_agent_db.get_coordination_event_by_id(
        support.coordinator.REQUEST_EVENT_PREFIX + support.HEAD
    )
    assert request["resolution_status"] == "pending"
    assert real_agent_db.get_coordination_event_by_id(
        support.coordinator.COMPLETION_EVENT_PREFIX + support.HEAD
    ) is None


def test_activation_cannot_substitute_canonical_generation_or_receipt(
    roots,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    workspace, authority = roots
    git = support.FakeGit((support.HEAD, support.HEAD))
    support._patch_state(monkeypatch, authority, git)
    effects: list[str] = []
    mismatched = support._transaction_result()
    mismatched.generation_id = "sha256:" + ("9" * 64)

    result = support.authority_transaction._advance_reddog_holoindex_authority_for_test(
        workspace_root=workspace,
        repo_root=authority,
        target_repo_head_sha=support.HEAD,
        expected_authority_root_digest=(
            support.authority_transaction.repository_root_digest(authority)
        ),
        environ={"HOLOINDEX_SSD_PATH": str(tmp_path / "ssd")},
        git_runner=git,
        cleanup_owner=lambda: effects.append("cleanup"),
        ensure_current=lambda **_kwargs: support._transaction_result(),
        activate_replica=lambda **_kwargs: mismatched,
        lease_factory=lambda _path: support._Lease(effects),
    )

    assert result.ready is False
    assert result.error == "HOLOINDEX_POSTMERGE_OPERATIONAL_BINDING_MISMATCH"
    assert effects == [
        "lease_enter", "cleanup", "lease_exit",
        "lease_enter", "cleanup", "lease_exit",
    ]


def test_second_authority_lease_busy_cleans_activated_owner(
    roots,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    workspace, authority = roots
    git = support.FakeGit((support.HEAD, support.HEAD))
    support._patch_state(monkeypatch, authority, git)
    effects: list[str] = []
    lease_calls = 0

    def lease_factory(_path):
        nonlocal lease_calls
        lease_calls += 1
        if lease_calls == 2:
            raise support.authority_transaction.MaintenanceLeaseBusy("busy")
        return support._Lease(effects)

    result = support.authority_transaction._advance_reddog_holoindex_authority_for_test(
        workspace_root=workspace,
        repo_root=authority,
        target_repo_head_sha=support.HEAD,
        expected_authority_root_digest=(
            support.authority_transaction.repository_root_digest(authority)
        ),
        environ={"HOLOINDEX_SSD_PATH": str(tmp_path / "ssd")},
        git_runner=git,
        cleanup_owner=lambda: effects.append("cleanup"),
        ensure_current=lambda **_kwargs: support._transaction_result(),
        activate_replica=lambda **kwargs: (
            effects.append("activation") or kwargs["current"]
        ),
        lease_factory=lease_factory,
    )

    assert result.ready is False
    assert result.status == "BUSY"
    assert effects == [
        "lease_enter", "cleanup", "lease_exit", "activation", "cleanup",
    ]


def test_initial_authority_lease_busy_does_not_stop_unowned_process(
    roots,
    tmp_path: Path,
) -> None:
    workspace, authority = roots
    effects: list[str] = []

    result = support.authority_transaction._advance_reddog_holoindex_authority_for_test(
        workspace_root=workspace,
        repo_root=authority,
        target_repo_head_sha=support.HEAD,
        expected_authority_root_digest=(
            support.authority_transaction.repository_root_digest(authority)
        ),
        environ={"HOLOINDEX_SSD_PATH": str(tmp_path / "ssd")},
        cleanup_owner=lambda: effects.append("cleanup"),
        lease_factory=lambda _path: (_ for _ in ()).throw(
            support.authority_transaction.MaintenanceLeaseBusy("busy")
        ),
    )

    assert result.status == "BUSY"
    assert effects == []


def test_supersession_after_activation_advances_and_invalidates(
    roots,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    workspace, authority = roots
    git = support.FakeGit((support.HEAD, support.NEWER_HEAD))
    support._patch_state(monkeypatch, authority, git)
    effects: list[str] = []

    result = support.authority_transaction._advance_reddog_holoindex_authority_for_test(
        workspace_root=workspace,
        repo_root=authority,
        target_repo_head_sha=support.HEAD,
        expected_authority_root_digest=(
            support.authority_transaction.repository_root_digest(authority)
        ),
        environ={"HOLOINDEX_SSD_PATH": str(tmp_path / "ssd")},
        git_runner=git,
        cleanup_owner=lambda: effects.append("cleanup"),
        ensure_current=lambda **_kwargs: support._transaction_result(),
        activate_replica=support._activate_current,
        lease_factory=lambda _path: support._Lease(effects),
    )

    assert result.status == "SUPERSEDED"
    assert result.observed_origin_main_sha == support.NEWER_HEAD
    assert effects == [
        "lease_enter", "cleanup", "lease_exit",
        "lease_enter", "cleanup", "lease_exit",
    ]
    assert git.switch_target == support.NEWER_HEAD


def test_supersession_invalidation_failure_leaves_durable_marker(
    roots,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    workspace, authority = roots

    class LatestSwitchFails(support.FakeGit):
        def __call__(self, argv: Sequence[str], cwd: Path):
            if (
                tuple(argv)[:4] == ("git", "switch", "--detach", "--quiet")
                and tuple(argv)[4] == support.NEWER_HEAD
            ):
                return SimpleNamespace(returncode=1, stdout="", stderr="")
            return super().__call__(argv, cwd)

    git = LatestSwitchFails((support.HEAD, support.NEWER_HEAD))
    support._patch_state(monkeypatch, authority, git)
    monkeypatch.setattr(
        support.authority_transaction,
        "_invalidate_generation",
        lambda **_kwargs: False,
    )
    result = support.authority_transaction._advance_reddog_holoindex_authority_for_test(
        workspace_root=workspace,
        repo_root=authority,
        target_repo_head_sha=support.HEAD,
        expected_authority_root_digest=(
            support.authority_transaction.repository_root_digest(authority)
        ),
        environ={"HOLOINDEX_SSD_PATH": str(tmp_path / "ssd")},
        git_runner=git,
        cleanup_owner=lambda: None,
        ensure_current=lambda **_kwargs: support._transaction_result(),
        activate_replica=support._activate_current,
        lease_factory=lambda _path: support._Lease([]),
    )

    marker = authority / ".holoindex_authority_blocked"
    assert result.status == "REJECTED"
    assert result.error == "target_superseded_invalidation_failed"
    assert marker.read_text(encoding="ascii") == "holoindex_authority_blocked_v1\n"


def test_authority_transaction_recovers_its_own_block_marker(
    roots,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    workspace, authority = roots
    marker = authority / ".holoindex_authority_blocked"
    marker.write_bytes(b"holoindex_authority_blocked_v1\n")
    git = support.FakeGit((support.HEAD, support.HEAD))

    monkeypatch.setattr(
        support.authority_transaction,
        "read_repository_state",
        lambda _path: support._state(
            git.switch_target or support.HEAD, clean=not marker.exists()
        ),
    )
    result = support.authority_transaction._advance_reddog_holoindex_authority_for_test(
        workspace_root=workspace,
        repo_root=authority,
        target_repo_head_sha=support.HEAD,
        expected_authority_root_digest=(
            support.authority_transaction.repository_root_digest(authority)
        ),
        environ={"HOLOINDEX_SSD_PATH": str(tmp_path / "ssd")},
        git_runner=git,
        cleanup_owner=lambda: None,
        ensure_current=lambda **_kwargs: support._transaction_result(status="READY"),
        activate_replica=support._activate_current,
        lease_factory=lambda _path: support._Lease([]),
    )

    assert result.ready is True
    assert not marker.exists()


def test_authority_transaction_rejects_substituted_authority_binding(
    roots,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    workspace, authority = roots
    git = support.FakeGit()
    support._patch_state(monkeypatch, authority, git)

    result = support.authority_transaction._advance_reddog_holoindex_authority_for_test(
        workspace_root=workspace,
        repo_root=authority,
        target_repo_head_sha=support.HEAD,
        expected_authority_root_digest="sha256:" + ("0" * 64),
        environ={"HOLOINDEX_SSD_PATH": str(tmp_path / "ssd")},
        git_runner=git,
        ensure_current=lambda **_kwargs: pytest.fail("must not refresh"),
        cleanup_owner=lambda: pytest.fail("must not stop owner"),
        lease_factory=lambda _path: support._Lease([]),
    )

    assert result.ready is False
    assert result.error == "authority_root_binding_invalid"
    assert not any(call[:3] == ("git", "fetch", "--quiet") for call, _ in git.calls)
