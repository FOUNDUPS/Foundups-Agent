"""Exact repository/source authority for inert query-runtime candidates."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
from typing import Any, Callable, Mapping

from holo_index.repository_state import (
    read_repository_state,
    repository_root_digest,
)
from modules.infrastructure.shared_utilities.runtime_artifact_confined_byte_reader import (
    confined_file_identity,
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


_HEAD = re.compile(r"[0-9a-f]{40}\Z")
_HEX = re.compile(r"[0-9a-f]{64}\Z")
_MANIFEST_KEYS = frozenset({
    "schema_version", "product", "backend_api_version",
    "runtime_dependency_graph_version", "required_executable_files",
    "required_bridge_files", "required_bridge_sha256", "required_runtime_files",
    "required_runtime_sha256", "required_repository_markers",
})
_PUBLIC_KEYS = frozenset({
    "repo_head_sha", "repo_root_digest", "repository_state_digest",
    "verified_runtime_closure_digest", "runtime_file_count",
    "runtime_file_bytes", "runtime_source_bytes_verified",
    "phase2a_module_set_digest", "phase2a_module_count",
    "phase2a_module_bytes", "phase2a_module_set_verified",
})
_SOURCE_MODULE_PATH = (
    "modules/infrastructure/foundups_mcp_bridge/src/"
    "reddog_holoindex_query_runtime_candidate_source.py"
)
_CANDIDATE_SOURCE_FILES = tuple(sorted((
    "modules/infrastructure/foundups_mcp_bridge/src/"
    "reddog_holoindex_query_distribution_graph.py",
    "modules/infrastructure/foundups_mcp_bridge/src/"
    "reddog_holoindex_query_distribution_metadata.py",
    "modules/infrastructure/foundups_mcp_bridge/src/"
    "reddog_holoindex_query_runtime_candidate_binding.py",
    "modules/infrastructure/foundups_mcp_bridge/src/"
    "reddog_holoindex_query_runtime_candidate_contract.py",
    "modules/infrastructure/foundups_mcp_bridge/src/"
    "reddog_holoindex_query_runtime_candidate_descriptor.py",
    "modules/infrastructure/foundups_mcp_bridge/src/"
    "reddog_holoindex_query_runtime_candidate_inputs.py",
    "modules/infrastructure/foundups_mcp_bridge/src/"
    "reddog_holoindex_query_runtime_candidate_record_contract.py",
    _SOURCE_MODULE_PATH,
)))
_MAX_MANIFEST_BYTES = 4 * 1024 * 1024
_MAX_SOURCE_FILE_BYTES = 64 * 1024 * 1024
_MAX_SOURCE_BYTES = 512 * 1024 * 1024
_MAX_SOURCE_FILES = 10_000


class CandidateSourceAuthorityError(RuntimeError):
    """Stable fail-closed repository/source authority error."""


def _fail(code: str) -> None:
    raise CandidateSourceAuthorityError(code)


@dataclass(frozen=True)
class CandidateSourceAuthority:
    repo_root: Path
    repo_head_sha: str
    repo_root_digest: str
    repository_state_digest: str
    backend_manifest_digest: str
    verified_runtime_closure_digest: str
    runtime_file_count: int
    runtime_file_bytes: int
    runtime_source_bytes_verified: bool
    phase2a_module_set_digest: str
    phase2a_module_count: int
    phase2a_module_bytes: int
    phase2a_module_set_verified: bool

    @property
    def public_binding(self) -> Mapping[str, Any]:
        return {
            "repo_head_sha": self.repo_head_sha,
            "repo_root_digest": self.repo_root_digest,
            "repository_state_digest": self.repository_state_digest,
            "verified_runtime_closure_digest": self.verified_runtime_closure_digest,
            "runtime_file_count": self.runtime_file_count,
            "runtime_file_bytes": self.runtime_file_bytes,
            "runtime_source_bytes_verified": self.runtime_source_bytes_verified,
            "phase2a_module_set_digest": self.phase2a_module_set_digest,
            "phase2a_module_count": self.phase2a_module_count,
            "phase2a_module_bytes": self.phase2a_module_bytes,
            "phase2a_module_set_verified": self.phase2a_module_set_verified,
        }


def verify_candidate_source_authority(
    *, source_root: Path | str, expected_repo_head_sha: str,
) -> CandidateSourceAuthority:
    """Verify source authority with the production repository-state reader."""

    return _verify_candidate_source_authority(
        source_root=source_root, expected_repo_head_sha=expected_repo_head_sha,
        state_reader=read_repository_state,
        executing_source_paths=_phase2a_executing_sources(),
        candidate_source_files=_CANDIDATE_SOURCE_FILES,
    )


def _verify_candidate_source_authority_for_test(
    *, source_root: Path | str, expected_repo_head_sha: str,
    state_reader: Callable[[Path], Any],
    candidate_source_files: tuple[str, ...] = ("runtime.py",),
    executing_source_relative: str = "runtime.py",
    executing_source_paths: Mapping[str, Path] | None = None,
) -> CandidateSourceAuthority:
    """Exercise source verification with a controlled repository-state reader."""

    return _verify_candidate_source_authority(
        source_root=source_root, expected_repo_head_sha=expected_repo_head_sha,
        state_reader=state_reader,
        executing_source_paths=(
            dict(executing_source_paths)
            if executing_source_paths is not None
            else {executing_source_relative: Path(source_root) / executing_source_relative}
        ),
        candidate_source_files=candidate_source_files,
    )


def _verify_candidate_source_authority(
    *, source_root: Path | str, expected_repo_head_sha: str,
    state_reader: Callable[[Path], Any],
    executing_source_paths: Mapping[str, Path],
    candidate_source_files: tuple[str, ...],
) -> CandidateSourceAuthority:
    """Verify exact-HEAD identity, backend closure, and declared Phase-2A files."""

    root = _approved_absolute_root(source_root)
    head = str(expected_repo_head_sha or "").lower()
    if _HEAD.fullmatch(head) is None:
        _fail("QUERY_RUNTIME_CANDIDATE_SOURCE_HEAD_INVALID")
    before = _repository_state(root, head, state_reader)
    _bind_executing_sources(root, executing_source_paths, candidate_source_files)
    manifest = _manifest(root)
    rows, total = _verified_runtime_rows(root, manifest)
    candidate_rows, candidate_total = _verified_candidate_rows(
        root, candidate_source_files,
    )
    _verify_repository_markers(root, manifest["required_repository_markers"])
    after = _repository_state(root, head, state_reader)
    if after != before:
        _fail("QUERY_RUNTIME_CANDIDATE_SOURCE_MUTATED_DURING_SCAN")
    return CandidateSourceAuthority(
        root, head, repository_root_digest(root), before.state_digest,
        _backend_manifest_digest(manifest), digest_bytes(canonical_json_bytes(rows)),
        len(rows), total, True,
        digest_bytes(canonical_json_bytes(candidate_rows)),
        len(candidate_rows), candidate_total, True,
    )


def validate_candidate_source_public_binding(value: object) -> dict[str, Any]:
    """Validate the path-free source authority carried by candidate identity."""

    if type(value) is not dict or frozenset(value) != _PUBLIC_KEYS:
        _fail("QUERY_RUNTIME_CANDIDATE_SOURCE_BINDING_INVALID")
    source = dict(value)
    if (
        _HEAD.fullmatch(str(source.get("repo_head_sha") or "")) is None
        or any(not is_digest(source.get(name)) for name in (
            "repo_root_digest", "repository_state_digest",
            "verified_runtime_closure_digest", "phase2a_module_set_digest",
        ))
        or any(
            type(source.get(name)) is not int or source[name] <= 0
            for name in (
                "runtime_file_count", "runtime_file_bytes",
                "phase2a_module_count", "phase2a_module_bytes",
            )
        )
        or source.get("runtime_source_bytes_verified") is not True
        or source.get("phase2a_module_set_verified") is not True
    ):
        _fail("QUERY_RUNTIME_CANDIDATE_SOURCE_BINDING_INVALID")
    return source


def _manifest(root: Path) -> dict[str, Any]:
    raw = _read_confined(root / "scripts/reddog_backend_manifest.json", root, _MAX_MANIFEST_BYTES)
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError):
        _fail("QUERY_RUNTIME_CANDIDATE_SOURCE_MANIFEST_INVALID")
    if type(value) is not dict or frozenset(value) != _MANIFEST_KEYS:
        _fail("QUERY_RUNTIME_CANDIDATE_SOURCE_MANIFEST_INVALID")
    if (
        value.get("schema_version") != "reddog_backend_manifest.v3"
        or value.get("product") != "foundups-agent-reddog-backend"
        or type(value.get("backend_api_version")) is not int
        or value["backend_api_version"] != 2
        or type(value.get("runtime_dependency_graph_version")) is not int
        or value["runtime_dependency_graph_version"] != 2
    ):
        _fail("QUERY_RUNTIME_CANDIDATE_SOURCE_MANIFEST_INVALID")
    _validate_manifest_sets(value)
    return value


def _backend_manifest_digest(value: Mapping[str, Any]) -> str:
    """Match the backend generator's canonical JSON digest (without a newline)."""

    payload = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
    ).encode("ascii")
    return f"sha256:{hashlib.sha256(payload).hexdigest()}"


def _validate_manifest_sets(value: Mapping[str, Any]) -> None:
    runtime = _path_list(
        value.get("required_runtime_files"), _MAX_SOURCE_FILES, ordered=True,
    )
    executables = _path_list(value.get("required_executable_files"), 256)
    bridges = _path_list(value.get("required_bridge_files"), 256)
    markers = _path_list(value.get("required_repository_markers"), 64)
    runtime_hashes = _digest_map(
        value.get("required_runtime_sha256"), _MAX_SOURCE_FILES, ordered=True,
    )
    bridge_hashes = _digest_map(value.get("required_bridge_sha256"), 256)
    if (
        set(runtime) != set(runtime_hashes)
        or not set(bridges) <= set(executables) <= set(runtime)
        or set(bridges) != set(bridge_hashes)
        or any(bridge_hashes[path] != runtime_hashes[path] for path in bridges)
        or not markers
    ):
        _fail("QUERY_RUNTIME_CANDIDATE_SOURCE_MANIFEST_INVALID")


def _verified_runtime_rows(
    root: Path, manifest: Mapping[str, Any],
) -> tuple[list[Mapping[str, Any]], int]:
    rows: list[Mapping[str, Any]] = []
    total = 0
    expected = manifest["required_runtime_sha256"]
    for relative in manifest["required_runtime_files"]:
        payload = _read_confined(root.joinpath(*relative.split("/")), root, _MAX_SOURCE_FILE_BYTES)
        actual = hashlib.sha256(payload.replace(b"\r\n", b"\n")).hexdigest()
        if actual != expected[relative]:
            _fail("QUERY_RUNTIME_CANDIDATE_SOURCE_DIGEST_MISMATCH")
        rows.append({"relative_path": relative, "size": len(payload), "digest": actual})
        total += len(payload)
        if total > _MAX_SOURCE_BYTES:
            _fail("QUERY_RUNTIME_CANDIDATE_SOURCE_LIMIT_EXCEEDED")
    return rows, total


def _verified_candidate_rows(
    root: Path, values: tuple[str, ...],
) -> tuple[list[Mapping[str, Any]], int]:
    paths = _path_list(list(values), 64, ordered=True)
    rows: list[Mapping[str, Any]] = []
    total = 0
    for relative in paths:
        payload = _read_confined(
            root.joinpath(*relative.split("/")), root, _MAX_SOURCE_FILE_BYTES,
        ).replace(b"\r\n", b"\n")
        rows.append({
            "relative_path": relative, "size": len(payload),
            "digest": hashlib.sha256(payload).hexdigest(),
        })
        total += len(payload)
        if total > _MAX_SOURCE_BYTES:
            _fail("QUERY_RUNTIME_CANDIDATE_SOURCE_LIMIT_EXCEEDED")
    return rows, total


def _phase2a_executing_sources() -> Mapping[str, Path]:
    rows: dict[str, Path] = {}
    for relative in _CANDIDATE_SOURCE_FILES:
        module_name = relative.removesuffix(".py").replace("/", ".")
        module = sys.modules.get(module_name)
        path = getattr(module, "__file__", None)
        if type(path) is not str:
            _fail("QUERY_RUNTIME_CANDIDATE_EXECUTING_SOURCE_INVALID")
        rows[relative] = Path(path)
    return rows


def _bind_executing_sources(
    root: Path, observed: Mapping[str, Path], expected_files: tuple[str, ...],
) -> None:
    if set(observed) != set(expected_files):
        _fail("QUERY_RUNTIME_CANDIDATE_EXECUTING_SOURCE_INVALID")
    for relative in expected_files:
        expected = root.joinpath(*_relative_path(relative).split("/"))
        try:
            observed_path = observed[relative].resolve(strict=True)
            expected_path = expected.resolve(strict=True)
        except (KeyError, OSError):
            _fail("QUERY_RUNTIME_CANDIDATE_EXECUTING_SOURCE_INVALID")
        if os.path.normcase(str(observed_path)) != os.path.normcase(str(expected_path)):
            _fail("QUERY_RUNTIME_CANDIDATE_EXECUTING_SOURCE_INVALID")


def _verify_repository_markers(root: Path, values: list[str]) -> None:
    for relative in values:
        target = root.joinpath(*relative.split("/"))
        try:
            secure_read_confined_bytes_impl(target, allowed_root=root, max_bytes=1)
            require_unnamed_data_stream_only(target)
        except Exception as exc:
            raise CandidateSourceAuthorityError(
                "QUERY_RUNTIME_CANDIDATE_SOURCE_MARKER_INVALID"
            ) from exc


def _read_confined(path: Path, root: Path, maximum: int) -> bytes:
    try:
        before = os.lstat(path)
        identity = confined_file_identity(before)
        if not stat.S_ISREG(before.st_mode) or identity.links != 1 or identity.size > maximum:
            _fail("QUERY_RUNTIME_CANDIDATE_SOURCE_FILE_INVALID")
        payload, cursor = secure_read_confined_bytes_impl(
            path, allowed_root=root, max_bytes=identity.size + 1,
        )
        require_unnamed_data_stream_only(path)
        stable = confined_file_identity(os.lstat(path)) == identity
    except CandidateSourceAuthorityError:
        raise
    except Exception as exc:
        raise CandidateSourceAuthorityError(
            "QUERY_RUNTIME_CANDIDATE_SOURCE_FILE_INVALID"
        ) from exc
    if not stable or cursor != identity.size or len(payload) != identity.size:
        _fail("QUERY_RUNTIME_CANDIDATE_SOURCE_FILE_CHANGED")
    return payload


def _path_list(value: object, maximum: int, *, ordered: bool = False) -> list[str]:
    if type(value) is not list or not value or len(value) > maximum:
        _fail("QUERY_RUNTIME_CANDIDATE_SOURCE_MANIFEST_INVALID")
    rows = [_relative_path(item) for item in value]
    if (
        (ordered and rows != sorted(rows))
        or len(rows) != len(set(path.casefold() for path in rows))
    ):
        _fail("QUERY_RUNTIME_CANDIDATE_SOURCE_MANIFEST_INVALID")
    return rows


def _digest_map(
    value: object, maximum: int, *, ordered: bool = False,
) -> dict[str, str]:
    if type(value) is not dict or not value or len(value) > maximum:
        _fail("QUERY_RUNTIME_CANDIDATE_SOURCE_MANIFEST_INVALID")
    rows: dict[str, str] = {}
    for path, digest in value.items():
        canonical = _relative_path(path)
        if canonical in rows or type(digest) is not str or _HEX.fullmatch(digest) is None:
            _fail("QUERY_RUNTIME_CANDIDATE_SOURCE_MANIFEST_INVALID")
        rows[canonical] = digest
    if ordered and list(rows) != sorted(rows):
        _fail("QUERY_RUNTIME_CANDIDATE_SOURCE_MANIFEST_INVALID")
    return rows


def _relative_path(value: object) -> str:
    if (
        type(value) is not str or not value or len(value) > 512
        or "\\" in value or ":" in value or value.startswith("/")
        or any(part in {"", ".", ".."} for part in value.split("/"))
    ):
        _fail("QUERY_RUNTIME_CANDIDATE_SOURCE_MANIFEST_INVALID")
    return value


def _repository_state(root: Path, head: str, reader: Callable[[Path], Any]) -> Any:
    state = reader(root)
    if not getattr(state, "proven_clean", False) or getattr(state, "head_sha", "") != head:
        _fail("QUERY_RUNTIME_CANDIDATE_SOURCE_STATE_INVALID")
    if not is_digest(getattr(state, "state_digest", "")):
        _fail("QUERY_RUNTIME_CANDIDATE_SOURCE_STATE_INVALID")
    return state


def _approved_absolute_root(value: Path | str) -> Path:
    path = Path(value)
    raw = str(value)
    if (
        not raw or len(raw) > 2048 or "\x00" in raw or not path.is_absolute()
        or path.drive.rstrip(":").upper() not in {"O", "E"}
        or any(part in {".", ".."} for part in path.parts)
        or _contains_link_component(path)
    ):
        _fail("QUERY_RUNTIME_CANDIDATE_SOURCE_ROOT_INVALID")
    try:
        root = path.resolve(strict=True)
    except OSError:
        _fail("QUERY_RUNTIME_CANDIDATE_SOURCE_ROOT_INVALID")
    if (
        root.drive.rstrip(":").upper() not in {"O", "E"}
        or not root.is_dir() or _contains_link_component(root)
    ):
        _fail("QUERY_RUNTIME_CANDIDATE_SOURCE_ROOT_INVALID")
    return root


def _contains_link_component(path: Path) -> bool:
    current = Path(path.anchor)
    for component in path.parts:
        if component == path.anchor:
            continue
        current /= component
        try:
            metadata = os.lstat(current)
        except OSError:
            _fail("QUERY_RUNTIME_CANDIDATE_SOURCE_ROOT_INVALID")
        attributes = int(getattr(metadata, "st_file_attributes", 0))
        if (
            stat.S_ISLNK(metadata.st_mode)
            or attributes & int(getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0))
            or bool(getattr(current, "is_junction", lambda: False)())
        ):
            return True
    return False


__all__ = [
    "CandidateSourceAuthority", "CandidateSourceAuthorityError",
    "validate_candidate_source_public_binding", "verify_candidate_source_authority",
]
