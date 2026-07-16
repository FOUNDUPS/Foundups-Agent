"""One-shot bridge for RedDog thin client -> resident architect session.

Slice: REDDOG_EXTENSION_TO_RESIDENT_ARCHITECT_SESSION_RUNTIME_PHASE1

The editor runtime may call this script only when the resident architect
session is explicitly enabled. It delegates to the read-only audit/research/
decision E2E runtime and returns a bounded status packet. It does not perform
source mutation, shell work, worktree creation, PR creation, HoloIndex re-index,
Hermes dispatch, or live FoundUp enqueue.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Mapping

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from modules.communication.moltbot_bridge.src.reddog_readonly_audit_research_decision_e2e_runtime import (  # noqa: E402
    run_reddog_readonly_audit_research_decision_e2e,
)

RESIDENT_ARCHITECT_SESSION_ACCEPT = "RESIDENT_ARCHITECT_SESSION_ACCEPT"
RESIDENT_ARCHITECT_SESSION_REJECT = "RESIDENT_ARCHITECT_SESSION_REJECT"


def _read_payload() -> Dict[str, Any]:
    try:
        raw = sys.stdin.buffer.read()
        payload = json.loads(raw.decode("utf-8") if raw else "{}")
    except Exception as exc:
        return {"_bridge_error": "invalid_json", "_bridge_error_class": type(exc).__name__}
    return payload if isinstance(payload, dict) else {"_bridge_error": "payload_not_object"}


def _string(value: Any) -> str:
    return str(value) if value is not None else ""


def _int(value: Any, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default


def _reject(reason: str, *, bridge_error_class: str | None = None) -> Dict[str, Any]:
    output: Dict[str, Any] = {
        "decision": RESIDENT_ARCHITECT_SESSION_REJECT,
        "accepted": False,
        "status": "REJECT",
        "resident_backend_invoked": False,
        "python_invocation_performed": True,
        "snapshot_id": "",
        "swarm_id": "",
        "task_count": 0,
        "reports_persisted": 0,
        "architect_action": "",
        "architect_next_slice": "",
        "architect_determination_id": "",
        "queue_candidate_count": 0,
        "rejection_reasons": [reason],
        "no_shell_command_executed": True,
        "no_repo_mutation_performed": True,
        "no_holoindex_reindex_performed": True,
        "no_hermes_dispatch_performed": True,
        "no_worktree_operation_performed": True,
        "no_pr_created": True,
        "no_pattern_memory_promotion_performed": True,
        "no_live_foundup_enqueue_performed": True,
        "coding_worker_spawned": False,
    }
    if bridge_error_class:
        output["bridge_error_class"] = bridge_error_class
    return output


def _summarize_result(result: Any) -> Dict[str, Any]:
    initial = result.initial_bootstrap
    final = result.final_bootstrap
    final_status = final.status if final else ""
    reports_persisted = sum(1 for task in result.task_runs if task.persist_accepted)
    return {
        "decision": RESIDENT_ARCHITECT_SESSION_ACCEPT if result.accepted else RESIDENT_ARCHITECT_SESSION_REJECT,
        "accepted": bool(result.accepted),
        "status": str(result.status),
        "resident_backend_invoked": True,
        "red_dog_intent_submitted": True,
        "python_invocation_performed": True,
        "snapshot_id": _string(getattr(initial, "snapshot_receipt_id", "")),
        "final_snapshot_id": _string(getattr(final, "snapshot_receipt_id", "")) if final else "",
        "swarm_id": _string(getattr(initial, "swarm_id", "")),
        "cycle_id": _string(getattr(initial, "swarm_id", "")),
        "initial_status": _string(getattr(initial, "status", "")),
        "final_status": final_status,
        "task_count": len(result.task_runs),
        "reports_persisted": reports_persisted,
        "readonly_audit_tasks_enqueued": bool(result.readonly_audit_tasks_enqueued),
        "readonly_audit_tasks_executed": bool(result.readonly_audit_tasks_executed),
        "architect_action": _string(getattr(final, "backend_architect_determination_action", "")) if final else "",
        "architect_next_slice": (
            _string(getattr(final, "backend_architect_determination_next_slice", "")) if final else ""
        ),
        "architect_determination_id": (
            _string(getattr(final, "backend_architect_determination_id", "")) if final else ""
        ),
        "queue_candidate_count": int(
            getattr(final, "backend_architect_determination_queue_candidate_count", 0) if final else 0
        ),
        "rejection_reasons": list(result.rejection_reasons),
        "no_shell_command_executed": bool(result.no_shell_command_executed),
        "no_repo_mutation_performed": bool(result.no_repo_mutation_performed),
        "no_holoindex_reindex_performed": bool(result.no_holoindex_reindex_performed),
        "no_hermes_dispatch_performed": bool(result.no_hermes_dispatch_performed),
        "no_worktree_operation_performed": bool(result.no_worktree_operation_performed),
        "no_pr_created": bool(result.no_pr_created),
        "no_pattern_memory_promotion_performed": bool(result.no_pattern_memory_promotion_performed),
        "no_live_foundup_enqueue_performed": bool(result.no_live_foundup_enqueue_performed),
        "coding_worker_spawned": bool(result.coding_worker_spawned),
    }


def _result(payload: Mapping[str, Any]) -> Dict[str, Any]:
    if payload.get("_bridge_error"):
        return _reject(str(payload["_bridge_error"]), bridge_error_class=str(payload.get("_bridge_error_class") or "Error"))
    if payload.get("explicit_resident_architect_session_requested") is not True:
        return _reject("explicit_resident_architect_session_request_missing")
    intent = payload.get("red_dog_intent")
    if not isinstance(intent, dict) or intent.get("schema_version") != "reddog_intent.v1":
        return _reject("reddog_intent_missing_or_invalid")
    if intent.get("submits_executable_authority") is not False:
        return _reject("reddog_intent_must_not_submit_executable_authority")

    repo_root_text = payload.get("repo_root")
    repo_root = Path(str(repo_root_text)).resolve() if repo_root_text else REPO_ROOT
    try:
        result = run_reddog_readonly_audit_research_decision_e2e(
            repo_root=repo_root,
            work_state_path=_string(payload.get("work_state_path") or os.getenv("REDDOG_AUTHORITATIVE_WORK_STATE_PATH", "")),
            holoindex_receipt_path=_string(payload.get("holoindex_receipt_path") or os.getenv("HOLOINDEX_FRESHNESS_RECEIPT", "")),
            holoindex_ssd_path=_string(payload.get("holoindex_ssd_path") or os.getenv("HOLOINDEX_SSD_PATH", "")),
            requested_operation="extension_resident_architect_session",
            prompt_text=_string(payload.get("work_focus") or "extension resident RedDog architect session"),
            timeout_seconds=_int(payload.get("timeout_seconds"), 60),
        )
    except Exception as exc:
        output = _reject("resident_architect_session_bridge_failed", bridge_error_class=type(exc).__name__)
        output["resident_backend_invoked"] = True
        return output
    summary = _summarize_result(result)
    summary["intent_id"] = _string(payload.get("intent_id") or intent.get("intent_id"))
    return summary


def main() -> int:
    try:
        output = _result(_read_payload())
    except Exception as exc:
        output = _reject("resident_architect_session_bridge_failed", bridge_error_class=type(exc).__name__)
        output["resident_backend_invoked"] = True
    sys.stdout.write(json.dumps(output, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
