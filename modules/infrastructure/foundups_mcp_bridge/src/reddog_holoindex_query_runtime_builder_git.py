"""Pinned Git image and committed-byte proof for an inert evidence builder."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import posixpath
import re
import stat
from typing import Mapping, Sequence
import unicodedata

from modules.infrastructure.shared_utilities.runtime_artifact_windows_streams import (
    require_unnamed_data_stream_only,
)
from modules.infrastructure.wre_core.src.wre_git_bounded_io import run_bounded_stdout

from .reddog_holoindex_dependency_runtime_contract import (
    canonical_json_bytes,
    digest_bytes,
    is_digest,
)
from .reddog_holoindex_process_image import (
    ProcessExecutableCapability,
    ProcessExecutableProof,
    hold_process_executable_for_launch,
    prove_process_executable_path,
)


_HEAD = re.compile(r"[0-9a-f]{40}\Z")
_MAX_GIT_OUTPUT = 32 * 1024 * 1024
_MAX_SOURCE_BYTES = 128 * 1024 * 1024
_MAX_SOURCE_FILE_BYTES = 64 * 1024 * 1024
_MAX_BOUND_PATHS = 10_000
_MAX_GIT_IMAGE_BYTES = 256 * 1024 * 1024


class QueryRuntimeBuilderGitError(RuntimeError):
    """Stable fail-closed pinned-Git authority error."""


def _fail(code: str) -> None:
    raise QueryRuntimeBuilderGitError(code)


@dataclass(frozen=True)
class PinnedGitAuthority:
    repo_root: Path
    repo_head_sha: str
    git_executable_content_digest: str
    repository_state_digest: str
    tracked_files: frozenset[str]
    committed_files: tuple[tuple[str, int, str], ...]


def prove_pinned_git_authority(
    *, root: Path, expected_head: str, executable: Path,
    expected_digest: str, bound_paths: Sequence[str],
) -> PinnedGitAuthority:
    """Use one pinned O:/E: Git image and a bounded committed-blob batch."""

    head, paths = _validated_inputs(root, expected_head, expected_digest, bound_paths)
    topology_before = _git_topology_snapshot(root)
    try:
        proof = prove_process_executable_path(executable)
        actual_digest, observations = _held_git_observations(
            root, proof, head, paths, expected_digest,
        )
    except QueryRuntimeBuilderGitError:
        raise
    except Exception:
        _fail("QUERY_BUILDER_GIT_IMAGE_UNAVAILABLE")
    topology_after = _git_topology_snapshot(root)
    if topology_after != topology_before:
        _fail("QUERY_BUILDER_GIT_TOPOLOGY_MUTATED")
    top, actual_head, tracked_raw, flags_raw, committed = observations
    tracked = _validate_observations(
        root, head, top, actual_head, tracked_raw, flags_raw,
    )
    if not set(paths) <= tracked:
        _fail("QUERY_BUILDER_GIT_BOUND_FILE_UNTRACKED")
    state = {
        "head": head,
        "bound_head_blobs_digest": digest_bytes(canonical_json_bytes(committed)),
        "tracked_files_digest": digest_bytes(canonical_json_bytes(sorted(tracked))),
        "git_topology_digest": digest_bytes(canonical_json_bytes(topology_before)),
    }
    return PinnedGitAuthority(
        root, head, actual_digest, digest_bytes(canonical_json_bytes(state)),
        tracked, committed,
    )


def _validated_inputs(
    root: Path, expected_head: str, expected_digest: str,
    bound_paths: Sequence[str],
) -> tuple[str, tuple[str, ...]]:
    _validate_root(root)
    head = str(expected_head)
    if (
        _HEAD.fullmatch(head) is None or not is_digest(expected_digest)
        or len(bound_paths) > _MAX_BOUND_PATHS
    ):
        _fail("QUERY_BUILDER_GIT_EXPECTATION_INVALID")
    validated = tuple(_relative_path(path) for path in bound_paths)
    if (
        not validated or len(validated) != len(set(validated))
        or len(validated) != len(set(path.casefold() for path in validated))
    ):
        _fail("QUERY_BUILDER_GIT_EXPECTATION_INVALID")
    return head, tuple(sorted(validated))


def _run_git_observations(
    root: Path, proof: ProcessExecutableProof,
    capability: ProcessExecutableCapability, head: str, paths: Sequence[str],
) -> tuple[bytes, bytes, bytes, bytes, tuple[tuple[str, int, str], ...]]:
    environment = _git_environment(proof.path, root)
    try:
        prefix = _git_prefix(capability.launch_path, root)
        top = _git(prefix, root, environment, "rev-parse", "--show-toplevel", limit=4096)
        actual_head = _git(
            prefix, root, environment, "rev-parse", "--verify", "--end-of-options",
            "HEAD^{commit}", limit=128,
        )
        tracked = _git(prefix, root, environment, "ls-files", "-z", limit=_MAX_GIT_OUTPUT)
        flags = _git(
            prefix, root, environment, "ls-files", "-v", "-z",
            limit=_MAX_GIT_OUTPUT,
        )
        committed = _committed_file_rows(prefix, root, environment, head, paths)
    except QueryRuntimeBuilderGitError:
        raise
    except Exception:
        _fail("QUERY_BUILDER_GIT_EXECUTION_FAILED")
    return top, actual_head, tracked, flags, committed


def _held_git_observations(
    root: Path, proof: ProcessExecutableProof, head: str, paths: Sequence[str],
    expected_digest: str,
) -> tuple[str, tuple[bytes, bytes, bytes, bytes, tuple[tuple[str, int, str], ...]]]:
    with hold_process_executable_for_launch(proof) as capability:
        before = _hash_held_executable(capability, proof)
        if before != expected_digest:
            _fail("QUERY_BUILDER_GIT_IMAGE_MISMATCH")
        observations = _run_git_observations(root, proof, capability, head, paths)
        after = _hash_held_executable(capability, proof)
    if after != before:
        _fail("QUERY_BUILDER_GIT_IMAGE_MUTATED")
    return before, observations


def _validate_observations(
    root: Path, head: str, top: bytes, actual_head: bytes,
    tracked_raw: bytes, flags_raw: bytes,
) -> frozenset[str]:
    try:
        decoded_top = top.decode("utf-8", errors="strict").strip()
        decoded_head = actual_head.decode("ascii", errors="strict").strip()
    except UnicodeError:
        _fail("QUERY_BUILDER_GIT_OUTPUT_INVALID")
    if (
        str(Path(decoded_top).absolute()) != str(root.absolute())
        or decoded_head != head
    ):
        _fail("QUERY_BUILDER_GIT_REPOSITORY_STATE_INVALID")
    tracked = _parse_tracked(tracked_raw)
    _validate_index_flags(flags_raw, tracked)
    return tracked


def _git_prefix(executable: Path, root: Path) -> tuple[str, ...]:
    return (
        str(executable), "--no-replace-objects",
        "-c", f"core.hooksPath={os.devnull}",
        "-c", "core.fsmonitor=false", "-c", "core.untrackedCache=false",
        "-c", "submodule.recurse=false", "-C", str(root),
    )


def _git_environment(executable: Path, root: Path) -> dict[str, str]:
    allowed = ("SYSTEMROOT", "WINDIR", "COMSPEC", "PATHEXT")
    environment = {name: str(os.environ[name]) for name in allowed if os.environ.get(name)}
    temporary = Path(f"{root.drive}/tmp")
    if not temporary.is_dir():
        _fail("QUERY_BUILDER_GIT_TEMPORARY_ROOT_INVALID")
    environment.update({
        "PATH": str(executable.parent), "TEMP": str(temporary), "TMP": str(temporary),
        "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_OPTIONAL_LOCKS": "0", "GIT_TERMINAL_PROMPT": "0",
        "GIT_NO_LAZY_FETCH": "1",
        "LC_ALL": "C", "LANG": "C",
    })
    return environment


def _committed_file_rows(
    prefix: Sequence[str], root: Path, environment: Mapping[str, str],
    head: str, paths: Sequence[str],
) -> tuple[tuple[str, int, str], ...]:
    raw_tree = _git(
        prefix, root, environment, "ls-tree", "-r", "-z", "--full-tree", head,
        limit=_MAX_GIT_OUTPUT,
    )
    object_ids = _tree_blob_ids(raw_tree, paths)
    request = b"".join(object_ids[path].encode("ascii") + b"\n" for path in paths)
    raw_blobs = _git(
        prefix, root, environment, "cat-file", "--batch",
        limit=_MAX_SOURCE_BYTES + len(paths) * 128, stdin_bytes=request,
    )
    return _batch_blob_rows(raw_blobs, paths, object_ids)


def _tree_blob_ids(raw: bytes, paths: Sequence[str]) -> dict[str, str]:
    wanted, result = set(paths), {}
    try:
        records = raw.split(b"\0")
        if records[-1:] != [b""]:
            _fail("QUERY_BUILDER_GIT_TREE_INVALID")
        for record in records[:-1]:
            header, raw_path = record.split(b"\t", 1)
            mode, kind, object_id = header.decode("ascii").split(" ")
            path = raw_path.decode("utf-8")
            if path not in wanted:
                continue
            if (
                mode not in {"100644", "100755"} or kind != "blob"
                or len(object_id) != 40
                or any(char not in "0123456789abcdef" for char in object_id)
                or path in result
            ):
                _fail("QUERY_BUILDER_GIT_TREE_INVALID")
            result[path] = object_id
    except QueryRuntimeBuilderGitError:
        raise
    except (UnicodeError, ValueError):
        _fail("QUERY_BUILDER_GIT_TREE_INVALID")
    if set(result) != wanted:
        _fail("QUERY_BUILDER_GIT_HEAD_BLOB_MISSING")
    return result


def _batch_blob_rows(
    raw: bytes, paths: Sequence[str], object_ids: Mapping[str, str],
) -> tuple[tuple[str, int, str], ...]:
    cursor, rows, total = 0, [], 0
    for path in paths:
        line_end = raw.find(b"\n", cursor)
        if line_end < 0:
            _fail("QUERY_BUILDER_GIT_BATCH_INVALID")
        object_id, size = _batch_header(raw[cursor:line_end], object_ids[path])
        end = line_end + 1 + size
        payload = raw[line_end + 1:end]
        if len(payload) != size or raw[end:end + 1] != b"\n":
            _fail("QUERY_BUILDER_GIT_BATCH_INVALID")
        framed = f"blob {size}\0".encode("ascii") + payload
        if hashlib.sha1(framed).hexdigest() != object_id:
            _fail("QUERY_BUILDER_GIT_BLOB_ID_MISMATCH")
        rows.append((path, size, digest_bytes(payload)))
        total += size
        if total > _MAX_SOURCE_BYTES:
            _fail("QUERY_BUILDER_GIT_SOURCE_LIMIT_EXCEEDED")
        cursor = end + 1
    if cursor != len(raw):
        _fail("QUERY_BUILDER_GIT_BATCH_INVALID")
    return tuple(rows)


def _batch_header(raw: bytes, expected_id: str) -> tuple[str, int]:
    try:
        object_id, kind, raw_size = raw.decode("ascii").split(" ")
        size = int(raw_size)
    except (UnicodeError, ValueError):
        _fail("QUERY_BUILDER_GIT_BATCH_INVALID")
    if object_id != expected_id or kind != "blob" or size < 0:
        _fail("QUERY_BUILDER_GIT_BATCH_INVALID")
    if size > _MAX_SOURCE_FILE_BYTES:
        _fail("QUERY_BUILDER_GIT_SOURCE_LIMIT_EXCEEDED")
    return object_id, size


def _git(
    prefix: Sequence[str], root: Path, environment: Mapping[str, str],
    *arguments: str, limit: int, stdin_bytes: bytes | None = None,
) -> bytes:
    return run_bounded_stdout(
        (*prefix, *arguments), cwd=root, max_bytes=limit, timeout_s=30,
        environment=environment, stdin_bytes=stdin_bytes,
    )


def _git_topology_snapshot(root: Path) -> tuple[tuple[object, ...], ...]:
    git_dir, pending, path_bytes = root / ".git", [root / ".git"], 0
    try:
        metadata = os.lstat(git_dir)
        if not stat.S_ISDIR(metadata.st_mode) or _is_link(git_dir, metadata):
            _fail("QUERY_BUILDER_GIT_TOPOLOGY_INVALID")
        require_unnamed_data_stream_only(git_dir)
        rows: list[tuple[object, ...]] = [(
            "", "d", int(metadata.st_dev), int(metadata.st_ino),
            int(metadata.st_size), int(metadata.st_mtime_ns),
            int(getattr(metadata, "st_file_attributes", 0)),
        )]
        for forbidden in ("commondir", "gitdir", "objects/info/alternates"):
            if (git_dir / forbidden).exists():
                _fail("QUERY_BUILDER_GIT_TOPOLOGY_INVALID")
        while pending:
            path_bytes = _scan_git_directory(
                git_dir, pending.pop(), pending, rows, path_bytes,
            )
    except QueryRuntimeBuilderGitError:
        raise
    except (OSError, ValueError):
        _fail("QUERY_BUILDER_GIT_TOPOLOGY_INVALID")
    return tuple(sorted(rows, key=lambda row: str(row[0]).casefold()))


def _scan_git_directory(
    git_dir: Path, directory: Path, pending: list[Path],
    rows: list[tuple[object, ...]], path_bytes: int,
) -> int:
    entries = tuple(sorted(os.scandir(directory), key=lambda item: item.name.casefold()))
    names = tuple(entry.name.casefold() for entry in entries)
    if len(names) != len(set(names)):
        _fail("QUERY_BUILDER_GIT_TOPOLOGY_INVALID")
    for entry in entries:
        path, metadata = Path(entry.path), os.lstat(entry.path)
        relative = path.relative_to(git_dir).as_posix()
        path_bytes += len(relative.encode("utf-8"))
        is_directory = stat.S_ISDIR(metadata.st_mode)
        if (
            _is_link(path, metadata) or path_bytes > 64 * 1024 * 1024
            or len(rows) >= 200_000
            or (not is_directory and (
                not stat.S_ISREG(metadata.st_mode)
                or int(getattr(metadata, "st_nlink", 1)) != 1
            ))
        ):
            _fail("QUERY_BUILDER_GIT_TOPOLOGY_INVALID")
        require_unnamed_data_stream_only(path)
        rows.append((
            relative, "d" if is_directory else "f", int(metadata.st_dev),
            int(metadata.st_ino), int(metadata.st_size), int(metadata.st_mtime_ns),
            int(getattr(metadata, "st_file_attributes", 0)),
        ))
        if is_directory:
            pending.append(path)
    return path_bytes


def _hash_held_executable(
    capability: ProcessExecutableCapability, proof: ProcessExecutableProof,
) -> str:
    if (
        type(capability) is not ProcessExecutableCapability
        or type(proof) is not ProcessExecutableProof
        or not proof.path.is_absolute()
        or proof.path.drive.rstrip(":").upper() not in {"O", "E"}
        or proof.identity[2] <= 0 or proof.identity[2] > _MAX_GIT_IMAGE_BYTES
    ):
        _fail("QUERY_BUILDER_GIT_VOLUME_INVALID")
    duplicate = -1
    try:
        if _descriptor_identity(os.fstat(capability.descriptor)) != proof.identity:
            _fail("QUERY_BUILDER_GIT_IMAGE_UNAVAILABLE")
        require_unnamed_data_stream_only(proof.path)
        duplicate = os.dup(capability.descriptor)
        os.lseek(duplicate, 0, os.SEEK_SET)
        hasher, total = hashlib.sha256(), 0
        with os.fdopen(duplicate, "rb", closefd=True) as stream:
            duplicate = -1
            while chunk := stream.read(64 * 1024):
                total += len(chunk)
                if total > _MAX_GIT_IMAGE_BYTES:
                    _fail("QUERY_BUILDER_GIT_IMAGE_UNAVAILABLE")
                hasher.update(chunk)
        if total != proof.identity[2] or _descriptor_identity(
            os.fstat(capability.descriptor)
        ) != proof.identity:
            _fail("QUERY_BUILDER_GIT_IMAGE_UNAVAILABLE")
    except Exception:
        _fail("QUERY_BUILDER_GIT_IMAGE_UNAVAILABLE")
    finally:
        if duplicate >= 0:
            os.close(duplicate)
    return "sha256:" + hasher.hexdigest()


def _descriptor_identity(metadata: os.stat_result) -> tuple[int, int, int, int, int, int]:
    return (
        int(metadata.st_dev), int(metadata.st_ino), int(metadata.st_size),
        int(metadata.st_mtime_ns), int(stat.S_IFMT(metadata.st_mode)),
        int(getattr(metadata, "st_nlink", 1)),
    )


def _parse_tracked(raw: bytes) -> frozenset[str]:
    try:
        values = raw.decode("utf-8").split("\0")
    except UnicodeDecodeError:
        _fail("QUERY_BUILDER_GIT_TRACKED_SET_INVALID")
    if values[-1:] != [""]:
        _fail("QUERY_BUILDER_GIT_TRACKED_SET_INVALID")
    paths = tuple(_relative_path(value) for value in values[:-1])
    if len(paths) != len(set(path.casefold() for path in paths)):
        _fail("QUERY_BUILDER_GIT_TRACKED_SET_INVALID")
    return frozenset(paths)


def _validate_index_flags(raw: bytes, tracked: frozenset[str]) -> None:
    try:
        records = raw.decode("utf-8").split("\0")
    except UnicodeDecodeError:
        _fail("QUERY_BUILDER_GIT_INDEX_FLAGS_INVALID")
    if records[-1:] != [""]:
        _fail("QUERY_BUILDER_GIT_INDEX_FLAGS_INVALID")
    observed = []
    for record in records[:-1]:
        if len(record) < 3 or record[0:2] != "H ":
            _fail("QUERY_BUILDER_GIT_INDEX_FLAGS_INVALID")
        observed.append(_relative_path(record[2:]))
    if (
        frozenset(observed) != tracked
        or len(observed) != len(set(path.casefold() for path in observed))
    ):
        _fail("QUERY_BUILDER_GIT_INDEX_FLAGS_INVALID")


def _relative_path(value: object) -> str:
    if (
        type(value) is not str or not value or len(value) > 512
        or "\\" in value or ":" in value or value.startswith("/")
        or any(part in {"", ".", ".."} for part in value.split("/"))
        or posixpath.normpath(value) != value
        or unicodedata.normalize("NFC", value) != value
        or any(unicodedata.category(char) in {"Cc", "Cf", "Cs"} for char in value)
    ):
        _fail("QUERY_BUILDER_GIT_PATH_INVALID")
    return value


def _validate_root(root: Path) -> None:
    raw = str(root)
    if (
        not root.is_absolute() or root.drive.rstrip(":").upper() not in {"O", "E"}
        or unicodedata.normalize("NFC", raw) != raw
        or any(unicodedata.category(char) in {"Cc", "Cf", "Cs"} for char in raw)
        or any(part in {".", ".."} for part in root.parts)
    ):
        _fail("QUERY_BUILDER_GIT_EXPECTATION_INVALID")
    try:
        resolved = root.resolve(strict=True)
        current = Path(root.anchor)
        for part in root.parts[1:]:
            current /= part
            metadata = os.lstat(current)
            if _is_link(current, metadata):
                _fail("QUERY_BUILDER_GIT_EXPECTATION_INVALID")
            require_unnamed_data_stream_only(current)
    except QueryRuntimeBuilderGitError:
        raise
    except (OSError, ValueError):
        _fail("QUERY_BUILDER_GIT_EXPECTATION_INVALID")
    if str(resolved) != str(root.absolute()) or not root.is_dir():
        _fail("QUERY_BUILDER_GIT_EXPECTATION_INVALID")


def _is_link(path: Path, metadata: os.stat_result) -> bool:
    return bool(
        stat.S_ISLNK(metadata.st_mode)
        or int(getattr(metadata, "st_file_attributes", 0))
        & int(getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0))
        or getattr(path, "is_junction", lambda: False)()
    )


__all__ = [
    "PinnedGitAuthority", "QueryRuntimeBuilderGitError",
    "prove_pinned_git_authority",
]
