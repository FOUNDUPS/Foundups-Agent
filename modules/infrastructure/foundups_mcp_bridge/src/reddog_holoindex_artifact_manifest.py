"""Exact artifact-manifest validation and per-file copy proofs."""

from __future__ import annotations

import os
import posixpath
import stat
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from .reddog_holoindex_acceptance_guards import (
    AcceptanceGuardError,
    _fail,
    _is_link_or_reparse,
    _reject_link_components,
)
from .reddog_holoindex_acceptance_model_descriptors import DescriptorCopyProof


@dataclass(frozen=True)
class ExpectedArtifactFile:
    relative_path: str
    size: int
    sha256: str


@dataclass(frozen=True)
class ArtifactFileProof:
    relative_path: str
    size: int
    source_before_sha256: str
    source_after_sha256: str
    destination_sha256: str


@dataclass(frozen=True)
class ModelCopyLimits:
    max_files: int
    max_file_bytes: int
    max_total_bytes: int

    def validate(self) -> None:
        values = (self.max_files, self.max_file_bytes, self.max_total_bytes)
        if any(type(value) is not int or value <= 0 for value in values):
            _fail("MODEL_COPY_LIMIT_INVALID")


@dataclass(frozen=True)
class ModelCopyProof:
    source_digest: str
    destination_digest: str
    file_count: int
    total_bytes: int
    relative_files: tuple[str, ...]
    files: tuple[ArtifactFileProof, ...] = ()


@dataclass(frozen=True)
class ArtifactSnapshot:
    files: list[tuple[str, Path, os.stat_result]]
    directories: dict[Path, os.stat_result]


def snapshot_artifact_files(source: Path, limits: ModelCopyLimits) -> ArtifactSnapshot:
    limits.validate()
    _reject_link_components(source)
    try:
        root_metadata = os.lstat(source)
    except OSError as exc:
        raise AcceptanceGuardError("MODEL_SOURCE_UNAVAILABLE") from exc
    if not stat.S_ISDIR(root_metadata.st_mode) or _is_link_or_reparse(source, root_metadata):
        _fail("MODEL_SOURCE_NOT_DIRECTORY")
    files: list[tuple[str, Path, os.stat_result]] = []
    directories = {source: root_metadata}
    pending = [source]
    while pending:
        _scan_directory(source, pending.pop(), pending, directories, files)
    files.sort(key=lambda item: _normalized_path_key(item[0]))
    _validate_snapshot_bounds(files, limits)
    return ArtifactSnapshot(files, directories)


def _scan_directory(
    root: Path, directory: Path, pending: list[Path],
    directories: dict[Path, os.stat_result],
    files: list[tuple[str, Path, os.stat_result]],
) -> None:
    try:
        entries = sorted(os.scandir(directory), key=lambda item: item.name)
    except OSError as exc:
        raise AcceptanceGuardError("MODEL_ENUMERATION_FAILED") from exc
    next_directories: list[Path] = []
    for entry in entries:
        candidate = Path(entry.path)
        try:
            metadata = os.lstat(candidate)
        except OSError as exc:
            raise AcceptanceGuardError("MODEL_ENUMERATION_CHANGED") from exc
        if _is_link_or_reparse(candidate, metadata):
            _fail("MODEL_LINK_OR_REPARSE_REJECTED")
        if stat.S_ISDIR(metadata.st_mode):
            directories[candidate] = metadata
            next_directories.append(candidate)
        elif stat.S_ISREG(metadata.st_mode) and int(getattr(metadata, "st_nlink", 1)) == 1:
            files.append((candidate.relative_to(root).as_posix(), candidate, metadata))
        else:
            _fail("MODEL_SPECIAL_FILE_REJECTED")
    pending.extend(reversed(next_directories))


def _validate_snapshot_bounds(
    files: list[tuple[str, Path, os.stat_result]], limits: ModelCopyLimits
) -> None:
    if not files or len(files) > limits.max_files:
        _fail("MODEL_FILE_COUNT_BOUND")
    total = 0
    for _, _, metadata in files:
        size = int(metadata.st_size)
        if size > limits.max_file_bytes:
            _fail("MODEL_FILE_SIZE_BOUND")
        total += size
        if total > limits.max_total_bytes:
            _fail("MODEL_TOTAL_SIZE_BOUND")


def validate_expected_manifest(
    snapshot_files: Iterable[tuple[str, Path, Any]],
    expected_manifest: tuple[ExpectedArtifactFile, ...] | None,
) -> dict[str, ExpectedArtifactFile]:
    if expected_manifest is None:
        return {}
    if type(expected_manifest) is not tuple or not expected_manifest:
        _fail("MODEL_EXPECTED_MANIFEST_INVALID")
    if not all(_valid_manifest_item(item) for item in expected_manifest):
        _fail("MODEL_EXPECTED_MANIFEST_INVALID")
    keys = tuple(_normalized_path_key(item.relative_path) for item in expected_manifest)
    ordered = tuple(sorted(keys))
    if keys != ordered or len(set(keys)) != len(keys):
        _fail("MODEL_EXPECTED_MANIFEST_INVALID")
    actual = tuple((relative, int(metadata.st_size)) for relative, _, metadata in snapshot_files)
    expected = tuple((item.relative_path, item.size) for item in expected_manifest)
    if actual != expected:
        _fail("MODEL_EXPECTED_MANIFEST_MISMATCH")
    return {item.relative_path: item for item in expected_manifest}


def _normalized_path_key(value: str) -> str:
    normalized = posixpath.normpath(value.replace("\\", "/"))
    return unicodedata.normalize("NFC", normalized).casefold()


def _valid_manifest_item(item: ExpectedArtifactFile) -> bool:
    return bool(
        isinstance(item, ExpectedArtifactFile)
        and type(item.relative_path) is str
        and item.relative_path
        and not item.relative_path.startswith("/")
        and "\\" not in item.relative_path
        and ".." not in Path(item.relative_path).parts
        and posixpath.normpath(item.relative_path) == item.relative_path
        and type(item.size) is int
        and item.size >= 0
        and type(item.sha256) is str
        and len(item.sha256) == 71
        and item.sha256.startswith("sha256:")
        and all(character in "0123456789abcdef" for character in item.sha256[7:])
    )


def build_file_proof(
    relative: str,
    descriptor_proof: DescriptorCopyProof,
    expected: ExpectedArtifactFile | None,
) -> ArtifactFileProof:
    if expected is not None and descriptor_proof.source_before_sha256 != expected.sha256:
        _fail("MODEL_EXPECTED_DIGEST_MISMATCH")
    return ArtifactFileProof(
        relative_path=relative,
        size=descriptor_proof.copied_bytes,
        source_before_sha256=descriptor_proof.source_before_sha256,
        source_after_sha256=descriptor_proof.source_after_sha256,
        destination_sha256=descriptor_proof.destination_sha256,
    )


__all__ = [
    "ArtifactSnapshot",
    "ArtifactFileProof",
    "ExpectedArtifactFile",
    "ModelCopyLimits",
    "ModelCopyProof",
    "build_file_proof",
    "snapshot_artifact_files",
    "validate_expected_manifest",
]
