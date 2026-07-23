"""Bounded, repository-confined filesystem helpers for bundle retrieval."""

from __future__ import annotations

import os
from pathlib import Path, PurePosixPath, PureWindowsPath

LEXICAL_MODULE_DOMAIN_MAX_ENTRIES = 64
LEXICAL_MODULE_MAX_ENTRIES = 2048
LEXICAL_MODULE_MAX_DEPTH = 8
LEXICAL_NAVIGATION_MAX_BYTES = 262144
WINDOWS_REPARSE_POINT = 0x400


def _safe_relative_parts(value: str) -> tuple[str, ...] | None:
    normalized = str(value or "").replace("\\", "/")
    posix = PurePosixPath(normalized)
    windows = PureWindowsPath(normalized)
    if (
        not normalized
        or posix.is_absolute()
        or windows.is_absolute()
        or windows.drive
    ):
        return None
    parts = tuple(posix.parts)
    if not parts or any(part in {"", ".", ".."} for part in parts):
        return None
    return parts


def _is_link_or_reparse(path: Path) -> bool:
    try:
        metadata = os.lstat(path)
    except OSError:
        return True
    attributes = int(getattr(metadata, "st_file_attributes", 0) or 0)
    return path.is_symlink() or bool(attributes & WINDOWS_REPARSE_POINT)


def _confined_repo_path(
    repo_root: Path | str,
    relative_path: str,
    *,
    directory: bool,
) -> Path | None:
    parts = _safe_relative_parts(relative_path)
    root = Path(repo_root)
    if parts is None or not root.is_absolute() or _is_link_or_reparse(root):
        return None
    try:
        resolved_root = root.resolve(strict=True)
    except OSError:
        return None
    if not resolved_root.is_dir():
        return None
    candidate = resolved_root
    for part in parts:
        candidate = candidate / part
        if _is_link_or_reparse(candidate):
            return None
    try:
        resolved = candidate.resolve(strict=True)
        resolved.relative_to(resolved_root)
    except (OSError, ValueError):
        return None
    if directory and not resolved.is_dir():
        return None
    if not directory and not resolved.is_file():
        return None
    return resolved


def _bounded_directory_names(
    repo_root: Path | str,
    relative_dir: str,
    *,
    entry_cap: int,
    prefix: str = "",
    suffix: str = "",
    directories: bool,
) -> tuple[str, ...]:
    """Return sorted names from a bounded, no-follow directory scan."""
    root = Path(os.path.abspath(repo_root))
    directory = _confined_repo_path(root, relative_dir, directory=True)
    if directory is None or entry_cap <= 0:
        return ()
    names: list[str] = []
    try:
        with os.scandir(directory) as entries:
            for inspected, entry in enumerate(entries):
                if inspected >= entry_cap:
                    return ()
                path = Path(entry.path)
                if _is_link_or_reparse(path):
                    continue
                expected_kind = (
                    entry.is_dir(follow_symlinks=False)
                    if directories
                    else entry.is_file(follow_symlinks=False)
                )
                if not expected_kind:
                    continue
                if prefix and not entry.name.startswith(prefix):
                    continue
                if suffix and not entry.name.endswith(suffix):
                    continue
                names.append(entry.name)
    except OSError:
        return ()
    return tuple(sorted(names, key=lambda name: (name.casefold(), name)))


def _read_confined_bytes(
    repo_root: Path | str,
    relative_path: str,
    *,
    max_bytes: int,
    reject_oversize: bool,
) -> bytes | None:
    """Read one bounded regular file after repository/no-follow validation."""
    path = _confined_repo_path(repo_root, relative_path, directory=False)
    if path is None or max_bytes < 0:
        return None
    try:
        if reject_oversize:
            metadata = os.stat(path, follow_symlinks=False)
            if metadata.st_size > max_bytes:
                return None
        with path.open("rb") as handle:
            raw = handle.read(max_bytes + 1 if reject_oversize else max_bytes)
    except (OSError, ValueError):
        return None
    if reject_oversize and len(raw) > max_bytes:
        return None
    return raw[:max_bytes]


def _read_confined_text(
    repo_root: Path | str,
    relative_path: str,
    *,
    max_bytes: int,
    reject_oversize: bool,
) -> str | None:
    """Decode a bounded repository-confined file without following links."""
    raw = _read_confined_bytes(
        repo_root,
        relative_path,
        max_bytes=max_bytes,
        reject_oversize=reject_oversize,
    )
    if raw is None:
        return None
    return raw.decode("utf-8-sig", errors="ignore")


def _resolve_module_dir(repo_root: Path | str, hint: str) -> Path | None:
    """Resolve one repository-relative module hint without following links."""
    raw = (hint or "").strip()
    parts = _safe_relative_parts(raw)
    if parts is None:
        return None
    norm = "/".join(parts)
    direct = _confined_repo_path(repo_root, norm, directory=True)
    if direct is not None:
        return direct
    if "/" in norm and not norm.startswith("modules/"):
        prefixed = _confined_repo_path(
            repo_root, f"modules/{norm}", directory=True
        )
        if prefixed is not None:
            return prefixed
    modules_root = _confined_repo_path(repo_root, "modules", directory=True)
    if modules_root is None:
        return None
    domains = _bounded_directory_names(
        repo_root,
        "modules",
        entry_cap=LEXICAL_MODULE_DOMAIN_MAX_ENTRIES,
        directories=True,
    )
    for domain_name in domains:
        candidate = _confined_repo_path(
            repo_root,
            f"modules/{domain_name}/{norm}",
            directory=True,
        )
        if candidate is not None:
            return candidate
    return None


def _sorted_module_paths(files: list[Path], root: Path) -> tuple[Path, ...]:
    def relative_key(path: Path) -> tuple[str, str]:
        relative = path.relative_to(root).as_posix()
        return relative.casefold(), relative

    return tuple(sorted(files, key=relative_key))


def _bounded_module_files(
    repo_root: Path | str,
    module_dir: Path | str,
) -> tuple[Path, ...]:
    """Enumerate a confined module without following links or reparse points."""
    root = Path(os.path.abspath(repo_root))
    module = Path(os.path.abspath(module_dir))
    try:
        relative_module = module.relative_to(root).as_posix()
    except ValueError:
        return ()
    confined = _confined_repo_path(root, relative_module, directory=True)
    if confined is None:
        return ()
    files: list[Path] = []
    stack: list[tuple[Path, int]] = [(confined, 0)]
    inspected = 0
    while stack:
        current, depth = stack.pop()
        try:
            with os.scandir(current) as entries:
                for entry in entries:
                    inspected += 1
                    if inspected > LEXICAL_MODULE_MAX_ENTRIES:
                        return ()
                    path = Path(entry.path)
                    if _is_link_or_reparse(path):
                        continue
                    is_dir = entry.is_dir(follow_symlinks=False)
                    is_file = entry.is_file(follow_symlinks=False)
                    if not is_dir and not is_file:
                        continue
                    relative = path.relative_to(root).as_posix()
                    verified = _confined_repo_path(
                        root, relative, directory=is_dir
                    )
                    if verified is None:
                        return ()
                    if is_dir:
                        if depth >= LEXICAL_MODULE_MAX_DEPTH:
                            return ()
                        stack.append((verified, depth + 1))
                    else:
                        files.append(verified)
        except (OSError, ValueError):
            return ()
    return _sorted_module_paths(files, root)


def _artifact_exists(
    repo_root: Path | str,
    module_dir: Path | str,
    name: str,
    *,
    directory: bool,
) -> bool:
    root = Path(os.path.abspath(repo_root))
    module = Path(os.path.abspath(module_dir))
    try:
        module_relative = module.relative_to(root)
    except ValueError:
        return False
    artifact_relative = module_relative / name.rstrip("/")
    return (
        _confined_repo_path(
            root,
            artifact_relative.as_posix(),
            directory=directory,
        )
        is not None
    )


__all__ = [
    "LEXICAL_MODULE_DOMAIN_MAX_ENTRIES",
    "LEXICAL_MODULE_MAX_DEPTH",
    "LEXICAL_MODULE_MAX_ENTRIES",
    "LEXICAL_NAVIGATION_MAX_BYTES",
    "_artifact_exists",
    "_bounded_directory_names",
    "_bounded_module_files",
    "_confined_repo_path",
    "_is_link_or_reparse",
    "_read_confined_bytes",
    "_read_confined_text",
    "_resolve_module_dir",
]
