# -*- coding: utf-8 -*-
"""Bounded consumer admission seam for FoundUp model capability projections."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Optional

from .foundup_job_model_capability_projection import (
    FoundUpJobModelCapabilityProjection,
    get_foundup_job_model_capability_profile,
    resolve_foundup_job_model_capability_projection,
)
from .foundup_job_router import RouteStatus


@dataclass(frozen=True)
class ModelCapabilityConsumerAdmission:
    """Projection plus its non-authoritative dispatch admission outcome."""

    projection: Optional[FoundUpJobModelCapabilityProjection]
    blocked: bool
    reason: str

    def rejection_result_fields(
        self,
        job_id: str,
        route_envelope: Any,
    ) -> dict[str, Any]:
        """Return the stable blocked-result fields for rejected admission."""
        return {
            "job_id": job_id,
            "dispatched": False,
            "route_status": RouteStatus.BLOCKED,
            "target_backend": route_envelope.target_backend,
            "reason": f"Model capability projection rejected: {self.reason}",
            "envelope": route_envelope,
            "checkpoint_state": "BLOCKED",
            "checkpoint_blocker": self.reason,
            "model_capability_projection": self.projection.to_dict(),
        }


def resolve_model_capability_consumer_admission(
    *,
    job: Any,
    route_envelope: Any,
    dry_run_mode: bool,
) -> ModelCapabilityConsumerAdmission:
    """Resolve projection and block only explicit projection rejection."""
    action = getattr(job, "requested_action", None)
    if (
        action != "validate_foundup"
        or get_foundup_job_model_capability_profile(action) is None
    ):
        return ModelCapabilityConsumerAdmission(None, False, "")
    payload = getattr(job, "payload", None)
    payload = payload if isinstance(payload, Mapping) else {}
    projection = resolve_foundup_job_model_capability_projection(
        job=job,
        route_envelope=route_envelope,
        dry_run_mode=dry_run_mode,
        model_runtime_binding_receipt=payload.get(
            "model_runtime_binding_receipt"
        ),
        model_runtime_binding_digest=payload.get(
            "model_runtime_binding_digest"
        ),
    )
    reasons = projection.rejection_reasons
    reason = reasons[0] if reasons else ""
    return ModelCapabilityConsumerAdmission(
        projection=projection,
        blocked=projection.decision == "rejected",
        reason=reason,
    )


def attach_model_capability_projection(
    result: Any,
    admission: ModelCapabilityConsumerAdmission,
) -> Any:
    """Attach a detached projection without changing the existing result path."""
    if admission.projection is not None:
        result.model_capability_projection = admission.projection.to_dict()
    return result


__all__ = [
    "ModelCapabilityConsumerAdmission",
    "attach_model_capability_projection",
    "resolve_model_capability_consumer_admission",
]
