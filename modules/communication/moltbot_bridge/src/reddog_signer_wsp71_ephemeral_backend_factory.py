"""WSP 71 key-provider factory for one resolve-per-sign call."""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import asdict, dataclass, field, replace
import hashlib
import json
from threading import RLock, get_ident
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


_LEASED_PROPOSAL_OWNER = ContextVar("leased_proposal_owner", default=None)


@dataclass
class _ProposalLeaseScope:
    factory: Any
    config: Any
    owner: Any
    active: bool = True
    thread_id: int = field(default_factory=get_ident)
    last_epoch: int | None = None

    def require_current(self):
        if not self.active or self.thread_id != get_ident() or _LEASED_PROPOSAL_OWNER.get() is not self:
            raise ValueError("signer_grant_proposal_owner_lease_required")
        now = int(time.time())
        if self.last_epoch is not None and now < self.last_epoch:
            raise ValueError("signer_grant_proposal_lease_clock_reversed")
        self.last_epoch = now
        return now


@dataclass(frozen=True)
class _LeasedProposalKey:
    key: Any
    scope: _ProposalLeaseScope
    expected: Any

    def public_key(self):
        return self.key.public_key()

    def sign(self, data):
        self._require_authority()
        signature = self.key.sign(data)
        self._require_authority()
        return signature

    def _require_authority(self):
        self.scope.require_current()
        current = _verified_proposal_inputs(self.scope.config, self.scope.owner,
                                           self.scope.factory.proposal_replay_high_water_store,
                                           clock=self.scope.require_current)
        finished = self.scope.require_current()
        if current != self.expected or finished >= min(current[0].expected_payload.expires_at, current[1].expires_at):
            raise ValueError("signer_grant_proposal_authority_changed")


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


def _owner_ephemeral_binding(config: Any, admission: Any, owner: Any):
    from pathlib import Path
    from modules.communication.moltbot_bridge.src.reddog_signer_owner_e0_admission_validation import require_policy_config_binding
    from modules.communication.moltbot_bridge.src.reddog_signer_independent_secret_grant_binding import resolve_secret_grant_target_binding, require_owner_bound_replay_store
    from modules.communication.moltbot_bridge.src.reddog_signer_secret_grant_root_protected_use_oracle import RootAuthorizedSignerGrantRevocationOracle

    profiles = tuple(config.key_provider_profiles) or (config.key_provider_profile,)
    if len(profiles) != 1 or any(value is not None for value in (
        config.conversation_scope_signer_policy,
        config.verified_outcome_signer_policy,
    )):
        raise ValueError("signer_grant_profile_scope_unsupported")
    profile = require_policy_config_binding(owner.policy, config)
    oracle = admission.revocation_oracle
    if type(oracle) is not RootAuthorizedSignerGrantRevocationOracle or not oracle.matches_owner(
        policy=owner.policy, binding=owner.revocation_binding,
    ):
        raise ValueError("signer_grant_oracle_owner_mismatch")
    require_owner_bound_replay_store(owner.policy, admission.replay_store, repo_root=Path(config.repo_root))
    binding = resolve_secret_grant_target_binding(owner.policy, admission.replay_store)
    return profile, binding


def _verified_proposal_inputs(config, owner, high_water, *, clock=None):
    from .reddog_architect_proposal_runtime_authorization import verify_architect_proposal_runtime_authorization
    from .reddog_signer_socket_service_runtime_wiring import _proposal_high_water_valid
    if not _proposal_high_water_valid(config, high_water, config.proposal_replay_high_water_store_id):
        raise ValueError("signer_grant_proposal_high_water_invalid")
    sample = clock if clock is not None else lambda: int(time.time())
    started = sample()
    policy, authorization = verify_architect_proposal_runtime_authorization(
        config, principal_key_resolver=owner.resolver, now_epoch=started,
        require_trusted_principal=True,
    )
    finished = sample()
    if not started <= finished < min(authorization.expires_at, policy.expected_payload.expires_at):
        raise ValueError("signer_grant_proposal_authority_expired_or_clock_reversed")
    return policy, authorization


def _build_leased_proposal(factory, resolver):
    from .reddog_signer_key_provider_dryrun import _build_proposal_signer_backend_from_verified_runtime
    scope = _LEASED_PROPOSAL_OWNER.get()
    if type(scope) is not _ProposalLeaseScope or scope.factory is not factory:
        raise ValueError("signer_grant_proposal_owner_lease_required")
    scope.require_current()
    config, owner = scope.config, scope.owner
    policy, authorization = _verified_proposal_inputs(config, owner, factory.proposal_replay_high_water_store,
                                                            clock=scope.require_current)
    result = _build_proposal_signer_backend_from_verified_runtime(
        factory.profile, resolver, provider_mode=PROVIDER_MODE_WSP71_PERMISSIONED,
        allow_test_only_key_material=False, permission_snapshot_fresh=True,
        proposal_authority_policy=policy, proposal_policy_authorization=authorization,
        proposal_nonce_store_path=config.proposal_nonce_store_path,
        proposal_replay_high_water_store=factory.proposal_replay_high_water_store,
        proposal_replay_high_water_store_id=config.proposal_replay_high_water_store_id,
        proposal_replay_high_water_durability_receipt_id=config.proposal_replay_high_water_durability_receipt_id,
        proposal_nonce_store_allowed_root=config.signer_runtime_root,
        proposal_nonce_store_repo_root=config.repo_root,
    )
    if result.ok and result.backend is not None:
        if (policy, authorization) != _verified_proposal_inputs(config, owner, factory.proposal_replay_high_water_store,
                                                            clock=scope.require_current):
            raise ValueError("signer_grant_proposal_authority_changed")
        _activate_proposal(factory, result.backend.proposal_nonce_store, authorization)
        key = _LeasedProposalKey(result.backend.private_key, scope, (policy, authorization))
        key._require_authority()
        result = replace(result, backend=replace(result.backend, private_key=key))
    return result


def _activate_proposal(factory, store, authorization):
    from .reddog_signer_socket_service_runtime_wiring import _reserve_policy_authorization, _commit_policy_authorization
    identity = {"authorization": authorization.to_dict(), "binding": asdict(factory.owner_context[2])}
    digest = hashlib.sha256(json.dumps(identity, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("ascii")).hexdigest()
    if factory._activation_digest is not None:
        if factory._activation_digest != digest:
            raise ValueError("signer_grant_proposal_activation_changed")
        return
    reservation = _reserve_policy_authorization(store, authorization)
    if not reservation or not _commit_policy_authorization(store, reservation):
        raise ValueError("signer_grant_proposal_activation_rejected")
    object.__setattr__(factory, "_activation_digest", digest)


def deferred_proposal_activation_matches(backend, config, high_water):
    from .reddog_signer_resolve_per_sign_backend import ResolvePerSignSignerBackend
    if type(backend) is not ResolvePerSignSignerBackend:
        return False
    factory = backend.backend_factory
    return (type(factory) is Wsp71EphemeralSignerBackendFactory
            and factory.owner_context is not None and factory.owner_context[0] == config
            and factory.owner_context[2] == backend.binding
            and factory.proposal_replay_high_water_store is high_water)


__all__ = ["Wsp71EphemeralSignerBackendFactory", "build_owner_leased_ephemeral_backend"]
