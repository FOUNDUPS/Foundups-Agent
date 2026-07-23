# -*- coding: utf-8 -*-
"""Bounded consumer admission seam for FoundUp model capability projections."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, Protocol

from .foundup_job_model_capability_projection import (
    FoundUpJobModelCapabilityProjection,
    get_foundup_job_model_capability_profile,
    resolve_foundup_job_model_capability_projection,
)
from .foundup_job_router import RouteStatus
from .foundup_job_validate_snapshot import freeze_validate_foundup_job


@dataclass(frozen=True)
class ModelRuntimeBindingLookup:
    """Immutable identity passed to the trusted persisted-artifact boundary."""

    job_id: str
    tenant_id: str
    foundup_id: Optional[str]
    requested_action: str
    profile_id: str
    runtime_surface: Optional[str]
    task_family: Optional[str]


@dataclass(frozen=True)
class TrustedModelRuntimeBindingArtifact:
    """Artifact and provenance returned by a confined trusted resolver."""

    artifact: Any
    artifact_digest: Any
    provenance: str


class TrustedModelRuntimeBindingResolver(Protocol):
    """Injected trust anchor; implementations resolve persisted artifacts."""

    def __call__(
        self,
        lookup: ModelRuntimeBindingLookup,
    ) -> Optional[TrustedModelRuntimeBindingArtifact]: ...


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


def no_trusted_model_runtime_binding(
    lookup: ModelRuntimeBindingLookup,
) -> Optional[TrustedModelRuntimeBindingArtifact]:
    """Default trust boundary: no persisted artifact is available."""
    del lookup
    return None


def prepare_validate_model_capability_admission(
    *,
    job: Any,
    route_envelope: Any,
    dry_run_mode: bool,
    binding_resolver: TrustedModelRuntimeBindingResolver,
) -> tuple[Any, ModelCapabilityConsumerAdmission]:
    """Freeze validate input, then resolve only trusted artifact supply."""
    action = getattr(job, "requested_action", None)
    if (
        action != "validate_foundup"
        or get_foundup_job_model_capability_profile(action) is None
    ):
        return job, ModelCapabilityConsumerAdmission(None, False, "")
    execution_job = freeze_validate_foundup_job(job)
    if execution_job is None:
        admission = _resolve_admission(
            job,
            route_envelope,
            dry_run_mode,
            object(),
            "invalid",
        )
        return None, admission
    profile = get_foundup_job_model_capability_profile(action)
    lookup = ModelRuntimeBindingLookup(
        job_id=execution_job.job_id,
        tenant_id=execution_job.tenant_id,
        foundup_id=execution_job.foundup_id,
        requested_action=action,
        profile_id=profile.profile_id,
        runtime_surface=profile.runtime_surface,
        task_family=profile.task_family,
    )
    receipt, digest = _trusted_binding(binding_resolver, lookup)
    return execution_job, _resolve_admission(
        execution_job,
        route_envelope,
        dry_run_mode,
        receipt,
        digest,
    )


def _resolve_admission(
    job: Any,
    route_envelope: Any,
    dry_run_mode: bool,
    receipt: Any,
    digest: Any,
) -> ModelCapabilityConsumerAdmission:
    projection = resolve_foundup_job_model_capability_projection(
        job=job,
        route_envelope=route_envelope,
        dry_run_mode=dry_run_mode,
        model_runtime_binding_receipt=receipt,
        model_runtime_binding_digest=digest,
    )
    reasons = projection.rejection_reasons
    reason = reasons[0] if reasons else ""
    return ModelCapabilityConsumerAdmission(
        projection=projection,
        blocked=projection.decision == "rejected",
        reason=reason,
    )


def _trusted_binding(
    resolver: TrustedModelRuntimeBindingResolver,
    lookup: ModelRuntimeBindingLookup,
) -> tuple[Any, Any]:
    try:
        supply = resolver(lookup)
        if supply is None:
            return None, None
        if (
            type(supply) is not TrustedModelRuntimeBindingArtifact
            or type(supply.provenance) is not str
            or not supply.provenance
            or supply.artifact is None
            or supply.artifact_digest is None
        ):
            return object(), "invalid"
        return supply.artifact, supply.artifact_digest
    except Exception:
        return object(), "invalid"


def attach_model_capability_projection(
    result: Any,
    admission: ModelCapabilityConsumerAdmission,
) -> Any:
    """Attach a detached projection without changing the existing result path."""
    if admission.projection is not None:
        result.model_capability_projection = admission.projection.to_dict()
    return result


__all__ = [
    "ModelRuntimeBindingLookup",
    "ModelCapabilityConsumerAdmission",
    "TrustedModelRuntimeBindingArtifact",
    "TrustedModelRuntimeBindingResolver",
    "attach_model_capability_projection",
    "no_trusted_model_runtime_binding",
    "prepare_validate_model_capability_admission",
]
