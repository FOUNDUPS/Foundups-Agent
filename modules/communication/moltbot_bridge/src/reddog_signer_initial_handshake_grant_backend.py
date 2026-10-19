"""One initial LOW handshake obtains its grant inside the isolated target."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock
import time

from .reddog_isolated_signer_socket_protocol import SignerPeerAttestation, _valid_peer_attestation
from .reddog_signer_delegated_authority_runtime import RuntimeRejectCode, SigningRequest
from .reddog_signer_independent_grant_authority_client_supply import load_system_service_independent_grant_authority_client
from .reddog_signer_independent_secret_grant_provider import IndependentSignerSecretGrantProvider
from .reddog_signer_mutual_peer_handshake import signer_handshake_request_matches_instance
from .reddog_signer_resolve_per_sign_backend import ResolvePerSignSignerBackend, _reject
from .reddog_signer_socket_peer_credential_attestor import rehydrate_peer_credential_policy
from .reddog_signer_socket_service_bootstrap_admission import lease_signer_socket_service_grant_admission


@dataclass(frozen=True)
class InitialHandshakeGrantBackend:
    """Narrow adapter; authority stays in current E0, provider and target owners."""

    target: ResolvePerSignSignerBackend
    _attempt_lock: object = field(default_factory=Lock, init=False, repr=False, compare=False)
    _attempted: bool = field(default=False, init=False, repr=False, compare=False)

    @property
    def binding(self):
        return self.target.binding

    @property
    def backend_factory(self):
        return self.target.backend_factory

    def sign(self, request, peer):
        try:
            self._require_request(request, peer)
            identity = request.to_dict()
            with self._attempt_lock:
                if self._attempted:
                    raise ValueError("initial_handshake_grant_attempt_used")
                object.__setattr__(self, "_attempted", True)
            policy = self._current_policy(request, peer)
            config, admission, _ = self.backend_factory.owner_context
            supply = load_system_service_independent_grant_authority_client(
                owner_config_path=admission.owner_config_path,
                repo_root=Path(config.repo_root), owner_policy=policy,
                timeout_s=config.timeout_s,
            )
            provider = IndependentSignerSecretGrantProvider(
                Path(config.repo_root), Path(admission.owner_config_path),
                policy, admission.replay_store, supply.binding,
            )
            # issue_grant exits both owner leases cleanly before target root RPC.
            grant = provider.issue_grant(request)
            if request.to_dict() != identity:
                raise ValueError("initial_handshake_request_changed")
            if self._current_policy(request, peer) != policy:
                raise ValueError("initial_handshake_owner_changed")
            return self.target.sign_with_secret_grant(request, peer, grant)
        except Exception:
            return _reject(RuntimeRejectCode.SIGNER_RESPONSE_INVALID)

    def sign_with_secret_grant(self, request, peer, grant):
        """Preserve the existing supplied-grant API and all its checks."""
        return self.target.sign_with_secret_grant(request, peer, grant)

    def _require_request(self, request, peer):
        from .reddog_signer_wsp71_ephemeral_backend_factory import Wsp71EphemeralSignerBackendFactory

        factory = self.backend_factory
        if (type(self.target) is not ResolvePerSignSignerBackend
                or type(factory) is not Wsp71EphemeralSignerBackendFactory
                or factory.owner_context is None
                or type(request) is not SigningRequest
                or type(peer) is not SignerPeerAttestation
                or not _valid_peer_attestation(peer)
                or request.requester_principal_id != peer.peer_principal_id
                or request.elevated_consensus_proof is not None):
            raise ValueError("initial_handshake_peer_invalid")
        config, _, expected = factory.owner_context
        peers = rehydrate_peer_credential_policy(config.peer_policy)
        instance = factory.signer_peer_instance_binding
        if (config.initial_handshake_only is not True
                or type(config.max_requests) is not int or config.max_requests != 1
                or peers is None or peer.peer_principal_id not in peers.uid_to_principal.values()
                or expected != self.binding or instance is None
                or type(instance.generation) is not int or instance.generation != 1
                or not signer_handshake_request_matches_instance(
                    request, instance, now_epoch=int(time.time()))):
            raise ValueError("initial_handshake_request_invalid")

    def _current_policy(self, request, peer):
        from .reddog_signer_proposal_activation import _owner_ephemeral_binding

        config, admission, _ = self.backend_factory.owner_context
        with lease_signer_socket_service_grant_admission(config, admission) as (current, owner):
            self._require_request(request, peer)
            profile, binding = _owner_ephemeral_binding(current, admission, owner)
            policy = owner.policy
            if (profile != self.backend_factory.profile or binding != self.binding
                    or type(policy["generation"]) is not int or policy["generation"] != 1
                    or tuple(policy["allowed_operations"]) != ("signer_socket_peer_handshake",)
                    or tuple(policy["allowed_authority_tiers"]) != ("LOW",)
                    or tuple(policy["consensus_required_tiers"]) != ()):
                raise ValueError("initial_handshake_current_scope_invalid")
        return policy


def build_owner_backend(config, resolver, admission, owner, *, control_loop_anchor_store,
                        control_loop_authority_policy, proposal_replay_high_water_store=None):
    """Existing ephemeral composition, with internal acquisition only for initial LOW."""
    from .reddog_ed25519_signature_verifier_backend import Ed25519SignatureVerifier
    from .reddog_signer_secret_access_grant import SignerSecretAccessGrantBoundary
    from . import reddog_signer_wsp71_ephemeral_backend_factory as factory_owner

    profile, binding = factory_owner._owner_ephemeral_binding(config, admission, owner)
    if config.proposal_authority_policy is not None:
        factory_owner._verified_proposal_inputs(config, owner, proposal_replay_high_water_store)
    factory = factory_owner.Wsp71EphemeralSignerBackendFactory(
        profile, resolver, control_loop_anchor_store=control_loop_anchor_store,
        control_loop_authority_policy=control_loop_authority_policy,
        signer_peer_instance_binding=config.signer_peer_instance_binding,
        owner_context=(config, admission, binding),
        proposal_replay_high_water_store=proposal_replay_high_water_store,
    )
    backend = ResolvePerSignSignerBackend(
        binding, SignerSecretAccessGrantBoundary(
            nonce_store=admission.replay_store, revocation_oracle=admission.revocation_oracle,
            clock=lambda: int(time.time()),
        ), Ed25519SignatureVerifier(), owner.resolver, factory,
    )
    return InitialHandshakeGrantBackend(backend) if config.initial_handshake_only is True else backend


__all__ = ["InitialHandshakeGrantBackend", "build_owner_backend"]
