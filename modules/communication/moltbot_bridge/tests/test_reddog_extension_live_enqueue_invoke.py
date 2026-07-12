"""Tests for RedDog extension-to-live-enqueue explicit valve invoke guard."""

from __future__ import annotations

import ast
from pathlib import Path

from modules.communication.moltbot_bridge.src.reddog_extension_live_enqueue_invoke import (
    EXTENSION_LIVE_ENQUEUE_INVOKE_ACCEPT,
    EXTENSION_LIVE_ENQUEUE_INVOKE_REJECT,
    ExtensionLiveEnqueueInvokeReason,
    invoke_reddog_extension_live_enqueue_explicit_valve,
)
from modules.communication.moltbot_bridge.src.reddog_operator_loop_wardrobe_selection import (
    WARDROBE_ARCHITECT_AUDIT,
    select_reddog_operator_loop_wardrobe_dryrun,
)
from modules.communication.moltbot_bridge.src.reddog_wre_execution_valve import (
    VALVE_CLOSED,
    VALVE_OPEN_LIVE_ENQUEUE,
)

REPO_ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = (
    REPO_ROOT
    / "modules"
    / "communication"
    / "moltbot_bridge"
    / "src"
    / "reddog_extension_live_enqueue_invoke.py"
)
EXTENSION_JS = REPO_ROOT / "extensions" / "foundups_advisory_workers" / "extension.js"


class _FakeWriter:
    def __init__(self) -> None:
        self.calls = []

    def enqueue_foundup_job(self, intake, receipt):
        self.calls.append(("foundup_job", dict(intake), dict(receipt)))
        return {"ok": True, "openclaw_queue_item_id": intake["proposed_job_id"], "agentdb_task_id": None}

    def enqueue_autonomous_task(self, intake, receipt):
        self.calls.append(("autonomous_task", dict(intake), dict(receipt)))
        return {"ok": True, "openclaw_queue_item_id": None, "agentdb_task_id": intake["proposed_task_id"]}


def _holo():
    return {
        "holoindex_query": "RedDog extension live enqueue explicit valve invoke",
        "holoindex_status": "bundle_json_ok",
        "index_gap_detected": False,
        "skill_hits": [{"skill_name": "autonomous_slice_worker"}],
    }


def _selection_receipt(**overrides):
    result = select_reddog_operator_loop_wardrobe_dryrun(
        "Invoke RedDog live enqueue through the explicit valve path.",
        authority_request="live_enqueue",
        holoindex_evidence=_holo(),
    )
    payload = result.receipt.to_dict()
    payload.update(overrides)
    return payload


def _adapter():
    return {
        "decision": "ADAPTER_DRYRUN_ACCEPT",
        "work_order_id": "wo-extension-live-enqueue-001",
        "proposed_intake": {
            "target_type": "foundup_job",
            "proposed_job_id": "reddog-fj-extension-001",
            "proposed_task_id": None,
            "work_order_id": "wo-extension-live-enqueue-001",
            "operation": "feature_slice",
            "requested_action": "build_foundup",
            "repo_scope": "FOUNDUPS/Foundups-Agent",
            "allowed_paths": ["modules/communication/moltbot_bridge/**"],
            "denied_paths": [".env"],
            "required_tests": [
                "modules/communication/moltbot_bridge/tests/test_reddog_extension_live_enqueue_invoke.py"
            ],
            "evidence_refs": ["policy_gate:sha256:policy"],
            "no_enqueue_performed": True,
            "no_execution_performed": True,
        },
        "adapter_receipt": {
            "adapter_receipt_id": "adapter-extension-live-enqueue-001",
            "adapter_receipt_digest": "sha256:adapter-extension",
            "decision": "ADAPTER_DRYRUN_ACCEPT",
            "target_type": "foundup_job",
            "work_order_id": "wo-extension-live-enqueue-001",
            "created_at": "2026-07-12T00:00:00+00:00",
            "rejection_reasons": [],
        },
        "rejection_reasons": [],
        "no_enqueue_performed": True,
        "no_execution_performed": True,
    }


def _policy():
    return {
        "decision": "POLICY_ACCEPT",
        "receipt_digest": "sha256:policy",
        "signature_gate_status": "SIGNATURE_GATE_ACCEPTED",
        "signature_gate_digest": "sha256:signed-authority",
        "no_execution_performed": True,
        "work_order_id": "wo-extension-live-enqueue-001",
    }


def _chain():
    return {
        "decision": "SIGNED_RECEIPT_CHAIN_ACCEPT",
        "accepted": True,
        "terminal_receipt_hash": "sha256:terminal-receipt",
        "no_execution_performed": True,
        "no_reward_settlement_performed": True,
    }


def _valve(state=VALVE_OPEN_LIVE_ENQUEUE):
    return {
        "valve_state": state,
        "work_order_id": "wo-extension-live-enqueue-001",
        "decision_digest": "sha256:live-enqueue-valve",
        "rejection_reasons": [],
        "gates_checked": ["execution_valve_evaluator"],
        "no_execution_performed": True,
        "intake_target": "foundup_job",
    }


def test_accepts_only_explicit_sovereign_selection_and_calls_injected_writer() -> None:
    writer = _FakeWriter()
    result = invoke_reddog_extension_live_enqueue_explicit_valve(
        explicit_live_enqueue_requested=True,
        selection_receipt=_selection_receipt(),
        adapter_result=_adapter(),
        policy_gate_receipt=_policy(),
        signed_receipt_chain_result=_chain(),
        valve_decision=_valve(),
        writer=writer,
        seen_live_enqueue_keys=set(),
    )

    assert result.decision == EXTENSION_LIVE_ENQUEUE_INVOKE_ACCEPT
    assert result.live_enqueue_result is not None
    assert result.live_enqueue_result.live_enqueue_performed is True
    assert result.live_enqueue_result.no_execution_performed is True
    assert writer.calls[0][0] == "foundup_job"


def test_rejects_when_explicit_request_missing_before_writer_call() -> None:
    writer = _FakeWriter()
    result = invoke_reddog_extension_live_enqueue_explicit_valve(
        explicit_live_enqueue_requested=False,
        selection_receipt=_selection_receipt(),
        adapter_result=_adapter(),
        policy_gate_receipt=_policy(),
        signed_receipt_chain_result=_chain(),
        valve_decision=_valve(),
        writer=writer,
    )

    assert result.decision == EXTENSION_LIVE_ENQUEUE_INVOKE_REJECT
    assert result.rejection_reasons == [ExtensionLiveEnqueueInvokeReason.EXPLICIT_INVOKE_MISSING]
    assert writer.calls == []


def test_rejects_missing_selection_receipt_before_writer_call() -> None:
    writer = _FakeWriter()
    result = invoke_reddog_extension_live_enqueue_explicit_valve(
        explicit_live_enqueue_requested=True,
        selection_receipt=None,
        adapter_result=_adapter(),
        policy_gate_receipt=_policy(),
        signed_receipt_chain_result=_chain(),
        valve_decision=_valve(),
        writer=writer,
    )

    assert result.decision == EXTENSION_LIVE_ENQUEUE_INVOKE_REJECT
    assert result.rejection_reasons == [ExtensionLiveEnqueueInvokeReason.SELECTION_RECEIPT_MISSING]
    assert writer.calls == []


def test_rejects_non_sovereign_selection_before_writer_call() -> None:
    writer = _FakeWriter()
    selection = _selection_receipt(
        selected_wardrobe=WARDROBE_ARCHITECT_AUDIT,
        execution_plane="audit_only",
        authority_boundary="no_authority",
    )
    result = invoke_reddog_extension_live_enqueue_explicit_valve(
        explicit_live_enqueue_requested=True,
        selection_receipt=selection,
        adapter_result=_adapter(),
        policy_gate_receipt=_policy(),
        signed_receipt_chain_result=_chain(),
        valve_decision=_valve(),
        writer=writer,
    )

    assert result.decision == EXTENSION_LIVE_ENQUEUE_INVOKE_REJECT
    assert ExtensionLiveEnqueueInvokeReason.SELECTION_NOT_SOVEREIGN in result.rejection_reasons
    assert ExtensionLiveEnqueueInvokeReason.SELECTION_PLANE_NOT_GOVERNED in result.rejection_reasons
    assert writer.calls == []


def test_rejects_selection_with_rejection_reasons_before_writer_call() -> None:
    writer = _FakeWriter()
    result = invoke_reddog_extension_live_enqueue_explicit_valve(
        explicit_live_enqueue_requested=True,
        selection_receipt=_selection_receipt(rejection_reasons=["write_sensitive_index_gap"]),
        adapter_result=_adapter(),
        policy_gate_receipt=_policy(),
        signed_receipt_chain_result=_chain(),
        valve_decision=_valve(),
        writer=writer,
    )

    assert result.decision == EXTENSION_LIVE_ENQUEUE_INVOKE_REJECT
    assert ExtensionLiveEnqueueInvokeReason.SELECTION_HAS_REJECTIONS in result.rejection_reasons
    assert writer.calls == []


def test_rejects_wrong_valve_before_writer_call() -> None:
    writer = _FakeWriter()
    result = invoke_reddog_extension_live_enqueue_explicit_valve(
        explicit_live_enqueue_requested=True,
        selection_receipt=_selection_receipt(),
        adapter_result=_adapter(),
        policy_gate_receipt=_policy(),
        signed_receipt_chain_result=_chain(),
        valve_decision=_valve(VALVE_CLOSED),
        writer=writer,
    )

    assert result.decision == EXTENSION_LIVE_ENQUEUE_INVOKE_REJECT
    assert result.rejection_reasons == [ExtensionLiveEnqueueInvokeReason.VALVE_NOT_LIVE_ENQUEUE]
    assert writer.calls == []


def test_lower_live_enqueue_rejection_is_preserved() -> None:
    result = invoke_reddog_extension_live_enqueue_explicit_valve(
        explicit_live_enqueue_requested=True,
        selection_receipt=_selection_receipt(),
        adapter_result=_adapter(),
        policy_gate_receipt=_policy(),
        signed_receipt_chain_result=_chain(),
        valve_decision=_valve(),
        writer=None,
    )

    assert result.decision == EXTENSION_LIVE_ENQUEUE_INVOKE_REJECT
    assert ExtensionLiveEnqueueInvokeReason.LIVE_ENQUEUE_REJECTED in result.rejection_reasons
    assert "REJECT_LIVE_ENQUEUE_WRITER_MISSING" in result.rejection_reasons


def test_ast_boundary_no_extension_runtime_concrete_writer_or_command_execution() -> None:
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
    imports = set()
    calls = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                calls.add(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                calls.add(node.func.attr)

    forbidden_import_fragments = (
        "subprocess",
        "reddog_openclaw_live_enqueue_writer",
        "openclaw_foundup_orchestrator",
        "agent_db",
        "hermes",
        "wre_core",
        "skillz",
    )
    forbidden_calls = {"open", "eval", "exec", "system", "popen", "run", "check_call", "check_output"}
    assert not any(fragment in imported for imported in imports for fragment in forbidden_import_fragments)
    assert not (calls & forbidden_calls)


def test_extension_runtime_not_modified_by_this_slice() -> None:
    text = EXTENSION_JS.read_text(encoding="utf-8")
    assert "invoke_reddog_extension_live_enqueue_explicit_valve" not in text
    assert "reddog_extension_live_enqueue_invoke.py" not in text
