"""Canonical contract for signed RedDog runtime-artifact manifests."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any, Mapping


SCHEMA_VERSION = "reddog_signed_runtime_artifact_manifest.v1"
SIGNING_OPERATION = "attest_reddog_runtime_artifact_manifest"
SIGNING_PREFIX = "reddog-runtime-artifact-manifest.v1."
SIGNER_ROLE = "reddog_runtime_artifact_manifest"
DEFAULT_MAX_TTL_SECONDS = 300
MAX_ARTIFACT_BYTES = 1024 * 1024
REQUIRED_RUNTIME_ARTIFACTS = (
    "authoritative_work_state.json",
    "authority_profile.json",
    "execution_valve_env.json",
    "permission_snapshots.json",
    "principal_authority_records.json",
    "signer_service_config.json",
    "signer_service_run_packet.json",
)
SIGNATURE_FIELDS = frozenset(
    {
        "signature",
        "signer_audit_mac",
        "signer_audit_attestation_signature",
    }
)
UNSIGNED_FIELDS = frozenset(
    {
        "schema_version",
        "manifest_id",
        "revision",
        "repo_root_digest",
        "runtime_root_digest",
        "queue_item_id",
        "work_state_revision",
        "work_authority_digest",
        "publication_receipt_id",
        "publication_binding_digest",
        "artifact_count",
        "artifact_generation_digest",
        "artifacts",
        "issuer_principal_id",
        "signer_public_key",
        "signer_key_fingerprint",
        "key_epoch",
        "consensus_receipt_digest",
        "authority_profile_digest",
        "authority_profile_source_receipt_id",
        "signer_service_config_digest",
        "nonce",
        "issued_at",
        "expires_at",
    }
)


class RuntimeArtifactManifestError(ValueError):
    """Fail-closed manifest contract violation."""


@dataclass(frozen=True)
class RuntimeArtifactDescriptor:
    filename: str
    byte_count: int
    content_digest: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def canonical_signing_input(payload: Mapping[str, Any]) -> str:
    """Return the only accepted Ed25519 signing input."""

    unsigned = {
        key: value
        for key, value in payload.items()
        if key not in SIGNATURE_FIELDS
    }
    validate_unsigned_payload(unsigned)
    return SIGNING_PREFIX + canonical_json(unsigned)


def validate_signed_payload(value: Mapping[str, Any]) -> dict[str, Any]:
    """Validate exact signed shape without granting authority."""

    if not isinstance(value, Mapping):
        raise RuntimeArtifactManifestError("manifest_not_mapping")
    payload = dict(value)
    unsigned = {
        key: item
        for key, item in payload.items()
        if key not in SIGNATURE_FIELDS
    }
    validate_unsigned_payload(unsigned)
    if set(payload) != set(unsigned) | SIGNATURE_FIELDS:
        raise RuntimeArtifactManifestError("manifest_signed_fields_invalid")
    for field in SIGNATURE_FIELDS:
        require_text(payload.get(field))
    return payload


def validate_unsigned_payload(value: Mapping[str, Any]) -> dict[str, Any]:
    """Validate exact unsigned schema, descriptors, ID, and ASCII boundary."""

    payload = dict(value)
    if set(payload) != UNSIGNED_FIELDS or not ascii_deep(payload):
        raise RuntimeArtifactManifestError("manifest_fields_invalid")
    if payload["schema_version"] != SCHEMA_VERSION:
        raise RuntimeArtifactManifestError("manifest_schema_invalid")
    _validate_descriptors(payload)
    for field in _digest_fields():
        if not is_sha256(payload.get(field)):
            raise RuntimeArtifactManifestError("manifest_digest_invalid")
    if not is_revision(payload.get("work_state_revision")):
        raise RuntimeArtifactManifestError("manifest_revision_invalid")
    for field in _text_fields():
        require_text(payload.get(field))
    if type(payload["issued_at"]) is not int or type(
        payload["expires_at"]
    ) is not int:
        raise RuntimeArtifactManifestError("manifest_time_invalid")
    expected = manifest_id_for(payload)
    if payload["manifest_id"] != expected or payload["revision"] != expected[7:]:
        raise RuntimeArtifactManifestError("manifest_id_invalid")
    return payload


def manifest_id_for(payload: Mapping[str, Any]) -> str:
    body = dict(payload)
    body.pop("manifest_id", None)
    body.pop("revision", None)
    for field in SIGNATURE_FIELDS:
        body.pop(field, None)
    return digest(body)


def validate_freshness(
    payload: Mapping[str, Any],
    *,
    now_epoch: int,
    max_ttl_seconds: int,
) -> None:
    issued = int(payload["issued_at"])
    expires = int(payload["expires_at"])
    ttl = expires - issued
    if (
        type(now_epoch) is not int
        or issued > now_epoch
        or expires <= now_epoch
        or ttl <= 0
        or ttl > max_ttl_seconds
    ):
        raise RuntimeArtifactManifestError("manifest_expired")


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )


def digest(value: Any) -> str:
    return raw_digest(canonical_json(value).encode("utf-8"))


def raw_digest(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def is_sha256(value: object) -> bool:
    text = str(value or "")
    return len(text) == 71 and text.startswith("sha256:") and all(
        char in "0123456789abcdef" for char in text[7:]
    )


def is_revision(value: object) -> bool:
    text = str(value or "")
    return len(text) == 64 and all(
        char in "0123456789abcdef" for char in text
    )


def require_text(value: object) -> str:
    if (
        not isinstance(value, str)
        or not value.strip()
        or not value.isascii()
        or len(value) > 1024
    ):
        raise RuntimeArtifactManifestError("manifest_text_invalid")
    return value.strip()


def ascii_deep(value: Any) -> bool:
    if isinstance(value, str):
        return value.isascii()
    if isinstance(value, Mapping):
        return all(
            isinstance(key, str)
            and key.isascii()
            and ascii_deep(item)
            for key, item in value.items()
        )
    if isinstance(value, (list, tuple)):
        return all(ascii_deep(item) for item in value)
    return value is None or isinstance(value, (bool, int, float))


def _validate_descriptors(payload: Mapping[str, Any]) -> None:
    artifacts = payload.get("artifacts")
    if (
        type(payload.get("artifact_count")) is not int
        or payload["artifact_count"] != len(REQUIRED_RUNTIME_ARTIFACTS)
        or not isinstance(artifacts, (list, tuple))
        or len(artifacts) != len(REQUIRED_RUNTIME_ARTIFACTS)
    ):
        raise RuntimeArtifactManifestError("manifest_artifacts_invalid")
    names: list[str] = []
    for item in artifacts:
        if not isinstance(item, Mapping) or set(item) != {
            "filename",
            "byte_count",
            "content_digest",
        }:
            raise RuntimeArtifactManifestError("manifest_descriptor_invalid")
        names.append(str(item["filename"]))
        if (
            type(item["byte_count"]) is not int
            or item["byte_count"] <= 0
            or not is_sha256(item["content_digest"])
        ):
            raise RuntimeArtifactManifestError("manifest_descriptor_invalid")
    if tuple(names) != REQUIRED_RUNTIME_ARTIFACTS:
        raise RuntimeArtifactManifestError("manifest_artifact_set_invalid")
    if payload.get("artifact_generation_digest") != digest(artifacts):
        raise RuntimeArtifactManifestError(
            "manifest_artifact_generation_invalid"
        )


def _digest_fields() -> tuple[str, ...]:
    return (
        "repo_root_digest",
        "runtime_root_digest",
        "work_authority_digest",
        "publication_receipt_id",
        "publication_binding_digest",
        "consensus_receipt_digest",
        "authority_profile_digest",
        "authority_profile_source_receipt_id",
        "signer_service_config_digest",
        "artifact_generation_digest",
    )


def _text_fields() -> tuple[str, ...]:
    return (
        "manifest_id",
        "queue_item_id",
        "issuer_principal_id",
        "signer_public_key",
        "signer_key_fingerprint",
        "key_epoch",
        "nonce",
    )


__all__ = [
    "DEFAULT_MAX_TTL_SECONDS",
    "MAX_ARTIFACT_BYTES",
    "REQUIRED_RUNTIME_ARTIFACTS",
    "RuntimeArtifactDescriptor",
    "RuntimeArtifactManifestError",
    "SCHEMA_VERSION",
    "SIGNATURE_FIELDS",
    "SIGNER_ROLE",
    "SIGNING_OPERATION",
    "SIGNING_PREFIX",
    "ascii_deep",
    "canonical_json",
    "canonical_signing_input",
    "digest",
    "is_revision",
    "is_sha256",
    "manifest_id_for",
    "raw_digest",
    "require_text",
    "validate_freshness",
    "validate_signed_payload",
    "validate_unsigned_payload",
]
