"""Exact public artifacts for the isolated grant-authority service."""

from __future__ import annotations

import hashlib
from typing import Any, Mapping

from modules.communication.moltbot_bridge.src.reddog_runtime_artifact_manifest_contract import (
    GRANT_AUTHORITY_SERVICE_ARCHIVE,
    GRANT_AUTHORITY_SERVICE_CONFIG,
    RuntimeArtifactManifestError,
    canonical_json,
    digest,
    is_sha256,
)
from modules.communication.moltbot_bridge.src.reddog_signer_owner_e0_policy_v6 import (
    valid_service_agent_id,
    valid_service_token,
)


CONFIG_SCHEMA = "reddog_grant_authority_service_config.v1"
RUN_PACKET_SCHEMA = "reddog_grant_authority_service_run_packet.v1"
SERVICE_ID = "reddog-grant-authority"
ENTRYPOINT = "reddog_grant_authority_service:main"
CONFIG_FIELDS = frozenset(
    {
        "schema_version", "service_id", "signer_agent_id",
        "signer_profile_id", "public_key", "key_fingerprint", "key_epoch",
        "signing_key_ref_hash", "audit_mac_key_ref_hash",
        "permission_snapshot_digest", "permission_snapshot_receipt_id",
        "archive_digest",
    }
)
RUN_PACKET_FIELDS = frozenset(
    {
        "schema_version", "service_id", "config_filename", "config_digest",
        "archive_filename", "archive_digest", "artifact_set_digest",
        "entrypoint",
    }
)


def validate_grant_service_config(value: Mapping[str, Any]) -> dict[str, str]:
    """Validate the exact public config; secret references are never allowed."""

    raw = _exact_text_mapping(value, CONFIG_FIELDS, "config")
    if raw["schema_version"] != CONFIG_SCHEMA or raw["service_id"] != SERVICE_ID:
        raise RuntimeArtifactManifestError("grant_service_config_invalid")
    digest_fields = CONFIG_FIELDS - {
        "schema_version", "service_id", "signer_agent_id",
        "signer_profile_id", "public_key", "key_epoch",
    }
    if any(not is_sha256(raw[name]) for name in digest_fields):
        raise RuntimeArtifactManifestError("grant_service_config_invalid")
    if (
        not valid_service_agent_id(raw["signer_agent_id"])
        or not valid_service_token(raw["signer_profile_id"])
        or not valid_service_token(raw["key_epoch"])
    ):
        raise RuntimeArtifactManifestError("grant_service_config_invalid")
    fingerprint = "sha256:" + hashlib.sha256(
        raw["public_key"].encode("ascii")
    ).hexdigest()
    if raw["key_fingerprint"] != fingerprint:
        raise RuntimeArtifactManifestError("grant_service_config_invalid")
    return raw


def validate_grant_service_run_packet(
    value: Mapping[str, Any], *, config_digest: str, archive_digest: str
) -> dict[str, str]:
    """Validate the inert launch description against exact artifact digests."""

    raw = _exact_text_mapping(value, RUN_PACKET_FIELDS, "run_packet")
    expected_set = digest(
        {"archive_digest": archive_digest, "config_digest": config_digest}
    )
    expected = {
        "schema_version": RUN_PACKET_SCHEMA,
        "service_id": SERVICE_ID,
        "config_filename": GRANT_AUTHORITY_SERVICE_CONFIG,
        "config_digest": config_digest,
        "archive_filename": GRANT_AUTHORITY_SERVICE_ARCHIVE,
        "archive_digest": archive_digest,
        "artifact_set_digest": expected_set,
        "entrypoint": ENTRYPOINT,
    }
    if raw != expected:
        raise RuntimeArtifactManifestError("grant_service_run_packet_invalid")
    return raw


def _exact_text_mapping(
    value: Mapping[str, Any], fields: frozenset[str], label: str
) -> dict[str, str]:
    if not isinstance(value, Mapping) or set(value) != fields:
        raise RuntimeArtifactManifestError(f"grant_service_{label}_invalid")
    raw = dict(value)
    if any(
        type(item) is not str
        or not item
        or not item.isascii()
        or len(item) > 4096
        for item in raw.values()
    ):
        raise RuntimeArtifactManifestError(f"grant_service_{label}_invalid")
    try:
        canonical_json(raw)
    except (TypeError, ValueError) as exc:
        raise RuntimeArtifactManifestError(
            f"grant_service_{label}_invalid"
        ) from exc
    return raw


__all__ = [
    "CONFIG_FIELDS", "CONFIG_SCHEMA", "ENTRYPOINT", "RUN_PACKET_FIELDS",
    "RUN_PACKET_SCHEMA", "SERVICE_ID", "validate_grant_service_config",
    "validate_grant_service_run_packet",
]
