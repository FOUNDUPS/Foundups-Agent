"""Focused Memex lineage checks for signed worker dispatch."""

import pytest

from modules.communication.moltbot_bridge.src.reddog_signed_worker_0102_readonly_review_binding import (
    build_readonly_0102_context_from_signed_worker,
)
from modules.communication.moltbot_bridge.src.reddog_signed_worker_dispatch_task_executor import (
    SignedWorkerDispatchTaskExecutorReason,
    _memex_binding_reasons,
)
from modules.communication.moltbot_bridge.src.reddog_signer_optional_authority_bindings import (
    optional_authority_binding_values_valid,
)


MEMEX_ID = "sha256:memex-supply"
MEMEX_DIGEST = "sha256:" + ("d" * 64)


def _binding(**overrides: str) -> dict[str, str]:
    payload = {
        "memex_supply_receipt_id": MEMEX_ID,
        "memex_supply_digest": MEMEX_DIGEST,
    }
    payload.update(overrides)
    return payload


def test_executor_memex_triplet_accepts_exact_signed_lineage() -> None:
    binding = _binding()

    assert _memex_binding_reasons(
        context=binding,
        intent=binding,
        receipt=binding,
    ) == []


def test_executor_memex_triplet_rejects_tamper_and_half_pair() -> None:
    assert _memex_binding_reasons(
        context=_binding(memex_supply_digest="sha256:tampered"),
        intent=_binding(),
        receipt=_binding(),
    ) == [
        SignedWorkerDispatchTaskExecutorReason.MEMEX_SUPPLY_BINDING_MISMATCH
    ]
    assert _memex_binding_reasons(
        context=_binding(memex_supply_digest=""),
        intent=_binding(),
        receipt=_binding(),
    ) == [
        SignedWorkerDispatchTaskExecutorReason.MEMEX_SUPPLY_BINDING_MISMATCH
    ]


def test_executor_memex_triplet_preserves_absent_compatibility() -> None:
    absent = {
        "memex_supply_receipt_id": "",
        "memex_supply_digest": "",
    }

    assert _memex_binding_reasons(
        context=absent,
        intent=absent,
        receipt=absent,
    ) == []


def test_memex_binding_rejects_non_string_receipt_identity() -> None:
    assert optional_authority_binding_values_valid(
        {"receipt_id": MEMEX_ID},
        MEMEX_DIGEST,
    ) is False
    assert optional_authority_binding_values_valid(7, MEMEX_DIGEST) is False


def test_readonly_0102_assignment_preserves_signed_memex_lineage() -> None:
    allocation = {
        "receipt_id": "sha256:wsp15",
        "allowed_read_targets": ["docs/work_ledger.schema.json"],
    }
    authority = {
        "receipt_id": "signed-authority-receipt",
        "work_order_id": "work-order-1",
        "foundup_id": "paccess_001",
        **_binding(),
    }
    intent = {
        "intent_id": "worker-intent-1",
        "work_order_id": "work-order-1",
        "foundup_id": "paccess_001",
        **_binding(),
    }
    context = {
        "authorized_principal_id": "github:foundups",
        "queue_item_id": "queue-1",
        "selected_slice": "MEMEX_BINDING_PHASE1",
        "worker_role": "fusion_lead",
        "capability": "architect_review",
        "source": "reddog_signed_worker_dispatch_runtime",
        "worker_runtime": "0102",
        **_binding(),
    }

    readonly = build_readonly_0102_context_from_signed_worker(
        task_id="task-1",
        task_context=context,
        worker_dispatch_intent=intent,
        signed_authority_receipt=authority,
        allocation=allocation,
    )

    assert readonly["memex_supply_receipt_id"] == MEMEX_ID
    assert readonly["assignment"]["memex_supply_digest"] == MEMEX_DIGEST
    assert readonly["signed_worker_binding"]["memex_supply_receipt_id"] == MEMEX_ID


def test_readonly_0102_assignment_rejects_conflicting_memex_lineage() -> None:
    allocation = {
        "receipt_id": "sha256:wsp15",
        "allowed_read_targets": ["docs/work_ledger.schema.json"],
    }
    context = {
        "memex_supply_receipt_id": MEMEX_ID,
        "memex_supply_digest": MEMEX_DIGEST,
    }
    intent = dict(context)
    authority = dict(context)
    intent["memex_supply_digest"] = "sha256:" + ("e" * 64)

    with pytest.raises(ValueError, match="Memex authority binding"):
        build_readonly_0102_context_from_signed_worker(
            task_id="task-1",
            task_context=context,
            worker_dispatch_intent=intent,
            signed_authority_receipt=authority,
            allocation=allocation,
        )
