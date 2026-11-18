"""Deterministic archive contract for the isolated grant-authority service."""

from __future__ import annotations

import io
import stat
import zipfile
from pathlib import PurePosixPath
from typing import Any, Mapping

from modules.communication.moltbot_bridge.src.reddog_runtime_artifact_manifest_contract import (
    RuntimeArtifactManifestError,
    canonical_json,
    digest,
    is_sha256,
    raw_digest,
)

ARCHIVE_SCHEMA = "reddog_grant_authority_service_archive.v1"
ARCHIVE_MANIFEST = "grant_authority_archive_manifest.json"
ARCHIVE_ENTRYPOINT = "reddog_grant_authority_service:main"
ARCHIVE_MAIN = (
    b"from reddog_grant_authority_service import main\n\n"
    b"raise SystemExit(main())\n"
)
ARCHIVE_TIMESTAMP = (1980, 1, 1, 0, 0, 0)
ARCHIVE_MODE = stat.S_IFREG | 0o444
MAX_ARCHIVE_FILES = 512
MAX_ARCHIVE_FILE_BYTES = 1024 * 1024
MAX_ARCHIVE_CONTENT_BYTES = 8 * 1024 * 1024
MAX_ARCHIVE_BYTES = 10 * 1024 * 1024


def build_grant_service_archive(
    files: Mapping[str, bytes], *, source_commit_sha: str
) -> bytes:
    """Build the only canonical ZIP_STORED archive accepted by the verifier."""
    payloads = validated_archive_payloads(files)
    descriptors = tuple(
        {
            "path": path,
            "byte_count": len(body),
            "content_digest": raw_digest(body),
        }
        for path, body in payloads.items()
    )
    source_digest = digest(
        {
            "claimed_source_commit_sha": source_commit_sha,
            "files": descriptors,
        }
    )
    manifest = {
        "schema_version": ARCHIVE_SCHEMA,
        "archive_manifest_id": "",
        "entrypoint": ARCHIVE_ENTRYPOINT,
        "claimed_source_commit_sha": source_commit_sha,
        "archive_source_descriptor_digest": source_digest,
        "file_count": len(descriptors),
        "files": descriptors,
    }
    manifest["archive_manifest_id"] = _manifest_id(manifest)
    manifest = validate_archive_manifest(manifest)
    entries = {
        ARCHIVE_MANIFEST: canonical_json(manifest).encode("ascii"),
        **payloads,
    }
    return _canonical_zip(entries)


def validate_archive_manifest(value: Mapping[str, Any]) -> dict[str, Any]:
    """Validate exact manifest shape, ordering, digests, and source identity."""
    fields = {
        "schema_version", "archive_manifest_id", "entrypoint",
        "claimed_source_commit_sha", "archive_source_descriptor_digest",
        "file_count", "files",
    }
    raw = dict(value) if isinstance(value, Mapping) else {}
    files = raw.get("files")
    if (
        set(raw) != fields
        or raw.get("schema_version") != ARCHIVE_SCHEMA
        or raw.get("entrypoint") != ARCHIVE_ENTRYPOINT
        or not _commit_sha(raw.get("claimed_source_commit_sha"))
        or type(raw.get("file_count")) is not int
        or not isinstance(files, (list, tuple))
        or raw.get("file_count") != len(files)
        or not 2 <= len(files) <= MAX_ARCHIVE_FILES
    ):
        raise RuntimeArtifactManifestError("grant_service_archive_manifest_invalid")
    descriptors = tuple(_descriptor(item) for item in files)
    paths = tuple(item["path"] for item in descriptors)
    if paths != tuple(sorted(paths)) or len(set(paths)) != len(paths):
        raise RuntimeArtifactManifestError("grant_service_archive_manifest_invalid")
    expected_tree = digest(
        {
            "claimed_source_commit_sha": raw["claimed_source_commit_sha"],
            "files": descriptors,
        }
    )
    if (
        raw.get("archive_source_descriptor_digest") != expected_tree
        or not is_sha256(expected_tree)
    ):
        raise RuntimeArtifactManifestError("grant_service_archive_manifest_invalid")
    normalized = {**raw, "files": list(descriptors)}
    if normalized["archive_manifest_id"] != _manifest_id(normalized):
        raise RuntimeArtifactManifestError("grant_service_archive_manifest_invalid")
    return normalized


def canonical_archive_bytes(entries: Mapping[str, bytes]) -> bytes:
    """Rebuild parsed entries so validation can reject alternate ZIP encodings."""
    return _canonical_zip(entries)


def valid_archive_path(value: object) -> bool:
    text = value if isinstance(value, str) else ""
    path = PurePosixPath(text)
    return bool(
        text
        and text.isascii()
        and all(33 <= ord(char) <= 126 for char in text)
        and len(text) <= 240
        and "\\" not in text
        and not path.is_absolute()
        and path.parts
        and all(part not in {"", ".", ".."} for part in path.parts)
        and (text == ARCHIVE_MANIFEST or text.endswith(".py") and all(
            part.isidentifier() for part in (*path.parts[:-1], path.name[:-3])
        ))
        and text == path.as_posix()
    )


def validated_archive_payloads(files: Mapping[str, bytes]) -> dict[str, bytes]:
    raw = dict(files) if isinstance(files, Mapping) else {}
    if set(raw) == {ARCHIVE_MANIFEST} or ARCHIVE_MANIFEST in raw:
        raise RuntimeArtifactManifestError("grant_service_archive_files_invalid")
    if raw.get("__main__.py") != ARCHIVE_MAIN:
        raise RuntimeArtifactManifestError("grant_service_archive_entrypoint_invalid")
    if "reddog_grant_authority_service.py" not in raw:
        raise RuntimeArtifactManifestError("grant_service_archive_entrypoint_invalid")
    if not 2 <= len(raw) <= MAX_ARCHIVE_FILES:
        raise RuntimeArtifactManifestError("grant_service_archive_files_invalid")
    ordered = {path: raw[path] for path in sorted(raw)}
    if any(
        not valid_archive_path(path)
        or not path.endswith(".py")
        or not isinstance(body, bytes)
        or not body
        or len(body) > MAX_ARCHIVE_FILE_BYTES
        for path, body in ordered.items()
    ) or sum(map(len, ordered.values())) > MAX_ARCHIVE_CONTENT_BYTES:
        raise RuntimeArtifactManifestError("grant_service_archive_files_invalid")
    return ordered


def _descriptor(value: object) -> dict[str, Any]:
    fields = {"path", "byte_count", "content_digest"}
    item = dict(value) if isinstance(value, Mapping) else {}
    if (
        set(item) != fields
        or not valid_archive_path(item.get("path"))
        or item.get("path") == ARCHIVE_MANIFEST
        or type(item.get("byte_count")) is not int
        or not 0 < item["byte_count"] <= MAX_ARCHIVE_FILE_BYTES
        or not is_sha256(item.get("content_digest"))
    ):
        raise RuntimeArtifactManifestError("grant_service_archive_manifest_invalid")
    return item


def _canonical_zip(entries: Mapping[str, bytes]) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_STORED) as archive:
        for path in sorted(entries):
            info = zipfile.ZipInfo(path, ARCHIVE_TIMESTAMP)
            info.create_system = 3
            info.external_attr = ARCHIVE_MODE << 16
            archive.writestr(info, entries[path])
    return output.getvalue()


def _manifest_id(value: Mapping[str, Any]) -> str:
    body = dict(value)
    body.pop("archive_manifest_id", None)
    return digest(body)


def _commit_sha(value: object) -> bool:
    text = value if isinstance(value, str) else ""
    return len(text) in {40, 64} and all(char in "0123456789abcdef" for char in text)


__all__ = [
    "ARCHIVE_ENTRYPOINT", "ARCHIVE_MAIN", "ARCHIVE_MANIFEST", "ARCHIVE_SCHEMA",
    "MAX_ARCHIVE_BYTES", "MAX_ARCHIVE_CONTENT_BYTES", "MAX_ARCHIVE_FILE_BYTES", "MAX_ARCHIVE_FILES",
    "build_grant_service_archive", "canonical_archive_bytes", "validate_archive_manifest", "valid_archive_path", "validated_archive_payloads",
]
