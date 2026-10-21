"""Load protected issuer custody after isolation; never provision it implicitly."""
from __future__ import annotations

import time
from pathlib import Path

from .foundup_verified_outcome_root_authority_client import build_root_authority_socket_exchange
from .foundup_verified_outcome_root_authority_wire_codec import canonical_bytes, decode_message
from .foundup_verified_outcome_root_revocation_client import _create_root_revocation_anchor_authority
from .foundup_verified_outcome_root_revocation_protocol import GRANT_ROLE
from .foundup_verified_outcome_root_runtime_materializer import _materialize_durable_revocation_reader
from .reddog_grant_authority_root_request_signer import build_grant_root_request_signer
from .reddog_grant_authority_service import (
    GrantAuthorityServiceDependencies, _policy_scope, _profile_binding, _verify_installed_runtime,
)
from .reddog_grant_authority_startup_custody import (
    current_grant_custody, require_grant_rate_target_separation, require_private_grant_rate_store,
)
from .reddog_signer_owner_e0_capability_state import freeze_owner_e0_policy, thaw_owner_e0_policy
from .reddog_signer_owner_e0_current_selection import lease_validated_owner_e0_current_admission
from .reddog_signer_process_isolation_gate import enforce_signer_process_isolation
from .reddog_signer_secret_grant_root_protected_use_oracle import build_grant_issuer_revocation_oracle
from .reddog_signer_socket_peer_credential_attestor import PeerCredentialPolicy
from .reddog_signer_system_service_manifest_selection_loader import (
    SCHEMA_VERSION_V9, SCHEMA_VERSION_V10, SCHEMA_VERSION_V11, SCHEMA_VERSION_V12, SCHEMA_VERSION_V13, _load_owner_config, _read_root_owned_bytes,
)
from .reddog_signer_system_service_runtime_dependencies import (
    _materialize_startup_replay, _materialize_provisioned_replay,
)
from modules.infrastructure.secrets_mcp.src.systemd_credential_secret_resolver import SystemdCredentialSecretResolver


def _isolate(owner, policy):
    issuer, target = owner["independent_grant_authority"], owner["verified_outcome_authority"]
    peers = PeerCredentialPolicy({target["signer_uid"]: policy["grant_requester_principal_id"]},
        allowed_gids=(target["signer_gid"],))
    result = enforce_signer_process_isolation(peers,
        expected_signer_uid=issuer["authority_service_uid"],
        expected_signer_gid=issuer["authority_service_gid"])
    if result.accepted is not True:
        raise ValueError("grant_startup_process_isolation_required")


def _current_owner(owner_path, repo, owner, policy):
    current = _load_owner_config(owner_path, repo=repo)
    if (current["schema_version"] not in {SCHEMA_VERSION_V9, SCHEMA_VERSION_V10, SCHEMA_VERSION_V11, SCHEMA_VERSION_V12, SCHEMA_VERSION_V13}
            or current["config_id"] != policy["owner_config_id"]
            or canonical_bytes(current) != canonical_bytes(owner)):
        raise ValueError("grant_startup_owner_changed")
    # Re-read the protected full policy, including its signatures and permission.
    raw = _read_root_owned_bytes(Path(current["startup_custody"]["policy_path"]), owner_path.parent)
    if canonical_bytes(decode_message(raw)) != canonical_bytes(thaw_owner_e0_policy(policy)):
        raise ValueError("grant_startup_policy_changed")
    return current_grant_custody(current, policy)


def _oracle(owner, repo, policy, lease_binding, resolver, signer):
    root = owner["verified_outcome_authority"]
    anchor = _create_root_revocation_anchor_authority(root["descriptor"],
        owner_config_id=owner["config_id"], policy=thaw_owner_e0_policy(policy), binding=lease_binding,
        exchange=build_root_authority_socket_exchange(
            repo_root=repo, socket_path=root["authority_socket_path"],
            expected_server_uid=root["authority_service_uid"]),
        request_signer=signer, now_epoch=int(time.time()), requester_role=GRANT_ROLE)
    durable = _materialize_durable_revocation_reader(repo, policy, lease_binding, anchor, resolver)
    return build_grant_issuer_revocation_oracle(durable=durable, policy=policy, binding=lease_binding)


def materialize_grant_authority_runtime_dependencies(*, owner_config_path, repo_root,
                                                   expected_owner_config_id):
    """Load existing protected installation, returning inputs for the bounded service.

    This performs no installation and does not authorize deployment or issue grants.
    Root LOAD is outside the current-generation lock; all inputs are revalidated
    under that lock before returning. Missing custody/permission remains an error.
    """
    repo, path = Path(repo_root).resolve(), Path(owner_config_path)
    if not path.is_absolute():
        raise ValueError("grant_startup_owner_path_not_absolute")
    owner = _load_owner_config(path, repo=repo)
    if owner["schema_version"] not in {SCHEMA_VERSION_V9, SCHEMA_VERSION_V10, SCHEMA_VERSION_V11, SCHEMA_VERSION_V12, SCHEMA_VERSION_V13} or owner["config_id"] != expected_owner_config_id:
        raise ValueError("grant_startup_owner_selection_mismatch")
    raw = _read_root_owned_bytes(Path(owner["startup_custody"]["policy_path"]), path.parent)
    policy = freeze_owner_e0_policy(decode_message(raw))
    _policy_scope(policy)
    _isolate(owner, policy)
    with lease_validated_owner_e0_current_admission(
        owner_config_path=path, repo_root=repo, policy=policy,
    ) as current:
        custody, signing, loader, profile = _current_owner(path, repo, owner, current.policy)
        _verify_installed_runtime(repo, path, current.policy)
        replay = _materialize_issuer_store(repo, owner, custody, current.policy,
                                          SystemdCredentialSecretResolver(loader))
        _current_owner(path, repo, owner, current.policy)
        signer = build_grant_root_request_signer(owner_config_path=path, repo_root=repo,
            policy=current.policy, descriptor=owner["verified_outcome_authority"]["descriptor"],
            credential_binding=loader)
        binding, resolver = current.revocation_binding, current.resolver
    oracle = _oracle(owner, repo, policy, binding, resolver, signer)
    dependencies = GrantAuthorityServiceDependencies(policy, profile, signing, replay, oracle)
    _revalidate_dependencies(path, repo, owner, dependencies)
    return dependencies


def _materialize_issuer_store(repo, owner, custody, policy, resolver):
    if owner["schema_version"] in {SCHEMA_VERSION_V10, SCHEMA_VERSION_V11, SCHEMA_VERSION_V12, SCHEMA_VERSION_V13}:
        config, _ = require_grant_rate_target_separation(owner, policy, repo)
        require_private_grant_rate_store(owner, config)
        return _materialize_provisioned_replay(config, custody["replay_integrity_permission"],
                                              policy["expires_at"], resolver)
    replay_custody = {**owner["startup_custody"],
        "replay_integrity_permission": custody["replay_integrity_permission"]}
    return _materialize_startup_replay(repo, replay_custody, policy, resolver)


def _revalidate_dependencies(path, repo, owner, dependencies):
    policy, oracle = dependencies.owner_policy, dependencies.revocation_oracle
    def check_current():
        with lease_validated_owner_e0_current_admission(
            owner_config_path=path, repo_root=repo, policy=policy,
        ) as current:
            _current_owner(path, repo, owner, current.policy)
            _verify_installed_runtime(repo, path, current.policy)
            _profile_binding(dependencies, owner)
            if not oracle.matches_owner(policy=current.policy, binding=current.revocation_binding):
                raise ValueError("grant_startup_revocation_owner_changed")
            _current_owner(path, repo, owner, current.policy)
    # Admission must sample time inside the durable fence, not before lock/I/O.
    oracle.authorize_current_key_epoch_use(key_epoch=policy["grant_authority_key_epoch"],
        expires_at=policy["expires_at"], action=check_current)


__all__ = ["materialize_grant_authority_runtime_dependencies"]
