"""Tests for REDDOG_WRE_QUEUE_AUTHORIZED_MODEL_FEEDBACK_LEDGER_ADMISSION_INVOKE_PHASE1."""

from __future__ import annotations

import ast
from pathlib import Path

from modules.ai_intelligence.ai_gateway.src.model_feedback_ledger import (
    InMemoryModelFeedbackLedgerStore,
    ModelFeedbackLedgerAdmissionReason,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_authorized_model_feedback_ledger_admission_invoke import (
    QUEUE_AUTHORIZED_MODEL_FEEDBACK_LEDGER_ADMISSION_INVOKE_ACCEPT,
    QUEUE_AUTHORIZED_MODEL_FEEDBACK_LEDGER_ADMISSION_INVOKE_REJECT,
    QueueAuthorizedModelFeedbackLedgerAdmissionInvokeReason,
    invoke_reddog_wre_queue_authorized_model_feedback_ledger_admission,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_authorized_verified_outcome_ratchet_invoke import (
    QUEUE_AUTHORIZED_VERIFIED_OUTCOME_RATCHET_INVOKE_REJECT,
)
from modules.communication.moltbot_bridge.tests.test_reddog_wre_queue_authorized_verified_outcome_ratchet_invoke import (
    _invoke as _invoke_ratchet,
    _ratchet_request_with_model_feedback,
)


REPO_ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = (
    REPO_ROOT
    / "modules"
    / "communication"
    / "moltbot_bridge"
    / "src"
    / "reddog_wre_queue_authorized_model_feedback_ledger_admission_invoke.py"
)


def _accepted_queue_ratchet() -> dict:
    return _invoke_ratchet(request=_ratchet_request_with_model_feedback()).to_dict()


def _invoke(*, queue_ratchet: dict | None = None, store=None):
    return invoke_reddog_wre_queue_authorized_model_feedback_ledger_admission(
        explicit_queue_authorized_model_feedback_ledger_admission_requested=True,
        queue_verified_outcome_ratchet_result=queue_ratchet or _accepted_queue_ratchet(),
        store=store or InMemoryModelFeedbackLedgerStore(),
    )


def test_admits_model_feedback_after_accepted_queue_outcome_ratchet() -> None:
    store = InMemoryModelFeedbackLedgerStore()

    result = _invoke(store=store)

    assert result.decision == QUEUE_AUTHORIZED_MODEL_FEEDBACK_LEDGER_ADMISSION_INVOKE_ACCEPT
    assert result.rejection_reasons == []
    assert result.model_feedback_write_performed is True
    assert result.model_feedback_admission_result is not None
    assert (
        result.model_feedback_admission_result["decision"]
        == "MODEL_FEEDBACK_LEDGER_ADMISSION_ACCEPT"
    )
    assert result.no_provider_call_performed is True
    assert result.no_benchmark_execution_performed is True
    assert result.no_model_promotion_performed is True
    assert result.no_command_execution_performed is True
    assert result.no_pattern_memory_write_performed is True
    assert result.no_holoindex_reindex_performed is True
    assert len(store.records) == 1
    assert store.records[0]["record_type"] == "model_selection_outcome_feedback"
    assert store.records[0]["source_ratchet_id"].startswith("outcome_ratchet_")


def test_explicit_invoke_and_store_are_required() -> None:
    store = InMemoryModelFeedbackLedgerStore()

    missing_explicit = invoke_reddog_wre_queue_authorized_model_feedback_ledger_admission(
        explicit_queue_authorized_model_feedback_ledger_admission_requested=False,
        queue_verified_outcome_ratchet_result=_accepted_queue_ratchet(),
        store=store,
    )
    missing_store = invoke_reddog_wre_queue_authorized_model_feedback_ledger_admission(
        explicit_queue_authorized_model_feedback_ledger_admission_requested=True,
        queue_verified_outcome_ratchet_result=_accepted_queue_ratchet(),
        store=None,
    )

    assert missing_explicit.decision == QUEUE_AUTHORIZED_MODEL_FEEDBACK_LEDGER_ADMISSION_INVOKE_REJECT
    assert (
        QueueAuthorizedModelFeedbackLedgerAdmissionInvokeReason.EXPLICIT_INVOKE_MISSING
        in missing_explicit.rejection_reasons
    )
    assert missing_store.decision == QUEUE_AUTHORIZED_MODEL_FEEDBACK_LEDGER_ADMISSION_INVOKE_REJECT
    assert (
        QueueAuthorizedModelFeedbackLedgerAdmissionInvokeReason.STORE_REQUIRED
        in missing_store.rejection_reasons
    )
    assert store.records == []


def test_unaccepted_or_missing_ratchet_payload_rejects_before_store() -> None:
    store = InMemoryModelFeedbackLedgerStore()
    rejected = _accepted_queue_ratchet()
    rejected["decision"] = QUEUE_AUTHORIZED_VERIFIED_OUTCOME_RATCHET_INVOKE_REJECT
    missing_payload = _accepted_queue_ratchet()
    missing_payload["ratchet_result"] = {}

    first = _invoke(queue_ratchet=rejected, store=store)
    second = _invoke(queue_ratchet=missing_payload, store=store)

    assert first.decision == QUEUE_AUTHORIZED_MODEL_FEEDBACK_LEDGER_ADMISSION_INVOKE_REJECT
    assert (
        QueueAuthorizedModelFeedbackLedgerAdmissionInvokeReason.OUTCOME_RATCHET_INVOKE_NOT_ACCEPTED
        in first.rejection_reasons
    )
    assert second.decision == QUEUE_AUTHORIZED_MODEL_FEEDBACK_LEDGER_ADMISSION_INVOKE_REJECT
    assert (
        QueueAuthorizedModelFeedbackLedgerAdmissionInvokeReason.RATCHET_PAYLOAD_MISSING
        in second.rejection_reasons
    )
    assert store.records == []


def test_missing_model_outcome_receipt_rejects_before_store() -> None:
    store = InMemoryModelFeedbackLedgerStore()
    queue_ratchet = _accepted_queue_ratchet()
    queue_ratchet["model_selection_outcome_receipt"] = None

    result = _invoke(queue_ratchet=queue_ratchet, store=store)

    assert result.decision == QUEUE_AUTHORIZED_MODEL_FEEDBACK_LEDGER_ADMISSION_INVOKE_REJECT
    assert (
        QueueAuthorizedModelFeedbackLedgerAdmissionInvokeReason.MODEL_OUTCOME_RECEIPT_MISSING
        in result.rejection_reasons
    )
    assert store.records == []


def test_admission_rejection_bubbles_up_and_does_not_write() -> None:
    store = InMemoryModelFeedbackLedgerStore()
    queue_ratchet = _accepted_queue_ratchet()
    queue_ratchet["ratchet_result"]["receipt"]["verifier_receipt_id"] = "verify:other"

    result = _invoke(queue_ratchet=queue_ratchet, store=store)

    assert result.decision == QUEUE_AUTHORIZED_MODEL_FEEDBACK_LEDGER_ADMISSION_INVOKE_REJECT
    assert (
        QueueAuthorizedModelFeedbackLedgerAdmissionInvokeReason.ADMISSION_NOT_ACCEPTED
        in result.rejection_reasons
    )
    assert (
        ModelFeedbackLedgerAdmissionReason.VERIFIER_RECEIPT_MISMATCH
        in result.rejection_reasons
    )
    assert store.records == []


def test_module_has_no_provider_network_command_patternmemory_or_holoindex_authority() -> None:
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
    banned_calls = {"eval", "exec", "compile", "__import__", "open"}

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name.split(".", 1)[0] not in banned_import_roots
        if isinstance(node, ast.ImportFrom) and node.module:
            assert node.module.split(".", 1)[0] not in banned_import_roots
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id not in banned_calls
