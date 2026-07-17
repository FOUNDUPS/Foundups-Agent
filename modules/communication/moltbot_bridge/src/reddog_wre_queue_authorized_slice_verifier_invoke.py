"""RedDog queue-authorized autonomous slice verifier explicit invoke guard.

Slice: REDDOG_WRE_QUEUE_AUTHORIZED_SLICE_VERIFIER_INVOKE_PHASE1

This module consumes an accepted queue-authorized bounded worker pilot result
and machine-derived verifier evidence, then invokes the existing WRE autonomous
slice verifier runtime. It performs no command execution, no GitHub call, no
draft PR publishing, no merge, no PatternMemory write, no reward settlement,
and no HoloIndex re-index.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Sequence

from modules.communication.moltbot_bridge.src.reddog_bounded_worktree_worker_execution_pilot import (
    BOUNDED_WORKTREE_PILOT_ACCEPT,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_authorized_bounded_worker_pilot_invoke import (
    QUEUE_AUTHORIZED_BOUNDED_WORKER_PILOT_INVOKE_ACCEPT,
)
from modules.infrastructure.wre_core.src.wre_autonomous_slice_verifier_runtime import (
    AUTONOMOUS_SLICE_VERIFIER_ACCEPT,
    AutonomousSliceVerifierResult,
    verify_autonomous_slice_runtime,
)


QUEUE_AUTHORIZED_SLICE_VERIFIER_INVOKE_ACCEPT = "QUEUE_AUTHORIZED_SLICE_VERIFIER_INVOKE_ACCEPT"
QUEUE_AUTHORIZED_SLICE_VERIFIER_INVOKE_REJECT = "QUEUE_AUTHORIZED_SLICE_VERIFIER_INVOKE_REJECT"


class QueueAuthorizedSliceVerifierInvokeReason:
    EXPLICIT_INVOKE_MISSING = "REJECT_EXPLICIT_QUEUE_AUTHORIZED_SLICE_VERIFIER_INVOKE_MISSING"
    BOUNDED_PILOT_NOT_ACCEPTED = "REJECT_QUEUE_BOUNDED_PILOT_NOT_ACCEPTED"
    PILOT_PAYLOAD_MISSING = "REJECT_BOUNDED_PILOT_PAYLOAD_MISSING"
    PILOT_PAYLOAD_NOT_ACCEPTED = "REJECT_BOUNDED_PILOT_PAYLOAD_NOT_ACCEPTED"
    PILOT_RECEIPT_MISSING = "REJECT_BOUNDED_PILOT_RECEIPT_MISSING"
    PILOT_SIDE_EFFECT_FLAGS_INVALID = "REJECT_BOUNDED_PILOT_SIDE_EFFECT_FLAGS_INVALID"
    VERIFIER_REQUEST_INVALID = "REJECT_VERIFIER_REQUEST_INVALID"
    WORK_ORDER_ID_MISMATCH = "REJECT_WORK_ORDER_ID_MISMATCH"
    DIFF_PATHS_MISMATCH = "REJECT_DIFF_PATHS_DO_NOT_MATCH_PILOT_ARTIFACTS"
    VERIFIER_NOT_ACCEPTED = "REJECT_AUTONOMOUS_SLICE_VERIFIER_NOT_ACCEPTED"


@dataclass(frozen=True)
class QueueAuthorizedSliceVerifierInvokeResult:
    decision: str
    rejection_reasons: List[str] = field(default_factory=list)
    verifier_result: Optional[AutonomousSliceVerifierResult] = None
    explicit_queue_authorized_slice_verifier_requested: bool = False
    no_command_execution_performed: bool = True
    no_github_call_performed: bool = True
    no_pr_publish_performed: bool = True
    no_merge_performed: bool = True
    no_pattern_memory_write_performed: bool = True
    no_reward_settlement_performed: bool = True
    no_holoindex_reindex_performed: bool = True

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["verifier_result"] = self.verifier_result.to_dict() if self.verifier_result else None
        return payload


def _mapping(value: Any) -> Mapping[str, Any]:
    if hasattr(value, "to_dict"):
        candidate = value.to_dict()
        return candidate if isinstance(candidate, Mapping) else {}
    if isinstance(value, Mapping):
        return value
    return {}


def _list(value: Any) -> List[Any]:
    return value if isinstance(value, list) else []


def _dedupe(values: Sequence[str]) -> List[str]:
    return list(dict.fromkeys(str(v) for v in values if str(v or "").strip()))


def _reject(
    reasons: Sequence[str],
    *,
    explicit_requested: bool,
    verifier_result: Optional[AutonomousSliceVerifierResult] = None,
) -> QueueAuthorizedSliceVerifierInvokeResult:
    return QueueAuthorizedSliceVerifierInvokeResult(
        decision=QUEUE_AUTHORIZED_SLICE_VERIFIER_INVOKE_REJECT,
        rejection_reasons=_dedupe(reasons),
        verifier_result=verifier_result,
        explicit_queue_authorized_slice_verifier_requested=explicit_requested,
    )


def _changed_paths(verifier_request: Mapping[str, Any]) -> List[str]:
    diff_evidence = _mapping(verifier_request.get("diff_evidence"))
    return [str(path).replace("\\", "/").strip().strip("/") for path in _list(diff_evidence.get("changed_paths"))]


def _written_artifacts(pilot_receipt: Mapping[str, Any]) -> List[str]:
    return [
        str(path).replace("\\", "/").strip().strip("/")
        for path in _list(pilot_receipt.get("written_artifacts"))
    ]


def _pilot_flags_ok(queue_pilot: Mapping[str, Any], pilot_payload: Mapping[str, Any]) -> bool:
    return (
        queue_pilot.get("shell_command_executed") is False
        and queue_pilot.get("draft_pr_created") is False
        and queue_pilot.get("merge_performed") is False
        and queue_pilot.get("openclaw_enqueue_performed") is False
        and queue_pilot.get("hermes_dispatch_performed") is False
        and queue_pilot.get("reward_settlement_performed") is False
        and queue_pilot.get("holoindex_reindex_performed") is False
        and pilot_payload.get("shell_command_executed") is False
        and pilot_payload.get("draft_pr_created") is False
        and pilot_payload.get("merge_performed") is False
        and pilot_payload.get("openclaw_enqueue_performed") is False
        and pilot_payload.get("hermes_dispatch_performed") is False
        and pilot_payload.get("reward_settlement_performed") is False
        and pilot_payload.get("holoindex_reindex_performed") is False
    )


def _enrich_verifier_request(
    verifier_request: Mapping[str, Any],
    pilot_receipt: Mapping[str, Any],
    artifact_generation_receipt: Mapping[str, Any],
) -> Dict[str, Any]:
    enriched = dict(verifier_request)
    enriched["worktree_receipt"] = {
        "accepted": True,
        "receipt_id": str(pilot_receipt.get("receipt_id") or ""),
    }
    enriched["bounded_worker_pilot_receipt"] = {
        "accepted": True,
        **dict(pilot_receipt),
    }
    if artifact_generation_receipt:
        enriched["artifact_generation_receipt"] = dict(artifact_generation_receipt)
    return enriched


def invoke_reddog_wre_queue_authorized_slice_verifier(
    *,
    explicit_queue_authorized_slice_verifier_requested: bool,
    queue_bounded_worker_pilot_result: Mapping[str, Any],
    verifier_request: Mapping[str, Any],
) -> QueueAuthorizedSliceVerifierInvokeResult:
    """Invoke the independent autonomous-slice verifier after a bounded pilot."""

    if explicit_queue_authorized_slice_verifier_requested is not True:
        return _reject(
            [QueueAuthorizedSliceVerifierInvokeReason.EXPLICIT_INVOKE_MISSING],
            explicit_requested=False,
        )

    reasons: List[str] = []
    queue_pilot = _mapping(queue_bounded_worker_pilot_result)
    if queue_pilot.get("decision") != QUEUE_AUTHORIZED_BOUNDED_WORKER_PILOT_INVOKE_ACCEPT:
        reasons.append(QueueAuthorizedSliceVerifierInvokeReason.BOUNDED_PILOT_NOT_ACCEPTED)

    pilot_payload = _mapping(queue_pilot.get("pilot_result"))
    if not pilot_payload:
        reasons.append(QueueAuthorizedSliceVerifierInvokeReason.PILOT_PAYLOAD_MISSING)
    elif pilot_payload.get("decision") != BOUNDED_WORKTREE_PILOT_ACCEPT:
        reasons.append(QueueAuthorizedSliceVerifierInvokeReason.PILOT_PAYLOAD_NOT_ACCEPTED)

    pilot_receipt = _mapping(pilot_payload.get("receipt"))
    if not pilot_receipt:
        reasons.append(QueueAuthorizedSliceVerifierInvokeReason.PILOT_RECEIPT_MISSING)
    artifact_generation_receipt = _mapping(
        _mapping(queue_pilot.get("artifact_generation_result")).get("receipt")
    )

    if pilot_payload and not _pilot_flags_ok(queue_pilot, pilot_payload):
        reasons.append(QueueAuthorizedSliceVerifierInvokeReason.PILOT_SIDE_EFFECT_FLAGS_INVALID)

    verifier_payload = _mapping(verifier_request)
    if not verifier_payload:
        reasons.append(QueueAuthorizedSliceVerifierInvokeReason.VERIFIER_REQUEST_INVALID)

    if pilot_receipt and verifier_payload:
        if str(verifier_payload.get("work_order_id") or "") != str(pilot_receipt.get("work_order_id") or ""):
            reasons.append(QueueAuthorizedSliceVerifierInvokeReason.WORK_ORDER_ID_MISMATCH)
        if sorted(_changed_paths(verifier_payload)) != sorted(_written_artifacts(pilot_receipt)):
            reasons.append(QueueAuthorizedSliceVerifierInvokeReason.DIFF_PATHS_MISMATCH)

    if reasons:
        return _reject(reasons, explicit_requested=True)

    verifier = verify_autonomous_slice_runtime(
        _enrich_verifier_request(
            verifier_payload,
            pilot_receipt,
            artifact_generation_receipt,
        )
    )
    if verifier.decision != AUTONOMOUS_SLICE_VERIFIER_ACCEPT:
        return _reject(
            [
                QueueAuthorizedSliceVerifierInvokeReason.VERIFIER_NOT_ACCEPTED,
                *verifier.rejection_reasons,
            ],
            explicit_requested=True,
            verifier_result=verifier,
        )

    return QueueAuthorizedSliceVerifierInvokeResult(
        decision=QUEUE_AUTHORIZED_SLICE_VERIFIER_INVOKE_ACCEPT,
        rejection_reasons=[],
        verifier_result=verifier,
        explicit_queue_authorized_slice_verifier_requested=True,
    )


__all__ = [
    "QUEUE_AUTHORIZED_SLICE_VERIFIER_INVOKE_ACCEPT",
    "QUEUE_AUTHORIZED_SLICE_VERIFIER_INVOKE_REJECT",
    "QueueAuthorizedSliceVerifierInvokeReason",
    "QueueAuthorizedSliceVerifierInvokeResult",
    "invoke_reddog_wre_queue_authorized_slice_verifier",
]
