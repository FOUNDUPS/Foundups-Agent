"""Exact public artifacts for the isolated grant-authority service."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

from modules.communication.moltbot_bridge.src.reddog_runtime_artifact_manifest_contract import (
    GRANT_AUTHORITY_SERVICE_ARCHIVE,
    GRANT_AUTHORITY_SERVICE_CONFIG,
    RuntimeArtifactManifestError,
    canonical_json,
    digest,
    is_sha256,
    raw_digest,
)
from modules.communication.moltbot_bridge.src.reddog_signer_owner_e0_policy_v6 import (
    valid_service_agent_id,
    valid_service_token,
)


CONFIG_SCHEMA = "reddog_grant_authority_service_config.v1"
CONFIG_SCHEMA_V2 = "reddog_grant_authority_service_config.v2"
RUN_PACKET_SCHEMA = "reddog_grant_authority_service_run_packet.v1"
CONFIG_SCHEMA_V3 = "reddog_grant_authority_service_config.v3"
RUN_PACKET_SCHEMA_V2 = "reddog_grant_authority_service_run_packet.v2"
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
SOURCE_POLICY_CONFIG_FIELDS = frozenset(
    {
        "source_policy_owner_config_id",
        "source_policy_repo_root_digest",
        "source_policy_digest",
    }
)
CONFIG_FIELDS_V2 = CONFIG_FIELDS | SOURCE_POLICY_CONFIG_FIELDS
CONFIG_FIELDS_V3 = (CONFIG_FIELDS - {"archive_digest"}) | {
    "installed_runtime_descriptor_digest", "owner_config_id", "repo_root_digest",
}
RUN_PACKET_FIELDS_V2 = frozenset({"schema_version", "service_id", "config_filename",
    "config_digest", "source_descriptor_filename", "installed_runtime_descriptor_digest",
    "artifact_set_digest", "entrypoint", "dependency_loader"})
RUN_PACKET_FIELDS = frozenset(
    {
        "schema_version", "service_id", "config_filename", "config_digest",
        "archive_filename", "archive_digest", "artifact_set_digest",
        "entrypoint",
    }
)


def validate_grant_service_config(value: Mapping[str, Any]) -> dict[str, str]:
    """Validate the exact public config; secret references are never allowed."""

    schema = value.get("schema_version") if isinstance(value, Mapping) else None
    fields = {
        CONFIG_SCHEMA: CONFIG_FIELDS,
        CONFIG_SCHEMA_V2: CONFIG_FIELDS_V2,
    }.get(schema)
    if fields is None:
        raise RuntimeArtifactManifestError("grant_service_config_invalid")
    raw = _exact_text_mapping(value, fields, "config")
    if raw["service_id"] != SERVICE_ID:
        raise RuntimeArtifactManifestError("grant_service_config_invalid")
    digest_fields = fields - {
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


def validate_installed_grant_service_config(value: Mapping[str, Any]) -> dict[str, str]:
    """Validate inert v3 metadata; archive admission deliberately rejects v3."""
    from .reddog_ed25519_signature_verifier_backend import decode_ed25519_public_key
    raw = _exact_text_mapping(value, CONFIG_FIELDS_V3, "installed_config")
    if raw["schema_version"] != CONFIG_SCHEMA_V3:
        raise RuntimeArtifactManifestError("grant_service_installed_config_invalid")
    for name in ("installed_runtime_descriptor_digest", "owner_config_id", "repo_root_digest"):
        if not is_sha256(raw[name]):
            raise RuntimeArtifactManifestError("grant_service_installed_config_invalid")
    # Reuse existing public identity validation without broadening archive schemas.
    common = {name: raw[name] for name in CONFIG_FIELDS - {"archive_digest"}}
    common.update(schema_version=CONFIG_SCHEMA, archive_digest=raw["installed_runtime_descriptor_digest"])
    validate_grant_service_config(common)
    if decode_ed25519_public_key(raw["public_key"]) is None:
        raise RuntimeArtifactManifestError("grant_service_installed_config_invalid")
    return raw


def _installed_packet(config_digest, descriptor_digest):
    from .reddog_grant_authority_installed_source_contract import (
        INSTALLED_SOURCE_FILENAME, INSTALLED_ENTRYPOINT, INSTALLED_DEPENDENCY_LOADER,
    )
    if not is_sha256(config_digest) or not is_sha256(descriptor_digest):
        raise RuntimeArtifactManifestError("grant_service_installed_run_packet_invalid")
    binding = {"config_digest": config_digest, "installed_runtime_descriptor_digest": descriptor_digest}
    return {"schema_version": RUN_PACKET_SCHEMA_V2, "service_id": SERVICE_ID,
        "config_filename": GRANT_AUTHORITY_SERVICE_CONFIG,
        "source_descriptor_filename": INSTALLED_SOURCE_FILENAME,
        "entrypoint": INSTALLED_ENTRYPOINT, "dependency_loader": INSTALLED_DEPENDENCY_LOADER,
        "artifact_set_digest": digest(binding), **binding}


def validate_installed_grant_service_run_packet(value, *, config_digest,
                                               installed_runtime_descriptor_digest):
    """Bind the grant config itself, never the target signer's config digest."""
    raw = _exact_text_mapping(value, RUN_PACKET_FIELDS_V2, "installed_run_packet")
    if raw != _installed_packet(config_digest, installed_runtime_descriptor_digest):
        raise RuntimeArtifactManifestError("grant_service_installed_run_packet_invalid")
    return raw


def compose_installed_grant_service_artifacts(*, profile, owner_config_id,
                                            repo_root_digest, source_descriptor):
    """Prepare three inert canonical artifacts; no writes, signatures or grants."""
    from .reddog_grant_authority_installed_source_contract import (
        INSTALLED_SOURCE_FILENAME, validate_installed_grant_source,
    )
    from .reddog_runtime_artifact_manifest_contract import GRANT_AUTHORITY_SERVICE_RUN_PACKET
    fields = CONFIG_FIELDS - {"schema_version", "service_id", "archive_digest"}
    identity = _exact_text_mapping(profile, fields, "installed_profile")
    descriptor = validate_installed_grant_source(source_descriptor)
    descriptor_bytes = canonical_json(descriptor).encode("ascii")
    descriptor_digest = raw_digest(descriptor_bytes)
    config = validate_installed_grant_service_config(dict(identity,
        schema_version=CONFIG_SCHEMA_V3, service_id=SERVICE_ID, owner_config_id=owner_config_id,
        repo_root_digest=repo_root_digest, installed_runtime_descriptor_digest=descriptor_digest))
    config_bytes = canonical_json(config).encode("ascii")
    packet = _installed_packet(raw_digest(config_bytes), descriptor_digest)
    artifacts = {GRANT_AUTHORITY_SERVICE_CONFIG: config_bytes,
        GRANT_AUTHORITY_SERVICE_RUN_PACKET: canonical_json(packet).encode("ascii"),
        INSTALLED_SOURCE_FILENAME: descriptor_bytes}
    validate_installed_grant_service_artifacts(artifacts)
    return artifacts


def validate_installed_grant_service_artifacts(artifacts):
    """Check a complete inert bundle; current runtime enrollment is still required."""
    from .reddog_grant_authority_installed_source_contract import (
        INSTALLED_SOURCE_FILENAME, validate_installed_grant_source,
    )
    from .reddog_runtime_artifact_manifest_contract import (
        GRANT_AUTHORITY_SERVICE_RUN_PACKET, MAX_ARTIFACT_BYTES,
    )
    expected = {GRANT_AUTHORITY_SERVICE_CONFIG, GRANT_AUTHORITY_SERVICE_RUN_PACKET, INSTALLED_SOURCE_FILENAME}
    if not isinstance(artifacts, Mapping) or set(artifacts) != expected:
        raise RuntimeArtifactManifestError("grant_service_installed_bundle_invalid")
    bodies = dict(artifacts)
    values = {name: _installed_json(body, MAX_ARTIFACT_BYTES) for name, body in bodies.items()}
    config = validate_installed_grant_service_config(values[GRANT_AUTHORITY_SERVICE_CONFIG])
    descriptor = validate_installed_grant_source(values[INSTALLED_SOURCE_FILENAME])
    descriptor_digest = raw_digest(bodies[INSTALLED_SOURCE_FILENAME])
    if config["installed_runtime_descriptor_digest"] != descriptor_digest:
        raise RuntimeArtifactManifestError("grant_service_installed_descriptor_mismatch")
    config_digest = raw_digest(bodies[GRANT_AUTHORITY_SERVICE_CONFIG])
    packet = validate_installed_grant_service_run_packet(values[GRANT_AUTHORITY_SERVICE_RUN_PACKET],
        config_digest=config_digest, installed_runtime_descriptor_digest=descriptor_digest)
    return {"config": config, "run_packet": packet, "source_descriptor": descriptor,
        "config_digest": config_digest, "installed_runtime_descriptor_digest": descriptor_digest,
        "run_packet_digest": raw_digest(bodies[GRANT_AUTHORITY_SERVICE_RUN_PACKET])}


def _installed_json(body, maximum):
    if type(body) is not bytes or not 0 < len(body) <= maximum:
        raise RuntimeArtifactManifestError("grant_service_installed_bundle_invalid")
    try:
        value = json.loads(body.decode("ascii"))
        if type(value) is not dict or canonical_json(value).encode("ascii") != body:
            raise ValueError("noncanonical")
        return value
    except (ValueError, TypeError, UnicodeError) as exc:
        raise RuntimeArtifactManifestError("grant_service_installed_bundle_invalid") from exc


__all__ = [
    "CONFIG_FIELDS", "CONFIG_FIELDS_V2", "CONFIG_SCHEMA", "CONFIG_SCHEMA_V2",
    "ENTRYPOINT", "RUN_PACKET_FIELDS", "SOURCE_POLICY_CONFIG_FIELDS",
    "RUN_PACKET_SCHEMA", "SERVICE_ID", "validate_grant_service_config",
    "validate_grant_service_run_packet",
    "CONFIG_SCHEMA_V3", "CONFIG_FIELDS_V3", "RUN_PACKET_SCHEMA_V2", "RUN_PACKET_FIELDS_V2",
    "validate_installed_grant_service_config", "validate_installed_grant_service_run_packet",
    "compose_installed_grant_service_artifacts", "validate_installed_grant_service_artifacts",
]
