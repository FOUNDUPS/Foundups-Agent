"""Canonical exact-Git provenance contract for grant-service archives."""

from __future__ import annotations

from typing import Any, Mapping

from modules.communication.moltbot_bridge.src.reddog_grant_authority_service_archive_contract import (
    ARCHIVE_ENTRYPOINT,
    ARCHIVE_MAIN,
    ARCHIVE_MANIFEST,
    MAX_ARCHIVE_FILE_BYTES,
    MAX_ARCHIVE_FILES,
    canonical_archive_bytes,
    valid_archive_path,
    validated_archive_payloads,
)
from modules.communication.moltbot_bridge.src.reddog_runtime_artifact_manifest_contract import (
    RuntimeArtifactManifestError,
    canonical_json,
    digest,
    is_sha256,
    raw_digest,
)
from modules.infrastructure.wre_core.src.wre_git_tree_manifest import (
    portable_git_path,
)

ARCHIVE_SCHEMA_V2 = "reddog_grant_authority_service_archive.v2"
CANONICAL_ENTRYPOINT_SOURCE = "builtin:grant-authority-entrypoint.v1"
_FIELDS = {
    "schema_version", "archive_manifest_id", "entrypoint",
    "source_commit_sha", "source_object_format",
    "archive_source_descriptor_digest", "file_count", "files",
}
_DESCRIPTOR_FIELDS = {
    "path", "byte_count", "content_digest", "source_kind", "source_path",
    "source_object_id",
}

def build_git_provenance_grant_service_archive(
    files: Mapping[str, bytes], *, source_commit_sha: str,
    source_object_format: str, source_bindings: Mapping[str, Mapping[str, str]],
) -> bytes:
    """Build canonical v2 bytes from independently loaded exact Git blobs."""
    payloads = validated_archive_payloads(files)
    if set(source_bindings) != set(payloads) - {"__main__.py"}:
        raise RuntimeArtifactManifestError(
            "grant_service_archive_source_binding_invalid"
        )
    descriptors = tuple(
        _source_descriptor(path, body, source_bindings)
        for path, body in payloads.items()
    )
    manifest = _manifest(
        descriptors, source_commit_sha=source_commit_sha,
        source_object_format=source_object_format,
    )
    entries = {
        ARCHIVE_MANIFEST: canonical_json(manifest).encode("ascii"), **payloads,
    }
    return canonical_archive_bytes(entries)

def validate_git_provenance_archive_manifest(
    value: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate exact v2 shape, provenance descriptors, and digest lineage."""
    raw = dict(value) if isinstance(value, Mapping) else {}
    files = raw.get("files")
    if not _valid_manifest_shape(raw, files):
        raise RuntimeArtifactManifestError("grant_service_archive_manifest_invalid")
    object_format = str(raw["source_object_format"])
    descriptors = tuple(_descriptor(item, object_format) for item in files)
    _validate_order(descriptors)
    normalized = {**raw, "files": list(descriptors)}
    if (
        raw["archive_source_descriptor_digest"]
        != _source_digest(raw, descriptors)
        or raw["archive_manifest_id"] != _manifest_id(normalized)
    ):
        raise RuntimeArtifactManifestError("grant_service_archive_manifest_invalid")
    return normalized

def _manifest(
    descriptors: tuple[dict[str, Any], ...], *, source_commit_sha: str,
    source_object_format: str,
) -> dict[str, Any]:
    value = {
        "schema_version": ARCHIVE_SCHEMA_V2,
        "archive_manifest_id": "", "entrypoint": ARCHIVE_ENTRYPOINT,
        "source_commit_sha": source_commit_sha,
        "source_object_format": source_object_format,
        "archive_source_descriptor_digest": "",
        "file_count": len(descriptors), "files": descriptors,
    }
    value["archive_source_descriptor_digest"] = _source_digest(
        value, descriptors
    )
    value["archive_manifest_id"] = _manifest_id(value)
    return validate_git_provenance_archive_manifest(value)

def _source_descriptor(
    path: str, body: bytes, bindings: Mapping[str, Mapping[str, str]],
) -> dict[str, Any]:
    if path == "__main__.py":
        if path in bindings:
            raise RuntimeArtifactManifestError(
                "grant_service_archive_source_binding_invalid"
            )
        source = {
            "source_kind": "canonical_entrypoint",
            "source_path": CANONICAL_ENTRYPOINT_SOURCE,
            "source_object_id": raw_digest(ARCHIVE_MAIN),
        }
    else:
        value = bindings.get(path)
        source = dict(value) if isinstance(value, Mapping) else {}
        source["source_kind"] = "git_blob"
    return {
        "path": path, "byte_count": len(body),
        "content_digest": raw_digest(body), **source,
    }

def _descriptor(value: object, object_format: str) -> dict[str, Any]:
    item = dict(value) if isinstance(value, Mapping) else {}
    if (
        set(item) != _DESCRIPTOR_FIELDS or not valid_archive_path(item.get("path"))
        or item.get("path") == ARCHIVE_MANIFEST
        or type(item.get("byte_count")) is not int or item["byte_count"] <= 0
        or item["byte_count"] > MAX_ARCHIVE_FILE_BYTES
        or not is_sha256(item.get("content_digest"))
        or not _valid_source(item, object_format)
    ):
        raise RuntimeArtifactManifestError("grant_service_archive_manifest_invalid")
    return item

def _valid_source(item: Mapping[str, Any], object_format: str) -> bool:
    if item["path"] == "__main__.py":
        return bool(
            item["source_kind"] == "canonical_entrypoint"
            and item["source_path"] == CANONICAL_ENTRYPOINT_SOURCE
            and item["source_object_id"] == raw_digest(ARCHIVE_MAIN)
        )
    length = 40 if object_format == "sha1" else 64
    source_path = item["source_path"]
    object_id = item["source_object_id"]
    return bool(
        item["source_kind"] == "git_blob"
        and isinstance(source_path, str) and portable_git_path(source_path)
        and isinstance(object_id, str) and len(object_id) == length
        and all(char in "0123456789abcdef" for char in object_id)
    )


def _valid_manifest_shape(raw: Mapping[str, Any], files: object) -> bool:
    sha = raw.get("source_commit_sha")
    return bool(
        set(raw) == _FIELDS and raw.get("schema_version") == ARCHIVE_SCHEMA_V2
        and raw.get("entrypoint") == ARCHIVE_ENTRYPOINT
        and isinstance(sha, str) and len(sha) in {40, 64}
        and all(char in "0123456789abcdef" for char in sha)
        and raw.get("source_object_format") in {"sha1", "sha256"}
        and len(sha) == (40 if raw.get("source_object_format") == "sha1" else 64)
        and type(raw.get("file_count")) is int
        and isinstance(files, (list, tuple))
        and raw["file_count"] == len(files)
        and 2 <= len(files) <= MAX_ARCHIVE_FILES
    )

def _validate_order(descriptors: tuple[dict[str, Any], ...]) -> None:
    paths = tuple(item["path"] for item in descriptors)
    sources = tuple(
        item["source_path"] for item in descriptors
        if item["source_kind"] == "git_blob"
    )
    if paths != tuple(sorted(paths)) or len(set(paths)) != len(paths) or len(
        set(sources)
    ) != len(sources):
        raise RuntimeArtifactManifestError("grant_service_archive_manifest_invalid")


def _source_digest(
    value: Mapping[str, Any], files: tuple[dict[str, Any], ...],
) -> str:
    return digest({
        "source_commit_sha": value["source_commit_sha"],
        "source_object_format": value["source_object_format"], "files": files,
    })


def _manifest_id(value: Mapping[str, Any]) -> str:
    body = dict(value)
    body.pop("archive_manifest_id", None)
    return digest(body)


__all__ = [
    "ARCHIVE_SCHEMA_V2", "CANONICAL_ENTRYPOINT_SOURCE",
    "build_git_provenance_grant_service_archive",
    "validate_git_provenance_archive_manifest",
]
