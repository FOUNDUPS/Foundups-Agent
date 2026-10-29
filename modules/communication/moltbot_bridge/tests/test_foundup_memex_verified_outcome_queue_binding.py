"""Focused tests for resident queue verified-outcome authority binding."""

from __future__ import annotations

import copy
from pathlib import Path

import pytest

from modules.communication.moltbot_bridge.src.reddog_resident_queue_chain_results_store import (
    AtomicJsonResidentQueueChainResultsStore,
    InMemoryResidentQueueChainResultsStore,
    ResidentQueueChainResultReceipt,
    resident_queue_chain_receipt_id,
)
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


RECORDED_AT = "2026-08-04T00:00:00Z"


def _chain() -> dict:
    state = {
        "schema_version": "reddog_resident_queue_chain_results.v1",
        "selected_slice": "SLICE_PHASE1",
        "updated_at": RECORDED_AT,
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
    receipt_fields = {
        "queue_item_id": "queue-1", "selected_slice": "SLICE_PHASE1",
        "recorded_stage": "held_out_regression_gate",
        "previous_plan_id": "plan-before", "next_plan_id": "plan-after",
    }
    receipt = ResidentQueueChainResultReceipt(
        receipt_id=resident_queue_chain_receipt_id(**receipt_fields),
        **receipt_fields, next_action="invoke-pattern-memory", store_revision=None,
    ).to_dict()
    receipt["recorded_at"] = RECORDED_AT
    state["receipts"] = [receipt]
    store = InMemoryResidentQueueChainResultsStore()
    store.commit(state, expected_revision=None)
    return dict(store.load())


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
    assert metadata["verified_at"] == RECORDED_AT


def test_admission_timestamp_survives_store_reload_and_later_snapshot(tmp_path: Path) -> None:
    snapshot = _snapshot(
        foundup_id="foundup-1", snapshot_id="snapshot-1",
        snapshot_content_digest="sha256:" + "d" * 64,
    )
    store = AtomicJsonResidentQueueChainResultsStore(tmp_path / "chain.json", allowed_root=tmp_path)
    store.commit(_chain(), expected_revision=None)
    initial = derive_verified_outcome_admission(store.load(), snapshot, RECORDED_AT)
    assert initial is not None
    later = dict(store.load())
    later["updated_at"] = "2026-08-04T00:00:02Z"
    store.commit(later, expected_revision=later["revision"])
    reopened = AtomicJsonResidentQueueChainResultsStore(tmp_path / "chain.json", allowed_root=tmp_path)
    durable_bytes = (tmp_path / "chain.json").read_bytes()
    retry = derive_verified_outcome_admission(reopened.load(), snapshot, "2026-08-04T00:00:03Z")
    assert retry == initial
    assert retry["admission_metadata"]["verified_at"] == RECORDED_AT
    assert (tmp_path / "chain.json").read_bytes() == durable_bytes


@pytest.mark.parametrize("case", [
    "missing_time", "naive_time", "malformed_time", "future_time",
    "wrong_queue", "wrong_slice", "wrong_receipt_id", "duplicate_receipt",
    "missing_receipt", "noncanonical_snapshot",
])
def test_admission_rejects_unbound_or_missing_event_time(case: str) -> None:
    chain = _chain()
    receipt = chain["receipts"][0]
    if case == "missing_time":
        receipt.pop("recorded_at")
    elif case == "naive_time":
        receipt["recorded_at"] = "2026-08-04T00:00:00"
    elif case == "malformed_time":
        receipt["recorded_at"] = "invalid"
    elif case == "future_time":
        receipt["recorded_at"] = "2026-08-04T00:00:10Z"
    elif case == "wrong_queue":
        receipt["queue_item_id"] = "another-queue"
    elif case == "wrong_slice":
        receipt["selected_slice"] = "ANOTHER_SLICE"
    elif case == "wrong_receipt_id":
        receipt["receipt_id"] = "sha256:" + "f" * 64
    elif case == "duplicate_receipt":
        chain["receipts"].append(copy.deepcopy(receipt))
    elif case == "missing_receipt":
        chain["receipts"] = []
    elif case == "noncanonical_snapshot":
        receipt["recorded_at"] = "2026-08-03T23:59:59Z"
    if case != "noncanonical_snapshot":
        store = InMemoryResidentQueueChainResultsStore()
        store.commit(chain, expected_revision=None)
        chain = dict(store.load())
    before = copy.deepcopy(chain)
    assert derive_verified_outcome_admission(
        chain,
        _snapshot(foundup_id="foundup-1", snapshot_id="snapshot-1", snapshot_content_digest="sha256:" + "d" * 64),
        "2026-08-04T00:00:03Z",
    ) is None
    assert chain == before


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
