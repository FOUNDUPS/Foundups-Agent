"""Durable fail-closed marker operations for the Holo authority checkout."""

from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Callable, Sequence

from holo_index.maintenance_lock import (
    AUTHORITY_BLOCK_MARKER_CONTENT,
    AUTHORITY_BLOCK_MARKER_FILENAME,
    authority_block_marker_path,
    authority_block_marker_valid,
)


GitRunner = Callable[[Sequence[str], Path], Any]


def valid_authority_block_marker(root: Path) -> bool:
    return authority_block_marker_valid(root)


def publish_authority_block_marker(root: Path) -> bool:
    temporary_name = ""
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            prefix=f"{AUTHORITY_BLOCK_MARKER_FILENAME}.",
            suffix=".tmp",
            dir=root,
            delete=False,
        ) as handle:
            temporary_name = handle.name
            handle.write(AUTHORITY_BLOCK_MARKER_CONTENT)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, authority_block_marker_path(root))
        return valid_authority_block_marker(root)
    except OSError:
        return False
    finally:
        if temporary_name:
            try:
                Path(temporary_name).unlink(missing_ok=True)
            except OSError:
                pass


def clear_authority_block_marker(root: Path) -> bool:
    marker = authority_block_marker_path(root)
    if not marker.exists():
        return True
    if not valid_authority_block_marker(root):
        return False
    try:
        marker.unlink()
    except OSError:
        return False
    return not marker.exists()


def marker_is_only_dirty_path(root: Path, runner: GitRunner) -> bool:
    try:
        result = runner(
            ("git", "status", "--porcelain=v1", "--untracked-files=all"), root
        )
    except (OSError, subprocess.SubprocessError, ValueError):
        return False
    if result is None or getattr(result, "returncode", 1) != 0:
        return False
    entries = [
        line.strip()
        for line in str(getattr(result, "stdout", "") or "").splitlines()
        if line.strip()
    ]
    return entries == [f"?? {AUTHORITY_BLOCK_MARKER_FILENAME}"]


__all__ = [
    "clear_authority_block_marker",
    "marker_is_only_dirty_path",
    "publish_authority_block_marker",
    "valid_authority_block_marker",
]
