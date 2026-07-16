"""Assignment-bound Memex projection supplier for RedDog read-only workers.

The supplier turns an already assembled Memex view into a governed HoloIndex
shadow projection plus access-policy receipt. It performs no Memex write,
HoloIndex write, re-index, worker spawn, shell, or repo mutation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from holo_index.memex_access_policy_receipt import (
    MemexAccessPolicyReceipt,
    build_memex_access_policy_receipt,
)
from holo_index.memex_projection_adapter import (
    MemexProjectionResult,
    project_foundup_memex_to_holoindex_shadow,
)
from holo_index.memex_projection_integrity import verify_and_rehydrate_memex_projection


SUPPLIER_ACCEPTED = "MEMEX_SNAPSHOT_PROJECTION_SUPPLIED"
SUPPLIER_REJECTED = "MEMEX_SNAPSHOT_PROJECTION_REJECTED"


@dataclass(frozen=True)
class MemexSnapshotProjectionSupplyResult:
    accepted: bool
    status: str
    projection: MemexProjectionResult | None
    access_policy_receipt: MemexAccessPolicyReceipt | None
    rejection_reasons: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "accepted": self.accepted,
            "status": self.status,
            "projection": self.projection.to_dict() if self.projection else None,
            "access_policy_receipt": (
                self.access_policy_receipt.to_dict() if self.access_policy_receipt else None
            ),
            "rejection_reasons": list(self.rejection_reasons),
        }


def supply_assignment_bound_memex_projection(
    *,
    memex_view: Mapping[str, Any],
    foundup_id: str,
    principal_id: str,
    work_order_id: str,
    source_scope: str,
    source_revision: str,
    snapshot_receipt_id: str,
    snapshot_content_digest: str,
    holoindex_generation_id: str,
    issued_at: str,
    expires_at: str,
    sensitivity_classes: Sequence[str] = ("internal",),
    allowed_record_sections: Sequence[str] = (),
    denied_record_sections: Sequence[str] = (),
    max_records: int = 32,
) -> MemexSnapshotProjectionSupplyResult:
    """Supply a verified projection and policy receipt for one assignment."""

    reasons: list[str] = []
    if not isinstance(memex_view, Mapping):
        return _reject("memex_view_not_mapping")

    expected = {
        "foundup_id": _clean(foundup_id),
        "principal_id": _clean(principal_id),
        "work_order_id": _clean(work_order_id),
        "source_scope": _clean(source_scope),
        "source_revision": _clean(source_revision),
        "snapshot_receipt_id": _clean(snapshot_receipt_id),
        "snapshot_content_digest": _clean(snapshot_content_digest),
        "holoindex_generation_id": _clean(holoindex_generation_id),
        "issued_at": _clean(issued_at),
        "expires_at": _clean(expires_at),
    }
    for key, value in expected.items():
        if not value:
            reasons.append(f"missing_{key}")

    if _clean(memex_view.get("foundup_id")) != expected["foundup_id"]:
        reasons.append("memex_view_foundup_mismatch")
    if _clean(memex_view.get("snapshot_id")) != expected["snapshot_receipt_id"]:
        reasons.append("memex_view_snapshot_id_mismatch")
    if _clean(memex_view.get("snapshot_content_digest")) != expected["snapshot_content_digest"]:
        reasons.append("memex_view_snapshot_digest_mismatch")
    if reasons:
        return _reject(*reasons)

    policy = build_memex_access_policy_receipt(
        principal_id=expected["principal_id"],
        work_order_id=expected["work_order_id"],
        foundup_scope=(expected["foundup_id"],),
        source_scope=expected["source_scope"],
        sensitivity_classes=tuple(sensitivity_classes),
        allowed_record_sections=tuple(allowed_record_sections) or (
            "identity",
            "current_state",
            "roadmap_state",
            "verified_outcome",
        ),
        denied_record_sections=tuple(denied_record_sections),
        max_records=max_records,
        issued_at=expected["issued_at"],
        expires_at=expected["expires_at"],
        policy_generation_id=f"{expected['holoindex_generation_id']}:memex-policy",
    )
    if not policy.accepted or policy.receipt is None:
        return _reject(
            *("access_policy:" + reason for reason in policy.rejection_reasons)
        )

    projection = project_foundup_memex_to_holoindex_shadow(
        memex_view=memex_view,
        source_scope=expected["source_scope"],
        source_revision=expected["source_revision"],
        allowed_foundup_ids=(expected["foundup_id"],),
        access_policy_receipt=policy.receipt,
        holoindex_generation_id=expected["holoindex_generation_id"],
        now_iso=expected["issued_at"],
    )
    if not projection.accepted or projection.receipt is None:
        return _reject(*("projection:" + reason for reason in projection.rejection_reasons))

    gate = verify_and_rehydrate_memex_projection(
        projection,
        runtime_mode=True,
        now_iso=expected["issued_at"],
        expected_foundup_id=expected["foundup_id"],
        expected_source_scope=expected["source_scope"],
        expected_source_revision=expected["source_revision"],
        expected_access_policy_digest=policy.receipt.receipt_id,
        expected_holoindex_generation_id=expected["holoindex_generation_id"],
        expected_operational_snapshot_id=expected["snapshot_receipt_id"],
        expected_operational_snapshot_content_digest=expected["snapshot_content_digest"],
    )
    if not gate.accepted:
        return _reject(*("integrity:" + reason for reason in gate.rejection_reasons))

    return MemexSnapshotProjectionSupplyResult(
        accepted=True,
        status=SUPPLIER_ACCEPTED,
        projection=projection,
        access_policy_receipt=policy.receipt,
        rejection_reasons=(),
    )


def _reject(*reasons: str) -> MemexSnapshotProjectionSupplyResult:
    return MemexSnapshotProjectionSupplyResult(
        accepted=False,
        status=SUPPLIER_REJECTED,
        projection=None,
        access_policy_receipt=None,
        rejection_reasons=tuple(dict.fromkeys(reason for reason in reasons if reason)),
    )


def _clean(value: Any) -> str:
    return str(value or "").strip()


__all__ = [
    "MemexSnapshotProjectionSupplyResult",
    "SUPPLIER_ACCEPTED",
    "SUPPLIER_REJECTED",
    "supply_assignment_bound_memex_projection",
]
