"""RedDog OpenClaw live enqueue implementation seam.

Slice: REDDOG_OPENCLAW_LIVE_ENQUEUE_IMPLEMENTATION_PHASE1

This module is the first live OpenClaw queue-write seam, but it is intentionally
small and valve-gated. It validates the #904 adapter dry-run output, #950 signed
authority gate, #951 signed receipt-chain status, and `VALVE_OPEN_LIVE_ENQUEUE`
before calling an injected writer. It does NOT execute Hermes/WRE work, create
worktrees, edit files, push, create PRs, merge, or settle rewards.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Mapping, Optional, Protocol, Sequence, Union

from modules.communication.moltbot_bridge.src.reddog_openclaw_adapter_dryrun import (
    ADAPTER_DRYRUN_ACCEPT,
    TARGET_AUTONOMOUS_TASK,
    TARGET_FOUNDUP_JOB,
    ProposedOpenClawIntakeRecord,
    RedDogOpenClawAdapterDryRunResult,
)
from modules.communication.moltbot_bridge.src.reddog_openclaw_work_order_policy_gate import (
    POLICY_ACCEPT,
    SIGNATURE_GATE_ACCEPTED,
)
from modules.communication.moltbot_bridge.src.reddog_signed_receipt_chain import (
    SIGNED_RECEIPT_CHAIN_ACCEPT,
    SignedReceiptChainVerificationResult,
)
from modules.communication.moltbot_bridge.src.reddog_wre_execution_valve import (
    VALVE_OPEN_LIVE_ENQUEUE,
    ExecutionValveDecision,
)

LIVE_ENQUEUE_ACCEPT = "LIVE_ENQUEUE_ACCEPT"
LIVE_ENQUEUE_REJECT = "LIVE_ENQUEUE_REJECT"


class LiveEnqueueReason:
    ADAPTER_NOT_ACCEPTED = "REJECT_ADAPTER_NOT_ACCEPTED"
    MISSING_PROPOSED_INTAKE = "REJECT_MISSING_PROPOSED_INTAKE"
    INTAKE_ALREADY_ENQUEUED = "REJECT_INTAKE_ALREADY_ENQUEUED"
    POLICY_NOT_ACCEPTED = "REJECT_POLICY_NOT_ACCEPTED"
    SIGNATURE_GATE_NOT_ACCEPTED = "REJECT_SIGNATURE_GATE_NOT_ACCEPTED"
    RECEIPT_CHAIN_NOT_ACCEPTED = "REJECT_SIGNED_RECEIPT_CHAIN_NOT_ACCEPTED"
    VALVE_NOT_OPEN = "REJECT_VALVE_NOT_OPEN_LIVE_ENQUEUE"
    TARGET_NOT_CANONICAL = "REJECT_TARGET_NOT_CANONICAL"
    IDEMPOTENCY_REPLAY = "REJECT_LIVE_ENQUEUE_REPLAY"
    WRITER_MISSING = "REJECT_LIVE_ENQUEUE_WRITER_MISSING"
    WRITER_REJECTED = "REJECT_LIVE_ENQUEUE_WRITER_REJECTED"


class LiveEnqueueWriter(Protocol):
    def enqueue_foundup_job(self, intake: Mapping[str, Any], receipt: Mapping[str, Any]) -> Mapping[str, Any]: ...

    def enqueue_autonomous_task(self, intake: Mapping[str, Any], receipt: Mapping[str, Any]) -> Mapping[str, Any]: ...


@dataclass
class RedDogOpenClawLiveEnqueueReceipt:
    live_enqueue_id: str
    work_order_id: str
    target_type: str
    proposed_intake_digest: str
    adapter_dryrun_receipt_digest: str
    policy_gate_receipt_digest: str
    signature_gate_digest: str
    signed_receipt_chain_terminal_hash: Optional[str]
    valve_decision_digest: str
    openclaw_queue_item_id: Optional[str]
    agentdb_task_id: Optional[str]
    live_enqueue_performed: bool
    no_execution_performed: bool
    no_reward_settlement_performed: bool
    created_at: str
    receipt_digest: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RedDogOpenClawLiveEnqueueResult:
    decision: str
    work_order_id: str
    target_type: str
    rejection_reasons: List[str] = field(default_factory=list)
    receipt: Optional[RedDogOpenClawLiveEnqueueReceipt] = None
    live_enqueue_performed: bool = False
    no_execution_performed: bool = True
    no_reward_settlement_performed: bool = True

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        if self.receipt is not None:
            payload["receipt"] = self.receipt.to_dict()
        return payload


def _utc_now(now: Optional[datetime] = None) -> datetime:
    value = now or datetime.now(timezone.utc)
    return value.astimezone(timezone.utc)


def _iso8601(dt: datetime) -> str:
    return dt.replace(microsecond=0).isoformat()


def _canonical_digest(payload: Mapping[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _mapping(value: Any) -> Mapping[str, Any]:
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if isinstance(value, Mapping):
        return value
    return {}


def _intake_mapping(adapter: Mapping[str, Any]) -> Mapping[str, Any]:
    intake = adapter.get("proposed_intake")
    if hasattr(intake, "to_dict"):
        return intake.to_dict()
    if isinstance(intake, Mapping):
        return intake
    return {}


def _adapter_receipt_mapping(adapter: Mapping[str, Any]) -> Mapping[str, Any]:
    receipt = adapter.get("adapter_receipt")
    if hasattr(receipt, "to_dict"):
        return receipt.to_dict()
    if isinstance(receipt, Mapping):
        return receipt
    return {}


def _live_enqueue_key(work_order_id: str, adapter_receipt_digest: str) -> str:
    return f"{work_order_id}:{adapter_receipt_digest}"


def _reject(work_order_id: str, target_type: str, reasons: Sequence[str]) -> RedDogOpenClawLiveEnqueueResult:
    return RedDogOpenClawLiveEnqueueResult(
        decision=LIVE_ENQUEUE_REJECT,
        work_order_id=work_order_id or "unknown",
        target_type=target_type or "",
        rejection_reasons=list(dict.fromkeys(reasons)),
        live_enqueue_performed=False,
        no_execution_performed=True,
        no_reward_settlement_performed=True,
    )


def _validate_inputs(
    adapter_result: Mapping[str, Any],
    policy_gate_receipt: Mapping[str, Any],
    signed_receipt_chain_result: Mapping[str, Any],
    valve_decision: Mapping[str, Any],
    intake: Mapping[str, Any],
) -> List[str]:
    reasons: List[str] = []
    if adapter_result.get("decision") != ADAPTER_DRYRUN_ACCEPT:
        reasons.append(LiveEnqueueReason.ADAPTER_NOT_ACCEPTED)
    if not intake:
        reasons.append(LiveEnqueueReason.MISSING_PROPOSED_INTAKE)
    else:
        if intake.get("no_enqueue_performed") is not True:
            reasons.append(LiveEnqueueReason.INTAKE_ALREADY_ENQUEUED)
        if intake.get("target_type") not in {TARGET_FOUNDUP_JOB, TARGET_AUTONOMOUS_TASK}:
            reasons.append(LiveEnqueueReason.TARGET_NOT_CANONICAL)
    if policy_gate_receipt.get("decision") != POLICY_ACCEPT:
        reasons.append(LiveEnqueueReason.POLICY_NOT_ACCEPTED)
    if policy_gate_receipt.get("signature_gate_status") != SIGNATURE_GATE_ACCEPTED:
        reasons.append(LiveEnqueueReason.SIGNATURE_GATE_NOT_ACCEPTED)
    if signed_receipt_chain_result.get("decision") != SIGNED_RECEIPT_CHAIN_ACCEPT:
        reasons.append(LiveEnqueueReason.RECEIPT_CHAIN_NOT_ACCEPTED)
    if signed_receipt_chain_result.get("accepted") is not True:
        reasons.append(LiveEnqueueReason.RECEIPT_CHAIN_NOT_ACCEPTED)
    if valve_decision.get("valve_state") != VALVE_OPEN_LIVE_ENQUEUE:
        reasons.append(LiveEnqueueReason.VALVE_NOT_OPEN)
    if valve_decision.get("no_execution_performed") is not True:
        reasons.append(LiveEnqueueReason.VALVE_NOT_OPEN)
    return list(dict.fromkeys(reasons))


def perform_reddog_openclaw_live_enqueue(
    adapter_result: Union[RedDogOpenClawAdapterDryRunResult, Mapping[str, Any]],
    policy_gate_receipt: Mapping[str, Any],
    signed_receipt_chain_result: Union[SignedReceiptChainVerificationResult, Mapping[str, Any]],
    valve_decision: Union[ExecutionValveDecision, Mapping[str, Any]],
    *,
    writer: Optional[LiveEnqueueWriter],
    seen_live_enqueue_keys: Optional[set] = None,
    now: Optional[datetime] = None,
) -> RedDogOpenClawLiveEnqueueResult:
    """Validate and enqueue a proposed OpenClaw intake item through an injected writer."""
    adapter = _mapping(adapter_result)
    policy = _mapping(policy_gate_receipt)
    chain = _mapping(signed_receipt_chain_result)
    valve = _mapping(valve_decision)
    intake = _intake_mapping(adapter)
    adapter_receipt = _adapter_receipt_mapping(adapter)

    work_order_id = str(adapter.get("work_order_id") or intake.get("work_order_id") or "unknown")
    target_type = str(intake.get("target_type") or adapter_receipt.get("target_type") or "")
    reasons = _validate_inputs(adapter, policy, chain, valve, intake)
    if writer is None:
        reasons.append(LiveEnqueueReason.WRITER_MISSING)

    adapter_digest = str(adapter_receipt.get("adapter_receipt_digest") or "")
    replay_key = _live_enqueue_key(work_order_id, adapter_digest)
    if seen_live_enqueue_keys is not None and replay_key in seen_live_enqueue_keys:
        reasons.append(LiveEnqueueReason.IDEMPOTENCY_REPLAY)

    deduped = list(dict.fromkeys(reasons))
    if deduped:
        return _reject(work_order_id, target_type, deduped)

    assert writer is not None
    checked_at = _iso8601(_utc_now(now))
    proposed_intake_digest = _canonical_digest(dict(intake))
    receipt_seed = {
        "work_order_id": work_order_id,
        "target_type": target_type,
        "proposed_intake_digest": proposed_intake_digest,
        "adapter_dryrun_receipt_digest": adapter_digest,
        "policy_gate_receipt_digest": str(policy.get("receipt_digest") or ""),
        "signature_gate_digest": str(policy.get("signature_gate_digest") or ""),
        "signed_receipt_chain_terminal_hash": chain.get("terminal_receipt_hash"),
        "valve_decision_digest": str(valve.get("decision_digest") or ""),
        "created_at": checked_at,
    }
    live_enqueue_id = "live-enqueue-" + _canonical_digest(receipt_seed)[:16]
    provisional_receipt = {
        **receipt_seed,
        "live_enqueue_id": live_enqueue_id,
        "live_enqueue_performed": False,
        "no_execution_performed": True,
        "no_reward_settlement_performed": True,
    }

    try:
        if target_type == TARGET_AUTONOMOUS_TASK:
            write_result = writer.enqueue_autonomous_task(dict(intake), provisional_receipt)
        else:
            write_result = writer.enqueue_foundup_job(dict(intake), provisional_receipt)
    except Exception:
        return _reject(work_order_id, target_type, [LiveEnqueueReason.WRITER_REJECTED])

    if not isinstance(write_result, Mapping) or write_result.get("ok") is not True:
        return _reject(work_order_id, target_type, [LiveEnqueueReason.WRITER_REJECTED])

    if seen_live_enqueue_keys is not None:
        seen_live_enqueue_keys.add(replay_key)

    receipt = RedDogOpenClawLiveEnqueueReceipt(
        live_enqueue_id=live_enqueue_id,
        work_order_id=work_order_id,
        target_type=target_type,
        proposed_intake_digest=proposed_intake_digest,
        adapter_dryrun_receipt_digest=adapter_digest,
        policy_gate_receipt_digest=str(policy.get("receipt_digest") or ""),
        signature_gate_digest=str(policy.get("signature_gate_digest") or ""),
        signed_receipt_chain_terminal_hash=(
            None if chain.get("terminal_receipt_hash") is None else str(chain.get("terminal_receipt_hash"))
        ),
        valve_decision_digest=str(valve.get("decision_digest") or ""),
        openclaw_queue_item_id=None if write_result.get("openclaw_queue_item_id") is None else str(write_result.get("openclaw_queue_item_id")),
        agentdb_task_id=None if write_result.get("agentdb_task_id") is None else str(write_result.get("agentdb_task_id")),
        live_enqueue_performed=True,
        no_execution_performed=True,
        no_reward_settlement_performed=True,
        created_at=checked_at,
    )
    receipt.receipt_digest = _canonical_digest({k: v for k, v in receipt.to_dict().items() if k != "receipt_digest"})

    return RedDogOpenClawLiveEnqueueResult(
        decision=LIVE_ENQUEUE_ACCEPT,
        work_order_id=work_order_id,
        target_type=target_type,
        rejection_reasons=[],
        receipt=receipt,
        live_enqueue_performed=True,
        no_execution_performed=True,
        no_reward_settlement_performed=True,
    )


__all__ = [
    "LIVE_ENQUEUE_ACCEPT",
    "LIVE_ENQUEUE_REJECT",
    "LiveEnqueueReason",
    "LiveEnqueueWriter",
    "RedDogOpenClawLiveEnqueueReceipt",
    "RedDogOpenClawLiveEnqueueResult",
    "perform_reddog_openclaw_live_enqueue",
]
