"""Compose isolated signer startup custody using existing authenticated owners."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any


def materialize_system_service_runtime_dependencies(
    *, owner_config_path: Path | str, repo: Path, expected_owner_config_id: str,
) -> Any:
    """After isolation, authenticate custody and assemble existing runtime owners."""
    from .foundup_verified_outcome_root_runtime_materializer import materialize_system_service_revocation_oracle
    from .foundup_verified_outcome_root_authority_wire_codec import decode_message
    from .reddog_signer_owner_e0_current_selection import lease_validated_owner_e0_current_admission
    from .reddog_signer_system_service_manifest_selection_loader import _load_owner_config, _read_root_owned_bytes
    from .reddog_signer_socket_service_bootstrap_admission import (
        SignerSocketServiceGrantAdmission, SignerSocketServiceRuntimeDependencies,
    )
    from modules.infrastructure.secrets_mcp.src.systemd_credential_secret_resolver import (
        SystemdCredentialBinding, SystemdCredentialSecretResolver,
    )

    owner = _load_owner_config(owner_config_path, repo=repo)
    if owner["config_id"] != expected_owner_config_id:
        raise ValueError("startup_owner_selection_changed")
    custody = owner["startup_custody"]
    policy_path = Path(custody["policy_path"])
    policy = decode_message(_read_root_owned_bytes(policy_path, Path(owner_config_path).parent))
    metadata = dict(custody["credential_binding"])
    metadata["credential_ids"] = frozenset(metadata["credential_ids"])
    binding = SystemdCredentialBinding(**metadata)
    resolver = SystemdCredentialSecretResolver(binding)
    with lease_validated_owner_e0_current_admission(
        owner_config_path=owner_config_path, repo_root=repo, policy=policy,
    ) as current:
        if current.policy["owner_config_id"] != expected_owner_config_id:
            raise ValueError("startup_policy_owner_mismatch")
        replay = _materialize_startup_replay(repo, custody, current.policy, resolver)
        proposal_store = _materialize_startup_proposal_store(repo, custody, current.config)
        principal_resolver, policy = current.resolver, current.policy
    oracle = materialize_system_service_revocation_oracle(
        owner_config_path=owner_config_path, repo=repo, policy=policy,
        credential_binding=binding,
    )
    return SignerSocketServiceRuntimeDependencies(
        resolver, principal_resolver, proposal_store,
        SignerSocketServiceGrantAdmission(owner_config_path, policy, replay, oracle),
    )


def _materialize_startup_replay(repo, custody, policy, resolver):
    from .reddog_signer_secret_grant_durable_nonce_store import (
        DurableSignerSecretGrantNonceStore, SignerGrantReplayStoreConfig,
    )
    from .reddog_signer_independent_secret_grant_binding import require_owner_bound_replay_store

    raw = custody["replay_store"]
    permission = custody["replay_integrity_permission"]
    config = SignerGrantReplayStoreConfig(
        nonce_path=Path(policy["replay_path"]), nonce_root=Path(policy["replay_root"]),
        high_water_path=Path(raw["high_water_path"]), high_water_root=Path(raw["high_water_root"]),
        repo_root=repo, replay_store_binding_digest=raw["replay_store_binding_digest"],
        replay_store_id=policy["replay_store_id"],
        durability_receipt_id=policy["replay_store_durability_receipt_id"],
    )
    store = _materialize_provisioned_replay(config, permission, policy["expires_at"], resolver)
    require_owner_bound_replay_store(policy, store, repo_root=repo)
    return store


def _materialize_provisioned_replay(config, permission, expires_at, resolver):
    """Open one explicitly configured existing store; never provision implicitly."""
    from .reddog_signer_secret_grant_durable_nonce_store import (
        DurableSignerSecretGrantNonceStore, _validate_config, _require_store_files,
    )
    _validate_config(config)
    _require_store_files(config)
    raw = dict(high_water_path=config.high_water_path, high_water_root=config.high_water_root)
    _require_provisioned_high_water(config.repo_root, raw, config.replay_store_id, config.durability_receipt_id)
    if not permission["issued_at"] <= time.time() < min(permission["expires_at"], expires_at):
        raise ValueError("startup_replay_permission_expired")
    result = resolver.resolve(permission["reference"], permission["requester_id"])
    if result.success is not True or result.reference != permission["reference"]:
        raise ValueError("startup_replay_credential_rejected")
    secret = result.get_value()
    if type(secret) is not str or not secret:
        raise ValueError("startup_replay_credential_invalid")
    resolver._remaining()
    if not permission["issued_at"] <= time.time() < min(permission["expires_at"], expires_at):
        raise ValueError("startup_replay_permission_expired")
    return DurableSignerSecretGrantNonceStore(config, integrity_key=secret.encode("utf-8"), clock=time.time)


def _require_provisioned_high_water(repo, raw, store_id, durability_id):
    from .reddog_sqlite_monotonic_authority_store import SqliteMonotonicAuthorityReader

    reader = SqliteMonotonicAuthorityReader(
        raw["high_water_path"], allowed_root=raw["high_water_root"], repo_root=repo,
        store_id=store_id, durability_receipt_id=durability_id,
    )
    # Read-only opening must validate the already provisioned database before
    # constructing the existing writable store, whose constructor creates schema.
    reader.load("sha256:" + "0" * 64)


def _materialize_startup_proposal_store(repo, custody, config):
    from .reddog_sqlite_monotonic_authority_store import SqliteMonotonicAuthorityStore

    raw = custody["proposal_replay_store"]
    if config.proposal_authority_policy is None:
        if raw is not None:
            raise ValueError("startup_proposal_replay_unexpected")
        return None
    if raw is None:
        raise ValueError("startup_proposal_replay_missing")
    store_id = config.proposal_replay_high_water_store_id
    durability_id = config.proposal_replay_high_water_durability_receipt_id
    _require_provisioned_high_water(repo, raw, store_id, durability_id)
    return SqliteMonotonicAuthorityStore(
        raw["high_water_path"], allowed_root=raw["high_water_root"], repo_root=repo,
        store_id=store_id, durability_receipt_id=durability_id,
    )


__all__ = ["materialize_system_service_runtime_dependencies"]
