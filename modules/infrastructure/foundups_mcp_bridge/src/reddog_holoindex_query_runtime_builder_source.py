"""Manifest and loaded-source metadata proof for an inert evidence builder."""

from __future__ import annotations

import json
import os
from pathlib import Path
import posixpath
import re
import stat
import sys
from types import ModuleType
from typing import Any, Mapping, Sequence
import unicodedata

from holo_index.repository_state import repository_root_digest
from modules.infrastructure.shared_utilities.runtime_artifact_confined_byte_reader import (
    confined_file_identity,
    secure_digest_confined_file_impl,
    secure_read_confined_bytes_impl,
)
from modules.infrastructure.shared_utilities.runtime_artifact_windows_streams import (
    require_unnamed_data_stream_only,
)

from .reddog_holoindex_dependency_runtime_contract import (
    canonical_json_bytes,
    digest_bytes,
    is_digest,
)
from .reddog_holoindex_query_runtime_builder_contract import (
    BuilderSourceAuthority,
    _source_authority_capability,
)
from .reddog_holoindex_query_runtime_builder_git import (
    PinnedGitAuthority,
    QueryRuntimeBuilderGitError,
    prove_pinned_git_authority,
)


_HEX = re.compile(r"[0-9a-f]{64}\Z")
_MANIFEST_PATH = "scripts/reddog_backend_manifest.json"
_REQUIRED_BUILDER_FILES = tuple(sorted((
    "modules/infrastructure/foundups_mcp_bridge/src/"
    "reddog_holoindex_query_runtime_builder_contract.py",
    "modules/infrastructure/foundups_mcp_bridge/src/"
    "reddog_holoindex_query_runtime_builder_git.py",
    "modules/infrastructure/foundups_mcp_bridge/src/"
    "reddog_holoindex_query_runtime_builder_packaging.py",
    "modules/infrastructure/foundups_mcp_bridge/src/"
    "reddog_holoindex_query_runtime_builder_process.py",
    "modules/infrastructure/foundups_mcp_bridge/src/"
    "reddog_holoindex_query_runtime_builder_source.py",
)))
_MAX_MANIFEST_BYTES = 4 * 1024 * 1024
_MAX_SOURCE_FILE_BYTES = 64 * 1024 * 1024
_MAX_SOURCE_BYTES = 128 * 1024 * 1024


class QueryRuntimeBuilderSourceError(RuntimeError):
    """Stable fail-closed source metadata authority error."""


def _fail(code: str) -> None:
    raise QueryRuntimeBuilderSourceError(code)


def prove_builder_source_authority(
    *, repo_root: Path | str, expected_repo_head_sha: str,
    git_executable: Path | str, expected_git_executable_digest: str,
) -> BuilderSourceAuthority:
    """Bind exact HEAD blobs and stable loaded-source metadata before/after."""

    try:
        root = _approved_root(repo_root)
        executable = Path(git_executable)
        origins_before = _module_origins(root, sys.modules)
        bound_paths = tuple(sorted({
            _MANIFEST_PATH, *_REQUIRED_BUILDER_FILES, *origins_before,
        }))
        git_before = prove_pinned_git_authority(
            root=root, expected_head=str(expected_repo_head_sha),
            executable=executable, expected_digest=expected_git_executable_digest,
            bound_paths=bound_paths,
        )
        binding = _source_binding(
            root=root, git=git_before, origins=origins_before,
            required_builder_files=_REQUIRED_BUILDER_FILES,
        )
        origins_after = _module_origins(root, sys.modules)
        git_after = prove_pinned_git_authority(
            root=root, expected_head=str(expected_repo_head_sha),
            executable=executable, expected_digest=expected_git_executable_digest,
            bound_paths=bound_paths,
        )
        binding_after = _source_binding(
            root=root, git=git_after, origins=origins_after,
            required_builder_files=_REQUIRED_BUILDER_FILES,
        )
    except (QueryRuntimeBuilderSourceError, QueryRuntimeBuilderGitError):
        raise
    except Exception:
        _fail("QUERY_BUILDER_SOURCE_AUTHORITY_UNAVAILABLE")
    if (
        origins_after != origins_before or git_after != git_before
        or binding_after != binding
    ):
        _fail("QUERY_BUILDER_SOURCE_MUTATED_DURING_PROOF")
    return _source_authority_capability(binding)


def _prove_builder_source_authority_for_test(
    *, repo_root: Path, git_authority: PinnedGitAuthority,
    modules: Mapping[str, ModuleType], required_builder_files: Sequence[str],
) -> BuilderSourceAuthority:
    """Private deterministic seam; production never accepts injected evidence."""

    root = _approved_root(repo_root)
    return _source_authority_capability(_source_binding(
        root=root, git=git_authority, origins=_module_origins(root, modules),
        required_builder_files=tuple(required_builder_files),
    ))


def _source_binding(
    *, root: Path, git: PinnedGitAuthority,
    origins: Mapping[str, str], required_builder_files: Sequence[str],
) -> dict[str, Any]:
    if type(git) is not PinnedGitAuthority or git.repo_root != root:
        _fail("QUERY_BUILDER_SOURCE_GIT_AUTHORITY_INVALID")
    raw_manifest = _read_exact(root, _MANIFEST_PATH, _MAX_MANIFEST_BYTES)
    committed = _committed_file_index(git)
    if _committed_digest(committed, _MANIFEST_PATH) != digest_bytes(raw_manifest):
        _fail("QUERY_BUILDER_SOURCE_MANIFEST_HEAD_MISMATCH")
    manifest = _parse_manifest(raw_manifest)
    expected = manifest["required_runtime_sha256"]
    required = tuple(_relative_path(value) for value in required_builder_files)
    if any(path not in expected or path not in git.tracked_files for path in required):
        _fail("QUERY_BUILDER_SOURCE_REQUIRED_FILE_UNBOUND")
    observed = _observed_source_rows(
        root, origins, expected, git, committed_files=committed,
    )
    if not set(required) <= {row["relative_path"] for row in observed}:
        _fail("QUERY_BUILDER_SOURCE_REQUIRED_FILE_NOT_LOADED")
    return _source_public_binding(root, git, raw_manifest, observed)


def _source_public_binding(
    root: Path, git: PinnedGitAuthority, raw_manifest: bytes,
    observed: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "repo_head_sha": git.repo_head_sha,
        "repo_root_digest": repository_root_digest(root),
        "backend_manifest_digest": digest_bytes(raw_manifest),
        "observed_source_manifest_digest": digest_bytes(canonical_json_bytes([
            {"relative_path": row["relative_path"], "manifest_sha256": row["manifest_sha256"]}
            for row in observed
        ])),
        "observed_loaded_sources_digest": digest_bytes(canonical_json_bytes(observed)),
        "loaded_source_count": len(observed),
        "loaded_source_bytes": sum(int(row["size"]) for row in observed),
        "git_executable_content_digest": git.git_executable_content_digest,
        "repository_state_digest": git.repository_state_digest,
        "manifest_bytes_verified": True,
        "observed_loaded_source_metadata_verified": True,
        "pinned_git_executable_verified": True,
        "repository_topology_snapshot_verified": True,
        "git_environment_sanitized": True,
    }


def _parse_manifest(raw: bytes) -> dict[str, Any]:
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        _fail("QUERY_BUILDER_SOURCE_MANIFEST_INVALID")
    if (
        type(value) is not dict
        or value.get("schema_version") != "reddog_backend_manifest.v3"
        or value.get("product") != "foundups-agent-reddog-backend"
        or value.get("backend_api_version") != 2
    ):
        _fail("QUERY_BUILDER_SOURCE_MANIFEST_INVALID")
    files, digests = value.get("required_runtime_files"), value.get("required_runtime_sha256")
    if type(files) is not list or type(digests) is not dict or len(files) > 10_000:
        _fail("QUERY_BUILDER_SOURCE_MANIFEST_INVALID")
    paths = [_relative_path(path) for path in files]
    if paths != sorted(paths) or len(paths) != len(set(path.casefold() for path in paths)):
        _fail("QUERY_BUILDER_SOURCE_MANIFEST_INVALID")
    if set(paths) != set(digests):
        _fail("QUERY_BUILDER_SOURCE_MANIFEST_INVALID")
    for path, digest in digests.items():
        if _relative_path(path) != path or type(digest) is not str or _HEX.fullmatch(digest) is None:
            _fail("QUERY_BUILDER_SOURCE_MANIFEST_INVALID")
    return value


def _observed_source_rows(
    root: Path, origins: Mapping[str, str], expected: Mapping[str, str],
    git: PinnedGitAuthority,
    committed_files: Mapping[str, tuple[int, str]] | None = None,
) -> list[dict[str, Any]]:
    rows, total = [], 0
    committed = dict(committed_files) if committed_files is not None else _committed_file_index(git)
    for relative in sorted(origins):
        if relative not in expected or relative not in git.tracked_files:
            _fail("QUERY_BUILDER_SOURCE_LOADED_ORIGIN_UNBOUND")
        payload = _read_exact(root, relative, _MAX_SOURCE_FILE_BYTES)
        normalized = payload.replace(b"\r\n", b"\n")
        if digest_bytes(normalized).removeprefix("sha256:") != expected[relative]:
            _fail("QUERY_BUILDER_SOURCE_MANIFEST_DIGEST_MISMATCH")
        if _committed_digest(committed, relative) != digest_bytes(payload):
            _fail("QUERY_BUILDER_SOURCE_HEAD_BLOB_MISMATCH")
        rows.append({
            "module": origins[relative], "relative_path": relative,
            "size": len(payload), "sha256": digest_bytes(payload),
            "manifest_sha256": expected[relative],
        })
        total += len(payload)
        if total > _MAX_SOURCE_BYTES:
            _fail("QUERY_BUILDER_SOURCE_LIMIT_EXCEEDED")
    if not rows:
        _fail("QUERY_BUILDER_SOURCE_LOADED_SET_EMPTY")
    return rows


def _module_origins(
    root: Path, modules: Mapping[str, ModuleType],
) -> dict[str, str]:
    origins: dict[str, str] = {}
    for name, module in modules.items():
        if not isinstance(name, str) or not isinstance(module, ModuleType):
            continue
        raw = getattr(module, "__file__", None)
        if type(raw) is not str or not _within(Path(raw), root):
            continue
        origin = Path(raw).absolute()
        relative = _relative_path(origin.relative_to(root.absolute()).as_posix())
        expected = root.joinpath(*relative.split("/")).absolute()
        if str(origin) != str(expected) or not relative.endswith(".py") or relative in origins:
            _fail("QUERY_BUILDER_SOURCE_LOADED_ORIGIN_INVALID")
        if getattr(module, "__cached__", None) and Path(str(module.__cached__)).exists():
            _fail("QUERY_BUILDER_SOURCE_BYTECODE_CACHE_PRESENT")
        origins[relative] = name
    return origins


def _committed_file_index(git: PinnedGitAuthority) -> dict[str, tuple[int, str]]:
    rows = git.committed_files
    if type(rows) is not tuple:
        _fail("QUERY_BUILDER_SOURCE_HEAD_BLOB_INVALID")
    result: dict[str, tuple[int, str]] = {}
    case_keys: set[str] = set()
    for row in rows:
        if type(row) is not tuple or len(row) != 3:
            _fail("QUERY_BUILDER_SOURCE_HEAD_BLOB_INVALID")
        path, size, digest = row
        relative = _relative_path(path)
        key = relative.casefold()
        if (
            type(size) is not int or size < 0 or not is_digest(digest)
            or relative in result or key in case_keys
        ):
            _fail("QUERY_BUILDER_SOURCE_HEAD_BLOB_INVALID")
        result[relative] = (size, digest)
        case_keys.add(key)
    return result


def _committed_digest(committed: Mapping[str, tuple[int, str]], path: str) -> str:
    row = committed.get(path)
    if row is None:
        _fail("QUERY_BUILDER_SOURCE_HEAD_BLOB_MISSING")
    return row[1]


def _read_exact(root: Path, relative: str, maximum: int) -> bytes:
    path = root.joinpath(*_relative_path(relative).split("/"))
    try:
        metadata = os.lstat(path)
        identity = confined_file_identity(metadata)
        if not stat.S_ISREG(metadata.st_mode) or identity.links != 1 or identity.size > maximum:
            _fail("QUERY_BUILDER_SOURCE_FILE_INVALID")
        proof = secure_digest_confined_file_impl(
            path, allowed_root=root, expected_identity=identity,
            max_bytes=max(identity.size, 1),
        )
        payload, cursor = secure_read_confined_bytes_impl(
            path, allowed_root=root, max_bytes=identity.size + 1,
        )
        require_unnamed_data_stream_only(path)
        stable = confined_file_identity(os.lstat(path)) == identity
    except QueryRuntimeBuilderSourceError:
        raise
    except Exception:
        _fail("QUERY_BUILDER_SOURCE_FILE_UNAVAILABLE")
    if (
        not stable or cursor != identity.size or proof.size != identity.size
        or proof.digest != digest_bytes(payload)
    ):
        _fail("QUERY_BUILDER_SOURCE_FILE_MUTATED")
    return payload


def _approved_root(value: Path | str) -> Path:
    raw, path = str(value), Path(value)
    if (
        not raw or "\0" in raw or not path.is_absolute()
        or path.drive.rstrip(":").upper() not in {"O", "E"}
        or any(part in {".", ".."} for part in path.parts)
        or unicodedata.normalize("NFC", raw) != raw
        or any(unicodedata.category(char) in {"Cc", "Cf", "Cs"} for char in raw)
    ):
        _fail("QUERY_BUILDER_SOURCE_ROOT_INVALID")
    try:
        root = path.resolve(strict=True)
        current = Path(path.anchor)
        for part in path.parts[1:]:
            current /= part
            metadata = os.lstat(current)
            if _is_link(current, metadata):
                _fail("QUERY_BUILDER_SOURCE_ROOT_INVALID")
            require_unnamed_data_stream_only(current)
    except QueryRuntimeBuilderSourceError:
        raise
    except OSError:
        _fail("QUERY_BUILDER_SOURCE_ROOT_INVALID")
    if str(root) != str(path.absolute()) or not root.is_dir():
        _fail("QUERY_BUILDER_SOURCE_ROOT_INVALID")
    return root


def _relative_path(value: object) -> str:
    if type(value) is not str:
        _fail("QUERY_BUILDER_SOURCE_PATH_INVALID")
    if (
        not value or len(value) > 512 or "\\" in value or ":" in value
        or value.startswith("/") or posixpath.normpath(value) != value
        or any(part in {"", ".", ".."} for part in value.split("/"))
        or unicodedata.normalize("NFC", value) != value
        or any(unicodedata.category(char) in {"Cc", "Cf", "Cs"} for char in value)
    ):
        _fail("QUERY_BUILDER_SOURCE_PATH_INVALID")
    return value


def _within(path: Path, root: Path) -> bool:
    try:
        path.absolute().relative_to(root.absolute())
        return True
    except ValueError:
        return False


def _is_link(path: Path, metadata: os.stat_result) -> bool:
    return bool(
        stat.S_ISLNK(metadata.st_mode)
        or int(getattr(metadata, "st_file_attributes", 0))
        & int(getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0))
        or getattr(path, "is_junction", lambda: False)()
    )


__all__ = [
    "QueryRuntimeBuilderSourceError", "prove_builder_source_authority",
]
