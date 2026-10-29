"""Inert installed-source description; shape and hashes never confer authority.

The protected installer must authenticate the complete inventory, confinement,
Git provenance and root approval separately. This module performs no I/O.
"""
from __future__ import annotations

from pathlib import PurePosixPath
from typing import Mapping

from .reddog_runtime_artifact_manifest_contract import (
    RuntimeArtifactManifestError, canonical_json, digest, is_sha256, raw_digest,
)
from modules.infrastructure.wre_core.src.wre_git_tree_manifest import portable_git_path

INSTALLED_SOURCE_SCHEMA = "reddog_grant_authority_installed_source.v1"
INSTALLED_SOURCE_FILENAME = "grant_authority_installed_source.json"
SOURCE_DIRECTORY = "opt/grant-source"
INSTALLED_ENTRYPOINT = (
    "modules.communication.moltbot_bridge.src.reddog_grant_authority_service:serve_grant_authority_once"
)
INSTALLED_DEPENDENCY_LOADER = (
    "modules.communication.moltbot_bridge.src.reddog_grant_authority_runtime_dependencies:"
    "materialize_grant_authority_runtime_dependencies"
)
PYTHON_LAUNCH = ("/usr/bin/python3.12", "-I", "-S", "-B")
EXPLICIT_SYS_PATH = ("/usr/lib/python3.12", "/usr/lib/python3.12/lib-dynload",
                     "/usr/lib/python3/dist-packages", "/" + SOURCE_DIRECTORY)
MAX_INSTALLED_FILES = 8192
MAX_INSTALLED_FILE_BYTES = 64 * 1024 * 1024
MAX_INSTALLED_TOTAL_BYTES = 512 * 1024 * 1024
_FIELDS = frozenset({"schema_version", "installed_root", "source_commit_sha",
    "source_object_format", "source_directory", "directories", "files", "source_files",
    "python_launch", "explicit_sys_path", "entrypoint", "dependency_loader"})


def validate_installed_grant_source(value: Mapping) -> dict:
    """Return detached canonical metadata, not verified installation evidence."""
    if not isinstance(value, Mapping) or set(value) != _FIELDS:
        _invalid()
    raw = dict(value)
    expected = {"schema_version": INSTALLED_SOURCE_SCHEMA, "source_directory": SOURCE_DIRECTORY,
        "entrypoint": INSTALLED_ENTRYPOINT, "dependency_loader": INSTALLED_DEPENDENCY_LOADER,
        "python_launch": list(PYTHON_LAUNCH), "explicit_sys_path": list(EXPLICIT_SYS_PATH)}
    if any(type(raw[k]) is not type(v) or raw[k] != v for k, v in expected.items()):
        _invalid()
    root = raw["installed_root"]
    if (type(root) is not str or not root.isascii() or any(not 33 <= ord(c) < 127 for c in root)
            or not root.startswith("/") or root.startswith("//")
            or root == "/" or str(PurePosixPath(root)) != root or ".." in PurePosixPath(root).parts
            or "\\" in root or ":" in root or len(root) > 4096):
        _invalid()
    object_format = raw["source_object_format"]
    if type(object_format) is not str:
        _invalid()
    width = {"sha1": 40, "sha256": 64}.get(object_format)
    commit = raw["source_commit_sha"]
    if (width is None or type(commit) is not str or len(commit) != width
            or any(c not in "0123456789abcdef" for c in commit)):
        _invalid()
    files = _files(raw["files"])
    _directories(raw["directories"], files)
    _sources(raw["source_files"], files)
    executable = files.get(PYTHON_LAUNCH[0][1:])
    if executable is None or executable["mode"] != 0o555 or executable["bytes"] == 0:
        _invalid()
    for path in EXPLICIT_SYS_PATH:
        if path[1:] not in raw["directories"]:
            _invalid()
    # JSON round-trip detaches all nested caller-owned mutable containers.
    import json
    return json.loads(canonical_json(raw))


def installed_grant_source_digest(value: Mapping) -> str:
    """Stable descriptor binding excludes future E0, permission and manifest IDs."""
    return digest(validate_installed_grant_source(value))


def _files(value):
    if type(value) is not list or not 1 <= len(value) <= MAX_INSTALLED_FILES:
        _invalid()
    result, total = {}, 0
    for item in value:
        if type(item) is not dict or set(item) != {"path", "bytes", "mode", "sha256"}:
            _invalid()
        path, size, mode, hash_value = (item[n] for n in ("path", "bytes", "mode", "sha256"))
        if (not _relative(path) or path in result or type(size) is not int
                or not 0 <= size <= MAX_INSTALLED_FILE_BYTES or type(mode) is not int
                or mode not in {0o444, 0o555} or type(hash_value) is not str
                or not is_sha256("sha256:" + hash_value)):
            _invalid()
        if size == 0 and hash_value != raw_digest(b"")[7:]:
            _invalid()
        total += size
        result[path] = item
    if list(result) != sorted(result) or total > MAX_INSTALLED_TOTAL_BYTES:
        _invalid()
    return result


def _directories(value, files):
    if type(value) is not list or not value or len(value) > MAX_INSTALLED_FILES * 4:
        _invalid()
    if any(not _relative(path) for path in value) or value != sorted(set(value)):
        _invalid()
    directories = set(value)
    # Paths are canonical relative strings. Requiring each immediate parent,
    # including parents of empty directories, establishes full ancestor closure.
    for paths in (files, value):
        for path in paths:
            parent = path.rpartition("/")[0]
            if parent and parent not in directories:
                _invalid()
    if directories & files.keys():
        _invalid()


def _sources(value, files):
    if type(value) is not dict or not 1 <= len(value) <= 4096:
        _invalid()
    installed = {path[len(SOURCE_DIRECTORY) + 1:]: item for path, item in files.items()
                 if path.startswith(SOURCE_DIRECTORY + "/")}
    if set(value) != set(installed):
        _invalid()
    for path, hash_value in value.items():
        # Exact-string keys equal the suffixes of paths already checked by _files;
        # removing the fixed portable prefix preserves every _relative constraint.
        if (type(path) is not str or not path.endswith(".py") or not is_sha256(hash_value)
                or hash_value != "sha256:" + installed[path]["sha256"]
                or installed[path]["mode"] != 0o444):
            _invalid()
    # Namespace packages are legitimate. Completeness is established against Git
    # and real imports by the installer, not inferred from this declared map.
    if "modules/__init__.py" not in value:
        _invalid()
    for entrypoint in (INSTALLED_ENTRYPOINT, INSTALLED_DEPENDENCY_LOADER):
        if entrypoint.split(":")[0].replace(".", "/") + ".py" not in value:
            _invalid()


def _relative(value):
    return (type(value) is str and value.isascii() and len(value) <= 4096
            and not any(not 33 <= ord(c) < 127 for c in value)
            and portable_git_path(value) and str(PurePosixPath(value)) == value)


def _invalid():
    raise RuntimeArtifactManifestError("grant_installed_source_invalid")


__all__ = ["INSTALLED_SOURCE_SCHEMA", "INSTALLED_SOURCE_FILENAME", "SOURCE_DIRECTORY",
    "INSTALLED_ENTRYPOINT", "INSTALLED_DEPENDENCY_LOADER", "PYTHON_LAUNCH", "EXPLICIT_SYS_PATH",
    "validate_installed_grant_source", "installed_grant_source_digest"]
