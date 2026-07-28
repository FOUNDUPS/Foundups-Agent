"""Exact-state execution admission for the OpenClaw signed-worker route."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from modules.communication.moltbot_bridge.src.reddog_openclaw_hermes_0102_worker_dispatch_runtime import (
    SIGNED_WORKER_DISPATCH_TASK_SKILL,
    SIGNED_WORKER_DISPATCH_TASK_SOURCE,
)
from modules.communication.moltbot_bridge.src.reddog_signed_worker_claim_admission import (
    try_rehydrate_signed_worker_agentdb_context,
)
from modules.communication.moltbot_bridge.src.reddog_signed_worker_execution_claim import (
    admit_signed_worker_execution_once,
    bind_execution_admission,
)


@dataclass(frozen=True)
class SignedWorkerSupervisorAdmission:
    """Result of claiming and verifying one exact AgentDB task state."""

    status: str
    context: Mapping[str, Any]
    error: str = ""


def admit_signed_worker_for_supervisor(
    *,
    repo_root: Path,
    db: Any,
    task_id: str,
    env: Mapping[str, str],
    authority_verification_context: Any | None,
) -> SignedWorkerSupervisorAdmission:
    """CAS-admit first, then verify only the state won by that CAS."""

    admission = admit_signed_worker_execution_once(db=db, task_id=task_id)
    if admission is None:
        return SignedWorkerSupervisorAdmission("ALREADY_CLAIMED", {})
    claimed = admission.claimed_context
    admitted = bind_execution_admission(claimed, admission)
    if (
        admission.discovered_by != SIGNED_WORKER_DISPATCH_TASK_SOURCE
        or SIGNED_WORKER_DISPATCH_TASK_SKILL not in admission.required_skills
        or str(claimed.get("source") or "") != SIGNED_WORKER_DISPATCH_TASK_SOURCE
    ):
        return SignedWorkerSupervisorAdmission(
            "REJECTED", admitted, "signed_worker_task_routing_binding_mismatch"
        )
    verified, error = try_rehydrate_signed_worker_agentdb_context(
        repo_root=repo_root,
        task_id=task_id,
        context=claimed,
        env=env,
        authority_verification_context=authority_verification_context,
    )
    if verified is None:
        return SignedWorkerSupervisorAdmission("REJECTED", admitted, error)
    try:
        verified = {
            **dict(verified),
            **_validated_result_history(claimed),
        }
    except ValueError as exc:
        return SignedWorkerSupervisorAdmission("REJECTED", admitted, str(exc))
    return SignedWorkerSupervisorAdmission(
        "ADMITTED", bind_execution_admission(verified, admission)
    )


def _validated_result_history(
    context: Mapping[str, Any],
) -> Mapping[str, Any]:
    last = context.get("signed_worker_task_last_result")
    history = context.get("signed_worker_task_result_receipts")
    if last is None and history is None:
        return {}
    if not isinstance(last, Mapping) or not isinstance(history, list):
        raise ValueError("signed_worker_result_history_malformed")
    last_body = dict(last)
    supplied_digest = str(last_body.pop("receipt_digest", "") or "")
    if supplied_digest != _digest(last_body):
        raise ValueError("signed_worker_last_result_digest_mismatch")
    if not 1 <= len(history) <= 10:
        raise ValueError("signed_worker_result_history_count_invalid")
    normalized = []
    for item in history:
        if not isinstance(item, Mapping) or set(item) != {
            "claim_status", "receipt_id", "receipt_digest"
        }:
            raise ValueError("signed_worker_result_history_item_invalid")
        entry = {key: str(item.get(key) or "") for key in item}
        if not entry["claim_status"] or not entry["receipt_digest"].startswith("sha256:"):
            raise ValueError("signed_worker_result_history_item_invalid")
        normalized.append(entry)
    if any(normalized[-1][key] != str(last.get(key) or "") for key in normalized[-1]):
        raise ValueError("signed_worker_result_history_tail_mismatch")
    return {
        "signed_worker_task_last_result": dict(last),
        "signed_worker_task_result_receipts": normalized,
    }


def _digest(payload: Mapping[str, Any]) -> str:
    raw = json.dumps(
        dict(payload), sort_keys=True, separators=(",", ":"),
        ensure_ascii=True, default=str,
    )
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


__all__ = [
    "SignedWorkerSupervisorAdmission",
    "admit_signed_worker_for_supervisor",
]
