"""Tests for the resident model-feedback ledger admission stage handler."""

from __future__ import annotations

import ast
from pathlib import Path

from modules.ai_intelligence.ai_gateway.src.model_feedback_ledger import (
    InMemoryModelFeedbackLedgerStore,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_chain_results_store import (
    InMemoryResidentQueueChainResultsStore,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_model_feedback_ledger_admission_handler import (
    FAIL_DISPATCH_NEXT_ACTION_MISMATCH,
    FAIL_DISPATCH_STAGE_MISMATCH,
    FAIL_MODEL_FEEDBACK_LEDGER_STORE_MISSING,
    MODEL_FEEDBACK_ADMISSION_STAGE_KEY,
    build_reddog_resident_queue_model_feedback_ledger_admission_stage_handler,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_next_stage_dispatch import (
    ResidentQueueStageDispatchRequest,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_orchestration_plan import (
    NEXT_QUEUE_MODEL_FEEDBACK_LEDGER_ADMISSION_INVOKE,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_authorized_model_feedback_ledger_admission_invoke import (
    QUEUE_AUTHORIZED_MODEL_FEEDBACK_LEDGER_ADMISSION_INVOKE_ACCEPT,
    QUEUE_AUTHORIZED_MODEL_FEEDBACK_LEDGER_ADMISSION_INVOKE_REJECT,
)
from modules.communication.moltbot_bridge.tests.test_reddog_wre_queue_authorized_verified_outcome_ratchet_invoke import (
    _invoke as _invoke_ratchet,
    _ratchet_request,
    _ratchet_request_with_model_feedback,
)


REPO_ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = (
    REPO_ROOT
    / "modules"
    / "communication"
    / "moltbot_bridge"
    / "src"
    / "reddog_resident_queue_model_feedback_ledger_admission_handler.py"
)


def _request(**overrides: object) -> ResidentQueueStageDispatchRequest:
    payload = {
        "stage_key": MODEL_FEEDBACK_ADMISSION_STAGE_KEY,
        "next_action": NEXT_QUEUE_MODEL_FEEDBACK_LEDGER_ADMISSION_INVOKE,
        "queue_item_id": "queue-1",
        "selected_slice": "SLICE",
        "plan_id": "plan-1",
        "accepted_stages": ("verified_outcome_ratchet",),
    }
    payload.update(overrides)
    return ResidentQueueStageDispatchRequest(**payload)


def _store_with_ratchet(*, with_model_feedback: bool) -> InMemoryResidentQueueChainResultsStore:
    request = _ratchet_request_with_model_feedback() if with_model_feedback else _ratchet_request()
    result = _invoke_ratchet(request=request).to_dict()
    return InMemoryResidentQueueChainResultsStore(
        {
            "schema_version": "reddog_resident_queue_chain_results.v1",
            "stage_results": {"verified_outcome_ratchet": result},
        }
    )


def test_handler_admits_model_feedback_when_ratchet_emitted_outcome_receipt() -> None:
    ledger = InMemoryModelFeedbackLedgerStore()
    handler = build_reddog_resident_queue_model_feedback_ledger_admission_stage_handler(
        chain_results_store=_store_with_ratchet(with_model_feedback=True),
        store=ledger,
    )

    result = handler(_request())

    assert result["decision"] == QUEUE_AUTHORIZED_MODEL_FEEDBACK_LEDGER_ADMISSION_INVOKE_ACCEPT
    assert result["model_feedback_write_performed"] is True
    assert result["no_pattern_memory_write_performed"] is True
    assert result["no_holoindex_reindex_performed"] is True
    assert len(ledger.records) == 1
    assert ledger.records[0]["record_type"] == "model_selection_outcome_feedback"


def test_handler_records_noop_when_ratchet_has_no_model_feedback_receipt() -> None:
    handler = build_reddog_resident_queue_model_feedback_ledger_admission_stage_handler(
        chain_results_store=_store_with_ratchet(with_model_feedback=False),
        store=None,
    )

    result = handler(_request())

    assert result["decision"] == QUEUE_AUTHORIZED_MODEL_FEEDBACK_LEDGER_ADMISSION_INVOKE_ACCEPT
    assert result["model_feedback_write_performed"] is False
    assert result["model_feedback_noop_reason"] == "no_model_selection_outcome_receipt"


def test_handler_requires_store_when_model_feedback_receipt_exists() -> None:
    handler = build_reddog_resident_queue_model_feedback_ledger_admission_stage_handler(
        chain_results_store=_store_with_ratchet(with_model_feedback=True),
        store=None,
    )

    result = handler(_request())

    assert result["decision"] == QUEUE_AUTHORIZED_MODEL_FEEDBACK_LEDGER_ADMISSION_INVOKE_REJECT
    assert FAIL_MODEL_FEEDBACK_LEDGER_STORE_MISSING in result["rejection_reasons"]


def test_handler_rejects_wrong_stage_or_action() -> None:
    handler = build_reddog_resident_queue_model_feedback_ledger_admission_stage_handler(
        chain_results_store=_store_with_ratchet(with_model_feedback=False),
        store=None,
    )

    wrong_stage = handler(_request(stage_key="other"))
    wrong_action = handler(_request(next_action="OTHER_ACTION"))

    assert wrong_stage["decision"] == QUEUE_AUTHORIZED_MODEL_FEEDBACK_LEDGER_ADMISSION_INVOKE_REJECT
    assert FAIL_DISPATCH_STAGE_MISMATCH in wrong_stage["rejection_reasons"]
    assert wrong_action["decision"] == QUEUE_AUTHORIZED_MODEL_FEEDBACK_LEDGER_ADMISSION_INVOKE_REJECT
    assert FAIL_DISPATCH_NEXT_ACTION_MISMATCH in wrong_action["rejection_reasons"]


def test_handler_module_has_no_provider_network_command_patternmemory_or_holoindex_authority() -> None:
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
