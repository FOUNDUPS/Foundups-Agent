"""Resident RedDog PatternMemory admission stage handler.

Slice: REDDOG_RESIDENT_QUEUE_PATTERN_MEMORY_ADMISSION_HANDLER_PHASE1

This module adapts the existing queue-authorized PatternMemory admission
explicit invoke guard to the resident queue next-stage dispatcher. It reads the
recorded `held_out_regression_gate` stage result from the chain-results store
and invokes the existing admission guard with an injected admission request and
sink.

It writes only through the injected sink after held-out regression acceptance.
It does not instantiate PatternMemory, run commands, publish PRs, merge, settle
rewards, enqueue OpenClaw, dispatch Hermes, or re-index HoloIndex.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Optional

from modules.communication.moltbot_bridge.src.foundup_memex_verified_outcome_publisher import (
    VerifiedOutcomeEvidencePublisher,
)

from modules.communication.moltbot_bridge.src.reddog_resident_queue_chain_results_store import (
    ResidentQueueChainResultsStore,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_next_stage_dispatch import (
    ResidentQueueStageDispatchRequest,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_orchestration_plan import (
    NEXT_QUEUE_PATTERN_MEMORY_ADMISSION_INVOKE,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_authorized_pattern_memory_admission_invoke import (
    PatternMemoryAdmissionSink,
    QUEUE_AUTHORIZED_PATTERN_MEMORY_ADMISSION_INVOKE_REJECT,
    invoke_reddog_wre_queue_authorized_pattern_memory_admission,
)
from modules.communication.moltbot_bridge.src.reddog_verified_pattern_memory_sink import (
    reddog_verified_pattern_memory_record_id,
)


PATTERN_MEMORY_ADMISSION_STAGE_KEY = "pattern_memory_admission"
HELD_OUT_REGRESSION_GATE_STAGE_KEY = "held_out_regression_gate"

FAIL_DISPATCH_STAGE_MISMATCH = "FAIL_DISPATCH_STAGE_MISMATCH"
FAIL_DISPATCH_NEXT_ACTION_MISMATCH = "FAIL_DISPATCH_NEXT_ACTION_MISMATCH"
FAIL_HELD_OUT_REGRESSION_GATE_STAGE_MISSING = "FAIL_HELD_OUT_REGRESSION_GATE_STAGE_MISSING"
FAIL_ADMISSION_REQUEST_MISSING = "FAIL_ADMISSION_REQUEST_MISSING"
FAIL_PATTERN_MEMORY_SINK_MISSING = "FAIL_PATTERN_MEMORY_SINK_MISSING"
FAIL_VERIFIED_OUTCOME_EVIDENCE_PUBLICATION = (
    "FAIL_VERIFIED_OUTCOME_EVIDENCE_PUBLICATION"
)
SLICE_VERIFIER_STAGE_KEY = "slice_verifier"


def _mapping(value: Any) -> Mapping[str, Any]:
    if hasattr(value, "to_dict"):
        candidate = value.to_dict()
        return candidate if isinstance(candidate, Mapping) else {}
    if isinstance(value, Mapping):
        return value
    return {}


def _stage_results(state: Mapping[str, Any]) -> Mapping[str, Mapping[str, Any]]:
    raw = state.get("stage_results") if state.get("schema_version") == "reddog_resident_queue_chain_results.v1" else state
    if not isinstance(raw, Mapping):
        return {}
    return {str(key): value for key, value in raw.items() if isinstance(value, Mapping)}


def _reject(*reasons: str) -> dict[str, Any]:
    return {
        "decision": QUEUE_AUTHORIZED_PATTERN_MEMORY_ADMISSION_INVOKE_REJECT,
        "rejection_reasons": list(dict.fromkeys(reason for reason in reasons if reason)),
        "receipt": None,
        "explicit_queue_authorized_pattern_memory_admission_requested": False,
        "pattern_memory_write_performed": False,
        "no_command_execution_performed": True,
        "no_pr_publish_performed": True,
        "no_merge_performed": True,
        "no_reward_settlement_performed": True,
        "no_holoindex_reindex_performed": True,
    }


@dataclass(frozen=True)
class ResidentQueuePatternMemoryAdmissionStageHandler:
    """Callable handler for the resident queue `pattern_memory_admission` stage."""

    chain_results_store: ResidentQueueChainResultsStore
    admission_request: Mapping[str, Any]
    sink: Optional[PatternMemoryAdmissionSink]
    evidence_publisher: Optional[VerifiedOutcomeEvidencePublisher] = None

    def __call__(self, request: ResidentQueueStageDispatchRequest) -> Mapping[str, Any]:
        if request.stage_key != PATTERN_MEMORY_ADMISSION_STAGE_KEY:
            return _reject(
                FAIL_DISPATCH_STAGE_MISMATCH,
                f"expected:{PATTERN_MEMORY_ADMISSION_STAGE_KEY}",
                f"actual:{request.stage_key}",
            )
        if request.next_action != NEXT_QUEUE_PATTERN_MEMORY_ADMISSION_INVOKE:
            return _reject(
                FAIL_DISPATCH_NEXT_ACTION_MISMATCH,
                f"expected:{NEXT_QUEUE_PATTERN_MEMORY_ADMISSION_INVOKE}",
                f"actual:{request.next_action}",
            )
        stored = _mapping(self.chain_results_store.load())
        stage_results = _stage_results(stored)
        held_out_gate = _mapping(stage_results.get(HELD_OUT_REGRESSION_GATE_STAGE_KEY))
        if not held_out_gate:
            return _reject(FAIL_HELD_OUT_REGRESSION_GATE_STAGE_MISSING)

        admission_request = _mapping(self.admission_request)
        if not admission_request:
            return _reject(FAIL_ADMISSION_REQUEST_MISSING)
        admission_metadata = _mapping(admission_request.get("admission_metadata"))
        if (
            admission_metadata.get("schema_version")
            == "foundup_memex_verified_outcome_binding.v2"
            and self.evidence_publisher is None
        ):
            return _reject(FAIL_VERIFIED_OUTCOME_EVIDENCE_PUBLICATION)
        if self.sink is None:
            return _reject(FAIL_PATTERN_MEMORY_SINK_MISSING)

        if self.evidence_publisher is not None:
            return _publish_then_admit(
                publisher=self.evidence_publisher,
                sink=self.sink,
                stage_results=stage_results,
                held_out_gate=held_out_gate,
                admission_request=admission_request,
            )

        result = invoke_reddog_wre_queue_authorized_pattern_memory_admission(
            explicit_queue_authorized_pattern_memory_admission_requested=True,
            queue_held_out_gate_result=held_out_gate,
            admission_request=admission_request,
            sink=self.sink,
        )
        payload = result.to_dict()
        payload["verified_outcome_authority_published"] = False
        return payload


class _ValidatedRecordCapture:
    def __init__(self) -> None:
        self.record: Optional[dict[str, Any]] = None

    def store_verified_outcome(self, record: Mapping[str, Any]) -> str:
        if self.record is not None:
            raise RuntimeError("verified_outcome_capture_reused")
        self.record = dict(record)
        return reddog_verified_pattern_memory_record_id(self.record)


def _publish_then_admit(
    *,
    publisher: VerifiedOutcomeEvidencePublisher,
    sink: PatternMemoryAdmissionSink,
    stage_results: Mapping[str, Mapping[str, Any]],
    held_out_gate: Mapping[str, Any],
    admission_request: Mapping[str, Any],
) -> Mapping[str, Any]:
    capture = _ValidatedRecordCapture()
    validation = invoke_reddog_wre_queue_authorized_pattern_memory_admission(
        explicit_queue_authorized_pattern_memory_admission_requested=True,
        queue_held_out_gate_result=held_out_gate,
        admission_request=admission_request,
        sink=capture,
    )
    payload = validation.to_dict()
    payload["verified_outcome_authority_published"] = False
    if validation.decision == QUEUE_AUTHORIZED_PATTERN_MEMORY_ADMISSION_INVOKE_REJECT:
        return payload
    record = capture.record
    if record is None:
        return _publication_reject(payload)
    record_id = reddog_verified_pattern_memory_record_id(record)
    published_id = _publish_authority(
        publisher=publisher,
        stage_results=stage_results,
        held_out_gate=held_out_gate,
        record=record,
        record_id=record_id,
    )
    if published_id != record_id:
        return _publication_reject(payload)
    return _admit_published(
        publisher=publisher,
        sink=sink,
        held_out_gate=held_out_gate,
        admission_request=admission_request,
        record_id=record_id,
    )


def _publish_authority(
    *,
    publisher: VerifiedOutcomeEvidencePublisher,
    stage_results: Mapping[str, Mapping[str, Any]],
    held_out_gate: Mapping[str, Any],
    record: Mapping[str, Any],
    record_id: str,
) -> Optional[str]:
    verifier_stage = _mapping(stage_results.get(SLICE_VERIFIER_STAGE_KEY))
    verifier_result = _mapping(verifier_stage.get("verifier_result"))
    verification_receipt = _mapping(verifier_result.get("receipt"))
    held_out_payload = _mapping(held_out_gate.get("gate_result"))
    held_out_receipt = _mapping(held_out_payload.get("receipt"))
    try:
        published_id = publisher.publish(
            record_id=record_id,
            record=record,
            verification_receipt=verification_receipt,
            held_out_receipt=held_out_receipt,
        )
    except Exception:
        return None
    return str(published_id or "")


def _admit_published(
    *,
    publisher: VerifiedOutcomeEvidencePublisher,
    sink: PatternMemoryAdmissionSink,
    held_out_gate: Mapping[str, Any],
    admission_request: Mapping[str, Any],
    record_id: str,
) -> Mapping[str, Any]:
    admitted = invoke_reddog_wre_queue_authorized_pattern_memory_admission(
        explicit_queue_authorized_pattern_memory_admission_requested=True,
        queue_held_out_gate_result=held_out_gate,
        admission_request=admission_request,
        sink=sink,
    )
    admitted_payload = admitted.to_dict()
    admitted_payload["verified_outcome_authority_published"] = False
    admitted_record_id = str(
        _mapping(admitted_payload.get("receipt")).get("pattern_memory_record_id") or ""
    )
    if (
        admitted.decision == QUEUE_AUTHORIZED_PATTERN_MEMORY_ADMISSION_INVOKE_REJECT
        or admitted_record_id != record_id
    ):
        admitted_payload["decision"] = (
            QUEUE_AUTHORIZED_PATTERN_MEMORY_ADMISSION_INVOKE_REJECT
        )
        admitted_payload["rejection_reasons"] = [
            FAIL_VERIFIED_OUTCOME_EVIDENCE_PUBLICATION
        ]
        return admitted_payload
    try:
        activated_id = publisher.activate(record_id)
    except Exception:
        activated_id = ""
    if activated_id != record_id:
        admitted_payload["decision"] = (
            QUEUE_AUTHORIZED_PATTERN_MEMORY_ADMISSION_INVOKE_REJECT
        )
        admitted_payload["rejection_reasons"] = [
            FAIL_VERIFIED_OUTCOME_EVIDENCE_PUBLICATION
        ]
        return admitted_payload
    admitted_payload["verified_outcome_authority_published"] = True
    admitted_payload["verified_outcome_authority_record_id"] = record_id
    return admitted_payload


def _publication_reject(payload: dict[str, Any]) -> Mapping[str, Any]:
    payload["decision"] = QUEUE_AUTHORIZED_PATTERN_MEMORY_ADMISSION_INVOKE_REJECT
    payload["rejection_reasons"] = [FAIL_VERIFIED_OUTCOME_EVIDENCE_PUBLICATION]
    payload["pattern_memory_write_performed"] = False
    return payload


def build_reddog_resident_queue_pattern_memory_admission_stage_handler(
    *,
    chain_results_store: ResidentQueueChainResultsStore,
    admission_request: Mapping[str, Any],
    sink: Optional[PatternMemoryAdmissionSink],
    evidence_publisher: Optional[VerifiedOutcomeEvidencePublisher] = None,
) -> ResidentQueuePatternMemoryAdmissionStageHandler:
    """Build the injected PatternMemory admission handler for the dispatcher."""

    return ResidentQueuePatternMemoryAdmissionStageHandler(
        chain_results_store=chain_results_store,
        admission_request=admission_request,
        sink=sink,
        evidence_publisher=evidence_publisher,
    )


__all__ = [
    "FAIL_ADMISSION_REQUEST_MISSING",
    "FAIL_DISPATCH_NEXT_ACTION_MISMATCH",
    "FAIL_DISPATCH_STAGE_MISMATCH",
    "FAIL_HELD_OUT_REGRESSION_GATE_STAGE_MISSING",
    "FAIL_PATTERN_MEMORY_SINK_MISSING",
    "FAIL_VERIFIED_OUTCOME_EVIDENCE_PUBLICATION",
    "HELD_OUT_REGRESSION_GATE_STAGE_KEY",
    "PATTERN_MEMORY_ADMISSION_STAGE_KEY",
    "ResidentQueuePatternMemoryAdmissionStageHandler",
    "build_reddog_resident_queue_pattern_memory_admission_stage_handler",
]
