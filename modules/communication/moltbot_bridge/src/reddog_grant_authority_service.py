"""Bounded LOW grant issuer composed from existing authority owners.

Installed dependencies are inputs, never inferred from role-key possession.
The composition authenticates deployment before listening and permission again
for every request. It does not install custody, create stores, mint E0 policy or
bootstrap itself through the target's grant-required signing backend.
"""
from __future__ import annotations

import time
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any, Mapping

from .reddog_grant_authority_service_owner_binding import grant_authority_owner_runtime_root
from .reddog_grant_authority_wsp71_permission_rehydration import authorize_current_grant_authority_wsp71_use
from .reddog_isolated_signer_socket_resident_service import serve_reddog_isolated_signer_socket_bounded
from .reddog_signer_delegated_authority_runtime import SigningRequest, SigningResponse
from .reddog_signer_independent_secret_grant_binding import (
    build_secret_grant_authority_policy, require_owner_bound_replay_store,
    resolve_secret_grant_target_binding,
    resolve_secret_grant_target_binding_from_config,
)
from .reddog_signer_key_provider_dryrun import SignerKeyProviderProfile
from .reddog_signer_owner_e0_capability_state import freeze_owner_e0_policy
from .reddog_signer_owner_e0_policy_contract import signer_key_reference_digest
from .reddog_signer_process_isolation_gate import enforce_signer_process_isolation
from .reddog_signer_secret_grant_authority_policy import SECRET_GRANT_SIGNING_OPERATION
from .reddog_signer_secret_grant_durable_nonce_store import DurableSignerSecretGrantNonceStore
from .reddog_signer_secret_grant_durable_rate_authority import DurableSignerSecretGrantRateAuthority
from .reddog_signer_secret_grant_issuance import validate_secret_grant_signing_request
from .reddog_signer_secret_grant_root_protected_use_oracle import RootAuthorizedSignerGrantRevocationOracle
from .reddog_signer_socket_peer_credential_attestor import KernelPeerCredentialAttestor, PeerCredentialPolicy
from .reddog_signer_system_service_manifest_selection_loader import SCHEMA_VERSION_V10, SCHEMA_VERSION_V11, SCHEMA_VERSION_V12, SCHEMA_VERSION_V13, _load_owner_config
from .reddog_signer_wsp71_ephemeral_backend_factory import Wsp71EphemeralSignerBackendFactory
from modules.infrastructure.secrets_mcp.src.systemd_credential_secret_resolver import (
    SystemdCredentialBinding, SystemdCredentialSecretResolver, parse_systemd_credential_reference,
)

LOW_OPERATION = "signer_socket_peer_handshake"
REJECT = "grant_service_not_admitted"


@dataclass(frozen=True, slots=True)
class GrantAuthorityServiceDependencies:
    """Existing installed objects; construction alone conveys no authority."""

    owner_policy: Mapping[str, Any]
    issuer_profile: SignerKeyProviderProfile
    credential_binding: SystemdCredentialBinding
    replay_store: DurableSignerSecretGrantNonceStore
    revocation_oracle: RootAuthorizedSignerGrantRevocationOracle


@dataclass(frozen=True, slots=True)
class GrantAuthorityServiceResult:
    """Transport completion, not an assertion that a grant was accepted.

    The underlying socket owner's no-secret flags describe that owner alone;
    they must not be propagated as claims about this credential-using service.
    """

    accepted: bool
    rejection_reasons: tuple[str, ...] = ()
    requests_handled: int = 0
    response_digests: tuple[str, ...] = ()
    socket_removed: bool = False

    def to_dict(self):
        return asdict(self)


def _policy_scope(policy):
    if (tuple(policy.get("allowed_operations", ())) != (LOW_OPERATION,)
            or tuple(policy.get("allowed_authority_tiers", ())) != ("LOW",)
            or tuple(policy.get("consensus_required_tiers", ())) != ()):
        raise ValueError("grant_service_low_handshake_scope_required")


def _profile_binding(dependencies, owner):
    policy, profile = dependencies.owner_policy, dependencies.issuer_profile
    binding = dependencies.credential_binding
    if type(profile) is not SignerKeyProviderProfile or type(binding) is not SystemdCredentialBinding:
        raise ValueError("grant_service_custody_required")
    expected = {
        "signer_agent_id": policy["grant_authority_signer_agent_id"],
        "signer_profile_id": policy["grant_authority_signer_profile_id"],
        "expected_public_key": policy["grant_authority_public_key"],
        "expected_key_fingerprint": policy["grant_authority_key_fingerprint"],
        "expected_key_epoch": policy["grant_authority_key_epoch"],
        "permission_snapshot_digest": policy["grant_authority_permission_snapshot_digest"],
    }
    if any(getattr(profile, name) != value for name, value in expected.items()):
        raise ValueError("grant_service_profile_mismatch")
    for field in ("signing_key_ref", "audit_mac_key_ref"):
        if signer_key_reference_digest(getattr(profile, field)) != policy["grant_authority_" + field + "_hash"]:
            raise ValueError("grant_service_reference_mismatch")
    ids = frozenset(parse_systemd_credential_reference(reference) for reference in
                    (profile.signing_key_ref, profile.audit_mac_key_ref))
    identity = owner["independent_grant_authority"]
    if (None in ids or len(ids) != 2 or ids != binding.credential_ids
            or binding.expected_requester != profile.signer_agent_id
            or binding.expected_uid != identity["authority_service_uid"]
            or binding.expected_gid != identity["authority_service_gid"]):
        raise ValueError("grant_service_custody_scope_mismatch")


def _verify_installed_runtime(repo, owner_path, policy):
    from .reddog_signer_owner_e0_policy_contract import POLICY_SCHEMA_V10
    if policy.get("schema_version") != POLICY_SCHEMA_V10:
        return
    from .reddog_grant_authority_service_manifest_verifier import verify_current_grant_service_artifacts
    from .reddog_grant_authority_installed_runtime_guard import verify_installed_grant_runtime
    root = grant_authority_owner_runtime_root(owner_path, repo, policy["owner_config_id"])
    verified = verify_current_grant_service_artifacts(repo_root=repo, grant_root=root,
        policy=policy, owner_config_path=owner_path)
    verify_installed_grant_runtime(verified["source_descriptor"])


def _current_inputs(repo, owner_path, dependencies):
    policy = dependencies.owner_policy
    _policy_scope(policy)
    owner = _load_owner_config(owner_path, repo=repo)
    if owner["config_id"] != policy["owner_config_id"]:
        raise ValueError("grant_service_owner_changed")
    grant_authority_owner_runtime_root(owner_path, repo, policy["owner_config_id"])
    _verify_installed_runtime(repo, owner_path, policy)
    _profile_binding(dependencies, owner)
    target, rate_binding = _store_bindings(repo, owner_path, owner, dependencies)
    authority = build_secret_grant_authority_policy(policy, target, dependencies.replay_store,
        authority_principal_id=policy["grant_authority_principal_id"],
        authority_principal_provider=policy["grant_authority_principal_provider"],
        authority_public_key=policy["grant_authority_public_key"],
        authority_key_epoch=policy["grant_authority_key_epoch"],
        requester_principal_id=policy["grant_requester_principal_id"], issuer_rate_binding=rate_binding)
    return owner, authority


def _store_bindings(repo, owner_path, owner, dependencies):
    policy, store = dependencies.owner_policy, dependencies.replay_store
    if owner.get("schema_version") in {SCHEMA_VERSION_V10, SCHEMA_VERSION_V11, SCHEMA_VERSION_V12, SCHEMA_VERSION_V13}:
        from .reddog_grant_authority_startup_custody import target_replay_store_config
        from .reddog_signer_secret_grant_durable_rate_authority import bind_protected_issuer_rate_store
        binding = bind_protected_issuer_rate_store(owner_config_path=owner_path,
            repo_root=repo, owner_policy=policy, replay_store=store)
        target = resolve_secret_grant_target_binding_from_config(policy,
            target_replay_store_config(owner, policy, repo))
        return target, binding
    require_owner_bound_replay_store(policy, store, repo_root=repo)
    return resolve_secret_grant_target_binding(policy, store), None


@dataclass(frozen=True, slots=True)
class _CurrentLowGrantBackend:
    repo: Path
    owner_path: Path
    dependencies: GrantAuthorityServiceDependencies

    def authorize(self, action):
        return authorize_current_grant_authority_wsp71_use(
            owner_config_path=self.owner_path, repo_root=self.repo,
            owner_policy=self.dependencies.owner_policy, now_epoch=int(time.time()),
            revocation_oracle=self.dependencies.revocation_oracle, action=action)

    def sign(self, request, peer):
        policy = self.dependencies.owner_policy
        if (type(request) is not SigningRequest
                or request.requested_operation != SECRET_GRANT_SIGNING_OPERATION
                or request.authority_tier != "LOW" or request.consensus_receipt_digest is not None
                or request.elevated_consensus_proof is not None
                or getattr(peer, "boundary_attested", False) is not True
                or getattr(peer, "peer_principal_id", None) != policy["grant_requester_principal_id"]):
            return SigningResponse(accepted=False, rejection_code=REJECT)
        try:
            return self.authorize(lambda: self._sign_current(request, peer))
        except Exception:
            return SigningResponse(accepted=False, rejection_code=REJECT)

    def _sign_current(self, request, peer):
        _, authority = _current_inputs(self.repo, self.owner_path, self.dependencies)
        if validate_secret_grant_signing_request(request, authority, now_epoch=int(time.time())) is None:
            return SigningResponse(accepted=False, rejection_code=REJECT)
        # Permission and current-generation/revocation fences surround custody,
        # signing and response return. Each request gets a new backend, no cache.
        result = Wsp71EphemeralSignerBackendFactory(
            profile=self.dependencies.issuer_profile,
            resolver=SystemdCredentialSecretResolver(self.dependencies.credential_binding),
            secret_grant_authority_policy=authority,
            secret_grant_rate_authority=DurableSignerSecretGrantRateAuthority(self.dependencies.replay_store),
        )()
        if not result.ok or result.backend is None:
            return SigningResponse(accepted=False, rejection_code=REJECT)
        return result.backend.sign(request, peer)


def serve_grant_authority_once(*, repo_root, owner_config_path, dependencies=None,
                               timeout_s=5.0, ready_callback=None):
    """Serve at most one LOW grant request after authentic installed admission.

    The caller supplies installed dependency objects. The installed startup
    composition loads these through the fixed protected dependency loader.
    A transport success does not assert a grant was accepted or RSI occurred.
    """
    try:
        if type(dependencies) is not GrantAuthorityServiceDependencies:
            raise ValueError("grant_service_installed_dependencies_required")
        if (type(dependencies.replay_store) is not DurableSignerSecretGrantNonceStore
                or type(dependencies.revocation_oracle) is not RootAuthorizedSignerGrantRevocationOracle):
            raise ValueError("grant_service_durable_authority_required")
        dependencies = replace(dependencies, owner_policy=freeze_owner_e0_policy(dependencies.owner_policy))
        repo, owner_path = Path(repo_root).resolve(), Path(owner_config_path).resolve()
        owner, _ = _current_inputs(repo, owner_path, dependencies)
        service = owner["independent_grant_authority"]
        consumer = owner["verified_outcome_authority"]
        peers = PeerCredentialPolicy(
            {consumer["signer_uid"]: dependencies.owner_policy["grant_requester_principal_id"]},
            allowed_gids=(consumer["signer_gid"],))
        isolation = enforce_signer_process_isolation(peers,
            expected_signer_uid=service["authority_service_uid"],
            expected_signer_gid=service["authority_service_gid"])
        if isolation.accepted is not True:
            raise ValueError("grant_service_process_isolation_required")
        backend = _CurrentLowGrantBackend(repo, owner_path, dependencies)
        backend.authorize(lambda: _current_inputs(repo, owner_path, dependencies))
    except Exception:
        return GrantAuthorityServiceResult(accepted=False, rejection_reasons=(REJECT,))
    result = serve_reddog_isolated_signer_socket_bounded(
        repo_root=repo, socket_path=service["authority_socket_path"], backend=backend,
        peer_attestor=KernelPeerCredentialAttestor(peers), max_requests=1,
        timeout_s=timeout_s, ready_callback=ready_callback)
    return GrantAuthorityServiceResult(result.accepted, result.rejection_reasons,
        result.requests_handled, result.response_digests, result.socket_removed)


def serve_installed_grant_authority_once(*, repo_root, owner_config_path,
                                       expected_owner_config_id, timeout_s=5.0):
    """Join the existing protected loader and one-request issuer; never install."""
    from .reddog_grant_authority_runtime_dependencies import materialize_grant_authority_runtime_dependencies
    try:
        if type(timeout_s) not in (int, float) or not 0 < timeout_s <= 30:
            raise ValueError("grant_startup_timeout_invalid")
        dependencies = materialize_grant_authority_runtime_dependencies(
            repo_root=repo_root, owner_config_path=owner_config_path,
            expected_owner_config_id=expected_owner_config_id)
        return serve_grant_authority_once(repo_root=repo_root, owner_config_path=owner_config_path,
            dependencies=dependencies, timeout_s=timeout_s)
    except Exception:
        return GrantAuthorityServiceResult(accepted=False, rejection_reasons=(REJECT,))


def main(argv=None):
    """Fixed bounded issuer startup; input paths confer no execution authority."""
    import argparse
    import json
    parser = argparse.ArgumentParser(description="Run one admitted LOW grant request.")
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--owner-authority-config", required=True)
    parser.add_argument("--expected-owner-config-id", required=True)
    args = parser.parse_args(argv)
    result = serve_installed_grant_authority_once(repo_root=args.repo_root,
        owner_config_path=args.owner_authority_config, expected_owner_config_id=args.expected_owner_config_id)
    print(json.dumps(result.to_dict(), sort_keys=True))
    return 0 if result.accepted else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())


__all__ = ["GrantAuthorityServiceDependencies", "GrantAuthorityServiceResult", "serve_grant_authority_once",
           "serve_installed_grant_authority_once", "main"]
