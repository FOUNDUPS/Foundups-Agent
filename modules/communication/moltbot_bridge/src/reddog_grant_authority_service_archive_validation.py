"""Fail-closed executable and dependency-closure validation for grant PYZ bytes."""

from __future__ import annotations

import io
import json
import stat
import zipfile
from types import MappingProxyType
from typing import Any, Mapping

from modules.communication.moltbot_bridge.src.reddog_grant_authority_service_archive_contract import (
    ARCHIVE_MAIN,
    ARCHIVE_MANIFEST,
    MAX_ARCHIVE_BYTES,
    MAX_ARCHIVE_CONTENT_BYTES,
    MAX_ARCHIVE_FILE_BYTES,
    MAX_ARCHIVE_FILES,
    canonical_archive_bytes,
    validate_archive_manifest,
    valid_archive_path,
)
from modules.communication.moltbot_bridge.src.reddog_grant_authority_service_import_closure import (
    validate_grant_service_static_imports,
)
from modules.communication.moltbot_bridge.src.reddog_runtime_artifact_manifest_contract import (
    RuntimeArtifactManifestError,
    canonical_json,
    raw_digest,
)


def validate_grant_service_archive(raw: bytes) -> Mapping[str, Any]:
    """Verify canonical ZIP bytes, entrypoint, members, and Python import closure."""

    entries = _read_canonical_entries(raw)
    manifest = _manifest(entries)
    _verify_descriptors(entries, manifest)
    validate_grant_service_static_imports(entries)
    return MappingProxyType(manifest)


def _read_canonical_entries(raw: bytes) -> dict[str, bytes]:
    if not isinstance(raw, bytes) or not raw or len(raw) > MAX_ARCHIVE_BYTES:
        raise RuntimeArtifactManifestError("grant_service_archive_invalid")
    try:
        with zipfile.ZipFile(io.BytesIO(raw), "r") as archive:
            if archive.comment:
                raise ValueError("archive comment")
            infos = archive.infolist()
            if not 3 <= len(infos) <= MAX_ARCHIVE_FILES + 1:
                raise ValueError("archive member count")
            names = tuple(item.filename for item in infos)
            if names != tuple(sorted(names)) or len(set(names)) != len(names):
                raise ValueError("archive ordering")
            if ARCHIVE_MANIFEST not in names:
                raise ValueError("archive manifest")
            entries = {item.filename: _read_member(archive, item) for item in infos}
    except (OSError, ValueError, zipfile.BadZipFile, RuntimeError) as exc:
        raise RuntimeArtifactManifestError("grant_service_archive_invalid") from exc
    payload_bytes = sum(
        len(body) for path, body in entries.items() if path != ARCHIVE_MANIFEST
    )
    if payload_bytes > MAX_ARCHIVE_CONTENT_BYTES:
        raise RuntimeArtifactManifestError("grant_service_archive_invalid")
    if canonical_archive_bytes(entries) != raw:
        raise RuntimeArtifactManifestError("grant_service_archive_noncanonical")
    return entries


def _read_member(archive: zipfile.ZipFile, item: zipfile.ZipInfo) -> bytes:
    mode = item.external_attr >> 16
    if (
        not valid_archive_path(item.filename)
        or item.is_dir()
        or item.compress_type != zipfile.ZIP_STORED
        or item.flag_bits & 0x1
        or item.extra
        or item.comment
        or item.create_system != 3
        or item.file_size > MAX_ARCHIVE_FILE_BYTES
        or not stat.S_ISREG(mode)
        or stat.S_IMODE(mode) != 0o444
    ):
        raise ValueError("unsafe archive member")
    return archive.read(item)


def _manifest(entries: Mapping[str, bytes]) -> dict[str, Any]:
    try:
        raw = entries[ARCHIVE_MANIFEST]
        value = json.loads(raw.decode("ascii"))
        checked = validate_archive_manifest(value)
    except (KeyError, UnicodeDecodeError, TypeError, ValueError) as exc:
        raise RuntimeArtifactManifestError("grant_service_archive_manifest_invalid") from exc
    if raw != canonical_json(checked).encode("ascii"):
        raise RuntimeArtifactManifestError("grant_service_archive_manifest_invalid")
    return checked


def _verify_descriptors(
    entries: Mapping[str, bytes], manifest: Mapping[str, Any]
) -> None:
    expected = {ARCHIVE_MANIFEST, *(item["path"] for item in manifest["files"])}
    if set(entries) != expected or entries.get("__main__.py") != ARCHIVE_MAIN:
        raise RuntimeArtifactManifestError("grant_service_archive_entrypoint_invalid")
    for item in manifest["files"]:
        body = entries[item["path"]]
        if len(body) != item["byte_count"] or raw_digest(body) != item["content_digest"]:
            raise RuntimeArtifactManifestError("grant_service_archive_member_changed")


__all__ = ["validate_grant_service_archive"]
