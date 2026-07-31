"""Typed contracts for atomic signer-runtime provisioning."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from modules.communication.moltbot_bridge.src.reddog_signer_runtime_provisioning_signing_boundary import (
    SignerRuntimeProvisioningSigningBoundary,
    create_signer_runtime_provisioning_signing_boundary,
    require_signer_runtime_provisioning_signing_context,
)
from modules.communication.moltbot_bridge.src.reddog_signed_runtime_artifact_manifest import (
    RuntimeArtifactManifestSigningContext,
)
from modules.communication.moltbot_bridge.src.reddog_signer_runtime_generation_anchor import (
    DurableSignerRuntimeGenerationAnchor,
)


@dataclass(frozen=True)
class SignerRuntimeAtomicProvisioningContext:
    """Authenticated dependencies for one generation activation."""

    signing_authority: object
    signing_authority_boundary: SignerRuntimeProvisioningSigningBoundary
    generation_anchor: DurableSignerRuntimeGenerationAnchor

    def require_signing_context(self) -> RuntimeArtifactManifestSigningContext:
        return require_signer_runtime_provisioning_signing_context(
            self.signing_authority_boundary,
            self.signing_authority,
        )


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


def create_signer_runtime_atomic_provisioning_context(
    *,
    manifest_signing: RuntimeArtifactManifestSigningContext,
    generation_anchor: DurableSignerRuntimeGenerationAnchor,
) -> SignerRuntimeAtomicProvisioningContext:
    """Issue the only accepted process-local atomic provisioning context."""

    boundary, capability = (
        create_signer_runtime_provisioning_signing_boundary(manifest_signing)
    )
    return SignerRuntimeAtomicProvisioningContext(
        signing_authority=capability,
        signing_authority_boundary=boundary,
        generation_anchor=generation_anchor,
    )


__all__ = [
    "SignerRuntimeAtomicProvisioningContext",
    "SignerRuntimeAtomicProvisioningResult",
    "create_signer_runtime_atomic_provisioning_context",
]
