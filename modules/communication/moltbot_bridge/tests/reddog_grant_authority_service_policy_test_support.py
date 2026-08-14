"""Shared signed-policy fixture fields for grant-service tests."""

from __future__ import annotations

from modules.communication.moltbot_bridge.src.reddog_signer_delegated_authority_runtime import (
    public_key_fingerprint,
)
from modules.communication.moltbot_bridge.src.reddog_signer_owner_e0_policy_contract import (
    signer_key_reference_digest,
)


def grant_service_policy_fields(
    grant_public: str, *digests: str
) -> dict[str, str]:
    first, second, third, fourth, fifth = digests
    return {
        "grant_authority_signer_agent_id": "signer:grant-authority",
        "grant_authority_signer_profile_id": "reddog-grant-authority",
        "grant_authority_key_fingerprint": public_key_fingerprint(grant_public),
        "grant_authority_manifest_id": second,
        "grant_authority_artifact_generation_digest": third,
        "grant_authority_config_digest": fourth,
        "grant_authority_run_packet_digest": fifth,
        "grant_authority_signing_key_ref_hash": signer_key_reference_digest(
            "op://Foundups/reddog-grant-authority/private"
        ),
        "grant_authority_audit_mac_key_ref_hash": signer_key_reference_digest(
            "op://Foundups/reddog-grant-authority/audit"
        ),
        "grant_authority_permission_snapshot_digest": first,
        "grant_authority_permission_snapshot_receipt_id": second,
    }


__all__ = ["grant_service_policy_fields"]
