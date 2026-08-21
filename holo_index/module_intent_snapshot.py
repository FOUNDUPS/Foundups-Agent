"""Bounded, generation-keyed module names from the authoritative Git tree."""

from __future__ import annotations

import os
import subprocess
import threading
import unicodedata
from pathlib import Path
from typing import Callable

from holo_index.tier0_retrieval import module_path_from_hit


MAX_GIT_TREE_BYTES = 1_048_576
MAX_MODULE_PATHS = 4_096
GIT_TREE_TIMEOUT_SECONDS = 5.0
MAX_CACHED_GENERATIONS = 8
_CACHE: dict[tuple[str, str], tuple[str, ...]] = {}
_CACHE_LOCK = threading.Lock()


class ModuleIntentSnapshotError(RuntimeError):
    """The bounded Git module-name snapshot could not be proven."""


def _reject() -> None:
    raise ModuleIntentSnapshotError(
        "HOLOINDEX_MODULE_INTENT_SNAPSHOT_UNAVAILABLE"
    )


def _root_identity(root: Path) -> str:
    """Return an OS-aware identity without collapsing POSIX case."""
    return os.path.normcase(str(root))


def _tree_records(tree: bytes) -> tuple[str, ...]:
    """Decode one complete, nonempty NUL-framed ls-tree response."""
    if not tree.endswith(b"\0"):
        _reject()
    raw_records = tree[:-1].split(b"\0")
    if not raw_records or any(not record for record in raw_records):
        _reject()
    try:
        return tuple(record.decode("utf-8", errors="strict") for record in raw_records)
    except UnicodeDecodeError as exc:
        raise ModuleIntentSnapshotError(
            "HOLOINDEX_MODULE_INTENT_SNAPSHOT_UNAVAILABLE"
        ) from exc


def _tree_path(record: str) -> str:
    """Validate one complete Git header and repository-relative path."""
    prefix, separator, path = record.partition("\t")
    fields = prefix.split(" ")
    valid_header = (
        separator == "\t" and len(fields) == 3 and fields[0] == "040000"
        and fields[1] == "tree" and len(fields[2]) == 40
        and all(character in "0123456789abcdef" for character in fields[2])
    )
    parts = path.split("/")
    valid_path = (
        bool(path) and "\\" not in path and parts[0] == "modules"
        and all(part not in {"", ".", ".."} for part in parts)
        and not any(
            unicodedata.category(character) in {"Cc", "Cf", "Cs"}
            for character in path
        )
    )
    if not valid_header or not valid_path:
        _reject()
    return path


def _git(
    root: Path, args: tuple[str, ...], run: Callable[..., object]
) -> bytes:
    """Run one bounded, shell-free Git metadata read."""
    try:
        result = run(
            ["git", "-C", str(root), *args], check=False,
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            timeout=GIT_TREE_TIMEOUT_SECONDS, shell=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise ModuleIntentSnapshotError(
            "HOLOINDEX_MODULE_INTENT_SNAPSHOT_UNAVAILABLE"
        ) from exc
    if int(getattr(result, "returncode", 1)) != 0:
        raise ModuleIntentSnapshotError(
            "HOLOINDEX_MODULE_INTENT_SNAPSHOT_UNAVAILABLE"
        )
    output = bytes(getattr(result, "stdout", b""))
    if not output or len(output) > MAX_GIT_TREE_BYTES:
        raise ModuleIntentSnapshotError(
            "HOLOINDEX_MODULE_INTENT_SNAPSHOT_UNAVAILABLE"
        )
    return output


def _module_paths(tree: bytes) -> tuple[str, ...]:
    """Parse exact depth-three module directories from NUL-delimited ls-tree."""
    modules: set[str] = set()
    paths: set[str] = set()
    folded_paths: set[str] = set()
    for record in _tree_records(tree):
        path = _tree_path(record)
        folded_path = unicodedata.normalize("NFC", path).casefold()
        if path in paths or folded_path in folded_paths:
            _reject()
        paths.add(path)
        folded_paths.add(folded_path)
        parts = path.split("/")
        if len(parts) != 3:
            continue
        if module_path_from_hit({"path": path}) != path:
            _reject()
        modules.add(path)
        if len(modules) > MAX_MODULE_PATHS:
            _reject()
    if not modules:
        _reject()
    return tuple(sorted(modules, key=lambda value: (value.casefold(), value)))


def load_module_intent_paths(
    repo_root: Path, *, run: Callable[..., object] = subprocess.run,
) -> tuple[str, ...]:
    """Return the complete tracked module-root snapshot for current Git HEAD."""
    root = repo_root.resolve(strict=False)
    head_raw = _git(root, ("rev-parse", "--verify", "HEAD"), run)
    try:
        head = head_raw.decode("ascii", errors="strict").strip()
    except UnicodeDecodeError as exc:
        raise ModuleIntentSnapshotError(
            "HOLOINDEX_MODULE_INTENT_SNAPSHOT_UNAVAILABLE"
        ) from exc
    if len(head) != 40 or any(character not in "0123456789abcdef" for character in head):
        raise ModuleIntentSnapshotError(
            "HOLOINDEX_MODULE_INTENT_SNAPSHOT_UNAVAILABLE"
        )
    key = (_root_identity(root), head)
    with _CACHE_LOCK:
        cached = _CACHE.get(key)
    if cached is not None:
        return cached
    tree = _git(
        root,
        ("ls-tree", "-z", "-d", "-r", "--full-tree", head, "--", "modules"),
        run,
    )
    paths = _module_paths(tree)
    with _CACHE_LOCK:
        cached = _CACHE.get(key)
        if cached is not None:
            return cached
        while len(_CACHE) >= MAX_CACHED_GENERATIONS:
            _CACHE.pop(next(iter(_CACHE)))
        _CACHE[key] = paths
        return paths


def clear_module_intent_snapshot_cache() -> None:
    """Clear the bounded process cache for deterministic tests."""
    with _CACHE_LOCK:
        _CACHE.clear()


__all__ = [
    "GIT_TREE_TIMEOUT_SECONDS", "MAX_GIT_TREE_BYTES", "MAX_MODULE_PATHS",
    "ModuleIntentSnapshotError", "clear_module_intent_snapshot_cache",
    "load_module_intent_paths",
]
