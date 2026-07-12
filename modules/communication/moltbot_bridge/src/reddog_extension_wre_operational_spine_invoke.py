"""Extension-facing RedDog WRE operational-spine explicit invoke guard.

Slice: REDDOG_EXTENSION_TO_WRE_OPERATIONAL_SPINE_EXPLICIT_VALVE_INVOKE_PHASE1

This module is the narrow bridge between a RedDog operator-loop selection receipt
and the already-gated WRE worktree-create operational spine. It does not wire
`extension.js`, execute tasks, edit files, run tests, create PRs, push, merge,
enqueue OpenClaw, invoke Hermes, or settle rewards.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Mapping, MutableSet, Optional, Sequence, Union

from modules.communication.moltbot_bridge.src.reddog_operator_loop_wardrobe_selection import (
    AUTHORITY_SOVEREIGN_TOKEN_REQUIRED,
    EXECUTION_GOVERNED_CANDIDATE,
    WARDROBE_SOVEREIGN_EXECUTION,
    RedDogOperatorLoopWardrobeSelectionReceipt,
)
from modules.communication.moltbot_bridge.src.reddog_wre_execution_valve import (
    ExecutionValveEnvironment,
    INTAKE_FOUNDUP_JOB,
)
from modules.communication.moltbot_bridge.src.reddog_wre_operational_spine import (
    WORKTREE_SPINE_ACCEPT,
    RedDogWREOperationalSpineResult,
    run_reddog_wre_worktree_create_spine,
)

EXTENSION_WRE_OPERATIONAL_SPINE_INVOKE_ACCEPT = (
    "EXTENSION_WRE_OPERATIONAL_SPINE_INVOKE_ACCEPT"
)
EXTENSION_WRE_OPERATIONAL_SPINE_INVOKE_REJECT = (
    "EXTENSION_WRE_OPERATIONAL_SPINE_INVOKE_REJECT"
)


class ExtensionWREOperationalSpineInvokeReason:
    EXPLICIT_INVOKE_MISSING = "REJECT_EXPLICIT_WRE_OPERATIONAL_SPINE_INVOKE_MISSING"
    SELECTION_RECEIPT_MISSING = "REJECT_SELECTION_RECEIPT_MISSING"
    SELECTION_HAS_REJECTIONS = "REJECT_SELECTION_RECEIPT_HAS_REJECTIONS"
    SELECTION_NOT_SOVEREIGN = "REJECT_SELECTION_NOT_SOVEREIGN"
    SELECTION_PLANE_NOT_GOVERNED = "REJECT_SELECTION_PLANE_NOT_GOVERNED"
    SELECTION_AUTHORITY_BOUNDARY_INVALID = "REJECT_SELECTION_AUTHORITY_BOUNDARY_INVALID"
    SELECTION_ALREADY_EXECUTED = "REJECT_SELECTION_ALREADY_EXECUTED"
    WORKTREE_SPINE_REJECTED = "REJECT_WRE_OPERATIONAL_SPINE_REJECTED"


@dataclass(frozen=True)
class RedDogExtensionWREOperationalSpineInvokeResult:
    decision: str
    rejection_reasons: List[str] = field(default_factory=list)
    worktree_spine_result: Optional[RedDogWREOperationalSpineResult] = None
    explicit_wre_operational_spine_requested: bool = False
    no_task_execution_performed: bool = True
    no_file_edit_performed: bool = True
    no_pr_created: bool = True
    no_live_openclaw_enqueue: bool = True
    no_hermes_dispatch: bool = True
    merge_performed: bool = False
    main_checkout_untouched: bool = True
    no_reward_settlement_performed: bool = True

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        if self.worktree_spine_result is not None:
            payload["worktree_spine_result"] = self.worktree_spine_result.to_dict()
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


def _reject(
    reasons: Sequence[str],
    *,
    explicit_requested: bool,
    spine_result: Optional[RedDogWREOperationalSpineResult] = None,
) -> RedDogExtensionWREOperationalSpineInvokeResult:
    return RedDogExtensionWREOperationalSpineInvokeResult(
        decision=EXTENSION_WRE_OPERATIONAL_SPINE_INVOKE_REJECT,
        rejection_reasons=list(dict.fromkeys(reasons)),
        worktree_spine_result=spine_result,
        explicit_wre_operational_spine_requested=explicit_requested,
        no_task_execution_performed=True,
        no_file_edit_performed=True,
        no_pr_created=True,
        no_live_openclaw_enqueue=True,
        no_hermes_dispatch=True,
        merge_performed=False,
        main_checkout_untouched=True,
        no_reward_settlement_performed=True,
    )


def _validate_selection_receipt(selection_receipt: Mapping[str, Any]) -> List[str]:
    reasons: List[str] = []
    if not selection_receipt:
        return [ExtensionWREOperationalSpineInvokeReason.SELECTION_RECEIPT_MISSING]
    if selection_receipt.get("rejection_reasons"):
        reasons.append(ExtensionWREOperationalSpineInvokeReason.SELECTION_HAS_REJECTIONS)
    if selection_receipt.get("selected_wardrobe") != WARDROBE_SOVEREIGN_EXECUTION:
        reasons.append(ExtensionWREOperationalSpineInvokeReason.SELECTION_NOT_SOVEREIGN)
    if selection_receipt.get("execution_plane") != EXECUTION_GOVERNED_CANDIDATE:
        reasons.append(ExtensionWREOperationalSpineInvokeReason.SELECTION_PLANE_NOT_GOVERNED)
    if selection_receipt.get("authority_boundary") != AUTHORITY_SOVEREIGN_TOKEN_REQUIRED:
        reasons.append(
            ExtensionWREOperationalSpineInvokeReason.SELECTION_AUTHORITY_BOUNDARY_INVALID
        )
    if selection_receipt.get("no_execution_performed") is not True:
        reasons.append(ExtensionWREOperationalSpineInvokeReason.SELECTION_ALREADY_EXECUTED)
    if selection_receipt.get("no_enqueue_performed") is not True:
        reasons.append(ExtensionWREOperationalSpineInvokeReason.SELECTION_ALREADY_EXECUTED)
    return list(dict.fromkeys(reasons))


def invoke_reddog_extension_wre_operational_spine_explicit_valve(
    work_order: Mapping[str, Any],
    *,
    explicit_wre_operational_spine_requested: bool,
    selection_receipt: Union[RedDogOperatorLoopWardrobeSelectionReceipt, Mapping[str, Any], None],
    permission_snapshot: Optional[Mapping[str, Any]] = None,
    seen_nonces: Optional[MutableSet[str]] = None,
    receipt_store: Optional[Any] = None,
    valve_environment: Optional[ExecutionValveEnvironment | Mapping[str, Any]] = None,
    signature_verification_result: Optional[Mapping[str, Any]] = None,
    require_signed_authority: bool = True,
    runner: Optional[Any] = None,
    repo_root: Optional[Path] = None,
    now: Optional[datetime] = None,
    locks: Optional[MutableSet[str]] = None,
    intake_target: str = INTAKE_FOUNDUP_JOB,
    permission_ttl_seconds: int = 300,
    permission_expires_at: Optional[str] = None,
) -> RedDogExtensionWREOperationalSpineInvokeResult:
    """Invoke the WRE worktree-create spine only after explicit selection validation."""

    if explicit_wre_operational_spine_requested is not True:
        return _reject(
            [ExtensionWREOperationalSpineInvokeReason.EXPLICIT_INVOKE_MISSING],
            explicit_requested=False,
        )

    selection = _selection_mapping(selection_receipt)
    reasons = _validate_selection_receipt(selection)
    if reasons:
        return _reject(reasons, explicit_requested=True)

    spine_result = run_reddog_wre_worktree_create_spine(
        work_order,
        permission_snapshot=permission_snapshot,
        seen_nonces=seen_nonces,
        receipt_store=receipt_store,
        valve_environment=valve_environment,
        signature_verification_result=signature_verification_result,
        require_signed_authority=require_signed_authority,
        runner=runner,
        repo_root=repo_root,
        now=now,
        locks=locks,
        intake_target=intake_target,
        permission_ttl_seconds=permission_ttl_seconds,
        permission_expires_at=permission_expires_at,
    )
    if spine_result.decision != WORKTREE_SPINE_ACCEPT:
        reasons = [ExtensionWREOperationalSpineInvokeReason.WORKTREE_SPINE_REJECTED]
        reasons.extend(spine_result.rejection_reasons)
        return _reject(reasons, explicit_requested=True, spine_result=spine_result)

    return RedDogExtensionWREOperationalSpineInvokeResult(
        decision=EXTENSION_WRE_OPERATIONAL_SPINE_INVOKE_ACCEPT,
        rejection_reasons=[],
        worktree_spine_result=spine_result,
        explicit_wre_operational_spine_requested=True,
        no_task_execution_performed=True,
        no_file_edit_performed=True,
        no_pr_created=True,
        no_live_openclaw_enqueue=True,
        no_hermes_dispatch=True,
        merge_performed=False,
        main_checkout_untouched=True,
        no_reward_settlement_performed=True,
    )


__all__ = [
    "EXTENSION_WRE_OPERATIONAL_SPINE_INVOKE_ACCEPT",
    "EXTENSION_WRE_OPERATIONAL_SPINE_INVOKE_REJECT",
    "ExtensionWREOperationalSpineInvokeReason",
    "RedDogExtensionWREOperationalSpineInvokeResult",
    "invoke_reddog_extension_wre_operational_spine_explicit_valve",
]
