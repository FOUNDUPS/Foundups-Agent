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


def _produced_held_out_receipt():
    from modules.infrastructure.wre_core.tests import (
        test_wre_autonomous_slice_verifier_runtime as verifier_tests,
        test_reddog_held_out_recursive_improvement_regression_gate as gate_tests,
    )
    from modules.infrastructure.wre_core.src import (
        reddog_held_out_recursive_improvement_regression_gate as gate,
    )
    from modules.communication.moltbot_bridge.src.foundup_memex_verified_outcome_receipt_rehydration import (
        rehydrate_verified_slice_receipt,
    )

    verification = verifier_tests._verify(verifier_tests.valid_request())
    assert verification.accepted
    verifier = rehydrate_verified_slice_receipt(verification.receipt.to_dict())
    request = gate_tests.valid_request()
    request.update(work_order_id=verifier.work_order_id, slice_name=verifier.slice_name,
                   worker_id=verifier.worker_id, verification_result=verification.to_dict())
    request["held_out_regression"].update(
        evidence_author_id=verifier.verifier_id, candidate_head_sha=verifier.head_sha,
    )
    ratchet = gate_tests.record_gate_fixture(request)
    assert ratchet.accepted
    request["ratchet_result"] = ratchet.to_dict()
    result = gate.evaluate_held_out_recursive_improvement_regression_gate(request)
    assert result.accepted
    return result, verifier


def test_current_gate_receipt_roundtrips_into_memex_without_identity_rewrite():
    from modules.communication.moltbot_bridge.src.foundup_memex_verified_outcome_receipt_rehydration import (
        rehydrate_held_out_outcome_receipt,
    )

    result, verifier = _produced_held_out_receipt()
    wire = result.to_dict()["receipt"]
    restored = rehydrate_held_out_outcome_receipt(wire, verifier=verifier)
    assert restored.to_dict() == wire
    assert restored.gate_id == result.receipt.gate_id
    assert wire["identity_version"] == 2
    assert wire["evidence_digest"].startswith("sha256:")


@pytest.mark.parametrize("case", [
    "strip_both", "strip_version", "strip_digest", "bool_version", "float_version",
    "string_version", "unknown_version", "legacy_version", "null_digest",
    "empty_digest", "numeric_digest", "changed_digest", "extra_field",
])
def test_current_gate_receipt_rejects_tampering_and_downgrade(case):
    from modules.communication.moltbot_bridge.src.foundup_memex_verified_outcome_receipt_rehydration import (
        rehydrate_held_out_outcome_receipt,
    )

    result, verifier = _produced_held_out_receipt()
    wire = result.receipt.to_dict()
    if case == "strip_both":
        wire.pop("identity_version", None)
        wire.pop("evidence_digest", None)
    elif case == "strip_version":
        wire.pop("identity_version", None)
    elif case == "strip_digest":
        wire.pop("evidence_digest", None)
    elif case.endswith("_version"):
        wire["identity_version"] = {
            "bool_version": True, "float_version": 2.0, "string_version": "2",
            "unknown_version": 3, "legacy_version": 1,
        }[case]
    elif case == "extra_field":
        wire["unexpected"] = "value"
    else:
        wire["evidence_digest"] = {
            "null_digest": None, "empty_digest": "", "numeric_digest": 1,
            "changed_digest": "sha256:" + "0" * 64,
        }[case]
    with pytest.raises(ValueError):
        rehydrate_held_out_outcome_receipt(wire, verifier=verifier)


def test_legacy_held_out_receipt_preserves_exact_signed_wire_shape():
    from modules.communication.moltbot_bridge.tests.test_foundup_memex_verified_outcome_authenticity import (
        _verifier_receipt, _held_out_receipt,
    )
    from modules.communication.moltbot_bridge.src.foundup_memex_verified_outcome_receipt_rehydration import (
        rehydrate_verified_slice_receipt, rehydrate_held_out_outcome_receipt,
    )

    verifier_wire = _verifier_receipt()
    wire = _held_out_receipt(verifier_wire)
    restored = rehydrate_held_out_outcome_receipt(
        wire, verifier=rehydrate_verified_slice_receipt(verifier_wire),
    )
    assert restored.to_dict() == wire
    assert "identity_version" not in restored.to_dict()
    assert "evidence_digest" not in restored.to_dict()


@pytest.mark.parametrize("metadata", [
    {"identity_version": True}, {"identity_version": 1.0},
    {"evidence_digest": None}, {"evidence_digest": 0},
])
def test_legacy_serialization_does_not_hide_malformed_identity(metadata):
    from dataclasses import replace
    from modules.communication.moltbot_bridge.tests.test_foundup_memex_verified_outcome_authenticity import (
        _verifier_receipt, _held_out_receipt,
    )
    from modules.communication.moltbot_bridge.src.foundup_memex_verified_outcome_receipt_rehydration import (
        rehydrate_verified_slice_receipt, rehydrate_held_out_outcome_receipt,
    )

    verifier_wire = _verifier_receipt()
    verifier = rehydrate_verified_slice_receipt(verifier_wire)
    legacy = rehydrate_held_out_outcome_receipt(
        _held_out_receipt(verifier_wire), verifier=verifier,
    )
    wire = replace(legacy, **metadata).to_dict()
    with pytest.raises(ValueError):
        rehydrate_held_out_outcome_receipt(wire, verifier=verifier)


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
