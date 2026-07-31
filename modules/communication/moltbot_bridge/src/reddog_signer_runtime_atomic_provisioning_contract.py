"""Typed contracts for atomic signer-runtime provisioning."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from modules.communication.moltbot_bridge.src.reddog_ed25519_signature_verifier_backend import (
    Ed25519SignatureVerifier,
    decode_ed25519_public_key,
)
from modules.communication.moltbot_bridge.src.reddog_signed_runtime_artifact_manifest import (
    RuntimeArtifactManifestSigningContext,
)
from modules.communication.moltbot_bridge.src.reddog_signer_delegated_authority_runtime import (
    IsolatedSignerClient,
)
from modules.communication.moltbot_bridge.src.reddog_runtime_artifact_manifest_authority import (
    RuntimeArtifactManifestAuthority,
    RuntimeArtifactManifestAuthorityBoundary,
)
from modules.communication.moltbot_bridge.src.reddog_signer_runtime_generation_anchor import (
    DurableSignerRuntimeGenerationAnchor,
)


@dataclass(frozen=True)
class SignerRuntimeAtomicProvisioningContext:
    """Authenticated dependencies for one generation activation."""

    signer: IsolatedSignerClient
    authority: RuntimeArtifactManifestAuthority
    authority_boundary: RuntimeArtifactManifestAuthorityBoundary
    authority_tier: str
    generation_anchor: DurableSignerRuntimeGenerationAnchor

    def require_signing_context(self) -> RuntimeArtifactManifestSigningContext:
        values = self.authority_boundary.require(self.authority)
        if (
            not callable(getattr(self.signer, "sign", None))
            or decode_ed25519_public_key(
                str(values.get("signer_public_key") or "")
            )
            is None
            or not str(values.get("key_epoch") or "")
        ):
            raise ValueError("signer_runtime_signing_identity_invalid")
        return RuntimeArtifactManifestSigningContext(
            signer=self.signer,
            signature_verifier=Ed25519SignatureVerifier(),
            authority=self.authority,
            authority_boundary=self.authority_boundary,
            authority_tier=self.authority_tier,
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

    if not isinstance(manifest_signing, RuntimeArtifactManifestSigningContext):
        raise ValueError("signer_runtime_signing_context_invalid")
    return SignerRuntimeAtomicProvisioningContext(
        signer=manifest_signing.signer,
        authority=manifest_signing.authority,
        authority_boundary=manifest_signing.authority_boundary,
        authority_tier=manifest_signing.authority_tier,
        generation_anchor=generation_anchor,
    )


__all__ = [
    "SignerRuntimeAtomicProvisioningContext",
    "SignerRuntimeAtomicProvisioningResult",
    "create_signer_runtime_atomic_provisioning_context",
]
