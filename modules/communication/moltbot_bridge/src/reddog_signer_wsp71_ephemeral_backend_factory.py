"""WSP 71 key-provider factory for one resolve-per-sign call."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import asdict, dataclass, field, replace
from threading import RLock
import time
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


from .reddog_signer_proposal_activation import (
    _LEASED_PROPOSAL_OWNER, _ProposalLeaseScope, _owner_ephemeral_binding,
    _verified_proposal_inputs, _build_leased_proposal, deferred_proposal_activation_matches,
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
    owner_context: tuple[Any, Any, Any] | None = None
    proposal_replay_high_water_store: Any | None = None
    _activation_digest: str | None = field(default=None, init=False, repr=False, compare=False)
    _activation_lock: Any = field(default_factory=RLock, init=False, repr=False, compare=False)

    @contextmanager
    def signing_authority_lease(self):
        """Recheck owner state only inside the root protected-use callback."""
        if self.owner_context is None:
            raise ValueError("signer_grant_owner_context_required")
        from modules.communication.moltbot_bridge.src.reddog_signer_socket_service_bootstrap_admission import lease_signer_socket_service_grant_admission
        config, admission, expected = self.owner_context
        with lease_signer_socket_service_grant_admission(config, admission) as (current, owner):
            profile, binding = _owner_ephemeral_binding(current, admission, owner)
            if profile != self.profile or binding != expected:
                raise ValueError("signer_grant_current_owner_mismatch")
            with self._activation_lock:
                scope = _ProposalLeaseScope(self, current, owner)
                token = _LEASED_PROPOSAL_OWNER.set(scope)
                try:
                    yield binding
                finally:
                    scope.active = False
                    _LEASED_PROPOSAL_OWNER.reset(token)

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
        if self.owner_context is not None and self.owner_context[0].proposal_authority_policy is not None:
            result = _build_leased_proposal(self, resolver)
        else:
            result = build_signer_backend_from_provider(
                self.profile, resolver, provider_mode=PROVIDER_MODE_WSP71_PERMISSIONED,
                allow_test_only_key_material=False, permission_snapshot_fresh=True,
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


@contextmanager
def _lease_authenticated_factory(factory: Any, expected_binding: Any, boundary: Any):
    """Require a real owner lease matching the consuming backend's binding."""
    from modules.communication.moltbot_bridge.src.reddog_signer_resolve_per_sign_backend import ResolvePerSignBinding
    from modules.communication.moltbot_bridge.src.reddog_signer_secret_access_grant import SignerSecretAccessGrantBoundary
    if type(factory) is not Wsp71EphemeralSignerBackendFactory:
        raise ValueError("signer_grant_factory_unverified")
    with Wsp71EphemeralSignerBackendFactory.signing_authority_lease(factory) as binding:
        if not (type(binding) is type(expected_binding) is ResolvePerSignBinding
                and binding == expected_binding and type(boundary) is SignerSecretAccessGrantBoundary
                and boundary._nonce_store is factory.owner_context[1].replay_store
                and boundary._revocation_oracle is factory.owner_context[1].revocation_oracle):
            raise ValueError("signer_grant_current_owner_mismatch")
        yield
def build_owner_leased_ephemeral_backend(
    config: Any, resolver: SignerKeyResolver, admission: Any, owner: Any,
    *, control_loop_anchor_store: ControlLoopAnchorStore | None,
    control_loop_authority_policy: ControlLoopAuthorityPolicy | None,
    proposal_replay_high_water_store: Any | None = None,
) -> Any:
    """Compose existing one-use owners without resolving any signing material."""
    from modules.communication.moltbot_bridge.src.reddog_ed25519_signature_verifier_backend import Ed25519SignatureVerifier
    from modules.communication.moltbot_bridge.src.reddog_signer_secret_access_grant import SignerSecretAccessGrantBoundary
    from modules.communication.moltbot_bridge.src.reddog_signer_resolve_per_sign_backend import ResolvePerSignSignerBackend
    profile, binding = _owner_ephemeral_binding(config, admission, owner)
    if config.proposal_authority_policy is not None:
        _verified_proposal_inputs(config, owner, proposal_replay_high_water_store)
    factory = Wsp71EphemeralSignerBackendFactory(
        profile, resolver, control_loop_anchor_store=control_loop_anchor_store,
        control_loop_authority_policy=control_loop_authority_policy,
        signer_peer_instance_binding=config.signer_peer_instance_binding,
        owner_context=(config, admission, binding),
        proposal_replay_high_water_store=proposal_replay_high_water_store,
    )
    return ResolvePerSignSignerBackend(
        binding, SignerSecretAccessGrantBoundary(
            nonce_store=admission.replay_store, revocation_oracle=admission.revocation_oracle,
            clock=lambda: int(time.time()),
        ), Ed25519SignatureVerifier(), owner.resolver, factory,
    )


__all__ = ["Wsp71EphemeralSignerBackendFactory", "build_owner_leased_ephemeral_backend"]
