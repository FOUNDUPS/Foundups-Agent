"""Shared unresolved-path safety primitives for executable WRE Skillz."""

from __future__ import annotations

import os
from pathlib import Path
import stat


def absolute_unresolved(path: Path) -> Path:
    """Make a path absolute without resolving links or reparse points."""
    return Path(os.path.abspath(Path(path)))


def has_link_or_reparse_component(root: Path, candidate: Path) -> bool:
    """Inspect every checkout-local component before resolving the candidate."""
    root = absolute_unresolved(root)
    raw = candidate if candidate.is_absolute() else root / candidate
    raw = absolute_unresolved(raw)
    try:
        relative = raw.relative_to(root)
    except ValueError:
        return True
    current = root
    for part in relative.parts:
        current = current / part
        if _is_link_or_reparse(current):
            return True
    return False


def path_has_link_or_reparse(candidate: Path) -> bool:
    """Inspect an absolute path from its filesystem anchor through its leaf."""
    absolute = absolute_unresolved(candidate)
    current = Path(absolute.anchor)
    for part in absolute.parts[1:]:
        current = current / part
        if _is_link_or_reparse(current):
            return True
    return False


def _is_link_or_reparse(path: Path) -> bool:
    try:
        metadata = os.lstat(path)
    except FileNotFoundError:
        return False
    except OSError:
        return True
    attributes = getattr(metadata, "st_file_attributes", 0)
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return stat.S_ISLNK(metadata.st_mode) or bool(attributes & reparse_flag)
