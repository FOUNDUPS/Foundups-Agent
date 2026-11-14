"""Tests for model AutoResearch cycle feedback ledger admission."""

from __future__ import annotations

import ast
import json
from dataclasses import replace
from pathlib import Path

from modules.ai_intelligence.ai_gateway.src.model_autoresearch_cycle_feedback_ledger import (
    InMemoryModelAutoResearchCycleFeedbackLedgerStore,
    JsonlModelAutoResearchCycleFeedbackLedgerStore,
    MODEL_AUTORESEARCH_CYCLE_FEEDBACK_LEDGER_ADMISSION_ACCEPT,
    MODEL_AUTORESEARCH_CYCLE_FEEDBACK_LEDGER_ADMISSION_REJECT,
    MODEL_AUTORESEARCH_CYCLE_FEEDBACK_LEDGER_RECORD_TYPE,
    ModelAutoResearchCycleFeedbackLedgerAdmissionReason,
    admit_model_autoresearch_cycle_feedback,
)
from modules.ai_intelligence.ai_gateway.src.model_autoresearch_cycle_receipt import build_model_autoresearch_cycle_receipt
from modules.ai_intelligence.ai_gateway.tests.test_model_autoresearch_campaign_execution import REPO_ROOT
from modules.ai_intelligence.ai_gateway.tests.test_model_autoresearch_cycle_receipt import (
    _cycle_sources,
)


MODULE_PATH = (
    REPO_ROOT
    / "modules"
    / "ai_intelligence"
    / "ai_gateway"
    / "src"
    / "model_autoresearch_cycle_feedback_ledger.py"
)


class FailingCycleFeedbackLedgerStore(InMemoryModelAutoResearchCycleFeedbackLedgerStore):
    def append(self, record):
        raise RuntimeError("store failed")


def _cycle(tmp_path: Path):
    plan, execution, gate_supply = _cycle_sources(tmp_path)
    return build_model_autoresearch_cycle_receipt(
        plan_receipt=plan,
        campaign_execution_receipt=execution,
        promotion_gate_supply_receipt=gate_supply,
    )


def _cycle_with_plan(tmp_path: Path):
    plan, execution, gate_supply = _cycle_sources(tmp_path)
    cycle = build_model_autoresearch_cycle_receipt(
        plan_receipt=plan,
        campaign_execution_receipt=execution,
        promotion_gate_supply_receipt=gate_supply,
    )
    return cycle, plan


def test_admits_autoresearch_cycle_receipt_to_injected_ledger_store(tmp_path: Path) -> None:
    cycle, plan = _cycle_with_plan(tmp_path)
    store = InMemoryModelAutoResearchCycleFeedbackLedgerStore()

    result = admit_model_autoresearch_cycle_feedback(
        explicit_autoresearch_cycle_feedback_ledger_admission_requested=True,
        cycle_receipt=cycle.to_dict(),
        source_plan_receipt=plan.to_dict(),
        store=store,
    )

    assert result.decision == MODEL_AUTORESEARCH_CYCLE_FEEDBACK_LEDGER_ADMISSION_ACCEPT
    assert result.rejection_reasons == []
    assert result.feedback_write_performed is True
    assert result.receipt is not None
    assert result.receipt.cycle_receipt_id == cycle.receipt_id
    assert result.receipt.source_plan_receipt_id == cycle.source_plan_receipt_id
    assert result.receipt.no_provider_call_performed is True
    assert result.receipt.no_model_promotion_performed is True
    assert result.receipt.no_holoindex_reindex_performed is True
    assert len(store.records) == 1
    assert store.records[0]["record_type"] == MODEL_AUTORESEARCH_CYCLE_FEEDBACK_LEDGER_RECORD_TYPE
    assert store.records[0]["cycle_receipt_id"] == cycle.receipt_id
    assert store.records[0]["source_plan_context_bound"] is True
    assert store.records[0]["task_family"] == plan.policy.task_family
    assert store.records[0]["catalog_snapshot_id"] == plan.policy.catalog_snapshot_id
    assert store.records[0]["source_plan_receipt_digest"].startswith("sha256:")
    assert store.records[0]["executed_candidate_ids"] == list(cycle.executed_candidate_ids)


def test_jsonl_store_writes_one_feedback_record(tmp_path: Path) -> None:
    cycle, plan = _cycle_with_plan(tmp_path)
    path = tmp_path / "cycle_feedback.jsonl"
    store = JsonlModelAutoResearchCycleFeedbackLedgerStore(path)

    result = admit_model_autoresearch_cycle_feedback(
        explicit_autoresearch_cycle_feedback_ledger_admission_requested=True,
        cycle_receipt=cycle,
        source_plan_receipt=plan,
        store=store,
    )

    assert result.decision == MODEL_AUTORESEARCH_CYCLE_FEEDBACK_LEDGER_ADMISSION_ACCEPT
    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert len(records) == 1
    assert records[0]["cycle_receipt_id"] == cycle.receipt_id
    assert records[0]["source_plan_context_bound"] is True


def test_explicit_request_and_store_are_required(tmp_path: Path) -> None:
    cycle, plan = _cycle_with_plan(tmp_path)
    store = InMemoryModelAutoResearchCycleFeedbackLedgerStore()

    missing_request = admit_model_autoresearch_cycle_feedback(
        explicit_autoresearch_cycle_feedback_ledger_admission_requested=False,
        cycle_receipt=cycle.to_dict(),
        source_plan_receipt=plan.to_dict(),
        store=store,
    )
    missing_store = admit_model_autoresearch_cycle_feedback(
        explicit_autoresearch_cycle_feedback_ledger_admission_requested=True,
        cycle_receipt=cycle.to_dict(),
        source_plan_receipt=plan.to_dict(),
        store=None,
    )

    assert missing_request.decision == MODEL_AUTORESEARCH_CYCLE_FEEDBACK_LEDGER_ADMISSION_REJECT
    assert (
        ModelAutoResearchCycleFeedbackLedgerAdmissionReason.EXPLICIT_INVOKE_MISSING
        in missing_request.rejection_reasons
    )
    assert missing_store.decision == MODEL_AUTORESEARCH_CYCLE_FEEDBACK_LEDGER_ADMISSION_REJECT
    assert ModelAutoResearchCycleFeedbackLedgerAdmissionReason.STORE_REQUIRED in missing_store.rejection_reasons
    assert store.records == []


def test_tampered_serialized_cycle_receipt_rejects_before_store_write(tmp_path: Path) -> None:
    cycle, plan = _cycle_with_plan(tmp_path)
    cycle_payload = cycle.to_dict()
    cycle_payload["executed_candidate_ids"] = ["provider/tampered"]
    store = InMemoryModelAutoResearchCycleFeedbackLedgerStore()

    result = admit_model_autoresearch_cycle_feedback(
        explicit_autoresearch_cycle_feedback_ledger_admission_requested=True,
        cycle_receipt=cycle_payload,
        source_plan_receipt=plan.to_dict(),
        store=store,
    )

    assert result.decision == MODEL_AUTORESEARCH_CYCLE_FEEDBACK_LEDGER_ADMISSION_REJECT
    assert ModelAutoResearchCycleFeedbackLedgerAdmissionReason.CYCLE_RECEIPT_INVALID in result.rejection_reasons
    assert store.records == []


def test_mismatched_source_plan_rejects_before_store_write(tmp_path: Path) -> None:
    cycle, plan = _cycle_with_plan(tmp_path)
    mismatched_plan = plan.to_dict()
    mismatched_plan["policy"] = {
        **mismatched_plan["policy"],
        "task_family": "security",
    }
    # Rehydration rejects this as digest tamper before the mismatch check.
    store = InMemoryModelAutoResearchCycleFeedbackLedgerStore()
    tampered_result = admit_model_autoresearch_cycle_feedback(
        explicit_autoresearch_cycle_feedback_ledger_admission_requested=True,
        cycle_receipt=cycle.to_dict(),
        source_plan_receipt=mismatched_plan,
        store=store,
    )
    assert tampered_result.decision == MODEL_AUTORESEARCH_CYCLE_FEEDBACK_LEDGER_ADMISSION_REJECT
    assert (
        ModelAutoResearchCycleFeedbackLedgerAdmissionReason.SOURCE_PLAN_RECEIPT_INVALID
        in tampered_result.rejection_reasons
    )

    other_plan = replace(
        plan,
        receipt_id="model_autoresearch_plan:other",
    )
    mismatch_result = admit_model_autoresearch_cycle_feedback(
        explicit_autoresearch_cycle_feedback_ledger_admission_requested=True,
        cycle_receipt=cycle,
        source_plan_receipt=other_plan,
        store=store,
    )
    assert mismatch_result.decision == MODEL_AUTORESEARCH_CYCLE_FEEDBACK_LEDGER_ADMISSION_REJECT
    assert (
        ModelAutoResearchCycleFeedbackLedgerAdmissionReason.SOURCE_PLAN_RECEIPT_MISMATCH
        in mismatch_result.rejection_reasons
    )
    assert store.records == []


def test_non_feedback_eligible_cycle_never_enters_ledger(tmp_path: Path) -> None:
    cycle = replace(_cycle(tmp_path), executed_candidate_ids=())
    store = InMemoryModelAutoResearchCycleFeedbackLedgerStore()

    result = admit_model_autoresearch_cycle_feedback(
        explicit_autoresearch_cycle_feedback_ledger_admission_requested=True,
        cycle_receipt=cycle,
        store=store,
    )

    assert result.decision == MODEL_AUTORESEARCH_CYCLE_FEEDBACK_LEDGER_ADMISSION_REJECT
    assert (
        ModelAutoResearchCycleFeedbackLedgerAdmissionReason.CYCLE_NOT_FEEDBACK_ELIGIBLE
        in result.rejection_reasons
    )
    assert store.records == []


def test_secret_marker_in_cycle_feedback_record_rejects_before_store_write(tmp_path: Path) -> None:
    cycle = replace(_cycle(tmp_path), executed_candidate_ids=("provider/token=leak",))
    store = InMemoryModelAutoResearchCycleFeedbackLedgerStore()

    result = admit_model_autoresearch_cycle_feedback(
        explicit_autoresearch_cycle_feedback_ledger_admission_requested=True,
        cycle_receipt=cycle,
        store=store,
    )

    assert result.decision == MODEL_AUTORESEARCH_CYCLE_FEEDBACK_LEDGER_ADMISSION_REJECT
    assert ModelAutoResearchCycleFeedbackLedgerAdmissionReason.SECRET_IN_RECORD in result.rejection_reasons
    assert store.records == []


def test_store_failure_rejects_with_receipt_and_no_write_claim(tmp_path: Path) -> None:
    cycle = _cycle(tmp_path)

    result = admit_model_autoresearch_cycle_feedback(
        explicit_autoresearch_cycle_feedback_ledger_admission_requested=True,
        cycle_receipt=cycle.to_dict(),
        store=FailingCycleFeedbackLedgerStore(),
    )

    assert result.decision == MODEL_AUTORESEARCH_CYCLE_FEEDBACK_LEDGER_ADMISSION_REJECT
    assert ModelAutoResearchCycleFeedbackLedgerAdmissionReason.STORE_WRITE_FAILED in result.rejection_reasons
    assert result.feedback_write_performed is False
    assert result.receipt is not None
    assert result.receipt.feedback_record_id is None


def test_result_is_json_serializable(tmp_path: Path) -> None:
    cycle = _cycle(tmp_path)
    result = admit_model_autoresearch_cycle_feedback(
        explicit_autoresearch_cycle_feedback_ledger_admission_requested=True,
        cycle_receipt=cycle.to_dict(),
        store=InMemoryModelAutoResearchCycleFeedbackLedgerStore(),
    )

    payload = result.to_dict()
    assert payload["decision"] == MODEL_AUTORESEARCH_CYCLE_FEEDBACK_LEDGER_ADMISSION_ACCEPT
    json.dumps(payload, sort_keys=True)


def test_cycle_feedback_ledger_module_has_no_provider_network_command_or_runtime_imports() -> None:
    source = MODULE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    banned_import_roots = {
        "subprocess",
        "os",
        "shutil",
        "requests",
        "urllib",
        "http",
        "socket",
        "sqlite3",
        "holo_index",
        "git",
        "pattern_memory",
    }
    banned_calls = {"eval", "exec", "compile", "__import__"}

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name.split(".", 1)[0] not in banned_import_roots
        if isinstance(node, ast.ImportFrom) and node.module:
            assert node.module.split(".", 1)[0] not in banned_import_roots
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id not in banned_calls
