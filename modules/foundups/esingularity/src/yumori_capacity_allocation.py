"""Physical GPU-capacity allocation guard for YUMORI feasibility evidence.

The financial model may expose many commercial products from one GPU fleet, but
customer demand must not create multiple copies of the same physical inventory.
This module audits explicit customer/offtake records against a fixed GPU pool.

Important boundaries:
- ``requested_gpus`` is demand evidence, not a reservation.
- ``reserved_capacity_gpus`` is the only field counted as reserved inventory.
- VERIFIED/COMMITTED reservations consume hard capacity.
- POTENTIAL/MODEL ONLY reservations are pipeline and remain separate.
- this audit does not create revenue or construction funding.

WSP: 3, 50, 84, 95, 97, 109.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable, Tuple

from .yumori_feasibility_finance import CustomerOfftake, EvidenceStatus

_COMMITTED = {EvidenceStatus.VERIFIED, EvidenceStatus.COMMITTED}


@dataclass(frozen=True)
class CapacityReservationRow:
    organization: str
    product: str
    evidence_status: str
    requested_gpus: int
    reserved_gpus: int
    reservation_class: str


@dataclass(frozen=True)
class CapacityAllocationResult:
    total_gpu_capacity: int
    requested_gpu_demand: int
    committed_reserved_gpus: int
    potential_reserved_gpus: int
    committed_headroom_gpus: int
    pipeline_headroom_gpus: int
    committed_utilization_pct: float
    pipeline_utilization_pct: float
    committed_overbooked_gpus: int
    pipeline_overbooked_gpus: int
    committed_capacity_valid: bool
    rows: Tuple[CapacityReservationRow, ...]

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def audit_gpu_capacity(
    total_gpu_capacity: int,
    records: Iterable[CustomerOfftake],
) -> CapacityAllocationResult:
    """Audit explicit reservations against one physical GPU inventory.

    Committed reservations are a hard gate. Potential/model-only reservations are
    allowed to exceed remaining capacity because they are pipeline, but the
    resulting overbooking is surfaced rather than hidden.
    """
    if total_gpu_capacity <= 0:
        raise ValueError("total_gpu_capacity must be positive")

    requested = committed = potential = 0
    rows = []
    for record in records:
        if record.requested_gpus < 0 or record.reserved_capacity_gpus < 0:
            raise ValueError("Customer GPU demand/reservation cannot be negative")
        requested += record.requested_gpus
        if record.evidence_status in _COMMITTED:
            committed += record.reserved_capacity_gpus
            reservation_class = "COMMITTED_CAPACITY"
        else:
            potential += record.reserved_capacity_gpus
            reservation_class = "PIPELINE_CAPACITY"
        rows.append(
            CapacityReservationRow(
                organization=record.organization,
                product=record.product,
                evidence_status=record.evidence_status.value,
                requested_gpus=record.requested_gpus,
                reserved_gpus=record.reserved_capacity_gpus,
                reservation_class=reservation_class,
            )
        )

    committed_overbooked = max(0, committed - total_gpu_capacity)
    committed_headroom = max(0, total_gpu_capacity - committed)
    combined_reserved = committed + potential
    pipeline_overbooked = max(0, combined_reserved - total_gpu_capacity)
    pipeline_headroom = max(0, total_gpu_capacity - combined_reserved)

    return CapacityAllocationResult(
        total_gpu_capacity=total_gpu_capacity,
        requested_gpu_demand=requested,
        committed_reserved_gpus=committed,
        potential_reserved_gpus=potential,
        committed_headroom_gpus=committed_headroom,
        pipeline_headroom_gpus=pipeline_headroom,
        committed_utilization_pct=committed / total_gpu_capacity,
        pipeline_utilization_pct=combined_reserved / total_gpu_capacity,
        committed_overbooked_gpus=committed_overbooked,
        pipeline_overbooked_gpus=pipeline_overbooked,
        committed_capacity_valid=committed_overbooked == 0,
        rows=tuple(rows),
    )


def require_committed_capacity_valid(
    total_gpu_capacity: int,
    records: Iterable[CustomerOfftake],
) -> CapacityAllocationResult:
    """Fail closed when signed/verified reservations exceed physical capacity."""
    result = audit_gpu_capacity(total_gpu_capacity, records)
    if not result.committed_capacity_valid:
        raise ValueError(
            "Committed GPU reservations exceed physical capacity by "
            f"{result.committed_overbooked_gpus} GPUs"
        )
    return result
