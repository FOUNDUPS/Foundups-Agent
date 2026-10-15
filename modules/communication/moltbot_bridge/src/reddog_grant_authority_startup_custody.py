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
        _startup_permission(value["replay_integrity_permission"], loader, REPLAY_PURPOSE)
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


__all__ = ["validate_grant_startup_custody", "current_grant_custody", "GRANT_LOAD_PURPOSE"]
