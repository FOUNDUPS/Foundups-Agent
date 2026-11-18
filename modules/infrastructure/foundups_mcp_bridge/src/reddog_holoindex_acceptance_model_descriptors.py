"""Descriptor-level copying and hashing for isolated model snapshots."""

from __future__ import annotations

import hashlib
import json
import os
import stat
from pathlib import Path
from dataclasses import dataclass
from typing import Protocol

from .reddog_holoindex_acceptance_guards import AcceptanceGuardError, _fail


class CopyLimits(Protocol):
    max_file_bytes: int
    max_total_bytes: int


@dataclass(frozen=True)
class DescriptorCopyProof:
    copied_bytes: int
    source_before_sha256: str
    source_after_sha256: str
    destination_sha256: str


def _descriptor_sha256(descriptor: int) -> str:
    digest = hashlib.sha256()
    os.lseek(descriptor, 0, os.SEEK_SET)
    for block in iter(lambda: os.read(descriptor, 1024 * 1024), b""):
        digest.update(block)
    return "sha256:" + digest.hexdigest()


def _after_source_before_hash(_descriptor: int) -> None:
    """Trusted no-op seam for deterministic source-mutation tests."""


def _copy_stream(
    source_fd: int,
    target_fd: int,
    *,
    limits: CopyLimits,
    total_before: int,
) -> int:
    copied = 0
    while True:
        block = os.read(source_fd, 1024 * 1024)
        if not block:
            return copied
        next_file_bytes = copied + len(block)
        if next_file_bytes > limits.max_file_bytes:
            _fail("MODEL_FILE_SIZE_BOUND")
        if total_before + next_file_bytes > limits.max_total_bytes:
            _fail("MODEL_TOTAL_SIZE_BOUND")
        view = memoryview(block)
        while view:
            written = os.write(target_fd, view)
            if written <= 0:
                _fail("MODEL_COPY_INCOMPLETE")
            view = view[written:]
        copied = next_file_bytes


def file_identity(metadata: os.stat_result) -> tuple[int, int, int, int, int]:
    return (
        int(metadata.st_dev),
        int(metadata.st_ino),
        int(metadata.st_size),
        int(metadata.st_mtime_ns),
        int(getattr(metadata, "st_nlink", 1)),
    )


def copy_descriptors(
    source_fd: int,
    target_fd: int,
    expected: os.stat_result,
    *,
    limits: CopyLimits,
    total_before: int,
) -> DescriptorCopyProof:
    opened = os.fstat(source_fd)
    if (
        file_identity(opened) != file_identity(expected)
        or not stat.S_ISREG(opened.st_mode)
        or int(getattr(opened, "st_nlink", 1)) != 1
    ):
        _fail("MODEL_SOURCE_CHANGED")
    source_before = _descriptor_sha256(source_fd)
    _after_source_before_hash(source_fd)
    os.lseek(source_fd, 0, os.SEEK_SET)
    copied = _copy_stream(
        source_fd, target_fd, limits=limits, total_before=total_before
    )
    os.fsync(target_fd)
    source_after = _descriptor_sha256(source_fd)
    if file_identity(opened) != file_identity(os.fstat(source_fd)):
        _fail("MODEL_SOURCE_CHANGED")
    target_metadata = os.fstat(target_fd)
    if (
        not stat.S_ISREG(target_metadata.st_mode)
        or int(getattr(target_metadata, "st_nlink", 1)) != 1
        or int(target_metadata.st_size) != copied
    ):
        _fail("MODEL_COPY_INCOMPLETE")
    destination = _descriptor_sha256(target_fd)
    if source_before != source_after or source_after != destination:
        _fail("MODEL_SOURCE_CHANGED")
    return DescriptorCopyProof(
        copied_bytes=copied,
        source_before_sha256=source_before,
        source_after_sha256=source_after,
        destination_sha256=destination,
    )


def copy_one_posix(
    source: Path,
    target: Path,
    expected: os.stat_result,
    *,
    limits: CopyLimits,
    total_before: int,
) -> DescriptorCopyProof:
    read_flags = (
        os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    )
    write_flags = (
        os.O_WRONLY
        | os.O_CREAT
        | os.O_EXCL
        | getattr(os, "O_BINARY", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    source_fd = os.open(source, read_flags)
    try:
        target_fd = os.open(target, write_flags, 0o600)
    except BaseException:
        os.close(source_fd)
        raise
    try:
        return copy_descriptors(
            source_fd,
            target_fd,
            expected,
            limits=limits,
            total_before=total_before,
        )
    finally:
        os.close(target_fd)
        os.close(source_fd)


def descriptor_artifact_digest(
    relative_files: tuple[str, ...], descriptors: list[int]
) -> str:
    if len(relative_files) != len(descriptors) or not descriptors:
        _fail("MODEL_DIGEST_MISMATCH")
    manifest = []
    for relative, descriptor in zip(relative_files, descriptors):
        metadata = os.fstat(descriptor)
        digest = hashlib.sha256()
        os.lseek(descriptor, 0, os.SEEK_SET)
        for block in iter(lambda: os.read(descriptor, 1024 * 1024), b""):
            digest.update(block)
        manifest.append(
            {
                "path": relative,
                "size": int(metadata.st_size),
                "sha256": digest.hexdigest(),
            }
        )
    payload = json.dumps(manifest, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


__all__ = [
    "DescriptorCopyProof",
    "copy_descriptors",
    "copy_one_posix",
    "descriptor_artifact_digest",
    "file_identity",
]
