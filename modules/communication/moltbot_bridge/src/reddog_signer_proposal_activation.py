"""Current-owner proposal activation and per-signature authority checks."""
from __future__ import annotations
from contextvars import ContextVar
from dataclasses import asdict, dataclass, field, replace
import hashlib
import json
from threading import get_ident
import time
from typing import Any
from .reddog_signer_key_provider_dryrun import PROVIDER_MODE_WSP71_PERMISSIONED

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
    from .reddog_signer_wsp71_ephemeral_backend_factory import Wsp71EphemeralSignerBackendFactory
    from .reddog_signer_resolve_per_sign_backend import ResolvePerSignSignerBackend
    if type(backend) is not ResolvePerSignSignerBackend:
        return False
    factory = backend.backend_factory
    return (type(factory) is Wsp71EphemeralSignerBackendFactory
            and factory.owner_context is not None and factory.owner_context[0] == config
            and factory.owner_context[2] == backend.binding
            and factory.proposal_replay_high_water_store is high_water)
