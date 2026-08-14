"""One-descriptor confined byte reads with an explicit caller bound."""

from __future__ import annotations

import os
from pathlib import Path


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


__all__ = ["secure_read_confined_bytes_impl"]
