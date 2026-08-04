"""Focused tests for resident queue verified-outcome authority binding."""

from __future__ import annotations

from modules.communication.moltbot_bridge.src.foundup_memex_verified_outcome_queue_binding import (
    derive_verified_outcome_admission,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_pattern_memory_admission_handler import (
    FAIL_VERIFIED_OUTCOME_EVIDENCE_PUBLICATION,
    ResidentQueuePatternMemoryAdmissionStageHandler,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_next_stage_dispatch import (
    ResidentQueueStageDispatchRequest,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_orchestration_plan import (
    NEXT_QUEUE_PATTERN_MEMORY_ADMISSION_INVOKE,
)


def _chain() -> dict:
    return {
        "queue_item_id": "queue-1",
        "stage_results": {
            "slice_verifier": {
                "verifier_result": {
                    "receipt": {
                        "verifier_id": "verifier-1",
                        "worker_id": "worker-1",
                    }
                }
            },
            "held_out_regression_gate": {
                "gate_result": {
                    "accepted": True,
                    "receipt": {
                        "pattern_memory_admission_allowed": True,
                        "work_order_id": "work-1",
                        "gate_id": "gate-1",
                        "ratchet_id": "ratchet-1",
                        "verifier_receipt_id": "verify-1",
                        "held_out_suite_id": "suite-1",
                        "held_out_suite_digest": "sha256:" + "a" * 64,
                        "candidate_head_sha": "b" * 40,
                        "slice_name": "SLICE_PHASE1",
                        "improvement_job_id": "job-1",
                        "model_runtime_binding_receipt_id": "runtime-1",
                        "model_runtime_binding_digest": "sha256:" + "c" * 64,
                    },
                }
            },
        },
    }


def _snapshot(**queue_overrides: str) -> dict:
    queue_item = {"queue_item_id": "queue-1", **queue_overrides}
    return {"wre_queue_items": [queue_item]}


def test_queue_without_runtime_binding_rejects_by_default() -> None:
    admission = derive_verified_outcome_admission(_chain(), _snapshot(), "")

    assert admission is None


def test_hash_shaped_legacy_compatibility_cannot_authorize_admission() -> None:
    snapshot = _snapshot()
    snapshot["verified_outcome_legacy_compatibility"] = {
        "schema_version": "foundup_memex_verified_outcome_legacy_compatibility.v1",
        "mode": "AUTHENTICATED_AUTHORITATIVE_WORK_STATE",
        "enabled": True,
        "authorization_receipt_id": "sha256:" + "e" * 64,
    }
    admission = derive_verified_outcome_admission(_chain(), snapshot, "")

    assert admission is None


def test_complete_runtime_binding_requires_v2_signed_evidence() -> None:
    admission = derive_verified_outcome_admission(
        _chain(),
        _snapshot(
            foundup_id="foundup-1",
            snapshot_id="snapshot-1",
            snapshot_content_digest="sha256:" + "d" * 64,
        ),
        "2026-08-04T00:00:00Z",
    )

    assert admission is not None
    metadata = admission["admission_metadata"]
    assert metadata["schema_version"] == "foundup_memex_verified_outcome_binding.v2"
    assert metadata["foundup_id"] == "foundup-1"
    assert metadata["snapshot_id"] == "snapshot-1"
    assert metadata["verification_receipt_digest"].startswith("sha256:")
    assert metadata["held_out_receipt_digest"].startswith("sha256:")


def test_partial_runtime_binding_is_rejected() -> None:
    admission = derive_verified_outcome_admission(
        _chain(), _snapshot(foundup_id="foundup-1"), "2026-08-04T00:00:00Z"
    )

    assert admission is None


def test_missing_queue_item_rejects_even_with_legacy_compatibility() -> None:
    snapshot = {
        "wre_queue_items": [],
        "verified_outcome_legacy_compatibility": {
            "authorization_receipt_id": "sha256:" + "e" * 64
        },
    }

    assert derive_verified_outcome_admission(_chain(), snapshot, "") is None


class _Store:
    def load(self) -> dict:
        return {
            "schema_version": "reddog_resident_queue_chain_results.v1",
            "stage_results": _chain()["stage_results"],
        }


class _Sink:
    def __init__(self) -> None:
        self.calls = 0

    def store_verified_outcome(self, _record: object) -> str:
        self.calls += 1
        return "record-1"


def test_v2_admission_without_publisher_rejects_before_sink_write() -> None:
    sink = _Sink()
    admission = derive_verified_outcome_admission(
        _chain(),
        _snapshot(
            foundup_id="foundup-1",
            snapshot_id="snapshot-1",
            snapshot_content_digest="sha256:" + "d" * 64,
        ),
        "2026-08-04T00:00:00Z",
    )
    handler = ResidentQueuePatternMemoryAdmissionStageHandler(
        chain_results_store=_Store(),
        admission_request=admission or {},
        sink=sink,
    )

    result = handler(
        ResidentQueueStageDispatchRequest(
            stage_key="pattern_memory_admission",
            next_action=NEXT_QUEUE_PATTERN_MEMORY_ADMISSION_INVOKE,
            queue_item_id="queue-1",
            selected_slice="SLICE_PHASE1",
            plan_id="plan-1",
            accepted_stages=("held_out_regression_gate",),
        )
    )

    assert FAIL_VERIFIED_OUTCOME_EVIDENCE_PUBLICATION in result["rejection_reasons"]
    assert sink.calls == 0
