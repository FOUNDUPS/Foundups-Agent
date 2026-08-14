"""Typed contracts for atomic signer-runtime provisioning."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterator, Mapping

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
from modules.communication.moltbot_bridge.src.reddog_grant_authority_service_owner_binding import (
    grant_authority_owner_operation_fence,
    require_grant_authority_provisioning_binding,
)
from modules.communication.moltbot_bridge.src.reddog_grant_authority_source_policy_authority import (
    load_grant_authority_source_policy_authority,
)
from modules.communication.moltbot_bridge.src.reddog_runtime_artifact_manifest_contract import (
    RUNTIME_PROFILE_GRANT_AUTHORITY_SERVICE_GIT_PROVENANCE,
    RuntimeArtifactManifestError,
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
    runtime_profile: str | None = None
    owner_config_path: str | None = None

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

    @contextmanager
    def source_policy_fence(self) -> Iterator[None]:
        """Hold the root-owner fence for one complete grant activation."""

        if self.runtime_profile is None:
            if self.owner_config_path is not None:
                raise RuntimeArtifactManifestError(
                    "grant_source_policy_context_invalid"
                )
            yield
            return
        values = self.authority_boundary.require(self.authority)
        with grant_authority_owner_operation_fence(
            self._owner_path(), repo_root=Path(values["repo_root"])
        ):
            self.revalidate_source_policy()
            yield

    def revalidate_source_policy(
        self, manifest: Mapping[str, Any] | None = None
    ) -> Mapping[str, Any] | None:
        """Revalidate current owner and exact grant artifact lineage."""

        if self.runtime_profile is None:
            return None
        if (
            self.runtime_profile
            != RUNTIME_PROFILE_GRANT_AUTHORITY_SERVICE_GIT_PROVENANCE
        ):
            raise RuntimeArtifactManifestError(
                "grant_source_policy_context_invalid"
            )
        runtime = self.authority_boundary.require(self.authority)
        source_authority, source_boundary = (
            load_grant_authority_source_policy_authority(
                owner_config_path=self._owner_path(),
                repo_root=runtime["repo_root"],
            )
        )
        policy = source_boundary.revalidate(source_authority)
        require_grant_authority_provisioning_binding(
            owner_config_path=self._owner_path(),
            repo_root=runtime["repo_root"],
            runtime_root=runtime["runtime_root"],
            source_policy=policy,
            manifest_authority=self.authority,
            manifest_boundary=self.authority_boundary,
            manifest=manifest,
        )
        return policy

    def _owner_path(self) -> Path:
        if not self.owner_config_path:
            raise RuntimeArtifactManifestError(
                "grant_source_policy_owner_path_missing"
            )
        return Path(self.owner_config_path).resolve()


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


def create_grant_runtime_atomic_provisioning_context(
    *, manifest_signing: RuntimeArtifactManifestSigningContext,
    generation_anchor: DurableSignerRuntimeGenerationAnchor,
    owner_config_path: Path | str,
) -> SignerRuntimeAtomicProvisioningContext:
    """Issue a grant-v3 context without caller-selected profile authority."""

    base = create_signer_runtime_atomic_provisioning_context(
        manifest_signing=manifest_signing,
        generation_anchor=generation_anchor,
    )
    context = SignerRuntimeAtomicProvisioningContext(
        signer=base.signer,
        authority=base.authority,
        authority_boundary=base.authority_boundary,
        authority_tier=base.authority_tier,
        generation_anchor=base.generation_anchor,
        runtime_profile=(
            RUNTIME_PROFILE_GRANT_AUTHORITY_SERVICE_GIT_PROVENANCE
        ),
        owner_config_path=str(Path(owner_config_path).resolve()),
    )
    context.revalidate_source_policy()
    return context


__all__ = [
    "SignerRuntimeAtomicProvisioningContext",
    "SignerRuntimeAtomicProvisioningResult",
    "create_grant_runtime_atomic_provisioning_context",
    "create_signer_runtime_atomic_provisioning_context",
]
