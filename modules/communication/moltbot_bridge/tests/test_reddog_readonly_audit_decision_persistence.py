"""Tests for REDDOG_READONLY_AUDIT_DECISION_PERSISTENCE_PHASE1."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from modules.communication.moltbot_bridge.src.reddog_readonly_audit_decision_persistence import (
    READONLY_AUDIT_DECISION_PERSIST_ACCEPT,
    READONLY_AUDIT_DECISION_PERSIST_REJECT,
    AgentDbReadOnlyAuditDecisionStore,
    ReadOnlyAuditDecisionPersistReason,
    persist_reddog_readonly_audit_decision,
)
from modules.communication.moltbot_bridge.src.reddog_readonly_audit_decision_runtime import (
    ACTION_FIX,
    READONLY_AUDIT_DECISION_ACCEPT,
    READONLY_AUDIT_DECISION_REJECT,
    ReadOnlyAuditDecisionReceipt,
)
from modules.infrastructure.database.src.db_manager import DatabaseManager


REPO_ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = (
    REPO_ROOT
    / "modules"
    / "communication"
    / "moltbot_bridge"
    / "src"
    / "reddog_readonly_audit_decision_persistence.py"
)


@pytest.fixture(autouse=True)
def isolated_agent_db(tmp_path, monkeypatch):
    monkeypatch.setenv("FOUNDUPS_DB_PATH", str(tmp_path / "foundups.db"))
    DatabaseManager.reset_for_tests()
    yield
    DatabaseManager.reset_for_tests()


def _decision(
    *,
    decision_id: str = "sha256:decision-1",
    swarm_id: str = "sha256:swarm-1",
    accepted: bool = True,
) -> ReadOnlyAuditDecisionReceipt:
    return ReadOnlyAuditDecisionReceipt(
        decision_id=decision_id,
        accepted=accepted,
        status=READONLY_AUDIT_DECISION_ACCEPT if accepted else READONLY_AUDIT_DECISION_REJECT,
        action=ACTION_FIX,
        swarm_id=swarm_id,
        report_bundle_id="sha256:bundle-1",
        report_count=5,
        finding_count=1,
        selected_finding_digest="sha256:finding-1",
        next_slice_name="REDDOG_NEXT_OPERATIONAL_SLICE_PHASE1",
        wsp15_priority="P1",
        decision_reasons=("selected:repo-code-finding-1",),
        rejection_reasons=(),
        finding_digests=("sha256:finding-1",),
    )


def test_persisted_decision_loads_by_id_and_latest() -> None:
    store = AgentDbReadOnlyAuditDecisionStore()
    decision = _decision()

    result = persist_reddog_readonly_audit_decision(decision=decision, store=store)
    loaded = store.load_readonly_audit_decision(decision.decision_id)
    latest = store.load_latest_readonly_audit_decision()

    assert result.accepted is True
    assert result.status == READONLY_AUDIT_DECISION_PERSIST_ACCEPT
    assert result.stored is True
    assert result.idempotent is False
    assert loaded is not None
    assert loaded["decision_id"] == decision.decision_id
    assert latest is not None
    assert latest["next_slice_name"] == "REDDOG_NEXT_OPERATIONAL_SLICE_PHASE1"
    assert result.no_decision_execution_performed is True


def test_persisted_decision_is_idempotent_for_same_payload() -> None:
    store = AgentDbReadOnlyAuditDecisionStore()
    decision = _decision()

    first = persist_reddog_readonly_audit_decision(decision=decision, store=store)
    second = persist_reddog_readonly_audit_decision(decision=decision, store=store)

    assert first.accepted is True
    assert second.accepted is True
    assert second.stored is False
    assert second.idempotent is True


def test_persist_rejects_conflicting_decision_for_same_swarm() -> None:
    store = AgentDbReadOnlyAuditDecisionStore()
    first = _decision(decision_id="sha256:decision-1", swarm_id="sha256:swarm-1")
    second = _decision(decision_id="sha256:decision-2", swarm_id="sha256:swarm-1")

    accepted = persist_reddog_readonly_audit_decision(decision=first, store=store)
    rejected = persist_reddog_readonly_audit_decision(decision=second, store=store)

    assert accepted.accepted is True
    assert rejected.accepted is False
    assert rejected.status == READONLY_AUDIT_DECISION_PERSIST_REJECT
    assert rejected.rejection_reasons == (ReadOnlyAuditDecisionPersistReason.STORE_REJECTED,)


def test_persist_rejects_unaccepted_or_side_effect_claiming_decision() -> None:
    rejected_decision = _decision(accepted=False)
    side_effect = _decision().to_dict()
    side_effect["no_repo_mutation_performed"] = False

    rejected = persist_reddog_readonly_audit_decision(decision=rejected_decision)
    side_effect_result = persist_reddog_readonly_audit_decision(decision=side_effect)

    assert rejected.accepted is False
    assert ReadOnlyAuditDecisionPersistReason.DECISION_NOT_ACCEPTED in rejected.rejection_reasons
    assert side_effect_result.accepted is False
    assert ReadOnlyAuditDecisionPersistReason.DECISION_CLAIMS_SIDE_EFFECT in side_effect_result.rejection_reasons


def test_decision_persistence_module_has_no_execution_or_repo_mutation() -> None:
    source = MODULE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    forbidden_import_roots = {
        "subprocess",
        "requests",
        "httpx",
        "socket",
        "openclaw_supervisor",
        "hermes_job_executor",
    }
    forbidden_text = (
        "execute_skill",
        "holo_index.py --index",
        "create_autonomous_task",
        "write_text",
        "mkdir",
        "git push",
        "gh pr",
    )
    for token in forbidden_text:
        assert token not in source
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name.split(".")[0] not in forbidden_import_roots
        if isinstance(node, ast.ImportFrom):
            assert (node.module or "").split(".")[0] not in forbidden_import_roots
