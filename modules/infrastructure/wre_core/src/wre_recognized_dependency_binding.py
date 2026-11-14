"""Recognized dependency/config parity for exact-SHA test planning."""

from __future__ import annotations

import fnmatch
import hashlib
import json
from pathlib import Path, PurePosixPath
from typing import Any, Sequence

MAX_DEPENDENCY_FILE_BYTES = 64 * 1024 * 1024
MAX_DEPENDENCY_FILES = 4096
_NAMES = {
    "Cargo.lock", "Cargo.toml", "Gemfile.lock", "Pipfile", "Pipfile.lock",
    "composer.lock", "conda-lock.yml", "environment.yml", "go.mod", "go.sum",
    "package-lock.json", "package.json", "pnpm-lock.yaml", "poetry.lock",
    "pyproject.toml", "pytest.ini", "setup.cfg", "setup.py", "tox.ini",
    "uv.lock", "yarn.lock",
}
_PATTERNS = ("requirements*.txt",)


def matching_recognized_dependency_digest(
    base_root: Path, candidate_root: Path,
) -> str:
    """Return a digest only when every recognized dependency file is unchanged."""
    paths = tuple(sorted(
        set(_recognized_paths(base_root)) | set(_recognized_paths(candidate_root))
    ))
    if len(paths) > MAX_DEPENDENCY_FILES:
        return ""
    base = _content_digest(base_root, paths)
    candidate = _content_digest(candidate_root, paths)
    return base if base and base == candidate else ""


def _recognized_paths(root: Path) -> tuple[str, ...]:
    return tuple(sorted(
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file() and _recognized(path.name)
    ))


def _recognized(name: str) -> bool:
    return name in _NAMES or any(
        fnmatch.fnmatchcase(name, pattern) for pattern in _PATTERNS
    )


def _content_digest(root: Path, paths: Sequence[str]) -> str:
    records = []
    for relative in paths:
        path = (root / PurePosixPath(relative)).resolve()
        if root.resolve() not in path.parents or not path.is_file():
            return ""
        if path.stat().st_size > MAX_DEPENDENCY_FILE_BYTES:
            return ""
        records.append((relative, hashlib.sha256(path.read_bytes()).hexdigest()))
    return _digest(records)


def _digest(value: Any) -> str:
    raw = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
        allow_nan=False,
    )
    return "sha256:" + hashlib.sha256(raw.encode("ascii")).hexdigest()


__all__ = [
    "MAX_DEPENDENCY_FILES", "matching_recognized_dependency_digest",
]
