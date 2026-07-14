"""RedDog queue verified-authority to work-order invocation guard.

Slice: REDDOG_WRE_QUEUE_VERIFIED_AUTHORITY_WORK_ORDER_INVOCATION_PHASE1

This module bridges an accepted queue-authority verification result into the
existing governed work-order dry-run invocation path. It binds the verified
authority payload to the exact work order before calling the existing policy
gate with signed-authority required.

It does not issue signatures, spawn workers, create worktrees, run shell
commands, enqueue OpenClaw, dispatch Hermes, mutate repository files, publish
PRs, settle rewards, or re-index HoloIndex.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Mapping, MutableSet, Optional, Sequence

from modules.communication.moltbot_bridge.src.reddog_work_order_receipt import (
    RedDogWorkOrderReceiptStore,
)
from modules.communication.moltbot_bridge.src.reddog_work_order_runtime_invocation import (
    INVOCATION_REJECT,
    WorkOrderDryRunInvocationResult,
    invoke_reddog_work_order_dryrun,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_authority_runtime_invoke import (
    QUEUE_AUTHORITY_RUNTIME_INVOKE_ACCEPT,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_authority_verification_invoke import (
    QUEUE_AUTHORITY_VERIFICATION_INVOKE_ACCEPT,
)


AUTHORITY_ISSUED_STATUS = "AUTHORITY_ISSUED"

QUEUE_VERIFIED_AUTHORITY_WORK_ORDER_INVOKE_ACCEPT = (
    "QUEUE_VERIFIED_AUTHORITY_WORK_ORDER_INVOKE_ACCEPT"
)
QUEUE_VERIFIED_AUTHORITY_WORK_ORDER_INVOKE_REJECT = (
    "QUEUE_VERIFIED_AUTHORITY_WORK_ORDER_INVOKE_REJECT"
)


class QueueVerifiedAuthorityWorkOrderInvokeReason:
    EXPLICIT_INVOKE_MISSING = "REJECT_EXPLICIT_QUEUE_WORK_ORDER_INVOCATION_MISSING"
    AUTHORITY_VERIFICATION_NOT_ACCEPTED = "REJECT_QUEUE_AUTHORITY_VERIFICATION_NOT_ACCEPTED"
    AUTHORITY_RUNTIME_NOT_ACCEPTED = "REJECT_QUEUE_AUTHORITY_RUNTIME_NOT_ACCEPTED"
    AUTHORITY_PAYLOAD_MISSING = "REJECT_QUEUE_AUTHORITY_PAYLOAD_MISSING"
    AUTHORITY_WORK_ORDER_BINDING_MISMATCH = "REJECT_AUTHORITY_WORK_ORDER_BINDING_MISMATCH"
    WORK_ORDER_INVOCATION_REJECTED = "REJECT_WORK_ORDER_INVOCATION_REJECTED"


@dataclass(frozen=True)
class QueueVerifiedAuthorityWorkOrderInvokeResult:
    decision: str
    rejection_reasons: List[str] = field(default_factory=list)
    invocation_result: Optional[WorkOrderDryRunInvocationResult] = None
    explicit_queue_work_order_invocation_requested: bool = False
    no_signing_performed: bool = True
    no_authority_issued: bool = True
    no_worker_spawn_performed: bool = True
    no_worktree_created: bool = True
    no_shell_command_executed: bool = True
    no_openclaw_enqueue_performed: bool = True
    no_hermes_dispatch_performed: bool = True
    no_repo_mutation_performed: bool = True
    no_holoindex_reindex_performed: bool = True
    no_pr_created: bool = True
    no_reward_settlement_performed: bool = True

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["invocation_result"] = (
            self.invocation_result.to_dict() if self.invocation_result else None
        )
        return payload


def _mapping(value: Any) -> Mapping[str, Any]:
    if hasattr(value, "to_dict"):
        candidate = value.to_dict()
        return candidate if isinstance(candidate, Mapping) else {}
    if isinstance(value, Mapping):
        return value
    return {}


def _string_list(value: Any) -> List[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return []
    return [str(item) for item in value]


def _repo_permission_snapshot_digest(work_order: Mapping[str, Any]) -> str:
    snapshot = _mapping(work_order.get("repo_permission_snapshot"))
    return str(snapshot.get("digest") or "")


def _extract_verification_payload(
    queue_authority_verification_result: Mapping[str, Any],
) -> Mapping[str, Any]:
    if queue_authority_verification_result.get("decision") != QUEUE_AUTHORITY_VERIFICATION_INVOKE_ACCEPT:
        return {}
    verification = _mapping(queue_authority_verification_result.get("verification_result"))
    if verification.get("accepted") is not True:
        return {}
    return verification


def _extract_work_authority(queue_authority_runtime_result: Mapping[str, Any]) -> Mapping[str, Any]:
    authority = _mapping(queue_authority_runtime_result.get("authority_result"))
    receipt = _mapping(authority.get("receipt"))
    if (
        queue_authority_runtime_result.get("decision") != QUEUE_AUTHORITY_RUNTIME_INVOKE_ACCEPT
        or authority.get("accepted") is not True
        or receipt.get("status") != AUTHORITY_ISSUED_STATUS
    ):
        return {}
    return _mapping(authority.get("work_authority"))


def _authority_work_order_binding_reasons(
    *,
    work_order: Mapping[str, Any],
    work_authority: Mapping[str, Any],
) -> List[str]:
    reasons: List[str] = []
    checks = (
        ("work_order_id", work_authority.get("work_order_id"), work_order.get("work_order_id")),
        ("repo_full_name", work_authority.get("repo_full_name"), work_order.get("repo_full_name")),
        (
            "requested_operation",
            work_authority.get("requested_operation"),
            work_order.get("requested_operation"),
        ),
        (
            "permission_snapshot_digest",
            work_authority.get("permission_snapshot_digest"),
            _repo_permission_snapshot_digest(work_order),
        ),
    )
    for name, authority_value, order_value in checks:
        if str(authority_value) != str(order_value):
            reasons.append(f"{QueueVerifiedAuthorityWorkOrderInvokeReason.AUTHORITY_WORK_ORDER_BINDING_MISMATCH}:{name}")

    if sorted(_string_list(work_authority.get("allowed_paths"))) != sorted(
        _string_list(work_order.get("allowed_paths"))
    ):
        reasons.append(
            f"{QueueVerifiedAuthorityWorkOrderInvokeReason.AUTHORITY_WORK_ORDER_BINDING_MISMATCH}:allowed_paths"
        )
    if sorted(_string_list(work_authority.get("denied_paths"))) != sorted(
        _string_list(work_order.get("denied_paths"))
    ):
        reasons.append(
            f"{QueueVerifiedAuthorityWorkOrderInvokeReason.AUTHORITY_WORK_ORDER_BINDING_MISMATCH}:denied_paths"
        )
    return reasons


def _reject(
    reasons: Sequence[str],
    *,
    explicit_requested: bool,
    invocation_result: Optional[WorkOrderDryRunInvocationResult] = None,
) -> QueueVerifiedAuthorityWorkOrderInvokeResult:
    return QueueVerifiedAuthorityWorkOrderInvokeResult(
        decision=QUEUE_VERIFIED_AUTHORITY_WORK_ORDER_INVOKE_REJECT,
        rejection_reasons=list(dict.fromkeys(reasons)),
        invocation_result=invocation_result,
        explicit_queue_work_order_invocation_requested=explicit_requested,
    )


def invoke_reddog_wre_queue_verified_authority_work_order(
    *,
    explicit_queue_work_order_invocation_requested: bool,
    queue_authority_verification_result: Mapping[str, Any],
    queue_authority_runtime_result: Mapping[str, Any],
    work_order: Mapping[str, Any],
    permission_snapshot: Optional[Mapping[str, Any]] = None,
    now: Optional[datetime] = None,
    seen_nonces: Optional[MutableSet[str]] = None,
    receipt_store: Optional[RedDogWorkOrderReceiptStore] = None,
    permission_ttl_seconds: int = 300,
    permission_expires_at: Optional[str] = None,
) -> QueueVerifiedAuthorityWorkOrderInvokeResult:
    """Invoke existing work-order dry-run only from verified queue authority."""

    if explicit_queue_work_order_invocation_requested is not True:
        return _reject(
            [QueueVerifiedAuthorityWorkOrderInvokeReason.EXPLICIT_INVOKE_MISSING],
            explicit_requested=False,
        )

    verification = _extract_verification_payload(_mapping(queue_authority_verification_result))
    if not verification:
        reasons = [QueueVerifiedAuthorityWorkOrderInvokeReason.AUTHORITY_VERIFICATION_NOT_ACCEPTED]
        raw_verification = _mapping(queue_authority_verification_result).get("verification_result")
        raw_reasons = _mapping(raw_verification).get("reason_codes")
        reasons.extend(str(reason) for reason in _string_list(raw_reasons))
        return _reject(reasons, explicit_requested=True)

    work_authority = _extract_work_authority(_mapping(queue_authority_runtime_result))
    if not work_authority:
        return _reject(
            [QueueVerifiedAuthorityWorkOrderInvokeReason.AUTHORITY_RUNTIME_NOT_ACCEPTED],
            explicit_requested=True,
        )

    binding_reasons = _authority_work_order_binding_reasons(
        work_order=_mapping(work_order),
        work_authority=work_authority,
    )
    if binding_reasons:
        return _reject(binding_reasons, explicit_requested=True)

    invocation = invoke_reddog_work_order_dryrun(
        work_order,
        permission_snapshot=permission_snapshot,
        now=now,
        seen_nonces=seen_nonces,
        receipt_store=receipt_store,
        permission_ttl_seconds=permission_ttl_seconds,
        permission_expires_at=permission_expires_at,
        require_signed_authority=True,
        signature_verification_result=verification,
    )
    if invocation.decision == INVOCATION_REJECT:
        return _reject(
            [
                QueueVerifiedAuthorityWorkOrderInvokeReason.WORK_ORDER_INVOCATION_REJECTED,
                *invocation.rejection_reasons,
            ],
            explicit_requested=True,
            invocation_result=invocation,
        )

    return QueueVerifiedAuthorityWorkOrderInvokeResult(
        decision=QUEUE_VERIFIED_AUTHORITY_WORK_ORDER_INVOKE_ACCEPT,
        rejection_reasons=[],
        invocation_result=invocation,
        explicit_queue_work_order_invocation_requested=True,
    )


__all__ = [
    "QUEUE_VERIFIED_AUTHORITY_WORK_ORDER_INVOKE_ACCEPT",
    "QUEUE_VERIFIED_AUTHORITY_WORK_ORDER_INVOKE_REJECT",
    "QueueVerifiedAuthorityWorkOrderInvokeReason",
    "QueueVerifiedAuthorityWorkOrderInvokeResult",
    "invoke_reddog_wre_queue_verified_authority_work_order",
]
