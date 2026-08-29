"""Exact ``packaging`` ownership proof for an inert query evidence builder."""

from __future__ import annotations

import base64
import csv
from dataclasses import dataclass
from email.parser import BytesParser
import importlib.machinery
import io
import os
from pathlib import Path
import re
import stat
import sys
from types import ModuleType
from typing import Any, Mapping

from modules.infrastructure.shared_utilities.runtime_artifact_confined_byte_reader import (
    confined_file_identity,
    secure_digest_confined_file_impl,
    secure_read_confined_bytes_impl,
)
from modules.infrastructure.shared_utilities.runtime_artifact_windows_streams import (
    require_unnamed_data_stream_only,
)

from .reddog_holoindex_dependency_runtime_contract import (
    DependencyRuntimeBinding,
    canonical_relative_path,
    canonical_json_bytes,
    dependency_tree_digest,
    digest_bytes,
    validate_inventory,
)
from .reddog_holoindex_dependency_runtime_descriptor import (
    verify_dependency_runtime_generation,
)
from .reddog_holoindex_artifact_manifest import ModelCopyLimits, snapshot_artifact_files
from .reddog_holoindex_query_runtime_builder_contract import (
    BuilderPackagingAuthority,
    _packaging_authority_capability,
)


_NAME = "packaging"
_VERSION = "26.0"
_DIST_INFO = "packaging-26.0.dist-info"
_RECORD_SIZE = re.compile(r"(?:0|[1-9][0-9]*)\Z")
_REQUIRED_MODULES = (
    "packaging",
    "packaging.markers",
    "packaging.requirements",
    "packaging.specifiers",
    "packaging.utils",
    "packaging.version",
)
_FORBIDDEN_SUFFIXES = (
    ".pyc", ".pyo", ".pyd", ".dll", ".exe", ".zip", ".egg-link",
)
_FORBIDDEN_NAMES = {"direct_url.json", "sitecustomize.py", "usercustomize.py"}


class QueryRuntimeBuilderPackagingError(RuntimeError):
    """Stable fail-closed packaging authority error."""


def _fail(code: str) -> None:
    raise QueryRuntimeBuilderPackagingError(code)


@dataclass(frozen=True)
class _PackagingOwnershipProof:
    """Private verified ownership state retained for loaded-origin proof."""

    site_packages_root: Path
    dependency_inventory_digest: str
    record_digest: str
    owned_files_digest: str
    owned_file_count: int
    owned_file_bytes: int
    files: tuple[tuple[str, int, str], ...]


def prove_builder_packaging_authority(
    *, dependency_verification_kwargs: Mapping[str, Any],
    dependency_inventory: Mapping[str, Any],
) -> BuilderPackagingAuthority:
    """Atomically bind source-only ownership and every loaded packaging origin."""

    try:
        before = verify_dependency_runtime_generation(**dict(dependency_verification_kwargs))
        authority = _prove_builder_packaging_authority(
            dependency_runtime=before,
            dependency_inventory=dependency_inventory,
            modules=sys.modules,
        )
        after = verify_dependency_runtime_generation(**dict(dependency_verification_kwargs))
    except QueryRuntimeBuilderPackagingError:
        raise
    except Exception:
        _fail("QUERY_BUILDER_PACKAGING_AUTHORITY_UNAVAILABLE")
    if after != before:
        _fail("QUERY_BUILDER_PACKAGING_RUNTIME_MUTATED_DURING_PROOF")
    return authority


def _prove_builder_packaging_authority_for_test(
    *, dependency_runtime: DependencyRuntimeBinding,
    dependency_inventory: Mapping[str, Any], modules: Mapping[str, ModuleType],
) -> BuilderPackagingAuthority:
    """Private deterministic seam; production never accepts an injected table."""

    return _prove_builder_packaging_authority(
        dependency_runtime=dependency_runtime,
        dependency_inventory=dependency_inventory,
        modules=modules,
    )


def _prove_builder_packaging_authority(
    *, dependency_runtime: DependencyRuntimeBinding,
    dependency_inventory: Mapping[str, Any], modules: Mapping[str, ModuleType],
) -> BuilderPackagingAuthority:
    before = _prove_packaging_dependency_ownership(
        dependency_runtime=dependency_runtime,
        dependency_inventory=dependency_inventory,
    )
    loaded_before = _loaded_packaging_binding(before, modules)
    after = _prove_packaging_dependency_ownership(
        dependency_runtime=dependency_runtime,
        dependency_inventory=dependency_inventory,
    )
    loaded_after = _loaded_packaging_binding(after, modules)
    if after != before or loaded_after != loaded_before:
        _fail("QUERY_BUILDER_PACKAGING_MUTATED_DURING_PROOF")
    return _packaging_authority_capability(loaded_after)


def _prove_packaging_dependency_ownership(
    *, dependency_runtime: DependencyRuntimeBinding,
    dependency_inventory: Mapping[str, Any],
) -> _PackagingOwnershipProof:
    """Bind one source-only packaging 26.0 payload to its sealed inventory."""

    if type(dependency_runtime) is not DependencyRuntimeBinding:
        _fail("QUERY_BUILDER_PACKAGING_RUNTIME_INVALID")
    inventory = validate_inventory(dependency_inventory)
    _bind_inventory(dependency_runtime, inventory)
    root = _approved_site_root(dependency_runtime)
    rows = tuple(
        (str(row["path"]), int(row["size"]), str(row["sha256"]))
        for row in inventory["files"]
    )
    _reject_unsafe_topology(inventory)
    _verify_exact_tree(root, inventory)
    dist_info = _one_dist_info(rows)
    _require_distribution_only(rows, dist_info)
    metadata = _read_owned(root, _row(rows, f"{dist_info}/METADATA"))
    _validate_metadata(metadata)
    record_row = _row(rows, f"{dist_info}/RECORD")
    record = _read_owned(root, record_row)
    record_rows = _parse_record(record, record_row[0])
    record_by_path = _record_ownership_index(rows, record_rows)
    verified = tuple(_verify_record_member(root, row, record_by_path) for row in rows)
    return _PackagingOwnershipProof(
        site_packages_root=root,
        dependency_inventory_digest=dependency_runtime.inventory_digest,
        record_digest=digest_bytes(record),
        owned_files_digest=digest_bytes(canonical_json_bytes(verified)),
        owned_file_count=len(verified),
        owned_file_bytes=sum(row[1] for row in verified),
        files=verified,
    )


def _loaded_packaging_binding(
    ownership: _PackagingOwnershipProof, modules: Mapping[str, ModuleType],
) -> dict[str, Any]:
    if type(ownership) is not _PackagingOwnershipProof:
        _fail("QUERY_BUILDER_PACKAGING_OWNERSHIP_INVALID")
    by_path = {path: (path, size, digest) for path, size, digest in ownership.files}
    observed = []
    loaded_names = tuple(sorted(
        name for name in modules
        if name == "packaging" or name.startswith("packaging.")
    ))
    if not set(_REQUIRED_MODULES) <= set(loaded_names):
        _fail("QUERY_BUILDER_PACKAGING_MODULE_MISSING")
    for name in loaded_names:
        observed.append(_loaded_module_row(
            ownership.site_packages_root, name, modules.get(name), by_path,
        ))
    return {
        "distribution_name": _NAME,
        "distribution_version": _VERSION,
        "dependency_inventory_digest": ownership.dependency_inventory_digest,
        "record_digest": ownership.record_digest,
        "owned_files_digest": ownership.owned_files_digest,
        "owned_file_count": ownership.owned_file_count,
        "owned_file_bytes": ownership.owned_file_bytes,
        "loaded_origins_digest": digest_bytes(canonical_json_bytes(observed)),
        "loaded_module_count": len(observed),
        "record_ownership_verified": True,
        "source_only_topology_verified": True,
        "bytecode_cache_absent": True,
        "loaded_origin_metadata_verified": True,
    }


def _loaded_module_row(
    root: Path, name: str, module: object,
    by_path: Mapping[str, tuple[str, int, str]],
) -> dict[str, Any]:
    if not isinstance(module, ModuleType):
        _fail("QUERY_BUILDER_PACKAGING_MODULE_MISSING")
    origin = _module_origin(root, module)
    row = by_path.get(origin)
    if row is None or not origin.endswith(".py"):
        _fail("QUERY_BUILDER_PACKAGING_MODULE_UNOWNED")
    loader = getattr(module, "__loader__", None)
    if (
        type(loader) is not importlib.machinery.SourceFileLoader
        or loader.name != name
        or os.path.abspath(loader.path) != os.path.abspath(str(module.__file__))
    ):
        _fail("QUERY_BUILDER_PACKAGING_LOADER_INVALID")
    cached = getattr(module, "__cached__", None)
    if cached and Path(str(cached)).exists():
        _fail("QUERY_BUILDER_PACKAGING_BYTECODE_CACHE_PRESENT")
    payload = _read_owned(root, row)
    return {
        "module": name, "origin": origin, "size": len(payload),
        "sha256": digest_bytes(payload),
    }


def _bind_inventory(binding: DependencyRuntimeBinding, inventory: Mapping[str, Any]) -> None:
    rows, directories = inventory["files"], inventory["directories"]
    if (
        digest_bytes(canonical_json_bytes(inventory)) != binding.inventory_digest
        or dependency_tree_digest(directories, rows) != binding.dependency_tree_digest
        or len(rows) != binding.file_count
        or len(directories) != binding.directory_count
        or sum(int(row["size"]) for row in rows) != binding.total_bytes
    ):
        _fail("QUERY_BUILDER_PACKAGING_INVENTORY_MISMATCH")


def _approved_site_root(binding: DependencyRuntimeBinding) -> Path:
    root = binding.site_packages_root
    if (
        not root.is_absolute()
        or root.drive.rstrip(":").upper() not in {"O", "E"}
        or root != binding.generation_root / "site-packages"
    ):
        _fail("QUERY_BUILDER_PACKAGING_ROOT_INVALID")
    try:
        resolved = root.resolve(strict=True)
    except OSError:
        _fail("QUERY_BUILDER_PACKAGING_ROOT_INVALID")
    if os.path.normcase(str(resolved)) != os.path.normcase(str(root.absolute())):
        _fail("QUERY_BUILDER_PACKAGING_ROOT_INVALID")
    return root


def _reject_unsafe_topology(inventory: Mapping[str, Any]) -> None:
    paths = [str(row["path"]) for row in inventory["files"]]
    paths.extend(str(path) for path in inventory["directories"])
    for path in paths:
        lowered = path.casefold()
        parts = lowered.split("/")
        if (
            "__pycache__" in parts
            or lowered.endswith(_FORBIDDEN_SUFFIXES)
            or Path(lowered).name in _FORBIDDEN_NAMES
            or lowered.endswith(".pth")
        ):
            _fail("QUERY_BUILDER_PACKAGING_SOURCE_ONLY_REQUIRED")


def _verify_exact_tree(root: Path, inventory: Mapping[str, Any]) -> None:
    rows = inventory["files"]
    limits = ModelCopyLimits(
        max_files=max(len(rows), 1),
        max_file_bytes=max(max(int(row["size"]) for row in rows), 1),
        max_total_bytes=max(sum(int(row["size"]) for row in rows), 1),
    )
    try:
        snapshot = snapshot_artifact_files(root, limits)
        actual_files = tuple(
            (relative, int(metadata.st_size))
            for relative, _path, metadata in snapshot.files
        )
        expected_files = tuple((row["path"], row["size"]) for row in rows)
        actual_directories = tuple(sorted(
            (
                path.relative_to(root).as_posix()
                for path in snapshot.directories if path != root
            ),
            key=str.casefold,
        ))
        for directory in snapshot.directories:
            require_unnamed_data_stream_only(directory)
    except Exception:
        _fail("QUERY_BUILDER_PACKAGING_TREE_INVALID")
    if actual_files != expected_files or actual_directories != tuple(inventory["directories"]):
        _fail("QUERY_BUILDER_PACKAGING_TREE_INVALID")


def _one_dist_info(rows: tuple[tuple[str, int, str], ...]) -> str:
    candidates = {
        path.split("/", 1)[0]
        for path, _size, _digest in rows
        if "/" in path and path.split("/", 1)[0].casefold().endswith(".dist-info")
    }
    if candidates != {_DIST_INFO}:
        _fail("QUERY_BUILDER_PACKAGING_DISTRIBUTION_SET_INVALID")
    return _DIST_INFO


def _require_distribution_only(
    rows: tuple[tuple[str, int, str], ...], dist_info: str,
) -> None:
    prefixes = ("packaging/", f"{dist_info}/")
    if any(not path.startswith(prefixes) for path, _size, _digest in rows):
        _fail("QUERY_BUILDER_PACKAGING_DISTRIBUTION_SET_INVALID")


def _row(
    rows: tuple[tuple[str, int, str], ...], path: str,
) -> tuple[str, int, str]:
    matches = [row for row in rows if row[0] == path]
    if len(matches) != 1:
        _fail("QUERY_BUILDER_PACKAGING_MEMBER_MISSING")
    return matches[0]


def _validate_metadata(raw: bytes) -> None:
    message = BytesParser().parsebytes(raw, headersonly=True)
    if message.get_all("Name", []) != [_NAME] or message.get_all("Version", []) != [_VERSION]:
        _fail("QUERY_BUILDER_PACKAGING_VERSION_INVALID")


def _parse_record(raw: bytes, record_path: str) -> tuple[tuple[str, int, str], ...]:
    try:
        text = raw.decode("utf-8")
        rows = tuple(csv.reader(io.StringIO(text, newline=""), strict=True))
    except (UnicodeDecodeError, csv.Error):
        _fail("QUERY_BUILDER_PACKAGING_RECORD_INVALID")
    parsed = []
    for row in rows:
        if len(row) != 3 or canonical_relative_path(row[0]) != row[0]:
            _fail("QUERY_BUILDER_PACKAGING_RECORD_INVALID")
        if row[0] == record_path:
            if row[1:] != ["", ""]:
                _fail("QUERY_BUILDER_PACKAGING_RECORD_INVALID")
            parsed.append((row[0], len(raw), digest_bytes(raw)))
            continue
        if not row[1].startswith("sha256=") or _RECORD_SIZE.fullmatch(row[2]) is None:
            _fail("QUERY_BUILDER_PACKAGING_RECORD_UNHASHED_MEMBER")
        parsed.append((row[0], int(row[2]), _record_digest(row[1][7:])))
    if sum(path == record_path for path, _size, _digest in parsed) != 1:
        _fail("QUERY_BUILDER_PACKAGING_RECORD_INVALID")
    return tuple(parsed)


def _record_ownership_index(
    inventory_rows: tuple[tuple[str, int, str], ...],
    record_rows: tuple[tuple[str, int, str], ...],
) -> dict[str, tuple[str, int, str]]:
    inventory_paths = {path for path, _size, _digest in inventory_rows}
    record_paths = {path for path, _size, _digest in record_rows}
    if (
        len(record_paths) != len(record_rows)
        or len({path.casefold() for path in record_paths}) != len(record_rows)
        or inventory_paths != record_paths
    ):
        _fail("QUERY_BUILDER_PACKAGING_RECORD_OWNERSHIP_INVALID")
    return {row[0]: row for row in record_rows}


def _record_digest(value: str) -> str:
    try:
        padded = (value + "=" * (-len(value) % 4)).encode("ascii")
        raw = base64.b64decode(padded, altchars=b"-_", validate=True)
    except (ValueError, TypeError, UnicodeError):
        _fail("QUERY_BUILDER_PACKAGING_RECORD_INVALID")
    canonical = base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")
    if len(raw) != 32 or canonical != value:
        _fail("QUERY_BUILDER_PACKAGING_RECORD_INVALID")
    return "sha256:" + raw.hex()


def _verify_record_member(
    root: Path, inventory_row: tuple[str, int, str],
    record_by_path: Mapping[str, tuple[str, int, str]],
) -> tuple[str, int, str]:
    record = record_by_path.get(inventory_row[0])
    if record is None or record[1:] != inventory_row[1:]:
        _fail("QUERY_BUILDER_PACKAGING_RECORD_OWNERSHIP_INVALID")
    payload = _read_owned(root, inventory_row)
    if len(payload) != inventory_row[1] or digest_bytes(payload) != inventory_row[2]:
        _fail("QUERY_BUILDER_PACKAGING_MEMBER_MUTATED")
    return inventory_row


def _read_owned(root: Path, row: tuple[str, int, str]) -> bytes:
    path = root / row[0]
    try:
        before = os.lstat(path)
        if not stat.S_ISREG(before.st_mode) or int(getattr(before, "st_nlink", 1)) != 1:
            _fail("QUERY_BUILDER_PACKAGING_MEMBER_INVALID")
        identity = confined_file_identity(before)
        proof = secure_digest_confined_file_impl(
            path, allowed_root=root, expected_identity=identity,
            max_bytes=max(row[1], 1),
        )
        payload, cursor = secure_read_confined_bytes_impl(
            path, allowed_root=root, max_bytes=row[1] + 1,
        )
        require_unnamed_data_stream_only(path)
        stable = confined_file_identity(os.lstat(path)) == identity
    except QueryRuntimeBuilderPackagingError:
        raise
    except Exception:
        _fail("QUERY_BUILDER_PACKAGING_MEMBER_UNAVAILABLE")
    if (
        not stable or cursor != row[1] or len(payload) != row[1]
        or proof.size != row[1] or proof.digest != row[2]
    ):
        _fail("QUERY_BUILDER_PACKAGING_MEMBER_MUTATED")
    return payload


def _module_origin(root: Path, module: ModuleType) -> str:
    raw = getattr(module, "__file__", None)
    if type(raw) is not str or not raw:
        _fail("QUERY_BUILDER_PACKAGING_MODULE_ORIGIN_INVALID")
    try:
        origin = Path(raw).absolute()
        relative = origin.relative_to(root.absolute()).as_posix()
    except (OSError, ValueError):
        _fail("QUERY_BUILDER_PACKAGING_MODULE_ORIGIN_INVALID")
    return relative


__all__ = [
    "QueryRuntimeBuilderPackagingError",
    "prove_builder_packaging_authority",
]
