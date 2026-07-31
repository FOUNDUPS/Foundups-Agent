"""Typed contracts for atomic signer-runtime provisioning."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from modules.communication.moltbot_bridge.src.reddog_signed_runtime_artifact_manifest import (
    RuntimeArtifactManifestSigningContext,
)
from modules.communication.moltbot_bridge.src.reddog_signer_runtime_generation_anchor import (
    DurableSignerRuntimeGenerationAnchor,
)


@dataclass(frozen=True)
class SignerRuntimeAtomicProvisioningContext:
    """Authenticated dependencies for one generation activation."""

    manifest_signing: RuntimeArtifactManifestSigningContext
    generation_anchor: DurableSignerRuntimeGenerationAnchor


@dataclass(frozen=True)
class SignerRuntimeAtomicProvisioningResult:
    """Evidence from manifest publication and last-step activation."""

    accepted: bool
    manifest_path: str | None
    manifest_id: str | None
    generation: int | None
    activation_revision: str | None
    rejection_reasons: tuple[str, ...]
    inactive_artifacts_preserved: bool
    recovered_existing_activation: bool
    no_service_start_performed_by_coordinator: bool = True
    no_work_execution_performed_by_coordinator: bool = True
    no_repo_mutation_performed_by_coordinator: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


__all__ = [
    "SignerRuntimeAtomicProvisioningContext",
    "SignerRuntimeAtomicProvisioningResult",
]
