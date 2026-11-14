"""Adversarial active-consumption tests for verified v2 grounding evidence."""

from __future__ import annotations

from pathlib import Path

import pytest

import modules.communication.moltbot_bridge.src.reddog_readonly_0102_audit_worker_runtime as runtime
from holo_index.repository_state import RepositoryState
from modules.communication.moltbot_bridge.src.reddog_grounded_target_assignment_continuity import (
    canonical_digest,
)
from modules.communication.moltbot_bridge.src.reddog_readonly_audit_task_executor import (
    ReadOnlyAuditTaskRejectReason,
    execute_reddog_readonly_audit_task,
)
from modules.communication.moltbot_bridge.tests.test_reddog_readonly_audit_task_executor import (
    _EchoEvidenceModelRunner,
    _FakeQueryAdapter,
    _grounded_model_context,
    _model_context,
    _repo,
)


def _holo(context) -> _FakeQueryAdapter:
    receipt = context["grounding_receipt"]
    adapter = _FakeQueryAdapter(
        freshness="CURRENT", generation_id=receipt["holoindex_generation_id"],
        freshness_digest=receipt["holoindex_freshness_receipt_digest"])
    adapter.repo_head_sha = receipt["holoindex_repo_head_sha"]
    adapter.repo_root_digest = receipt["holoindex_repo_root_digest"]
    return adapter


def _bind_state(monkeypatch: pytest.MonkeyPatch, context) -> None:
    head = context["grounding_receipt"]["holoindex_repo_head_sha"]
    monkeypatch.setattr(
        runtime, "read_repository_state", lambda *args, **kwargs: RepositoryState(
            head_sha=head, clean=True, state_digest="sha256:test-clean"
        ),
    )


def _execute(root: Path, context, runner, holo):
    return execute_reddog_readonly_audit_task(
        task_context=context, repo_root=root, task_id="task-verified-grounding",
        model_runner=runner, holoindex_adapter=holo,
        codeindex_adapter=_FakeQueryAdapter(),
    )


def _replace_grounding(context, receipt) -> None:
    receipt["receipt_id"] = canonical_digest(
        {key: value for key, value in receipt.items() if key != "receipt_id"}
    )
    digest = canonical_digest(receipt)
    context["grounding_receipt"] = receipt
    context["grounding_receipt_id"] = receipt["receipt_id"]
    context["grounding_receipt_digest"] = digest
    context["assignment"]["grounding_receipt_id"] = receipt["receipt_id"]
    context["assignment"]["grounding_receipt_digest"] = digest


def test_model_backed_audit_rejects_v1_grounding_before_model(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    context = _grounded_model_context(root)
    receipt = dict(context["grounding_receipt"])
    receipt["schema_version"] = "reddog_grounded_target_receipt.v1"
    receipt["receipt_id"] = canonical_digest(
        {key: value for key, value in receipt.items() if key != "receipt_id"}
    )
    context["grounding_receipt"] = receipt
    context["grounding_receipt_id"] = receipt["receipt_id"]
    context["grounding_receipt_digest"] = canonical_digest(receipt)
    context["assignment"]["grounding_receipt_id"] = receipt["receipt_id"]
    context["assignment"]["grounding_receipt_digest"] = canonical_digest(receipt)
    runner, holo = _EchoEvidenceModelRunner(), _FakeQueryAdapter()

    result = _execute(root, context, runner, holo)

    assert result.accepted is False
    assert ReadOnlyAuditTaskRejectReason.GROUNDING_RECEIPT_INVALID in result.rejection_reasons
    assert runner.calls == [] and holo.calls == []


def test_model_backed_audit_rejects_missing_grounding_before_model(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    context = _model_context(root)
    for key in ("grounding_receipt", "grounding_receipt_id", "grounding_receipt_digest"):
        context.pop(key, None)
        context["assignment"].pop(key, None)
    context.pop("typed_targets", None)
    context.pop("work_focus", None)
    runner, holo = _EchoEvidenceModelRunner(), _FakeQueryAdapter()

    result = _execute(root, context, runner, holo)

    assert result.accepted is False
    assert ReadOnlyAuditTaskRejectReason.GROUNDING_RECEIPT_INVALID in result.rejection_reasons
    assert runner.calls == [] and holo.calls == []


def test_semantic_evidence_outside_assignment_scope_rejects_before_model(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    context = _grounded_model_context(root)
    context["assignment"]["allowed_read_targets"] = ["docs/work_ledger.schema.json"]
    runner, holo = _EchoEvidenceModelRunner(), _FakeQueryAdapter()

    result = _execute(root, context, runner, holo)

    assert result.accepted is False
    assert "grounding_assignment_binding_mismatch" in result.rejection_reasons
    assert runner.calls == [] and holo.calls == []


def test_unrelated_holo_path_rejects_before_model(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _repo(tmp_path)
    context = _grounded_model_context(root)
    holo = _holo(context)
    original_query = holo.query

    def query_with_unrelated(**kwargs):
        result = dict(original_query(**kwargs))
        result["hits"] = [*result["hits"], {
            "path": "modules/unrelated/attacker.py", "title": "unrelated injected hit"
        }]
        return result

    holo.query = query_with_unrelated
    _bind_state(monkeypatch, context)
    runner = _EchoEvidenceModelRunner()

    result = _execute(root, context, runner, holo)

    assert result.accepted is False
    assert ReadOnlyAuditTaskRejectReason.INDEX_QUERY_FAILED in result.rejection_reasons
    assert runner.calls == []


def test_model_context_uses_head_content_not_worktree_overlay(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _repo(tmp_path)
    context = _grounded_model_context(root)
    target = root / "modules" / "communication" / "moltbot_bridge" / "src" / "sample.py"
    target.write_text("ATTACKER WORKTREE OVERLAY\n", encoding="utf-8")
    _bind_state(monkeypatch, context)
    runner = _EchoEvidenceModelRunner()

    result = _execute(root, context, runner, _holo(context))

    assert result.accepted is True
    assert "ATTACKER WORKTREE OVERLAY" not in runner.calls[0]["context"]
    assert "RedDog worker grounding implementation fixture" in runner.calls[0]["context"]


@pytest.mark.parametrize("field", ["repo_state_head_sha", "repo_state_root_digest"])
def test_rehashed_repository_state_substitution_rejects_before_model(
    tmp_path: Path, field: str
) -> None:
    root = _repo(tmp_path)
    context = _grounded_model_context(root)
    receipt = dict(context["grounding_receipt"])
    receipt[field] = ("a" * 40) if field.endswith("head_sha") else ("sha256:" + "a" * 64)
    _replace_grounding(context, receipt)
    runner = _EchoEvidenceModelRunner()

    result = _execute(root, context, runner, _holo(context))

    assert result.accepted is False
    assert "grounding_semantic_generation_invalid" in result.rejection_reasons
    assert runner.calls == []


def test_holo_generation_drift_rejects_before_model(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    context = _grounded_model_context(root)
    holo = _holo(context)
    holo.generation_id = "sha256:" + "9" * 64
    runner = _EchoEvidenceModelRunner()

    result = _execute(root, context, runner, holo)

    assert result.accepted is False
    assert ReadOnlyAuditTaskRejectReason.REPOSITORY_STATE_CHANGED in result.rejection_reasons
    assert runner.calls == []
