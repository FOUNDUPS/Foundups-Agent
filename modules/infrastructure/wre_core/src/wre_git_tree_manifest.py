"""Exact regular-file manifest for one Git commit tree."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from types import MappingProxyType
from typing import Mapping
import unicodedata

from .wre_git_bounded_io import (
    git_read_environment,
    resolve_exact_commit,
    run_bounded_stdout,
)

MAX_TREE_LIST_BYTES = 64 * 1024 * 1024
MAX_TREE_ENTRIES = 100_000
_REGULAR_MODES = {"100644", "100755"}
_WINDOWS_DEVICES = {
    "CON", "PRN", "AUX", "NUL", "COM1", "COM2", "COM3", "COM4",
    "COM5", "COM6", "COM7", "COM8", "COM9", "LPT1", "LPT2", "LPT3",
    "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9",
    "COM\u00b9", "COM\u00b2", "COM\u00b3", "LPT\u00b9", "LPT\u00b2", "LPT\u00b3",
}


@dataclass(frozen=True)
class ExactGitTreeManifest:
    commit_sha: str
    object_format: str
    blobs: Mapping[str, str]


def exact_git_tree_manifest(repo: Path, sha: str) -> ExactGitTreeManifest:
    """Return exact path-to-blob bindings without checkout attribute filters."""
    commit = resolve_exact_commit(repo, sha)
    object_format = _object_format(repo)
    raw = run_bounded_stdout(
        ("git", "--no-replace-objects", "-C", str(repo), "ls-tree", "-rz",
         "--full-tree", commit),
        cwd=repo, max_bytes=MAX_TREE_LIST_BYTES, timeout_s=120,
        environment=git_read_environment(),
    )
    blobs: dict[str, str] = {}
    spellings: dict[tuple[str, ...], dict[str, str]] = {}
    leaves: set[tuple[str, ...]] = set()
    branches: set[tuple[str, ...]] = set()
    records = raw.split(b"\0")
    if records and records[-1] == b"":
        records.pop()
    if not records or len(records) > MAX_TREE_ENTRIES:
        raise ValueError("git_tree_entry_bounds_invalid")
    for record in records:
        path, object_id, materialize = _tree_record(record, object_format)
        _claim_portable_path(path, spellings, leaves, branches)
        if materialize:
            blobs[path] = object_id
    return ExactGitTreeManifest(
        commit, object_format, MappingProxyType(dict(blobs)),
    )


def portable_git_path(value: str) -> bool:
    """Reject paths that are unsafe or ambiguous on supported filesystems."""
    if not value or "\\" in value or any(ord(char) < 32 for char in value):
        return False
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        return False
    for part in path.parts:
        stem = part.split(".", 1)[0].upper()
        invalid = any(char in '<>:"|?*' for char in part)
        if (
            invalid or unicodedata.normalize("NFC", part) != part
            or part.endswith((" ", ".")) or stem in _WINDOWS_DEVICES
        ):
            return False
    return True


def _claim_portable_path(
    path: str, spellings: dict[tuple[str, ...], dict[str, str]],
    leaves: set[tuple[str, ...]], branches: set[tuple[str, ...]],
) -> None:
    parts = PurePosixPath(path).parts
    keys = tuple(part.casefold() for part in parts)
    parent: tuple[str, ...] = ()
    for part, key in zip(parts, keys):
        siblings = spellings.setdefault(parent, {})
        if key in siblings and siblings[key] != part:
            raise ValueError("git_tree_path_collision")
        siblings[key] = part
        parent += (key,)
    if keys in leaves or keys in branches or any(keys[:i] in leaves for i in range(1, len(keys))):
        raise ValueError("git_tree_path_collision")
    branches.update(keys[:i] for i in range(1, len(keys)))
    leaves.add(keys)


def _tree_record(record: bytes, object_format: str) -> tuple[str, str, bool]:
    try:
        metadata, raw_path = record.split(b"\t", 1)
        raw_mode, kind, raw_object_id = metadata.split(b" ", 2)
        mode = raw_mode.decode("ascii", errors="strict")
        path = raw_path.decode("utf-8", errors="strict")
        object_id = raw_object_id.decode("ascii", errors="strict")
    except (UnicodeError, ValueError) as exc:
        raise ValueError("git_tree_record_invalid") from exc
    expected_length = 40 if object_format == "sha1" else 64
    regular = mode in _REGULAR_MODES and kind == b"blob"
    gitlink = mode == "160000" and kind == b"commit"
    valid = (
        (regular or gitlink) and portable_git_path(path)
        and len(object_id) == expected_length
        and all(char in "0123456789abcdef" for char in object_id)
    )
    if not valid:
        raise ValueError("git_tree_record_invalid")
    return path, object_id, regular


def _object_format(repo: Path) -> str:
    raw = run_bounded_stdout(
        ("git", "--no-replace-objects", "-C", str(repo), "rev-parse",
         "--show-object-format"),
        cwd=repo, max_bytes=32, timeout_s=30,
        environment=git_read_environment(),
    )
    value = raw.decode("ascii", errors="strict").strip()
    if value not in {"sha1", "sha256"}:
        raise ValueError("git_object_format_invalid")
    return value


__all__ = [
    "ExactGitTreeManifest", "MAX_TREE_ENTRIES", "MAX_TREE_LIST_BYTES",
    "exact_git_tree_manifest", "portable_git_path",
]
