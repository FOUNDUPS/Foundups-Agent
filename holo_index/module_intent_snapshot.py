"""Bounded, generation-keyed module names from the authoritative Git tree."""

from __future__ import annotations

import os
import subprocess
import threading
import unicodedata
from pathlib import Path
from typing import Callable

from holo_index.cli.repo_audit_discovery import (
    git_read_command,
    git_read_environment,
)
from holo_index.tier0_retrieval import module_path_from_hit


# Eight MiB accommodates the declared 4,096-module ceiling at the measured
# repository shape while remaining independently bounded by time and scope.
MAX_GIT_TREE_BYTES = 8_388_608
MAX_MODULE_PATHS = 4_096
MAX_GIT_BATCH_INPUT_BYTES = MAX_MODULE_PATHS * 41
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


def _tree_entry(record: str) -> tuple[str, str]:
    """Validate one complete Git-tree directory record."""
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
    return path, fields[2]


def _git(
    root: Path, args: tuple[str, ...], run: Callable[..., object],
    *, input_data: bytes | None = None,
) -> bytes:
    """Run one bounded, shell-free Git metadata read."""
    if input_data is not None and (
        not input_data or len(input_data) > MAX_GIT_BATCH_INPUT_BYTES
    ):
        _reject()
    command = git_read_command(root, args)
    if not command:
        _reject()
    try:
        kwargs = {
            "check": False, "stdout": subprocess.PIPE,
            "stderr": subprocess.DEVNULL,
            "timeout": GIT_TREE_TIMEOUT_SECONDS, "shell": False,
            "env": git_read_environment(),
        }
        if input_data is not None:
            kwargs["input"] = input_data
        result = run(command, **kwargs)
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


def _directory_projection(
    tree: bytes,
) -> tuple[tuple[tuple[str, str], ...], set[str]]:
    """Return candidate roots and roots proved by direct src/tests trees."""
    candidates: dict[str, str] = {}
    structural_modules: set[str] = set()
    paths: set[str] = set()
    folded_paths: set[str] = set()
    for record in _tree_records(tree):
        path, oid = _tree_entry(record)
        folded_path = unicodedata.normalize("NFC", path).casefold()
        if path in paths or folded_path in folded_paths:
            _reject()
        paths.add(path)
        folded_paths.add(folded_path)
        parts = path.split("/")
        if len(parts) == 3:
            if module_path_from_hit({"path": path}) != path:
                _reject()
            candidates[path] = oid
            if len(candidates) > MAX_MODULE_PATHS:
                _reject()
        elif len(parts) == 4 and parts[3] in {"src", "tests"}:
            structural_modules.add("/".join(parts[:3]))
    if not candidates or not structural_modules.issubset(candidates):
        _reject()
    ordered = tuple(sorted(
        candidates.items(), key=lambda item: (item[0].casefold(), item[0])
    ))
    return ordered, structural_modules


def _tree_object_entries(tree: bytes) -> tuple[tuple[str, str], ...]:
    """Parse one raw Git tree object and reject ambiguous entry names."""
    entries: list[tuple[str, str]] = []
    names: set[str] = set()
    folded_names: set[str] = set()
    offset = 0
    while offset < len(tree):
        separator = tree.find(b" ", offset)
        terminator = tree.find(b"\0", separator + 1)
        if separator <= offset or terminator <= separator + 1:
            _reject()
        oid_end = terminator + 21
        if oid_end > len(tree):
            _reject()
        try:
            mode = tree[offset:separator].decode("ascii", errors="strict")
            name = tree[separator + 1:terminator].decode(
                "utf-8", errors="strict"
            )
        except UnicodeDecodeError as exc:
            raise ModuleIntentSnapshotError(
                "HOLOINDEX_MODULE_INTENT_SNAPSHOT_UNAVAILABLE"
            ) from exc
        valid_name = (
            name not in {"", ".", ".."} and "/" not in name
            and "\\" not in name
            and not any(
                unicodedata.category(character) in {"Cc", "Cf", "Cs"}
                for character in name
            )
        )
        if mode not in {"40000", "100644", "100755", "120000", "160000"}:
            _reject()
        folded_name = unicodedata.normalize("NFC", name).casefold()
        if not valid_name or name in names or folded_name in folded_names:
            _reject()
        names.add(name)
        folded_names.add(folded_name)
        entries.append((mode, name))
        offset = oid_end
    if not entries:
        _reject()
    return tuple(entries)


def _documented_module_roots(
    batch: bytes, candidates: tuple[tuple[str, str], ...],
) -> set[str]:
    """Verify batch framing and find root module contracts only."""
    documented: set[str] = set()
    offset = 0
    for path, expected_oid in candidates:
        newline = batch.find(b"\n", offset)
        if newline < offset or newline - offset > 96:
            _reject()
        try:
            header = batch[offset:newline].decode("ascii", errors="strict")
        except UnicodeDecodeError as exc:
            raise ModuleIntentSnapshotError(
                "HOLOINDEX_MODULE_INTENT_SNAPSHOT_UNAVAILABLE"
            ) from exc
        fields = header.split(" ")
        if (
            len(fields) != 3 or fields[0] != expected_oid
            or fields[1] != "tree" or not fields[2].isdigit()
        ):
            _reject()
        size = int(fields[2])
        body_start = newline + 1
        body_end = body_start + size
        if size <= 0 or body_end >= len(batch) or batch[body_end] != 0x0A:
            _reject()
        entries = _tree_object_entries(batch[body_start:body_end])
        if any(
            mode in {"100644", "100755"}
            and name in {"README.md", "INTERFACE.md"}
            for mode, name in entries
        ):
            documented.add(path)
        offset = body_end + 1
    if offset != len(batch):
        _reject()
    return documented


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
    directory_tree = _git(
        root,
        ("ls-tree", "-z", "-d", "-r", "--full-tree", head, "--", "modules"),
        run,
    )
    candidates, structural_modules = _directory_projection(directory_tree)
    batch_input = b"".join(
        oid.encode("ascii") + b"\n" for _path, oid in candidates
    )
    immediate_trees = _git(
        root, ("cat-file", "--batch"), run, input_data=batch_input,
    )
    modules = structural_modules | _documented_module_roots(
        immediate_trees, candidates
    )
    if not modules or len(modules) > MAX_MODULE_PATHS:
        _reject()
    paths = tuple(sorted(modules, key=lambda value: (value.casefold(), value)))
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
