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
    build_signer_backend_from_provider,
)
from modules.communication.moltbot_bridge.src.reddog_signer_secret_grant_authority_policy import (
    SignerSecretGrantAuthorityPolicy,
)
from modules.communication.moltbot_bridge.src.reddog_signer_secret_grant_durable_rate_authority import (
    DurableSignerSecretGrantRateAuthority,
)


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

    @property
    def signer_agent_id(self) -> str:
        return self.profile.signer_agent_id

    @property
    def permission_snapshot_digest(self) -> str:
        return self.profile.permission_snapshot_digest

    def __call__(self) -> SignerKeyProviderDryRunResult:
        result = build_signer_backend_from_provider(
            self.profile,
            self.resolver,
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
        )
        return replace(result, backend=backend)


__all__ = ["Wsp71EphemeralSignerBackendFactory"]
