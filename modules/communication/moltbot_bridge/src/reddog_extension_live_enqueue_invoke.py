"""Extension-facing RedDog live-enqueue explicit invoke guard.

Slice: REDDOG_EXTENSION_TO_LIVE_ENQUEUE_EXPLICIT_VALVE_INVOKE_PHASE1

This module is the narrow bridge between a RedDog operator-loop selection receipt and the
already-gated OpenClaw live enqueue seam. It does not wire `extension.js`, construct the
concrete writer, execute queued tasks, run shell commands, create worktrees, push, merge,
or settle rewards.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Union

from modules.communication.moltbot_bridge.src.reddog_openclaw_live_enqueue import (
    LIVE_ENQUEUE_ACCEPT,
    LIVE_ENQUEUE_REJECT,
    LiveEnqueueWriter,
    RedDogOpenClawLiveEnqueueResult,
    perform_reddog_openclaw_live_enqueue,
)
from modules.communication.moltbot_bridge.src.reddog_live_enqueue_admission_capability import (
    InMemoryLiveEnqueueAdmissionRegistry,
)
from modules.communication.moltbot_bridge.src.reddog_operator_loop_wardrobe_selection import (
    AUTHORITY_SIGNED_VALVE_REQUIRED,
    AUTHORITY_SOVEREIGN_TOKEN_REQUIRED,
    EXECUTION_GOVERNED_CANDIDATE,
    WARDROBE_SOVEREIGN_EXECUTION,
    RedDogOperatorLoopWardrobeSelectionReceipt,
)
from modules.communication.moltbot_bridge.src.reddog_wre_execution_valve import (
    VALVE_OPEN_LIVE_ENQUEUE,
)
from modules.communication.moltbot_bridge.src.reddog_registered_foundup_target_verifier import (
    verify_registered_foundup_target,
)

EXTENSION_LIVE_ENQUEUE_INVOKE_ACCEPT = "EXTENSION_LIVE_ENQUEUE_INVOKE_ACCEPT"
EXTENSION_LIVE_ENQUEUE_INVOKE_REJECT = "EXTENSION_LIVE_ENQUEUE_INVOKE_REJECT"


class ExtensionLiveEnqueueInvokeReason:
    EXPLICIT_INVOKE_MISSING = "REJECT_EXPLICIT_LIVE_ENQUEUE_INVOKE_MISSING"
    SELECTION_RECEIPT_MISSING = "REJECT_SELECTION_RECEIPT_MISSING"
    SELECTION_HAS_REJECTIONS = "REJECT_SELECTION_RECEIPT_HAS_REJECTIONS"
    SELECTION_NOT_SOVEREIGN = "REJECT_SELECTION_NOT_SOVEREIGN"
    SELECTION_PLANE_NOT_GOVERNED = "REJECT_SELECTION_PLANE_NOT_GOVERNED"
    SELECTION_AUTHORITY_BOUNDARY_INVALID = "REJECT_SELECTION_AUTHORITY_BOUNDARY_INVALID"
    SELECTION_ALREADY_EXECUTED = "REJECT_SELECTION_ALREADY_EXECUTED"
    VALVE_NOT_LIVE_ENQUEUE = "REJECT_VALVE_NOT_OPEN_LIVE_ENQUEUE"
    LIVE_ENQUEUE_REJECTED = "REJECT_LIVE_ENQUEUE_SEAM_REJECTED"
    AUTHORITATIVE_ADMISSION_MISSING = "REJECT_AUTHORITATIVE_LIVE_ENQUEUE_ADMISSION_MISSING"
    FOUNDUP_TARGET_INVALID = "REJECT_REGISTERED_FOUNDUP_TARGET_INVALID"


@dataclass(frozen=True)
class RedDogExtensionLiveEnqueueInvokeResult:
    decision: str
    rejection_reasons: List[str] = field(default_factory=list)
    live_enqueue_result: Optional[RedDogOpenClawLiveEnqueueResult] = None
    explicit_live_enqueue_requested: bool = False
    no_execution_performed: bool = True
    no_reward_settlement_performed: bool = True

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        if self.live_enqueue_result is not None:
            payload["live_enqueue_result"] = self.live_enqueue_result.to_dict()
        return payload


def _mapping(value: Any) -> Mapping[str, Any]:
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if isinstance(value, Mapping):
        return value
    return {}


def _selection_mapping(
    value: Union[RedDogOperatorLoopWardrobeSelectionReceipt, Mapping[str, Any], None],
) -> Mapping[str, Any]:
    if value is None:
        return {}
    return _mapping(value)


def _adapter_work_order_id(adapter_result: Mapping[str, Any]) -> str:
    adapter = _mapping(adapter_result)
    intake = _mapping(adapter.get("proposed_intake"))
    return str(adapter.get("work_order_id") or intake.get("work_order_id") or "")


def _reject(reasons: Sequence[str], explicit_requested: bool) -> RedDogExtensionLiveEnqueueInvokeResult:
    return RedDogExtensionLiveEnqueueInvokeResult(
        decision=EXTENSION_LIVE_ENQUEUE_INVOKE_REJECT,
        rejection_reasons=list(dict.fromkeys(reasons)),
        live_enqueue_result=None,
        explicit_live_enqueue_requested=explicit_requested,
        no_execution_performed=True,
        no_reward_settlement_performed=True,
    )


def _validate_selection_receipt(
    selection_receipt: Mapping[str, Any],
    valve_decision: Mapping[str, Any],
) -> List[str]:
    reasons: List[str] = []
    if not selection_receipt:
        return [ExtensionLiveEnqueueInvokeReason.SELECTION_RECEIPT_MISSING]
    if selection_receipt.get("rejection_reasons"):
        reasons.append(ExtensionLiveEnqueueInvokeReason.SELECTION_HAS_REJECTIONS)
    if selection_receipt.get("selected_wardrobe") != WARDROBE_SOVEREIGN_EXECUTION:
        reasons.append(ExtensionLiveEnqueueInvokeReason.SELECTION_NOT_SOVEREIGN)
    if selection_receipt.get("execution_plane") != EXECUTION_GOVERNED_CANDIDATE:
        reasons.append(ExtensionLiveEnqueueInvokeReason.SELECTION_PLANE_NOT_GOVERNED)
    if selection_receipt.get("authority_boundary") not in {
        AUTHORITY_SIGNED_VALVE_REQUIRED,
        AUTHORITY_SOVEREIGN_TOKEN_REQUIRED,
    }:
        reasons.append(ExtensionLiveEnqueueInvokeReason.SELECTION_AUTHORITY_BOUNDARY_INVALID)
    if selection_receipt.get("no_execution_performed") is not True:
        reasons.append(ExtensionLiveEnqueueInvokeReason.SELECTION_ALREADY_EXECUTED)
    if selection_receipt.get("no_enqueue_performed") is not True:
        reasons.append(ExtensionLiveEnqueueInvokeReason.SELECTION_ALREADY_EXECUTED)
    if valve_decision.get("valve_state") != VALVE_OPEN_LIVE_ENQUEUE:
        reasons.append(ExtensionLiveEnqueueInvokeReason.VALVE_NOT_LIVE_ENQUEUE)
    return list(dict.fromkeys(reasons))


def invoke_reddog_extension_live_enqueue_explicit_valve(
    *,
    explicit_live_enqueue_requested: bool,
    selection_receipt: Union[RedDogOperatorLoopWardrobeSelectionReceipt, Mapping[str, Any], None],
    adapter_result: Mapping[str, Any],
    policy_gate_receipt: Mapping[str, Any],
    signed_receipt_chain_result: Mapping[str, Any],
    valve_decision: Mapping[str, Any],
    registered_foundup_target_receipt: Optional[Mapping[str, Any]] = None,
    repo_root: Optional[Path] = None,
    writer: Optional[LiveEnqueueWriter],
    seen_live_enqueue_keys: Optional[set] = None,
    admission_registry: Optional[InMemoryLiveEnqueueAdmissionRegistry] = None,
) -> RedDogExtensionLiveEnqueueInvokeResult:
    """Invoke live enqueue only after explicit request and selection-receipt validation."""

    if explicit_live_enqueue_requested is not True:
        return _reject(
            [ExtensionLiveEnqueueInvokeReason.EXPLICIT_INVOKE_MISSING],
            explicit_requested=False,
        )
    selection = _selection_mapping(selection_receipt)
    valve = _mapping(valve_decision)
    reasons = _validate_selection_receipt(selection, valve)
    target_reasons = verify_registered_foundup_target(
        repo_root or Path.cwd(),
        registered_foundup_target_receipt,
        selection_receipt=selection,
    )
    if target_reasons:
        reasons.extend([ExtensionLiveEnqueueInvokeReason.FOUNDUP_TARGET_INVALID, *target_reasons])
    if reasons:
        return _reject(reasons, explicit_requested=True)
    if admission_registry is None:
        return _reject(
            [ExtensionLiveEnqueueInvokeReason.AUTHORITATIVE_ADMISSION_MISSING],
            explicit_requested=True,
        )

    evidence = {
        "selection_receipt": selection,
        "adapter_result": _mapping(adapter_result),
        "policy_gate_receipt": _mapping(policy_gate_receipt),
        "signed_receipt_chain_result": _mapping(signed_receipt_chain_result),
        "valve_decision": valve,
    }
    work_order_id = _adapter_work_order_id(adapter_result)
    live_result = perform_reddog_openclaw_live_enqueue(
        adapter_result,
        policy_gate_receipt,
        signed_receipt_chain_result,
        valve,
        writer=writer,
        seen_live_enqueue_keys=seen_live_enqueue_keys,
        admission_consumer=lambda: admission_registry.consume(
            work_order_id=work_order_id,
            evidence=evidence,
        )
        is not None,
    )
    if live_result.decision != LIVE_ENQUEUE_ACCEPT:
        reasons = [ExtensionLiveEnqueueInvokeReason.LIVE_ENQUEUE_REJECTED]
        reasons.extend(live_result.rejection_reasons)
        return RedDogExtensionLiveEnqueueInvokeResult(
            decision=EXTENSION_LIVE_ENQUEUE_INVOKE_REJECT,
            rejection_reasons=list(dict.fromkeys(reasons)),
            live_enqueue_result=live_result,
            explicit_live_enqueue_requested=True,
            no_execution_performed=True,
            no_reward_settlement_performed=True,
        )

    return RedDogExtensionLiveEnqueueInvokeResult(
        decision=EXTENSION_LIVE_ENQUEUE_INVOKE_ACCEPT,
        rejection_reasons=[],
        live_enqueue_result=live_result,
        explicit_live_enqueue_requested=True,
        no_execution_performed=True,
        no_reward_settlement_performed=True,
    )


__all__ = [
    "EXTENSION_LIVE_ENQUEUE_INVOKE_ACCEPT",
    "EXTENSION_LIVE_ENQUEUE_INVOKE_REJECT",
    "ExtensionLiveEnqueueInvokeReason",
    "RedDogExtensionLiveEnqueueInvokeResult",
    "invoke_reddog_extension_live_enqueue_explicit_valve",
]
