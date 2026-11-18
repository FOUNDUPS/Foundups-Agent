"""Current queue-truth regressions for the RedDog execution valve."""

from __future__ import annotations

import pytest

from modules.communication.moltbot_bridge.src.reddog_execution_valve_use_time_authority import (
    _queue_receipt_binding_reasons,
)
from modules.communication.moltbot_bridge.src.reddog_work_order_binding import (
    canonical_full_work_order_digest,
)


def _queue_binding_fixture():
    receipt = {
        "queue_item_id": "queue-1",
        "slice_id": "REDDOG_TEST_SLICE_PHASE1",
        "claim_id": "claim-1",
        "worker_id": "worker-1",
        "progressive_policy_stage_receipt_id": "sha256:" + ("1" * 64),
        "progressive_policy_stage_digest": "sha256:" + ("2" * 64),
    }
    authority = {
        "work_order_id": "wo-bound",
        "selected_slice": receipt["slice_id"],
        "queue_consumer_receipt_digest": canonical_full_work_order_digest(receipt),
        "progressive_policy_stage_receipt_id": receipt[
            "progressive_policy_stage_receipt_id"
        ],
        "progressive_policy_stage_digest": receipt["progressive_policy_stage_digest"],
    }
    return receipt, authority


def _reasons(receipt, authority, selected_slice=None):
    return _queue_receipt_binding_reasons(
        receipt,
        authority,
        {"work_order_id": "wo-bound"},
        selected_slice or receipt["slice_id"],
    )


def test_exact_current_queue_receipt_is_accepted() -> None:
    receipt, authority = _queue_binding_fixture()

    assert _reasons(receipt, authority) == []


@pytest.mark.parametrize(
    ("field", "replacement", "expected_reason"),
    (
        (
            "claim_id",
            "claim-substituted",
            "canonical_queue_authority_binding_mismatch:queue_consumer_receipt_digest",
        ),
        (
            "slice_id",
            "REDDOG_OTHER_SLICE_PHASE1",
            "canonical_queue_authority_binding_mismatch:slice_id",
        ),
        (
            "progressive_policy_stage_receipt_id",
            "sha256:" + ("3" * 64),
            "canonical_queue_authority_binding_mismatch:progressive_policy_stage_receipt_id",
        ),
        (
            "progressive_policy_stage_digest",
            "sha256:" + ("4" * 64),
            "canonical_queue_authority_binding_mismatch:progressive_policy_stage_digest",
        ),
    ),
)
def test_current_queue_receipt_substitution_is_rejected(
    field: str, replacement: str, expected_reason: str
) -> None:
    receipt, authority = _queue_binding_fixture()
    receipt[field] = replacement

    assert expected_reason in _reasons(receipt, authority)


def test_caller_selected_slice_substitution_is_rejected() -> None:
    receipt, authority = _queue_binding_fixture()

    reasons = _reasons(receipt, authority, "REDDOG_OTHER_SLICE_PHASE1")

    assert "canonical_queue_authority_binding_mismatch:selected_slice" in reasons
