"""Tests for model feedback ledger admission."""

from __future__ import annotations

import ast
import json
from pathlib import Path

from modules.ai_intelligence.ai_gateway.src.model_feedback_ledger import (
    InMemoryModelFeedbackLedgerStore,
    MODEL_FEEDBACK_LEDGER_ADMISSION_ACCEPT,
    MODEL_FEEDBACK_LEDGER_ADMISSION_REJECT,
    MODEL_FEEDBACK_LEDGER_RECORD_TYPE,
    ModelFeedbackLedgerAdmissionReason,
    admit_model_selection_outcome_feedback,
)
from modules.ai_intelligence.ai_gateway.src.model_intelligence_catalog import (
    ModelCapabilityCard,
    PromotionState,
    build_model_catalog_snapshot,
)
from modules.ai_intelligence.ai_gateway.src.model_intelligence_outcomes import (
    ModelOutcomeMetrics,
    VerifierDecision,
    build_model_selection_outcome_receipt,
)
from modules.ai_intelligence.ai_gateway.src.model_intelligence_selection import (
    ModelTaskRequirements,
    SelectionDecision,
    select_models_for_task,
)


REPO_ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = (
    REPO_ROOT
    / "modules"
    / "ai_intelligence"
    / "ai_gateway"
    / "src"
    / "model_feedback_ledger.py"
)


class FailingModelFeedbackLedgerStore(InMemoryModelFeedbackLedgerStore):
    def append(self, record):
        raise RuntimeError("store failed")


def _selected_receipt():
    snapshot = build_model_catalog_snapshot(
        (
            ModelCapabilityCard(
                provider="provider",
                model_id="provider/model",
                canonical_model_id="provider/model",
                source="test",
                promotion_state=PromotionState.CANDIDATE,
                task_families=("architecture",),
            ).normalized(),
        ),
        generated_at="2026-07-16T00:00:00+00:00",
    )
    receipt = select_models_for_task(snapshot, ModelTaskRequirements(task_family="architecture"))
    assert receipt.decision == SelectionDecision.SELECTED
    return receipt


def _runtime_binding_receipt(selection):
    return {
        "schema_version": "reddog_model_runtime_binding_receipt.v1",
        "receipt_id": "reddog_model_runtime_binding:test",
        "decision": "bound",
        "runtime_surface": "backend_architect",
        "catalog_snapshot_id": selection.catalog_snapshot_id,
        "selection_receipt_id": selection.receipt_id,
        "task_family": selection.requirements.task_family,
        "principal_model": selection.selected_model_ids[0],
        "panel_models": [],
        "role_bindings": [
            {
                "role": "principal",
                "model_id": selection.selected_model_ids[0],
                "provider": "provider",
            }
        ],
        "benchmark_evidence_receipt_ids": ["model_benchmark_evidence:test"],
        "promotion_evidence_receipt_ids": ["model_promotion_evidence:test"],
        "signed_promotion_receipt_ids": ["signature:test"],
        "policy": {
            "schema_version": "reddog_model_runtime_binding_policy.v1",
            "task_family": selection.requirements.task_family,
            "runtime_surface": "backend_architect",
            "min_verifier_pass_rate": 0.9,
            "required_task_set_digest": "sha256:taskset",
            "required_held_out_split_digest": "sha256:heldout",
            "required_verifier_digest": "sha256:verifier",
            "max_panel_models": 4,
            "required_panel_topology_digest": None,
            "authority_receipt_id": "authority:test",
        },
        "rejection_reasons": [],
    }


def _accepted_outcome(*, verification_receipt_id: str = "verify:1", with_runtime: bool = True):
    selection = _selected_receipt()
    return build_model_selection_outcome_receipt(
        selection,
        model_runtime_binding_receipt=(
            _runtime_binding_receipt(selection) if with_runtime else None
        ),
        verifier_decision=VerifierDecision.ACCEPT,
        verification_receipt_ids=(verification_receipt_id,),
        task_completed=True,
        evidence_correct=True,
        metrics=ModelOutcomeMetrics(latency_ms=100, input_tokens=200, output_tokens=50),
    )


def _source_ratchet(outcome) -> dict:
    return {
        "ratchet_id": "outcome_ratchet_1234",
        "work_order_id": "wo-model-feedback-1",
        "verifier_receipt_id": outcome.verification_receipt_ids[0],
        "model_runtime_binding_receipt_id": outcome.model_runtime_binding_receipt_id,
        "model_runtime_binding_digest": outcome.model_runtime_binding_digest,
        "rejection_reasons": [],
    }


def test_admits_feedback_eligible_outcome_to_injected_ledger_store():
    outcome = _accepted_outcome()
    store = InMemoryModelFeedbackLedgerStore()

    result = admit_model_selection_outcome_feedback(
        explicit_model_feedback_ledger_admission_requested=True,
        model_selection_outcome_receipt=outcome.to_dict(),
        source_ratchet_receipt=_source_ratchet(outcome),
        store=store,
    )

    assert result.decision == MODEL_FEEDBACK_LEDGER_ADMISSION_ACCEPT
    assert result.rejection_reasons == []
    assert result.feedback_write_performed is True
    assert result.receipt is not None
    assert result.receipt.outcome_receipt_id == outcome.receipt_id
    assert result.receipt.model_runtime_binding_receipt_id == "reddog_model_runtime_binding:test"
    assert result.receipt.source_ratchet_id == "outcome_ratchet_1234"
    assert result.receipt.no_provider_call_performed is True
    assert result.receipt.no_benchmark_execution_performed is True
    assert result.receipt.no_model_promotion_performed is True
    assert result.receipt.no_holoindex_reindex_performed is True
    assert len(store.records) == 1
    assert store.records[0]["record_type"] == MODEL_FEEDBACK_LEDGER_RECORD_TYPE
    assert store.records[0]["outcome_receipt_id"] == outcome.receipt_id
    assert store.records[0]["source_ratchet_id"] == "outcome_ratchet_1234"


def test_explicit_request_and_store_are_required():
    outcome = _accepted_outcome()
    store = InMemoryModelFeedbackLedgerStore()

    missing_request = admit_model_selection_outcome_feedback(
        explicit_model_feedback_ledger_admission_requested=False,
        model_selection_outcome_receipt=outcome.to_dict(),
        store=store,
    )
    missing_store = admit_model_selection_outcome_feedback(
        explicit_model_feedback_ledger_admission_requested=True,
        model_selection_outcome_receipt=outcome.to_dict(),
        store=None,
    )

    assert missing_request.decision == MODEL_FEEDBACK_LEDGER_ADMISSION_REJECT
    assert ModelFeedbackLedgerAdmissionReason.EXPLICIT_INVOKE_MISSING in missing_request.rejection_reasons
    assert missing_store.decision == MODEL_FEEDBACK_LEDGER_ADMISSION_REJECT
    assert ModelFeedbackLedgerAdmissionReason.STORE_REQUIRED in missing_store.rejection_reasons
    assert store.records == []


def test_tampered_serialized_outcome_rejects_before_store_write():
    outcome = _accepted_outcome().to_dict()
    outcome["selected_model_ids"] = ["provider/other"]
    store = InMemoryModelFeedbackLedgerStore()

    result = admit_model_selection_outcome_feedback(
        explicit_model_feedback_ledger_admission_requested=True,
        model_selection_outcome_receipt=outcome,
        store=store,
    )

    assert result.decision == MODEL_FEEDBACK_LEDGER_ADMISSION_REJECT
    assert ModelFeedbackLedgerAdmissionReason.OUTCOME_RECEIPT_INVALID in result.rejection_reasons
    assert store.records == []


def test_rejected_or_incomplete_outcome_never_enters_feedback_ledger():
    selection = _selected_receipt()
    outcome = build_model_selection_outcome_receipt(
        selection,
        verifier_decision=VerifierDecision.REJECT,
        verification_receipt_ids=("verify:1",),
        task_completed=True,
        evidence_correct=True,
    )
    store = InMemoryModelFeedbackLedgerStore()

    result = admit_model_selection_outcome_feedback(
        explicit_model_feedback_ledger_admission_requested=True,
        model_selection_outcome_receipt=outcome,
        store=store,
    )

    assert result.decision == MODEL_FEEDBACK_LEDGER_ADMISSION_REJECT
    assert ModelFeedbackLedgerAdmissionReason.OUTCOME_NOT_FEEDBACK_ELIGIBLE in result.rejection_reasons
    assert store.records == []


def test_source_ratchet_rejection_verifier_and_runtime_mismatch_fail_closed():
    outcome = _accepted_outcome()

    cases = [
        (
            {"rejection_reasons": ["FAIL_REGRESSION"]},
            ModelFeedbackLedgerAdmissionReason.SOURCE_RATCHET_REJECTED,
        ),
        (
            {"verifier_receipt_id": "verify:other"},
            ModelFeedbackLedgerAdmissionReason.VERIFIER_RECEIPT_MISMATCH,
        ),
        (
            {"model_runtime_binding_digest": "sha256:" + "0" * 64},
            ModelFeedbackLedgerAdmissionReason.MODEL_RUNTIME_BINDING_MISMATCH,
        ),
    ]

    for override, expected_reason in cases:
        source = _source_ratchet(outcome)
        source.update(override)
        store = InMemoryModelFeedbackLedgerStore()
        result = admit_model_selection_outcome_feedback(
            explicit_model_feedback_ledger_admission_requested=True,
            model_selection_outcome_receipt=outcome.to_dict(),
            source_ratchet_receipt=source,
            store=store,
        )
        assert result.decision == MODEL_FEEDBACK_LEDGER_ADMISSION_REJECT
        assert expected_reason in result.rejection_reasons
        assert store.records == []


def test_secret_marker_in_feedback_record_rejects_before_store_write():
    outcome = _accepted_outcome(verification_receipt_id="verify:token=leak")
    store = InMemoryModelFeedbackLedgerStore()

    result = admit_model_selection_outcome_feedback(
        explicit_model_feedback_ledger_admission_requested=True,
        model_selection_outcome_receipt=outcome.to_dict(),
        store=store,
    )

    assert result.decision == MODEL_FEEDBACK_LEDGER_ADMISSION_REJECT
    assert ModelFeedbackLedgerAdmissionReason.SECRET_IN_RECORD in result.rejection_reasons
    assert store.records == []


def test_store_failure_rejects_with_receipt_and_no_write_claim():
    outcome = _accepted_outcome()

    result = admit_model_selection_outcome_feedback(
        explicit_model_feedback_ledger_admission_requested=True,
        model_selection_outcome_receipt=outcome.to_dict(),
        source_ratchet_receipt=_source_ratchet(outcome),
        store=FailingModelFeedbackLedgerStore(),
    )

    assert result.decision == MODEL_FEEDBACK_LEDGER_ADMISSION_REJECT
    assert ModelFeedbackLedgerAdmissionReason.STORE_WRITE_FAILED in result.rejection_reasons
    assert result.feedback_write_performed is False
    assert result.receipt is not None
    assert result.receipt.feedback_record_id is None


def test_result_is_json_serializable():
    outcome = _accepted_outcome()
    result = admit_model_selection_outcome_feedback(
        explicit_model_feedback_ledger_admission_requested=True,
        model_selection_outcome_receipt=outcome.to_dict(),
        source_ratchet_receipt=_source_ratchet(outcome),
        store=InMemoryModelFeedbackLedgerStore(),
    )

    payload = result.to_dict()
    assert payload["decision"] == MODEL_FEEDBACK_LEDGER_ADMISSION_ACCEPT
    json.dumps(payload, sort_keys=True)


def test_model_feedback_ledger_module_has_no_provider_network_command_or_runtime_imports():
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
