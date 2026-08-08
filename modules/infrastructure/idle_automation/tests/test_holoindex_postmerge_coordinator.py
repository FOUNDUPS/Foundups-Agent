"""Exact-SHA HoloIndex post-merge coordinator regressions."""

from __future__ import annotations

import ast
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Sequence

import pytest

from modules.infrastructure.idle_automation.src import (
    holoindex_postmerge_coordinator as coordinator,
)
from modules.infrastructure.idle_automation.src import (
    holoindex_postmerge_contract as contract,
)
from modules.infrastructure.idle_automation.src import (
    holoindex_postmerge_executor as executor,
)
from modules.infrastructure.foundups_mcp_bridge.src import (
    reddog_holoindex_authority_transaction as authority_transaction,
)


HEAD = "a" * 40
NEWER_HEAD = "b" * 40


def test_idle_automation_package_keeps_contract_import_lightweight() -> None:
    package_source = (
        Path(__file__).resolve().parents[1] / "__init__.py"
    ).read_text(encoding="utf-8")
    tree = ast.parse(package_source)
    eager_modules = {
        node.module
        for node in tree.body
        if isinstance(node, ast.ImportFrom) and node.level == 1
    }
    assert "src.idle_automation_dae" not in eager_modules
    assert "src.self_research_refresh" not in eager_modules
    assert "def __getattr__(name: str)" in package_source


class FakeDB:
    def __init__(self) -> None:
        self.tasks: dict[str, dict[str, Any]] = {}
        self.events: dict[str, dict[str, Any]] = {}

    def get_autonomous_task_by_id(self, task_id: str):
        task = self.tasks.get(task_id)
        return dict(task) if task else None

    def create_autonomous_task(self, **kwargs):
        task_id = kwargs["task_id"]
        if task_id in self.tasks:
            return False
        self.tasks[task_id] = {
            **kwargs,
            "status": "pending",
        }
        return True

    def create_holoindex_postmerge_task_if_absent(self, **kwargs):
        return self.create_autonomous_task(**kwargs)

    def create_coordination_event(
        self,
        event_id: str,
        event_type: str,
        initiator_agent: str,
        target_agents: list[str],
        payload: dict[str, Any],
    ):
        if event_id in self.events:
            return False
        self.events[event_id] = {
            "event_id": event_id,
            "event_type": event_type,
            "initiator_agent": initiator_agent,
            "target_agents": list(target_agents),
            "payload": dict(payload),
            "resolution_status": "pending",
        }
        return True

    def get_coordination_event_by_id(self, event_id: str):
        event = self.events.get(event_id)
        return dict(event) if event else None

    def resolve_coordination_event(self, event_id: str, status: str = "completed"):
        if event_id not in self.events:
            return False
        self.events[event_id]["resolution_status"] = status
        return True

    def schedule_holoindex_postmerge_task_retry(
        self,
        task_id: str,
        *,
        context: dict[str, Any],
        retry_not_before: str,
    ):
        task = self.tasks.get(task_id)
        if not task or task.get("status") != "failed":
            return False
        task["status"] = "retry_wait"
        task["context"] = dict(context)
        task["retry_not_before"] = retry_not_before
        return True

    def requeue_holoindex_postmerge_task(
        self, task_id: str, *, expected_status: str
    ):
        task = self.tasks.get(task_id)
        if not task or task.get("status") != expected_status:
            return False
        task["status"] = "pending"
        return True

    def claim_holoindex_postmerge_task(
        self,
        task_id: str,
        agent_id: str,
        *,
        expected_source: str,
        expected_schema_version: str,
        expected_target_repo_head_sha: str,
        expected_authority_root_digest: str,
    ):
        task = self.tasks.get(task_id)
        context = task.get("context") if task else None
        if (
            not task
            or task.get("status") != "pending"
            or task.get("assigned_to")
            or not isinstance(context, dict)
            or context.get("source") != expected_source
            or context.get("schema_version") != expected_schema_version
            or context.get("target_repo_head_sha")
            != expected_target_repo_head_sha
            or context.get("authority_root_digest")
            != expected_authority_root_digest
        ):
            return False
        task["status"] = "assigned"
        task["assigned_to"] = agent_id
        task["assigned_at"] = datetime.now(UTC).isoformat()
        claimed_context = dict(context)
        claimed_context.update(
            {
                "claim_id": "hpmc_test",
                "claim_binding_digest": "sha256:" + ("c" * 64),
                "claim_expires_at": (
                    datetime.now(UTC)
                    + timedelta(seconds=coordinator.ASSIGNMENT_LEASE_SECONDS)
                ).isoformat(),
            }
        )
        task["context"] = claimed_context
        return "hpmc_test"

    def start_holoindex_postmerge_execution(
        self,
        task_id: str,
        agent_id: str,
        *,
        claim_id: str,
        claim_binding_digest: str,
    ):
        task = self.tasks.get(task_id)
        context = task.get("context") if task else None
        if (
            not task
            or task.get("status") != "assigned"
            or task.get("assigned_to") != agent_id
            or not isinstance(context, dict)
            or context.get("claim_id") != claim_id
            or context.get("claim_binding_digest") != claim_binding_digest
        ):
            return False
        task["status"] = "executing"
        return True

    def fail_holoindex_postmerge_task(
        self,
        task_id: str,
        agent_id: str,
        *,
        claim_id: str,
        claim_binding_digest: str,
        status: str = "failed",
    ):
        task = self.tasks.get(task_id)
        context = task.get("context") if task else None
        if (
            not task
            or task.get("status") not in {"assigned", "executing"}
            or task.get("assigned_to") != agent_id
            or not isinstance(context, dict)
            or context.get("claim_id") != claim_id
            or context.get("claim_binding_digest") != claim_binding_digest
        ):
            return False
        task["status"] = status
        return True

    def reclaim_expired_holoindex_postmerge_task(
        self,
        task_id: str,
        agent_id: str,
        *,
        expected_assigned_at: str,
    ):
        task = self.tasks.get(task_id)
        if (
            not task
            or task.get("status") not in {"assigned", "executing"}
            or task.get("assigned_to") != agent_id
            or task.get("assigned_at") != expected_assigned_at
        ):
            return False
        task["status"] = "failed"
        return True

    def commit_holoindex_postmerge_completion(
        self,
        *,
        task_id: str,
        agent_id: str,
        request_event_id: str,
        request_payload_digest: str,
        completion_event_id: str,
        completion_payload: dict[str, Any],
        claim_id: str,
        claim_binding_digest: str,
    ):
        task = self.tasks.get(task_id)
        request = self.events.get(request_event_id)
        context = task.get("context") if task else None
        if (
            not task
            or task.get("status") != "executing"
            or task.get("assigned_to") != agent_id
            or not isinstance(context, dict)
            or context.get("claim_id") != claim_id
            or context.get("claim_binding_digest") != claim_binding_digest
            or not request
            or request.get("resolution_status") != "pending"
            or request["payload"].get("payload_digest") != request_payload_digest
            or completion_event_id in self.events
        ):
            return False
        self.events[completion_event_id] = {
            "event_id": completion_event_id,
            "event_type": "holoindex_postmerge_maintenance_completed",
            "initiator_agent": agent_id,
            "target_agents": ["wre"],
            "payload": dict(completion_payload),
            "resolution_status": "pending",
        }
        request["resolution_status"] = "completed"
        task["status"] = "completed"
        return True


class FakeGit:
    def __init__(self, heads: Sequence[str] = (HEAD,)) -> None:
        self.heads = list(heads)
        self.calls: list[tuple[tuple[str, ...], Path]] = []
        self.switch_target = ""

    def __call__(self, argv: Sequence[str], cwd: Path):
        normalized = tuple(argv)
        self.calls.append((normalized, Path(cwd)))
        if normalized[:3] == ("git", "fetch", "--quiet"):
            return SimpleNamespace(returncode=0, stdout="", stderr="")
        if normalized == ("git", "rev-parse", "FETCH_HEAD"):
            value = self.heads.pop(0) if len(self.heads) > 1 else self.heads[0]
            return SimpleNamespace(returncode=0, stdout=value + "\n", stderr="")
        if normalized[-2:] == (
            "--path-format=absolute",
            "--git-common-dir",
        ):
            return SimpleNamespace(
                returncode=0,
                stdout=str(Path(cwd).parent / "common.git") + "\n",
                stderr="",
            )
        if normalized[:4] == ("git", "switch", "--detach", "--quiet"):
            self.switch_target = normalized[4]
            return SimpleNamespace(returncode=0, stdout="", stderr="")
        if normalized[:3] == ("git", "merge-base", "--is-ancestor"):
            return SimpleNamespace(returncode=0, stdout="", stderr="")
        if normalized[:3] == ("git", "status", "--porcelain=v1"):
            marker = Path(cwd) / ".holoindex_authority_blocked"
            output = "?? .holoindex_authority_blocked\n" if marker.exists() else ""
            return SimpleNamespace(returncode=0, stdout=output, stderr="")
        raise AssertionError(f"unexpected git command: {normalized}")


@pytest.fixture
def roots(tmp_path: Path):
    workspace = tmp_path / "Foundups-Agent"
    authority = tmp_path / "Foundups-Agent-holo-authority"
    workspace.mkdir()
    authority.mkdir()
    (workspace / ".git").write_text("gitdir: common\n", encoding="utf-8")
    (authority / ".git").write_text("gitdir: common\n", encoding="utf-8")
    return workspace, authority


def _state(head: str = HEAD, *, clean: bool = True):
    return SimpleNamespace(
        head_sha=head,
        proven_clean=clean,
        error="" if clean else "dirty",
    )


def _patch_state(
    monkeypatch: pytest.MonkeyPatch,
    authority: Path,
    git: FakeGit,
    *,
    authority_clean: bool = True,
) -> None:
    def read_state(path: Path):
        if Path(path) == authority:
            return _state(git.switch_target or HEAD, clean=authority_clean)
        return _state(HEAD)

    monkeypatch.setattr(contract, "read_repository_state", read_state)
    monkeypatch.setattr(authority_transaction, "read_repository_state", read_state)


def _environment(authority: Path) -> dict[str, str]:
    return {coordinator.AUTHORITY_REPO_ROOT_ENV: str(authority)}


def _claim(db: FakeDB, task_id: str) -> None:
    context = db.tasks[task_id]["context"]
    assert db.claim_holoindex_postmerge_task(
        task_id,
        executor.CLAIM_AGENT_ID,
        expected_source=coordinator.SOURCE,
        expected_schema_version=coordinator.SCHEMA_VERSION,
        expected_target_repo_head_sha=context["target_repo_head_sha"],
        expected_authority_root_digest=context["authority_root_digest"],
    )


def _execution_claim(db: FakeDB, task_id: str) -> dict[str, str]:
    context = db.tasks[task_id]["context"]
    return {
        "claim_id": str(context["claim_id"]),
        "claim_binding_digest": str(context["claim_binding_digest"]),
    }


def _transaction_result(
    *,
    ready: bool = True,
    status: str = "REFRESHED",
    observed_sha: str = HEAD,
    error: str = "",
):
    return SimpleNamespace(
        ready=ready,
        status=status,
        refreshed=status == "REFRESHED",
        error=error,
        target_repo_head_sha=HEAD,
        repo_head_sha=HEAD,
        observed_origin_main_sha=observed_sha,
        generation_id="sha256:" + ("1" * 64) if ready else "",
        freshness_receipt_digest="sha256:" + ("2" * 64) if ready else "",
    )


def test_exact_sha_task_is_queued_once(
    roots,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace, authority = roots
    db = FakeDB()
    git = FakeGit()
    _patch_state(monkeypatch, authority, git)

    first = coordinator.coordinate_holoindex_postmerge(
        repo_root=workspace,
        db=db,
        environment=_environment(authority),
        git_runner=git,
    )
    second = coordinator.coordinate_holoindex_postmerge(
        repo_root=workspace,
        db=db,
        environment=_environment(authority),
        git_runner=git,
    )

    assert first.accepted and first.status == "QUEUED"
    assert second.accepted and second.status == "PENDING"
    assert tuple(db.tasks) == (coordinator.TASK_PREFIX + HEAD,)
    context = db.tasks[first.task_id]["context"]
    assert context["target_repo_head_sha"] == HEAD
    assert context["authority_root_digest"] == first.authority_root_digest


def test_tampered_completion_event_fails_closed(
    roots,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace, authority = roots
    db = FakeDB()
    git = FakeGit()
    _patch_state(monkeypatch, authority, git)
    queued = coordinator.coordinate_holoindex_postmerge(
        repo_root=workspace,
        db=db,
        environment=_environment(authority),
        git_runner=git,
    )
    db.events[coordinator.COMPLETION_EVENT_PREFIX + HEAD] = {
        "payload": {
            "schema_version": coordinator.SCHEMA_VERSION,
            "target_repo_head_sha": HEAD,
            "authority_root_digest": queued.authority_root_digest,
            "status": "COMPLETED",
            "generation_id": "forged",
            "freshness_receipt_digest": "forged",
            "payload_digest": "sha256:" + ("0" * 64),
        }
    }

    result = coordinator.coordinate_holoindex_postmerge(
        repo_root=workspace,
        db=db,
        environment=_environment(authority),
        git_runner=git,
    )

    assert result.accepted is False
    assert result.rejection_reasons == ("completion_event_invalid",)


def test_failed_task_enters_bounded_retry_then_requeues(
    roots,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace, authority = roots
    db = FakeDB()
    git = FakeGit()
    _patch_state(monkeypatch, authority, git)
    start = datetime(2026, 7, 26, tzinfo=UTC)
    queued = coordinator.coordinate_holoindex_postmerge(
        repo_root=workspace,
        db=db,
        environment=_environment(authority),
        git_runner=git,
        now=lambda: start,
    )
    db.tasks[queued.task_id]["status"] = "failed"

    waiting = coordinator.coordinate_holoindex_postmerge(
        repo_root=workspace,
        db=db,
        environment=_environment(authority),
        git_runner=git,
        now=lambda: start,
    )
    assert waiting.status == "RETRY_WAIT"
    assert db.tasks[queued.task_id]["context"]["retry_count"] == 1

    requeued = coordinator.coordinate_holoindex_postmerge(
        repo_root=workspace,
        db=db,
        environment=_environment(authority),
        git_runner=git,
        now=lambda: start + timedelta(seconds=coordinator.RETRY_DELAY_SECONDS + 1),
    )
    assert requeued.status == "REQUEUED"
    assert db.tasks[queued.task_id]["status"] == "pending"


def test_expired_assignment_is_reclaimed_into_bounded_retry(
    roots,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace, authority = roots
    db = FakeDB()
    git = FakeGit()
    _patch_state(monkeypatch, authority, git)
    start = datetime(2026, 7, 26, tzinfo=UTC)
    queued = coordinator.coordinate_holoindex_postmerge(
        repo_root=workspace,
        db=db,
        environment=_environment(authority),
        git_runner=git,
        now=lambda: start,
    )
    _claim(db, queued.task_id)
    db.tasks[queued.task_id]["assigned_at"] = (
        start
        - timedelta(seconds=coordinator.ASSIGNMENT_LEASE_SECONDS + 1)
    ).isoformat()

    result = coordinator.coordinate_holoindex_postmerge(
        repo_root=workspace,
        db=db,
        environment=_environment(authority),
        git_runner=git,
        now=lambda: start,
    )

    assert result.status == "RETRY_WAIT"
    assert db.tasks[queued.task_id]["status"] == "retry_wait"
    assert db.tasks[queued.task_id]["context"]["retry_count"] == 1


def test_execution_rejects_context_before_any_effect(
    roots,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace, authority = roots
    db = FakeDB()
    db.tasks[coordinator.TASK_PREFIX + HEAD] = {
        "status": "assigned",
        "assigned_to": executor.CLAIM_AGENT_ID,
        "context": {},
    }
    effects: list[str] = []

    result = coordinator.execute_holoindex_postmerge_task(
        repo_root=workspace,
        task_id=coordinator.TASK_PREFIX + HEAD,
        context={
            "schema_version": coordinator.SCHEMA_VERSION,
            "source": coordinator.SOURCE,
            "target_repo_head_sha": NEWER_HEAD,
        },
        db=db,
        environment=_environment(authority),
        authority_transaction=lambda **_kwargs: effects.append("authority"),
    )

    assert result["ok"] is False
    assert result["detail"] == "postmerge_persisted_context_mismatch"
    assert effects == []
    assert db.tasks[coordinator.TASK_PREFIX + HEAD]["status"] == "assigned"


def test_valid_execution_updates_authority_and_persists_proof(
    roots,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace, authority = roots
    db = FakeDB()
    git = FakeGit((HEAD, HEAD))
    _patch_state(monkeypatch, authority, git)
    queued = coordinator.coordinate_holoindex_postmerge(
        repo_root=workspace,
        db=db,
        environment=_environment(authority),
        git_runner=git,
    )
    _claim(db, queued.task_id)
    transaction_calls: list[dict[str, Any]] = []

    def run_transaction(**kwargs):
        transaction_calls.append(kwargs)
        return _transaction_result()

    missing_claim = coordinator.execute_holoindex_postmerge_task(
        repo_root=workspace,
        task_id=queued.task_id,
        context=db.tasks[queued.task_id]["context"],
        db=db,
        environment=_environment(authority),
        authority_transaction=run_transaction,
    )
    assert missing_claim["ok"] is False
    assert (
        missing_claim["detail"]
        == "postmerge_execution_claim_missing_or_mismatched"
    )
    assert transaction_calls == []

    result = coordinator.execute_holoindex_postmerge_task(
        repo_root=workspace,
        task_id=queued.task_id,
        context=db.tasks[queued.task_id]["context"],
        execution_claim=_execution_claim(db, queued.task_id),
        db=db,
        environment=_environment(authority),
        authority_transaction=run_transaction,
    )

    assert result["ok"] is True
    assert result["executor"] == "wre:holoindex_postmerge"
    assert result["finalization_owned"] is True
    assert db.tasks[queued.task_id]["status"] == "completed"
    completion = db.events[coordinator.COMPLETION_EVENT_PREFIX + HEAD]
    assert completion["payload"]["generation_id"] == "sha256:" + ("1" * 64)
    assert (
        completion["payload"]["freshness_receipt_digest"]
        == "sha256:" + ("2" * 64)
    )
    assert (
        db.events[coordinator.REQUEST_EVENT_PREFIX + HEAD]["resolution_status"]
        == "completed"
    )
    assert transaction_calls == [
        {
            "workspace_root": workspace,
            "repo_root": authority,
            "target_repo_head_sha": HEAD,
            "expected_authority_root_digest": queued.authority_root_digest,
            "environ": _environment(authority),
        }
    ]
    duplicate = coordinator.execute_holoindex_postmerge_task(
        repo_root=workspace,
        task_id=queued.task_id,
        context=db.tasks[queued.task_id]["context"],
        execution_claim=_execution_claim(db, queued.task_id),
        db=db,
        environment=_environment(authority),
        authority_transaction=run_transaction,
    )
    assert duplicate["ok"] is False
    assert duplicate["detail"] == "postmerge_execution_claim_rejected"
    assert len(transaction_calls) == 1


def test_invalid_request_event_blocks_authority_effect(
    roots,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace, authority = roots
    db = FakeDB()
    git = FakeGit()
    _patch_state(monkeypatch, authority, git)
    queued = coordinator.coordinate_holoindex_postmerge(
        repo_root=workspace,
        db=db,
        environment=_environment(authority),
        git_runner=git,
    )
    _claim(db, queued.task_id)
    db.events[coordinator.REQUEST_EVENT_PREFIX + HEAD]["payload"][
        "payload_digest"
    ] = "sha256:" + ("0" * 64)
    effects: list[str] = []

    result = coordinator.execute_holoindex_postmerge_task(
        repo_root=workspace,
        task_id=queued.task_id,
        context=db.tasks[queued.task_id]["context"],
        execution_claim=_execution_claim(db, queued.task_id),
        db=db,
        environment=_environment(authority),
        authority_transaction=lambda **_kwargs: effects.append("authority"),
    )

    assert result["ok"] is False
    assert "request_event_invalid" in result["detail"]
    assert effects == []


def test_origin_main_advance_after_refresh_blocks_completion(
    roots,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace, authority = roots
    db = FakeDB()
    setup_git = FakeGit()
    _patch_state(monkeypatch, authority, setup_git)
    queued = coordinator.coordinate_holoindex_postmerge(
        repo_root=workspace,
        db=db,
        environment=_environment(authority),
        git_runner=setup_git,
    )
    _claim(db, queued.task_id)
    monkeypatch.setattr(
        coordinator,
        "coordinate_holoindex_postmerge",
        lambda **_kwargs: coordinator.HoloIndexPostMergeCoordinationResult(
            True,
            "QUEUED",
            target_repo_head_sha=NEWER_HEAD,
        ),
    )

    result = coordinator.execute_holoindex_postmerge_task(
        repo_root=workspace,
        task_id=queued.task_id,
        context=db.tasks[queued.task_id]["context"],
        execution_claim=_execution_claim(db, queued.task_id),
        db=db,
        environment=_environment(authority),
        authority_transaction=lambda **_kwargs: _transaction_result(
            ready=False,
            status="SUPERSEDED",
            observed_sha=NEWER_HEAD,
            error="target_superseded",
        ),
    )

    assert result["ok"] is False
    assert result["detail"] == "target_superseded"
    assert coordinator.COMPLETION_EVENT_PREFIX + HEAD not in db.events
    assert db.tasks[queued.task_id]["status"] == "superseded"
    assert result["structured_result"]["follow_up"]["status"] == "QUEUED"


def test_dirty_or_unrelated_authority_never_queues(
    roots,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace, authority = roots
    db = FakeDB()
    git = FakeGit()
    _patch_state(monkeypatch, authority, git, authority_clean=False)

    result = coordinator.coordinate_holoindex_postmerge(
        repo_root=workspace,
        db=db,
        environment=_environment(authority),
        git_runner=git,
    )

    assert result.accepted is False
    assert "authority_root_dirty" in result.rejection_reasons
    assert db.tasks == {}


def test_completion_requires_canonical_operational_proof(
    roots,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace, authority = roots
    db = FakeDB()
    git = FakeGit()
    _patch_state(monkeypatch, authority, git)
    queued = coordinator.coordinate_holoindex_postmerge(
        repo_root=workspace,
        db=db,
        environment=_environment(authority),
        git_runner=git,
    )
    _claim(db, queued.task_id)
    completed = coordinator.execute_holoindex_postmerge_task(
        repo_root=workspace,
        task_id=queued.task_id,
        context=db.tasks[queued.task_id]["context"],
        execution_claim=_execution_claim(db, queued.task_id),
        db=db,
        environment=_environment(authority),
        authority_transaction=lambda **_kwargs: _transaction_result(),
    )
    assert completed["ok"] is True

    current = coordinator.coordinate_holoindex_postmerge(
        repo_root=workspace,
        db=db,
        environment=_environment(authority),
        git_runner=git,
        prove_operational=lambda **_kwargs: SimpleNamespace(
            allowed=True,
            binding={
                "repo_head_sha": HEAD,
                "freshness_generation_id": "sha256:" + ("1" * 64),
                "freshness_receipt_digest": "sha256:" + ("2" * 64),
            },
        ),
    )
    assert current.accepted is True
    assert current.status == "CURRENT"

    rejected = coordinator.coordinate_holoindex_postmerge(
        repo_root=workspace,
        db=db,
        environment=_environment(authority),
        git_runner=git,
        prove_operational=lambda **_kwargs: SimpleNamespace(
            allowed=True,
            binding={
                "repo_head_sha": HEAD,
                "freshness_generation_id": "sha256:" + ("3" * 64),
                "freshness_receipt_digest": "sha256:" + ("2" * 64),
            },
        ),
    )
    assert rejected.accepted is False
    assert rejected.rejection_reasons == (
        "completion_operational_proof_invalid",
    )


class _Lease:
    def __init__(self, effects: list[str]) -> None:
        self.effects = effects

    def __enter__(self):
        self.effects.append("lease_enter")
        return self

    def __exit__(self, *_args):
        self.effects.append("lease_exit")


def test_authority_transaction_holds_lease_through_switch_and_refresh(
    roots,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    workspace, authority = roots
    git = FakeGit((HEAD, HEAD))
    _patch_state(monkeypatch, authority, git)
    effects: list[str] = []
    operational_args: dict[str, object] = {}

    def ensure_operational(**kwargs):
        operational_args.update(kwargs)
        effects.append("refresh")
        return SimpleNamespace(
            ready=True,
            status="REFRESHED",
            refreshed=True,
            error="",
            repo_head_sha=HEAD,
            generation_id="sha256:" + ("1" * 64),
            freshness_receipt_digest="sha256:" + ("2" * 64),
        )

    result = authority_transaction.advance_reddog_holoindex_authority(
        workspace_root=workspace,
        repo_root=authority,
        target_repo_head_sha=HEAD,
        expected_authority_root_digest=(
            authority_transaction.repository_root_digest(authority)
        ),
        environ={"HOLOINDEX_SSD_PATH": str(tmp_path / "ssd")},
        git_runner=git,
        cleanup_owner=lambda: effects.append("cleanup"),
        ensure_operational=ensure_operational,
        lease_factory=lambda _path: _Lease(effects),
    )

    assert result.ready is True
    assert effects == ["lease_enter", "cleanup", "refresh", "lease_exit"]
    assert operational_args["owner_runtime_root"] == workspace
    assert git.switch_target == HEAD


def test_authority_transaction_rejects_non_forward_update(
    roots,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    workspace, authority = roots

    def read_state(_path: Path):
        return _state(NEWER_HEAD)

    monkeypatch.setattr(authority_transaction, "read_repository_state", read_state)

    class NonAncestorGit(FakeGit):
        def __call__(self, argv: Sequence[str], cwd: Path):
            if tuple(argv)[:3] == ("git", "merge-base", "--is-ancestor"):
                return SimpleNamespace(returncode=1, stdout="", stderr="")
            return super().__call__(argv, cwd)

    git = NonAncestorGit()
    result = authority_transaction.advance_reddog_holoindex_authority(
        workspace_root=workspace,
        repo_root=authority,
        target_repo_head_sha=HEAD,
        expected_authority_root_digest=(
            authority_transaction.repository_root_digest(authority)
        ),
        environ={"HOLOINDEX_SSD_PATH": str(tmp_path / "ssd")},
        git_runner=git,
        ensure_operational=lambda **_kwargs: pytest.fail("must not refresh"),
        cleanup_owner=lambda: pytest.fail("must not stop owner"),
        lease_factory=lambda _path: _Lease([]),
    )

    assert result.ready is False
    assert result.error == "authority_non_forward_update_rejected"


def test_authority_transaction_supersession_stops_owner_and_advances_checkout(
    roots,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    workspace, authority = roots
    git = FakeGit((HEAD, NEWER_HEAD))
    _patch_state(monkeypatch, authority, git)
    effects: list[str] = []

    result = authority_transaction.advance_reddog_holoindex_authority(
        workspace_root=workspace,
        repo_root=authority,
        target_repo_head_sha=HEAD,
        expected_authority_root_digest=(
            authority_transaction.repository_root_digest(authority)
        ),
        environ={"HOLOINDEX_SSD_PATH": str(tmp_path / "ssd")},
        git_runner=git,
        cleanup_owner=lambda: effects.append("cleanup"),
        ensure_operational=lambda **_kwargs: _transaction_result(),
        lease_factory=lambda _path: _Lease(effects),
    )

    assert result.ready is False
    assert result.status == "SUPERSEDED"
    assert result.observed_origin_main_sha == NEWER_HEAD
    assert effects == [
        "lease_enter",
        "cleanup",
        "cleanup",
        "lease_exit",
    ]
    assert git.switch_target == NEWER_HEAD


def test_supersession_invalidation_failure_leaves_durable_block_marker(
    roots,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    workspace, authority = roots

    class LatestSwitchFails(FakeGit):
        def __call__(self, argv: Sequence[str], cwd: Path):
            if (
                tuple(argv)[:4] == ("git", "switch", "--detach", "--quiet")
                and tuple(argv)[4] == NEWER_HEAD
            ):
                return SimpleNamespace(returncode=1, stdout="", stderr="")
            return super().__call__(argv, cwd)

    git = LatestSwitchFails((HEAD, NEWER_HEAD))
    _patch_state(monkeypatch, authority, git)
    monkeypatch.setattr(
        authority_transaction,
        "_invalidate_generation",
        lambda **_kwargs: False,
    )

    result = authority_transaction.advance_reddog_holoindex_authority(
        workspace_root=workspace,
        repo_root=authority,
        target_repo_head_sha=HEAD,
        expected_authority_root_digest=(
            authority_transaction.repository_root_digest(authority)
        ),
        environ={"HOLOINDEX_SSD_PATH": str(tmp_path / "ssd")},
        git_runner=git,
        cleanup_owner=lambda: None,
        ensure_operational=lambda **_kwargs: _transaction_result(),
        lease_factory=lambda _path: _Lease([]),
    )

    marker = authority / ".holoindex_authority_blocked"
    assert result.ready is False
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
    git = FakeGit((HEAD, HEAD))

    def read_state(_path: Path):
        return _state(
            git.switch_target or HEAD,
            clean=not marker.exists(),
        )

    monkeypatch.setattr(authority_transaction, "read_repository_state", read_state)
    result = authority_transaction.advance_reddog_holoindex_authority(
        workspace_root=workspace,
        repo_root=authority,
        target_repo_head_sha=HEAD,
        expected_authority_root_digest=(
            authority_transaction.repository_root_digest(authority)
        ),
        environ={"HOLOINDEX_SSD_PATH": str(tmp_path / "ssd")},
        git_runner=git,
        cleanup_owner=lambda: None,
        ensure_operational=lambda **_kwargs: SimpleNamespace(
            ready=True,
            status="READY",
            refreshed=False,
            error="",
            repo_head_sha=HEAD,
            generation_id="sha256:" + ("1" * 64),
            freshness_receipt_digest="sha256:" + ("2" * 64),
        ),
        lease_factory=lambda _path: _Lease([]),
    )

    assert result.ready is True
    assert not marker.exists()


def test_coordinator_queues_and_executes_block_marker_recovery(
    roots,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    workspace, authority = roots
    marker = authority / ".holoindex_authority_blocked"
    marker.write_bytes(b"holoindex_authority_blocked_v1\n")
    git = FakeGit((NEWER_HEAD, NEWER_HEAD, NEWER_HEAD))

    def read_state(path: Path):
        if Path(path) == authority:
            return _state(
                git.switch_target or HEAD,
                clean=not marker.exists(),
            )
        return _state(HEAD)

    monkeypatch.setattr(contract, "read_repository_state", read_state)
    monkeypatch.setattr(authority_transaction, "read_repository_state", read_state)
    db = FakeDB()
    queued = coordinator.coordinate_holoindex_postmerge(
        repo_root=workspace,
        db=db,
        environment=_environment(authority),
        git_runner=git,
    )
    assert queued.accepted is True
    assert queued.target_repo_head_sha == NEWER_HEAD
    _claim(db, queued.task_id)

    def run_transaction(**kwargs):
        return authority_transaction.advance_reddog_holoindex_authority(
            **kwargs,
            git_runner=git,
            cleanup_owner=lambda: None,
            ensure_operational=lambda **_inner: SimpleNamespace(
                ready=True,
                status="REFRESHED",
                refreshed=True,
                error="",
                repo_head_sha=NEWER_HEAD,
                generation_id="sha256:" + ("1" * 64),
                freshness_receipt_digest="sha256:" + ("2" * 64),
            ),
            lease_factory=lambda _path: _Lease([]),
        )

    executed = coordinator.execute_holoindex_postmerge_task(
        repo_root=workspace,
        task_id=queued.task_id,
        context=db.tasks[queued.task_id]["context"],
        execution_claim=_execution_claim(db, queued.task_id),
        db=db,
        environment={
            **_environment(authority),
            "HOLOINDEX_SSD_PATH": str(tmp_path / "ssd"),
        },
        authority_transaction=run_transaction,
    )

    assert executed["ok"] is True
    assert db.tasks[queued.task_id]["status"] == "completed"
    assert not marker.exists()


def test_authority_transaction_rejects_substituted_authority_binding(
    roots,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    workspace, authority = roots
    git = FakeGit()
    _patch_state(monkeypatch, authority, git)

    result = authority_transaction.advance_reddog_holoindex_authority(
        workspace_root=workspace,
        repo_root=authority,
        target_repo_head_sha=HEAD,
        expected_authority_root_digest="sha256:" + ("0" * 64),
        environ={"HOLOINDEX_SSD_PATH": str(tmp_path / "ssd")},
        git_runner=git,
        ensure_operational=lambda **_kwargs: pytest.fail("must not refresh"),
        cleanup_owner=lambda: pytest.fail("must not stop owner"),
        lease_factory=lambda _path: _Lease([]),
    )

    assert result.ready is False
    assert result.error == "authority_root_binding_invalid"
    assert not any(call[:3] == ("git", "fetch", "--quiet") for call, _ in git.calls)


def test_postmerge_runtime_has_no_shell_or_destructive_git_path() -> None:
    source_paths = (
        Path(contract.__file__),
        Path(coordinator.__file__),
        Path(executor.__file__),
        Path(authority_transaction.__file__),
    )
    combined = "\n".join(
        path.read_text(encoding="utf-8") for path in source_paths
    )
    assert "reset --hard" not in combined
    assert '"pull"' not in combined
    assert '"checkout"' not in combined
    for path in source_paths:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                assert not (
                    isinstance(node.func, ast.Name)
                    and node.func.id in {"eval", "exec"}
                )
                for keyword in node.keywords:
                    if keyword.arg == "shell":
                        assert isinstance(keyword.value, ast.Constant)
                        assert keyword.value.value is False
