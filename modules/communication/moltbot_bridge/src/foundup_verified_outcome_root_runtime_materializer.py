"""Materialize root authority service dependencies from authenticated owner state."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Callable, Mapping

from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_authority_client import (
    build_root_authority_socket_exchange,
)
from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_authority_dependency import (
    RootAuthorityServiceDependencies,
    build_root_authority_service_dependencies,
    state_binding_from_owner_config,
)
from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_authority_service import (
    RootAuthoritySnapshot,
)
from modules.communication.moltbot_bridge.src.reddog_runtime_artifact_manifest_contract import (
    RuntimeArtifactManifestError,
)
from modules.communication.moltbot_bridge.src.reddog_signer_secret_grant_revocation_authority_binding import (
    SignerGrantRevocationAuthorityBinding,
)

OwnerSupplier = Callable[[], Mapping[str, Any]]


def materialize_root_authority_service_dependencies(
    *, owner_config_path: Path | str, repo: Path,
    owner_supplier: OwnerSupplier,
) -> RootAuthorityServiceDependencies:
    from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_revocation_authority import (
        _create_root_revocation_service_authority,
    )

    owner = owner_supplier()
    raw = _root_policy(owner)

    def supply() -> RootAuthoritySnapshot:
        current = owner_supplier()
        current_raw = _root_policy(current)
        descriptor = dict(current_raw["descriptor"])
        return RootAuthoritySnapshot(
            owner_config_id=str(current["config_id"]),
            authority_generation_sequence=int(
                descriptor["authority_generation_sequence"]
            ),
            state_binding_digest=state_binding_from_owner_config(
                current_raw, repo=repo
            ),
            signer_principal_id=str(current_raw["signer_principal_id"]),
            signer_uid=int(current_raw["signer_uid"]),
            signer_gid=int(current_raw["signer_gid"]),
            descriptor=descriptor,
        )

    return build_root_authority_service_dependencies(
        raw, repo=repo, snapshot_supplier=supply,
        revocation_authority=_create_root_revocation_service_authority(
            owner_config_path=owner_config_path, repo_root=repo,
        ),
    )


def materialize_revocation_anchor_authority(
    *, owner: Mapping[str, Any], repo: Path, policy: Mapping[str, Any],
    binding: SignerGrantRevocationAuthorityBinding,
    request_signer: Callable[[str], str], now_epoch: int | None,
) -> Any:
    from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_revocation_client import (
        _create_root_revocation_anchor_authority,
    )

    raw = _root_policy(owner)
    exchange = build_root_authority_socket_exchange(
        repo_root=repo, socket_path=raw["authority_socket_path"],
        expected_server_uid=int(raw["authority_service_uid"]),
    )
    return _create_root_revocation_anchor_authority(
        raw["descriptor"], owner_config_id=str(owner["config_id"]),
        policy=policy, binding=binding, exchange=exchange,
        request_signer=request_signer,
        now_epoch=int(time.time()) if now_epoch is None else now_epoch,
    )


def materialize_root_protected_use_authority(
    *, owner: Mapping[str, Any], repo: Path, policy: Mapping[str, Any],
    binding: SignerGrantRevocationAuthorityBinding,
    request_signer: Callable[[str], str], now_epoch: int | None,
) -> Any:
    from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_protected_use_client import (
        _create_root_protected_use_authority,
    )

    raw = _root_policy(owner)
    exchange = build_root_authority_socket_exchange(
        repo_root=repo, socket_path=raw["authority_socket_path"],
        expected_server_uid=int(raw["authority_service_uid"]),
    )
    return _create_root_protected_use_authority(
        raw["descriptor"], owner_config_id=str(owner["config_id"]),
        policy=policy, binding=binding, exchange=exchange,
        request_signer=request_signer,
        now_epoch=int(time.time()) if now_epoch is None else now_epoch,
    )


def _root_policy(owner: Mapping[str, Any]) -> Mapping[str, Any]:
    raw = owner.get("verified_outcome_authority")
    if not isinstance(raw, Mapping) or not isinstance(raw.get("descriptor"), Mapping):
        raise RuntimeArtifactManifestError("verified_outcome_authority_missing")
    return raw


def materialize_system_service_revocation_oracle(
    *, owner_config_path: Path | str, repo: Path, policy: Mapping[str, Any],
    credential_binding: Any,
) -> Any:
    """Compose existing readers and root clients without holding a lease over RPC."""
    from .reddog_signer_owner_e0_current_selection import lease_validated_owner_e0_current_admission
    from .reddog_signer_owner_e0_capability_state import thaw_owner_e0_policy
    from .reddog_signer_system_service_manifest_selection_loader import _load_owner_config
    from .reddog_signer_system_service_wsp71_resolver_supply import (
        build_system_service_root_request_signer, ROOT_LOAD_PURPOSE, ROOT_CONTROL_PURPOSE,
    )
    from .reddog_signer_secret_grant_root_protected_use_oracle import RootAuthorizedSignerGrantRevocationOracle

    with lease_validated_owner_e0_current_admission(
        owner_config_path=owner_config_path, repo_root=repo, policy=policy,
    ) as lease:
        owner = _load_owner_config(owner_config_path, repo=repo)
        if owner["config_id"] != lease.policy["owner_config_id"]:
            raise ValueError("startup_revocation_owner_mismatch")
        binding, current_policy, resolver = lease.revocation_binding, thaw_owner_e0_policy(lease.policy), lease.resolver
        descriptor = _root_policy(owner)["descriptor"]
        signers = [build_system_service_root_request_signer(
            owner_config_path=owner_config_path, repo_root=repo, policy=current_policy,
            descriptor=descriptor, purpose=purpose, credential_binding=credential_binding,
        ) for purpose in (ROOT_LOAD_PURPOSE, ROOT_CONTROL_PURPOSE)]
    anchor = materialize_revocation_anchor_authority(
        owner=owner, repo=repo, policy=current_policy, binding=binding,
        request_signer=signers[0], now_epoch=None,
    )
    protected = materialize_root_protected_use_authority(
        owner=owner, repo=repo, policy=current_policy, binding=binding,
        request_signer=signers[1], now_epoch=None,
    )
    oracle = RootAuthorizedSignerGrantRevocationOracle(
        durable=_materialize_durable_revocation_reader(repo, current_policy, binding, anchor, resolver),
        protected_use=protected,
    )
    with lease_validated_owner_e0_current_admission(
        owner_config_path=owner_config_path, repo_root=repo, policy=current_policy,
    ) as current:
        if not oracle.matches_owner(policy=current.policy, binding=current.revocation_binding):
            raise ValueError("startup_revocation_owner_changed")
    return oracle


def _materialize_durable_revocation_reader(repo, policy, binding, anchor, resolver):
    from .reddog_ed25519_signature_verifier_backend import Ed25519SignatureVerifier
    from .reddog_signer_secret_grant_revocation_authority_reader import SignerGrantRevocationAuthorityReader
    from .reddog_signer_secret_grant_revocation_durable_oracle import UncomposedDurableSignerGrantRevocationOracle
    from .reddog_sqlite_monotonic_authority_store import SqliteMonotonicAuthorityReader

    return UncomposedDurableSignerGrantRevocationOracle(
        binding=binding, policy=policy,
        reader=SignerGrantRevocationAuthorityReader(binding, repo_root=repo),
        witness=SqliteMonotonicAuthorityReader(
            binding.witness_path, allowed_root=binding.witness_root, repo_root=repo,
            store_id=binding.witness_store_id,
            durability_receipt_id=binding.witness_durability_receipt_id,
        ),
        anchor=anchor, principal_key_resolver=resolver,
        signature_verifier=Ed25519SignatureVerifier(), clock=lambda: int(time.time()),
    )


def materialize_system_service_runtime_dependencies(
    *, owner_config_path: Path | str, repo: Path, expected_owner_config_id: str,
) -> Any:
    """After isolation, authenticate custody and assemble existing runtime owners."""
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
    from .reddog_signer_secret_grant_durable_nonce_store import _validate_config, _require_store_files
    _validate_config(config)
    _require_store_files(config)
    _require_provisioned_high_water(repo, raw, config.replay_store_id, config.durability_receipt_id)
    if not permission["issued_at"] <= time.time() < min(permission["expires_at"], policy["expires_at"]):
        raise ValueError("startup_replay_permission_expired")
    result = resolver.resolve(permission["reference"], permission["requester_id"])
    if result.success is not True or result.reference != permission["reference"]:
        raise ValueError("startup_replay_credential_rejected")
    secret = result.get_value()
    if type(secret) is not str or not secret:
        raise ValueError("startup_replay_credential_invalid")
    resolver._remaining()
    if not permission["issued_at"] <= time.time() < min(permission["expires_at"], policy["expires_at"]):
        raise ValueError("startup_replay_permission_expired")
    store = DurableSignerSecretGrantNonceStore(config, integrity_key=secret.encode("utf-8"), clock=time.time)
    require_owner_bound_replay_store(policy, store, repo_root=repo)
    return store


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


__all__ = [
    "materialize_revocation_anchor_authority",
    "materialize_root_protected_use_authority",
    "materialize_root_authority_service_dependencies",
    "materialize_system_service_revocation_oracle",
    "materialize_system_service_runtime_dependencies",
]
