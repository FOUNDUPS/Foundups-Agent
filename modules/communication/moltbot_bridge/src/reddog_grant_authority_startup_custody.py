"""Protected issuer custody metadata; full current E0 admission is separate."""
from __future__ import annotations

import time
from pathlib import Path
from typing import Mapping

from .reddog_runtime_artifact_manifest_contract import RuntimeArtifactManifestError
from .reddog_signer_key_provider_dryrun import SignerKeyProviderProfile
from .reddog_signer_owner_e0_policy_contract import signer_key_reference_digest
from .reddog_signer_system_service_wsp71_resolver_supply import (
    _startup_credential_binding, _startup_permission,
)
from modules.infrastructure.secrets_mcp.src.systemd_credential_secret_resolver import (
    parse_systemd_credential_reference,
)

GRANT_LOAD_PURPOSE = "grant-issuer-root-load.v1"
REPLAY_PURPOSE = "signer-grant-replay-integrity.v1"
RATE_PURPOSE = "grant-issuer-rate-integrity.v1"
RATE_STORE_PURPOSE = "grant-issuer-rate.v1"
RATE_FIELDS = frozenset({"purpose", "nonce_path", "nonce_root", "high_water_path",
    "high_water_root", "replay_store_binding_digest", "replay_store_id", "durability_receipt_id"})
CUSTODY_FIELDS = frozenset({"signing_key_ref", "audit_mac_key_ref", "credential_binding",
    "loader_credential_binding", "root_load_permission", "replay_integrity_permission"})


def validate_grant_startup_custody(owner: Mapping, *, repo_root: Path, owner_root: Path) -> None:
    """Validate root-installed v9 metadata without resolving any credential."""
    try:
        value = owner["grant_startup_custody"]
        if type(value) is not dict or set(value) != CUSTODY_FIELDS:
            raise ValueError("shape")
        service = owner["independent_grant_authority"]
        requester = value["credential_binding"]["expected_requester"]
        authority = dict(signer_uid=service["authority_service_uid"],
            signer_gid=service["authority_service_gid"], signer_principal_id=requester)
        signing = _startup_credential_binding(value["credential_binding"], authority)
        loader = _startup_credential_binding(value["loader_credential_binding"], {
            **authority, "signer_principal_id": value["root_load_permission"]["requester_id"]})
        refs = [value["signing_key_ref"], value["audit_mac_key_ref"],
                value["replay_integrity_permission"]["reference"]]
        ids = [parse_systemd_credential_reference(ref) for ref in refs]
        if None in ids or len(set(ids)) != 3:
            raise ValueError("references")
        if signing.credential_ids != frozenset(ids[:2]) or loader.credential_ids != frozenset((ids[0], ids[2])):
            raise ValueError("credential_scope")
        if signing.credential_directory != loader.credential_directory:
            raise ValueError("credential_directory")
        permission = value["root_load_permission"]
        if permission["reference"] != refs[0]:
            raise ValueError("proof_reference")
        _startup_permission(permission, loader, GRANT_LOAD_PURPOSE,
            identity={name: permission[name] for name in ("public_key", "key_epoch")})
        purpose = RATE_PURPOSE if "grant_rate_store" in owner else REPLAY_PURPOSE
        _startup_permission(value["replay_integrity_permission"], loader, purpose)
        if "grant_rate_store" in owner:
            validate_grant_rate_store(owner, repo_root=repo_root, owner_root=owner_root)
        target = owner["verified_outcome_authority"]
        descriptor = target["descriptor"]
        if (signing.expected_uid == target["signer_uid"]
                or target["signer_principal_id"] in {requester, loader.expected_requester}
                or permission["public_key"] in {descriptor["signer_public_key"],
                    descriptor["root_control_authentication"]["public_key"]}):
            raise ValueError("target_custody_overlap")
    except (KeyError, TypeError, ValueError) as exc:
        raise RuntimeArtifactManifestError("grant_startup_custody_invalid") from exc


def current_grant_custody(owner, policy):
    """Bind protected references/permissions to the current signed issuer identity."""
    value = owner["grant_startup_custody"]
    identity = owner["independent_grant_authority"]
    authority = dict(signer_uid=identity["authority_service_uid"],
        signer_gid=identity["authority_service_gid"],
        signer_principal_id=policy["grant_authority_signer_agent_id"])
    signing = _startup_credential_binding(value["credential_binding"], authority)
    loader = _startup_credential_binding(value["loader_credential_binding"], {
        **authority, "signer_principal_id": policy["grant_authority_principal_id"]})
    for field in ("signing_key_ref", "audit_mac_key_ref"):
        if signer_key_reference_digest(value[field]) != policy["grant_authority_" + field + "_hash"]:
            raise ValueError("grant_startup_reference_mismatch")
    proof = value["root_load_permission"]
    if (proof["public_key"] != policy["grant_authority_public_key"]
            or proof["key_epoch"] != policy["grant_authority_key_epoch"]):
        raise ValueError("grant_startup_proof_identity_mismatch")
    now = time.time()
    for bound in (signing, loader):
        if not bound.issued_at <= now < bound.expires_at:
            raise ValueError("grant_startup_custody_expired")
    for permission in (proof, value["replay_integrity_permission"]):
        if not max(permission["issued_at"], policy["issued_at"]) <= now < min(permission["expires_at"], policy["expires_at"]):
            raise ValueError("grant_startup_permission_expired")
    profile = SignerKeyProviderProfile(
        signer_profile_id=policy["grant_authority_signer_profile_id"],
        signer_agent_id=policy["grant_authority_signer_agent_id"],
        signing_key_ref=value["signing_key_ref"], audit_mac_key_ref=value["audit_mac_key_ref"],
        expected_public_key=policy["grant_authority_public_key"],
        expected_key_fingerprint=policy["grant_authority_key_fingerprint"],
        expected_key_epoch=policy["grant_authority_key_epoch"],
        permission_snapshot_digest=policy["grant_authority_permission_snapshot_digest"],
        ttl_seconds=max(1, int(min(signing.expires_at, policy["expires_at"]) - now)))
    return value, signing, loader, profile


def grant_rate_store_config(owner, repo_root):
    """Derive the issuer store solely from protected owner metadata."""
    from .reddog_signer_secret_grant_durable_nonce_store import SignerGrantReplayStoreConfig
    raw = owner["grant_rate_store"]
    if type(raw) is not dict or set(raw) != RATE_FIELDS or raw["purpose"] != RATE_STORE_PURPOSE:
        raise ValueError("grant_rate_store_shape_invalid")
    return SignerGrantReplayStoreConfig(
        **{name: Path(raw[name]) for name in ("nonce_path", "nonce_root", "high_water_path", "high_water_root")},
        repo_root=Path(repo_root), **{name: raw[name] for name in
            ("replay_store_binding_digest", "replay_store_id", "durability_receipt_id")})


def target_replay_store_config(owner, policy, repo_root):
    """Public target paths remain signed by E0; high-water metadata by owner ID."""
    from .reddog_signer_secret_grant_durable_nonce_store import SignerGrantReplayStoreConfig
    raw = owner["startup_custody"]["replay_store"]
    return SignerGrantReplayStoreConfig(
        nonce_path=Path(policy["replay_path"]), nonce_root=Path(policy["replay_root"]),
        high_water_path=Path(raw["high_water_path"]), high_water_root=Path(raw["high_water_root"]),
        repo_root=Path(repo_root), replay_store_binding_digest=raw["replay_store_binding_digest"],
        replay_store_id=policy["replay_store_id"],
        durability_receipt_id=policy["replay_store_durability_receipt_id"])


def validate_grant_rate_store(owner, *, repo_root, owner_root):
    from .reddog_signer_secret_grant_durable_nonce_store import _validate_config, _paths_overlap
    from modules.infrastructure.shared_utilities.runtime_artifact_safety import (
        validate_runtime_artifact_path, validate_runtime_root_path,
    )
    config = grant_rate_store_config(owner, repo_root)
    _validate_config(config)
    roots = (config.nonce_root, config.high_water_root)
    forbidden = [Path(owner_root), Path(repo_root), Path(owner["anchor_path"]).parent]
    forbidden.extend(Path(owner[name]) for name in ("runtime_root", "high_water_root", "witness_root"))
    # All existing writable domains remain distinct, including target replay,
    # revocation and grant socket roots. No new shared writer is authorized.
    def collect(value):
        if isinstance(value, Mapping):
            for name, item in value.items():
                if name != "grant_rate_store" and name.endswith("_root") and type(item) is str:
                    forbidden.append(Path(item))
                elif name != "grant_rate_store":
                    collect(item)
    collect(owner)
    for path, root in ((config.nonce_path, roots[0]), (config.high_water_path, roots[1])):
        validate_runtime_root_path(root, repo_root=repo_root)
        validate_runtime_artifact_path(path, repo_root=repo_root, allowed_root=root)
        if any(_paths_overlap(root.resolve(), item.resolve()) for item in forbidden):
            raise ValueError("grant_rate_store_domain_overlap")


def require_private_grant_rate_store(owner, config):
    """Require actual issuer-only POSIX custody before any credential access."""
    import os
    import stat
    if os.name != "posix":
        raise ValueError("grant_rate_store_posix_required")
    identity = owner["independent_grant_authority"]
    uid, gid = identity["authority_service_uid"], identity["authority_service_gid"]
    if os.geteuid() != uid or os.getegid() != gid:
        raise ValueError("grant_rate_store_identity_mismatch")
    for path in (config.nonce_root, config.high_water_root, config.nonce_path, config.high_water_path):
        metadata = path.lstat()
        expected = 0o700 if path in (config.nonce_root, config.high_water_root) else 0o600
        if (metadata.st_uid != uid or metadata.st_gid != gid or stat.S_IMODE(metadata.st_mode) != expected
                or stat.S_ISLNK(metadata.st_mode)
                or (expected == 0o600 and (not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1))
                or (expected == 0o700 and not stat.S_ISDIR(metadata.st_mode))):
            raise ValueError("grant_rate_store_private_custody_required")
    for parent in set(config.nonce_path.parents) | set(config.high_water_path.parents):
        metadata = parent.lstat()
        root_sticky = metadata.st_uid == 0 and bool(metadata.st_mode & stat.S_ISVTX)
        if (not stat.S_ISDIR(metadata.st_mode) or metadata.st_uid not in {0, uid}
                or (metadata.st_mode & 0o022 and not root_sticky)):
            raise ValueError("grant_rate_store_ancestry_invalid")


def require_grant_rate_target_separation(owner, policy, repo_root):
    from .reddog_signer_secret_grant_durable_nonce_store import _paths_overlap, _validate_config
    rate, target = grant_rate_store_config(owner, repo_root), target_replay_store_config(owner, policy, repo_root)
    _validate_config(target)
    if (rate.replay_store_id == target.replay_store_id
            or rate.replay_store_binding_digest == target.replay_store_binding_digest
            or rate.durability_receipt_id == target.durability_receipt_id
            or any(_paths_overlap(left.resolve(), right.resolve())
                   for left in (rate.nonce_root, rate.high_water_root)
                   for right in (target.nonce_root, target.high_water_root))):
        raise ValueError("grant_rate_target_domain_overlap")
    return rate, target


__all__ = ["validate_grant_startup_custody", "current_grant_custody", "GRANT_LOAD_PURPOSE"]
