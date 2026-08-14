"""Authenticated E0-to-manifest binding for the isolated grant service."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping

from .reddog_grant_authority_service_manifest_verifier import (
    verify_current_grant_service_artifacts,
)
from .reddog_grant_authority_service_owner_binding import (
    grant_authority_owner_runtime_root,
)
from modules.communication.moltbot_bridge.src.reddog_runtime_artifact_manifest_contract import (
    RuntimeArtifactManifestError,
)
from modules.communication.moltbot_bridge.src.reddog_signer_owner_e0_current_selection import (
    lease_validated_owner_e0_current_admission,
)
from modules.communication.moltbot_bridge.src.reddog_signer_owner_e0_policy_contract import (
    POLICY_SCHEMA_V6,
)
from modules.communication.moltbot_bridge.src.reddog_work_order_signature_verifier import (
    constant_time_compare,
)


@dataclass(frozen=True, slots=True)
class GrantAuthorityServiceManifestBinding:
    """Hash-only evidence; callers receive no launch or secret capability."""

    owner_policy_id: str
    manifest_id: str
    artifact_generation_digest: str
    config_digest: str
    run_packet_digest: str
    service_archive_digest: str
    signer_agent_id: str
    signer_profile_id: str
    public_key: str
    key_fingerprint: str
    key_epoch: str
    permission_snapshot_digest: str
    permission_snapshot_receipt_id: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def bind_grant_authority_service_manifest(
    *,
    owner_config_path: Path | str,
    repo_root: Path | str,
    owner_policy: Mapping[str, Any],
) -> GrantAuthorityServiceManifestBinding:
    """Reload current root-owned E0 and verify its exact grant artifact set."""

    repo = Path(repo_root).resolve()
    with lease_validated_owner_e0_current_admission(
        owner_config_path=owner_config_path,
        repo_root=repo,
        policy=owner_policy,
    ) as admission:
        policy = admission.policy
        if policy.get("schema_version") != POLICY_SCHEMA_V6:
            raise RuntimeArtifactManifestError(
                "grant_authority_service_binding_invalid"
            )
        grant_root = grant_authority_owner_runtime_root(
            owner_config_path, repo, str(policy["owner_config_id"])
        )
        verified = verify_current_grant_service_artifacts(
            repo_root=repo, grant_root=grant_root, policy=policy
        )
        return _binding(policy, verified)


def _binding(
    policy: Mapping[str, Any], verified: Mapping[str, Any]
) -> GrantAuthorityServiceManifestBinding:
    config = verified["config"]
    expected = _expected_bindings(policy, verified, config)
    if any(
        not constant_time_compare(str(left), str(right))
        for left, right in expected
    ):
        raise RuntimeArtifactManifestError(
            "grant_authority_service_binding_mismatch"
        )
    return GrantAuthorityServiceManifestBinding(
        owner_policy_id=str(policy["policy_id"]),
        manifest_id=str(verified["manifest_id"]),
        artifact_generation_digest=str(
            verified["artifact_generation_digest"]
        ),
        config_digest=str(policy["grant_authority_config_digest"]),
        run_packet_digest=str(policy["grant_authority_run_packet_digest"]),
        service_archive_digest=str(verified["service_archive_digest"]),
        signer_agent_id=str(config["signer_agent_id"]),
        signer_profile_id=str(config["signer_profile_id"]),
        public_key=str(config["public_key"]),
        key_fingerprint=str(config["key_fingerprint"]),
        key_epoch=str(config["key_epoch"]),
        permission_snapshot_digest=str(config["permission_snapshot_digest"]),
        permission_snapshot_receipt_id=str(
            config["permission_snapshot_receipt_id"]
        ),
    )


def _expected_bindings(
    policy: Mapping[str, Any], verified: Mapping[str, Any],
    config: Mapping[str, Any],
) -> tuple[tuple[object, object], ...]:
    return (
        (verified["manifest_id"], policy["grant_authority_manifest_id"]),
        (
            verified["artifact_generation_digest"],
            policy["grant_authority_artifact_generation_digest"],
        ),
        (config["signer_agent_id"], policy["grant_authority_signer_agent_id"]),
        (
            config["signer_profile_id"],
            policy["grant_authority_signer_profile_id"],
        ),
        (config["public_key"], policy["grant_authority_public_key"]),
        (config["key_fingerprint"], policy["grant_authority_key_fingerprint"]),
        (config["key_epoch"], policy["grant_authority_key_epoch"]),
        (
            config["signing_key_ref_hash"],
            policy["grant_authority_signing_key_ref_hash"],
        ),
        (
            config["audit_mac_key_ref_hash"],
            policy["grant_authority_audit_mac_key_ref_hash"],
        ),
        (
            config["permission_snapshot_digest"],
            policy["grant_authority_permission_snapshot_digest"],
        ),
        (
            config["permission_snapshot_receipt_id"],
            policy["grant_authority_permission_snapshot_receipt_id"],
        ),
    )


__all__ = [
    "GrantAuthorityServiceManifestBinding",
    "bind_grant_authority_service_manifest",
]
