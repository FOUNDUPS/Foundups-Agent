"""Security tests for durable start-operations Holo repair."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from modules.communication.moltbot_bridge.src import (
    reddog_start_operations_holo_repair_contract as contract,
)
from modules.communication.moltbot_bridge.src.reddog_start_operations_holo_repair import (
    repair_start_operations_holoindex,
)
from modules.communication.moltbot_bridge.src.reddog_start_operations_holo_repair_contract import (
    CLAIM_AGENT_ID,
    holo_repair_task_context,
    holo_repair_task_id,
    validate_holo_repair_task_binding,
)


HEAD = "a" * 40
CONTROL_ID = "sha256:" + ("b" * 64)
GENERATION = "sha256:" + ("c" * 64)
RECEIPT = "sha256:" + ("d" * 64)


class _DB:
    def __init__(self) -> None:
        self.tasks = {}
        self.claims = []

    def create_autonomous_task_if_absent(self, **kwargs):
        task_id = kwargs["task_id"]
        if task_id in self.tasks:
            return False
        self.tasks[task_id] = {
            **kwargs,
            "status": "pending",
            "assigned_to": None,
        }
        return True

    def get_autonomous_task_by_id(self, task_id):
        return self.tasks.get(task_id)

    def requeue_autonomous_task(self, task_id, *, expected_status):
        task = self.tasks[task_id]
        if task["status"] != expected_status:
            return False
        task["status"] = "pending"
        task["assigned_to"] = None
        return True

    def assign_autonomous_task(self, task_id, agent_id):
        task = self.tasks[task_id]
        if task["status"] != "pending":
            return False
        task["status"] = "assigned"
        task["assigned_to"] = agent_id
        self.claims.append((task_id, agent_id))
        return True


def _owner(ready: bool):
    return SimpleNamespace(
        ready=ready,
        repo_head_sha=HEAD,
        generation_id=GENERATION if ready else "",
        freshness_receipt_digest=RECEIPT if ready else "",
    )


def _clean_repo(monkeypatch, root: Path) -> None:
    monkeypatch.setattr(
        contract,
        "read_repository_state",
        lambda _root: SimpleNamespace(proven_clean=True, head_sha=HEAD),
    )
    monkeypatch.setattr(
        contract,
        "repository_root_digest",
        lambda _root: "sha256:" + ("e" * 64),
    )


def test_current_owner_skips_agentdb_maintenance(tmp_path, monkeypatch) -> None:
    _clean_repo(monkeypatch, tmp_path)
    db = _DB()

    result = repair_start_operations_holoindex(
        repo_root=tmp_path,
        repo_head_sha=HEAD,
        control_request_id=CONTROL_ID,
        environ={},
        db=db,
        ensure_operational=lambda **_kwargs: _owner(True),
    )

    assert result.accepted is True
    assert result.status == "OWNER_READY"
    assert result.maintenance_performed is False
    assert db.tasks == {}


def test_semantic_miss_alone_never_triggers_maintenance() -> None:
    assert contract.repairable_grounding_failure(
        ("grounding_semantic_evidence_insufficient",)
    ) is False


def test_openclaw_claims_repairs_and_reproves_exact_owner(
    tmp_path, monkeypatch
) -> None:
    _clean_repo(monkeypatch, tmp_path)
    db = _DB()
    owner_results = iter((_owner(False), _owner(True)))

    def execute(task_id, *, repo_root):
        assert repo_root == tmp_path
        assert db.tasks[task_id]["assigned_to"] == CLAIM_AGENT_ID
        return {
            "ok": True,
            "structured_result": {
                "ready": True,
                "repo_head_sha": HEAD,
                "generation_id": GENERATION,
                "freshness_receipt_digest": RECEIPT,
            },
        }

    result = repair_start_operations_holoindex(
        repo_root=tmp_path,
        repo_head_sha=HEAD,
        control_request_id=CONTROL_ID,
        environ={},
        db=db,
        ensure_operational=lambda **_kwargs: next(owner_results),
        task_executor=execute,
    )

    assert result.accepted is True
    assert result.status == "REPAIRED"
    assert result.maintenance_performed is True
    assert db.claims == [(result.task_id, CLAIM_AGENT_ID)]
    assert db.tasks[result.task_id]["context"]["target_repo_head_sha"] == HEAD


def test_tampered_existing_task_fails_before_claim(tmp_path, monkeypatch) -> None:
    _clean_repo(monkeypatch, tmp_path)
    db = _DB()
    context = holo_repair_task_context(
        repo_root=tmp_path,
        repo_head_sha=HEAD,
        control_request_id=CONTROL_ID,
    )
    task_id = holo_repair_task_id(context)
    db.tasks[task_id] = {
        "task_id": task_id,
        "context": {**context, "target_repo_head_sha": "f" * 40},
        "status": "pending",
    }

    result = repair_start_operations_holoindex(
        repo_root=tmp_path,
        repo_head_sha=HEAD,
        control_request_id=CONTROL_ID,
        environ={},
        db=db,
        ensure_operational=lambda **_kwargs: _owner(False),
    )

    assert result.accepted is False
    assert result.rejection_reasons == ("holo_repair_task_conflict",)
    assert db.claims == []


def test_execution_proof_mismatch_fails_closed(tmp_path, monkeypatch) -> None:
    _clean_repo(monkeypatch, tmp_path)
    owners = iter((_owner(False), _owner(True)))
    result = repair_start_operations_holoindex(
        repo_root=tmp_path,
        repo_head_sha=HEAD,
        control_request_id=CONTROL_ID,
        environ={},
        db=_DB(),
        ensure_operational=lambda **_kwargs: next(owners),
        task_executor=lambda *_args, **_kwargs: {
            "ok": True,
            "structured_result": {
                "ready": True,
                "repo_head_sha": HEAD,
                "generation_id": "sha256:attacker",
                "freshness_receipt_digest": RECEIPT,
            },
        },
    )
    assert result.accepted is False
    assert result.status == "FAILED"
    assert result.rejection_reasons == (
        "holo_repair_operational_proof_invalid",
    )


def test_task_binding_rejects_changed_repository(tmp_path, monkeypatch) -> None:
    _clean_repo(monkeypatch, tmp_path)
    context = holo_repair_task_context(
        repo_root=tmp_path,
        repo_head_sha=HEAD,
        control_request_id=CONTROL_ID,
    )
    monkeypatch.setattr(
        contract,
        "read_repository_state",
        lambda _root: SimpleNamespace(proven_clean=True, head_sha="f" * 40),
    )
    reasons = validate_holo_repair_task_binding(
        repo_root=tmp_path,
        task_id=holo_repair_task_id(context),
        context=context,
    )
    assert reasons == ("holo_repair_repository_state_changed",)
