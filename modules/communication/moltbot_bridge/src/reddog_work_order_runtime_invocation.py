"""RedDog governed work-order runtime invocation dry-run (no execution).

Slice: REDDOG_WORK_ORDER_RUNTIME_INVOCATION_DRYRUN_PHASE1
Contract: docs/audits/architecture/REDDOG_GOVERNED_REPO_WORK_ORDER_CONTRACT_PHASE1.md

Orchestrates the pre-execution governance spine:
  work order -> #893 policy gate -> #894 Hermes-compatible receipt -> caller result

WSP 97 TRUTH BOUNDARIES:
  ✓ DOES:
    - Evaluate OpenClaw policy gate on a RedDogGovernedWorkOrder
    - Emit/persist audit receipt via #894 receipt layer
    - Return dry-run invocation result to caller (digests/refs only)

  ✗ DOES NOT:
    - Create branches, PRs, commits, merges, or mutate repository content
    - Invoke WRE executor, shell, git, live GitHub probe, Skillz execution, or Hermes queue
    - Make external API calls
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Mapping, MutableSet, Optional, Union

from modules.communication.moltbot_bridge.src.reddog_openclaw_work_order_policy_gate import (
    POLICY_ACCEPT,
    POLICY_ACCEPT_WITH_RETRIEVAL_GAP,
    POLICY_REJECT,
    PolicyGateReceipt,
    evaluate_work_order_policy_gate,
)
from modules.communication.moltbot_bridge.src.reddog_work_order_receipt import (
    RedDogWorkOrderReceiptStore,
    emit_work_order_receipt,
)

INVOCATION_ACCEPT = "INVOCATION_ACCEPT"
INVOCATION_REJECT = "INVOCATION_REJECT"
INVOCATION_ACCEPT_WITH_RETRIEVAL_GAP = "INVOCATION_ACCEPT_WITH_RETRIEVAL_GAP"

_POLICY_TO_INVOCATION = {
    POLICY_ACCEPT: INVOCATION_ACCEPT,
    POLICY_REJECT: INVOCATION_REJECT,
    POLICY_ACCEPT_WITH_RETRIEVAL_GAP: INVOCATION_ACCEPT_WITH_RETRIEVAL_GAP,
}


@dataclass
class WorkOrderDryRunInvocationResult:
    decision: str
    work_order_id: str
    policy_gate_decision: str
    receipt_id: str
    receipt_digest: str
    no_execution_performed: bool
    rejection_reasons: List[str]
    gates_checked: List[str]
    idempotent_replay: bool = False
    policy_gate_receipt_digest: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _canonical_digest(payload: Mapping[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _merge_permission_snapshot(
    work_order: Mapping[str, Any],
    permission_snapshot: Optional[Mapping[str, Any]],
) -> Dict[str, Any]:
    merged = dict(work_order)
    if permission_snapshot is None:
        return merged
    base = dict(merged.get("repo_permission_snapshot") or {})
    base.update(dict(permission_snapshot))
    merged["repo_permission_snapshot"] = base
    return merged


def _invocation_decision(policy_decision: str) -> str:
    return _POLICY_TO_INVOCATION.get(policy_decision, INVOCATION_REJECT)


def invoke_reddog_work_order_dryrun(
    work_order: Mapping[str, Any],
    permission_snapshot: Optional[Mapping[str, Any]] = None,
    *,
    now: Optional[datetime] = None,
    seen_nonces: Optional[MutableSet[str]] = None,
    receipt_store: Optional[RedDogWorkOrderReceiptStore] = None,
    permission_ttl_seconds: int = 300,
    permission_expires_at: Optional[str] = None,
) -> WorkOrderDryRunInvocationResult:
    """Run governed work-order dry-run invocation: policy gate + receipt, no execution."""
    order = _merge_permission_snapshot(work_order, permission_snapshot)
    checked = now or datetime.now(timezone.utc)

    policy_receipt: PolicyGateReceipt = evaluate_work_order_policy_gate(
        order,
        now=checked,
        seen_nonces=seen_nonces,
        permission_ttl_seconds=permission_ttl_seconds,
        permission_expires_at=permission_expires_at,
    )

    emission = emit_work_order_receipt(policy_receipt, store=receipt_store, now=checked)
    if not emission.success or emission.receipt is None:
        return WorkOrderDryRunInvocationResult(
            decision=INVOCATION_REJECT,
            work_order_id=str(order.get("work_order_id") or "unknown"),
            policy_gate_decision=policy_receipt.decision,
            receipt_id="",
            receipt_digest="",
            no_execution_performed=True,
            rejection_reasons=list(policy_receipt.rejection_reasons) + (
                [emission.error] if emission.error else ["receipt_emission_failed"]
            ),
            gates_checked=list(policy_receipt.gates_checked),
            policy_gate_receipt_digest=policy_receipt.receipt_digest,
        )

    receipt = emission.receipt
    invocation_decision = _invocation_decision(policy_receipt.decision)

    return WorkOrderDryRunInvocationResult(
        decision=invocation_decision,
        work_order_id=receipt.work_order_id,
        policy_gate_decision=policy_receipt.decision,
        receipt_id=receipt.receipt_id,
        receipt_digest=receipt.receipt_digest,
        no_execution_performed=True,
        rejection_reasons=list(policy_receipt.rejection_reasons),
        gates_checked=list(policy_receipt.gates_checked),
        idempotent_replay=emission.idempotent_replay,
        policy_gate_receipt_digest=policy_receipt.receipt_digest,
    )


__all__ = [
    "INVOCATION_ACCEPT",
    "INVOCATION_ACCEPT_WITH_RETRIEVAL_GAP",
    "INVOCATION_REJECT",
    "WorkOrderDryRunInvocationResult",
    "invoke_reddog_work_order_dryrun",
]
