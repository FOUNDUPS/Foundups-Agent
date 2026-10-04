"""WSP 71 key-provider factory for one resolve-per-sign call."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

from modules.communication.moltbot_bridge.src.reddog_ed25519_signer_backend import (
    ControlLoopAuthorityPolicy,
)
from modules.communication.moltbot_bridge.src.reddog_signer_control_loop_anchor import (
    ControlLoopAnchorStore,
)
from modules.communication.moltbot_bridge.src.reddog_signer_key_provider_dryrun import (
    PROVIDER_MODE_WSP71_PERMISSIONED,
    SignerKeyProviderDryRunResult,
    SignerKeyProviderProfile,
    SignerKeyResolver,
    _provider_mode_authorized,
    build_signer_backend_from_provider,
)
from modules.communication.moltbot_bridge.src.reddog_signer_owner_e0_policy_contract import (
    signer_key_reference_digest,
)
from modules.communication.moltbot_bridge.src.reddog_signer_mutual_peer_handshake import (
    SignerPeerInstanceBinding,
)
from modules.communication.moltbot_bridge.src.reddog_signer_secret_grant_authority_policy import (
    SignerSecretGrantAuthorityPolicy,
)
from modules.communication.moltbot_bridge.src.reddog_signer_secret_grant_durable_rate_authority import (
    DurableSignerSecretGrantRateAuthority,
)
from modules.infrastructure.secrets_mcp.src.vault_resolver import (
    ResolveErrorCode,
    ResolveResult,
    hash_reference,
)


@dataclass(frozen=True)
class _GrantReferenceResolver:
    """Bind resolution metadata to full E0 digests without changing audit logs."""

    resolver: SignerKeyResolver

    def resolve(self, reference: str, requester_id: str | None = None) -> ResolveResult:
        result = self.resolver.resolve(reference, requester_id=requester_id)
        if not isinstance(result, ResolveResult) or result.success is False:
            return result
        audit_digest = hash_reference(reference)
        full_digest = signer_key_reference_digest(reference)
        if (
            result.success is not True
            or type(result.reference) is not str
            or result.reference != reference
            or type(result.reference_hash) is not str
            or result.reference_hash not in (audit_digest, full_digest)
        ):
            return ResolveResult(
                success=False,
                reference=reference,
                reference_hash=audit_digest,
                error_code=ResolveErrorCode.INVALID_REFERENCE,
            )
        return replace(result, reference_hash=full_digest)


@dataclass(frozen=True)
class Wsp71EphemeralSignerBackendFactory:
    """Resolve current signer material afresh for each factory call."""

    profile: SignerKeyProviderProfile
    resolver: SignerKeyResolver
    control_loop_anchor_store: ControlLoopAnchorStore | None = None
    control_loop_authority_policy: ControlLoopAuthorityPolicy | None = None
    secret_grant_authority_policy: SignerSecretGrantAuthorityPolicy | None = None
    secret_grant_rate_authority: DurableSignerSecretGrantRateAuthority | None = None
    elevated_consensus_signer_authority: Any | None = None
    signer_peer_instance_binding: SignerPeerInstanceBinding | None = None

    @property
    def signer_agent_id(self) -> str:
        return self.profile.signer_agent_id

    @property
    def permission_snapshot_digest(self) -> str:
        return self.profile.permission_snapshot_digest

    def __call__(self) -> SignerKeyProviderDryRunResult:
        resolver = self.resolver
        # Check the original resolver before an adapter could hide mock identity.
        if _provider_mode_authorized(
            PROVIDER_MODE_WSP71_PERMISSIONED,
            allow_test_only_key_material=False,
            resolver=resolver,
        ):
            resolver = _GrantReferenceResolver(resolver)
        result = build_signer_backend_from_provider(
            self.profile,
            resolver,
            provider_mode=PROVIDER_MODE_WSP71_PERMISSIONED,
            allow_test_only_key_material=False,
            permission_snapshot_fresh=True,
            control_loop_anchor_store=self.control_loop_anchor_store,
            control_loop_authority_policy=self.control_loop_authority_policy,
        )
        if not result.ok or result.backend is None:
            return result
        backend = replace(
            result.backend,
            secret_grant_authority_policy=self.secret_grant_authority_policy,
            secret_grant_rate_authority=self.secret_grant_rate_authority,
            elevated_consensus_signer_authority=(
                self.elevated_consensus_signer_authority
            ),
            signer_peer_instance_binding=self.signer_peer_instance_binding,
        )
        return replace(result, backend=backend)


__all__ = ["Wsp71EphemeralSignerBackendFactory"]
