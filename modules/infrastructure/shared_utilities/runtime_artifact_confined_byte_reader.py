"""One-descriptor confined byte reads with an explicit caller bound."""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ConfinedFileIdentity:
    device: int
    inode: int
    mode: int
    links: int
    size: int
    modified_ns: int
    changed_ns: int
    attributes: int


@dataclass(frozen=True)
class ConfinedFileDigestProof:
    digest: str
    size: int
    identity: ConfinedFileIdentity


def confined_file_identity(metadata: os.stat_result) -> ConfinedFileIdentity:
    """Capture the fields that must remain stable around one descriptor read."""

    return ConfinedFileIdentity(
        device=int(metadata.st_dev),
        inode=int(metadata.st_ino),
        mode=int(metadata.st_mode),
        links=int(getattr(metadata, "st_nlink", 0)),
        size=int(metadata.st_size),
        modified_ns=int(metadata.st_mtime_ns),
        changed_ns=int(metadata.st_ctime_ns),
        attributes=int(getattr(metadata, "st_file_attributes", 0)),
    )


def _descriptor_identity_matches(
    metadata: os.stat_result, expected: ConfinedFileIdentity,
) -> bool:
    """Compare handle fields; Windows handle ctime is not path lstat ctime."""

    observed = confined_file_identity(metadata)
    return bool(
        observed.device == expected.device
        and observed.inode == expected.inode
        and observed.mode == expected.mode
        and observed.links == expected.links
        and observed.size == expected.size
        and observed.modified_ns == expected.modified_ns
        and observed.attributes == expected.attributes
    )


def secure_read_confined_bytes_impl(
    path: Path | str,
    *,
    allowed_root: Path | str,
    offset: int = 0,
    max_bytes: int = 64 * 1024,
) -> tuple[bytes, int]:
    """Read from one verified descriptor without silently lowering the bound."""

    from . import runtime_artifact_safety as safety

    root, expected = _validated_paths(path, allowed_root, safety)
    flags = (
        os.O_RDONLY
        | getattr(os, "O_BINARY", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    descriptor = os.open(safety._runtime_open_path(expected), flags)
    try:
        metadata = os.fstat(descriptor)
        safety._require_private_regular_file(metadata)
        _verify_descriptor(descriptor, expected, root, safety)
        position = min(max(int(offset), 0), int(metadata.st_size))
        os.lseek(descriptor, position, os.SEEK_SET)
        data = _read_chunks(descriptor, max(int(max_bytes), 0))
        return data, int(os.lseek(descriptor, 0, os.SEEK_CUR))
    finally:
        os.close(descriptor)


def secure_digest_confined_file_impl(
    path: Path | str,
    *,
    allowed_root: Path | str,
    expected_identity: ConfinedFileIdentity,
    max_bytes: int,
) -> ConfinedFileDigestProof:
    """Stream-hash one exact pre-snapshotted file through a stable descriptor."""

    if type(expected_identity) is not ConfinedFileIdentity:
        raise ValueError("confined_digest_expected_identity_invalid")
    if type(max_bytes) is not int or max_bytes <= 0:
        raise ValueError("confined_digest_bound_invalid")
    from . import runtime_artifact_safety as safety

    root, expected = _validated_paths(path, allowed_root, safety)
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(safety._runtime_open_path(expected), flags)
    try:
        before = os.fstat(descriptor)
        safety._require_private_regular_file(before)
        if not _descriptor_identity_matches(before, expected_identity):
            raise ValueError("confined_digest_identity_mismatch")
        if int(before.st_size) > max_bytes:
            raise ValueError("confined_digest_bound_exceeded")
        _verify_descriptor(descriptor, expected, root, safety)
        digest = hashlib.sha256()
        total = 0
        os.lseek(descriptor, 0, os.SEEK_SET)
        for block in iter(lambda: os.read(descriptor, 1024 * 1024), b""):
            total += len(block)
            if total > max_bytes:
                raise ValueError("confined_digest_bound_exceeded")
            digest.update(block)
        after = os.fstat(descriptor)
        if not _descriptor_identity_matches(after, expected_identity) or total != expected_identity.size:
            raise ValueError("confined_digest_identity_changed")
        current = os.lstat(expected)
        if confined_file_identity(current) != expected_identity:
            raise ValueError("confined_digest_path_identity_changed")
        _verify_descriptor(descriptor, expected, root, safety)
        return ConfinedFileDigestProof(
            digest="sha256:" + digest.hexdigest(),
            size=total,
            identity=expected_identity,
        )
    finally:
        os.close(descriptor)


def _validated_paths(path: Path | str, allowed_root: Path | str, safety):
    raw = str(path or "").strip()
    if (
        not raw
        or "\x00" in raw
        or safety._UNSAFE_RUNTIME_NAMESPACE.match(raw.replace("\\", "/"))
    ):
        raise ValueError("confined_read_path_invalid")
    root_candidate = Path(os.path.abspath(Path(allowed_root).expanduser()))
    expected = Path(raw).expanduser()
    if not expected.is_absolute():
        expected = root_candidate / expected
    expected = Path(os.path.abspath(expected))
    if not safety._is_relative_to(expected, root_candidate):
        raise ValueError("confined_read_path_outside_root")
    if safety._contains_link_component(
        root_candidate
    ) or safety._contains_link_component(expected):
        raise ValueError("confined_read_path_link_rejected")
    root = safety._resolve_runtime_path(root_candidate, strict=True)
    resolved = safety._resolve_runtime_path(expected, strict=True)
    if not safety._is_relative_to(resolved, root):
        raise ValueError("confined_read_path_outside_root")
    return root, resolved


def _verify_descriptor(descriptor: int, expected: Path, root: Path, safety) -> None:
    final_path = safety._descriptor_final_path(descriptor)
    final_resolved = safety._resolve_runtime_path(final_path, strict=True)
    if not safety._is_relative_to(final_resolved, root):
        raise ValueError("confined_read_descriptor_outside_root")
    if os.path.normcase(str(final_resolved)) != os.path.normcase(str(expected)):
        raise ValueError("confined_read_descriptor_path_mismatch")


def _read_chunks(descriptor: int, limit: int) -> bytes:
    chunks: list[bytes] = []
    remaining = limit
    while remaining > 0:
        chunk = os.read(descriptor, min(remaining, 1024 * 1024))
        if not chunk:
            break
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


__all__ = [
    "ConfinedFileDigestProof",
    "ConfinedFileIdentity",
    "confined_file_identity",
    "secure_digest_confined_file_impl",
    "secure_read_confined_bytes_impl",
]
