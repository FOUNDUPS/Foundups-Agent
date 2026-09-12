import pytest

from modules.foundups.esingularity.src.yumori_capacity_allocation import (
    audit_gpu_capacity,
    require_committed_capacity_valid,
)
from modules.foundups.esingularity.src.yumori_feasibility_finance import (
    CustomerOfftake,
    EvidenceStatus,
)


def test_requested_demand_is_not_reserved_capacity():
    record = CustomerOfftake(
        organization="University A",
        customer_type="university",
        product="gpu_academic",
        requested_gpus=96,
        reserved_capacity_gpus=0,
        evidence_status=EvidenceStatus.POTENTIAL,
    )
    result = audit_gpu_capacity(384, [record])
    assert result.requested_gpu_demand == 96
    assert result.committed_reserved_gpus == 0
    assert result.potential_reserved_gpus == 0
    assert result.committed_headroom_gpus == 384


def test_committed_and_pipeline_reservations_remain_separate():
    committed = CustomerOfftake(
        organization="Enterprise A",
        customer_type="enterprise",
        product="gpu_reserved",
        requested_gpus=128,
        reserved_capacity_gpus=128,
        evidence_status=EvidenceStatus.COMMITTED,
    )
    pipeline = CustomerOfftake(
        organization="University B",
        customer_type="university",
        product="gpu_academic",
        requested_gpus=96,
        reserved_capacity_gpus=64,
        evidence_status=EvidenceStatus.POTENTIAL,
    )
    result = audit_gpu_capacity(384, [committed, pipeline])
    assert result.requested_gpu_demand == 224
    assert result.committed_reserved_gpus == 128
    assert result.potential_reserved_gpus == 64
    assert result.committed_headroom_gpus == 256
    assert result.pipeline_headroom_gpus == 192
    assert result.committed_utilization_pct == pytest.approx(128 / 384)
    assert result.pipeline_utilization_pct == pytest.approx(192 / 384)


def test_pipeline_may_exceed_capacity_but_overbooking_is_explicit():
    committed = CustomerOfftake(
        organization="Enterprise A",
        customer_type="enterprise",
        product="gpu_reserved",
        reserved_capacity_gpus=256,
        evidence_status=EvidenceStatus.VERIFIED,
    )
    potential = CustomerOfftake(
        organization="Pipeline B",
        customer_type="enterprise",
        product="gpu_burst",
        reserved_capacity_gpus=256,
        evidence_status=EvidenceStatus.POTENTIAL,
    )
    result = audit_gpu_capacity(384, [committed, potential])
    assert result.committed_capacity_valid is True
    assert result.committed_overbooked_gpus == 0
    assert result.pipeline_overbooked_gpus == 128
    assert result.pipeline_headroom_gpus == 0


def test_committed_reservations_cannot_exceed_physical_gpu_pool():
    records = [
        CustomerOfftake(
            organization="Enterprise A",
            customer_type="enterprise",
            product="gpu_reserved",
            reserved_capacity_gpus=256,
            evidence_status=EvidenceStatus.COMMITTED,
        ),
        CustomerOfftake(
            organization="University A",
            customer_type="university",
            product="gpu_academic",
            reserved_capacity_gpus=160,
            evidence_status=EvidenceStatus.VERIFIED,
        ),
    ]
    audit = audit_gpu_capacity(384, records)
    assert audit.committed_capacity_valid is False
    assert audit.committed_overbooked_gpus == 32
    with pytest.raises(ValueError, match="exceed physical capacity by 32 GPUs"):
        require_committed_capacity_valid(384, records)


def test_zero_or_negative_physical_capacity_fails_closed():
    with pytest.raises(ValueError, match="must be positive"):
        audit_gpu_capacity(0, [])
