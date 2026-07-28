"""Canonical bounded result receipts for every signed-worker execution path."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from modules.infrastructure.database.src.signed_worker_result_history import (
    RESULT_HISTORY_LIMIT,
    canonical_digest,
)


DIRECT_ACCEPT = "DIRECT_ACCEPT"
DIRECT_REJECT = "DIRECT_REJECT"
DIRECT_REQUEUED = "DIRECT_REQUEUED"


def build_signed_worker_task_result_receipt(
    *,
    base_context: Mapping[str, Any],
    claim_status: str,
    result: Mapping[str, Any],
    runner_result: Mapping[str, Any] | None = None,
    rejection_reasons: Sequence[str] = (),
) -> dict[str, Any]:
    """Build one canonical full receipt without persisting it."""
    result_payload = dict(result)
    result_supplied = bool(result_payload)
    runner_payload = _runner_payload(result_payload, runner_result)
    receipt = {
        "schema_version": "reddog_signed_worker_task_result.v1",
        "claim_status": str(claim_status or ""),
        "accepted": (
            result_payload.get("accepted") is True
            or result_payload.get("ok") is True
        ),
        "decision": str(result_payload.get("decision") or ""),
        "receipt_id": str(result_payload.get("receipt_id") or ""),
        **_identity_fields(base_context, result_payload),
        "rejection_reasons": _reasons(
            tuple(rejection_reasons)
            or tuple(result_payload.get("rejection_reasons") or ())
        ),
        "runner_result_digest": canonical_digest(runner_payload)
        if runner_payload else "",
        "run_result_digest": (
            canonical_digest(result_payload) if result_supplied else ""
        ),
        "runner_result_summary": _runner_summary(runner_payload),
        **_effect_fields(result_payload, supplied=result_supplied),
    }
    assurance_completion = assurance_completion_request_from_runner(
        runner_payload
    )
    if assurance_completion:
        receipt["assurance_completion_request"] = assurance_completion
    receipt["receipt_digest"] = canonical_digest(receipt)
    return receipt


def _identity_fields(
    base_context: Mapping[str, Any],
    result: Mapping[str, Any],
) -> dict[str, str]:
    return {
        field: str(result.get(field) or base_context.get(field) or "")
        for field in ("worker_role", "worker_runtime", "capability")
    }


def append_signed_worker_result_history(
    context: Mapping[str, Any], receipt: Mapping[str, Any]
) -> dict[str, Any]:
    """Append one linked entry while retaining only the latest context window."""

    updated = dict(context)
    raw_history = updated.get("signed_worker_task_result_receipts", [])
    if not isinstance(raw_history, list) or any(
        not isinstance(item, Mapping) for item in raw_history
    ):
        raise ValueError("signed_worker_result_history_malformed")
    history = [dict(item) for item in raw_history]
    prior = history[-1] if history else None
    sequence = int(prior.get("attempt_sequence") or 0) + 1 if prior else 1
    entry = {
        "attempt_sequence": sequence,
        "claim_status": str(receipt.get("claim_status") or ""),
        "receipt_id": str(receipt.get("receipt_id") or ""),
        "receipt_digest": str(receipt.get("receipt_digest") or ""),
        "previous_history_digest": (
            str(prior.get("history_entry_digest") or "")
            if prior
            else canonical_digest([])
        ),
    }
    entry["history_entry_digest"] = canonical_digest(entry)
    history.append(entry)
    updated["signed_worker_task_last_result"] = dict(receipt)
    updated["signed_worker_task_result_receipts"] = history[-RESULT_HISTORY_LIMIT:]
    return updated


def _runner_payload(
    result: Mapping[str, Any], supplied: Mapping[str, Any] | None
) -> dict[str, Any]:
    if isinstance(supplied, Mapping):
        return dict(supplied)
    nested = result.get("runner_result")
    if isinstance(nested, Mapping):
        return dict(nested)
    structured = result.get("structured_result")
    return dict(structured) if isinstance(structured, Mapping) else {}


def _runner_summary(payload: Mapping[str, Any]) -> dict[str, Any]:
    if not payload:
        return {}
    nested = payload.get("runner_result")
    effective = dict(nested) if isinstance(nested, Mapping) else dict(payload)
    bootstrap = effective.get("bootstrap_result")
    bootstrap = dict(bootstrap) if isinstance(bootstrap, Mapping) else {}
    return {
        "accepted": payload.get("accepted") is True or effective.get("accepted") is True,
        "decision": str(payload.get("decision") or effective.get("decision") or ""),
        "receipt_id": str(payload.get("receipt_id") or effective.get("receipt_id") or ""),
        "queue_item_id": str(effective.get("queue_item_id") or ""),
        "queue_chain_complete": effective.get("queue_chain_complete") is True,
        "assigned_stage_complete": effective.get("assigned_stage_complete") is True,
        "queue_chain_requeue_required": (
            effective.get("queue_chain_requeue_required") is True
        ),
        "retry_at": str(effective.get("retry_at") or ""),
        "rejection_reasons": _reasons(effective.get("rejection_reasons") or ()),
        "bootstrap_status": str(bootstrap.get("status") or ""),
        "bootstrap_next_action": str(bootstrap.get("next_action") or ""),
        "bootstrap_dispatched_stages": _reasons(
            bootstrap.get("dispatched_stages") or ()
        ),
    }


def assurance_completion_request_from_runner(
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    """Return the verifier terminalization request from the bounded runner path."""

    if not isinstance(payload, Mapping):
        return {}
    nested = payload.get("runner_result")
    effective = dict(nested) if isinstance(nested, Mapping) else dict(payload)
    bootstrap = effective.get("bootstrap_result")
    bootstrap = dict(bootstrap) if isinstance(bootstrap, Mapping) else {}
    request = bootstrap.get("assurance_completion_request")
    return dict(request) if isinstance(request, Mapping) else {}


def _effect_fields(
    result: Mapping[str, Any], *, supplied: bool
) -> dict[str, bool]:
    source = result.get("structured_result")
    source = dict(source) if isinstance(source, Mapping) else dict(result)
    fields = (
        "no_shell_command_executed", "no_source_repo_mutation_performed",
        "no_holoindex_reindex_performed", "no_hermes_dispatch_performed",
        "no_worktree_operation_performed", "no_pr_created",
        "no_live_foundup_enqueue_performed", "no_pattern_memory_write_performed",
        "no_reward_settlement_performed",
    )
    return {
        field: source.get(field) is True if supplied else True
        for field in fields
    }


def _reasons(values: Sequence[Any]) -> list[str]:
    return list(
        dict.fromkeys(str(value) for value in values if str(value or "").strip())
    )


__all__ = [
    "DIRECT_ACCEPT",
    "DIRECT_REJECT",
    "DIRECT_REQUEUED",
    "append_signed_worker_result_history",
    "assurance_completion_request_from_runner",
    "build_signed_worker_task_result_receipt",
]
